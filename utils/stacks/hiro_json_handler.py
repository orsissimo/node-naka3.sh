#!/usr/bin/env python3
"""Handler for fetching and processing Hiro API transaction data."""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from utils.types.hiro.infrastructure import (
    ContractMetadata,
    TransferMetadata,
    ContractCallMetadata,
    ContractCallEvent,
)
from utils.stacks.hiro_api import HiroAPI
from utils.logger import logger
from utils.parsers import parse_contract_id, parse_abi, parse_abi_functions


@dataclass
class RangeFilter:
    """
    Represents a filtering range for transactions.

    Can filter by:
    - start_timestamp/end_timestamp: Uses burn_block_time (Bitcoin anchor time)
    - start_block_height/end_block_height: Uses block_height (Stacks block)
    - start_burn_block_height/end_burn_block_height: Uses burn_block_height (Bitcoin anchor block)

    All filters are optional and can be combined (AND logic).
    """

    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
    start_block_height: Optional[int] = None
    end_block_height: Optional[int] = None
    start_burn_block_height: Optional[int] = None
    end_burn_block_height: Optional[int] = None


@dataclass
class EventFilter:
    """
    Filter for specific event types and patterns.

    Can filter by:
    - event_types: List of event types to include (e.g., ["smart_contract_log", "stx_asset"])
    - event_names: List of event names to include (extracted from event repr)
    - sender_address: Filter events by sender
    - recipient_address: Filter events by recipient
    - contract_id: Filter events by contract ID

    All filters are optional and can be combined (AND logic).
    Can also be combined with RangeFilter for time/block filtering.
    """

    event_types: Optional[List[str]] = None
    event_names: Optional[List[str]] = None
    sender_address: Optional[str] = None
    recipient_address: Optional[str] = None
    contract_id: Optional[str] = None


def _parse_event_name(event_repr: str) -> Optional[str]:
    """Extract event name from Clarity event log representation."""
    event_match = re.search(r'\(event\s+"([^"]+)"\)', event_repr)
    return event_match.group(1) if event_match else None


def _matches_range_filter(item: Dict, range_filter: Optional[RangeFilter]) -> bool:
    """
    Check if an event/transaction is within the specified range filter.

    Args:
        item: Event or transaction dict to check
        range_filter: Optional RangeFilter criteria

    Returns:
        True if item matches filter (or no filter specified), False otherwise
    """
    if not range_filter:
        return True

    # Check block height if available and filter is specified
    if (
        range_filter.start_block_height is not None
        or range_filter.end_block_height is not None
    ):
        block_height = item.get("block_height")
        if block_height is None:
            # Block height not available - allow through
            # (Some API endpoints don't include block_height in events)
            return True

        if range_filter.start_block_height is not None:
            if block_height < range_filter.start_block_height:
                return False

        if range_filter.end_block_height is not None:
            if block_height > range_filter.end_block_height:
                return False

    # Check timestamp range if available and filter is specified
    if (
        range_filter.start_timestamp is not None
        or range_filter.end_timestamp is not None
    ):
        # Events typically don't have timestamps, transactions use burn_block_time
        timestamp = item.get("burn_block_time")
        if timestamp is None:
            # Try block_time as fallback
            timestamp = item.get("block_time")

        if timestamp is None:
            # No timestamp available - allow through
            return True

        if range_filter.start_timestamp is not None:
            if timestamp < range_filter.start_timestamp:
                return False

        if range_filter.end_timestamp is not None:
            if timestamp > range_filter.end_timestamp:
                return False

    # Check burn block height if available and filter is specified
    if (
        range_filter.start_burn_block_height is not None
        or range_filter.end_burn_block_height is not None
    ):
        burn_block_height = item.get("burn_block_height")
        if burn_block_height is None:
            # Not available - allow through
            return True

        if range_filter.start_burn_block_height is not None:
            if burn_block_height < range_filter.start_burn_block_height:
                return False

        if range_filter.end_burn_block_height is not None:
            if burn_block_height > range_filter.end_burn_block_height:
                return False

    return True


def _matches_event_filter(event: Dict, event_filter: Optional[EventFilter]) -> bool:
    """
    Check if an event matches the event filter criteria.

    Args:
        event: Event dict to check
        event_filter: Optional EventFilter criteria

    Returns:
        True if event matches filter (or no filter specified), False otherwise
    """
    if not event_filter:
        return True

    # Filter by event type
    if event_filter.event_types is not None:
        event_type = event.get("event_type")
        if event_type not in event_filter.event_types:
            return False

    # Filter by event name (for smart_contract_log events)
    if event_filter.event_names is not None:
        if event.get("event_type") == "smart_contract_log":
            contract_log = event.get("contract_log", {})
            value_repr = contract_log.get("value", {}).get("repr", "")
            event_name = _parse_event_name(value_repr)

            if event_name not in event_filter.event_names:
                return False

    # Filter by sender (for asset events)
    if event_filter.sender_address is not None:
        asset = event.get("asset", {})
        sender = asset.get("sender")
        if sender != event_filter.sender_address:
            return False

    # Filter by recipient (for asset events)
    if event_filter.recipient_address is not None:
        asset = event.get("asset", {})
        recipient = asset.get("recipient")
        if recipient != event_filter.recipient_address:
            return False

    # Filter by contract_id (for smart_contract_log events)
    if event_filter.contract_id is not None:
        if event.get("event_type") == "smart_contract_log":
            contract_log = event.get("contract_log", {})
            contract_id = contract_log.get("contract_id")
            if contract_id != event_filter.contract_id:
                return False

    return True


def _apply_filters(
    items: List[Dict],
    range_filter: Optional[RangeFilter] = None,
    event_filter: Optional[EventFilter] = None,
) -> List[Dict]:
    """
    Apply range and/or event filters to a list of items (events or transactions).

    Args:
        items: List of items (events or transactions) to filter
        range_filter: Optional RangeFilter for time/block filtering
        event_filter: Optional EventFilter for event-specific filtering

    Returns:
        Filtered list of items
    """
    if not range_filter and not event_filter:
        return items

    filtered = []
    for item in items:
        # Apply both filters (AND logic)
        if _matches_range_filter(item, range_filter) and _matches_event_filter(item, event_filter):
            filtered.append(item)

    return filtered


class ResponseCollection:
    """Manages a collection of API endpoint responses."""

    def __init__(self, target_identifier: str):
        """Initialize response collection given a target_identifier (tx_id, contract_id, address, etc.)"""
        self.data = {"target_tx_id": target_identifier, "endpoints": {}}

    def add(
        self, method_name: str, response: Any = None, error: Optional[str] = None
    ) -> None:
        result = {}

        if error:
            result["error"] = error
        else:
            # Convert Pydantic models to dict
            if hasattr(response, "model_dump"):
                result["response"] = response.model_dump()
            elif hasattr(response, "__dict__"):
                result["response"] = response.__dict__
            else:
                result["response"] = response

        self.data["endpoints"][method_name] = result

    def save(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def get_data(self) -> Dict[str, Any]:
        return self.data

    def __len__(self) -> int:
        """Return the number of endpoints in the collection."""
        return len(self.data["endpoints"])


class TransactionHandler:
    """
    Main handler for processing transactions from a txid.

    Delegates to specific handlers based on transaction type:
    - DeploymentHandler for smart contract deployments
    - ContractCallHandler for contract calls
    - TransferHandler for token transfers
    """

    def __init__(self, txid: str, api: HiroAPI, event_filter: Optional[EventFilter] = None):
        self._txid = txid
        self._api = api
        self._collection = ResponseCollection(txid)
        self._tx = None
        self._event_filter = event_filter

    def fetch_and_extract(self) -> ContractMetadata | ContractCallMetadata | TransferMetadata | None:
        """Fetch transaction data and extract metadata based on transaction type."""
        # Fetch transaction details
        try:
            self._tx = self._api.get_transaction_by_id(self._txid)
            self._collection.add("get_transaction_by_id", self._tx)
            logger.debug(f"Transaction fetched: {self._tx.tx_type}")
            logger.debug(f"Status: {self._tx.tx_status}")
        except Exception as e:
            logger.error(f"Failed to fetch transaction: {e}")
            self._collection.add("get_transaction_by_id", error=str(e))
            return None

        # Delegate to appropriate handler
        if self._tx.smart_contract:
            handler = DeploymentHandler(self._tx, self._api, self._collection, event_filter=self._event_filter)
            return handler.extract()
        elif self._tx.contract_call:
            handler = ContractCallHandler(self._tx, self._api, self._collection)
            return handler.extract()
        elif self._tx.token_transfer:
            handler = TransferHandler(self._tx, self._api, self._collection)
            return handler.extract()
        else:
            logger.warning(f"Unsupported transaction type: {self._tx.tx_type}")
            return None

    def save_collection(self, file_path: str) -> None:
        """Save the response collection to a file."""
        self._collection.save(file_path)

    def get_collection(self) -> ResponseCollection:
        """Get the response collection."""
        return self._collection

    def fetch_extract_and_save(self, output_dir: str) -> tuple[ContractMetadata | ContractCallMetadata | TransferMetadata | None, str | None]:
        """Fetch, extract, and save transaction data to a file."""
        # Fetch and extract metadata
        metadata = self.fetch_and_extract()

        if metadata is None:
            return None, None

        # Determine output filename based on metadata type
        import os

        if isinstance(metadata, ContractMetadata):
            filename = f"{metadata.contract_name}_mainnet_data.json"
        elif isinstance(metadata, ContractCallMetadata):
            filename = f"{metadata.contract_metadata.contract_name}_call_{metadata.tx_id[:8]}_mainnet_data.json"
        elif isinstance(metadata, TransferMetadata):
            filename = f"transfer_{metadata.tx_id[:8]}_mainnet_data.json"
        else:
            filename = f"tx_{self._txid[:8]}_mainnet_data.json"

        # Save to output directory
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, filename)
        self.save_collection(output_file)

        from utils.logger import logger
        logger.debug(f"All data saved to: {output_file}")
        logger.debug(f"Endpoints called: {len(self._collection)}")

        return metadata, output_file


class DeploymentHandler:
    """Handles smart contract deployment transactions."""

    def __init__(
        self,
        tx,
        api: HiroAPI,
        collection: ResponseCollection,
        event_filter: Optional[EventFilter] = None,
    ):
        self._tx = tx
        self._api = api
        self._collection = collection
        self._contract_id = tx.smart_contract.contract_id
        self._event_filter = event_filter

    def extract(self) -> ContractMetadata:
        """Extract contract metadata from deployment transaction."""
        logger.debug(f"Contract deployment detected")
        logger.debug(f"Contract ID: {self._contract_id}")

        # Fetch raw transaction
        self._fetch_raw_transaction()

        # Fetch contract details
        contract_response = self._fetch_contract_details()

        # Fetch contract events
        self._fetch_contract_events()

        # Parse contract data
        parsed_id = parse_contract_id(self._contract_id)
        abi_dict = parse_abi(contract_response["abi"])
        abi_functions = parse_abi_functions(abi_dict)
        contract_events = self._extract_contract_call_events()

        return ContractMetadata(
            contract_id=self._contract_id,
            contract_name=parsed_id.contract_name,
            contract_address=parsed_id.address,
            source_code=contract_response["source_code"],
            abi=abi_dict,
            abi_functions=abi_functions,
            tx_id=contract_response["tx_id"],
            contract_events=contract_events,
        )

    def _fetch_raw_transaction(self) -> None:
        """Fetch raw transaction data."""
        try:
            raw_tx = self._api.get_raw_transaction_by_id(self._tx.tx_id)
            self._collection.add("get_raw_transaction_by_id", raw_tx)
            logger.debug(f"Raw transaction fetched: {len(raw_tx)} chars")
        except Exception as e:
            logger.error(f"Failed to fetch raw transaction: {e}")
            self._collection.add("get_raw_transaction_by_id", error=str(e))

    def _fetch_contract_details(self) -> dict:
        """Fetch contract details and return response."""
        try:
            contract = self._api.get_contract_by_id(self._contract_id)
            self._collection.add("get_contract_by_id", contract)
            logger.debug(f"Contract fetched: {contract.contract_id}")
            logger.debug(f"Source code length: {len(contract.source_code)} chars")
            return contract.model_dump()
        except Exception as e:
            logger.error(f"Failed to fetch contract: {e}")
            self._collection.add("get_contract_by_id", error=str(e))
            raise

    def _fetch_contract_events(self) -> None:
        """Fetch contract events."""
        try:
            events = self._api.get_contract_events_by_id(self._contract_id)
            self._collection.add("get_contract_events_by_id", events)
            logger.debug(f"Contract events fetched: {len(events.results)} events")
        except Exception as e:
            logger.error(f"Failed to fetch contract events: {e}")
            self._collection.add("get_contract_events_by_id", error=str(e))

    def _extract_contract_call_events(self) -> List[ContractCallEvent]:
        """Extract and parse contract call events from collection data."""
        data = self._collection.get_data()

        if "get_contract_events_by_id" not in data["endpoints"]:
            return []

        events_response = data["endpoints"]["get_contract_events_by_id"]["response"]
        events = events_response["results"]

        # Reverse to get chronological order (API returns newest first)
        events = list(reversed(events))

        # Apply event filtering if provided
        if self._event_filter:
            events = _apply_filters(events, event_filter=self._event_filter)
            logger.debug(f"After filtering: {len(events)} events")

        contract_call_events = []
        for event in events:
            if event.get("event_type") == "smart_contract_log":
                contract_log = event.get("contract_log")
                if contract_log:
                    value_repr = contract_log["value"]["repr"]
                    event_name = _parse_event_name(value_repr)

                    contract_call_events.append(
                        ContractCallEvent(
                            event_repr=value_repr,
                            event_name=event_name,
                            tx_id=event["tx_id"],
                            event_index=event["event_index"],
                        )
                    )

        return contract_call_events


class ContractCallHandler:
    """Handles contract call transactions."""

    def __init__(self, tx, api: HiroAPI, collection: ResponseCollection):
        self._tx = tx
        self._api = api
        self._collection = collection
        self._contract_id = tx.contract_call.contract_id

    def extract(self) -> ContractCallMetadata:
        """Extract contract call metadata from contract call transaction."""
        logger.debug(f"Contract call detected")
        logger.debug(f"Contract ID: {self._contract_id}")
        logger.debug(f"Function: {self._tx.contract_call.function_name}")
        logger.debug(f"Args: {self._tx.contract_call.function_args}")

        # Fetch contract metadata (without events)
        contract_metadata = self._fetch_contract_metadata()

        # Return contract call metadata with function call details
        return ContractCallMetadata(
            tx_id=self._tx.tx_id,
            contract_metadata=contract_metadata,
            function_name=self._tx.contract_call.function_name,
            function_args=self._tx.contract_call.function_args or [],
            sender_address=self._tx.sender_address,
            fee=self._tx.fee_rate,
        )

    def _fetch_contract_metadata(self) -> ContractMetadata:
        """Fetch contract metadata for the called contract (without events)."""
        # Fetch contract details
        try:
            contract = self._api.get_contract_by_id(self._contract_id)
            self._collection.add("get_contract_by_id", contract)
            logger.debug(f"Contract fetched: {contract.contract_id}")
            logger.debug(f"Source code length: {len(contract.source_code)} chars")
        except Exception as e:
            logger.error(f"Failed to fetch contract: {e}")
            self._collection.add("get_contract_by_id", error=str(e))
            raise

        # Parse contract data
        parsed_id = parse_contract_id(self._contract_id)
        abi_dict = parse_abi(contract.abi)
        abi_functions = parse_abi_functions(abi_dict)

        return ContractMetadata(
            contract_id=self._contract_id,
            contract_name=parsed_id.contract_name,
            contract_address=parsed_id.address,
            source_code=contract.source_code,
            abi=abi_dict,
            abi_functions=abi_functions,
            tx_id=contract.tx_id,
            contract_events=None,  # Not fetched for contract calls
        )


class TransferHandler:
    """Handles token transfer transactions."""

    def __init__(self, tx, api: HiroAPI, collection: ResponseCollection):
        self._tx = tx
        self._api = api
        self._collection = collection

    def extract(self) -> TransferMetadata:
        """Extract transfer metadata."""
        logger.debug(f"Token transfer detected")
        logger.debug(f"Sender: {self._tx.sender_address}")
        logger.debug(f"Recipient: {self._tx.token_transfer.recipient_address}")
        logger.debug(f"Amount: {self._tx.token_transfer.amount}")

        return TransferMetadata(
            tx_id=self._tx.tx_id,
            sender_address=self._tx.sender_address,
            recipient_address=self._tx.token_transfer.recipient_address,
            amount=self._tx.token_transfer.amount,
            memo=self._tx.token_transfer.memo,
            fee=self._tx.fee_rate,
        )


class PrincipalHandler:
    """Handles fetching and processing all transactions for a principal address."""

    def __init__(
        self,
        principal: str,
        api: HiroAPI,
        range_filter: Optional[RangeFilter] = None,
        event_filter: Optional[EventFilter] = None,
    ):
        self._principal = principal
        self._api = api
        self._range_filter = range_filter
        self._event_filter = event_filter
        self._transactions = []
        self._transaction_list = None

    def fetch_transaction_list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs,
    ) -> List:
        """Fetch transactions for the principal from the API."""
        logger.debug(f"Fetching transactions for principal: {self._principal}")

        # Build API parameters
        api_params: Dict[str, Any] = {"from_address": self._principal}

        if limit is not None:
            api_params["limit"] = limit
        if offset is not None:
            api_params["offset"] = offset

        # Add filter range timestamp parameters if provided
        if self._range_filter:
            if self._range_filter.start_timestamp is not None:
                api_params["start_time"] = self._range_filter.start_timestamp
            if self._range_filter.end_timestamp is not None:
                api_params["end_time"] = self._range_filter.end_timestamp

        # Merge with any additional kwargs
        api_params.update(kwargs)

        # Fetch from API
        try:
            self._transaction_list = self._api.get_transaction_list(**api_params)
            logger.info(
                f"Fetched {len(self._transaction_list.results)} transactions from API"
            )
        except Exception as e:
            logger.error(f"Failed to fetch transaction list: {e}")
            return []

        # Apply client-side filtering
        if self._range_filter:
            # Convert Pydantic models to dicts for unified filtering
            tx_dicts = []
            for tx in self._transaction_list.results:
                if hasattr(tx, "model_dump"):
                    tx_dicts.append(tx.model_dump())
                elif hasattr(tx, "__dict__"):
                    tx_dicts.append(tx.__dict__)
                else:
                    tx_dicts.append(tx)

            filtered_dicts = _apply_filters(tx_dicts, range_filter=self._range_filter)

            # Map filtered results back to original transaction objects
            filtered_tx_ids = {tx_dict["tx_id"] for tx_dict in filtered_dicts}
            self._transactions = [
                tx for tx in self._transaction_list.results if tx.tx_id in filtered_tx_ids
            ]
        else:
            self._transactions = self._transaction_list.results

        logger.info(
            f"After filtering: {len(self._transactions)} transactions "
            f"(removed {len(self._transaction_list.results) - len(self._transactions)})"
        )

        return self._transactions

    def process_all_transactions(
        self, output_dir: str
    ) -> List[
        Tuple[str, ContractMetadata | ContractCallMetadata | TransferMetadata | None]
    ]:
        """
        Deep dive: Process each transaction through TransactionHandler.

        Creates individual ResponseCollection and metadata file for each transaction.
        If event_filter is provided, it will be passed to DeploymentHandler for filtering events.
        """
        if not self._transactions:
            logger.warning("No transactions to process. Call fetch_transaction_list() first.")
            return []

        logger.info(f"Processing {len(self._transactions)} transactions...")

        results = []
        for idx, tx in enumerate(self._transactions, 1):
            logger.debug(f"Processing transaction {idx}/{len(self._transactions)}: {tx.tx_id[:20]}...")

            handler = TransactionHandler(tx.tx_id, self._api, event_filter=self._event_filter)
            metadata, data_file = handler.fetch_extract_and_save(output_dir)

            if metadata:
                results.append((tx.tx_id, metadata))
                logger.debug(f"Saved to: {data_file}")
            else:
                logger.warning(f"Failed to process transaction: {tx.tx_id}")

        logger.success(
            f"Successfully processed {len(results)}/{len(self._transactions)} transactions"
        )

        return results

    def get_transactions(self) -> List:
        """Get the list of filtered transactions."""
        return self._transactions

    def get_transaction_count(self) -> int:
        """Get the count of filtered transactions."""
        return len(self._transactions)
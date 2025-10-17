#!/usr/bin/env python3
"""
Transaction data handler for Hiro API.

This module provides handlers for different transaction types:
- DeploymentHandler: Smart contract deployments
- ContractCallHandler: Contract function calls
- TransferHandler: Token transfers

All handlers are accessed through the main TransactionHandler class.
"""

import json
import re
from typing import Any, Dict, List, Optional

from utils.types.hiro.infrastructure import (
    ContractMetadata,
    TransferMetadata,
    ContractCallMetadata,
    ParsedContractId,
    AbiFunctions,
    ContractCallEvent,
)
from utils.hiro.hiro_api import HiroAPI
from utils.logger import logger


class ResponseCollection:
    """Manages a collection of API endpoint responses."""

    def __init__(self, target_identifier: str):
        """
        Initialize response collection.

        Args:
            target_identifier: The target being queried (tx_id, contract_id, address, etc.)
        """
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

    def __init__(self, txid: str):
        self._txid = txid
        self._api = HiroAPI()
        self._collection = ResponseCollection(txid)
        self._tx = None

    def fetch_and_extract(self) -> ContractMetadata | ContractCallMetadata | TransferMetadata | None:
        """
        Fetch transaction data and extract metadata based on transaction type.

        Returns:
            - ContractMetadata for smart contract deployments
            - ContractCallMetadata for contract calls
            - TransferMetadata for token transfers
            - None if fetch failed or unsupported type
        """
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
            handler = DeploymentHandler(self._tx, self._api, self._collection)
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
        """
        Fetch, extract, and save transaction data to a file.

        Args:
            output_dir: Directory where to save the JSON file

        Returns:
            Tuple of (metadata, file_path). Both None if failed.
        """
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

    def __init__(self, tx, api: HiroAPI, collection: ResponseCollection):
        self._tx = tx
        self._api = api
        self._collection = collection
        self._contract_id = tx.smart_contract.contract_id

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
        parsed_id = self._parse_contract_id(self._contract_id)
        abi_dict = self._parse_abi(contract_response["abi"])
        abi_functions = self._parse_abi_functions(abi_dict)
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

    def _parse_abi(self, abi_data) -> dict:
        """Parse ABI string to dict if needed."""
        return json.loads(abi_data) if isinstance(abi_data, str) else abi_data

    def _parse_abi_functions(self, abi_dict: dict) -> AbiFunctions:
        """Parse ABI and group functions by access type."""
        public_functions = [
            func for func in abi_dict["functions"] if func["access"] == "public"
        ]

        read_only_functions = [
            func for func in abi_dict["functions"] if func["access"] == "read_only"
        ]

        return AbiFunctions(
            public=public_functions,
            read_only=read_only_functions,
            public_names=[func["name"] for func in public_functions],
            read_only_names=[func["name"] for func in read_only_functions],
        )

    def _extract_contract_call_events(self) -> List[ContractCallEvent]:
        """Extract and parse contract call events from collection data."""
        data = self._collection.get_data()

        if "get_contract_events_by_id" not in data["endpoints"]:
            return []

        events_response = data["endpoints"]["get_contract_events_by_id"]["response"]
        events = events_response["results"]

        # Reverse to get chronological order (API returns newest first)
        events = list(reversed(events))

        contract_call_events = []
        for event in events:
            if event.get("event_type") == "smart_contract_log":
                contract_log = event.get("contract_log")
                if contract_log:
                    value_repr = contract_log["value"]["repr"]
                    event_name = self._parse_event_name(value_repr)

                    contract_call_events.append(
                        ContractCallEvent(
                            event_repr=value_repr,
                            event_name=event_name,
                            tx_id=event["tx_id"],
                            event_index=event["event_index"],
                        )
                    )

        return contract_call_events

    def _parse_event_name(self, event_repr: str) -> str | None:
        """Extract event name from Clarity event log representation."""
        event_match = re.search(r'\(event\s+"([^"]+)"\)', event_repr)
        return event_match.group(1) if event_match else None

    def _parse_contract_id(self, contract_id: str) -> ParsedContractId:
        """Split contract_id into address and contract name components."""
        parts = contract_id.split(".")
        return ParsedContractId(
            address=parts[0],
            contract_name=parts[1] if len(parts) > 1 else "",
        )


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

        # Use DeploymentHandler to fetch contract details
        deployment_handler = DeploymentHandler(self._tx, self._api, self._collection)
        deployment_handler._contract_id = self._contract_id
        contract_metadata = deployment_handler.extract()

        # Return contract call metadata with function call details
        return ContractCallMetadata(
            tx_id=self._tx.tx_id,
            contract_metadata=contract_metadata,
            function_name=self._tx.contract_call.function_name,
            function_args=self._tx.contract_call.function_args or [],
            sender_address=self._tx.sender_address,
            fee=self._tx.fee_rate,
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



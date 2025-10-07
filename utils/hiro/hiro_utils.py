#!/usr/bin/env python3
"""
Utility functions for working with Hiro API and mainnet data.
"""

from typing import List, Optional

from utils.logger import logger
from utils.hiro.hiro_api import HiroAPI
from utils.hiro.hiro_manager import (
    ResponseCollection,
    find_function_by_event,
)
from utils.types.hiro.infrastructure import (
    ContractCallEvent,
    ContractMetadata,
    AbiFunctions,
    ReplicationResult,
    ReadOnlyResult,
)
from utils.types.tokens import StacksToken


def fetch_contract_data(tx_id: str) -> str | None:
    """
    Fetch contract data from mainnet starting from a deployment transaction ID.

    This function:
    1. Fetches the transaction details
    2. Extracts contract information dynamically
    3. Fetches raw transaction data
    4. Fetches contract details (source code, ABI)
    5. Fetches contract events
    6. Saves all data to a JSON file

    Args:
        tx_id: The transaction ID of the contract deployment
        output_file: Optional path to save JSON output. If None, auto-generates
                    filename based on contract name or tx_id.

    Returns:
        Path to the saved JSON file containing all contract data
    """
    api = HiroAPI()
    collection = ResponseCollection(tx_id)

    logger.header("FETCHING CONTRACT DATA FROM MAINNET")

    # Step 1: Get transaction details
    logger.header("Step 1: Fetch transaction details")
    logger.info(f"Transaction ID: {tx_id}")

    contract_id = None

    try:
        tx = api.get_transaction_by_id(tx_id)
        collection.add("get_transaction_by_id", tx)
        logger.success(f"Transaction fetched: {tx.tx_type}")
        logger.info(f"Status: {tx.tx_status}")

        # Extract contract ID for subsequent calls
        if tx.contract_call:
            contract_id = tx.contract_call.contract_id
            logger.info(f"Contract call detected")
            logger.info(f"Contract ID: {contract_id}")
            logger.info(f"Function: {tx.contract_call.function_name}")
        elif tx.smart_contract:
            contract_id = tx.smart_contract.contract_id
            logger.info(f"Contract deployment detected")
            logger.info(f"Contract ID: {contract_id}")
        else:
            logger.warning(f"No contract information found in transaction")
            contract_id = None

    except Exception as e:
        logger.error(f"Failed to fetch transaction: {e}")
        collection.add("get_transaction_by_id", error=str(e))
        return None

    # Step 2: Get raw transaction
    logger.header("Step 2: Fetch raw transaction")

    try:
        raw_tx = api.get_raw_transaction_by_id(tx_id)
        collection.add("get_raw_transaction_by_id", raw_tx)
        logger.success(f"Raw transaction fetched: {len(raw_tx)} chars")
    except Exception as e:
        logger.error(f"Failed to fetch raw transaction: {e}")
        collection.add("get_raw_transaction_by_id", error=str(e))

    # Step 3: Get contract details
    if contract_id:
        logger.header("Step 3: Fetch contract details")

        try:
            contract = api.get_contract_by_id(contract_id)
            collection.add("get_contract_by_id", contract)
            logger.success(f"Contract fetched: {contract.contract_id}")
            logger.info(f"Source code length: {len(contract.source_code)} chars")
        except Exception as e:
            logger.error(f"Failed to fetch contract: {e}")
            collection.add("get_contract_by_id", error=str(e))

        # Step 4: Get contract events
        logger.header("Step 4: Fetch contract events")

        try:
            events = api.get_contract_events_by_id(contract_id)
            collection.add("get_contract_events_by_id", events)
            logger.success(f"Contract events fetched: {len(events.results)} events")
        except Exception as e:
            logger.error(f"Failed to fetch contract events: {e}")
            collection.add("get_contract_events_by_id", error=str(e))

    if contract_id:
        # Use contract name from contract_id
        contract_name = contract_id.split(".")[-1]
        output_file = f"{contract_name}_mainnet_data.json"
    else:
        # Fallback to tx_id based name
        output_file = f"contract_{tx_id[:8]}_mainnet_data.json"

    # Save to output file
    collection.save(output_file)

    logger.success(f"All data saved to: {output_file}")
    logger.info(f"Endpoints called: {len(collection)}")

    return output_file


def replicate_contract_call_events(
    contract_call_events: List[ContractCallEvent],
    contract_metadata: ContractMetadata,
    abi_functions: AbiFunctions,
    chain,
    caller_account,
    deployer_address: str,
    fee: Optional[StacksToken] = None,
    timeout: int = 120,
) -> List[ReplicationResult]:
    """
    Replicate contract call events from mainnet on local blockchain.

    This function:
    1. Iterates through each contract call event
    2. Finds the corresponding function in the contract source
    3. Calls the function on the local blockchain
    4. Returns results for each event

    Args:
        contract_call_events: List of parsed contract call events
        contract_metadata: Contract metadata (contains source code and contract name)
        abi_functions: Parsed ABI functions (contains public function names)
        chain: StacksChain instance for making blockchain calls
        caller_account: Account to use for calling functions
        deployer_address: Address where contract is deployed
        fee: Transaction fee (defaults to 10,000 microstx)
        timeout: Timeout for transaction confirmation in seconds

    Returns:
        List of ReplicationResult objects with status of each replication
    """
    if fee is None:
        fee = StacksToken.from_microstx(10_000)

    results = []

    for i, event in enumerate(contract_call_events):
        logger.info(f"Event {i+1}: {event.event_repr}")

        if not event.event_name:
            logger.warning(f"Could not parse event name from: {event.event_repr}")
            results.append(ReplicationResult(
                event_name="<unknown>",
                function_name=None,
                confirmed=False,
                txid=None,
                error="Could not parse event name"
            ))
            continue

        logger.info(f"Detected event: {event.event_name}")

        # Find which function contains this event
        function_name = find_function_by_event(event.event_name, contract_metadata.source_code)

        if not function_name or function_name not in abi_functions.public_names:
            logger.warning(f"Could not find function for event '{event.event_name}' in source code")
            results.append(ReplicationResult(
                event_name=event.event_name,
                function_name=function_name,
                confirmed=False,
                txid=None,
                error="Function not found in source code"
            ))
            continue

        logger.info(f"Found function in source: {function_name}")

        # Call the function
        call_result = chain.call_contract_write_function_and_confirm(
            caller_account=caller_account,
            contract_address=deployer_address,
            contract_name=contract_metadata.contract_name,
            function_name=function_name,
            function_args=[],
            fee=fee,
            timeout=timeout,
        )

        if call_result.confirmed:
            logger.success(f"{function_name} confirmed: {call_result.txid}")
            results.append(ReplicationResult(
                event_name=event.event_name,
                function_name=function_name,
                confirmed=True,
                txid=call_result.txid,
            ))
        else:
            logger.error(f"{function_name} failed")
            results.append(ReplicationResult(
                event_name=event.event_name,
                function_name=function_name,
                confirmed=False,
                txid=call_result.txid if hasattr(call_result, 'txid') else None,
                error="Transaction failed"
            ))

    return results


def call_read_only_functions(
    abi_functions: AbiFunctions,
    contract_metadata: ContractMetadata,
    chain,
    caller_address: str,
    deployer_address: str,
) -> List[ReadOnlyResult]:
    """
    Call all read-only functions from a contract's ABI.

    This function:
    1. Iterates through all read-only functions in the ABI
    2. Calls each function on the blockchain
    3. Returns results for each function call

    Args:
        abi_functions: Parsed ABI functions
        contract_metadata: Contract metadata (contains contract name)
        chain: StacksChain instance for making blockchain calls
        caller_address: Address to use as sender for read-only calls
        deployer_address: Address where contract is deployed

    Returns:
        List of ReadOnlyResult objects with status of each function call
    """
    results = []

    logger.info(f"Found {len(abi_functions.read_only)} read-only functions")

    for func in abi_functions.read_only:
        function_name = func["name"]
        logger.info(f"Calling read-only: {function_name}")

        read_result = chain.call_contract_read_function(
            contract_address=deployer_address,
            contract_name=contract_metadata.contract_name,
            function_name=function_name,
            sender=caller_address,
            function_args=[],
        )

        if read_result.okay:
            logger.success(f"{function_name}: {read_result.result}")
            results.append(ReadOnlyResult(
                function_name=function_name,
                success=True,
                result=read_result.result,
            ))
        else:
            logger.error(f"{function_name} failed: {read_result.cause}")
            results.append(ReadOnlyResult(
                function_name=function_name,
                success=False,
                error=read_result.cause,
            ))

    return results

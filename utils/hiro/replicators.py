#!/usr/bin/env python3
"""
Transaction replication utilities for replaying mainnet behavior locally.

This module provides the ContractReplicator for replicating contract deployments and operations.
"""

import re
from typing import List, Optional

from utils.logger import logger
from utils.types.hiro.infrastructure import (
    ContractMetadata,
    ReplicationResult,
    ReadOnlyResult,
)
from utils.types.tokens import StacksToken


def _find_function_by_event(event_name: str, source_code: str) -> str | None:
    """
    Find which function contains a specific event by searching the source code.

    This searches for print statements containing the event name, then determines
    which public function contains that print statement.

    Args:
        event_name: The event name (e.g., "incremented")
        source_code: The contract source code

    Returns:
        The function name that contains this event, or None if not found
    """
    # Search for the event in print statements
    # Pattern: (print {event: "event_name"
    event_pattern = rf'\(print\s+\{{[^}}]*event:\s*"{re.escape(event_name)}"'
    event_match = re.search(event_pattern, source_code)

    if not event_match:
        return None

    # Find the position of the event
    event_pos = event_match.start()

    # Find all public function definitions
    # Pattern: (define-public (function-name)
    func_pattern = r"\(define-public\s+\(([a-zA-Z0-9\-_]+)"

    # Find all functions and their positions
    functions = []
    for match in re.finditer(func_pattern, source_code):
        func_name = match.group(1)
        func_start = match.start()
        functions.append((func_name, func_start))

    # Find which function contains this event
    # The event belongs to the last function that starts before the event position
    containing_function = None
    for func_name, func_start in sorted(functions, key=lambda x: x[1]):
        if func_start < event_pos:
            containing_function = func_name
        else:
            break

    return containing_function


class ContractReplicator:
    """
    Replicates mainnet contract operations on a local blockchain.

    This class encapsulates all operations needed to replay contract
    behavior from mainnet onto a local test environment.
    """

    def __init__(self, chain, metadata: ContractMetadata):
        """
        Initialize the contract replicator.

        Args:
            chain: StacksChain instance for making blockchain calls
            metadata: Contract metadata from mainnet
        """
        self._chain = chain
        self._metadata = metadata

    def replicate_events(
        self,
        caller_account,
        local_deployer_address: str,
        fee: Optional[StacksToken] = None,
        timeout: int = 120,
    ) -> List[ReplicationResult]:
        """
        Replicate contract call events from mainnet on local blockchain.

        This method:
        1. Iterates through each contract call event
        2. Finds the corresponding function in the contract source
        3. Calls the function on the local blockchain
        4. Returns results for each event

        Args:
            caller_account: Account to use for calling functions
            local_deployer_address: Address where contract is deployed locally
            fee: Transaction fee (defaults to 10,000 microstx)
            timeout: Timeout for transaction confirmation in seconds

        Returns:
            List of ReplicationResult objects with status of each replication
        """
        if fee is None:
            fee = StacksToken.from_microstx(10_000)

        results = []

        for i, event in enumerate(self._metadata.contract_events):
            logger.info(f"Event {i+1}: {event.event_repr}")

            if not event.event_name:
                logger.warning(f"Could not parse event name from: {event.event_repr}")
                results.append(
                    ReplicationResult(
                        event_name="<unknown>",
                        function_name=None,
                        confirmed=False,
                        txid=None,
                        error="Could not parse event name",
                    )
                )
                continue

            logger.info(f"Detected event: {event.event_name}")

            # Find which function contains this event
            function_name = _find_function_by_event(
                event.event_name, self._metadata.source_code
            )

            if (
                not function_name
                or function_name not in self._metadata.abi_functions.public_names
            ):
                logger.warning(
                    f"Could not find function for event '{event.event_name}' in source code"
                )
                results.append(
                    ReplicationResult(
                        event_name=event.event_name,
                        function_name=function_name,
                        confirmed=False,
                        txid=None,
                        error="Function not found in source code",
                    )
                )
                continue

            logger.info(f"Found function in source: {function_name}")

            # Call the function
            call_result = self._chain.call_contract_write_function_and_confirm(
                caller_account=caller_account,
                contract_address=local_deployer_address,
                contract_name=self._metadata.contract_name,
                function_name=function_name,
                function_args=[],
                fee=fee,
                timeout=timeout,
            )

            if call_result.confirmed:
                logger.success(f"{function_name} confirmed: {call_result.txid}")
                results.append(
                    ReplicationResult(
                        event_name=event.event_name,
                        function_name=function_name,
                        confirmed=True,
                        txid=call_result.txid,
                    )
                )
            else:
                logger.error(f"{function_name} failed")
                results.append(
                    ReplicationResult(
                        event_name=event.event_name,
                        function_name=function_name,
                        confirmed=False,
                        txid=call_result.txid if hasattr(call_result, "txid") else None,
                        error="Transaction failed",
                    )
                )

        return results

    def call_read_only_functions(
        self,
        caller_address: str,
        local_deployer_address: str,
    ) -> List[ReadOnlyResult]:
        """
        Call all read-only functions from the contract's ABI.

        This method:
        1. Iterates through all read-only functions in the ABI
        2. Calls each function on the blockchain
        3. Returns results for each function call

        Args:
            caller_address: Address to use as sender for read-only calls
            local_deployer_address: Address where contract is deployed locally

        Returns:
            List of ReadOnlyResult objects with status of each function call
        """
        results = []

        logger.info(
            f"Found {len(self._metadata.abi_functions.read_only)} read-only functions"
        )

        for func in self._metadata.abi_functions.read_only:
            function_name = func["name"]
            logger.info(f"Calling read-only: {function_name}")

            read_result = self._chain.call_contract_read_function(
                contract_address=local_deployer_address,
                contract_name=self._metadata.contract_name,
                function_name=function_name,
                sender=caller_address,
                function_args=[],
            )

            if read_result.okay:
                logger.success(f"{function_name}: {read_result.result}")
                results.append(
                    ReadOnlyResult(
                        function_name=function_name,
                        success=True,
                        result=read_result.result,
                    )
                )
            else:
                logger.error(f"{function_name} failed: {read_result.cause}")
                results.append(
                    ReadOnlyResult(
                        function_name=function_name,
                        success=False,
                        error=read_result.cause,
                    )
                )

        return results



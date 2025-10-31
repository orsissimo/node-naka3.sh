#!/usr/bin/env python3
"""Advanced contract operations and macros for Stacks blockchain."""

import re
from typing import List, Optional

from utils.logger import logger
from utils.types.hiro.infrastructure import (
    ContractMetadata,
    ContractCallEvent,
    EventCallResult,
    ReadOnlyResult,
)
from utils.types.tokens import StacksToken


def _find_function_by_event(event_name: str, source_code: str) -> str | None:
    """Find which function contains a specific event by searching the source code."""
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


class ContractMacros:
    """Advanced contract operations for Stacks blockchain."""

    def __init__(self, chain, metadata: ContractMetadata):
        """
        Initialize the contract macros.

        Args:
            chain: StacksChain instance for making blockchain calls
            metadata: Contract metadata containing ABI, source code, and events
        """
        self._chain = chain
        self._metadata = metadata

    def call_events(
        self,
        caller_account,
        local_deployer_address: str,
        events: Optional[List[ContractCallEvent]] = None,
        fee: Optional[StacksToken] = None,
        timeout: int = 120,
    ) -> List[EventCallResult]:
        """Call contract functions based on provided events or metadata events."""
        if fee is None:
            fee = StacksToken.from_microstx(10_000)

        # Use provided events, or fallback to metadata events, or empty list
        events = events or self._metadata.contract_events or []

        if not events:
            logger.warning("No events available to process")
            return []

        results = []

        for i, event in enumerate(events):
            logger.debug(f"Event {i+1}: {event.event_repr}")

            if not event.event_name:
                logger.warning(f"Could not parse event name from: {event.event_repr}")
                results.append(
                    EventCallResult(
                        event_name="<unknown>",
                        function_name=None,
                        confirmed=False,
                        txid=None,
                        error="Could not parse event name",
                    )
                )
                continue

            logger.debug(f"Detected event: {event.event_name}")

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
                    EventCallResult(
                        event_name=event.event_name,
                        function_name=function_name,
                        confirmed=False,
                        txid=None,
                        error="Function not found in source code",
                    )
                )
                continue

            logger.debug(f"Found function in source: {function_name}")

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
                    EventCallResult(
                        event_name=event.event_name,
                        function_name=function_name,
                        confirmed=True,
                        txid=call_result.txid,
                    )
                )
            else:
                logger.error(f"{function_name} failed")
                results.append(
                    EventCallResult(
                        event_name=event.event_name,
                        function_name=function_name,
                        confirmed=False,
                        txid=call_result.txid if hasattr(call_result, "txid") else None,
                        error="Transaction failed",
                    )
                )

        return results

    # TODO: Add option to pass a list of readonly functions to override all
    def call_read_only_functions(
        self,
        caller_address: str,
        local_deployer_address: str,
    ) -> List[ReadOnlyResult]:
        """Call all read-only functions from the contract's ABI."""
        results = []

        logger.debug(
            f"Found {len(self._metadata.abi_functions.read_only)} read-only functions"
        )

        for func in self._metadata.abi_functions.read_only:
            function_name = func["name"]
            logger.debug(f"Calling read-only: {function_name}")

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



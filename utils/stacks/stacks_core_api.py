#!/usr/bin/env python3

import requests
from typing import List, Optional, Dict, Any, TypeVar, Type, Union
from ..logger import logger
from ..api_client import APIClient
from ..types.stacks.api import *
from ..types.stacks.exceptions import *
from ..types.wrappers import Integer, Bytes, String, SortitionList

T = TypeVar("T")


class StacksCoreAPI:
    def __init__(
        self,
        base_url: str = "http://localhost:20443",
        auth_token: Optional[str] = None,
        timeout: int = 20,
    ):
        self._client = APIClient(
            base_url=base_url,
            timeout=timeout,
            timeout_exception=StacksTimeoutException,
            network_exception=StacksNetworkException,
            http_exception=StacksHTTPException,
        )
        if auth_token:
            self._client.session.headers.update(
                {"Authorization": f"Basic {auth_token}"}
            )

    @property
    def base_url(self) -> str:
        return self._client.base_url

    @property
    def timeout(self) -> int:
        return self._client.timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self._client.timeout = value

    def _parse_hex_balance(self, balance_hex: Union[str, int, None]) -> int:
        """Convert hex balance string to integer."""
        if balance_hex is None:
            logger.warning("Received None balance from API, defaulting to 0")
            return 0

        if not isinstance(balance_hex, str):
            logger.warning(
                f"Received non-string balance: {type(balance_hex)} = {balance_hex}, attempting conversion"
            )
            balance_hex = str(balance_hex)

        balance_hex = balance_hex.strip()
        if not balance_hex:
            logger.warning("Received empty balance string from API, defaulting to 0")
            return 0

        try:
            if balance_hex.startswith("0x"):
                return int(balance_hex, 16)
            return int(balance_hex)
        except ValueError as e:
            logger.error(f"Failed to parse balance '{balance_hex}' as integer: {e}")
            logger.error(
                "This might indicate an API format change - please verify against latest API docs"
            )
            raise StacksValidationException(
                f"Unable to parse balance value '{balance_hex}' as integer"
            ) from e

    def _extract_error_message(
        self, response: requests.Response, error_details: Dict[str, Any]
    ) -> str:
        """Extract error message from Stacks API error response."""
        reason = error_details.get("reason", "Unknown API error")
        reason_data = error_details.get("reason_data", {})
        if reason_data:
            return (
                f"API Error ({response.status_code}): {reason} - Details: {reason_data}"
            )
        return f"API Error ({response.status_code}): {reason}"

    def _handle_custom_types(
        self, response: requests.Response, response_type: Type[T], content_type: str
    ) -> Optional[T]:
        """Handle Stacks-specific wrapper types."""
        if response_type is Integer:
            if "application/json" in content_type:
                return Integer(response.json())  # type: ignore
            return Integer(response.text.strip('"'))  # type: ignore

        if response_type is Bytes:
            if "application/octet-stream" in content_type:
                return Bytes(response.content)  # type: ignore
            else:
                # Handle hex-encoded bytes in JSON responses
                data = (
                    response.json()
                    if "application/json" in content_type
                    else response.text
                )
                if isinstance(data, str) and data.startswith("0x"):
                    return Bytes(data)  # type: ignore
                return Bytes(response.content)  # type: ignore

        if response_type is String:
            return String(response.text.strip('"'))  # type: ignore

        if response_type is SortitionList:
            data = (
                response.json() if "application/json" in content_type else response.text
            )
            return SortitionList.from_raw(data)  # type: ignore

        return None

    # --- V2 Transactions, Accounts, and Info ---
    def get_info(self) -> NodeInfo:
        """GET /v2/info - Get Core API information."""
        return self._client.do_get(
            "/v2/info", NodeInfo, self._extract_error_message, self._handle_custom_types
        )

    def post_raw_transaction(self, raw_tx_bytes: bytes) -> String:
        """POST /v2/transactions - Broadcast a raw transaction. Use bytes.fromhex(cli_hex) where cli_hex comes from CLI functions."""
        return self._client.do_post(
            "/v2/transactions",
            String,
            self._extract_error_message,
            self._handle_custom_types,
            data=raw_tx_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )

    def get_account_info(
        self, principal: str, *, proof: Optional[int] = None, tip: Optional[str] = None
    ) -> AccountInfo:
        """GET /v2/accounts/{principal} - Get account information. Expects principal as address string."""
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        return self._client.do_get(
            f"/v2/accounts/{principal}",
            AccountInfo,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
            address=principal,
            balance=lambda data: self._parse_hex_balance(data.get("balance", "0x0")),
        )

    def get_pox_info(self, *, tip: Optional[str] = None) -> PoxInfo:
        """GET /v2/pox - Get Proof of Transfer (PoX) information."""
        return self._client.do_get(
            "/v2/pox",
            PoxInfo,
            self._extract_error_message,
            self._handle_custom_types,
            params={"tip": tip} if tip else {},
        )

    # --- V2 Smart Contracts and Clarity ---
    def call_read_only_function(
        self,
        contract_address: str,
        contract_name: str,
        function_name: str,
        sender: str,
        arguments: List[str],
        *,
        tip: Optional[str] = None,
    ) -> ReadOnlyFunctionResult:
        """
        POST /v2/contracts/call-read/{...} - Call a read-only function.
        Note: 'arguments' parameter must be hex-encoded Clarity values (use clarity-cli to encode: e.g. 'u100' -> '0x0100000000000000000000000000000064').
        """
        endpoint = f"/v2/contracts/call-read/{contract_address}/{contract_name}/{function_name}"
        return self._client.do_post(
            endpoint,
            ReadOnlyFunctionResult,
            self._extract_error_message,
            self._handle_custom_types,
            json_data={"sender": sender, "arguments": arguments},
            params={"tip": tip} if tip else {},
        )

    def get_contract_source(
        self,
        contract_address: str,
        contract_name: str,
        *,
        proof: Optional[int] = None,
        tip: Optional[str] = None,
    ) -> ContractSource:
        """GET /v2/contracts/source/{...} - Get contract source code."""
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        return self._client.do_get(
            f"/v2/contracts/source/{contract_address}/{contract_name}",
            ContractSource,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
        )

    def get_contract_interface(
        self, contract_address: str, contract_name: str, *, tip: Optional[str] = None
    ) -> ContractInterface:
        """GET /v2/contracts/interface/{...} - Get contract interface."""
        return self._client.do_get(
            f"/v2/contracts/interface/{contract_address}/{contract_name}",
            ContractInterface,
            self._extract_error_message,
            self._handle_custom_types,
            params={"tip": tip} if tip else {},
        )

    def get_map_entry(
        self,
        contract_address: str,
        contract_name: str,
        map_name: str,
        key_hex_json_string: str,
        *,
        proof: Optional[int] = None,
        tip: Optional[str] = None,
    ) -> Optional[MapEntry]:
        """
        POST /v2/map_entry/{...} - Get a data-map entry.
        Note: 'key_hex_json_string' must be hex-encoded Clarity value (use clarity-cli to encode: e.g. 'u100' -> '0x0100000000000000000000000000000064').
        """
        endpoint = f"/v2/map_entry/{contract_address}/{contract_name}/{map_name}"
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        # API expects JSON string atom containing the hex key
        import json

        return self._client.do_post(
            endpoint,
            MapEntry,
            self._extract_error_message,
            self._handle_custom_types,
            data=json.dumps(key_hex_json_string),
            headers={"Content-Type": "application/json"},
            params=params,
        )

    def get_is_trait_implemented(
        self,
        contract_address: str,
        contract_name: str,
        trait_contract_address: str,
        trait_contract_name: str,
        trait_name: str,
        *,
        tip: Optional[str] = None,
    ) -> TraitImplementationResponse:
        """GET /v2/traits/{...} - Check if a contract implements a trait."""
        endpoint = (
            f"/v2/traits/{contract_address}/{contract_name}/"
            f"{trait_contract_address}/{trait_contract_name}/{trait_name}"
        )
        return self._client.do_get(
            endpoint,
            TraitImplementationResponse,
            self._extract_error_message,
            self._handle_custom_types,
            params={"tip": tip} if tip else {},
        )

    # --- V2 Fees ---
    def get_fee_rate_for_transfer(self) -> Integer:
        """GET /v2/fees/transfer - Get estimated fee rate for STX transfers."""
        return self._client.do_get(
            "/v2/fees/transfer",
            Integer,
            self._extract_error_message,
            self._handle_custom_types,
        )

    # --- V3 Blocks, Tenures, and Transactions ---
    def get_block_by_id(self, block_id: str) -> Bytes:
        """GET /v3/blocks/{block_id} - Fetch a Nakamoto block by its ID hash. Expects block_id hash string. Returns raw block bytes."""
        return self._client.do_get(
            f"/v3/blocks/{block_id}",
            Bytes,
            self._extract_error_message,
            self._handle_custom_types,
        )

    def get_block_by_height(
        self, block_height: int, *, tip: Optional[str] = None
    ) -> Bytes:
        """GET /v3/blocks/height/{block_height} - Fetch a Nakamoto block by height. Expects block_height int. Returns raw block bytes."""
        params = {"tip": tip} if tip else {}
        return self._client.do_get(
            f"/v3/blocks/height/{block_height}",
            Bytes,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
        )

    def get_transaction_by_id(
        self, txid: str, is_retry_context: bool = False
    ) -> TransactionDetails:
        """GET /v3/transaction/{txid} - Retrieve transaction details. Expects txid string (e.g. from transfer_result.txid)."""
        return self._client.do_get(
            f"/v3/transaction/{txid}",
            TransactionDetails,
            self._extract_error_message,
            self._handle_custom_types,
            is_retry_context=is_retry_context,
            txid=txid,
            tx_status="unknown",
            tx_type="unknown",
        )

    def get_tenure_info(self) -> Optional[TenureInfo]:
        """GET /v3/tenures/info - Fetch metadata about the ongoing Nakamoto tenure."""
        return self._client.do_get(
            "/v3/tenures/info",
            TenureInfo,
            self._extract_error_message,
            self._handle_custom_types,
        )

    def get_tenure_blocks(self, block_id: str, *, stop: Optional[str] = None) -> Bytes:
        """
        GET /v3/tenures/{block_id} - Fetch a sequence of Nakamoto blocks in a tenure.
        Expects block_id as hex string. Returns raw bytes containing sequence of blocks in the tenure.
        """
        params = {"stop": stop} if stop else {}
        return self._client.do_get(
            f"/v3/tenures/{block_id}",
            Bytes,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
        )

    def get_sortitions(
        self, *, lookup_kind: Optional[str] = None, lookup: Optional[str] = None
    ) -> List[SortitionInfo]:
        """GET /v3/sortitions/{lookup_kind}/{lookup} - Fetch burnchain block info."""
        endpoint = "/v3/sortitions"
        if lookup_kind and lookup:
            endpoint += f"/{lookup_kind}/{lookup}"
        elif lookup_kind:
            endpoint += f"/{lookup_kind}"

        # Get sortition data using SortitionList wrapper
        sortition_list = self._client.do_get(
            endpoint,
            SortitionList,
            self._extract_error_message,
            self._handle_custom_types,
        )

        # Parse each item into SortitionInfo
        return [SortitionInfo.model_validate(item) for item in sortition_list.value]

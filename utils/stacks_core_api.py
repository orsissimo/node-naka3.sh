#!/usr/bin/env python3

import requests
import json
from typing import List, Optional, Dict, Any, TypeVar, Type, Union
from .logger import logger, Colors
from .parsers import parse_api_response
from .types.api import *
from .types.exceptions import *
from .types.wrappers import Integer, Bytes, String, SortitionList

T = TypeVar("T")


class StacksCoreAPI:
    def __init__(
        self,
        base_url: str = "http://localhost:20443",
        auth_token: Optional[str] = None,
        timeout: int = 20,
    ):
        self._base_url = self._validate_url(base_url)
        self._session = requests.Session()
        self._timeout = self._validate_timeout(timeout)
        if auth_token:
            self._session.headers.update({"Authorization": f"Basic {auth_token}"})

    def _validate_url(self, url: str) -> str:
        if not url:
            raise ValueError("Base URL cannot be empty")
        url = url.rstrip("/")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return url

    def _validate_timeout(self, timeout: int) -> int:
        if timeout <= 0:
            raise ValueError("Timeout must be a positive integer")
        return timeout

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout(self) -> int:
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self._timeout = self._validate_timeout(value)

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

    def _send_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make raw API request and return response object for centralized handling"""
        url = f"{self._base_url}{endpoint}"
        logger.debug(f"-> {method} {url}")

        try:
            response = self._session.request(
                method, url, **kwargs, timeout=self._timeout
            )
            if 200 <= response.status_code < 300:
                indicator = f"{Colors.GREEN}✓{Colors.RESET}"
            elif 400 <= response.status_code < 500:
                indicator = f"{Colors.RED}✗{Colors.RESET}"
            elif 500 <= response.status_code < 600:
                indicator = f"{Colors.RED}✗{Colors.RESET}"
            else:
                indicator = f"{Colors.YELLOW}?{Colors.RESET}"

            logger.debug(f"<- Status: {response.status_code} {indicator}")
            return response
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout occurred: {str(e)}")
            raise StacksTimeoutException(f"Request timeout for {method} {url}") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error occurred: {str(e)}")
            raise StacksNetworkException(f"Connection error for {method} {url}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"An HTTP request error occurred: {str(e)}")
            raise StacksNetworkException(
                f"Request failed for {method} {url}: {str(e)}"
            ) from e

    def _handle_api_response(
        self,
        response: requests.Response,
        response_type: Optional[Type[T]] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> Any:
        """
        Centralized handler for all API responses.
        On success (200), intelligently parses and returns the body content.
        On failure, raises appropriate StacksAPIException with details.
        """
        if response.status_code != 200:
            error_details = {}  # Initialize to prevent unbound variable
            try:
                error_details = response.json()
                reason = error_details.get("reason", "Unknown API error")
                reason_data = error_details.get("reason_data", {})
                error_message = f"API Error ({response.status_code}): {reason} - Details: {reason_data}"
            except json.JSONDecodeError:
                error_message = f"API Error ({response.status_code}): {response.text}"

            if is_retry_context and response.status_code == 404:
                logger.warning(
                    f"API call temporarily failed (will retry): {error_message}"
                )
            else:
                logger.error(f"API call failed: {error_message}")

            raise StacksHTTPException(
                error_message,
                status_code=response.status_code,
                error_details=error_details,
            )

        # Handle successful responses
        content_type = response.headers.get("Content-Type", "")

        # Handle special wrapper types that don't come from JSON
        if response_type is not None:
            if response_type is Integer:
                if "application/json" in content_type:
                    return Integer(response.json())
                return Integer(response.text.strip('"'))

            if response_type is Bytes:
                if "application/octet-stream" in content_type:
                    return Bytes(response.content)
                else:
                    # Handle hex-encoded bytes in JSON responses
                    data = (
                        response.json()
                        if "application/json" in content_type
                        else response.text
                    )
                    if isinstance(data, str) and data.startswith("0x"):
                        return Bytes(data)
                    return Bytes(response.content)

            if response_type is String:
                return String(response.text.strip('"'))

            if response_type is SortitionList:
                data = (
                    response.json()
                    if "application/json" in content_type
                    else response.text
                )
                return SortitionList.from_raw(data)

        if "application/json" in content_type:
            data = response.json()
            # If response_type is provided, automatically parse the JSON response
            if response_type is not None:
                # Apply any additional data modifications from parse_kwargs
                for key, value in parse_kwargs.items():
                    if callable(value):
                        # If value is a callable, call it with the data as parameter
                        data[key] = value(data)
                    else:
                        data[key] = value
                return parse_api_response(data, response_type)  # type: ignore # FIXME: Can we avoid this ignore?
            return data
        elif "application/octet-stream" in content_type:
            return response.content
        else:
            return response.text.strip('"')

    def _do_request(
        self,
        method: str,
        endpoint: str,
        response_type: Optional[Type[T]] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> Any:
        """
        Combines _send_request + _handle_api_response in a single call.
        """
        kwargs = {}
        if params:
            kwargs["params"] = params
        if json_data:
            kwargs["json"] = json_data
        if data:
            kwargs["data"] = data
        if headers:
            kwargs["headers"] = headers

        response = self._send_request(method, endpoint, **kwargs)
        return self._handle_api_response(
            response, response_type, is_retry_context, **parse_kwargs
        )

    def do_get(
        self,
        endpoint: str,
        response_type: Type[T],
        params: Optional[Dict] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> T:
        """
        Typed GET request.
        Returns typed object with automatic JSON parsing and exception handling.
        Always requires a response_type and returns T.
        """
        return self._do_request(
            "GET",
            endpoint,
            response_type,
            params=params,
            is_retry_context=is_retry_context,
            **parse_kwargs,
        )

    def do_post(
        self,
        endpoint: str,
        response_type: Type[T],
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> T:
        """
        Typed POST request.
        Returns typed object with automatic JSON parsing and exception handling.
        Always requires a response_type and returns T.
        """
        return self._do_request(
            "POST",
            endpoint,
            response_type,
            params=params,
            json_data=json_data,
            data=data,
            headers=headers,
            is_retry_context=is_retry_context,
            **parse_kwargs,
        )

    # --- V2 Transactions, Accounts, and Info ---
    def get_info(self) -> NodeInfo:
        """GET /v2/info - Get Core API information."""
        return self.do_get("/v2/info", NodeInfo)

    def post_raw_transaction(self, raw_tx_bytes: bytes) -> String:
        """POST /v2/transactions - Broadcast a raw transaction. Use bytes.fromhex(cli_hex) where cli_hex comes from CLI functions."""
        return self.do_post(
            "/v2/transactions",
            String,
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
        return self.do_get(
            f"/v2/accounts/{principal}",
            AccountInfo,
            params=params,
            address=principal,
            balance=lambda data: self._parse_hex_balance(data.get("balance", "0x0")),
        )

    def get_pox_info(self, *, tip: Optional[str] = None) -> PoxInfo:
        """GET /v2/pox - Get Proof of Transfer (PoX) information."""
        return self.do_get("/v2/pox", PoxInfo, params={"tip": tip} if tip else {})

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
        return self.do_post(
            endpoint,
            ReadOnlyFunctionResult,
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
        return self.do_get(
            f"/v2/contracts/source/{contract_address}/{contract_name}",
            ContractSource,
            params=params,
        )

    def get_contract_interface(
        self, contract_address: str, contract_name: str, *, tip: Optional[str] = None
    ) -> ContractInterface:
        """GET /v2/contracts/interface/{...} - Get contract interface."""
        return self.do_get(
            f"/v2/contracts/interface/{contract_address}/{contract_name}",
            ContractInterface,
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

        return self.do_post(
            endpoint,
            MapEntry,
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
        return self.do_get(
            endpoint, TraitImplementationResponse, params={"tip": tip} if tip else {}
        )

    # --- V2 Fees ---
    def get_fee_rate_for_transfer(self) -> Integer:
        """GET /v2/fees/transfer - Get estimated fee rate for STX transfers."""
        return self.do_get("/v2/fees/transfer", Integer)

    # --- V3 Blocks, Tenures, and Transactions ---
    def get_block_by_id(self, block_id: str) -> Bytes:
        """GET /v3/blocks/{block_id} - Fetch a Nakamoto block by its ID hash. Expects block_id hash string. Returns raw block bytes."""
        return self.do_get(f"/v3/blocks/{block_id}", Bytes)

    def get_block_by_height(
        self, block_height: int, *, tip: Optional[str] = None
    ) -> Bytes:
        """GET /v3/blocks/height/{block_height} - Fetch a Nakamoto block by height. Expects block_height int. Returns raw block bytes."""
        params = {"tip": tip} if tip else {}
        return self.do_get(f"/v3/blocks/height/{block_height}", Bytes, params=params)

    def get_transaction_by_id(
        self, txid: str, is_retry_context: bool = False
    ) -> TransactionDetails:
        """GET /v3/transaction/{txid} - Retrieve transaction details. Expects txid string (e.g. from transfer_result.txid)."""
        return self.do_get(
            f"/v3/transaction/{txid}",
            TransactionDetails,
            is_retry_context=is_retry_context,
            txid=txid,
            tx_status="unknown",
            tx_type="unknown",
        )

    def get_tenure_info(self) -> Optional[TenureInfo]:
        """GET /v3/tenures/info - Fetch metadata about the ongoing Nakamoto tenure."""
        return self.do_get("/v3/tenures/info", TenureInfo)

    def get_tenure_blocks(self, block_id: str, *, stop: Optional[str] = None) -> Bytes:
        """
        GET /v3/tenures/{block_id} - Fetch a sequence of Nakamoto blocks in a tenure.
        Expects block_id as hex string. Returns raw bytes containing sequence of blocks in the tenure.
        """
        params = {"stop": stop} if stop else {}
        return self.do_get(f"/v3/tenures/{block_id}", Bytes, params=params)

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
        sortition_list = self.do_get(endpoint, SortitionList)

        # Parse each item into SortitionInfo
        return [SortitionInfo.model_validate(item) for item in sortition_list.value]

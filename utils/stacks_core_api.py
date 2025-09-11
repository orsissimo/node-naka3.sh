#!/usr/bin/env python3

import requests
import json
from typing import List, Optional, Dict, Any, TypeVar, Type
from pydantic import BaseModel, ValidationError
from .logger import logger, Colors
from .types.config import AccountInfo
from .types.exceptions import *
from .types.stacks_core_api import (
    NodeInfo,
    PoxInfo,
    TransactionDetails,
    StackerSet,
    TenureInfo,
    ContractSource,
    ContractInterface,
    ReadOnlyFunctionResult,
    FeeEstimate,
)

T = TypeVar("T", bound=BaseModel)



class StacksCoreAPI:
    """1:1 Python port of Stacks 3.0+ RPC API with automatic JSON parsing."""

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
        """Validate and normalize the base URL"""
        if not url:
            raise ValueError("Base URL cannot be empty")

        url = url.rstrip("/")

        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Base URL must start with http:// or https://")

        return url

    def _validate_timeout(self, timeout: int) -> int:
        """Validate timeout value"""
        if timeout <= 0:
            raise ValueError("Timeout must be a positive integer")
        return timeout

    @property
    def base_url(self) -> str:
        """Get the base URL (read-only)"""
        return self._base_url

    @property
    def timeout(self) -> int:
        """Get the request timeout"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        """Set the request timeout with validation"""
        self._timeout = self._validate_timeout(value)

    def _parse_json_response(self, data: Dict[str, Any], response_type: Type[T]) -> T:
        """Automatic JSON→typed object parsing with exception handling."""
        if not data:
            raise StacksValidationException(
                f"Empty or None data for {response_type.__name__}"
            )

        try:
            logger.debug(f"Parsing JSON data for {response_type.__name__}: {data}")

            parsed_object = response_type.parse_obj(data)
            logger.debug(f"Successfully created {response_type.__name__} object")
            return parsed_object

        except ValidationError as e:
            logger.error(f"Pydantic validation error for {response_type.__name__}: {e}")
            logger.error(f"JSON data: {data}")
            raise StacksValidationException(
                f"Validation failed for {response_type.__name__}: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error parsing {response_type.__name__}: {e}")
            raise StacksAPIException(
                f"Unexpected error parsing {response_type.__name__}: {e}"
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
                return self._parse_json_response(data, response_type)
            return data
        elif "application/octet-stream" in content_type:
            return response.content
        else:
            return response.text.strip('"')

    def _parse_hex_balance(self, balance_hex: str) -> int:
        """Convert hex balance string to integer."""
        if balance_hex.startswith("0x"):
            return int(balance_hex, 16)
        return int(balance_hex)

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
        Facade pattern for unified request handling.
        Combines _send_request + _handle_api_response in a single call.
        Eliminates code duplication across all API methods.
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
        Typed GET request facade.
        Returns typed object with automatic JSON parsing and exception handling.
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
        response_type: Optional[Type[T]] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> Any:
        """
        Typed POST request facade.
        Returns typed object with automatic JSON parsing and exception handling.
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
    def get_info(self) -> "NodeInfo":
        """GET /v2/info - Get Core API information as typed object."""
        return self.do_get("/v2/info", NodeInfo)

    def post_raw_transaction(self, raw_tx_bytes: bytes) -> str:
        """POST /v2/transactions - Broadcast a raw transaction."""
        return self.do_post(
            "/v2/transactions",
            data=raw_tx_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )

    def get_account_info(
        self, principal: str, *, proof: Optional[int] = None, tip: Optional[str] = None
    ) -> AccountInfo:
        """GET /v2/accounts/{principal} - Get account information as typed object."""
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

    def get_pox_info(self, *, tip: Optional[str] = None) -> "PoxInfo":
        """GET /v2/pox - Get Proof of Transfer (PoX) information as typed object."""
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
    ) -> "ReadOnlyFunctionResult":
        """POST /v2/contracts/call-read/{...} - Call a read-only function."""
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
    ) -> "ContractSource":
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
    ) -> "ContractInterface":
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
    ) -> Optional[Dict[str, Any]]:
        """POST /v2/map_entry/{...} - Get a data-map entry.

        Returns raw dict - varies by map structure.
        """
        endpoint = f"/v2/map_entry/{contract_address}/{contract_name}/{map_name}"
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        return self.do_post(endpoint, data=key_hex_json_string, params=params)

    def get_constant_value(
        self,
        contract_address: str,
        contract_name: str,
        constant_name: str,
        *,
        tip: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """POST /v2/constant_val/{...} - Get the value of a constant.

        Returns raw dict - varies by constant type.
        """
        endpoint = (
            f"/v2/constant_val/{contract_address}/{contract_name}/{constant_name}"
        )
        return self.do_post(endpoint, params={"tip": tip} if tip else {})

    def get_is_trait_implemented(
        self,
        contract_address: str,
        contract_name: str,
        trait_contract_address: str,
        trait_contract_name: str,
        trait_name: str,
        *,
        tip: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """GET /v2/traits/{...} - Check if a contract implements a trait.

        Returns raw dict.
        """
        endpoint = (
            f"/v2/traits/{contract_address}/{contract_name}/"
            f"{trait_contract_address}/{trait_contract_name}/{trait_name}"
        )
        return self.do_get(endpoint, params={"tip": tip} if tip else {})  # type: ignore

    def get_clarity_marf_value(
        self, marf_key: str, *, proof: Optional[int] = None, tip: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """POST /v2/clarity/marf/{...} - Get the MARF value for a key (returns raw dict)."""
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        return self.do_post(f"/v2/clarity/marf/{marf_key}", params=params)

    def get_clarity_metadata(
        self,
        contract_address: str,
        contract_name: str,
        metadata_key: str,
        *,
        tip: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """POST /v2/clarity/metadata/{...} - Get contract metadata (returns raw dict)."""
        endpoint = (
            f"/v2/clarity/metadata/{contract_address}/{contract_name}/{metadata_key}"
        )
        return self.do_post(endpoint, params={"tip": tip} if tip else {})

    # --- V2 Fees ---
    def get_fee_rate_for_transfer(self) -> "FeeEstimate":
        """GET /v2/fees/transfer - Get estimated fee rate for STX transfers."""
        return self.do_get("/v2/fees/transfer", FeeEstimate)

    def get_fee_estimate_for_transaction(
        self, transaction_payload_hex: str, *, estimated_len: Optional[int] = None
    ) -> "FeeEstimate":
        """POST /v2/fees/transaction - Get an estimated fee for a given transaction payload."""
        payload = {"transaction_payload": transaction_payload_hex}
        if estimated_len is not None:
            payload["estimated_len"] = estimated_len  # type: ignore
        return self.do_post("/v2/fees/transaction", FeeEstimate, json_data=payload)

    # --- V3 Blocks, Tenures, and Transactions ---
    def get_block_by_id(self, block_id: str) -> bytes:
        """GET /v3/blocks/{block_id} - Fetch a Nakamoto block by its ID hash."""
        return self.do_get(f"/v3/blocks/{block_id}")  # type: ignore

    def get_block_by_height(
        self, block_height: int, *, tip: Optional[str] = None
    ) -> bytes:
        """GET /v3/blocks/height/{block_height} - Fetch a Nakamoto block by height."""
        return self.do_get(
            f"/v3/blocks/height/{block_height}",
            params={"tip": tip} if tip else {},
        )  # type: ignore

    def get_transaction_by_id(
        self, txid: str, is_retry_context: bool = False
    ) -> "TransactionDetails":
        """GET /v3/transaction/{txid} - Retrieve transaction details as typed object.
        NOTE: The OpenAPI spec incorrectly lists this as a POST endpoint. Real-world
        testing shows it is a GET endpoint. This implementation uses GET.
        """
        return self.do_get(
            f"/v3/transaction/{txid}",
            TransactionDetails,
            is_retry_context=is_retry_context,
            txid=txid,
            tx_status="unknown",
            tx_type="unknown",
        )

    def get_tenure_info(self) -> Optional["TenureInfo"]:
        """GET /v3/tenures/info - Fetch metadata about the ongoing Nakamoto tenure."""
        return self.do_get("/v3/tenures/info", TenureInfo)

    def get_tenure_blocks(self, block_id: str, *, stop: Optional[str] = None) -> bytes:
        """GET /v3/tenures/{block_id} - Fetch a sequence of Nakamoto blocks in a tenure."""
        return self.do_get(
            f"/v3/tenures/{block_id}", params={"stop": stop} if stop else {}
        )  # type: ignore

    def get_sortitions(
        self, *, lookup_kind: Optional[str] = None, lookup: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """GET /v3/sortitions/{lookup_kind}/{lookup} - Fetch burnchain block info.

        Returns raw dict.
        """
        endpoint = "/v3/sortitions"
        if lookup_kind and lookup:
            endpoint += f"/{lookup_kind}/{lookup}"
        elif lookup_kind:
            endpoint += f"/{lookup_kind}"
        return self.do_get(endpoint)  # type: ignore

    # --- V3 Mining and Stacking ---
    def post_block_proposal(
        self, block_proposal_data: Dict
    ) -> Optional[Dict[str, Any]]:
        """POST /v3/block_proposal - Validate a proposed Stacks block.

        Requires auth. Returns raw dict.
        """
        return self.do_post("/v3/block_proposal", json_data=block_proposal_data)

    def get_stacker_set(self, cycle_number: int) -> "StackerSet":
        """GET /v3/stacker_set/{cycle_number} - Fetch stacker set info for a cycle."""
        return self.do_get(
            f"/v3/stacker_set/{cycle_number}", StackerSet, cycle_number=cycle_number
        )

    def get_signer_block_count(self, signer_pubkey: str, cycle_number: int) -> int:
        """GET /v3/signer/{signer}/{cycle_number} - Get signer block count in cycle."""
        resp = self.do_get(f"/v3/signer/{signer_pubkey}/{cycle_number}")  # type: ignore
        if not resp or not isinstance(resp, str) or not resp.isdigit():
            raise StacksAPIException(f"Invalid signer block count response: {resp}")
        return int(resp)

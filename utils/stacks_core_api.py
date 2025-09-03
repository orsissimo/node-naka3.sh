#!/usr/bin/env python3

import requests
import json
from typing import List, Optional, Dict, Any, Union, TypeVar, Type
from pydantic import BaseModel, Field, ValidationError
from .logger import logger
from .config import (
    AccountInfo,
    TxStatus,
    ApiResult,
    ApiError,
    MICROSTX_PER_STX,
    StacksAPIException,
    StacksValidationException,
    StacksNetworkException,
    StacksTimeoutException,
)

T = TypeVar("T", bound=BaseModel)


class NodeInfo(BaseModel):
    """Typed node information from /v2/info endpoint."""

    peer_version: int
    pox_consensus: str
    burn_block_height: int
    stable_pox_consensus: str
    stable_burn_block_height: int
    server_version: str
    network_id: int
    parent_network_id: int
    stacks_tip_height: int
    stacks_tip: str
    stacks_tip_consensus_hash: str
    genesis_chainstate_hash: str
    unanchored_tip: Optional[str] = None
    unanchored_seq: Optional[int] = None
    tenure_height: int
    exit_at_block_height: Optional[int] = None
    is_fully_synced: bool
    node_public_key: Optional[str] = None
    node_public_key_hash: Optional[str] = None
    affirmations: Optional[Dict] = None
    last_pox_anchor: Optional[Dict] = None
    stackerdbs: Optional[List] = None

    class Config:
        populate_by_name = True


class PoxCycle(BaseModel):
    """PoX cycle information."""

    id: int
    min_threshold_ustx: int
    stacked_ustx: int
    is_pox_active: bool

    class Config:
        populate_by_name = True


class PoxInfo(BaseModel):
    """Typed PoX information from /v2/pox endpoint."""

    contract_id: str
    pox_activation_threshold_ustx: int
    first_burnchain_block_height: int
    current_burnchain_block_height: int
    prepare_phase_block_length: int
    reward_phase_block_length: int
    reward_slots: int
    rejection_fraction: Optional[int] = None
    total_liquid_supply_ustx: int
    current_cycle: PoxCycle
    next_cycle: PoxCycle
    epochs: List[Dict]  # Can be further typed if needed
    min_amount_ustx: int
    prepare_cycle_length: int
    reward_cycle_id: int
    reward_cycle_length: int
    rejection_votes_left_required: Optional[int] = None
    next_reward_cycle_in: int
    contract_versions: List[Dict]  # Can be further typed if needed

    class Config:
        populate_by_name = True


class TransactionDetails(BaseModel):
    """Transaction details from /v3/transaction endpoint."""

    index_block_hash: Optional[str] = None
    tx: Optional[str] = None  # Raw transaction hex
    result: Optional[str] = None  # Contract call result like '(ok true)'
    txid: Optional[str] = None  # Added manually by our code
    tx_status: Optional[str] = None  # Added manually by our code  
    tx_type: Optional[str] = None  # Added manually by our code
    receipt_time: Optional[int] = None
    receipt_time_iso: Optional[str] = None

    class Config:
        populate_by_name = True

    @property
    def status(self) -> TxStatus:
        """Get transaction status as typed enum with IDE autocompletion."""
        if self.tx_status == "success":
            return TxStatus.SUCCESS
        elif self.tx_status == "abort_by_response":
            return TxStatus.ABORT_BY_RESPONSE
        elif self.tx_status == "abort_by_post_condition":
            return TxStatus.ABORT_BY_POST_CONDITION
        elif self.tx_status == "pending":
            return TxStatus.PENDING
        else:
            return TxStatus.UNKNOWN

    # Additional fields can be added as needed


class StackerSet(BaseModel):
    """Stacker set information from /v3/stacker_set endpoint."""

    cycle_number: int
    # Additional fields based on actual response structure

    class Config:
        populate_by_name = True


class TenureInfo(BaseModel):
    """Tenure information from /v3/tenures/info endpoint."""

    consensus_hash: str
    tenure_start_block_id: str
    # Additional fields based on actual response structure

    class Config:
        populate_by_name = True


class ContractSource(BaseModel):
    """Contract source response from /v2/contracts/source endpoint."""

    source: str
    publish_height: int
    proof: Optional[str] = None

    class Config:
        populate_by_name = True


class ContractInterface(BaseModel):
    """Contract interface response from /v2/contracts/interface endpoint."""

    functions: List[Dict]
    variables: List[Dict]
    maps: List[Dict]
    fungible_tokens: List[Dict] = Field(default_factory=list)
    non_fungible_tokens: List[Dict] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class ReadOnlyFunctionResult(BaseModel):
    """Read-only function call result from /v2/contracts/call-read endpoint."""

    okay: bool
    result: str
    cause: Optional[str] = None

    class Config:
        populate_by_name = True


class FeeEstimate(BaseModel):
    """Fee estimate response from /v2/fees endpoints."""

    estimated_cost_scalar: int
    estimated_cost: int
    estimations: List[Dict]

    class Config:
        populate_by_name = True


class StacksCoreAPI:
    """
    A 1:1 Python port of the Stacks 3.0+ RPC API, covering all endpoints from
    the provided OpenAPI specification with automatic JSON→object parsing and
    centralized error handling. This class provides direct access to all API
    endpoints without additional abstraction layers.
    """

    def __init__(
        self, base_url: str = "http://localhost:20443", auth_token: Optional[str] = None, timeout: int = 20
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
        
        # Ensure URL doesn't end with slash for consistent endpoint building
        url = url.rstrip('/')
        
        # Basic URL format validation
        if not (url.startswith('http://') or url.startswith('https://')):
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
        """
        Bulletproof automatic JSON→typed object parsing for Stacks Core API.
        Raises exceptions instead of returning None for better error handling.
        """
        if not data:
            raise StacksValidationException(
                f"Empty or None data for {response_type.__name__}"
            )

        try:
            logger.debug(f"Parsing JSON data for {response_type.__name__}: {data}")

            # Automatic validation and object creation via Pydantic
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

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make raw API request and return response object for centralized handling"""
        url = f"{self._base_url}{endpoint}"
        logger.debug(f"-> {method} {url}")

        try:
            response = self._session.request(
                method, url, **kwargs, timeout=self._timeout
            )
            # Add visual indicator based on status code with colors
            if 200 <= response.status_code < 300:
                from .logger import Colors

                indicator = f"{Colors.GREEN}✓{Colors.RESET}"
            elif 400 <= response.status_code < 500:
                from .logger import Colors

                indicator = f"{Colors.RED}✗{Colors.RESET}"
            elif 500 <= response.status_code < 600:
                from .logger import Colors

                indicator = f"{Colors.RED}✗{Colors.RESET}"
            else:
                from .logger import Colors

                indicator = f"{Colors.YELLOW}?{Colors.RESET}"

            from .logger import Colors

            logger.debug(f"<- Status: {response.status_code} {indicator}")
            return response
        except requests.exceptions.Timeout as e:
            logger.critical(f"Request timeout occurred: {str(e)}")
            raise StacksTimeoutException(f"Request timeout for {method} {url}") from e
        except requests.exceptions.ConnectionError as e:
            logger.critical(f"Connection error occurred: {str(e)}")
            raise StacksNetworkException(f"Connection error for {method} {url}") from e
        # FIXME: Potrei fare except StacksHTTPException, che ha error_code: XYZ + error_message
        # FIXME: Dove ora cerco "404" nella stringa, poi controllo StacksHTTPException.error_code
        except requests.exceptions.RequestException as e:
            logger.critical(f"An HTTP request error occurred: {str(e)}")
            raise StacksNetworkException(
                f"Request failed for {method} {url}: {str(e)}"
            ) from e

    def _handle_api_response(self, response: requests.Response, response_type: Optional[Type[T]] = None, **parse_kwargs) -> Any:
        """
        Centralized handler for all API responses.
        On success (200), intelligently parses and returns the body content.
        On failure, raises appropriate StacksAPIException with details.
        """
        if response.status_code != 200:
            try:
                error_details = response.json()
                reason = error_details.get("reason", "Unknown API error")
                reason_data = error_details.get("reason_data", {})
                error_message = f"API Error ({response.status_code}): {reason} - Details: {reason_data}"
            except json.JSONDecodeError:
                error_message = f"API Error ({response.status_code}): {response.text}"

            logger.error(f"API call failed: {error_message}")
            raise StacksAPIException(
                error_message,
                status_code=response.status_code,
                error_details=error_details if "error_details" in locals() else {},
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

    # --- V2 Transactions, Accounts, and Info ---
    def get_info(self) -> "NodeInfo":
        """GET /v2/info - Get Core API information as typed object."""
        response = self._make_request("GET", "/v2/info")
        return self._handle_api_response(response, NodeInfo)

    def post_raw_transaction(self, raw_tx_bytes: bytes) -> str:
        """POST /v2/transactions - Broadcast a raw transaction."""
        response = self._make_request(
            "POST",
            "/v2/transactions",
            data=raw_tx_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        return self._handle_api_response(response)

    def get_account_info(
        self, principal: str, *, proof: Optional[int] = None, tip: Optional[str] = None
    ) -> AccountInfo:
        """GET /v2/accounts/{principal} - Get account information as typed object."""
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        response = self._make_request("GET", f"/v2/accounts/{principal}", params=params)
        return self._handle_api_response(response, AccountInfo,
                                       address=principal,
                                       balance=lambda data: self._parse_hex_balance(data.get("balance", "0x0")))

    def get_pox_info(self, *, tip: Optional[str] = None) -> "PoxInfo":
        """GET /v2/pox - Get Proof of Transfer (PoX) information as typed object."""
        response = self._make_request(
            "GET", "/v2/pox", params={"tip": tip} if tip else {}
        )
        return self._handle_api_response(response, PoxInfo)

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
        response = self._make_request(
            "POST",
            endpoint,
            json={"sender": sender, "arguments": arguments},
            params={"tip": tip} if tip else {},
        )
        return self._handle_api_response(response, ReadOnlyFunctionResult)

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
        response = self._make_request(
            "GET",
            f"/v2/contracts/source/{contract_address}/{contract_name}",
            params=params,
        )
        return self._handle_api_response(response, ContractSource)

    def get_contract_interface(
        self, contract_address: str, contract_name: str, *, tip: Optional[str] = None
    ) -> "ContractInterface":
        """GET /v2/contracts/interface/{...} - Get contract interface."""
        response = self._make_request(
            "GET",
            f"/v2/contracts/interface/{contract_address}/{contract_name}",
            params={"tip": tip} if tip else {},
        )
        return self._handle_api_response(response, ContractInterface)

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
        """POST /v2/map_entry/{...} - Get a data-map entry (returns raw dict - varies by map structure)."""
        endpoint = f"/v2/map_entry/{contract_address}/{contract_name}/{map_name}"
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        response = self._make_request(
            "POST", endpoint, json=key_hex_json_string, params=params
        )
        return self._handle_api_response(response)

    def get_constant_value(
        self,
        contract_address: str,
        contract_name: str,
        constant_name: str,
        *,
        tip: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """POST /v2/constant_val/{...} - Get the value of a constant (returns raw dict - varies by constant type)."""
        endpoint = (
            f"/v2/constant_val/{contract_address}/{contract_name}/{constant_name}"
        )
        response = self._make_request(
            "POST", endpoint, params={"tip": tip} if tip else {}
        )
        return self._handle_api_response(response)

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
        """GET /v2/traits/{...} - Check if a contract implements a trait (returns raw dict)."""
        endpoint = f"/v2/traits/{contract_address}/{contract_name}/{trait_contract_address}/{trait_contract_name}/{trait_name}"
        response = self._make_request(
            "GET", endpoint, params={"tip": tip} if tip else {}
        )
        return self._handle_api_response(response)

    def get_clarity_marf_value(
        self, marf_key: str, *, proof: Optional[int] = None, tip: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """POST /v2/clarity/marf/{...} - Get the MARF value for a key (returns raw dict)."""
        params = {
            k: v for k, v in {"proof": proof, "tip": tip}.items() if v is not None
        }
        response = self._make_request(
            "POST", f"/v2/clarity/marf/{marf_key}", params=params
        )
        return self._handle_api_response(response)

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
        response = self._make_request(
            "POST", endpoint, params={"tip": tip} if tip else {}
        )
        return self._handle_api_response(response)

    # --- V2 Fees ---
    def get_fee_rate_for_transfer(self) -> "FeeEstimate":
        """GET /v2/fees/transfer - Get estimated fee rate for STX transfers."""
        response = self._make_request("GET", "/v2/fees/transfer")
        return self._handle_api_response(response, FeeEstimate)

    def get_fee_estimate_for_transaction(
        self, transaction_payload_hex: str, *, estimated_len: Optional[int] = None
    ) -> "FeeEstimate":
        """POST /v2/fees/transaction - Get an estimated fee for a given transaction payload."""
        payload = {"transaction_payload": transaction_payload_hex}
        if estimated_len is not None:
            payload["estimated_len"] = estimated_len
        response = self._make_request("POST", "/v2/fees/transaction", json=payload)
        return self._handle_api_response(response, FeeEstimate)

    # --- V3 Blocks, Tenures, and Transactions ---
    def get_block_by_id(self, block_id: str) -> bytes:
        """GET /v3/blocks/{block_id} - Fetch a Nakamoto block by its ID hash."""
        response = self._make_request("GET", f"/v3/blocks/{block_id}")
        return self._handle_api_response(response)

    def get_block_by_height(
        self, block_height: int, *, tip: Optional[str] = None
    ) -> bytes:
        """GET /v3/blocks/height/{block_height} - Fetch a Nakamoto block by height."""
        response = self._make_request(
            "GET",
            f"/v3/blocks/height/{block_height}",
            params={"tip": tip} if tip else {},
        )
        return self._handle_api_response(response)

    def get_transaction_by_id(self, txid: str) -> "TransactionDetails":
        """GET /v3/transaction/{txid} - Retrieve transaction details as typed object.
        NOTE: The OpenAPI spec incorrectly lists this as a POST endpoint. Real-world
        testing shows it is a GET endpoint. This implementation uses GET.
        """
        response = self._make_request("GET", f"/v3/transaction/{txid}")
        return self._handle_api_response(response, TransactionDetails, 
                                       txid=txid, tx_status="unknown", tx_type="unknown")

    def get_tenure_info(self) -> Optional["TenureInfo"]:
        """GET /v3/tenures/info - Fetch metadata about the ongoing Nakamoto tenure."""
        response = self._make_request("GET", "/v3/tenures/info")
        return self._handle_api_response(response, TenureInfo)

    def get_tenure_blocks(self, block_id: str, *, stop: Optional[str] = None) -> bytes:
        """GET /v3/tenures/{block_id} - Fetch a sequence of Nakamoto blocks in a tenure."""
        response = self._make_request(
            "GET", f"/v3/tenures/{block_id}", params={"stop": stop} if stop else {}
        )
        return self._handle_api_response(response)

    def get_sortitions(
        self, *, lookup_kind: Optional[str] = None, lookup: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """GET /v3/sortitions/{lookup_kind}/{lookup} - Fetch information about evaluated burnchain blocks (returns raw dict)."""
        endpoint = "/v3/sortitions"
        if lookup_kind and lookup:
            endpoint += f"/{lookup_kind}/{lookup}"
        elif lookup_kind:
            endpoint += f"/{lookup_kind}"
        response = self._make_request("GET", endpoint)
        return self._handle_api_response(response)

    # --- V3 Mining and Stacking ---
    def post_block_proposal(
        self, block_proposal_data: Dict
    ) -> Optional[Dict[str, Any]]:
        """POST /v3/block_proposal - Validate a proposed Stacks block. Requires auth (returns raw dict)."""
        response = self._make_request(
            "POST", "/v3/block_proposal", json=block_proposal_data
        )
        return self._handle_api_response(response)

    def get_stacker_set(self, cycle_number: int) -> "StackerSet":
        """GET /v3/stacker_set/{cycle_number} - Fetch stacker set info for a cycle."""
        response = self._make_request("GET", f"/v3/stacker_set/{cycle_number}")
        return self._handle_api_response(response, StackerSet, cycle_number=cycle_number)

    def get_signer_block_count(self, signer_pubkey: str, cycle_number: int) -> int:
        """GET /v3/signer/{signer}/{cycle_number} - Get number of blocks signed by a signer in a cycle."""
        response = self._make_request(
            "GET", f"/v3/signer/{signer_pubkey}/{cycle_number}"
        )
        resp = self._handle_api_response(response)
        if not resp or not isinstance(resp, str) or not resp.isdigit():
            raise StacksAPIException(f"Invalid signer block count response: {resp}")
        return int(resp)

    def wait_for_tx_confirmation(
        self,
        txid: str,
        account_address: str,
        initial_nonce: int,
        initial_height: int,
        timeout: int = 60,
    ) -> bool:
        """Wait for transaction confirmation using smart block-based polling with detailed API response parsing"""
        import time

        start_time = time.time()
        last_checked_height = initial_height
        consecutive_failures = 0
        max_consecutive_failures = 5

        while time.time() - start_time < timeout:
            try:
                # Get current node info using existing method (eliminates repetition)
                node_info = self.get_info()
                current_height = node_info.stacks_tip_height

                # Only check transaction when block height increases (more efficient)
                if current_height > last_checked_height:
                    try:
                        # Check transaction result using existing method (eliminates repetition)
                        tx_details = self.get_transaction_by_id(txid)
                        
                        # Check if transaction has result field with '(ok true)'
                        if tx_details.result == '(ok true)':
                            logger.debug(f"Transaction {txid} successful with result: '(ok true)'")
                            return True
                        else:
                            logger.debug(f"Transaction {txid} completed with result: {tx_details.result}")
                            return False  # Transaction completed but not successful

                    except StacksAPIException as e:
                        # Transaction not found yet
                        if "404" in str(e):
                            logger.debug(f"Transaction {txid} not found yet in block {current_height}")
                        else:
                            raise  # Re-raise non-404 errors

                    last_checked_height = current_height
                    # Short sleep after block change
                    time.sleep(1)
                else:
                    # Longer sleep when no new blocks (more efficient)
                    time.sleep(3)

                # Reset failure counter on success
                consecutive_failures = 0

            except (StacksNetworkException, StacksTimeoutException) as e:
                consecutive_failures += 1
                logger.warning(
                    f"Network error during confirmation wait ({consecutive_failures}/{max_consecutive_failures}): {e}"
                )

                if consecutive_failures >= max_consecutive_failures:
                    raise StacksNetworkException(
                        f"Too many consecutive network failures during confirmation wait: {e}"
                    ) from e

                time.sleep(2)
            except StacksAPIException as e:
                consecutive_failures += 1
                logger.warning(
                    f"API error during confirmation wait ({consecutive_failures}/{max_consecutive_failures}): {e}"
                )

                if consecutive_failures >= max_consecutive_failures:
                    raise StacksAPIException(
                        f"Too many consecutive API failures during confirmation wait: {e}"
                    ) from e

                time.sleep(2)

        raise StacksTimeoutException(
            f"Transaction confirmation timeout after {timeout}s for account {account_address}"
        )


class StacksCoreAPIWrapper:
    """
    High-level wrapper around StacksCoreAPI providing convenient methods,
    error handling, and abstraction for common operations. This safe layer
    protects against API changes and provides graceful degradation.
    """

    def __init__(self, api: Optional["StacksCoreAPI"] = None):
        self.api = api or StacksCoreAPI()

    def _safe_execute(self, operation_name: str, operation_func) -> ApiResult:
        """
        Safe execution wrapper that handles all possible failure modes:
        - API request failures
        - JSON parsing errors
        - Validation errors
        - Future API changes
        - Network/connection issues
        """
        try:
            result = operation_func()
            if result is not None:
                return ApiResult(success=True, data=result)
            else:
                return ApiResult(
                    success=False,
                    error=ApiError.UNKNOWN_ERROR,
                    error_message=f"{operation_name} returned None - possible API format change or request failure",
                )
        except ValidationError as e:
            logger.warning(f"API format may have changed for {operation_name}: {e}")
            return ApiResult(
                success=False,
                error=ApiError.UNKNOWN_ERROR,
                error_message=f"API format validation failed for {operation_name}. This may indicate an API version change.",
            )
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return ApiResult(
                    success=False, error=ApiError.NOT_FOUND, error_message=error_msg
                )
            elif "timeout" in error_msg.lower():
                return ApiResult(
                    success=False, error=ApiError.TIMEOUT, error_message=error_msg
                )
            elif "connection" in error_msg.lower():
                return ApiResult(
                    success=False,
                    error=ApiError.CONNECTION_ERROR,
                    error_message=error_msg,
                )
            else:
                return ApiResult(
                    success=False, error=ApiError.UNKNOWN_ERROR, error_message=error_msg
                )

    def get_block_height(self) -> int:
        """Get current block height from the Stacks API - raises exceptions instead of returning None."""
        result = self._safe_execute("get_block_height", lambda: self.api.get_info())
        if result.success and result.data:
            return result.data.stacks_tip_height

        # Don't swallow the exception - propagate it properly
        if result.error == ApiError.NOT_FOUND:
            raise StacksAPIException("Node info not found")
        elif result.error == ApiError.TIMEOUT:
            raise StacksTimeoutException(result.error_message or "API timeout")
        elif result.error == ApiError.CONNECTION_ERROR:
            raise StacksNetworkException(result.error_message or "Connection error")
        else:
            raise StacksAPIException(result.error_message or "Unknown API error")

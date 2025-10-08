#!/usr/bin/env python3

import requests
import json
from typing import List, Optional, Dict, Any, TypeVar, Type, Union
from utils.logger import logger, Colors
from utils.parsers import parse_api_response
from utils.types.wrappers import String
from utils.types.hiro.api import *
from utils.types.hiro.exceptions import *

T = TypeVar("T")


class HiroAPI:
    def __init__(
        self,
        base_url: str = "https://api.mainnet.hiro.so",
        timeout: int = 30,
    ):
        self._base_url = self._validate_url(base_url)
        self._session = requests.Session()
        self._timeout = self._validate_timeout(timeout)

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
            raise HiroTimeoutException(f"Request timeout for {method} {url}") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error occurred: {str(e)}")
            raise HiroNetworkException(f"Connection error for {method} {url}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"An HTTP request error occurred: {str(e)}")
            raise HiroNetworkException(
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
        On failure, raises appropriate HiroAPIException with details.
        """
        if response.status_code != 200:
            error_details = {}
            try:
                error_details = response.json()
                reason = error_details.get(
                    "error", error_details.get("message", "Unknown API error")
                )
                error_message = f"API Error ({response.status_code}): {reason}"
            except json.JSONDecodeError:
                error_message = f"API Error ({response.status_code}): {response.text}"

            if is_retry_context and response.status_code == 404:
                logger.warning(
                    f"API call temporarily failed (will retry): {error_message}"
                )
            else:
                logger.error(f"API call failed: {error_message}")

            raise HiroHTTPException(
                error_message,
                status_code=response.status_code,
                error_details=error_details,
            )

        # Handle successful responses
        content_type = response.headers.get("Content-Type", "")

        # Handle special wrapper types that don't come from JSON
        if response_type is not None:
            if response_type is String:
                return String(response.text.strip('"'))

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
        else:
            return response.text

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

    # --- Extended API Status ---
    def get_status(self) -> ApiStatus:
        """GET /extended - Get API status information."""
        return self.do_get("/extended", ApiStatus)

    # --- Transaction Endpoints ---
    def get_transaction_list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        type_filter: Optional[List[str]] = None,
        unanchored: Optional[bool] = None,
    ) -> TransactionList:
        """GET /extended/v1/tx/ - Get recent transactions."""
        params = {}
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        if type_filter is not None:
            params["type"] = type_filter
        if unanchored is not None:
            params["unanchored"] = str(unanchored).lower()

        return self.do_get("/extended/v1/tx/", TransactionList, params=params)

    def get_tx_list_details(
        self,
        tx_ids: List[str],
        *,
        event_offset: Optional[int] = None,
        event_limit: Optional[int] = None,
        unanchored: Optional[bool] = None,
    ) -> TransactionMultipleResponse:
        """GET /extended/v1/tx/multiple - Get list of details for transactions."""
        params: Dict[str, Union[str, List[str]]] = {"tx_id": tx_ids}
        if event_offset is not None:
            params["event_offset"] = str(event_offset)
        if event_limit is not None:
            params["event_limit"] = str(event_limit)
        if unanchored is not None:
            params["unanchored"] = str(unanchored).lower()

        return self.do_get(
            "/extended/v1/tx/multiple", TransactionMultipleResponse, params=params
        )

    def get_transaction_by_id(
        self,
        tx_id: str,
        *,
        event_offset: Optional[int] = None,
        event_limit: Optional[int] = None,
        unanchored: Optional[bool] = None,
    ) -> Transaction:
        """GET /extended/v1/tx/{tx_id} - Get transaction by ID."""
        params = {}
        if event_offset is not None:
            params["event_offset"] = event_offset
        if event_limit is not None:
            params["event_limit"] = event_limit
        if unanchored is not None:
            params["unanchored"] = unanchored

        return self.do_get(f"/extended/v1/tx/{tx_id}", Transaction, params=params)

    def get_raw_transaction_by_id(self, tx_id: str) -> String:
        """GET /extended/v1/tx/{tx_id}/raw - Get raw transaction by ID."""
        return self.do_get(f"/extended/v1/tx/{tx_id}/raw", String)

    # --- Contract Endpoints ---
    def get_contract_by_id(
        self,
        contract_id: str,
        *,
        unanchored: Optional[bool] = None,
    ) -> ContractInfo:
        """GET /extended/v1/contract/{contract_id} - Get contract info."""
        params = {}
        if unanchored is not None:
            params["unanchored"] = unanchored

        return self.do_get(
            f"/extended/v1/contract/{contract_id}", ContractInfo, params=params
        )

    def get_contract_events_by_id(
        self,
        contract_id: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        unanchored: Optional[bool] = None,
    ) -> EventsList:
        """GET /extended/v1/contract/{contract_id}/events - Get contract events."""

        return self.do_get(f"/extended/v1/contract/{contract_id}/events", EventsList)

    # --- Address/Principal Endpoints ---

    def get_account_assets(
        self,
        principal: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        unanchored: Optional[bool] = None,
        until_block: Optional[str] = None,
    ) -> AddressAssets:
        """GET /extended/v1/address/{principal}/assets - Get account assets."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if unanchored is not None:
            params["unanchored"] = unanchored
        if until_block is not None:
            params["until_block"] = until_block

        return self.do_get(
            f"/extended/v1/address/{principal}/assets", AddressAssets, params=params
        )

    def get_account_inbound(
        self,
        principal: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        height: Optional[int] = None,
        unanchored: Optional[bool] = None,
        until_block: Optional[str] = None,
    ) -> AddressStxInboundList:
        """GET /extended/v1/address/{principal}/stx_inbound - Get inbound STX transfers."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if height is not None:
            params["height"] = height
        if unanchored is not None:
            params["unanchored"] = unanchored
        if until_block is not None:
            params["until_block"] = until_block

        return self.do_get(
            f"/extended/v1/address/{principal}/stx_inbound",
            AddressStxInboundList,
            params=params,
        )

    def get_address_mempool_transactions(
        self,
        principal: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        unanchored: Optional[bool] = None,
    ) -> TransactionList:
        """GET /extended/v1/address/{principal}/mempool - Get mempool transactions for address."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if unanchored is not None:
            params["unanchored"] = unanchored

        return self.do_get(
            f"/extended/v1/address/{principal}/mempool", TransactionList, params=params
        )

    def get_account_nonces(
        self,
        principal: str,
        *,
        unanchored: Optional[bool] = None,
        until_block: Optional[str] = None,
    ) -> AddressNonces:
        """GET /extended/v1/address/{principal}/nonces - Get account nonces."""
        params = {}
        if unanchored is not None:
            params["unanchored"] = unanchored
        if until_block is not None:
            params["until_block"] = until_block

        return self.do_get(
            f"/extended/v1/address/{principal}/nonces", AddressNonces, params=params
        )

    # --- Search Endpoint ---
    def search_by_id(
        self,
        id: str,
        *,
        include_metadata: Optional[bool] = None,
    ) -> SearchResult:
        """GET /extended/v1/search/{id} - Search blocks, transactions, contracts, or accounts by hash/ID."""
        params = {}
        if include_metadata is not None:
            params["include_metadata"] = include_metadata

        return self.do_get(f"/extended/v1/search/{id}", SearchResult, params=params)

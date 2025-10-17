#!/usr/bin/env python3

import requests
from typing import List, Optional, Dict, Any, TypeVar, Type, Union
from utils.api_client import APIClient
from utils.types.wrappers import String
from utils.types.hiro.api import *
from utils.types.hiro.exceptions import *

T = TypeVar("T")

# FIXME: Factory method class: HiroAPI.mainnet(), HiroAPI.testnet()

class HiroAPI:
    def __init__(
        self,
        base_url: str = "https://api.mainnet.hiro.so",
        timeout: int = 30,
    ):
        self._client = APIClient(
            base_url=base_url,
            timeout=timeout,
            timeout_exception=HiroTimeoutException,
            network_exception=HiroNetworkException,
            http_exception=HiroHTTPException,
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

    def _extract_error_message(
        self, response: requests.Response, error_details: Dict[str, Any]
    ) -> str:
        """Extract error message from Hiro API error response."""
        reason = error_details.get(
            "error", error_details.get("message", "Unknown API error")
        )
        return f"API Error ({response.status_code}): {reason}"

    def _handle_custom_types(
        self, response: requests.Response, response_type: Type[T], _content_type: str
    ) -> Optional[T]:
        """Handle Hiro-specific wrapper types."""
        if response_type is String:
            return String(response.text.strip('"'))  # type: ignore
        return None

    # --- Extended API Status ---
    def get_status(self) -> ApiStatus:
        """GET /extended - Get API status information."""
        return self._client.do_get(
            "/extended",
            ApiStatus,
            self._extract_error_message,
            self._handle_custom_types,
        )

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

        return self._client.do_get(
            "/extended/v1/tx/",
            TransactionList,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
        )

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

        return self._client.do_get(
            "/extended/v1/tx/multiple",
            TransactionMultipleResponse,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
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

        return self._client.do_get(
            f"/extended/v1/tx/{tx_id}",
            Transaction,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
        )

    def get_raw_transaction_by_id(self, tx_id: str) -> String:
        """GET /extended/v1/tx/{tx_id}/raw - Get raw transaction by ID."""
        return self._client.do_get(
            f"/extended/v1/tx/{tx_id}/raw",
            String,
            self._extract_error_message,
            self._handle_custom_types,
        )

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

        return self._client.do_get(
            f"/extended/v1/contract/{contract_id}",
            ContractInfo,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
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
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if unanchored is not None:
            params["unanchored"] = unanchored

        return self._client.do_get(
            f"/extended/v1/contract/{contract_id}/events",
            EventsList,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
        )

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

        return self._client.do_get(
            f"/extended/v1/address/{principal}/assets",
            AddressAssets,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
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

        return self._client.do_get(
            f"/extended/v1/address/{principal}/stx_inbound",
            AddressStxInboundList,
            self._extract_error_message,
            self._handle_custom_types,
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

        return self._client.do_get(
            f"/extended/v1/address/{principal}/mempool",
            TransactionList,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
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

        return self._client.do_get(
            f"/extended/v1/address/{principal}/nonces",
            AddressNonces,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
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

        return self._client.do_get(
            f"/extended/v1/search/{id}",
            SearchResult,
            self._extract_error_message,
            self._handle_custom_types,
            params=params,
        )

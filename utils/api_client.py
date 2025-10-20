#!/usr/bin/env python3
"""Utility object that handles common HTTP operations for API clients."""

import requests
import json
from typing import Optional, Dict, Any, TypeVar, Type, Callable
from utils.logger import logger, Colors
from utils.parsers import parse_api_response

T = TypeVar("T")


class APIClient:
    """
    Utility object that handles common HTTP operations for API clients.
    Use this via composition in your API classes.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int,
        timeout_exception: Type[Exception],
        network_exception: Type[Exception],
        http_exception: Type[Exception],
    ):
        """
        Initialize API client utility.

        Args:
            base_url: The base URL for API requests
            timeout: Request timeout in seconds
            timeout_exception: Exception class to raise on timeout
            network_exception: Exception class to raise on network errors
            http_exception: Exception class to raise on HTTP errors
        """
        self._base_url = self._validate_url(base_url)
        self._session = requests.Session()
        self._timeout = self._validate_timeout(timeout)
        self._timeout_exception = timeout_exception
        self._network_exception = network_exception
        self._http_exception = http_exception

    def _validate_url(self, url: str) -> str:
        """Validate and normalize base URL."""
        if not url:
            raise ValueError("Base URL cannot be empty")
        url = url.rstrip("/")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return url

    def _validate_timeout(self, timeout: int) -> int:
        """Validate timeout value."""
        if timeout <= 0:
            raise ValueError("Timeout must be a positive integer")
        return timeout

    @property
    def base_url(self) -> str:
        """Get base URL."""
        return self._base_url

    @property
    def timeout(self) -> int:
        """Get request timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        """Set request timeout with validation."""
        self._timeout = self._validate_timeout(value)

    @property
    def session(self) -> requests.Session:
        """Get the underlying requests session for custom configuration."""
        return self._session

    def send_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make raw API request and return response object for centralized handling."""
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
            raise self._timeout_exception(f"Request timeout for {method} {url}") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error occurred: {str(e)}")
            raise self._network_exception(f"Connection error for {method} {url}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"An HTTP request error occurred: {str(e)}")
            raise self._network_exception(
                f"Request failed for {method} {url}: {str(e)}"
            ) from e

    def handle_api_response(
        self,
        response: requests.Response,
        response_type: Optional[Type[T]],
        error_extractor: Callable[[requests.Response, Dict[str, Any]], str],
        custom_type_handler: Optional[
            Callable[[requests.Response, Type[T], str], Optional[T]]
        ] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> Any:
        """
        Centralized handler for all API responses.

        Args:
            response: The HTTP response object
            response_type: Type to parse the response into
            error_extractor: Function to extract error message from response
            custom_type_handler: Optional function to handle custom wrapper types
            is_retry_context: Whether this is being called in a retry context
            **parse_kwargs: Additional kwargs to pass to the parser

        Returns:
            Parsed response data
        """
        if response.status_code != 200:
            error_details = {}
            try:
                error_details = response.json()
                error_message = error_extractor(response, error_details)
            except json.JSONDecodeError:
                error_message = f"API Error ({response.status_code}): {response.text}"

            if is_retry_context and response.status_code == 404:
                logger.warning(
                    f"API call temporarily failed (will retry): {error_message}"
                )
            else:
                logger.error(f"API call failed: {error_message}")

            raise self._http_exception(
                error_message,
                response.status_code,
                error_details,
            )

        # Handle successful responses
        content_type = response.headers.get("Content-Type", "")

        # Allow custom handling of special wrapper types
        if response_type is not None and custom_type_handler is not None:
            custom_result = custom_type_handler(response, response_type, content_type)
            if custom_result is not None:
                return custom_result

        # Default JSON handling
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
                return parse_api_response(data, response_type)  # type: ignore
            return data
        elif "application/octet-stream" in content_type:
            return response.content
        else:
            return response.text.strip('"')

    def do_request(
        self,
        method: str,
        endpoint: str,
        response_type: Optional[Type[T]],
        error_extractor: Callable[[requests.Response, Dict[str, Any]], str],
        custom_type_handler: Optional[
            Callable[[requests.Response, Type[T], str], Optional[T]]
        ] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> Any:
        """
        Combines send_request + handle_api_response in a single call.
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

        response = self.send_request(method, endpoint, **kwargs)
        return self.handle_api_response(
            response,
            response_type,
            error_extractor,
            custom_type_handler,
            is_retry_context,
            **parse_kwargs,
        )

    def do_get(
        self,
        endpoint: str,
        response_type: Type[T],
        error_extractor: Callable[[requests.Response, Dict[str, Any]], str],
        custom_type_handler: Optional[
            Callable[[requests.Response, Type[T], str], Optional[T]]
        ] = None,
        params: Optional[Dict] = None,
        is_retry_context: bool = False,
        **parse_kwargs,
    ) -> T:
        """
        Typed GET request.
        Returns typed object with automatic JSON parsing and exception handling.
        """
        return self.do_request(
            "GET",
            endpoint,
            response_type,
            error_extractor,
            custom_type_handler,
            params=params,
            is_retry_context=is_retry_context,
            **parse_kwargs,
        )

    def do_post(
        self,
        endpoint: str,
        response_type: Type[T],
        error_extractor: Callable[[requests.Response, Dict[str, Any]], str],
        custom_type_handler: Optional[
            Callable[[requests.Response, Type[T], str], Optional[T]]
        ] = None,
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
        """
        return self.do_request(
            "POST",
            endpoint,
            response_type,
            error_extractor,
            custom_type_handler,
            params=params,
            json_data=json_data,
            data=data,
            headers=headers,
            is_retry_context=is_retry_context,
            **parse_kwargs,
        )

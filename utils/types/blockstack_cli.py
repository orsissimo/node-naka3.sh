#!/usr/bin/env python3

from pydantic import BaseModel, Field


class SecretKeyInfo(BaseModel):
    """Typed response from generate-sk command."""

    secret_key: str = Field(alias="secretKey")
    public_key: str = Field(alias="publicKey")
    stacks_address: str = Field(alias="stacksAddress")

    class Config:
        populate_by_name = True


class AddressInfo(BaseModel):
    """Typed response from addresses command."""

    stx_address: str = Field(alias="STX")
    btc_address: str = Field(alias="BTC")

    class Config:
        populate_by_name = True
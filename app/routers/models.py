from datetime import datetime
from typing import Any, Union

from pydantic import BaseModel, Field, field_validator

from eth_typing import HexStr
from safe_eth.eth.utils import (
    ChecksumAddress,
    fast_is_checksum_address,
    fast_to_checksum_address,
)

from ..services.data_decoder import DecodingAccuracyEnum


class About(BaseModel):
    version: str


class ProjectPublic(BaseModel):
    description: str
    logo_file: str

    class Config:
        from_attributes = True


class AbiPublic(BaseModel):
    abi_json: list[dict] | dict | None
    abi_hash: bytes | str
    modified: datetime

    class Config:
        from_attributes = True

    @field_validator("abi_hash")
    @classmethod
    def convert_bytes_to_hex(cls, abi_hash: bytes):
        """
        Convert bytes to hex

        :param abi_hash:
        :return:
        """
        if isinstance(abi_hash, bytes):
            return "0x" + abi_hash.hex()  # Convert bytes to a hex string
        return abi_hash


class ContractsPublic(BaseModel):
    address: bytes | ChecksumAddress
    name: str
    display_name: str | None
    chain_id: int
    project: ProjectPublic | None
    abi: AbiPublic | None
    modified: datetime

    class Config:
        from_attributes = True

    @field_validator("address")
    @classmethod
    def convert_to_checksum_address(cls, address: bytes):
        """
        Convert bytes address to checksum address

        :param address:
        :return:
        """
        if isinstance(address, bytes):
            return fast_to_checksum_address(address)
        return address


class DataDecoderInput(BaseModel):
    data: str = Field(
        ..., pattern=r"^0x[0-9a-fA-F]*$", description="0x-prefixed hexadecimal string"
    )
    to: ChecksumAddress | None = Field(
        None, pattern=r"^0x[0-9a-fA-F]{40}$", description="Optional to address"
    )
    chain_id: int | None = Field(
        None,
        gt=0,
        description="Optional Chain ID as a positive integer",
        alias="chainId",
    )

    @field_validator("to")
    def validate_checksum_address(cls, value):
        if value and not fast_is_checksum_address(value):
            raise ValueError("Address is not checksumed")
        return value


class ParameterDecodedPublic(BaseModel):
    name: str
    type: str
    value: Any
    value_decoded: (
        Union[list["MultisendDecodedPublic"], "DataDecodedPublic", None] | None
    ) = None


class DataDecodedPublic(BaseModel):
    method: str
    parameters: list[ParameterDecodedPublic]
    accuracy: DecodingAccuracyEnum


class MultisendDecodedPublic(BaseModel):
    operation: int
    to: ChecksumAddress
    value: str
    data: HexStr | None = None
    data_decoded: DataDecodedPublic | None = None

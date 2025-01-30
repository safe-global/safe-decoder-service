from datetime import datetime
from typing import Any, Union

from pydantic import Field, field_validator, model_validator

from eth_typing import HexStr
from fastapi_camelcase import CamelModel
from safe_eth.eth.utils import (
    ChecksumAddress,
    fast_is_checksum_address,
    fast_to_checksum_address,
)

from ..services.data_decoder import DecodingAccuracyEnum


class AboutPublic(CamelModel):
    version: str


class ProjectPublic(CamelModel):
    description: str
    logo_file: str

    class Config:
        from_attributes = True


class AbiPublic(CamelModel):
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


class ContractsPublic(CamelModel):
    address: bytes | ChecksumAddress
    name: str
    display_name: str | None
    chain_id: int
    project: ProjectPublic | None
    abi: AbiPublic
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


class DataDecoderInput(CamelModel):
    data: str = Field(
        ..., pattern=r"^0x[0-9a-fA-F]*$", description="0x-prefixed hexadecimal string"
    )
    to: ChecksumAddress | None = Field(
        default=None, pattern=r"^0x[0-9a-fA-F]{40}$", description="Optional to address"
    )
    chain_id: int | None = Field(
        default=None,
        gt=0,
        description="Optional Chain ID as a positive integer",
    )

    @field_validator("to")
    def validate_checksum_address(cls, value):
        if value and not fast_is_checksum_address(value):
            raise ValueError("Address is not checksumed")
        return value

    @model_validator(mode="before")
    @classmethod
    def check_chain_id_requires_to(cls, data: Any) -> Any:
        """
        ChainId requires to, it doesn't make sense otherwise

        :param data:
        :return:
        :raises ValueError: if `chain_id` is set but `to` is not
        """
        if isinstance(data, dict):
            if data.get("chainId") is not None and data.get("to") is None:
                raise ValueError("'chainId' requires 'to' to be set")
        return data


class ParameterDecodedPublic(CamelModel):
    name: str
    type: str
    value: Any
    value_decoded: Union[
        list["MultisendDecodedPublic"], "BaseDataDecodedPublic", None
    ] = None


class BaseDataDecodedPublic(CamelModel):
    method: str
    parameters: list[ParameterDecodedPublic]


class DataDecodedPublic(BaseDataDecodedPublic):
    accuracy: DecodingAccuracyEnum


class MultisendDecodedPublic(CamelModel):
    operation: int
    to: ChecksumAddress
    value: str
    data: HexStr | None = None
    data_decoded: BaseDataDecodedPublic | None = None

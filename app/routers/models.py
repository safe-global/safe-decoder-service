from datetime import datetime
from typing import Any, Union

from pydantic import Field, computed_field, field_validator, model_validator

from eth_typing import HexStr
from fastapi_camelcase import CamelModel
from safe_eth.eth.utils import (
    ChecksumAddress,
    fast_is_checksum_address,
    fast_to_checksum_address,
)
from safe_eth.util.util import to_0x_hex_str

from ..config import settings
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
            return to_0x_hex_str(abi_hash)  # Convert bytes to a hex string
        return abi_hash


class ContractsPublic(CamelModel):
    address: ChecksumAddress
    name: str
    display_name: str | None
    chain_id: int
    project: ProjectPublic | None
    abi: AbiPublic
    modified: datetime
    trusted_for_delegate_call: bool

    class Config:
        from_attributes = True

    @field_validator("address", mode="before")
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

    @computed_field(return_type=str | None)
    def logo_url(self) -> str | None:
        return f"{settings.CONTRACT_LOGO_BASE_URL}/{self.address}.png"


class DataDecoderInput(CamelModel):
    data: str = Field(
        pattern=r"^0x[0-9a-fA-F]*$",
        description="0x-prefixed hexadecimal string",
        examples=[
            "0xa9059cbb0000000000000000000000005afe3855358e112b5647b952709e6165e1c1eeee00000000000000000000000000000000000000000000001e1de1d2517bae38ac"
        ],
    )
    to: ChecksumAddress | None = Field(
        default=None,
        pattern=r"^0x[0-9a-fA-F]{40}$",
        description="Optional to address",
        examples=["0x5aFE3855358E112B5647B952709E6165e1c1eEEe"],
    )
    chain_id: int | None = Field(
        default=None,
        gt=0,
        description="Optional Chain ID as a positive integer",
        examples=[1],
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

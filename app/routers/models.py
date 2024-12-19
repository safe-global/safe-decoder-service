from pydantic import BaseModel, field_validator


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

    class Config:
        from_attributes = True

    @field_validator("abi_hash")
    @classmethod
    def convert_bytes_to_hex(cls, abi_hash):
        """
        Convert bytes to hex

        :param abi_hash:
        :return:
        """
        if isinstance(abi_hash, bytes):
            return "0x" + abi_hash.hex()  # Convert bytes to a hex string
        return abi_hash


class ContractsPublic(BaseModel):
    address: bytes | str
    name: str
    display_name: str
    chain_id: int
    project: ProjectPublic | None
    abi: AbiPublic | None

    class Config:
        from_attributes = True

    @field_validator("address")
    @classmethod
    def convert_bytes_to_hex(cls, address):
        """
        Convert address bytes to hex

        :param address:
        :return:
        """
        if isinstance(address, bytes):
            return "0x" + address.hex()
        return address

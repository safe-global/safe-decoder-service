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
    def convert_bytes_to_hex(cls, v):
        if isinstance(v, bytes):
            return "0x" + v.hex()  # Convert bytes to a hex string
        return v


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
    def convert_bytes_to_hex(cls, v):
        if isinstance(v, bytes):
            return "0x" + v.hex()  # Convert bytes to a hex string
        return v

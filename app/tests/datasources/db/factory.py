import random

from eth_account import Account
from faker import Faker
from hexbytes import HexBytes

from app.datasources.db.models import Contract

fake = Faker()

COMMON_CHAIN_IDS = [1, 5, 10, 56, 137, 42161, 11155111]


async def contract_factory(
    address: str | None = None,
    chain_id: int | None = None,
    name: str | None = None,
    display_name: str | None = None,
    description: str | None = None,
    trusted_for_delegate_call: bool = False,
) -> Contract:
    contract = Contract(
        address=HexBytes(address or Account.create().address),
        chain_id=chain_id or random.choice(COMMON_CHAIN_IDS),
        name=name or fake.company(),
        display_name=display_name or fake.catch_phrase(),
        description=description or fake.sentence(),
        trusted_for_delegate_call=trusted_for_delegate_call,
    )
    return await contract.create()

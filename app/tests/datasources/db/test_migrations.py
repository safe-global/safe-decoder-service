import asyncio

from alembic import command
from alembic.config import Config
from hexbytes import HexBytes
from sqlalchemy import text

from app.datasources.db.database import db_session, db_session_context
from app.datasources.db.models import Contract
from app.tests.datasources.db.async_db_test_case import AsyncDbTestCase


class TestMigrations(AsyncDbTestCase):
    def setUp(self):
        super().setUp()
        self.alembic_config = Config("alembic.ini")

    async def asyncTearDown(self):
        await asyncio.to_thread(command.upgrade, self.alembic_config, "head")

    @staticmethod
    async def get_alembic_version():
        result = await db_session.execute(
            text("SELECT version_num FROM alembic_version")
        )
        return result.scalar_one()

    @db_session_context
    async def test_migration_rename_trusted_for_delegate(self):
        tested_version = "03d30b614dc0"
        previous_version = "66c1eb4456de"
        address = HexBytes("0x6eEF70Da339a98102a642969B3956DEa71A1096e")
        name = "Safe Contract"
        contract = await Contract(
            address=address, name=name, chain_id=1, trusted_for_delegate_call=True
        ).create()
        await db_session.commit()

        await asyncio.to_thread(
            command.downgrade, self.alembic_config, previous_version
        )
        self.assertEqual(await self.get_alembic_version(), previous_version)
        trusted_for_delegate = await db_session.execute(
            text("Select trusted_for_delegate from contract limit 1")
        )
        await db_session.commit()
        self.assertTrue(trusted_for_delegate.scalar_one())

        await asyncio.to_thread(command.upgrade, self.alembic_config, tested_version)
        self.assertEqual(await self.get_alembic_version(), tested_version)
        contract = await Contract.get_contract(address=address, chain_id=1)
        self.assertTrue(contract.trusted_for_delegate_call)

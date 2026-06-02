# SPDX-License-Identifier: FSL-1.1-MIT
import asyncio

from alembic import command
from alembic.config import Config
from hexbytes import HexBytes
from sqlalchemy import text

from app.datasources.db.database import db_session, db_session_context
from app.datasources.db.models import Abi, AbiSource, Contract
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

    @db_session_context
    async def test_migration_abi_hash_generated_column(self):
        tested_version = "a4f3b2c1d8e9"
        previous_version = "0da35e86b777"

        # At head: abi_hash is a GENERATED ALWAYS AS column — insert an ABI and
        # verify PostgreSQL populates the hash automatically (sha256 = 32 bytes).
        source = AbiSource(name="migration_hash_test", url="")
        await source.create()
        source_id = source.id
        abi = Abi(
            abi_json=[{"type": "function", "name": "transfer"}],
            relevance=0,
            source_id=source_id,
        )
        await abi.create()
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT length(abi_hash) FROM abi LIMIT 1")
        )
        await db_session.commit()
        self.assertEqual(result.scalar_one(), 32)

        # Downgrade: abi_hash becomes a plain nullable bytea column.
        # Existing rows lose their hash value (NULL after column recreation).
        await asyncio.to_thread(
            command.downgrade, self.alembic_config, previous_version
        )
        self.assertEqual(await self.get_alembic_version(), previous_version)
        result = await db_session.execute(text("SELECT abi_hash FROM abi LIMIT 1"))
        await db_session.commit()
        self.assertIsNone(result.scalar_one())

        # Upgrade: abi_hash becomes a generated column again.
        # PostgreSQL recomputes the hash for all existing rows on the ALTER TABLE.
        await asyncio.to_thread(command.upgrade, self.alembic_config, tested_version)
        self.assertEqual(await self.get_alembic_version(), tested_version)
        result = await db_session.execute(
            text("SELECT length(abi_hash) FROM abi LIMIT 1")
        )
        await db_session.commit()
        self.assertEqual(result.scalar_one(), 32)

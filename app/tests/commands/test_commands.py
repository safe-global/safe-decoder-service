# SPDX-License-Identifier: FSL-1.1-MIT
import io
import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, call, patch

from hexbytes import HexBytes
from typer.testing import CliRunner

from app.commands.command_cli import app
from app.commands.download_contract import download_contract_command
from app.commands.safe_contracts import sync_safe_contracts_command
from app.datasources.db.database import db_session_context
from app.datasources.db.models import Abi, AbiSource, Contract
from app.services.safe_contracts_service import SafeContractsService
from app.tests.datasources.db.async_db_test_case import AsyncDbTestCase
from app.workers.tasks import get_contract_metadata_task

runner = CliRunner()


@contextmanager
def capture_stdout():
    buffer = io.StringIO()
    original_stdout = sys.stdout
    try:
        sys.stdout = buffer
        yield buffer
    finally:
        sys.stdout = original_stdout


class TestCommands(AsyncDbTestCase):
    @db_session_context
    @patch(
        "app.services.contract_metadata_service.ContractMetadataService.get_proxy_implementation_address"
    )
    @patch(
        "app.services.contract_metadata_service.ContractMetadataService.process_contract_metadata",
        new_callable=AsyncMock,
    )
    async def test_download_contract(
        self,
        mock_process_contract_metadata: AsyncMock,
        mock_get_proxy_implementation_address: MagicMock,
    ):
        address = "0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4"
        mock_process_contract_metadata.return_value = False
        mock_get_proxy_implementation_address.return_value = None
        with capture_stdout() as buffer:
            await download_contract_command(address=address, chain_id=1)
            self.assertEqual(
                buffer.getvalue(),
                "==================================================\n"
                "Downloading contract 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4\n"
                "==================================================\n"
                "Contract 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4 was never retrieved\n"
                "Failed to download contract metadata\n",
            )
        mock_process_contract_metadata.return_value = True
        with capture_stdout() as buffer:
            await download_contract_command(address=address, chain_id=1)
            self.assertEqual(
                buffer.getvalue(),
                "==================================================\n"
                "Downloading contract 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4\n"
                "==================================================\n"
                "Contract 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4 was never retrieved\n"
                "Success download contract metadata\n",
            )
        contract = await Contract(
            address=HexBytes(address), chain_id=1, fetch_retries=10
        ).create()
        with capture_stdout() as buffer:
            await download_contract_command(address=address, chain_id=1)
            self.assertEqual(
                buffer.getvalue(),
                "==================================================\n"
                "Downloading contract 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4\n"
                "==================================================\n"
                "Contract: 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4, retries: 10, contains ABI: False\n"
                "Success download contract metadata\n",
            )
        source, _ = await AbiSource.get_or_create("Etherscan", "")
        abi, _ = await Abi.get_or_create_abi(
            abi_json={}, source_id=source.id, relevance=100
        )
        contract.abi_id = abi.id
        await contract.update()
        with capture_stdout() as buffer:
            await download_contract_command(address=address, chain_id=1)
            self.assertEqual(
                buffer.getvalue(),
                "==================================================\n"
                "Downloading contract 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4\n"
                "==================================================\n"
                "Contract: 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4, retries: 10, contains ABI: True\n"
                "Success download contract metadata\n",
            )
        mock_get_proxy_implementation_address.return_value = (
            "0x41675C099F32341bf84BFc5382aF534df5C7461a"
        )
        with capture_stdout() as buffer:
            await download_contract_command(address=address, chain_id=1)
            self.assertEqual(
                buffer.getvalue(),
                "==================================================\n"
                "Downloading contract 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4\n"
                "==================================================\n"
                "Contract: 0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4, retries: 10, contains ABI: True\n"
                "Success download contract metadata\n"
                "The contract is a proxy.\n"
                "Adding task to download proxy implementation metadata with address 0x41675C099F32341bf84BFc5382aF534df5C7461a\n",
            )

    def test_sync_safe_contracts_requires_chain_id(self):
        result = runner.invoke(app, ["sync-safe-contracts"])
        self.assertEqual(result.exit_code, 2)

    @db_session_context
    @patch.object(get_contract_metadata_task, "kiq", new_callable=AsyncMock)
    async def test_sync_safe_contracts(self, mock_kiq: AsyncMock):
        safe_migration_address = HexBytes("0x6439e7ABD8Bb915A5263094784C5CF561c4172AC")
        await Contract(
            address=safe_migration_address, chain_id=480, fetch_retries=91
        ).create()
        deployments = SafeContractsService._get_default_deployments_by_version()

        with capture_stdout() as buffer:
            await sync_safe_contracts_command([480, 10])
        self.assertEqual(
            buffer.getvalue(),
            "==================================================\n"
            "Syncing Safe contracts\n"
            "==================================================\n"
            f"Chain 480: created {len(deployments) - 1} Safe contracts, "
            f"enqueued {len(deployments)} without ABI\n"
            f"Chain 10: created {len(deployments)} Safe contracts, "
            f"enqueued {len(deployments)} without ABI\n",
        )
        self.assertCountEqual(
            mock_kiq.call_args_list,
            [
                call(
                    address=contract_address.lower(),
                    chain_id=chain_id,
                    skip_attempt_download=True,
                )
                for chain_id in (480, 10)
                for _, _, contract_address in deployments
            ],
        )
        safe_migration = await Contract.get_contract(
            address=safe_migration_address, chain_id=480
        )
        self.assertEqual(safe_migration.name, "SafeMigration")
        self.assertTrue(safe_migration.trusted_for_delegate_call)
        self.assertEqual(safe_migration.fetch_retries, 0)

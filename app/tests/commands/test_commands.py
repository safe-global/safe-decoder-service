import io
import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from hexbytes import HexBytes
from typer.testing import CliRunner

from app.commands.download_contract import download_contract_command
from app.datasources.db.database import db_session_context
from app.datasources.db.models import Abi, AbiSource, Contract
from app.tests.datasources.db.async_db_test_case import AsyncDbTestCase

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

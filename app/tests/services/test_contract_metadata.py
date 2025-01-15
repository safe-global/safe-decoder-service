from unittest import mock
from unittest.mock import MagicMock

from eth_account import Account
from hexbytes import HexBytes
from safe_eth.eth.clients import (
    AsyncBlockscoutClient,
    AsyncEtherscanClientV2,
    AsyncSourcifyClient,
    BlockScoutConfigurationProblem,
    EtherscanClientConfigurationProblem,
    SourcifyClientConfigurationProblem,
)
from safe_eth.eth.utils import fast_to_checksum_address
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import database_session
from app.datasources.db.models import Abi, AbiSource, Contract
from app.services.contract_metadata_service import (
    ContractMetadataService,
    ContractSource,
    EnhancedContractMetadata,
)

from ..datasources.db.db_async_conn import DbAsyncConn
from ..mocks.contract_metadata_mocks import (
    blockscout_metadata_mock,
    etherscan_metadata_mock,
    etherscan_proxy_metadata_mock,
    sourcify_metadata_mock,
)


class TestContractMetadataService(DbAsyncConn):

    @mock.patch.object(
        AsyncEtherscanClientV2, "async_get_contract_metadata", autospec=True
    )
    @mock.patch.object(
        AsyncBlockscoutClient, "async_get_contract_metadata", autospec=True
    )
    @mock.patch.object(
        AsyncSourcifyClient, "is_chain_supported", autospec=True, return_value=True
    )
    @mock.patch.object(
        AsyncSourcifyClient, "async_get_contract_metadata", autospec=True
    )
    async def test_get_contract_metadata(
        self,
        sourcify_get_contract_metadata_mock: MagicMock,
        sourcify_is_chain_supported: MagicMock,
        blockscout_get_contract_metadata_mock: MagicMock,
        etherscan_get_contract_metadata_mock: MagicMock,
    ):
        contract_metadata_service = ContractMetadataService("")
        chain_id = 100
        etherscan_get_contract_metadata_mock.return_value = etherscan_metadata_mock
        sourcify_get_contract_metadata_mock.return_value = sourcify_metadata_mock
        blockscout_get_contract_metadata_mock.return_value = blockscout_metadata_mock

        random_address = Account.create().address
        contract_data = await contract_metadata_service.get_contract_metadata(
            random_address, chain_id
        )
        self.assertEqual(
            contract_data.metadata,
            etherscan_metadata_mock,
        )
        self.assertIsNotNone(contract_data.source)
        self.assertEqual(contract_data.source.value, "Etherscan")  # type: ignore

        etherscan_get_contract_metadata_mock.return_value = None
        contract_data = await contract_metadata_service.get_contract_metadata(
            random_address, chain_id
        )
        self.assertEqual(contract_data.address, random_address)
        self.assertEqual(
            contract_data.metadata,
            sourcify_metadata_mock,
        )
        self.assertIsNotNone(contract_data.source)
        self.assertEqual(contract_data.source.value, "Sourcify")  # type: ignore

        sourcify_get_contract_metadata_mock.side_effect = IOError
        contract_data = await contract_metadata_service.get_contract_metadata(
            random_address, chain_id
        )
        self.assertEqual(
            contract_data.metadata,
            blockscout_metadata_mock,
        )
        self.assertIsNotNone(contract_data.source)
        self.assertEqual(contract_data.source.value, "Blockscout")  # type: ignore

        blockscout_get_contract_metadata_mock.side_effect = IOError
        contract_data = await contract_metadata_service.get_contract_metadata(
            random_address, chain_id
        )
        self.assertIsNotNone(contract_data)
        self.assertIsNone(
            contract_data.metadata,
        )

    @mock.patch.object(
        AsyncEtherscanClientV2, "async_get_contract_metadata", autospec=True
    )
    async def test_multichain_contract_metadata(
        self,
        etherscan_get_contract_metadata_mock: MagicMock,
    ):
        etherscan_get_contract_metadata_mock.return_value = etherscan_metadata_mock
        contract_metadata_service = ContractMetadataService("")
        contract_address = fast_to_checksum_address(
            "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"
        )
        metadata_mainnet = await contract_metadata_service.get_contract_metadata(
            fast_to_checksum_address(contract_address), 1
        )
        self.assertIsNotNone(metadata_mainnet)
        metadata_gnosis_chain = await contract_metadata_service.get_contract_metadata(
            contract_address, 100
        )
        self.assertIsNotNone(metadata_gnosis_chain)
        self.assertEqual(metadata_gnosis_chain.metadata, metadata_mainnet.metadata)
        self.assertEqual(metadata_mainnet.chain_id, 1)
        self.assertEqual(metadata_gnosis_chain.chain_id, 100)

    @mock.patch.object(AsyncBlockscoutClient, "__init__", return_value=None)
    @mock.patch.object(AsyncSourcifyClient, "__init__", return_value=None)
    @mock.patch.object(AsyncEtherscanClientV2, "__init__", return_value=None)
    async def test_enabled_clients(
        self,
        mock_etherscan_client: MagicMock,
        mock_sourcify_client: MagicMock,
        mock_blockscout_client: MagicMock,
    ):
        chain_id = 100
        contract_metadata_service = ContractMetadataService("")
        enabled_clients = contract_metadata_service.enabled_clients(chain_id)
        self.assertEqual(len(enabled_clients), 3)
        self.assertIsInstance(enabled_clients[0], AsyncEtherscanClientV2)
        self.assertIsInstance(enabled_clients[1], AsyncSourcifyClient)
        self.assertIsInstance(enabled_clients[2], AsyncBlockscoutClient)
        contract_metadata_service.enabled_clients.cache_clear()
        mock_etherscan_client.side_effect = EtherscanClientConfigurationProblem
        enabled_clients = contract_metadata_service.enabled_clients(chain_id)
        self.assertEqual(len(enabled_clients), 2)
        self.assertIsInstance(enabled_clients[0], AsyncSourcifyClient)
        self.assertIsInstance(enabled_clients[1], AsyncBlockscoutClient)
        contract_metadata_service.enabled_clients.cache_clear()
        mock_sourcify_client.side_effect = SourcifyClientConfigurationProblem
        enabled_clients = contract_metadata_service.enabled_clients(chain_id)
        self.assertEqual(len(enabled_clients), 1)
        self.assertIsInstance(enabled_clients[0], AsyncBlockscoutClient)
        contract_metadata_service.enabled_clients.cache_clear()
        mock_blockscout_client.side_effect = BlockScoutConfigurationProblem
        enabled_clients = contract_metadata_service.enabled_clients(chain_id)
        self.assertEqual(len(enabled_clients), 0)

    @database_session
    async def test_process_contract_metadata(self, session: AsyncSession):
        # New contract and abi
        random_address = Account.create().address
        await AbiSource.get_or_create(session, "Etherscan", "")
        contract_data = EnhancedContractMetadata(
            address=random_address,
            metadata=etherscan_metadata_mock,
            source=ContractSource.ETHERSCAN,
            chain_id=1,
        )
        await ContractMetadataService.process_contract_metadata(session, contract_data)
        contract = await Contract.get_contract(
            session, address=HexBytes(random_address), chain_id=1
        )
        self.assertIsNotNone(contract)
        self.assertEqual(HexBytes(contract.address), HexBytes(random_address))
        self.assertEqual(contract.name, etherscan_metadata_mock.name)
        self.assertIsNone(contract.implementation)
        self.assertEqual(contract.abi.abi_json, etherscan_metadata_mock.abi)
        self.assertEqual(contract.chain_id, 1)
        self.assertEqual(contract.fetch_retries, 1)

        # New proxy contract
        proxy_contract_data = EnhancedContractMetadata(
            address=random_address,
            metadata=etherscan_proxy_metadata_mock,
            source=ContractSource.ETHERSCAN,
            chain_id=1,
        )
        await ContractMetadataService.process_contract_metadata(
            session, proxy_contract_data
        )
        proxy_contract = await Contract.get_contract(
            session, address=HexBytes(random_address), chain_id=1
        )
        self.assertIsNotNone(proxy_contract)
        self.assertEqual(
            proxy_contract.implementation,
            HexBytes("0x43506849d7c04f9138d1a2050bbf3a0c054402dd"),
        )

        # Same contract shouldn't be updated without abi
        contract_data.metadata = None
        await ContractMetadataService.process_contract_metadata(session, contract_data)
        contract = await Contract.get_contract(
            session, address=HexBytes(random_address), chain_id=1
        )
        self.assertEqual(contract.abi.abi_json, etherscan_metadata_mock.abi)
        # Should increment fetch_retries when abi was not downloaded
        contract_data.address = Account.create().address
        await ContractMetadataService.process_contract_metadata(session, contract_data)
        contract = await Contract.get_contract(
            session, address=HexBytes(contract_data.address), chain_id=1
        )
        self.assertIsNone(contract.abi_id)
        self.assertEqual(contract.fetch_retries, 1)
        await ContractMetadataService.process_contract_metadata(session, contract_data)
        contract = await Contract.get_contract(
            session, address=HexBytes(contract_data.address), chain_id=1
        )
        self.assertIsNone(contract.abi_id)
        self.assertEqual(contract.fetch_retries, 2)

        await AbiSource.get_or_create(session, "Blockscout", "")
        contract_data.metadata = blockscout_metadata_mock
        contract_data.source = ContractSource.BLOCKSCOUT
        await ContractMetadataService.process_contract_metadata(session, contract_data)
        new_contract = await Contract.get_contract(
            session, address=HexBytes(contract_data.address), chain_id=1
        )
        # Refresh was necessary to reuse the same session
        await session.refresh(new_contract)
        self.assertEqual(new_contract.abi.abi_json, blockscout_metadata_mock.abi)

    @database_session
    async def test_should_attempt_download(self, session: AsyncSession):
        random_address = Account.create().address
        contract = await Contract(address=HexBytes(random_address), chain_id=1).create(
            session
        )
        self.assertTrue(
            await ContractMetadataService.should_attempt_download(
                session, fast_to_checksum_address(random_address), 1, 0
            )
        )
        contract.fetch_retries += 1
        await contract.update(session)
        self.assertFalse(
            await ContractMetadataService.should_attempt_download(
                session, fast_to_checksum_address(random_address), 1, 0
            )
        )
        # Should be cached and don't reach the dataqbase
        with mock.patch.object(Contract, "get_contract") as mocked_get_contract:
            self.assertFalse(
                await ContractMetadataService.should_attempt_download(
                    session, fast_to_checksum_address(random_address), 1, 0
                )
            )
            mocked_get_contract.assert_not_called()

        # Should be false if contract has abi_id
        source, _ = await AbiSource.get_or_create(session, "Etherscan", "")
        abi = Abi(
            abi_hash=b"A Test Abi",
            abi_json=etherscan_metadata_mock.abi,
            relevance=10,
            source_id=source.id,
        )
        await abi.create(session)
        contract.abi_id = abi.id
        await contract.update(session)
        self.assertFalse(
            await ContractMetadataService.should_attempt_download(
                session, fast_to_checksum_address(random_address), 1, 10
            )
        )

        await Contract(address=HexBytes(random_address), chain_id=100).create(session)
        self.assertTrue(
            await ContractMetadataService.should_attempt_download(
                session, fast_to_checksum_address(random_address), 100, 0
            )
        )

    def test_get_proxy_implementation_address(self):
        random_address = Account.create().address
        proxy_contract_data = EnhancedContractMetadata(
            address=random_address,
            metadata=etherscan_proxy_metadata_mock,
            source=ContractSource.ETHERSCAN,
            chain_id=1,
        )
        proxy_implementation_address = (
            ContractMetadataService.get_proxy_implementation_address(
                proxy_contract_data
            )
        )
        self.assertEqual(
            proxy_implementation_address, "0x43506849D7C04F9138D1A2050bbF3A0c054402dd"
        )

        contract_data = EnhancedContractMetadata(
            address=random_address,
            metadata=etherscan_metadata_mock,
            source=ContractSource.ETHERSCAN,
            chain_id=1,
        )
        self.assertIsNone(
            ContractMetadataService.get_proxy_implementation_address(contract_data)
        )

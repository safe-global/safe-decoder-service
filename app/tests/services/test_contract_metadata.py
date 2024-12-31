import unittest
from unittest import mock
from unittest.mock import MagicMock

from eth_account import Account
from safe_eth.eth.clients import (
    AsyncBlockscoutClient,
    AsyncEtherscanClientV2,
    AsyncSourcifyClient,
    BlockScoutConfigurationProblem,
    EtherscanClientConfigurationProblem,
    SourcifyClientConfigurationProblem,
)

from app.services.contract_metadata_service import (
    ContractMetadataService,
    get_contract_metadata_service,
)
from app.tests.mocks.contract_metadata_mocks import (
    blockscout_metadata_mock,
    etherscan_metadata_mock,
    sourcify_metadata_mock,
)


class TestContractMetadataService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        get_contract_metadata_service.cache_clear()
        self.contract_metadata_service = get_contract_metadata_service()

    async def asyncTearDown(self):
        get_contract_metadata_service.cache_clear()

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
        chain_id = 100
        etherscan_get_contract_metadata_mock.return_value = etherscan_metadata_mock
        sourcify_get_contract_metadata_mock.return_value = sourcify_metadata_mock
        blockscout_get_contract_metadata_mock.return_value = blockscout_metadata_mock

        random_address = Account.create().address
        self.assertEqual(
            await self.contract_metadata_service.get_contract_metadata(
                random_address, chain_id
            ),
            etherscan_metadata_mock,
        )
        etherscan_get_contract_metadata_mock.return_value = None
        self.assertEqual(
            await self.contract_metadata_service.get_contract_metadata(
                random_address, chain_id
            ),
            sourcify_metadata_mock,
        )
        sourcify_get_contract_metadata_mock.side_effect = IOError
        self.assertEqual(
            await self.contract_metadata_service.get_contract_metadata(
                random_address, chain_id
            ),
            blockscout_metadata_mock,
        )

        blockscout_get_contract_metadata_mock.side_effect = IOError
        self.assertIsNone(
            await self.contract_metadata_service.get_contract_metadata(
                random_address, chain_id
            )
        )

    async def test_multichain_contract_metadata(self):
        contract_address = "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"
        metadata_mainnet = await self.contract_metadata_service.get_contract_metadata(
            contract_address, 1
        )
        self.assertIsNotNone(metadata_mainnet)
        metadata_gnosis_chain = (
            await self.contract_metadata_service.get_contract_metadata(
                contract_address, 100
            )
        )
        self.assertIsNotNone(metadata_gnosis_chain)
        self.assertEqual(metadata_gnosis_chain, metadata_mainnet)

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

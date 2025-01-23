from collections import Counter

from ...datasources.db.models import Abi, AbiSource
from ...services.abis import AbiService
from ...tests.datasources.db.db_async_conn import DbAsyncConn


class TestAbiService(DbAsyncConn):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.abi_service = AbiService()

    async def test_load_local_abis_in_database(self):
        self.assertEqual(await AbiSource.get_all(), [])
        self.assertEqual(await Abi.get_all(), [])

        await self.abi_service.load_local_abis_in_database()
        self.assertEqual(len(await AbiSource.get_all()), 1)
        abis = await Abi.get_all()
        self.assertEqual(len(abis), 152)
        relevance_counts = Counter(abi.relevance for abi in abis)
        self.assertEqual(relevance_counts[100], 5)
        self.assertEqual(relevance_counts[90], 5)
        self.assertEqual(relevance_counts[50], 142)

        await self.abi_service.load_local_abis_in_database()
        self.assertEqual(len(await Abi.get_all()), 152)

    def test_get_safe_contracts_abis(self):
        abis = self.abi_service.get_safe_contracts_abis()
        self.assertEqual(len(abis), 5)

    def test_get_safe_abis(self):
        abis = self.abi_service.get_safe_abis()
        self.assertEqual(len(abis), 3)

    def test_get_erc_abis(self):
        abis = self.abi_service.get_erc_abis()
        self.assertEqual(len(abis), 2)

    def test_get_third_parties_abis(self):
        abis = self.abi_service.get_third_parties_abis()
        self.assertEqual(len(abis), 142)

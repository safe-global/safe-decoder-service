import asyncio
import unittest

from app.services.contract_metadata_service import ContractMetadataService


class TestContractMetadataService(unittest.IsolatedAsyncioTestCase):

    async def test_get_contract_metadata(self):
        contract_metadata_service = ContractMetadataService()
        tasks = []
        for i in range(100):
            tasks.append(
                contract_metadata_service.get_contract_metadata(
                    "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552", 100
                )
            )

        results = await asyncio.gather(*tasks)
        self.assertIsNotNone(results)

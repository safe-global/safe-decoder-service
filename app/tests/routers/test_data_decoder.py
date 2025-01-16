import unittest

from fastapi.testclient import TestClient

from hexbytes import HexBytes
from sqlmodel.ext.asyncio.session import AsyncSession

from ...datasources.db.database import database_session
from ...datasources.db.models import AbiSource
from ...main import app
from ...services.abis import AbiService


class TestRouterAbout(unittest.TestCase):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @database_session
    async def test_view_data_decoder(self, session: AsyncSession):
        # Add safe abis for testing
        abi_service = AbiService()
        safe_abis = abi_service.get_safe_abis()
        abi_source, _ = await AbiSource.get_or_create(
            session, "localstorage", "decoder-service"
        )
        await abi_service._store_abis_in_database(session, safe_abis, 100, abi_source)

        add_owner_with_threshold_data = HexBytes(
            "0x0d582f130000000000000000000000001b9a0da11a5cace4e7035993cbb2e4"
            "b1b3b164cf000000000000000000000000000000000000000000000000000000"
            "0000000001"
        )

        response = self.client.post(
            "/api/v1/data-decoder/", json={"data": add_owner_with_threshold_data.hex()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "method": "addOwnerWithThreshold",
                "parameters": [
                    {
                        "name": "owner",
                        "type": "address",
                        "value": "0x1b9a0DA11a5caCE4e7035993Cbb2E4B1B3b164Cf",
                        "value_decoded": None,
                    },
                    {
                        "name": "_threshold",
                        "type": "uint256",
                        "value": "1",
                        "value_decoded": None,
                    },
                ],
            },
        )

        response = self.client.post("/api/v1/data-decoder/", json={"data": "0x123"})
        self.assertEqual(response.status_code, 404)

        # Test no checksumed address
        response = self.client.post(
            "/api/v1/data-decoder/",
            json={
                "data": add_owner_with_threshold_data.hex(),
                "to": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            },
        )
        self.assertEqual(response.status_code, 422)

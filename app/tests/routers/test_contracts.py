from fastapi.testclient import TestClient
from hexbytes import HexBytes

from ...config import settings
from ...datasources.cache.redis import del_contract_cache
from ...datasources.db.database import db_session_context
from ...datasources.db.models import Abi, AbiSource, Contract
from ...main import app
from ...utils import datetime_to_str
from ..datasources.db.async_db_test_case import AsyncDbTestCase
from ..datasources.db.factory import contract_factory
from ..mocks.abi_mock import mock_abi_json


class TestRouterContract(AsyncDbTestCase):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @db_session_context
    async def test_view_contracts(self):
        address_expected = "0x6eEF70Da339a98102a642969B3956DEa71A1096e"
        response = self.client.get(
            f"/api/v1/contracts/{address_expected}",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

        address = HexBytes(address_expected)
        contract = Contract(
            address=address, name="A Test Contracts", chain_id=1, fetch_retries=2
        )
        await contract.create()

        # Should return cached response with count 0
        response = self.client.get(
            f"/api/v1/contracts/{address_expected}",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

        # Invalidate cache
        del_contract_cache(address_expected)

        # Should return cached response with count 0
        response = self.client.get(
            f"/api/v1/contracts/{address_expected}",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertIsNone(response_json["results"][0]["abi"])
        source = AbiSource(name="Etherscan", url="https://api.etherscan.io/api")

        await source.create()
        abi = Abi(abi_json=mock_abi_json, source_id=source.id)
        await abi.create()
        contract.abi_id = abi.id
        await contract.update()

        # Invalidate cache
        del_contract_cache(address_expected)

        response = self.client.get(
            f"/api/v1/contracts/{address_expected}",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(response_json["previous"], None)
        self.assertEqual(response_json["next"], None)
        self.assertEqual(results[0]["name"], "A Test Contracts")
        self.assertEqual(results[0]["address"], address_expected)
        self.assertEqual(results[0]["abi"]["abiJson"], mock_abi_json)
        self.assertEqual(results[0]["abi"]["abiHash"], "0xb4b61541")
        self.assertEqual(results[0]["abi"]["modified"], datetime_to_str(abi.modified))
        self.assertEqual(results[0]["displayName"], None)
        self.assertEqual(results[0]["chainId"], 1)
        self.assertEqual(results[0]["project"], None)
        self.assertEqual(results[0]["modified"], datetime_to_str(contract.modified))
        self.assertFalse(results[0]["trustedForDelegateCall"])
        self.assertEqual(results[0]["fetchRetries"], 2)
        self.assertEqual(
            results[0]["logoUrl"],
            f"{settings.CONTRACT_LOGO_BASE_URL}/{address_expected}.png",
        )
        # Test filter by chain_id
        contract = Contract(
            address=address, name="A Test Contracts", chain_id=5, abi=abi
        )
        await contract.create()

        # Invalidate cache
        del_contract_cache(address_expected)

        response = self.client.get(
            f"/api/v1/contracts/{address_expected}?chain_ids=5",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chainId"], 5)
        # name could be None
        contract_without_name = "0xD1a2a63a9766673940B4D2d7cB16259876Aca8a2"
        contract = Contract(
            address=HexBytes(contract_without_name), chain_id=1, fetch_retries=2
        )
        await contract.create()

        # Invalidate cache
        del_contract_cache(address_expected)

        response = self.client.get(
            f"/api/v1/contracts/{contract_without_name}",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertIsNone(response_json["results"][0]["abi"])

    @db_session_context
    async def test_contracts_pagination(self):
        source = AbiSource(name="Etherscan", url="https://api.etherscan.io/api")
        await source.create()
        abi = Abi(abi_json=mock_abi_json, source_id=source.id)
        await abi.create()
        address_expected = "0x6eEF70Da339a98102a642969B3956DEa71A1096e"
        address = HexBytes(address_expected)
        for chain_id in range(0, 10):
            contract = Contract(
                address=address,
                name="A Test Contracts",
                chain_id=chain_id,
                abi=abi,
            )
            await contract.create()

        response = self.client.get(
            f"/api/v1/contracts/{address_expected}?limit=5",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(response_json["count"], 10)
        self.assertEqual(
            response_json["next"],
            f"http://testserver/api/v1/contracts/{address_expected}?limit=5&offset=5",
        )
        self.assertEqual(response_json["previous"], None)
        self.assertEqual(len(results), 5)

        response = self.client.get(
            f"/api/v1/contracts/{address_expected}?limit=5&offset=5",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(response_json["count"], 10)
        self.assertEqual(response_json["next"], None)
        self.assertEqual(
            response_json["previous"],
            f"http://testserver/api/v1/contracts/{address_expected}?limit=5&offset=0",
        )
        self.assertEqual(len(results), 5)

    @db_session_context
    async def test_view_list_all_contracts(self):
        response = self.client.get(
            "/api/v1/contracts/",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

        untrusted_contract = await contract_factory(
            address="0x0000000000000000000000000000000000000001", chain_id=6
        )
        response = self.client.get(
            "/api/v1/contracts/",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(response_json["next"], None)
        self.assertEqual(response_json["previous"], None)
        self.assertEqual(len(response_json["results"]), 1)
        self.assertEqual(
            response_json["results"][0]["chainId"], untrusted_contract.chain_id
        )
        self.assertEqual(response_json["results"][0]["name"], untrusted_contract.name)
        self.assertEqual(
            HexBytes(response_json["results"][0]["address"]), untrusted_contract.address
        )
        self.assertEqual(
            response_json["results"][0]["displayName"], untrusted_contract.display_name
        )
        self.assertFalse(response_json["results"][0]["trustedForDelegateCall"])

        trusted_contract = await contract_factory(
            address="0x0000000000000000000000000000000000000000",
            trusted_for_delegate_call=True,
            chain_id=5,
        )
        response = self.client.get(
            "/api/v1/contracts/",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 2)

        response = self.client.get(
            "/api/v1/contracts/?trusted_for_delegate_call=true",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["chainId"], trusted_contract.chain_id
        )
        self.assertEqual(response_json["results"][0]["name"], trusted_contract.name)
        self.assertEqual(
            HexBytes(response_json["results"][0]["address"]), trusted_contract.address
        )
        self.assertEqual(
            response_json["results"][0]["displayName"], trusted_contract.display_name
        )
        self.assertTrue(response_json["results"][0]["trustedForDelegateCall"])

        untrusted_contract_next_chain = await contract_factory(
            address="0x0000000000000000000000000000000000000001", chain_id=7
        )

        response = self.client.get(
            "/api/v1/contracts/",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["count"], 3)
        # Should be sorted right
        self.assertEqual(
            response_json["results"][0]["address"],
            "0x0000000000000000000000000000000000000000",
        )
        self.assertEqual(
            response_json["results"][1]["address"],
            "0x0000000000000000000000000000000000000001",
        )
        self.assertEqual(response_json["results"][1]["chainId"], 6)
        self.assertEqual(
            response_json["results"][2]["address"],
            "0x0000000000000000000000000000000000000001",
        )
        self.assertEqual(response_json["results"][2]["chainId"], 7)

        response = self.client.get(
            f"/api/v1/contracts/?chain_ids={untrusted_contract_next_chain.chain_id}",
        )
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["address"],
            "0x0000000000000000000000000000000000000001",
        )
        self.assertEqual(
            response_json["results"][0]["chainId"],
            untrusted_contract_next_chain.chain_id,
        )

    @db_session_context
    async def test_contracts_pagination_with_proxied_host_and_prefix(self):
        source = AbiSource(name="Etherscan", url="https://api.etherscan.io/api")
        await source.create()
        abi = Abi(abi_json=mock_abi_json, source_id=source.id)
        await abi.create()
        address_expected = "0x6eEF70Da339a98102a642969B3956DEa71A1096e"
        address = HexBytes(address_expected)

        # Create multiple contracts to test pagination
        for chain_id in range(0, 10):
            contract = Contract(
                address=address,
                name="A Test Contracts",
                chain_id=chain_id,
                abi=abi,
            )
            await contract.create()

        # Test first page with proxy headers
        response = self.client.get(
            f"/api/v1/contracts/{address_expected}?limit=5",
            headers={
                "x-forwarded-prefix": "/safe-decoder",
                "x-forwarded-host": "proxy.example.com",
                "x-forwarded-proto": "https",
                "x-forwarded-port": "443",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(response_json["count"], 10)
        self.assertEqual(len(results), 5)

        # Check that next URL includes proxy information
        next_url = response_json["next"]
        self.assertIsNotNone(next_url)
        self.assertTrue(
            next_url.startswith("https://proxy.example.com:443/safe-decoder/")
        )
        self.assertIn("limit=5&offset=5", next_url)

        # Previous should be None for first page
        self.assertEqual(response_json["previous"], None)

        # Test second page with proxy headers
        response = self.client.get(
            f"/api/v1/contracts/{address_expected}?limit=5&offset=5",
            headers={
                "x-forwarded-prefix": "/safe-decoder",
                "x-forwarded-host": "proxy.example.com",
                "x-forwarded-proto": "https",
                "x-forwarded-port": "443",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(response_json["count"], 10)
        self.assertEqual(len(results), 5)

        # Check that previous URL includes proxy information
        previous_url = response_json["previous"]
        self.assertIsNotNone(previous_url)
        self.assertTrue(
            previous_url.startswith("https://proxy.example.com:443/safe-decoder/")
        )
        self.assertIn("limit=5&offset=0", previous_url)

        # Next should be None for last page
        self.assertEqual(response_json["next"], None)

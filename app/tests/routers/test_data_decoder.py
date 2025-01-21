from typing import cast

from fastapi.testclient import TestClient

from hexbytes import HexBytes
from safe_eth.eth.constants import NULL_ADDRESS
from safe_eth.eth.utils import get_empty_tx_params
from sqlmodel.ext.asyncio.session import AsyncSession
from web3 import Web3
from web3.types import ABI

from ...datasources.db.database import database_session
from ...datasources.db.models import Abi, AbiSource, Contract
from ...main import app
from ...services.abis import AbiService
from ...services.data_decoder import get_data_decoder_service
from ..datasources.db.db_async_conn import DbAsyncConn


class TestRouterAbout(DbAsyncConn):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        get_data_decoder_service.cache_clear()

    def tearDown(self):
        get_data_decoder_service.cache_clear()

    @database_session
    async def test_view_data_decoder(self, session: AsyncSession):
        # Add safe abis for testing
        abi_service = AbiService()
        safe_abis = abi_service.get_safe_contracts_abis()
        abi_source, _ = await AbiSource.get_or_create(
            session, "localstorage", "decoder-service"
        )
        await abi_service._store_abis_in_database(session, safe_abis, 100, abi_source)

        # Add owner 0x1b9a0DA11a5caCE4e7035993Cbb2E4B1B3b164Cf with threshold 1
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

    @database_session
    async def test_view_data_decoder_with_chain_id(self, session: AsyncSession):
        example_abi = cast(
            ABI,
            [
                {
                    "inputs": [
                        {
                            "internalType": "uint256",
                            "name": "droidId",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "numberOfDroids",
                            "type": "uint256",
                        },
                    ],
                    "name": "buyDroid",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                },
            ],
        )

        example_swapped_abi = cast(
            ABI,
            [
                {
                    "inputs": [
                        {
                            "internalType": "uint256",
                            "name": "numberOfDroids",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "droidId",
                            "type": "uint256",
                        },
                    ],
                    "name": "buyDroid",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                },
            ],
        )

        source = AbiSource(name="local", url="")
        await source.create(session)

        contract_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        abi = Abi(
            abi_hash=b"ExampleABI",
            abi_json=example_abi,
            relevance=101,
            source_id=source.id,
        )
        await abi.create(session)
        contract = Contract(
            address=HexBytes(contract_address),
            abi=abi,
            name="SwappedContract",
            chain_id=1,
        )
        await contract.create(session)

        swapped_abi = Abi(
            abi_hash=b"SwappedABI",
            abi_json=example_swapped_abi,
            relevance=100,
            source_id=source.id,
        )
        await swapped_abi.create(session)
        contract = Contract(
            address=HexBytes(contract_address),
            abi=swapped_abi,
            name="SwappedContract",
            chain_id=2,
        )
        await contract.create(session)

        example_data = (
            Web3()
            .eth.contract(abi=example_abi)
            .functions.buyDroid(4, 10)
            .build_transaction(
                get_empty_tx_params() | {"to": NULL_ADDRESS, "chainId": 1}
            )["data"]
        )

        response = self.client.post(
            "/api/v1/data-decoder/", json={"data": example_data}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "method": "buyDroid",
                "parameters": [
                    {
                        "name": "droidId",
                        "type": "uint256",
                        "value": "4",
                        "value_decoded": None,
                    },
                    {
                        "name": "numberOfDroids",
                        "type": "uint256",
                        "value": "10",
                        "value_decoded": None,
                    },
                ],
            },
        )

        response = self.client.post("/api/v1/data-decoder/", json={"data": "0x123"})
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            "/api/v1/data-decoder/",
            json={
                "data": example_data,
                "to": contract_address,
                "chainId": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "method": "buyDroid",
                "parameters": [
                    {
                        "name": "numberOfDroids",
                        "type": "uint256",
                        "value": "4",
                        "value_decoded": None,
                    },
                    {
                        "name": "droidId",
                        "type": "uint256",
                        "value": "10",
                        "value_decoded": None,
                    },
                ],
            },
        )

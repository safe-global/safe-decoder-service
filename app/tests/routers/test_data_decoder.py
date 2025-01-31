from typing import cast

from fastapi.testclient import TestClient

from hexbytes import HexBytes
from safe_eth.eth.constants import NULL_ADDRESS
from safe_eth.eth.utils import get_empty_tx_params
from web3 import Web3
from web3.types import ABIEvent, ABIFunction

from ...datasources.abis.gnosis_protocol import cowswap_settlement_v2_abi
from ...datasources.db.database import db_session_context
from ...datasources.db.models import Abi, AbiSource, Contract
from ...main import app
from ...services.abis import AbiService
from ...services.data_decoder import DecodingAccuracyEnum, get_data_decoder_service
from ..datasources.db.db_async_conn import DbAsyncConn
from ..services.mocks_data_decoder import example_abi, example_swapped_abi


class TestRouterAbout(DbAsyncConn):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        get_data_decoder_service.cache_clear()

    def tearDown(self):
        get_data_decoder_service.cache_clear()

    @db_session_context
    async def test_view_data_decoder(self):
        # Add safe abis for testing
        abi_service = AbiService()
        safe_abis = abi_service.get_safe_contracts_abis()
        abi_source, _ = await AbiSource.get_or_create("localstorage", "decoder-service")
        await abi_service._store_abis_in_database(safe_abis, 100, abi_source)

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
                "accuracy": DecodingAccuracyEnum.ONLY_FUNCTION_MATCH.name,
                "method": "addOwnerWithThreshold",
                "parameters": [
                    {
                        "name": "owner",
                        "type": "address",
                        "value": "0x1b9a0DA11a5caCE4e7035993Cbb2E4B1B3b164Cf",
                        "valueDecoded": None,
                    },
                    {
                        "name": "_threshold",
                        "type": "uint256",
                        "value": "1",
                        "valueDecoded": None,
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

    @db_session_context
    async def test_view_data_decoder_with_chain_id_without_to(self):
        # Test no checksumed address
        response = self.client.post(
            "/api/v1/data-decoder/",
            json={
                "data": "0x1234",
                "chainId": 1,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "type": "value_error",
                        "loc": ["body"],
                        "msg": "Value error, 'chainId' requires 'to' to be set",
                        "input": {"data": "0x1234", "chainId": 1},
                        "ctx": {"error": {}},
                    }
                ]
            },
        )

    @db_session_context
    async def test_view_data_decoder_with_chain_id(self):
        source = AbiSource(name="local", url="")
        await source.create()

        contract_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        abi = Abi(
            abi_hash=b"ExampleABI",
            abi_json=example_abi,
            relevance=101,
            source_id=source.id,
        )
        await abi.create()
        contract = Contract(
            address=HexBytes(contract_address),
            abi=abi,
            name="SwappedContract",
            chain_id=1,
        )
        await contract.create()

        swapped_abi = Abi(
            abi_hash=b"SwappedABI",
            abi_json=example_swapped_abi,
            relevance=100,
            source_id=source.id,
        )
        await swapped_abi.create()
        contract = Contract(
            address=HexBytes(contract_address),
            abi=swapped_abi,
            name="SwappedContract",
            chain_id=2,
        )
        await contract.create()

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
                "accuracy": DecodingAccuracyEnum.ONLY_FUNCTION_MATCH.name,
                "method": "buyDroid",
                "parameters": [
                    {
                        "name": "droidId",
                        "type": "uint256",
                        "value": "4",
                        "valueDecoded": None,
                    },
                    {
                        "name": "numberOfDroids",
                        "type": "uint256",
                        "value": "10",
                        "valueDecoded": None,
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
                "accuracy": DecodingAccuracyEnum.FULL_MATCH.name,
                "method": "buyDroid",
                "parameters": [
                    {
                        "name": "numberOfDroids",
                        "type": "uint256",
                        "value": "4",
                        "valueDecoded": None,
                    },
                    {
                        "name": "droidId",
                        "type": "uint256",
                        "value": "10",
                        "valueDecoded": None,
                    },
                ],
            },
        )

        response = self.client.post(
            "/api/v1/data-decoder/",
            json={
                "data": example_data,
                "to": contract_address,
                "chainId": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "accuracy": DecodingAccuracyEnum.PARTIAL_MATCH.name,
                "method": "buyDroid",
                "parameters": [
                    {
                        "name": "droidId",
                        "type": "uint256",
                        "value": "4",
                        "valueDecoded": None,
                    },
                    {
                        "name": "numberOfDroids",
                        "type": "uint256",
                        "value": "10",
                        "valueDecoded": None,
                    },
                ],
            },
        )

    @db_session_context
    async def test_view_data_decoder_nested(self):
        # Add safe abis for testing
        abi_service = AbiService()
        safe_abis = abi_service.get_safe_contracts_abis()
        abi_source, _ = await AbiSource.get_or_create("localstorage", "decoder-service")
        await abi_service._store_abis_in_database(safe_abis, 50, abi_source)
        cowswap_abi = cast(list[ABIFunction | ABIEvent], cowswap_settlement_v2_abi)
        await abi_service._store_abis_in_database(
            [cowswap_abi],
            100,
            abi_source,
        )

        # Nested call to CowSwap settlement v2 contract
        # https://sepolia.etherscan.io/tx/0x2f2293ec868e1edf9763a51d19e890f56f6afee155d0a3371ae6518b4c394f30
        data = "0x6a7612020000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab4100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000140000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000022000000000000000000000000000000000000000000000000000000000000000a4ec6cb13f000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000038a1f6fb0cc6526262f88a720c8716adf2d0020645d2cce0e3997413375643e9562a73e61bd15b25b6958b4da3bfc759ca4db249b9678f9521000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008210d8d32da8b9a9da815fa3be1edb76c96d2648a3de1a58d410a961d75ca501e96955ecfefd97cdc953b6e6737377d6fddf644daf050d87bc1846724c6827b7fd1c936e977045ac01dd18a0cc6686354ed28910cba95b4ad5e688c35a3295c9e309124c950598ff534299144a53c4fc00016c30f667a11e90a29536b394d415f5061b000000000000000000000000000000000000000000000000000000000000"
        response = self.client.post(
            "/api/v1/data-decoder/",
            json={
                "data": data,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "method": "execTransaction",
                "parameters": [
                    {
                        "name": "to",
                        "type": "address",
                        "value": "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
                        "valueDecoded": None,
                    },
                    {
                        "name": "value",
                        "type": "uint256",
                        "value": "0",
                        "valueDecoded": None,
                    },
                    {
                        "name": "data",
                        "type": "bytes",
                        "value": "0xec6cb13f000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000038a1f6fb0cc6526262f88a720c8716adf2d0020645d2cce0e3997413375643e9562a73e61bd15b25b6958b4da3bfc759ca4db249b9678f95210000000000000000",
                        "valueDecoded": {
                            "method": "setPreSignature",
                            "parameters": [
                                {
                                    "name": "orderUid",
                                    "type": "bytes",
                                    "value": "0xa1f6fb0cc6526262f88a720c8716adf2d0020645d2cce0e3997413375643e9562a73e61bd15b25b6958b4da3bfc759ca4db249b9678f9521",
                                    "valueDecoded": None,
                                },
                                {
                                    "name": "signed",
                                    "type": "bool",
                                    "value": "True",
                                    "valueDecoded": None,
                                },
                            ],
                        },
                    },
                    {
                        "name": "operation",
                        "type": "uint8",
                        "value": "0",
                        "valueDecoded": None,
                    },
                    {
                        "name": "safeTxGas",
                        "type": "uint256",
                        "value": "0",
                        "valueDecoded": None,
                    },
                    {
                        "name": "baseGas",
                        "type": "uint256",
                        "value": "0",
                        "valueDecoded": None,
                    },
                    {
                        "name": "gasPrice",
                        "type": "uint256",
                        "value": "0",
                        "valueDecoded": None,
                    },
                    {
                        "name": "gasToken",
                        "type": "address",
                        "value": "0x0000000000000000000000000000000000000000",
                        "valueDecoded": None,
                    },
                    {
                        "name": "refundReceiver",
                        "type": "address",
                        "value": "0x0000000000000000000000000000000000000000",
                        "valueDecoded": None,
                    },
                    {
                        "name": "signatures",
                        "type": "bytes",
                        "value": "0x10d8d32da8b9a9da815fa3be1edb76c96d2648a3de1a58d410a961d75ca501e96955ecfefd97cdc953b6e6737377d6fddf644daf050d87bc1846724c6827b7fd1c936e977045ac01dd18a0cc6686354ed28910cba95b4ad5e688c35a3295c9e309124c950598ff534299144a53c4fc00016c30f667a11e90a29536b394d415f5061b",
                        "valueDecoded": None,
                    },
                ],
                "accuracy": "ONLY_FUNCTION_MATCH",
            },
        )

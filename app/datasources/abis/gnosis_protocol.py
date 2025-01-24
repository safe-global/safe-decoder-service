# flake8: noqa E501
import json

gnosis_protocol_abi = json.loads(
    '[{"constant":true,"inputs":[],"name":"IMPROVEMENT_DENOMINATOR","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getSecondsRemainingInBatch","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getEncodedOrders","outputs":[{"name":"elements","type":"bytes"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"buyToken","type":"uint16"},{"name":"sellToken","type":"uint16"},{"name":"validUntil","type":"uint32"},{"name":"buyAmount","type":"uint128"},{"name":"sellAmount","type":"uint128"}],"name":"placeOrder","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"batchId","type":"uint32"},{"name":"claimedObjectiveValue","type":"uint256"},{"name":"owners","type":"address[]"},{"name":"orderIds","type":"uint16[]"},{"name":"buyVolumes","type":"uint128[]"},{"name":"prices","type":"uint128[]"},{"name":"tokenIdsForPrice","type":"uint16[]"}],"name":"submitSolution","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"id","type":"uint16"}],"name":"tokenIdToAddressMap","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"token","type":"address"},{"name":"amount","type":"uint256"}],"name":"requestWithdraw","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"FEE_FOR_LISTING_TOKEN_IN_OWL","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"previousPageUser","type":"address"},{"name":"pageSize","type":"uint16"}],"name":"getUsersPaginated","outputs":[{"name":"users","type":"bytes"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"token","type":"address"},{"name":"amount","type":"uint256"}],"name":"deposit","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"orderIds","type":"uint16[]"}],"name":"cancelOrders","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"AMOUNT_MINIMUM","outputs":[{"name":"","type":"uint128"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"feeToken","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"buyTokens","type":"uint16[]"},{"name":"sellTokens","type":"uint16[]"},{"name":"validFroms","type":"uint32[]"},{"name":"validUntils","type":"uint32[]"},{"name":"buyAmounts","type":"uint128[]"},{"name":"sellAmounts","type":"uint128[]"}],"name":"placeValidFromOrders","outputs":[{"name":"orderIds","type":"uint16[]"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"","type":"uint16"}],"name":"currentPrices","outputs":[{"name":"","type":"uint128"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"user","type":"address"}],"name":"getEncodedUserOrders","outputs":[{"name":"elements","type":"bytes"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"},{"name":"","type":"uint256"}],"name":"orders","outputs":[{"name":"buyToken","type":"uint16"},{"name":"sellToken","type":"uint16"},{"name":"validFrom","type":"uint32"},{"name":"validUntil","type":"uint32"},{"name":"priceNumerator","type":"uint128"},{"name":"priceDenominator","type":"uint128"},{"name":"usedAmount","type":"uint128"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"UNLIMITED_ORDER_AMOUNT","outputs":[{"name":"","type":"uint128"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"numTokens","outputs":[{"name":"","type":"uint16"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"},{"name":"","type":"address"}],"name":"lastCreditBatchId","outputs":[{"name":"","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"previousPageUser","type":"address"},{"name":"previousPageUserOffset","type":"uint16"},{"name":"pageSize","type":"uint16"}],"name":"getEncodedUsersPaginated","outputs":[{"name":"elements","type":"bytes"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"addr","type":"address"}],"name":"hasToken","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"latestSolution","outputs":[{"name":"batchId","type":"uint32"},{"name":"solutionSubmitter","type":"address"},{"name":"feeReward","type":"uint256"},{"name":"objectiveValue","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"user","type":"address"},{"name":"token","type":"address"}],"name":"getPendingDeposit","outputs":[{"name":"","type":"uint256"},{"name":"","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"cancellations","type":"uint16[]"},{"name":"buyTokens","type":"uint16[]"},{"name":"sellTokens","type":"uint16[]"},{"name":"validFroms","type":"uint32[]"},{"name":"validUntils","type":"uint32[]"},{"name":"buyAmounts","type":"uint128[]"},{"name":"sellAmounts","type":"uint128[]"}],"name":"replaceOrders","outputs":[{"name":"","type":"uint16[]"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"user","type":"address"},{"name":"token","type":"address"}],"name":"getPendingWithdraw","outputs":[{"name":"","type":"uint256"},{"name":"","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"batchId","type":"uint32"}],"name":"acceptingSolutions","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"token","type":"address"}],"name":"addToken","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"user","type":"address"},{"name":"token","type":"address"}],"name":"getBalance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"FEE_DENOMINATOR","outputs":[{"name":"","type":"uint128"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"ENCODED_AUCTION_ELEMENT_WIDTH","outputs":[{"name":"","type":"uint128"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"BATCH_TIME","outputs":[{"name":"","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getCurrentBatchId","outputs":[{"name":"","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"user","type":"address"},{"name":"offset","type":"uint16"},{"name":"pageSize","type":"uint16"}],"name":"getEncodedUserOrdersPaginated","outputs":[{"name":"elements","type":"bytes"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"addr","type":"address"}],"name":"tokenAddressToIdMap","outputs":[{"name":"","type":"uint16"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"token","type":"address"},{"name":"amount","type":"uint256"},{"name":"batchId","type":"uint32"}],"name":"requestFutureWithdraw","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"user","type":"address"},{"name":"token","type":"address"}],"name":"hasValidWithdrawRequest","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"MAX_TOKENS","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"user","type":"address"},{"name":"token","type":"address"}],"name":"withdraw","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"MAX_TOUCHED_ORDERS","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getCurrentObjectiveValue","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"inputs":[{"name":"maxTokens","type":"uint256"},{"name":"_feeToken","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"index","type":"uint16"},{"indexed":true,"name":"buyToken","type":"uint16"},{"indexed":true,"name":"sellToken","type":"uint16"},{"indexed":false,"name":"validFrom","type":"uint32"},{"indexed":false,"name":"validUntil","type":"uint32"},{"indexed":false,"name":"priceNumerator","type":"uint128"},{"indexed":false,"name":"priceDenominator","type":"uint128"}],"name":"OrderPlacement","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"name":"token","type":"address"},{"indexed":false,"name":"id","type":"uint16"}],"name":"TokenListing","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"id","type":"uint16"}],"name":"OrderCancellation","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"id","type":"uint16"}],"name":"OrderDeletion","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"orderId","type":"uint16"},{"indexed":true,"name":"sellToken","type":"uint16"},{"indexed":false,"name":"buyToken","type":"uint16"},{"indexed":false,"name":"executedSellAmount","type":"uint128"},{"indexed":false,"name":"executedBuyAmount","type":"uint128"}],"name":"Trade","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"orderId","type":"uint16"},{"indexed":true,"name":"sellToken","type":"uint16"},{"indexed":false,"name":"buyToken","type":"uint16"},{"indexed":false,"name":"executedSellAmount","type":"uint128"},{"indexed":false,"name":"executedBuyAmount","type":"uint128"}],"name":"TradeReversion","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"submitter","type":"address"},{"indexed":false,"name":"utility","type":"uint256"},{"indexed":false,"name":"disregardedUtility","type":"uint256"},{"indexed":false,"name":"burntFees","type":"uint256"},{"indexed":false,"name":"lastAuctionBurntFees","type":"uint256"},{"indexed":false,"name":"prices","type":"uint128[]"},{"indexed":false,"name":"tokenIdsForPrice","type":"uint16[]"}],"name":"SolutionSubmission","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"user","type":"address"},{"indexed":true,"name":"token","type":"address"},{"indexed":false,"name":"amount","type":"uint256"},{"indexed":false,"name":"batchId","type":"uint32"}],"name":"Deposit","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"user","type":"address"},{"indexed":true,"name":"token","type":"address"},{"indexed":false,"name":"amount","type":"uint256"},{"indexed":false,"name":"batchId","type":"uint32"}],"name":"WithdrawRequest","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"user","type":"address"},{"indexed":true,"name":"token","type":"address"},{"indexed":false,"name":"amount","type":"uint256"}],"name":"Withdraw","type":"event"}]'
)

fleet_factory_deterministic_abi = json.loads(
    '[{"constant":true,"inputs":[],"name":"proxyFactory","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"owner","type":"address"},{"name":"size","type":"uint256"},{"name":"template","type":"address"},{"name":"saltNonce","type":"uint256"}],"name":"deployFleetWithNonce","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"_proxyFactory","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"fleet","type":"address[]"}],"name":"FleetDeployed","type":"event"}]'
)
fleet_factory_abi = json.loads(
    '[{"constant":false,"inputs":[{"name":"owner","type":"address"},{"name":"size","type":"uint256"},{"name":"template","type":"address"}],"name":"deployFleet","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"proxyFactory","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"inputs":[{"name":"_proxyFactory","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":false,"name":"fleet","type":"address[]"}],"name":"FleetDeployed","type":"event"}]'
)

# GPv2Settlement
cowswap_settlement_v2_abi = [
    {
        "inputs": [
            {
                "internalType": "contract GPv2Authentication",
                "name": "authenticator_",
                "type": "address",
            },
            {"internalType": "contract IVault", "name": "vault_", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "target",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "bytes4",
                "name": "selector",
                "type": "bytes4",
            },
        ],
        "name": "Interaction",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "bytes",
                "name": "orderUid",
                "type": "bytes",
            },
        ],
        "name": "OrderInvalidated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "bytes",
                "name": "orderUid",
                "type": "bytes",
            },
            {
                "indexed": False,
                "internalType": "bool",
                "name": "signed",
                "type": "bool",
            },
        ],
        "name": "PreSignature",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "solver",
                "type": "address",
            }
        ],
        "name": "Settlement",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "contract IERC20",
                "name": "sellToken",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "contract IERC20",
                "name": "buyToken",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "sellAmount",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "buyAmount",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "feeAmount",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "bytes",
                "name": "orderUid",
                "type": "bytes",
            },
        ],
        "name": "Trade",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "authenticator",
        "outputs": [
            {
                "internalType": "contract GPv2Authentication",
                "name": "",
                "type": "address",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "domainSeparator",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
        "name": "filledAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes[]", "name": "orderUids", "type": "bytes[]"}],
        "name": "freeFilledAmountStorage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes[]", "name": "orderUids", "type": "bytes[]"}],
        "name": "freePreSignatureStorage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "offset", "type": "uint256"},
            {"internalType": "uint256", "name": "length", "type": "uint256"},
        ],
        "name": "getStorageAt",
        "outputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "orderUid", "type": "bytes"}],
        "name": "invalidateOrder",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
        "name": "preSignature",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "orderUid", "type": "bytes"},
            {"internalType": "bool", "name": "signed", "type": "bool"},
        ],
        "name": "setPreSignature",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "contract IERC20[]",
                "name": "tokens",
                "type": "address[]",
            },
            {
                "internalType": "uint256[]",
                "name": "clearingPrices",
                "type": "uint256[]",
            },
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "sellTokenIndex",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "buyTokenIndex",
                        "type": "uint256",
                    },
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "uint256",
                        "name": "sellAmount",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "buyAmount", "type": "uint256"},
                    {"internalType": "uint32", "name": "validTo", "type": "uint32"},
                    {"internalType": "bytes32", "name": "appData", "type": "bytes32"},
                    {"internalType": "uint256", "name": "feeAmount", "type": "uint256"},
                    {"internalType": "uint256", "name": "flags", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "executedAmount",
                        "type": "uint256",
                    },
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                ],
                "internalType": "struct GPv2Trade.Data[]",
                "name": "trades",
                "type": "tuple[]",
            },
            {
                "components": [
                    {"internalType": "address", "name": "target", "type": "address"},
                    {"internalType": "uint256", "name": "value", "type": "uint256"},
                    {"internalType": "bytes", "name": "callData", "type": "bytes"},
                ],
                "internalType": "struct GPv2Interaction.Data[][3]",
                "name": "interactions",
                "type": "tuple[][3]",
            },
        ],
        "name": "settle",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "targetContract", "type": "address"},
            {"internalType": "bytes", "name": "calldataPayload", "type": "bytes"},
        ],
        "name": "simulateDelegatecall",
        "outputs": [{"internalType": "bytes", "name": "response", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "targetContract", "type": "address"},
            {"internalType": "bytes", "name": "calldataPayload", "type": "bytes"},
        ],
        "name": "simulateDelegatecallInternal",
        "outputs": [{"internalType": "bytes", "name": "response", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                    {
                        "internalType": "uint256",
                        "name": "assetInIndex",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "assetOutIndex",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "bytes", "name": "userData", "type": "bytes"},
                ],
                "internalType": "struct IVault.BatchSwapStep[]",
                "name": "swaps",
                "type": "tuple[]",
            },
            {
                "internalType": "contract IERC20[]",
                "name": "tokens",
                "type": "address[]",
            },
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "sellTokenIndex",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "buyTokenIndex",
                        "type": "uint256",
                    },
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "uint256",
                        "name": "sellAmount",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "buyAmount", "type": "uint256"},
                    {"internalType": "uint32", "name": "validTo", "type": "uint32"},
                    {"internalType": "bytes32", "name": "appData", "type": "bytes32"},
                    {"internalType": "uint256", "name": "feeAmount", "type": "uint256"},
                    {"internalType": "uint256", "name": "flags", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "executedAmount",
                        "type": "uint256",
                    },
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                ],
                "internalType": "struct GPv2Trade.Data",
                "name": "trade",
                "type": "tuple",
            },
        ],
        "name": "swap",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "vault",
        "outputs": [{"internalType": "contract IVault", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "vaultRelayer",
        "outputs": [
            {"internalType": "contract GPv2VaultRelayer", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {"stateMutability": "payable", "type": "receive"},
]

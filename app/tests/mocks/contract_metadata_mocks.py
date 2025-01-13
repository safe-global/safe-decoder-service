from safe_eth.eth.clients import ContractMetadata

etherscan_metadata_mock = ContractMetadata(
    "Etherscan Uxio Contract",
    [
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "etherscanParam",
                    "type": "address",
                }
            ],
            "name": "AddedOwner",
            "type": "event",
        },
        {
            "constant": False,
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_masterCopy",
                    "type": "address",
                }
            ],
            "name": "changeMasterCopy",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"internalType": "uint256", "name": "_threshold", "type": "uint256"}
            ],
            "name": "changeThreshold",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
    False,
)

etherscan_proxy_metadata_mock = ContractMetadata(
    "Etherscan Uxio Proxy Contract",
    [
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "etherscanParam",
                    "type": "address",
                }
            ],
            "name": "AddedOwner",
            "type": "event",
        },
        {
            "constant": False,
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_masterCopy",
                    "type": "address",
                }
            ],
            "name": "changeMasterCopy",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"internalType": "uint256", "name": "_threshold", "type": "uint256"}
            ],
            "name": "changeThreshold",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
    False,
    "0x43506849D7C04F9138D1A2050bbF3A0c054402dd",
)

sourcify_metadata_mock = ContractMetadata(
    "Sourcify Uxio Contract",
    [
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "sourcifyParam",
                    "type": "address",
                }
            ],
            "name": "AddedOwner",
            "type": "event",
        },
        {
            "constant": False,
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_masterCopy",
                    "type": "address",
                }
            ],
            "name": "changeMasterCopy",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"internalType": "uint256", "name": "_threshold", "type": "uint256"}
            ],
            "name": "changeThreshold",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
    True,
)

blockscout_metadata_mock = ContractMetadata(
    "Blockscout Moises Contract",
    [
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "blockscoutParam",
                    "type": "address",
                }
            ],
            "name": "AddedOwner",
            "type": "event",
        },
        {
            "constant": False,
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_masterCopy",
                    "type": "address",
                }
            ],
            "name": "changeMasterCopy",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"internalType": "uint256", "name": "_threshold", "type": "uint256"}
            ],
            "name": "changeThreshold",
            "outputs": [],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
    False,
)

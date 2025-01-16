from typing import Sequence, cast

from safe_eth.eth.contracts import (
    get_erc20_contract,
    get_erc721_contract,
    get_kyber_network_proxy_contract,
    get_multi_send_contract,
    get_safe_to_l2_migration_contract,
    get_safe_V0_0_1_contract,
    get_safe_V1_0_0_contract,
    get_safe_V1_1_1_contract,
    get_safe_V1_3_0_contract,
    get_safe_V1_4_1_contract,
    get_uniswap_exchange_contract,
)
from sqlmodel.ext.asyncio.session import AsyncSession
from web3 import Web3
from web3.types import ABIEvent, ABIFunction

from app.datasources.abis.aave import (
    aave_a_token,
    aave_lending_pool,
    aave_lending_pool_addresses_provider,
    aave_lending_pool_core,
)
from app.datasources.abis.admin_upgradeability_proxy import (
    initializable_admin_upgradeability_proxy_abi,
)
from app.datasources.abis.balancer import balancer_bactions, balancer_exchange_proxy
from app.datasources.abis.chainlink import chainlink_token_abi
from app.datasources.abis.compound import comptroller_abi, ctoken_abi
from app.datasources.abis.gnosis_protocol import (
    fleet_factory_abi,
    fleet_factory_deterministic_abi,
    gnosis_protocol_abi,
)
from app.datasources.abis.idle import idle_token_v3
from app.datasources.abis.maker_dao import maker_dao_abis
from app.datasources.abis.open_zeppelin import (
    open_zeppelin_admin_upgradeability_proxy,
    open_zeppelin_proxy_admin,
)
from app.datasources.abis.request import (
    request_erc20_proxy,
    request_erc20_swap_to_pay,
    request_ethereum_proxy,
)
from app.datasources.abis.sablier import (
    sablier_abi,
    sablier_ctoken_manager,
    sablier_payroll,
)
from app.datasources.abis.safe import safe_allowance_module_abi
from app.datasources.abis.sight import (
    conditional_token_abi,
    market_maker_abi,
    market_maker_factory_abi,
)
from app.datasources.abis.snapshot import snapshot_delegate_registry_abi
from app.datasources.abis.timelock import timelock_abi
from app.datasources.db.models import Abi, AbiSource


class AbiService:

    def __init__(self):
        self.dummy_w3 = Web3()

    @staticmethod
    async def _store_abis_in_database(
        session: AsyncSession,
        abi_jsons: list[Sequence[ABIFunction | ABIEvent]],
        relevance: int,
        abi_source: AbiSource,
    ) -> None:
        for abi_json in abi_jsons:
            abi = await Abi.get_abi(session, cast(list[dict], abi_json))
            if abi is None:
                await Abi(
                    abi_json=abi_json, source_id=abi_source.id, relevance=relevance
                ).create(session)

    async def load_local_abis_in_database(self, session: AsyncSession) -> None:
        abi_source, _ = await AbiSource.get_or_create(
            session, "localstorage", "decoder-service"
        )
        await self._store_abis_in_database(
            session, self.get_safe_contracts_abis(), 100, abi_source
        )
        await self._store_abis_in_database(
            session, self.get_erc_abis() + self.get_safe_abis(), 90, abi_source
        )
        await self._store_abis_in_database(
            session, self.get_third_parties_abis(), 50, abi_source
        )

    def get_safe_contracts_abis(self) -> list[Sequence[ABIFunction | ABIEvent]]:
        return [
            get_safe_V0_0_1_contract(self.dummy_w3).abi,
            get_safe_V1_0_0_contract(self.dummy_w3).abi,
            get_safe_V1_1_1_contract(self.dummy_w3).abi,
            get_safe_V1_3_0_contract(self.dummy_w3).abi,
            get_safe_V1_4_1_contract(self.dummy_w3).abi,
        ]

    def get_safe_abis(self) -> list[Sequence[ABIFunction | ABIEvent]]:
        return [
            get_multi_send_contract(self.dummy_w3).abi,
            get_safe_to_l2_migration_contract(self.dummy_w3).abi,
            safe_allowance_module_abi,
        ]

    def get_erc_abis(self) -> list[Sequence[ABIFunction | ABIEvent]]:
        return [
            get_erc721_contract(self.dummy_w3).abi,
            get_erc20_contract(self.dummy_w3).abi,
        ]

    def get_third_parties_abis(self) -> list[Sequence[ABIFunction | ABIEvent]]:
        aave_contracts = [
            aave_a_token,
            aave_lending_pool,
            aave_lending_pool_addresses_provider,
            aave_lending_pool_core,
        ]
        balancer_contracts = [balancer_bactions, balancer_exchange_proxy]
        chainlink_contracts = [chainlink_token_abi]
        compound_contracts = [ctoken_abi, comptroller_abi]
        exchanges = [
            get_uniswap_exchange_contract(self.dummy_w3).abi,
            get_kyber_network_proxy_contract(self.dummy_w3).abi,
        ]
        gnosis_protocol = [
            gnosis_protocol_abi,
            fleet_factory_deterministic_abi,
            fleet_factory_abi,
        ]
        idle_contracts = [idle_token_v3]
        initializable_admin_upgradeability_proxy_contracts = [
            initializable_admin_upgradeability_proxy_abi
        ]
        maker_dao_contracts = maker_dao_abis
        open_zeppelin_contracts = [
            open_zeppelin_admin_upgradeability_proxy,
            open_zeppelin_proxy_admin,
        ]
        request_contracts = [
            request_erc20_proxy,
            request_erc20_swap_to_pay,
            request_ethereum_proxy,
        ]
        sablier_contracts = [sablier_ctoken_manager, sablier_payroll, sablier_abi]
        sight_contracts = [
            conditional_token_abi,
            market_maker_abi,
            market_maker_factory_abi,
        ]
        snapshot_contracts = [snapshot_delegate_registry_abi]
        timelock_contracts = [timelock_abi]

        return (
            aave_contracts
            + balancer_contracts
            + chainlink_contracts
            + compound_contracts
            + exchanges
            + gnosis_protocol
            + idle_contracts
            + initializable_admin_upgradeability_proxy_contracts
            + maker_dao_contracts
            + open_zeppelin_contracts
            + request_contracts
            + sablier_contracts
            + sight_contracts
            + snapshot_contracts
            + timelock_contracts
        )

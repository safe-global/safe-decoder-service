from ...services.data_decoder import DataDecoderService
from ..db.db_async_conn import DbAsyncConn


class TestDataDecoderService(DbAsyncConn):
    async def test_init(self):
        d = DataDecoderService()
        await d.init()
        assert d.fn_selectors_with_abis == {}

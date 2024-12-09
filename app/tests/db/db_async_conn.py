import unittest

from sqlmodel import SQLModel

from app.datasources.db.database import engine


class DbAsyncConn(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = engine
        # Create the database tables
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def asyncTearDown(self):
        """
        Clean data between tests

        :return:
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

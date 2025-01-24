import unittest

from sqlmodel import SQLModel

from app.datasources.db.database import get_engine


class DbAsyncConn(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = get_engine()
        # Create the database tables
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

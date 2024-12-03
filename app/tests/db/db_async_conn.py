import unittest

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import engine


class DbAsyncConn(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = engine

        # Create the database tables
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

        # Creating a session for test
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        self.session = async_session()

    async def asyncTearDown(self):
        await self.session.close()

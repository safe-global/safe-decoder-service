from factory.alchemy import SQLAlchemyModelFactory
from sqlmodel import Session

from app.datasources.db.models import Chain


class ChainFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Chain
        sqlalchemy_session_factory = Session
        sqlalchemy_session_persistence = "commit"

from pydantic import BaseModel


class About(BaseModel):
    version: str

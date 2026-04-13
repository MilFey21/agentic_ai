from sqlalchemy.orm import DeclarativeBase

from src.database import metadata


class Base(DeclarativeBase):
    metadata = metadata

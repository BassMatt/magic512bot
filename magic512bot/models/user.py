from typing import List

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import JSONType

from .base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(
        BigInteger(), nullable=False, primary_key=True
    )  # discord user id
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sweat_roles: Mapped[List[str]] = mapped_column(JSONType, nullable=False)

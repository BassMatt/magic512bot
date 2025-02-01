from typing import List

from sqlalchemy import ARRAY, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(
        BigInteger(), nullable=False, primary_key=True
    )  # discord user id
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    roles: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)

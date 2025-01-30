from typing import List

from database import Base
from sqlalchemy import ARRAY, BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer(), nullable=False, primary_key=True)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger(), nullable=False
    )  # discord user id
    sweat_roles: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)

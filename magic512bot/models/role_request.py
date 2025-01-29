from sqlalchemy import Integer, String, ARRAY, BigInteger
from sqlalchemy.orm import mapped_column, Mapped
from typing import List
from database import Base

class Users(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer(), nullable=False, primary_key=True)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False) # discord user id
    roles: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
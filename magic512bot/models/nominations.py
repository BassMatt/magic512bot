from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Nominations(Base):
    __tablename__ = "nominations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )  # Auto-incrementing primary key
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Discord user ID
    format: Mapped[str] = mapped_column(String(55), nullable=False)  # Format nomination

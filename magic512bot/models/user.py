from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import JSONType

from magic512bot.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )  # discord user id
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sweat_roles: Mapped[list[str]] = mapped_column(JSONType, nullable=False)

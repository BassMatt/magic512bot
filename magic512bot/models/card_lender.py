from sqlalchemy import Integer, String, DateTime, BigInteger
from sqlalchemy.orm import mapped_column, Mapped
import datetime
from database import Base


class CardLoan(Base):
    __tablename__ = 'card_loans'
    id: Mapped[int] = mapped_column(
        Integer(), nullable=False, primary_key=True)
    # for now, just have cards as names
    card: Mapped[str] = mapped_column(String(100), nullable=False)
    lender: Mapped[int] = mapped_column(
        BigInteger(), nullable=False)  # discord user id of lender
    borrower: Mapped[int] = mapped_column(
        BigInteger(), nullable=False)  # discord user id of borrower
    borrower_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(), nullable=False)
    # order tag, if not specified defaults to ""
    order_tag: Mapped[str] = mapped_column(String(100), nullable=False)

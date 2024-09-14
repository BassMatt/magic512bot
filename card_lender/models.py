from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
import datetime

class Base(DeclarativeBase):
    pass

class CardLoan(Base):
    __tablename__ = 'card_loans'
    id: Mapped[int] = mapped_column(Integer(), nullable=False, primary_key=True)
    card: Mapped[str] = mapped_column(String(100), nullable=False) # for now, just have cards as names
    lender: Mapped[int] = mapped_column(Integer(), nullable=False) # discord user id of lender
    borrower: Mapped[int] = mapped_column(Integer(), nullable=False) # discord user id of borrower
    borrower_name: Mapped[String] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(), nullable=False)
    order_tag: Mapped[str] = mapped_column(String(100), nullable=False) # order tag, if not specified defaults to ""
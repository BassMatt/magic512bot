from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, mapped_column

class Base(DeclarativeBase):
    pass

# class Card(Base):
#    __tablename__ = 'cards'
#    id = mapped_column(Integer(), primary_key=True)

class CardLoan(Base):
    __tablename__ = 'card_loans'
    id = mapped_column(Integer(), nullable=False, primary_key=True)
    card = mapped_column(String(100), nullable=False) # for now, just have cards as names
    lender = mapped_column(Integer(), nullable=False) # discord user id of lender
    borrower = mapped_column(Integer(), nullable=False) # discord user id of borrower
    order_tag = mapped_column(String(100), nullable=True) # optional order tag

# class Member(Base):
#     id = mapped_column(String(100), primary_key=True)
#     borrowed_cards = mapped_column()
#     loaned_cards = mapped_column()

import requests
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select, delete
from dotenv import load_dotenv
import os
from models import CardLoan
from typing import Optional
from util import parse_cardlist
import datetime

load_dotenv()
engine=create_engine(os.getenv("DB_CONNECTION_STRING"))
Session = sessionmaker(engine)

def insert_cardloans(cards: list[str], borrower: int, lender: int, order_tag: str = ""):
    """
    Upserts Loan Objects into database based on if (Card Name + Tag) is already present
    """
    card_loans = []
    for quantity, card_name in parse_cardlist(cards):
        card_loans.append(CardLoan(
            created_at = datetime.datetime.now(),
            card = card_name,
            quantity = quantity,
            lender = lender,
            borrower = borrower,
            order_tag = order_tag
        ))
    
    with Session.begin() as session:
        session.add_all(card_loans)

def bulk_delete_cardloans(lender: int, borrower: Optional[int], tag: Optional[str]):
    """
    Removes rows from card_loans table for a given lender
    based on if they match either of the two given parameters

    If no borrower / tag is specified, deletes all rows for a given lender.
    """
    pass

def delete_cardloans(lender: int, borrower: int, tag: Optional[str], card_list: list[str]) -> list[str]:
    """
    Removes rows from card_loans table for a given lender if they
    match all the provided parameters and are in the specified list of
    card names

    Returns list[str] of card_names unable to be found / deleted in the provided card_names list.
    """

    for quantity, card_name in parse_cardlist(card_list):
        pass


    pass

def get_cardloans(lender: int, borrower: int, tag: Optional[str]) -> list[CardLoan]:
    """
    Returns a list of CardLoan objects that match the given parameters
    """

    statement = select(CardLoan).where(CardLoan.lender == lender, CardLoan.borrower == borrower)
    if tag:
        statement = statement.where(CardLoan.order_tag == tag)

    with Session() as session:
        result = session.scalars(statement).all()
        return result

def bulk_get_cardloans(lender: int):
    """
    Returns the list of all CardLoan objects for a given lender 
    """
    with Session.begin() as session:
        statement = select(CardLoan).filter_by(lender=lender)
        return session.scalars(statement).all()


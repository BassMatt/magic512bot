import requests
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select
from dotenv import load_dotenv
import os
from models import Base, CardLoan
from typing import Optional
from util import parse_cardlist

load_dotenv()
engine=create_engine(os.getenv("DB_CONNECTION_STRING"))
Session = sessionmaker(engine)

def download_oracle_cards():
    resp = requests.get("https://api.scryfall.com/bulk-data")
    if "data" not in resp.json():
        print("Unable to retrieve scryfall bulk-data links")
        return None
    
    for item in resp.json()["data"]:
        if item["type"] == "oracle-cards":
            oracle_url = item["download_url"]
            with requests.get(oracle_url, stream=True) as response:
                with open("ORACLE_CARDS.json", mode="wb") as file:
                    for chunk in response.iter_content(chunk_size=10 * 1024):
                        file.write(chunk)

def update_remote_db():
    # check if oracle card db is downloaded locally
    # upload to remote database
    return

def insert_cardloans(cards: list[str], borrower: int, lender: int, order_tag: str = ""):
    """
    Creates and inserts CardLoan objects into database with specified variables
    """
    card_loans = []
    for card_name in parse_cardlist(cards):
        card_loans.append(CardLoan(
            card = card_name,
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

def delete_cardloans(lender: int, borrower: int, tag: Optional[str], card_names: list[str]) -> list[str]:
    """
    Removes rows from card_loans table for a given lender if they
    match all the provided parameters and are in the specified list of
    card names

    Returns list[str] of card_names unable to be found / deleted in the provided card_names list.
    """
    pass

def get_cardloans(lender: int, borrower: Optional[int], tag: Optional[str]) -> list[CardLoan]:
    """
    Returns a list of CardLoan objects that match the given parameters
    """
    pass

def bulk_get_cardloans(lender: int):
    """
    Returns the list of all CardLoan objects for a given lender 
    """
    with Session.begin() as session:
        statement = select(CardLoan).filter_by(lender=lender)
        return session.scalars(statement).all()

def create_tables():
    # creates tables in DB based on ORM Mapped Classes
    Base.metadata.create_all(engine)
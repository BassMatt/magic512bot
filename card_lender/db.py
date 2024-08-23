import requests
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from models import Base, CardLoan


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

def insert_cardloans(cards: list[CardLoan]):
    with Session.begin() as session:
        session.add_all(cards)

def create_tables():
    # creates tables in DB based on ORM Mapped Classes
    Base.metadata.create_all(engine)
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, delete
from dotenv import load_dotenv
from models import Base, CardLoan
import requests

load_dotenv()
engine=create_engine("sqlite:///../db1.db")
Session = sessionmaker(engine)

def create_tables():
    # creates tables in DB based on ORM Mapped Classes
    Base.metadata.create_all(engine)

def delete_cardloans():
    with Session.begin() as session:
        statement = delete(CardLoan)
        result = session.execute(statement)
        print(result.rowcount)

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


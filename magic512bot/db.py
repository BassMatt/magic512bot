from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select, delete, inspect
from dotenv import load_dotenv
from models import CardLoan, Base
from util import parse_cardlist
import datetime
from errors import CardNotFoundError

class PostgresStore:
    def __init__(self, conn_string: str):
        load_dotenv()
        self.engine=create_engine(conn_string)
        self.Session = sessionmaker(self.engine)

        # create table if doesn't exist
        ins = inspect(self.engine)
        if not ins.has_table("card_loans"):
            self.create_tables()

    def insert_cardloans(self, card_list: list[str], lender: int, borrower: int, borrower_name: str, tag: str = "") -> int:
        """
        Upserts Loan Objects into database based on if (Card Name + Tag) is already present

        Returns int, number of cards added
        """
        card_loans = []
        cards_added = 0
        for card_name, quantity in parse_cardlist(card_list).items():
            card_loans.append(CardLoan(
                created_at = datetime.datetime.now(),
                card = card_name,
                quantity = quantity,
                lender = lender,
                borrower = borrower,
                borrower_name = borrower_name,
                order_tag = tag 
            ))

        cards_added = sum(card.quantity for card in card_loans) 
        with self.Session.begin() as session:
            session.add_all(card_loans)
        
        return cards_added

    def bulk_return_cardloans(self, lender: int, borrower: int, tag: str = "") -> int:
        """
        Removes rows from card_loans table for a given lender
        based on if they match either of the two given parameters

        If no borrower / tag is specified, deletes all rows for a given lender.
        """
        affected_row_count = 0
        with self.Session.begin() as session:
            stmt = delete(CardLoan).where(
                CardLoan.lender == lender,
                CardLoan.borrower == borrower)
            if tag:
                stmt.where(CardLoan.order_tag == tag)
            
            affected_row_count = len(session.execute(stmt).fetchall())
        return affected_row_count

    def return_cardloans(self, card_list: list[str], lender: int, borrower: int, tag: str) -> int:
        """
        Decrements quantity for each given card in card_list matching given parameters. If
        multiple rows are returned for a given card, decrements earliest matching rows first.

        Deletes card from CardLoan table if cards's quantity would become 0.

        Throws CardNotFoundError if card not found in loans table, or quantity would become < 0.

        Returns int, the number of cards successfully returned.
        """
        loans_to_return = parse_cardlist(card_list)
        not_found_errors = []
        total_return_count = 0

        with self.Session.begin() as session:
            for card_name, quantity_to_return in loans_to_return.items():
                card_query_stmt = select(CardLoan).where(
                    CardLoan.card == card_name,
                    CardLoan.lender == lender,
                    CardLoan.borrower == borrower)
                if tag:
                    card_query_stmt = card_query_stmt.where(CardLoan.order_tag == tag)
                
                result = session.scalars(card_query_stmt.order_by(CardLoan.created_at)).all()
                total_loaned_count = sum(card_loan.quantity for card_loan in result)

                if total_loaned_count < quantity_to_return:
                    not_found_errors.append((card_name, quantity_to_return))
                    continue

                for card_loan in result:
                    if card_loan.quantity < quantity_to_return:
                        total_return_count += card_loan.quantity
                        quantity_to_return -= card_loan.quantity
                        session.delete(card_loan)
                    else:
                        card_loan.quantity -= quantity_to_return
                        total_return_count += quantity_to_return
                        break
                
            if len(not_found_errors) > 0:
                raise CardNotFoundError(card_errors=not_found_errors)

            return total_return_count 

    def get_cardloans(self, lender: int, borrower: int, tag: str) -> list[CardLoan]:
        """
        Returns a list of CardLoan objects that match the given parameters
        """

        statement = select(CardLoan).where(CardLoan.lender == lender, CardLoan.borrower == borrower)
        if tag:
            statement = statement.where(CardLoan.order_tag == tag)

        with self.Session.begin() as session:
            result = session.scalars(statement).all()
            session.expunge_all()
            return result

    def bulk_get_cardloans(self, lender: int):
        """
        Returns the list of all CardLoan objects for a given lender 
        """
        with self.Session.begin() as session:
            statement = select(CardLoan).where(CardLoan.lender == lender)
            result = session.scalars(statement).all()
            session.expunge_all()
            return result

    def create_tables(self):
        # creates tables in DB based on ORM Mapped Classes
        Base.metadata.create_all(self.engine)

    def delete_all_cardloans(self):
        with self.Session.begin() as session:
            statement = delete(CardLoan)
            result = session.execute(statement)
            print(result.rowcount)
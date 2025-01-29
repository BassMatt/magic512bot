import datetime
from collections import Counter
from typing import Sequence

from errors import CardListInputError, CardNotFoundError
from models.card_lender import CardLoan
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from table2ascii import Alignment, PresetStyle, table2ascii


def insert_cardloans(
    session: Session,
    card_list: list[str],
    lender: int,
    borrower: int,
    borrower_name: str,
    tag: str = "",
) -> int:
    """
    Upserts Loan Objects into database based on if (Card Name + Tag) is already present

    Returns int, number of cards added
    """
    card_loans = []
    cards_added = 0
    for card_name, quantity in parse_cardlist(card_list).items():
        card_loans.append(
            CardLoan(
                created_at=datetime.datetime.now(),
                card=card_name,
                quantity=quantity,
                lender=lender,
                borrower=borrower,
                borrower_name=borrower_name,
                order_tag=tag,
            )
        )

    cards_added = sum(card.quantity for card in card_loans)
    session.add_all(card_loans)
    return cards_added


def bulk_return_cardloans(
    session: Session, lender: int, borrower: int, tag: str = ""
) -> int:
    """
    Removes rows from card_loans table for a given lender
    based on if they match either of the two given parameters

    If no borrower / tag is specified, deletes all rows for a given lender.
    """
    affected_row_count = 0
    stmt = delete(CardLoan).where(
        CardLoan.lender == lender, CardLoan.borrower == borrower
    )
    if tag:
        stmt.where(CardLoan.order_tag == tag)

    affected_row_count = len(session.execute(stmt).fetchall())
    return affected_row_count


def return_cardloans(
    session: Session, card_list: list[str], lender: int, borrower: int, tag: str
) -> int:
    """
    Decrements quantity for each given card in card_list matching given
    parameters. If multiple rows are returned for a given card, decrements
    earliest matching rows first.

    Deletes card from CardLoan table if cards's quantity would become 0.

    Throws CardNotFoundError if card not found in loans table, or quantity would
    become < 0.

    Returns int, the number of cards successfully returned.
    """
    loans_to_return = parse_cardlist(card_list)
    not_found_errors = []
    total_return_count = 0

    for card_name, quantity_to_return in loans_to_return.items():
        card_query_stmt = select(CardLoan).where(
            CardLoan.card == card_name,
            CardLoan.lender == lender,
            CardLoan.borrower == borrower,
        )
        if tag:
            card_query_stmt = card_query_stmt.where(CardLoan.order_tag == tag)

        result: Sequence[CardLoan] = session.scalars(
            card_query_stmt.order_by(CardLoan.created_at)
        ).all()
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


def get_cardloans(
    session: Session, lender: int, borrower: int, tag: str
) -> list[CardLoan]:
    """
    Returns a list of CardLoan objects that match the given parameters
    """

    statement = select(CardLoan).where(
        CardLoan.lender == lender, CardLoan.borrower == borrower
    )
    if tag:
        statement = statement.where(CardLoan.order_tag == tag)

    result = session.scalars(statement).all()
    return list(result)


def bulk_get_cardloans(session: Session, lender: int):
    """
    Returns the list of all CardLoan objects for a given lender
    """
    statement = select(CardLoan).where(CardLoan.lender == lender)
    result = session.scalars(statement).all()
    return list(result)


def delete_all_cardloans(session: Session):
    session.execute(delete(CardLoan))


def parse_cardlist(cardlist: list[str]) -> dict[str, int]:
    """
    Parses and validates provided cardlist is in MTGO format and contains valid
    cardnames.

    Returns: Dictionary that maps CardName -> Quantity
    """
    line_errors = []
    loans = Counter()
    for line in cardlist:
        split = line.split(" ", 1)

        if len(split) != 2:
            line_errors.append(line)
            continue

        if not split[0].isdigit():
            line_errors.append(line)
            continue

        quantity, card_name = int(split[0]), split[1]
        # TODO: Check if card_name is valid card here

        loans[card_name] += quantity

    if len(line_errors) > 0:
        raise CardListInputError(line_errors)
    else:
        return loans


def format_loanlist_output(cards: list[CardLoan]):
    """
    Returns ASCII Table representation of card loan data
    """
    cards = sorted(cards, key=lambda card: (card.order_tag, card.card, card.created_at))
    body = [
        [card.card, card.quantity, card.order_tag, card.created_at.strftime("%m/%d/%Y")]
        for card in cards
    ]

    output = table2ascii(
        header=["Name", "Quantity", "Tag", "Date"],
        body=body,
        column_widths=[30, 10, 10, 12],
        style=PresetStyle.borderless,
        alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.LEFT, Alignment.LEFT],
    )

    return output


def format_bulk_loanlist_output(cards: list[CardLoan]):

    bulk_list = []
    bulk_card_counts = {}
    for card in cards:
        if card.borrower_name not in bulk_card_counts:
            bulk_card_counts[card.borrower_name] = Counter()
        # if an empty tag, want to write out "<empty>" instead
        tag = "<empty>" if not card.order_tag else card.order_tag
        bulk_card_counts[card.borrower_name][card.order_tag] += card.quantity

    for borrower in bulk_card_counts.keys():
        for tag, card_count in bulk_card_counts[borrower].items():
            bulk_list.append([borrower, tag, card_count])

    output = table2ascii(
        header=["Borrower", "Tag", "Count"],
        body=sorted(bulk_list, key=lambda row: (row[1], row[2])),
        column_widths=[25, 10, 10],
        style=PresetStyle.borderless,
        alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.LEFT],
    )

    return output

from errors import LoanListInputError
from models import CardLoan

def parse_loanlist(loanlist: list[str]):
    """
    loanlist; list of strings in the form of "1 Ketria Triome"

    Parses the text input from loanlist modal to ensure data is in proper format.
    """
    line_errors = []
    cards_to_add = []
    for line in loanlist:
        split = line.split(" ", 1)

        if len(split) != 2:
            line_errors.append(line)
            continue

        if not split[0].isdigit():
            line_errors.append(line)
            continue
        
        quantity, card_name = int(split[0]), split[1]
        # TODO: Check if card_name is valid card here

        for _ in range(quantity):
            cards_to_add.append(card_name)
    
    if len(line_errors) > 0:
        raise LoanListInputError(line_errors)
    else:
        return cards_to_add

def create_loan(loanlist: list[str], lender: int, borrower: int, order_tag: str = ""):
    """
    loanlist: list of cards in MTGO Format

    Creates Loan() objects for each valid card given in LoanLists.
    """
    card_loans = []
    for card_name in parse_loanlist(loanlist):
        card_loans.append(CardLoan(
            card = card_name,
            lender = lender,
            borrower = borrower,
            order_tag = order_tag
        ))
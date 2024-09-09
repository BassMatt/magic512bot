from errors import CardListInputError
from models import CardLoan

def parse_cardlist(cardlist: list[str]) -> list[(int, str)]:
    """
    Parses and validates provided cardlist is in MTGO format and contains valid cardnames.

    Returns:  Card names in list, expanded for each of the given quantity.
    """
    line_errors = []
    loans = []
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

        loans.append((quantity, card_name))
    
    if len(line_errors) > 0:
        raise CardListInputError(line_errors)
    else:
        return loans 

def format_loanlist_output(cards: list[CardLoan]):
    """
    Returns ASCII Table representation of card loan data
    """
    output = ""

    header_row = ["Count", "Name", "Tag", "Date"]
    col_widths = [5, 30, 10, 10]

    output += "|".join(value.ljust(col_widths[i]) for i, value in enumerate(header_row)) + "\n"
    output += "|".join("-" * col_widths[i] for i in range(len(header_row))) + "\n"

    cards = sorted(cards, key=lambda card: (card.order_tag, card.card, card.created_at))

    for card in cards:
        card_data = [str(card.quantity), card.card, card.order_tag, card.created_at.strftime("%m/%d/%Y")]
        output += "|".join(value.ljust(col_widths[i]) for i, value in enumerate(card_data)) + "\n"
    
    return output
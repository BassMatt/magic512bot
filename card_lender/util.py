from errors import CardListInputError
from models import CardLoan
from collections import Counter
from table2ascii import table2ascii, Alignment, PresetStyle

def parse_cardlist(cardlist: list[str]) -> dict[str, int]:
    """
    Parses and validates provided cardlist is in MTGO format and contains valid cardnames.

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
    body = [[card.card, card.quantity, card.order_tag, card.created_at.strftime("%m/%d/%Y")] for card in cards]

    output = table2ascii(
        header = ["Name", "Quantity", "Tag", "Date"],
        body = body,
        column_widths = [30, 10, 10, 12],
        style = PresetStyle.thin_compact,
        alignments = [Alignment.LEFT, Alignment.LEFT, Alignment.LEFT, Alignment.LEFT]
    )

    return output

def format_bulk_loanlist_output(cards: list[CardLoan]):

    bulk_list = []
    bulk_card_counts = {}
    for card in cards:
        if not card.borrower_name in bulk_card_counts:
            bulk_card_counts[card.borrower_name] = Counter()
        # if an empty tag, want to write out "<empty>" instead
        tag = "<empty>" if not card.order_tag else card.order_tag
        bulk_card_counts[card.borrower_name][card.order_tag] += card.quantity

    for borrower in bulk_card_counts.keys():
        for tag, card_count in bulk_card_counts[borrower].items():
            bulk_list.append(
                [borrower, tag, card_count]
            )

    output = table2ascii(
        header = ["Borrower", "Tag", "Count"],
        body = sorted(bulk_list, key=lambda row: (row[1], row[2])),
        column_widths = [25, 10, 10],
        style = PresetStyle.thin_compact,
        alignments = [Alignment.LEFT, Alignment.LEFT, Alignment.LEFT]
    )

    return output
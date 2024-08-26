from errors import CardListInputError
from db import insert_cardloans

def parse_cardlist(cardlist: list[str]) -> list[str]:
    """
    Parses and validates provided cardlist is in MTGO format and contains valid cardnames.

    Returns:  Card names in list, expanded for each of the given quantity.
    """
    line_errors = []
    cards = []
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

        for _ in range(quantity):
            cards.append(card_name)
    
    if len(line_errors) > 0:
        raise CardListInputError(line_errors)
    else:
        return cards 
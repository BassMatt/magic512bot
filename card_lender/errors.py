class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class CardListInputError(Error):
    """Exception raised for errors in the LoanList Modal TextInput.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, line_errors):
        self.line_errors = line_errors

    def __str__(self):
        message = f"error parsing provided CardList\n\n Please ensure all lines follow the format of `<integer> <cardname>`.\n\n The following lines raised errors:\n"
        for line in "\n".join(self.line_errors):
            message += line
        return message
    
class CardNotFoundError(Error):
    """
    Exception raised when unable to find cards in database to return.
    """
    def __str__(self):
        message = f"unable to find card(s) in database. Please ensure all cards in cardlist match a given loan."
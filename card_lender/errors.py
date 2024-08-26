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
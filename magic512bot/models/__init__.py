from .cardloan import CardLoan
from .user import User


def register_models():
    return [User, CardLoan]

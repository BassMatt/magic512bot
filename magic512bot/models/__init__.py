from .cardloan import CardLoan
from .nomination import Nomination
from .user import User


def register_models() -> list:
    return [User, CardLoan, Nomination]

import pytest

from magic512bot.models import register_models
from magic512bot.models.base import Base
from magic512bot.models.cardloan import CardLoan
from magic512bot.models.user import User


def test_register_models():
    """Test that models are registered correctly."""
    models = register_models()
    assert User in models
    assert CardLoan in models


def test_base_metadata():
    """Test that the Base metadata contains our models."""
    register_models()
    tables = Base.metadata.tables
    assert "users" in tables
    assert "card_loans" in tables


@pytest.mark.parametrize(
    "model,expected_columns",
    [
        (User, ["id", "user_name", "sweat_roles"]),
        (
            CardLoan,
            [
                "id",
                "card",
                "lender",
                "borrower",
                "borrower_name",
                "quantity",
                "created_at",
                "order_tag",
            ],
        ),
    ],
)
def test_model_columns(model, expected_columns):
    """Test that models have the expected columns."""
    # Get the column names from the model
    columns = [column.name for column in model.__table__.columns]

    # Verify all expected columns are present
    for column in expected_columns:
        assert column in columns

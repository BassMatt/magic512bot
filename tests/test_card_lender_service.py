import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from magic512bot.errors import CardListInputError, CardNotFoundError
from magic512bot.models.cardloan import CardLoan
from magic512bot.services.card_lender import (
    bulk_get_cardloans,
    bulk_return_cardloans,
    format_bulk_loanlist_output,
    format_loanlist_output,
    get_cardloans,
    insert_cardloans,
    parse_cardlist,
    return_cardloans,
)


def test_parse_cardlist_valid():
    """Test parsing a valid card list."""
    card_list = ["2 Test Card 1", "3 Test Card 2"]
    result = parse_cardlist(card_list)

    assert result["Test Card 1"] == 2
    assert result["Test Card 2"] == 3


def test_parse_cardlist_invalid_format():
    """Test parsing a card list with invalid format."""
    card_list = ["Invalid Format", "2 Test Card"]

    with pytest.raises(CardListInputError):
        parse_cardlist(card_list)


def test_parse_cardlist_invalid_quantity():
    """Test parsing a card list with invalid quantity."""
    card_list = ["abc Test Card", "2 Test Card"]

    with pytest.raises(CardListInputError):
        parse_cardlist(card_list)


def test_insert_cardloans(db_session: Session):
    """Test inserting card loans."""
    card_list = ["2 Test Card 1", "3 Test Card 2"]
    lender_id = 12345
    borrower_id = 67890
    borrower_name = "TestBorrower"
    tag = "test_tag"

    # Insert the card loans
    result = insert_cardloans(
        db_session, card_list, lender_id, borrower_id, borrower_name, tag
    )

    # Verify the result
    assert result == 5  # Total quantity

    # Verify the database state
    loans = db_session.query(CardLoan).all()
    assert len(loans) == 2

    # Check the first loan
    assert loans[0].card == "Test Card 1"
    assert loans[0].quantity == 2
    assert loans[0].lender == lender_id
    assert loans[0].borrower == borrower_id
    assert loans[0].borrower_name == borrower_name
    assert loans[0].order_tag == tag

    # Check the second loan
    assert loans[1].card == "Test Card 2"
    assert loans[1].quantity == 3


def test_get_cardloans(db_session: Session):
    """Test getting card loans."""
    # Create some test loans
    loan1 = CardLoan(
        card="Test Card 1",
        quantity=2,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    loan2 = CardLoan(
        card="Test Card 2",
        quantity=3,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    db_session.add_all([loan1, loan2])
    db_session.commit()

    # Get the loans
    result = get_cardloans(db_session, 12345, 67890, "test_tag")

    # Verify the result
    assert len(result) == 2
    assert result[0].card == "Test Card 1"
    assert result[1].card == "Test Card 2"


def test_return_cardloans(db_session: Session):
    """Test returning card loans."""
    # Create some test loans
    loan1 = CardLoan(
        card="Test Card 1",
        quantity=2,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    loan2 = CardLoan(
        card="Test Card 2",
        quantity=3,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    db_session.add_all([loan1, loan2])
    db_session.commit()

    # Return some cards
    card_list = ["1 Test Card 1", "2 Test Card 2"]
    result = return_cardloans(db_session, card_list, 12345, 67890, "test_tag")

    # Verify the result
    assert result == 3  # Total returned

    # Verify the database state
    loans = db_session.query(CardLoan).all()
    assert len(loans) == 2

    # Check the first loan (partially returned)
    assert loans[0].card == "Test Card 1"
    assert loans[0].quantity == 1

    # Check the second loan (partially returned)
    assert loans[1].card == "Test Card 2"
    assert loans[1].quantity == 1


def test_return_cardloans_not_found(db_session: Session):
    """Test returning card loans that don't exist."""
    # Create some test loans
    loan = CardLoan(
        card="Test Card 1",
        quantity=1,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    db_session.add(loan)
    db_session.commit()

    # Try to return a card that doesn't exist
    card_list = ["1 Test Card 2"]

    with pytest.raises(CardNotFoundError):
        return_cardloans(db_session, card_list, 12345, 67890, "test_tag")


def test_bulk_return_cardloans(db_session: Session):
    """Test bulk returning card loans."""
    # Create some test loans
    loan1 = CardLoan(
        card="Test Card 1",
        quantity=2,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    loan2 = CardLoan(
        card="Test Card 2",
        quantity=3,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    db_session.add_all([loan1, loan2])
    db_session.commit()

    # Mock the delete statement execution
    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        mock_execute.return_value.fetchall.return_value = [loan1, loan2]

        # Bulk return the loans
        result = bulk_return_cardloans(db_session, 12345, 67890, "test_tag")

        # Verify the result
        assert result == 2  # Number of rows affected


def test_bulk_get_cardloans(db_session: Session):
    """Test bulk getting card loans."""
    # Create some test loans
    loan1 = CardLoan(
        card="Test Card 1",
        quantity=2,
        lender=12345,
        borrower=67890,
        borrower_name="TestBorrower",
        order_tag="test_tag",
        created_at=datetime.datetime.now(),
    )
    loan2 = CardLoan(
        card="Test Card 2",
        quantity=3,
        lender=12345,
        borrower=54321,
        borrower_name="OtherBorrower",
        order_tag="other_tag",
        created_at=datetime.datetime.now(),
    )
    db_session.add_all([loan1, loan2])
    db_session.commit()

    # Get all loans for the lender
    result = bulk_get_cardloans(db_session, 12345)

    # Verify the result
    assert len(result) == 2
    assert result[0].card == "Test Card 1"
    assert result[1].card == "Test Card 2"


def test_format_loanlist_output():
    """Test formatting loan list output."""
    # Create some mock loans
    loan1 = MagicMock()
    loan1.card = "Test Card 1"
    loan1.quantity = 2
    loan1.order_tag = "test_tag"
    loan1.created_at = datetime.datetime(2023, 1, 1)

    loan2 = MagicMock()
    loan2.card = "Test Card 2"
    loan2.quantity = 3
    loan2.order_tag = "test_tag"
    loan2.created_at = datetime.datetime(2023, 1, 2)

    # Format the output
    result = format_loanlist_output([loan1, loan2])

    # Verify the result contains the card names
    assert "Test Card 1" in result
    assert "Test Card 2" in result


def test_format_bulk_loanlist_output():
    """Test formatting bulk loan list output."""
    # Create some mock loans
    loan1 = MagicMock()
    loan1.borrower_name = "TestBorrower"
    loan1.order_tag = "test_tag"
    loan1.quantity = 2

    loan2 = MagicMock()
    loan2.borrower_name = "OtherBorrower"
    loan2.order_tag = "other_tag"
    loan2.quantity = 3

    # Mock table2ascii to avoid column width issues
    with patch("magic512bot.services.card_lender.table2ascii") as mock_table2ascii:
        mock_table2ascii.return_value = "Mocked Table Output"

        # Format the output
        result = format_bulk_loanlist_output([loan1, loan2])

        # Verify the result
        assert result == "Mocked Table Output"

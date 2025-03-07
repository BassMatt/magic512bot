from unittest.mock import MagicMock, patch

import pytest

from magic512bot.cogs.card_lender import (
    CardLender,
    InsertCardLoansModal,
    ReturnCardLoansModal,
)
from magic512bot.errors import CardNotFoundError


@pytest.mark.asyncio
async def test_loan_handler(mock_bot, mock_interaction, mock_member):
    """Test the loan_handler command."""
    cog = CardLender(mock_bot)

    # Access the callback directly instead of calling the command
    await cog.loan_handler.callback(cog, mock_interaction, mock_member, "test_tag")

    # Verify that the modal was sent
    mock_interaction.response.send_modal.assert_called_once()

    # Verify the modal has the correct attributes
    modal = mock_interaction.response.send_modal.call_args[0][0]
    assert isinstance(modal, InsertCardLoansModal)
    assert modal.borrower == mock_member
    assert modal.tag == "test_tag"


@pytest.mark.asyncio
async def test_return_cards(mock_bot, mock_interaction, mock_member):
    """Test the return_cards command."""
    cog = CardLender(mock_bot)

    # Access the callback directly
    await cog.return_cards.callback(cog, mock_interaction, mock_member, "test_tag")

    # Verify that the modal was sent
    mock_interaction.response.send_modal.assert_called_once()

    # Verify the modal has the correct attributes
    modal = mock_interaction.response.send_modal.call_args[0][0]
    assert isinstance(modal, ReturnCardLoansModal)
    assert modal.borrower == mock_member
    assert modal.tag == "test_tag"


@pytest.mark.asyncio
async def test_bulk_return_cards_handler(mock_bot, mock_interaction, mock_member):
    """Test the bulk_return_cards_handler command."""
    cog = CardLender(mock_bot)

    # Mock the bulk_return_cardloans function
    with patch("magic512bot.cogs.card_lender.bulk_return_cardloans", return_value=5):
        # Access the callback directly
        await cog.bulk_return_cards_handler.callback(
            cog, mock_interaction, mock_member, "test_tag"
        )

        # Verify that the response was sent
        mock_interaction.response.send_message.assert_called_once()

        # Verify the message contains the correct information
        message = mock_interaction.response.send_message.call_args[0][0]
        assert "returned **5**" in message
        assert mock_member.mention in message


@pytest.mark.asyncio
async def test_get_loans_handler(mock_bot, mock_interaction, mock_member):
    """Test the get_loans_handler command."""
    cog = CardLender(mock_bot)

    # Create mock card loans
    mock_loans = [
        MagicMock(quantity=2, card="Test Card 1", order_tag="test_tag"),
        MagicMock(quantity=3, card="Test Card 2", order_tag="test_tag"),
    ]

    # Mock the get_cardloans function
    with patch("magic512bot.cogs.card_lender.get_cardloans", return_value=mock_loans):
        # Mock the format_loanlist_output function
        with patch(
            "magic512bot.cogs.card_lender.format_loanlist_output",
            return_value="Formatted Output",
        ):
            # Access the callback directly
            await cog.get_loans_handler.callback(
                cog, mock_interaction, mock_member, "test_tag"
            )

            # Verify that the response was sent
            mock_interaction.response.send_message.assert_called_once()

            # Verify the message contains the correct information
            message = mock_interaction.response.send_message.call_args[0][0]
            assert "**5**" in message  # Sum of quantities
            assert mock_member.mention in message
            assert "Formatted Output" in message


@pytest.mark.asyncio
async def test_bulk_get_loans_handler(mock_bot, mock_interaction):
    """Test the bulk_get_loans_handler command."""
    cog = CardLender(mock_bot)

    # Mock the bulk_get_cardloans function
    with patch("magic512bot.cogs.card_lender.bulk_get_cardloans", return_value=[]):
        # Mock the format_bulk_loanlist_output function
        with patch(
            "magic512bot.cogs.card_lender.format_bulk_loanlist_output",
            return_value="Bulk Formatted Output",
        ):
            # Access the callback directly
            await cog.bulk_get_loans_handler.callback(cog, mock_interaction)

            # Verify that the response was sent
            mock_interaction.response.send_message.assert_called_once()

            # Verify the message contains the correct information
            message = mock_interaction.response.send_message.call_args[0][0]
            assert "Bulk Formatted Output" in message


@pytest.mark.asyncio
async def test_insert_card_loans_modal_on_submit(mock_interaction, db_session):
    """Test the on_submit method of InsertCardLoansModal."""
    # Create a mock sessionmaker that returns our test session
    mock_sessionmaker = MagicMock()
    mock_sessionmaker.begin.return_value.__enter__.return_value = db_session

    # Create a modal instance
    modal = InsertCardLoansModal(mock_sessionmaker, mock_interaction.user, "test_tag")
    modal.loanlist = MagicMock()
    modal.loanlist.value = "2 Test Card"

    # Mock the insert_cardloans function
    with patch("magic512bot.cogs.card_lender.insert_cardloans", return_value=2):
        # Call the on_submit method
        await modal.on_submit(mock_interaction)

        # Verify that the response was sent
        mock_interaction.response.send_message.assert_called_once()

        # Verify the message contains the correct information
        message = mock_interaction.response.send_message.call_args[0][0]
        assert "loaned **2**" in message


@pytest.mark.asyncio
async def test_return_card_loans_modal_on_submit(mock_interaction, db_session):
    """Test the on_submit method of ReturnCardLoansModal."""
    # Create a mock sessionmaker that returns our test session
    mock_sessionmaker = MagicMock()
    mock_sessionmaker.begin.return_value.__enter__.return_value = db_session

    # Create a modal instance
    modal = ReturnCardLoansModal(mock_sessionmaker, mock_interaction.user, "test_tag")
    modal.loanlist = MagicMock()
    modal.loanlist.value = "2 Test Card"

    # Mock the return_cardloans function
    with patch("magic512bot.cogs.card_lender.return_cardloans", return_value=2):
        # Call the on_submit method
        await modal.on_submit(mock_interaction)

        # Verify that the response was sent
        mock_interaction.response.send_message.assert_called_once()

        # Verify the message contains the correct information
        message = mock_interaction.response.send_message.call_args[0][0]
        assert "returned **2**" in message


@pytest.mark.asyncio
async def test_return_card_loans_modal_on_submit_error(mock_interaction, db_session):
    """Test the on_submit method of ReturnCardLoansModal when an error occurs."""
    # Create a mock sessionmaker that returns our test session
    mock_sessionmaker = MagicMock()
    mock_sessionmaker.begin.return_value.__enter__.return_value = db_session

    # Create a modal instance
    modal = ReturnCardLoansModal(mock_sessionmaker, mock_interaction.user, "test_tag")
    modal.loanlist = MagicMock()
    modal.loanlist.value = "2 Test Card"

    # Mock the return_cardloans function to raise an error
    with patch(
        "magic512bot.cogs.card_lender.return_cardloans",
        side_effect=CardNotFoundError([("Test Card", 2)]),
    ):
        # Call the on_submit method
        await modal.on_submit(mock_interaction)

        # Verify that the error response was sent
        mock_interaction.response.send_message.assert_called_once()

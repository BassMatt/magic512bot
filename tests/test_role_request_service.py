import pytest

from magic512bot.models.user import User
from magic512bot.services.role_request import (
    add_user_sweat_role,
    add_user_sweat_roles,
    get_user_sweat_roles,
    remove_user_sweat_roles,
)


def test_get_user_sweat_roles_existing_user(db_session):
    """Test getting sweat roles for an existing user."""
    # Create a test user
    user = User(id=12345, user_name="TestUser", sweat_roles=["Role1", "Role2"])
    db_session.add(user)
    db_session.commit()

    # Get the user's sweat roles
    roles = get_user_sweat_roles(db_session, 12345)

    # Verify the roles were retrieved correctly
    assert len(roles) == 2
    assert "Role1" in roles
    assert "Role2" in roles


def test_get_user_sweat_roles_nonexistent_user(db_session):
    """Test getting sweat roles for a nonexistent user."""
    # Get roles for a user that doesn't exist
    roles = get_user_sweat_roles(db_session, 99999)

    # Verify an empty list is returned
    assert roles == []


def test_add_user_sweat_role_existing_user(db_session):
    """Test adding a sweat role to an existing user."""
    # Create a test user
    user = User(id=12345, user_name="TestUser", sweat_roles=["Role1"])
    db_session.add(user)
    db_session.commit()

    print("\nBefore add_user_sweat_role:")
    print(f"User ID: {user.id}, Name: {user.user_name}")
    print(f"Roles: {user.sweat_roles}")

    # Add a role directly
    add_user_sweat_role(db_session, 12345, "TestUser", "Role2")

    # Check if the role was added to the user object in memory
    print("\nAfter add_user_sweat_role (before commit):")
    user_in_session = db_session.query(User).filter_by(id=12345).first()
    print(f"User in session - Roles: {user_in_session.sweat_roles}")
    print(f"Original user object - Roles: {user.sweat_roles}")
    print(f"Same object? {user is user_in_session}")

    db_session.commit()

    # Check after commit
    print("\nAfter commit:")
    user_after_commit = db_session.query(User).filter_by(id=12345).first()
    print(f"User after commit - Roles: {user_after_commit.sweat_roles}")
    print(f"Original user object - Roles: {user.sweat_roles}")
    print(f"Same object? {user is user_after_commit}")

    # Refresh the session to ensure we get the latest data
    db_session.refresh(user)

    print("\nAfter refresh:")
    print(f"Refreshed user - Roles: {user.sweat_roles}")

    # Verify the role was added
    assert "Role1" in user.sweat_roles
    assert "Role2" in user.sweat_roles


def test_add_user_sweat_role_new_user(db_session):
    """Test adding a sweat role to a new user."""
    # Make sure the user doesn't exist yet
    assert db_session.query(User).filter_by(id=54321).first() is None

    # Add a role to a new user
    add_user_sweat_role(db_session, 54321, "TestUser", "NewRole")
    db_session.commit()

    # Verify the user was created with the role
    new_user = db_session.query(User).filter_by(id=54321).first()
    assert new_user is not None
    assert "NewRole" in new_user.sweat_roles


def test_add_user_sweat_roles(db_session):
    """Test adding multiple sweat roles at once."""
    # Add roles to a new user
    add_user_sweat_roles(db_session, 12345, "TestUser", ["Role1", "Role2", "Role3"])
    db_session.commit()

    # Verify the roles were added
    roles = get_user_sweat_roles(db_session, 12345)
    assert len(roles) == 3
    assert "Role1" in roles
    assert "Role2" in roles
    assert "Role3" in roles


def test_remove_user_sweat_roles(db_session):
    """Test removing sweat roles from a user."""
    # Create a test user with multiple roles
    user = User(id=12345, user_name="TestUser", sweat_roles=["Role1", "Role2", "Role3"])
    db_session.add(user)
    db_session.commit()

    # Remove some roles
    remove_user_sweat_roles(db_session, 12345, "TestUser", ["Role1", "Role3"])
    db_session.commit()

    # Verify the roles were removed
    roles = get_user_sweat_roles(db_session, 12345)
    assert len(roles) == 1
    assert "Role2" in roles
    assert "Role1" not in roles
    assert "Role3" not in roles


def test_create_user(db_session):
    """Test creating a user in the database."""
    # Create a test user
    user = User(id=12345, user_name="TestUser", sweat_roles=["Role1", "Role2"])
    db_session.add(user)
    db_session.commit()

    # Query the user
    retrieved_user = db_session.query(User).filter_by(id=12345).first()

    # Verify the user was created correctly
    assert retrieved_user is not None
    assert retrieved_user.id == 12345
    assert retrieved_user.user_name == "TestUser"
    assert retrieved_user.sweat_roles == ["Role1", "Role2"]


@pytest.mark.asyncio
async def test_async_function(mock_interaction):
    """Test an async function."""
    # Call an async method on the mock
    await mock_interaction.response.send_message("Test message")

    # Verify it was called
    mock_interaction.response.send_message.assert_called_once_with("Test message")

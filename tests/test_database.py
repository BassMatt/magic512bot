import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from magic512bot.database import get_db  # Import your get_db function

@pytest.mark.asyncio
async def test_database_connection(db_session):
    assert isinstance(db_session, AsyncSession), f"db_session is of type {type(db_session)}, expected AsyncSession"
    
    print(f"Type of db_session: {type(db_session)}")
    print(f"Dir of db_session: {dir(db_session)}")
    
    try:
        async with db_session.begin():
            result = await db_session.execute(text("SELECT 1"))
            row = await result.fetchone()
        
        assert row[0] == 1, "Unexpected result from database query"
        print("Database connection test passed successfully!")
    except AttributeError as e:
        pytest.fail(f"AttributeError: {str(e)}")
    except Exception as e:
        pytest.fail(f"Unexpected error: {str(e)}")

# If you want to test the get_db function directly
@pytest.mark.asyncio
async def test_get_db():
    session = await anext(get_db())

    assert isinstance(session, AsyncSession), f"self.db_session is of type {type(session)}, expected AsyncSession"
    assert session is not None, "get_db did not return a session"

    # Test if we can execute a simple query
    try:
        result = await session.execute(text("SELECT 1"))
        row = result.fetchone()
        assert row[0] == 1, "Unexpected result from database query"
        print("get_db test passed successfully!")
    except Exception as e:
        pytest.fail(f"Database query failed: {e}")
    finally:
        await session.close()
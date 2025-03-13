from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from magic512bot.config import DB_CONNECTION_STRING, LOGGER
from magic512bot.models import register_models
from magic512bot.models.base import Base

engine = create_engine(DB_CONNECTION_STRING, echo=True)  # type: ignore
SessionLocal = sessionmaker(bind=engine)


def init_db() -> bool:
    """
    Initialize the database, creating tables only if they don't exist.
    Returns True if successful, False if there was an error.
    """
    inspector = inspect(engine)
    models = register_models()
    print(f"registering {len(models)}")

    try:
        # Get all table names from your models
        model_tables = Base.metadata.tables.keys()
        existing_tables = inspector.get_table_names()
        LOGGER.info(f"Existing tables: {existing_tables}")
        LOGGER.info(f"Model tables: {model_tables}")

        # Check which tables need to be created
        tables_to_create = set(model_tables) - set(existing_tables)

        if tables_to_create:
            LOGGER.info(f"🏗️ Creating missing tables: {tables_to_create}")
            Base.metadata.create_all(bind=engine)
            LOGGER.info("✨ Tables created successfully!")
        else:
            LOGGER.info("👍 All tables already exist!")

        return True

    except Exception as e:
        LOGGER.error(f"💥 Database initialization failed: {e!s}")
        return False

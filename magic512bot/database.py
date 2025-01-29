import config
from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import logger

engine=create_engine(config.DB_CONNECTION_STRING, echo=True)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def init_db():
    """
    Initialize the database, creating tables only if they don't exist.
    Returns True if successful, False if there was an error.
    """
    inspector = inspect(engine)
    
    try:
        # Get all table names from your models
        model_tables = Base.metadata.tables.keys()
        existing_tables = inspector.get_table_names()
        
        # Check which tables need to be created
        tables_to_create = set(model_tables) - set(existing_tables)
        
        if tables_to_create:
            logger.info(f"🏗️ Creating missing tables: {tables_to_create}")
            Base.metadata.create_all(bind=engine)
            logger.info("✨ Tables created successfully!")
        else:
            logger.info("👍 All tables already exist!")
            
        return True
        
    except Exception as e:
        logger.error(f"💥 Database initialization failed: {str(e)}")
        return False
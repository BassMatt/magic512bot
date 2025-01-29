import config
import datetime
from sqlalchemy import Integer, String, DateTime, BigInteger, ARRAY, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column, Mapped
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from typing import List
import asyncio
from config import logger

engine=create_async_engine(config.DB_CONNECTION_STRING, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class CardLoan(Base):
    __tablename__ = 'card_loans'
    id: Mapped[int] = mapped_column(Integer(), nullable=False, primary_key=True)
    card: Mapped[str] = mapped_column(String(100), nullable=False) # for now, just have cards as names
    lender: Mapped[int] = mapped_column(BigInteger(), nullable=False) # discord user id of lender
    borrower: Mapped[int] = mapped_column(BigInteger(), nullable=False) # discord user id of borrower
    borrower_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(), nullable=False)
    order_tag: Mapped[str] = mapped_column(String(100), nullable=False) # order tag, if not specified defaults to ""

class Users(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer(), nullable=False, primary_key=True)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False) # discord user id
    roles: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)

async def check_table_exists(engine: AsyncEngine, table_name: str) -> bool:
    async with engine.connect() as conn:
        def _check_table(connection):
            return inspect(connection).has_table(table_name)
        return await conn.run_sync(_check_table)

async def init_db(timeout_seconds: int = 30):
    logger.info("Initializing database...")
    try:
        async with asyncio.timeout(timeout_seconds):
            tables_to_create = []
            for table in Base.metadata.sorted_tables:
                if not await check_table_exists(engine, table.name):
                    logger.info(f"Table {table.name} does not exist. Adding to creation list.")
                    tables_to_create.append(table)
                else:
                    logger.info(f"Table {table.name} already exists. Skipping.")

            if tables_to_create:
                logger.info(f"Creating {len(tables_to_create)} new tables...")
                async with engine.begin() as conn:
                    await conn.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables_to_create))
                logger.info("New tables created successfully!")
            else:
                logger.info("All tables already exist. No new tables created.")

            logger.info("Database initialization complete!")
    except asyncio.TimeoutError:
        logger.info(f"Database initialization timed out after {timeout_seconds} seconds!")
        raise
    except Exception as e:
        logger.info(f"An error occurred during database initialization: {str(e)}")
        raise

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
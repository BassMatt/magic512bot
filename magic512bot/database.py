import config
import datetime
from sqlalchemy import Integer, String, DateTime, BigInteger, ARRAY
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column, Mapped
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import List, AsyncGenerator

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

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
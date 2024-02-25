from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_NAME
from misc import PathControl


class Base(AsyncAttrs, DeclarativeBase):
    pass


class FipiBankProblem(Base):
    __tablename__ = "fipibank_problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(String(6), nullable=False)
    subject = Column(String(5), nullable=False)
    url = Column(String, nullable=False)
    gia_type = Column(String(3), nullable=False)
    condition_html = Column(String, nullable=False)
    condition_image_urls = Column(String)

    def __repr__(self) -> str:
        return f"<FipiBankProblem subject={self.subject} problem_id={self.problem_id}>"


async def register_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


engine: AsyncEngine = create_async_engine(
    url=f'sqlite+aiosqlite:///{PathControl.get(f"database/{DATABASE_NAME}")}'
)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

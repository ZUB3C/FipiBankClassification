from enum import Enum

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, delete
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from ..misc import PathControl
from .const import DATABASE_NAME


class GiaTypeEnum(Enum):
    oge = "oge"
    ege = "ege"


class Base(AsyncAttrs, DeclarativeBase):
    pass


class GiaType(Base):
    __tablename__ = "gia_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(3), unique=True, nullable=False)

    @classmethod
    async def insert_data(cls, session: AsyncSession) -> None:
        await session.execute(delete(cls))
        session.add_all(
            [cls(id=0, name=GiaTypeEnum.oge.value), cls(id=1, name=GiaTypeEnum.ege.value)]
        )
        await session.commit()


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    hash = Column(String, unique=True, nullable=False)


class Theme(Base):
    __tablename__ = "codifier_themes"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    codifier_id = Column(String, nullable=False)
    name = Column(String, nullable=False)


class FipiBankProblem(Base):
    __tablename__ = "fipibank_problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(String(6), nullable=False)
    url = Column(String, nullable=False)
    condition_html = Column(String, nullable=False)
    gia_type = relationship(
        "GiaType", secondary="fipibank_problems_gia_types", backref="fipibank_problems"
    )
    subject = relationship("Subject", secondary="fipibank_problems_subjects")
    file_urls = relationship("FipiBankProblemFile")
    themes = relationship("Theme", secondary="fipibank_problems_codifier_themes")
    exam_number = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<FipiBankProblem problem_id={self.problem_id}>"


class FipiBankProblemGiaType(Base):
    __tablename__ = "fipibank_problems_gia_types"

    fipibank_problem_id = Column(Integer, ForeignKey("fipibank_problems.id"), primary_key=True)
    gia_type_id = Column(Integer, ForeignKey("gia_types.id"), primary_key=True)


class FipiBankProblemSubject(Base):
    __tablename__ = "fipibank_problems_subjects"

    fipibank_problem_id = Column(Integer, ForeignKey("fipibank_problems.id"), primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), primary_key=True)


class FipiBankProblemFile(Base):
    __tablename__ = "fipibank_problem_files"

    id = Column(Integer, primary_key=True)
    fipibank_problem_id = Column(Integer, ForeignKey("fipibank_problems.id"))
    file_url = Column(String, nullable=False)


class FipiBankProblemCodifierTheme(Base):
    __tablename__ = "fipibank_problems_codifier_themes"
    fipibank_problem_id = Column(Integer, ForeignKey("fipibank_problems.id"), primary_key=True)
    codifier_theme_id = Column(Integer, ForeignKey("codifier_themes.id"), primary_key=True)

    __table_args__ = (
        UniqueConstraint(
            "fipibank_problem_id",
            "codifier_theme_id",
            name="unique_fipibank_problem_codifier_theme",
        ),
    )


async def register_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        await GiaType.insert_data(session)


engine: AsyncEngine = create_async_engine(
    url=f"sqlite+aiosqlite:///{PathControl.get(f'../{DATABASE_NAME}')}"
)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

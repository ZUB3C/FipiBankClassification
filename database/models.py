from sqlalchemy import Column, Integer, String, Boolean, VARCHAR

from .main import Database
from config import FIPI_BANK_TABLE_NAME


class FIPIBankProblems(Database.BASE):
    __tablename__ = FIPI_BANK_TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(String(6), nullable=False)
    subject = Column(VARCHAR(5), nullable=False)
    condition_html = Column(String, nullable=False)
    raw_condition_text = Column(String)
    condition_images = Column(String)
    url = Column(String, nullable=False)
    gia_type = Column(String(3), nullable=False)
    new_bank = Column(Boolean, nullable=False)


def register_models() -> None:
    Database.BASE.metadata.create_all(Database().engine)

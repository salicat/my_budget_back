from tokenize import Floatnumber
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, String, Date
import datetime
from db.db_connection import Base, engine

class GoalsInDb(Base):
    __tablename__ = "goals"
    name        = Column(String, primary_key=True)
    username    = Column(String, ForeignKey("users.username"))
    current_val = Column(Floatnumber)
    final_value = Column(Floatnumber)
    final_date  = Column(Date)

Base.metadata.create_all(bind=engine)


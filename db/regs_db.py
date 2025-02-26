from tokenize import Floatnumber
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, Float, String, Date
import datetime
from db.db_connection import Base, engine

class RegsInDb(Base):
    __tablename__= "registers"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    username    = Column(String, ForeignKey("users.username"))
    date        = Column(Date)
    type        = Column(String)
    description = Column(String)
    category    = Column(String)
    value       = Column(Float)

Base.metadata.create_all(bind=engine)

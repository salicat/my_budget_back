from tokenize import Floatnumber
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, Float, String
from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy import Date
from db.db_connection import Base, engine

class CatsInDb(Base):
    __tablename__= "categories"
    id          = Column(Integer,  primary_key=True, autoincrement=True)
    category    = Column(String)
    type        = Column(String)
    username    = Column(String, ForeignKey("users.username"))
    budget      = Column(Float)
    value       = Column(Float)
    recurrency  = Column(Boolean)
    day         = Column(Date, nullable=True )
    active      = Column(Boolean)
    
Base.metadata.create_all(bind=engine)
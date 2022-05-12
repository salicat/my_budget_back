from tokenize import Floatnumber
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, String
from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy import Date
from db.db_connection import Base, engine

class CatsInDb(Base):
    __tablename__= "categories"
    id          = Column(Integer, primary_key=True)
    category    = Column(String, primary_key=True)
    type        = Column(String)
    username    = Column(String, ForeignKey("users.username"))
    budget      = Column(Integer)
    value       = Column(Integer)
    recurrency  = Column(Boolean)
    day         = Column(Date, nullable=True )
    
Base.metadata.create_all(bind=engine)
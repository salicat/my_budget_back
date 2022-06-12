from tokenize import Floatnumber
from sqlalchemy import Column, Integer, Float, String
from db.db_connection import Base, engine

class UserInDB(Base):
    __tablename__="users"
    username    = Column(String, primary_key=True, unique=True)
    password    = Column(String)
    liabilities = Column(Float)
    passives    = Column(Float)
    

Base.metadata.create_all(bind=engine)



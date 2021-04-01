from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, String
from db.db_connection import Base, engine

class CatsInDb(Base):
    __tablename__= "categories"
    category    = Column(String, primary_key=True)
    type        = Column(String)
    username    = Column(String, ForeignKey("users.username"))
    value       = Column(Integer)
    budget      = Column(Integer)
    
Base.metadata.create_all(bind=engine)
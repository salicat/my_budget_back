from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgres://hakalhdoaaovgo:15254fdb170ca445e9ade98697ec195707b4ae9dc9f1e54709b4621f274f8e20@ec2-52-45-73-150.compute-1.amazonaws.com:5432/d3i3ofaqrp7dgu"
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, 
                            autoflush=False, 
                            bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()
Base.metadata.schema = "my_budget_db"
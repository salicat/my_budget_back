from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "postgresql://deq88mms5u8hob:354a769cb1626c1cb73f3e0a6956518625ea9446e6bf2b336718cc61aa3cbc66@ec2-52-3-2-245.compute-1.amazonaws.com:5432/d5911ovk25i3u1"
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
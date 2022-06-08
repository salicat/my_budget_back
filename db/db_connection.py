from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "postgresql://uwwqomxcjzyenm:a0b4c1376dfbf47fc44c966d99f476a728f947a85571f6af23c39fa8f831812a@ec2-52-204-195-41.compute-1.amazonaws.com:5432/d2jt20o0r9kcas"
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
Base.metadata.schema = "myBudgetDB"
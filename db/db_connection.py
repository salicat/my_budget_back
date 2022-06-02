from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "postgresql://oqoghbhqwedwoz:2a748f967dd938bbb5ef24632d4235965dd507127807d7c6e43b29b0ccd073f7@ec2-54-227-248-71.compute-1.amazonaws.com:5432/d5911ovk25i3u1"
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
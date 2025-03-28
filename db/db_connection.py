from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://krlz:1317@localhost:5432/local_budget_db"

# DATABASE_URL = "postgresql+psycopg2://krlz:FyPqmZSSbhQWbQSr0ql5VeWYpjU7cCr6@dpg-cuvk1nt2ng1s738ps0k0-a.oregon-postgres.render.com:5432/budget_dd_render"


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

conn = engine.connect()
if conn.dialect.has_schema(conn, "by_budget_db"):
    Base.metadata.schema = "by_budget_db"
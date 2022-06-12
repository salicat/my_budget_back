from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "postgresql://mvmltkesjxfeun:787a58ec4497befcfc2626b8dfd1032ead98b553032df74dc4780d736b33e9fb@ec2-52-72-99-110.compute-1.amazonaws.com:5432/d4d3chl5l23csp"
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
if conn.dialect.has_schema(conn, schema_name):
    Base.metadata.schema = "myBudgetDB"
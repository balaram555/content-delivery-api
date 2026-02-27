from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import time
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# 🔥 WAIT FOR DATABASE TO BE READY
def wait_for_db():
    retries = 10
    while retries > 0:
        try:
            connection = engine.connect()
            connection.close()
            print("✅ Database connected successfully")
            return
        except OperationalError:
            print("⏳ Waiting for database...")
            retries -= 1
            time.sleep(3)
    raise Exception("❌ Database not available")


wait_for_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
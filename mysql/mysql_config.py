from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_USER = "testing1"
DB_PASSWORD = "testing1"
DB_HOST = "localhost"
DB_NAME = "testing"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # auto-reconnect if connection drops
    pool_recycle=3600,        # recycle connections every 1 hour
    echo=False                # set True to see SQL logs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_engine():
    return engine


def test_connection():
    try:
        with engine.connect() as conn:
            print(f"✅ Connected to MySQL: {DB_HOST}/{DB_NAME}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    test_connection()
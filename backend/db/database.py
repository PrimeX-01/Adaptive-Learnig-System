from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

# Build connection URL from environment variables (no hardcoded username)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "prefer"},  
    pool_recycle=60,
    pool_size=5,
    max_overflow=2,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session with automatic retry on SSL disconnect or server close."""
    retries = 0
    max_retries = 3
    while retries < max_retries:
        db = SessionLocal()
        try:
            yield db
            return
        except Exception as e:
            db.close()
            error_msg = str(e)
            # Retry on common connection drop errors
            if ('SSL SYSCALL' in error_msg or 'EOF' in error_msg or 
                'server closed the connection' in error_msg or
                'connection was closed' in error_msg) and retries < max_retries - 1:
                retries += 1
                wait_time = 0.5 * retries   # 0.5s, then 1s, then 1.5s
                print(f"[Database] Connection error, retrying in {wait_time}s... ({retries}/{max_retries-1})")
                time.sleep(wait_time)
                continue
            raise   # Non‑retriable error, propagate
        finally:
            try:
                db.close()
            except Exception:
                pass
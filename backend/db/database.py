from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

engine = create_engine(
    URL.create(
        drivername="postgresql",
        username="postgres.ighctpgbqovextofjvas",
        password=os.getenv("DATABASE_PASSWORD"),
        host="aws-0-eu-west-1.pooler.supabase.com",
        port=6543,
        database="postgres"
    ),
    connect_args={"sslmode": "require"},  
    pool_recycle  = 60,   
    pool_size     = 5,
    max_overflow  = 2,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session with automatic retry on SSL disconnect."""
    retries = 0
    while retries < 3:                          
        db = SessionLocal()
        try:
            yield db
            return
        except Exception as e:
            db.close()
            if ('SSL SYSCALL' in str(e) or 'EOF' in str(e)) and retries < 2:
                retries += 1
                time.sleep(0.5 * retries)       # wait 0.5s → 1s between retries
                continue
            raise
        finally:
            try:
                db.close()
            except Exception:
                pass
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# ✅ Ensure DATABASE_URL is set
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("ERROR: DATABASE_URL is missing in .env file!")

# ✅ Create PostgreSQL Engine with Optimized Connection Pooling for Production
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", 5)),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 60)),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", 3600)),
        pool_pre_ping=True,  # Validate connections before use
        echo=os.getenv("DB_ECHO", "False").lower() == "true",
        connect_args={
            "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", 30)),
            "application_name": "trading_app"
        }
    )
    print("Database connected successfully.")
except Exception as e:
    raise RuntimeError(f"Database connection failed: {e}")

# ✅ Session Management
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Dependency to get database session with proper error handling
def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        print(f"Database session error: {e}")
        if db:
            db.rollback()
        raise  # IMPORTANT: Re-raise the exception so FastAPI can handle it properly
    finally:
        if db:
            db.close()

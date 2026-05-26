from sqlmodel import Session,create_engine
from app.core.config import settings

engine=create_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

def get_session():
    with Session(engine) as session:
        yield session                  #beautiful use of yield(generator) and with(context manager)
                                       # to prevent connection leakage, no matter what the session will close

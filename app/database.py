import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Render üzerinden gelen Supabase linkini çek, yoksa yerelde sqlite kullan
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# KORUMA KALKANI: pgbouncer gibi psycopg2'yi bozan parametreleri temizle
if "?" in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.split("?")[0]

# 2. Supabase (PostgreSQL) linkleri 'postgres://' ile başlarsa, 'postgresql://' yapıyoruz
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Veritabanı motorunu çalıştır
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 🔥 STREAMLIT İÇİN DÜZELTİLEN KISIM (yield yerine doğrudan return)
def get_db():
    return SessionLocal()

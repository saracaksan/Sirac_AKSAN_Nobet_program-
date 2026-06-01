import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Render ortam değişkenlerinden DATABASE_URL'i çek, bulamazsa yerelde sqlite kullan
# Bu yapı sayesinde verileriniz Supabase çelik kasasında ömür boyu güvende kalır.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# 🔥 KORUMA KALKANI: ?pgbouncer=true gibi psycopg2 kütüphanesini hataya düşüren 
# tüm url parametrelerini otomatik olarak temizler ve bağlantıyı garantiye alır.
if "?" in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.split("?")[0]

# 2. Supabase/PostgreSQL linkleri 'postgres://' ile başlarsa, SQLAlchemy uyumluluğu için 'postgresql://' yapıyoruz
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Veritabanı motorunu ve havuzunu oluştur
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Veritabanı oturum fabrikasını kur
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Modellerin türetileceği temel sınıfı tanımla
Base = declarative_base()

# 🔥 STREAMLIT İÇİN SIFIRDAN DÜZELTİLEN KISIM
# yield kullanımı fonksiyonu jeneratöre dönüştürüp Streamlit'i çökerteceği için,
# doğrudan ve kesintisiz bir veritabanı oturum nesnesi (Session) döndürüyoruz.
def get_db():
    return SessionLocal()

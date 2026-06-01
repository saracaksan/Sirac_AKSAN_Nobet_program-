import hashlib

def sifre_olustur(password: str) -> str:
    """Girilen düz metin şifreyi SHA-256 algoritması ile şifreler."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def sifre_dogrula(password: str, hashed_password: str) -> bool:
    """Girilen şifrenin, veritabanındaki şifreli (hash) haliyle eşleşip eşleşmediğini kontrol eder."""
    return sifre_olustur(password) == hashed_password
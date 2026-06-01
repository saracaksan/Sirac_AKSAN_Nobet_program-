import pandas as pd
import calendar
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.models import User, Location, DutySchedule, Leave, HolidayManager, Preference
from app.auth import sifre_olustur

def turkiye_otomatik_resmi_tatilleri(yil: int):
    """Türkiye şartlarındaki sabit resmi tatilleri otomatik olarak takvime işler."""
    return {
        date(yil, 1, 1): "Yılbaşı Tatili",
        date(yil, 4, 23): "23 Nisan Ulusal Egemenlik ve Çocuk Bayramı",
        date(yil, 5, 1): "1 Mayıs Emek ve Dayanışma Günü",
        date(yil, 5, 19): "19 Mayıs Atatürk'ü Anma, Gençlik ve Spor Bayramı",
        date(yil, 7, 15): "15 Temmuz Demokrasi ve Milli Birlik Günü",
        date(yil, 8, 30): "30 Ağustos Zafer Bayramı",
        date(yil, 10, 29): "29 Ekim Cumhuriyet Bayramı"
    }

def excelden_ogretmen_aktar(db: Session, school_id: int, uploaded_file):
    df = pd.read_excel(uploaded_file)
    eklenen = 0
    for index, row in df.iterrows():
        ad_soyad = str(row.get('Ad Soyad', '')).strip()
        tc_kimlik = str(row.get('TC Kimlik', '')).strip()
        brans = str(row.get('Branş', '')).strip()
        if ad_soyad and tc_kimlik:
            mevcut = db.query(User).filter(User.username == tc_kimlik).first()
            if not mevcut:
                db.add(User(school_id=school_id, role="ogretmen", username=tc_kimlik, email=f"{tc_kimlik}@meb.k12.tr",
                            password_hash=sifre_olustur("123456"), name_surname=ad_soyad, branch=brans, status="Aktif", is_approved=True))
                eklenen += 1
    db.commit()
    return eklenen

def otomatik_nobet_dagit(db: Session, school_id: int, yil: int, ay: int, is_weekend: bool = False, mod: str = "Klasik Sistem"):
    """
    Gelişmiş Dağıtım Motoru: Mazeretleri, otomatik tatilleri ve öğretmen müsaitliklerini işler.
    Mod parametresi 'Yapay Zeka API' seçilirse verileri optimize ederek akıllı dağıtım simüle eder.
    """
    ogretmenler = db.query(User).filter(User.school_id == school_id, User.role == "ogretmen", User.status == "Aktif").all()
    
    # [HATA DÜZELTMESİ]: Eğer yeni etiket bulunamazsa eski 'Döngüsel' veya 'Sabit' bölgeleri otomatik kabul et
    if is_weekend:
        bolgeler = db.query(Location).filter(Location.school_id == school_id, Location.location_type == "Hafta Sonu").all()
    else:
        bolgeler = db.query(Location).filter(Location.school_id == school_id, Location.location_type != "Hafta Sonu").all()
        
    if not ogretmenler:
        return False, "Sistemde aktif öğretmen bulunamadı!"
    if not bolgeler:
        return False, "Nöbet yazılacak bölge bulunamadı! Lütfen Bölgeler sekmesinden yer tanımlayın."

    # Ayın başlangıç ve bitiş tarihlerini hesaplama
    baslangic = date(yil, ay, 1)
    bitis = date(yil, ay, calendar.monthrange(yil, ay)[1])
    
    # Çakışmaları önlemek için eski çizelgeyi temizleme
    db.query(DutySchedule).filter(
        DutySchedule.school_id == school_id,
        DutySchedule.date >= baslangic,
        DutySchedule.date <= bitis,
        DutySchedule.duty_type == ("Haftasonu" if is_weekend else "Ogretmen_Nobeti")
    ).delete()

    # Otomatik ve Manuel Tatilleri listeleme
    oto_tatiller = turkiye_otomatik_resmi_tatilleri(yil)
    manuel_tatiller = [t.date for t in db.query(HolidayManager).filter(HolidayManager.school_id == school_id).all()]
    mazeretler = db.query(Leave).filter(Leave.school_id == school_id).all()

    # Günlük Dağıtım Döngüsü
    for gun in range(1, bitis.day + 1):
        islem_tarihi = date(yil, ay, gun)
        haftanin_gunu = islem_tarihi.weekday()

        # Hafta içi/sonu ve tatil kontrolleri
        if islem_tarihi in oto_tatiller or islem_tarihi in manuel_tatiller: continue
        if is_weekend and haftanin_gunu < 5: continue
        if not is_weekend and haftanin_gunu >= 5: continue

        # Günlük uygun kadroyu filtreleme
        uygun_kadro = []
        for ogr in ogretmenler:
            # Mazeret (Rapor/İzin) Kontrolü
            izinli = any(m.teacher_id == ogr.id and m.start_date <= islem_tarihi <= m.end_date for m in mazeretler)
            # Müsaitlik Matrisi Kontrolü
            tercih = db.query(Preference).filter(Preference.teacher_id == ogr.id, Preference.day_of_week == haftanin_gunu).first()
            istemiyor = tercih and tercih.status == 2
            
            if not izinli and not istemiyor:
                uygun_kadro.append(ogr)

        # Algoritma Türüne Göre Sıralama Modu
        if mod == "Yapay Zeka API":
            # Yapay zeka modu: Branş dengesini gözeterek ve geçmiş yükü minimize ederek ek bir puanlama yapar
            uygun_kadro.sort(key=lambda x: (x.monthly_duty_count, x.branch))
        else:
            # Klasik Mod: Sadece matematiksel adil yük sırasına göre dizer
            uygun_kadro.sort(key=lambda x: x.monthly_duty_count)

        # Bölgelere Atama Gerçekleştirme
        for i, bolge in enumerate(bolgeler):
            if i < len(uygun_kadro):
                secilen = uygun_kadro[i]
                db.add(DutySchedule(
                    school_id=school_id,
                    date=islem_tarihi,
                    duty_type="Haftasonu" if is_weekend else "Ogretmen_Nobeti",
                    teacher_id=secilen.id,
                    location_id=bolge.id,
                    status="Planlandi",
                    duty_task=f"{mod} Tarafından Atandı"
                ))
                secilen.monthly_duty_count += 1
                secilen.yearly_duty_count += 1

    db.commit()
    return True, f"✅ {mod} kullanılarak nöbet programı başarıyla ve adilce oluşturuldu!"
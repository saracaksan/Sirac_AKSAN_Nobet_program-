import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import io, calendar, random, json, base64
from sqlalchemy import extract, desc, Column, Integer, String, Date, ForeignKey, Boolean, Text, Float
from babel.dates import format_date

from app.database import get_db, Base
from app.auth import sifre_olustur

# ─────────────────────────────────────────────
# SABİTLER VE EŞLEŞTİRMELER
# ─────────────────────────────────────────────
MONTHS_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

ALGO_LISTESI = [
    "1. Sabit Gün – Döngüsel Yer (Önerilen)",
    "2. Sabit Gün – Sabit Yer",
    "3. Tam Döngüsel (Gün ve Yer Değişir)",
    "4. Adalet Puanı ve Dinamik Joker (Yapay Zeka)",
    "5. Katı Müsaitlik Matrisi (Sadece İsteklere Göre)"
]

STATUS_MAP = {
    "🟢 1. Nöbet (Kesin İstiyorum)": "primary",
    "🟡 2. Nöbet (Joker)": "joker",
    "🔵 3. Nöbet (Ekstra)": "extra",
    "🔴 Müsait Değil": "unavail"
}
REV_STATUS_MAP = {v: k for k, v in STATUS_MAP.items()}
STATUS_OPTS = list(STATUS_MAP.keys())

# ─────────────────────────────────────────────
# GÜNCELLENMİŞ MODEL YAPISI (TÜM TABLOLAR)
# ─────────────────────────────────────────────
class School(Base):
    __tablename__ = "schools"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    kurum_kodu = Column(String, unique=True)
    name = Column(String)
    manager_name = Column(String)
    email = Column(String)
    is_approved = Column(Boolean, default=False)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    role = Column(String) 
    username = Column(String, unique=True)
    password_hash = Column(String)
    plain_password = Column(String) 
    name_surname = Column(String)
    email = Column(String)
    branch = Column(String, nullable=True)
    status = Column(String, default="Aktif")
    is_approved = Column(Boolean, default=False)
    monthly_duty_count = Column(Integer, default=0)
    yearly_duty_count = Column(Integer, default=0)

class Location(Base):
    __tablename__ = "locations"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    name = Column(String)
    location_type = Column(String) 

class DutySchedule(Base):
    __tablename__ = "duty_schedules"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    date = Column(Date)
    duty_type = Column(String)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    status = Column(String, default="Planlandi")

class Leave(Base):
    __tablename__ = "leaves"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    leave_type = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)

class HolidayManager(Base):
    __tablename__ = "holiday_manager"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    name = Column(String)
    date = Column(Date)

class Preference(Base):
    __tablename__ = "preferences"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    day_of_week = Column(Integer)
    status = Column(Integer)

class FixedRule(Base):
    __tablename__ = "fixed_rules"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=True)
    location_id = Column(Integer, nullable=True)

class AssistantPrincipal(Base):
    __tablename__ = "assistant_principals"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=False)
    name_surname = Column(String, nullable=False)

class SchoolRule(Base):
    __tablename__ = "school_rules_v1"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=False)
    madde = Column(String, nullable=False)
    sira = Column(Integer, default=0)

class DatePreference(Base):
    __tablename__ = "date_preferences"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blocked_date = Column(Date, nullable=False)

class BackupRecord(Base):
    __tablename__ = "backup_records"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=False)
    label = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    payload_b64 = Column(Text, nullable=False)

class TeacherDutySetting(Base):
    __tablename__ = "teacher_duty_settings"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    hafta_ici_tutar = Column(Boolean, default=True)
    hafta_sonu_tutar = Column(Boolean, default=False)

class IncidentLog(Base):
    __tablename__ = "incident_logs"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date)
    incident_type = Column(String)
    description = Column(Text)
    is_resolved = Column(Boolean, default=False)

class DutySubstitute(Base):
    __tablename__ = "duty_substitutes"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    duty_id = Column(Integer, ForeignKey("duty_schedules.id", ondelete="CASCADE"))
    substitute_teacher_id = Column(Integer, ForeignKey("users.id"))

# ─────────────────────────────────────────────
# GLOBAL ARAYÜZ CSS TASARIMI
# ─────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Playfair+Display:wght@700;800&display=swap');
:root {
  --navy:   #0f1f3d;
  --navy2:  #162647;
  --blue:   #1d4ed8;
  --gold:   #f59e0b;
  --gold2:  #fbbf24;
  --teal:   #0d9488;
  --danger: #dc2626;
  --success:#16a34a;
  --purple: #7c3aed;
  --bg:     #f1f5f9;
  --card:   #ffffff;
  --border: #e2e8f0;
  --text:   #1e293b;
  --muted:  #64748b;
  --radius: 14px;
  --shadow: 0 4px 24px rgba(15,31,61,.10);
}
html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif; background: var(--bg) !important; color: var(--text);
}
.app-header {
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy2) 60%, #1d3461 100%);
  border-radius: var(--radius); padding: 28px 32px 22px; margin-bottom: 24px; display: flex; align-items: center; gap: 20px; box-shadow: 0 8px 32px rgba(15,31,61,.25); border-left: 5px solid var(--gold);
}
.app-header h2 { font-family: 'Playfair Display', serif; font-size: 1.65rem; color: #fff; margin: 0 0 4px; }
.app-header small { color: #94a3b8; font-size: .85rem; }
.metric-card { background: var(--card); border-radius: var(--radius); padding: 18px 20px; border-left: 4px solid var(--blue); box-shadow: var(--shadow); margin-bottom: 8px; }
.metric-card .label { font-size: .78rem; color: var(--muted); font-weight: 600; text-transform:uppercase; margin-bottom: 4px; }
.metric-card .value { font-size: 2rem; font-weight: 800; line-height: 1.1; }
.metric-card .sub   { font-size: .75rem; color: var(--muted); margin-top: 2px; }
.section-title { font-family: 'Playfair Display', serif; font-size: 1.15rem; font-weight: 700; color: var(--navy); border-bottom: 2px solid var(--gold); padding-bottom: 6px; margin: 16px 0 14px; }
.info-box { background: #eff6ff; border-left: 4px solid var(--blue); border-radius: 8px; padding: 10px 14px; font-size: .85rem; color: #1e40af; margin: 8px 0 14px; }
.ai-box   { background: linear-gradient(135deg,#f0fdf4,#dcfce7); border-left: 4px solid var(--success); border-radius: var(--radius); padding: 14px 18px; font-size: .88rem; color: #166534; margin: 10px 0; }
.stTabs [data-baseweb="tab-list"] { background: var(--card); border-radius: 12px 12px 0 0; padding: 4px 8px 0; border-bottom: 2px solid var(--border); gap: 2px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; font-weight: 600; font-size: .82rem; padding: 8px 14px; color: var(--muted); }
.stTabs [aria-selected="true"] { background: var(--blue) !important; color: #fff !important; }
.stButton > button { border-radius: 8px !important; font-weight: 600 !important; font-size: .85rem !important; transition: all .2s !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg,var(--blue),#1e40af) !important; border: none !important; color: #fff !important; box-shadow: 0 2px 8px rgba(29,78,216,.35) !important; }
div[data-testid="stDataFrame"] { border-radius: var(--radius); overflow:hidden; }
</style>
"""

# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────
def get_algo_description(algo_name):
    descs = {
        "1. Sabit Gün – Döngüsel Yer (Önerilen)": "📌 Öğretmenin nöbet günü sabittir (Müsaitlik Matrisi 🟢 günler). Görev yeri her nöbette döngüsel değişir. Tüm bölgeler eşit kullanılır.",
        "2. Sabit Gün – Sabit Yer": "📌 Hem nöbet günü hem görev yeri değişmez. Sabit kurallar sekmesinden ayarlanır.",
        "3. Tam Döngüsel (Gün ve Yer Değişir)": "📌 Her hafta hem gün hem yer döner. Müsait olan herkese eşit sırayla verilir. Maksimum adaleti sağlar.",
        "4. Adalet Puanı ve Dinamik Joker (Yapay Zeka)": "📌 Nöbet sayıları ve raporlu günleri analiz edip eşitliği sağlamaya çalışır. Boşlukları doldurur."
    }
    return f'<div class="info-box">{descs.get(algo_name, "")}</div>'

def fmt_date(d): return format_date(d, format="dd MMMM yyyy EEEE", locale='tr_TR')

def turkiye_tatilleri(yil):
    return {
        date(yil,1,1):"Yılbaşı",date(yil,4,23):"23 Nisan",date(yil,5,1):"1 Mayıs",
        date(yil,5,19):"19 Mayıs",date(yil,7,15):"15 Temmuz",date(yil,8,30):"30 Ağustos",date(yil,10,29):"29 Ekim",
    }

def metric_card(label, value, sub="", color="var(--blue)"):
    return f'<div class="metric-card" style="border-left-color:{color}"><div class="label">{label}</div><div class="value" style="color:{color}">{value}</div><div class="sub">{sub}</div></div>'

def get_veya_olustur_duty_setting(db, teacher_id):
    ayar = db.query(TeacherDutySetting).filter(TeacherDutySetting.teacher_id==teacher_id).first()
    if not ayar:
        ayar = TeacherDutySetting(teacher_id=teacher_id, hafta_ici_tutar=True, hafta_sonu_tutar=False)
        db.add(ayar); db.commit(); db.refresh(ayar)
    return ayar

def get_musaitlik(db, school_id):
    key = f"musaitlik_v9_{school_id}"
    if key not in st.session_state: st.session_state[key] = {}
    return st.session_state[key]

def set_musaitlik(db, school_id, teacher_id, gun, durum):
    key = f"musaitlik_v9_{school_id}"
    if key not in st.session_state: st.session_state[key] = {}
    if teacher_id not in st.session_state[key]: st.session_state[key][teacher_id] = {}
    st.session_state[key][teacher_id][gun] = durum

def yedek_olustur(db, school_id, yil, ay):
    ogretmenler = db.query(User).filter(User.school_id==school_id, User.role=="ogretmen").all()
    nobetler    = db.query(DutySchedule).filter(DutySchedule.school_id==school_id).all()
    bolgeler    = db.query(Location).filter(Location.school_id==school_id).all()
    tatiller    = db.query(HolidayManager).filter(HolidayManager.school_id==school_id).all()
    kurallar    = db.query(SchoolRule).filter(SchoolRule.school_id==school_id).all()
    mazeretler  = db.query(Leave).filter(Leave.school_id==school_id).all()
    yardimcilar = db.query(AssistantPrincipal).filter(AssistantPrincipal.school_id==school_id).all()
    payload = {
        "meta": {"school_id":school_id,"yil":yil,"ay":ay,"tarih":str(date.today()),"versiyon":"v9.0 Master"},
        "ogretmenler": [{"id":o.id,"name":o.name_surname,"branch":o.branch,"monthly":o.monthly_duty_count,"yearly":o.yearly_duty_count} for o in ogretmenler],
        "nobetler":    [{"date":str(n.date),"type":n.duty_type,"teacher_id":n.teacher_id,"location_id":n.location_id,"status":n.status} for n in nobetler],
        "bolgeler":    [{"id":b.id,"name":b.name,"type":b.location_type} for b in bolgeler],
        "tatiller":    [{"name":t.name,"date":str(t.date)} for t in tatiller],
        "kurallar":    [{"madde":k.madde,"sira":k.sira} for k in kurallar],
        "mazeretler":  [{"teacher_id":m.teacher_id,"type":m.leave_type,"start":str(m.start_date),"end":str(m.end_date)} for m in mazeretler],
        "yardimcilar": [{"name":y.name_surname} for y in yardimcilar],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
# DAĞITIM MOTORU 
# ─────────────────────────────────────────────
def akilli_dagitim(db, school_id, yil, ay, is_weekend=False, algoritma="1. Sabit Gün – Döngüsel Yer (Önerilen)"):
    duty_type = "Haftasonu" if is_weekend else "Ogretmen_Nobeti"
    tum_ogretmenler = db.query(User).filter(User.school_id==school_id, User.role=="ogretmen", User.status=="Aktif").all()

    ogretmenler = []
    for ogr in tum_ogretmenler:
        ayar = get_veya_olustur_duty_setting(db, ogr.id)
        if is_weekend and ayar.hafta_sonu_tutar: ogretmenler.append(ogr)
        elif not is_weekend and ayar.hafta_ici_tutar: ogretmenler.append(ogr)

    loc_filter = "Hafta Sonu" if is_weekend else "!Hafta Sonu"
    bolgeler = (
        db.query(Location).filter(Location.school_id==school_id, Location.location_type=="Hafta Sonu").all()
        if is_weekend else
        db.query(Location).filter(Location.school_id==school_id, Location.location_type!="Hafta Sonu").all()
    )

    if not ogretmenler: return False,"❌ İlgili nöbet tipine atanmış aktif öğretmen bulunamadı. Lütfen Kadro sekmesinden Hafta İçi/Sonu tercihlerinizi işaretleyin.",""
    if not bolgeler:    return False,f"❌ {'Hafta Sonu' if is_weekend else 'Hafta İçi'} türünde nöbet bölgesi tanımlı değil.",""

    bas = date(yil,ay,1)
    bit = date(yil,ay,calendar.monthrange(yil,ay)[1])

    # Temizlik ve Sayaç Geri Alma (Adalet Koruması)
    eski = db.query(DutySchedule).filter(
        DutySchedule.school_id==school_id,
        DutySchedule.date>=bas, DutySchedule.date<=bit,
        DutySchedule.duty_type==duty_type
    ).all()
    for en in eski:
        ogr_guncelle = db.query(User).filter(User.id == en.teacher_id).first()
        if ogr_guncelle:
            ogr_guncelle.monthly_duty_count = max(0, (ogr_guncelle.monthly_duty_count or 0) - 1)
            ogr_guncelle.yearly_duty_count = max(0, (ogr_guncelle.yearly_duty_count or 0) - 1)
            
        db.query(DutySubstitute).filter(DutySubstitute.duty_id==en.id).delete()
    db.query(DutySchedule).filter(DutySchedule.school_id==school_id, DutySchedule.date>=bas, DutySchedule.date<=bit, DutySchedule.duty_type==duty_type).delete()
    db.commit()

    oto_tatil = turkiye_tatilleri(yil)
    man_tatil = [t.date for t in db.query(HolidayManager).filter(HolidayManager.school_id==school_id).all()]
    mazeretler   = db.query(Leave).filter(Leave.school_id==school_id).all()
    sabitlemeler = db.query(FixedRule).filter(FixedRule.school_id==school_id).all()
    ozel_kapat   = db.query(DatePreference).all()
    b_idler      = [b.id for b in bolgeler]
    musaitlik    = get_musaitlik(db, school_id)

    toplam_atanan = sabit_atanan = joker_atanan = ekstra_atanan = 0
    haftalik_nobetler = {ogr.id: {} for ogr in ogretmenler}  

    def get_week_number(d): return d.isocalendar()[1]

    def siradaki_lokasyonu_bul(t_id, available_loc_ids):
        son = db.query(DutySchedule).filter(DutySchedule.teacher_id==t_id, DutySchedule.duty_type==duty_type).order_by(desc(DutySchedule.date)).first()
        if son and son.location_id in b_idler:
            mevcut_idx = b_idler.index(son.location_id)
            for i in range(1,len(b_idler)+1):
                yeni_idx = (mevcut_idx+i) % len(b_idler)
                if b_idler[yeni_idx] in available_loc_ids:
                    return b_idler[yeni_idx]
        return available_loc_ids[0] if available_loc_ids else None

    # FAZ 1: SABİTLEMELER
    for g in range(1, bit.day+1):
        islem_tarihi = date(yil,ay,g)
        hw = islem_tarihi.weekday()
        week_num = get_week_number(islem_tarihi)
        if islem_tarihi in oto_tatil or islem_tarihi in man_tatil: continue
        if is_weekend and hw<5: continue
        if not is_weekend and hw>=5: continue

        atanan_b = []; gunluk_atanan = []
        for sab in sabitlemeler:
            if sab.day_of_week==hw or sab.day_of_week is None:
                ogr = next((o for o in ogretmenler if o.id==sab.teacher_id), None)
                if not ogr: continue
                
                izinli = any(m.teacher_id==ogr.id and m.start_date<=islem_tarihi<=m.end_date for m in mazeretler)
                ozel_k = any(dp.teacher_id==ogr.id and dp.blocked_date==islem_tarihi for dp in ozel_kapat)
                
                if not izinli and not ozel_k and ogr.id not in gunluk_atanan:
                    bosta_idler = [b for b in b_idler if b not in atanan_b]
                    hedef = None
                    if algoritma=="2. Sabit Gün – Sabit Yer" and sab.location_id and sab.location_id in bosta_idler:
                        hedef = sab.location_id
                    elif bosta_idler:
                        hedef = siradaki_lokasyonu_bul(ogr.id, bosta_idler)
                    if hedef:
                        nbt = DutySchedule(school_id=school_id,date=islem_tarihi,duty_type=duty_type,teacher_id=ogr.id,location_id=hedef,status="Asil")
                        db.add(nbt); db.commit(); db.refresh(nbt)
                        ogr.monthly_duty_count = (ogr.monthly_duty_count or 0)+1
                        ogr.yearly_duty_count = (ogr.yearly_duty_count or 0)+1
                        atanan_b.append(hedef); gunluk_atanan.append(ogr.id)
                        haftalik_nobetler[ogr.id][week_num] = haftalik_nobetler[ogr.id].get(week_num,0)+1
                        sabit_atanan+=1; toplam_atanan+=1

    # FAZ 2: BİRİNCİ NÖBETLER
    for g in range(1, bit.day+1):
        islem_tarihi = date(yil,ay,g)
        hw = islem_tarihi.weekday()
        week_num = get_week_number(islem_tarihi)
        if islem_tarihi in oto_tatil or islem_tarihi in man_tatil: continue
        if is_weekend and hw<5: continue
        if not is_weekend and hw>=5: continue

        atanan_b = [n.location_id for n in db.query(DutySchedule).filter(DutySchedule.date==islem_tarihi).all()]
        gunluk_atanan = [n.teacher_id for n in db.query(DutySchedule).filter(DutySchedule.date==islem_tarihi).all()]
        bosta_bolgeler = [b for b in bolgeler if b.id not in atanan_b]
        if not bosta_bolgeler: continue

        ogr_primary  = []
        for o in ogretmenler:
            if o.id in gunluk_atanan: continue
            izin = any(m.teacher_id==o.id and m.start_date<=islem_tarihi<=m.end_date for m in mazeretler)
            engel= any(dp.teacher_id==o.id and dp.blocked_date==islem_tarihi for dp in ozel_kapat)
            stat = STATUS_MAP.get(musaitlik.get(o.id,{}).get(hw,"🟢 1. Nöbet (Kesin İstiyorum)"), "primary")
            if not izin and not engel and stat=="primary" and haftalik_nobetler[o.id].get(week_num,0)==0:
                ogr_primary.append(o)
        
        ogr_primary.sort(key=lambda x: (x.monthly_duty_count or 0, x.yearly_duty_count or 0))

        for secilen in ogr_primary:
            if not bosta_bolgeler: break
            hedef_bolge = bosta_bolgeler.pop(0)
            bosta_idler = [b.id for b in [hedef_bolge]+bosta_bolgeler]
            final_loc_id = siradaki_lokasyonu_bul(secilen.id, bosta_idler)
            if final_loc_id and final_loc_id != hedef_bolge.id:
                alt = next((b for b in [hedef_bolge]+bosta_bolgeler if b.id==final_loc_id), None)
                if alt and alt in bosta_bolgeler: bosta_bolgeler.remove(alt); hedef_bolge = alt
            nbt = DutySchedule(school_id=school_id,date=islem_tarihi,duty_type=duty_type,teacher_id=secilen.id,location_id=hedef_bolge.id,status="Asil")
            db.add(nbt); db.commit(); db.refresh(nbt)
            secilen.monthly_duty_count = (secilen.monthly_duty_count or 0)+1
            secilen.yearly_duty_count  = (secilen.yearly_duty_count  or 0)+1
            gunluk_atanan.append(secilen.id)
            haftalik_nobetler[secilen.id][week_num] = haftalik_nobetler[secilen.id].get(week_num,0)+1
            toplam_atanan+=1

    # FAZ 3: JOKER (İKİNCİ NÖBETLER)
    for g in range(1, bit.day+1):
        islem_tarihi = date(yil,ay,g)
        hw = islem_tarihi.weekday()
        week_num = get_week_number(islem_tarihi)
        if islem_tarihi in oto_tatil or islem_tarihi in man_tatil: continue
        if is_weekend and hw<5: continue
        if not is_weekend and hw>=5: continue

        atanan_b = [n.location_id for n in db.query(DutySchedule).filter(DutySchedule.date==islem_tarihi).all()]
        gunluk_atanan = [n.teacher_id for n in db.query(DutySchedule).filter(DutySchedule.date==islem_tarihi).all()]
        bosta_bolgeler = [b for b in bolgeler if b.id not in atanan_b]
        if not bosta_bolgeler: continue

        ogr_joker = []
        for o in ogretmenler:
            if o.id in gunluk_atanan: continue
            izin = any(m.teacher_id==o.id and m.start_date<=islem_tarihi<=m.end_date for m in mazeretler)
            engel= any(dp.teacher_id==o.id and dp.blocked_date==islem_tarihi for dp in ozel_kapat)
            stat = STATUS_MAP.get(musaitlik.get(o.id,{}).get(hw,"🟢 1. Nöbet (Kesin İstiyorum)"), "primary")
            if not izin and not engel and stat in ("primary","joker"):
                ogr_joker.append(o)
                
        ogr_joker.sort(key=lambda x: (x.monthly_duty_count or 0, x.yearly_duty_count or 0))

        for secilen in ogr_joker:
            if not bosta_bolgeler: break
            hedef_bolge = bosta_bolgeler.pop(0)
            nbt = DutySchedule(school_id=school_id,date=islem_tarihi,duty_type=duty_type,teacher_id=secilen.id,location_id=hedef_bolge.id,status="Joker")
            db.add(nbt); db.commit(); db.refresh(nbt)
            secilen.monthly_duty_count = (secilen.monthly_duty_count or 0)+1
            secilen.yearly_duty_count  = (secilen.yearly_duty_count  or 0)+1
            gunluk_atanan.append(secilen.id)
            haftalik_nobetler[secilen.id][week_num] = haftalik_nobetler[secilen.id].get(week_num,0)+1
            joker_atanan+=1; toplam_atanan+=1

    # FAZ 4: ÜÇÜNCÜ NÖBETLER
    for g in range(1, bit.day+1):
        islem_tarihi = date(yil,ay,g)
        hw = islem_tarihi.weekday()
        week_num = get_week_number(islem_tarihi)
        if islem_tarihi in oto_tatil or islem_tarihi in man_tatil: continue
        if is_weekend and hw<5: continue
        if not is_weekend and hw>=5: continue

        atanan_b = [n.location_id for n in db.query(DutySchedule).filter(DutySchedule.date==islem_tarihi).all()]
        gunluk_atanan = [n.teacher_id for n in db.query(DutySchedule).filter(DutySchedule.date==islem_tarihi).all()]
        bosta_bolgeler = [b for b in bolgeler if b.id not in atanan_b]
        if not bosta_bolgeler: continue

        ogr_extra = []
        for o in ogretmenler:
            if o.id in gunluk_atanan: continue
            izin = any(m.teacher_id==o.id and m.start_date<=islem_tarihi<=m.end_date for m in mazeretler)
            engel= any(dp.teacher_id==o.id and dp.blocked_date==islem_tarihi for dp in ozel_kapat)
            stat = STATUS_MAP.get(musaitlik.get(o.id,{}).get(hw,"🟢 1. Nöbet (Kesin İstiyorum)"), "primary")
            if not izin and not engel and stat != "unavail":
                ogr_extra.append(o)
                
        ogr_extra.sort(key=lambda x: (x.monthly_duty_count or 0, x.yearly_duty_count or 0))

        for secilen in ogr_extra:
            if not bosta_bolgeler: break
            hedef_bolge = bosta_bolgeler.pop(0)
            nbt = DutySchedule(school_id=school_id,date=islem_tarihi,duty_type=duty_type,teacher_id=secilen.id,location_id=hedef_bolge.id,status="3. Nöbet")
            db.add(nbt); db.commit(); db.refresh(nbt)
            secilen.monthly_duty_count = (secilen.monthly_duty_count or 0)+1
            secilen.yearly_duty_count  = (secilen.yearly_duty_count  or 0)+1
            gunluk_atanan.append(secilen.id)
            haftalik_nobetler[secilen.id][week_num] = haftalik_nobetler[secilen.id].get(week_num,0)+1
            ekstra_atanan+=1; toplam_atanan+=1

    # FAZ 5: YEDEK ATAMA (Sadece Excel İçin)
    for g in range(1, bit.day+1):
        islem_tarihi = date(yil,ay,g)
        hw = islem_tarihi.weekday()
        if islem_tarihi in oto_tatil or islem_tarihi in man_tatil: continue
        if is_weekend and hw<5: continue
        if not is_weekend and hw>=5: continue

        atanan_nobetler_bugun = db.query(DutySchedule).filter(DutySchedule.date==islem_tarihi).all()
        gunluk_atanan = [n.teacher_id for n in atanan_nobetler_bugun]
        
        musait_yedekler = [o for o in ogretmenler if o.id not in gunluk_atanan and not any(m.teacher_id==o.id and m.start_date<=islem_tarihi<=m.end_date for m in mazeretler) and not any(dp.teacher_id==o.id and dp.blocked_date==islem_tarihi for dp in ozel_kapat)]
        musait_yedekler.sort(key=lambda x: (x.monthly_duty_count or 0))
        
        for n_bugun in atanan_nobetler_bugun:
            if musait_yedekler:
                secilen_yedek = musait_yedekler.pop(0)
                db.add(DutySubstitute(duty_id=n_bugun.id, substitute_teacher_id=secilen_yedek.id))
                gunluk_atanan.append(secilen_yedek.id)

    db.commit()

    arsiv_label = f"Otomatik – {MONTHS_TR[ay-1]} {yil}"
    db.query(BackupRecord).filter(BackupRecord.school_id==school_id, BackupRecord.label==arsiv_label).delete()
    db.add(BackupRecord(school_id=school_id,label=arsiv_label,created_at=str(datetime.now()),payload_b64=base64.b64encode(yedek_olustur(db,school_id,yil,ay).encode()).decode()))
    db.commit()

    rapor = f"""
#### 🧠 Dağıtım Özeti
* Nöbetler **{algoritma}** motoruyla dağıtıldı.
* **Toplam Atanan:** {toplam_atanan} | **Joker:** {joker_atanan} | **Ekstra:** {ekstra_atanan}
    """
    return True, f"✅ Nöbetler '{algoritma}' motoruyla başarıyla dağıtıldı!", rapor

# ─────────────────────────────────────────────
# PDF OLUŞTURUCU (ÇİZGİSİZ, SIFIR BOŞLUKLU)
# ─────────────────────────────────────────────
def pdf_olustur(okul, sec_yil, sec_ay, bolgeler_hi, pdf_rows, kural_listesi, hazirlayan):
    kural_html = "".join(f"<li>{k}</li>" for k in kural_listesi)
    th_cols    = "".join(f"<th>{b.name.upper()}</th>" for b in bolgeler_hi)
    tbody      = ""

    for row in pdf_rows:
        gun_tarihi = None
        for g2 in range(1, calendar.monthrange(sec_yil,sec_ay)[1]+1):
            d2 = date(sec_yil,sec_ay,g2)
            if d2.weekday()>=5: continue
            if fmt_date(d2)==row["Tarih/Gün"]: gun_tarihi=d2; break
        
        is_friday  = (gun_tarihi is not None and gun_tarihi.weekday()==4)
        week_sep   = "border-bottom:3px solid #0f172a!important;" if is_friday else ""

        if row.get("Durum"):
            colspan = len(bolgeler_hi)+2 
            tbody += f'<tr class="holiday" style="{week_sep}"><td style="text-align:left;font-weight:700;white-space:nowrap;{week_sep}">{row["Tarih/Gün"]}</td><td colspan="{colspan}" style="{week_sep}">{row["Durum"]}</td></tr>'
        else:
            tds = "".join(f'<td style="{week_sep}">{row.get(b.name,"-")}</td>' for b in bolgeler_hi)
            tbody += f'<tr style="{week_sep}"><td style="text-align:left;font-weight:600;white-space:nowrap;{week_sep}">{row["Tarih/Gün"]}</td>{tds}<td style="font-weight:700;{week_sep}">{row.get("Müdür Yrd.","")}</td><td style="{week_sep}"></td></tr>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;800&display=swap');
*{{box-sizing:border-box;margin:0;padding:0;}}
:root{{--fs:9pt;--pad:5px;}}
body{{font-family:'DM Sans',Arial,sans-serif;background:#fff;color:#111;}}
@media print{{@page{{size:A4 landscape;margin:5mm 8mm;}} .no-print{{display:none!important;}} body{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}}}
.no-print{{position:sticky;top:0;z-index:999;background:#1d4ed8;padding:10px 14px;display:flex;gap:8px;align-items:center;border-radius:0 0 8px 8px;margin-bottom:8px;}}
.btn-sz{{background:rgba(255,255,255,.2);color:#fff;border:none;padding:5px 12px;border-radius:5px;font-weight:700;cursor:pointer;}}
#sz-ind{{color:#fff;font-size:12px;font-weight:700;min-width:70px;text-align:center;}}
.btn-pr{{background:#fff;color:#1d4ed8;border:none;padding:7px 18px;border-radius:5px;font-weight:700;cursor:pointer;}}
.wrap{{width:97%;margin:0 auto;}}
.school-title{{text-align:center;font-weight:800;font-size:calc(var(--fs) + 2.5pt);line-height:1.3;margin-bottom:5px;}}
table{{width:100%;border-collapse:collapse;font-size:var(--fs);table-layout:auto;margin: 0 auto;}}
th{{background:#0f1f3d;color:#fff;padding:var(--pad) 2px;font-weight:800;text-align:center;border:1px solid #64748b;}}
td{{border:1px solid #94a3b8;padding:var(--pad) 2px;text-align:center;color:#0f172a;}}
.holiday td{{background:#fef2f2!important;color:#b91c1c;font-weight:700;}}
tr[style*="border-bottom:3px solid #0f172a"] td {{ border-bottom:3px solid #0f172a !important; }}
.rules-box{{border:1px solid #94a3b8;border-top:none;padding:4px 10px;font-size:calc(var(--fs) - 1pt);background:#f8fafc;margin-bottom: 0px !important;}}
.rules-box strong{{display:block;font-weight:800;margin-bottom:2px;}}
.rules-box ol{{padding-left:14px;margin:0;}}
.rules-box li{{line-height:1.15;margin-bottom:1px;}}
.sigs{{display:flex;justify-content:space-between;margin-top:0px !important;padding-top:0px !important;font-size:calc(var(--fs) - 0.5pt);text-align:center;}}
.sig-box .sig-line{{border-top:none;margin-top:25px;padding-top:2px;font-weight:700;width:220px;}}
.small-text {{ font-size: 8pt; color: #64748b; text-align: left; margin-top: 5px; }}
</style></head><body>
<div class="no-print"><button class="btn-sz" onclick="changeSize(-1)">➖</button><span id="sz-ind">Boyut: 9</span><button class="btn-sz" onclick="changeSize(1)">➕</button><button class="btn-pr" onclick="window.print()">🖨️ PDF Yazdır</button></div>
<div class="wrap">
<div class="school-title">T.C.<br>{okul.name.upper()} MÜDÜRLÜĞÜ<br>{MONTHS_TR[sec_ay-1].upper()} {sec_yil} ÖĞRETMEN NÖBET ÇİZELGESİ</div>
<table><thead><tr><th style="text-align:left;white-space:nowrap">TARİH / GÜN</th>{th_cols}<th>MD. YRD.</th><th>İMZA</th></tr></thead><tbody>{tbody}</tbody></table>
<div class="rules-box"><strong>📋 NÖBET YÖNERGESİ</strong><ol>{kural_html}</ol></div>
<div class="sigs">
  <div class="sig-box"><div class="sig-line">HAZIRLAYAN<br>{hazirlayan}<br>Müdür Yardımcısı</div></div>
  <div class="sig-box"><div class="sig-line">ONAYLAYAN<br>{date.today().strftime('%d.%m.%Y')}<br>{okul.manager_name}<br>Okul Müdürü</div></div>
</div>
<div class="small-text">Not: <b>Koyu renkli (kalın)</b> isimler 2. nöbet (Joker) tutanları, <b>*yıldızlı</b> isimler ise o haftaki 3. nöbet (ekstra) görevlerini belirtir.</div>
</div>
<script>var cv=9;function changeSize(d){{cv=Math.min(14,Math.max(5,parseFloat((cv+d*0.1).toFixed(1))));document.getElementById('sz-ind').textContent='Boyut: '+cv;document.documentElement.style.setProperty('--fs',cv+'pt');var p=Math.max(1,Math.floor(cv/2));document.documentElement.style.setProperty('--pad',p+'px');}}</script>
</body></html>"""

# ─────────────────────────────────────────────
# ANA RENDER FONKSİYONU
# ─────────────────────────────────────────────
def render_school_admin():
    db      = get_db()
    idareci = db.query(User).filter(User.id==st.session_state['kullanici_id']).first()
    okul    = db.query(School).filter(School.id==idareci.school_id).first()

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    if st.session_state.get('super_admin_return'):
        if st.button("🔙 Süper Admin Paneline Geri Dön", type="primary", use_container_width=True):
            st.session_state['kullanici_id']  = st.session_state['gercek_admin_id']
            st.session_state['kullanici_rolu']= 'super_admin'
            st.session_state['super_admin_return'] = False
            st.rerun()

    kurallar = db.query(SchoolRule).filter(SchoolRule.school_id==okul.id).all()
    if not kurallar:
        varsayilan = ["Nöbet görevine ders başlamadan 30 dakika önce başlanır.", "Öğrencilerin can güvenliğinden sorumludur."]
        for i,m in enumerate(varsayilan,1): db.add(SchoolRule(school_id=okul.id,madde=m,sira=i))
        db.commit()

    ogretmenler  = db.query(User).filter(User.school_id==okul.id, User.role=="ogretmen").all()
    aktif_ogr    = [o for o in ogretmenler if getattr(o,'status','Aktif')=='Aktif']
    md_yard      = db.query(AssistantPrincipal).filter(AssistantPrincipal.school_id==okul.id).all()
    bolgeler_all = db.query(Location).filter(Location.school_id==okul.id).all()
    tatiller_all = db.query(HolidayManager).filter(HolidayManager.school_id==okul.id).all()

    st.markdown(f'<div class="app-header"><div style="font-size:2.5rem;">🏫</div><div><h2>{okul.name} Yönetim Merkezi</h2><small>Okul Müdürü: <b>{okul.manager_name}</b> &nbsp;|&nbsp; Profesyonel Nöbet Otomasyon Sistemi v9.0</small></div></div>', unsafe_allow_html=True)

    if not st.session_state.get('super_admin_return'):
        st.columns([9,1])[1].button("🚪 Çıkış", on_click=lambda: st.session_state.clear() or st.rerun(), use_container_width=True)

    m1,m2,m3,m4 = st.columns(4)
    m1.markdown(metric_card("Aktif Kadro", len(aktif_ogr), f"Toplam {len(ogretmenler)} kayıtlı"), unsafe_allow_html=True)
    m2.markdown(metric_card("Nöbet Alanı", len(bolgeler_all), "Hafta içi + sonu", "var(--success)"), unsafe_allow_html=True)
    m3.markdown(metric_card("Müdür Yardımcısı", len(md_yard), "Çizelge rotasyonlu", "#8b5cf6"), unsafe_allow_html=True)
    m4.markdown(metric_card("Açık Tutanak", db.query(IncidentLog).filter(IncidentLog.school_id==okul.id, IncidentLog.is_resolved==False).count(), "Açık Tutanaklar", "var(--danger)"), unsafe_allow_html=True)

    st.write("")

    tabs = st.tabs([
        "📋 Hafta İçi",
        "🏖️ Hafta Sonu",
        "🗓️ Müsaitlik Matrisi",
        "📌 İzin & Sabit",
        "🔄 Nöbet Değişimi",
        "⚖️ Yönerge",
        "👥 Kadro & İdareci",
        "📍 Bölgeler",
        "📝 Tutanak",
        "📊 İstatistik",
        "🗄️ Arşiv"
    ])

    # 1. HAFTA İÇİ
    with tabs[0]:
        st.markdown('<div class="section-title">Hafta İçi Nöbet Programı</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 2])
        sec_yil = c1.number_input("Yıl", value=date.today().year, min_value=2020, key="hi_yil")
        sec_ay  = c2.selectbox("Ay", list(range(1, 13)), index=date.today().month - 1, format_func=lambda x: MONTHS_TR[x - 1], key="hi_ay")
        sec_algo = c3.selectbox("🧠 Algoritma Seçimi", ALGO_LISTESI, key="hi_algo")

        st.markdown(get_algo_description(sec_algo), unsafe_allow_html=True)
        col_dist, col_clear = st.columns([3, 1])
        
        if col_dist.button("✨ Otomatik Dağıt (Hafta İçi)", type="primary", use_container_width=True):
            ok, msg, rapor = akilli_dagitim(db, okul.id, sec_yil, sec_ay, is_weekend=False, algoritma=sec_algo)
            if ok: 
                st.session_state['ai_rapor_hi'] = rapor
                st.success(msg)
                st.rerun()
            else: 
                st.error(msg)
                
        if col_clear.button("🗑️ Temizle", use_container_width=True):
            bas, bit = date(sec_yil, sec_ay, 1), date(sec_yil, sec_ay, calendar.monthrange(sec_yil, sec_ay)[1])
            eski = db.query(DutySchedule).filter(DutySchedule.school_id == okul.id, DutySchedule.date >= bas, DutySchedule.date <= bit, DutySchedule.duty_type == "Ogretmen_Nobeti").all()
            for e in eski:
                ogr_guncelle = db.query(User).filter(User.id == e.teacher_id).first()
                if ogr_guncelle:
                    ogr_guncelle.monthly_duty_count = max(0, (ogr_guncelle.monthly_duty_count or 0) - 1)
                    ogr_guncelle.yearly_duty_count = max(0, (ogr_guncelle.yearly_duty_count or 0) - 1)
                db.query(DutySubstitute).filter(DutySubstitute.duty_id==e.id).delete()
            db.query(DutySchedule).filter(DutySchedule.school_id == okul.id, DutySchedule.date >= bas, DutySchedule.date <= bit, DutySchedule.duty_type == "Ogretmen_Nobeti").delete()
            db.commit()
            st.success("Temizlendi.")
            st.session_state.pop('ai_rapor_hi', None)
            st.rerun()

        if 'ai_rapor_hi' in st.session_state: 
            st.markdown(f'<div class="ai-box">{st.session_state["ai_rapor_hi"]}</div>', unsafe_allow_html=True)

        program = db.query(DutySchedule).filter(DutySchedule.school_id == okul.id, extract('month', DutySchedule.date) == sec_ay, extract('year',  DutySchedule.date) == sec_yil, DutySchedule.duty_type == "Ogretmen_Nobeti").all()

        if program:
            bolgeler_hi = [b for b in bolgeler_all if b.location_type != "Hafta Sonu"]
            oto_tatil = turkiye_tatilleri(sec_yil); man_tatil = {t.date: t.name for t in tatiller_all}
            hazirlayan = st.selectbox("Hazırlayan:", [m.name_surname for m in md_yard] if md_yard else ["Müdür Yardımcısı"], key="hi_mdyrd")

            excel_rows = []; pdf_rows = []; md_idx = 0
            for g in range(1, calendar.monthrange(sec_yil, sec_ay)[1] + 1):
                t = date(sec_yil, sec_ay, g)
                if t.weekday() >= 5: continue
                row_ex = {"Tarih/Gün": fmt_date(t)}; row_pdf = {"Tarih/Gün": fmt_date(t)}
                
                if t in oto_tatil or t in man_tatil:
                    row_ex["Durum"] = row_pdf["Durum"] = oto_tatil.get(t) or man_tatil.get(t)
                else:
                    row_ex["Durum"] = ""; row_pdf["Durum"] = ""
                    yedekler_metni = []
                    for b in bolgeler_hi:
                        kisi_ex = "-"; kisi_pdf = "-"
                        for p in program:
                            if p.date == t and p.location_id == b.id:
                                o = next((og for og in ogretmenler if og.id == p.teacher_id), None)
                                if o:
                                    not_ek = f" ({p.status})" if "Değişim" in p.status else ""
                                    if p.status == "Joker":
                                        kisi_ex  = f"{o.name_surname} (Joker){not_ek}"
                                        kisi_pdf = f"<b>{o.name_surname}</b>"
                                    elif p.status == "3. Nöbet":
                                        kisi_ex  = f"{o.name_surname} (3. Nöbet){not_ek}"
                                        kisi_pdf = f"*<b>{o.name_surname}</b>"
                                    else:
                                        kisi_ex = f"{o.name_surname}{not_ek}"
                                        kisi_pdf = o.name_surname
                                        
                                ydk = db.query(DutySubstitute).filter(DutySubstitute.duty_id == p.id).first()
                                if ydk:
                                    yo = next((og for og in ogretmenler if og.id == ydk.substitute_teacher_id), None)
                                    if yo and yo.name_surname not in yedekler_metni: yedekler_metni.append(yo.name_surname)
                        row_ex[b.name] = kisi_ex; row_pdf[b.name] = kisi_pdf
                    row_ex["Yedek (Sadece Excel)"] = ", ".join(yedekler_metni) if yedekler_metni else "-"
                    row_ex["Müdür Yrd."] = md_yard[md_idx % len(md_yard)].name_surname if md_yard else ""
                    row_pdf["Müdür Yrd."] = row_ex["Müdür Yrd."]
                    md_idx += 1
                excel_rows.append(row_ex); pdf_rows.append(row_pdf)

            st.dataframe(pd.DataFrame(excel_rows), hide_index=True, use_container_width=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w:
                pd.DataFrame(excel_rows).to_excel(w, index=False, sheet_name='Nöbet')
                for col in w.sheets['Nöbet'].columns: w.sheets['Nöbet'].column_dimensions[col[0].column_letter].width = 25
            st.download_button("📊 Excel İndir (Yedekler Excel'dedir)", data=buf.getvalue(), file_name=f"Nobet_{MONTHS_TR[sec_ay-1]}_{sec_yil}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            kural_listesi = [k.madde for k in sorted(kurallar, key=lambda x: x.sira or 0)]
            html_pdf = pdf_olustur(okul, sec_yil, sec_ay, bolgeler_hi, pdf_rows, kural_listesi, hazirlayan)
            st.divider(); st.components.v1.html(html_pdf, height=850, scrolling=True)

    # 2. HAFTA SONU (DYK)
    with tabs[1]:
        st.markdown('<div class="section-title">Hafta Sonu / DYK Nöbet Programı</div>', unsafe_allow_html=True)
        hs1, hs2, hs3 = st.columns([1, 1, 2])
        hs_yil = hs1.number_input("Yıl", value=date.today().year, min_value=2020, key="hs_yil")
        hs_ay  = hs2.selectbox("Ay", list(range(1, 13)), index=date.today().month - 1, format_func=lambda x: MONTHS_TR[x - 1], key="hs_ay")
        hs_algo = hs3.selectbox("🧠 Algoritma Seçimi", ALGO_LISTESI, key="hs_algo")
        st.markdown(get_algo_description(hs_algo), unsafe_allow_html=True)

        c_da, c_cl = st.columns([3, 1])
        if c_da.button("✨ Otomatik Dağıt (Hafta Sonu)", type="primary", use_container_width=True):
            ok, msg, rapor = akilli_dagitim(db, okul.id, hs_yil, hs_ay, is_weekend=True, algoritma=hs_algo)
            if ok: 
                st.session_state['ai_rapor_hs'] = rapor
                st.success(msg)
                st.rerun()
            else: 
                st.error(msg)
                
        if c_cl.button("🗑️ Temizle  ", use_container_width=True):
            bas, bit = date(hs_yil, hs_ay, 1), date(hs_yil, hs_ay, calendar.monthrange(hs_yil, hs_ay)[1])
            eski = db.query(DutySchedule).filter(DutySchedule.school_id == okul.id, DutySchedule.date >= bas, DutySchedule.date <= bit, DutySchedule.duty_type == "Haftasonu").all()
            for e in eski:
                ogr_guncelle = db.query(User).filter(User.id == e.teacher_id).first()
                if ogr_guncelle:
                    ogr_guncelle.monthly_duty_count = max(0, (ogr_guncelle.monthly_duty_count or 0) - 1)
                    ogr_guncelle.yearly_duty_count = max(0, (ogr_guncelle.yearly_duty_count or 0) - 1)
                db.query(DutySubstitute).filter(DutySubstitute.duty_id==e.id).delete()
            db.query(DutySchedule).filter(DutySchedule.school_id == okul.id, DutySchedule.date >= bas, DutySchedule.date <= bit, DutySchedule.duty_type == "Haftasonu").delete()
            db.commit()
            st.success("Silindi.")
            st.session_state.pop('ai_rapor_hs', None)
            st.rerun()

        if 'ai_rapor_hs' in st.session_state: 
            st.markdown(f'<div class="ai-box">{st.session_state["ai_rapor_hs"]}</div>', unsafe_allow_html=True)

        hs_prog = db.query(DutySchedule).filter(DutySchedule.school_id == okul.id, extract('month', DutySchedule.date) == hs_ay, extract('year',  DutySchedule.date) == hs_yil, DutySchedule.duty_type == "Haftasonu").all()
        bolgeler_hs = [b for b in bolgeler_all if b.location_type == "Hafta Sonu"]
        
        if hs_prog:
            oto_tatil2 = turkiye_tatilleri(hs_yil); man_tatil2 = {t.date: t.name for t in tatiller_all}; rows_hs = []
            for g in range(1, calendar.monthrange(hs_yil, hs_ay)[1] + 1):
                t = date(hs_yil, hs_ay, g)
                if t.weekday() < 5 or t in oto_tatil2 or t in man_tatil2: continue
                row = {"Tarih/Gün": fmt_date(t), "Gün": DAYS_TR[t.weekday()]}
                for b in bolgeler_hs:
                    kisi = "-"
                    for p in hs_prog:
                        if p.date == t and p.location_id == b.id:
                            o = next((og for og in ogretmenler if og.id == p.teacher_id), None)
                            if o:
                                if p.status == "Joker": kisi = f"**{o.name_surname}**"
                                elif p.status == "3. Nöbet": kisi = f"* **{o.name_surname}**"
                                else: kisi = o.name_surname
                    row[b.name] = kisi
                rows_hs.append(row)
            if rows_hs:
                st.dataframe(pd.DataFrame(rows_hs), hide_index=True, use_container_width=True)
                buf2 = io.BytesIO()
                with pd.ExcelWriter(buf2, engine='openpyxl') as w: pd.DataFrame(rows_hs).to_excel(w, index=False, sheet_name='HafSonu')
                st.download_button("📊 Hafta Sonu Excel İndir", data=buf2.getvalue(), file_name=f"HafSonu_{MONTHS_TR[hs_ay-1]}_{hs_yil}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # 3. İNTERAKTİF MÜSAİTLİK MATRİSİ (7 GÜNLÜK TAM SÜRÜM)
    with tabs[2]:
        st.markdown('<div class="section-title">7 Günlük İnteraktif Müsaitlik Matrisi</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="display: flex; gap: 15px; margin-bottom: 15px; font-size: 0.85rem; background: #fff; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;">
            <div>🟢 <b>1. Nöbet (Talep):</b> Temel nöbet önceliği.</div>
            <div>🟡 <b>2. Nöbet (Joker):</b> Boşlukta 2. nöbet yazılabilir.</div>
            <div>🔵 <b>3. Nöbet (Ekstra):</b> Kritik açıkta 3. nöbet yazılabilir.</div>
            <div>🔴 <b>Müsait Değil:</b> Kesinlikle görev verilmez.</div>
        </div>
        """, unsafe_allow_html=True)

        musaitlik_db = get_musaitlik(db, okul.id)
        matrix_rows = []
        for o in ogretmenler:
            row_dict = {"ID": o.id, "Öğretmen Adı Soyadı": o.name_surname}
            for i, d_name in enumerate(DAYS_TR):
                raw_stat = musaitlik_db.get(o.id, {}).get(i, "primary")
                row_dict[d_name] = REV_STATUS_MAP.get(raw_stat, "🟢 1. Nöbet (Kesin İstiyorum)")
            matrix_rows.append(row_dict)

        if matrix_rows:
            df_matrix = pd.DataFrame(matrix_rows)
            edited_matrix = st.data_editor(
                df_matrix, hide_index=True, use_container_width=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "Öğretmen Adı Soyadı": st.column_config.TextColumn("Öğretmen Adı Soyadı", disabled=True),
                    "Pazartesi": st.column_config.SelectboxColumn("Pazartesi", options=list(STATUS_MAP.keys())),
                    "Salı": st.column_config.SelectboxColumn("Salı", options=list(STATUS_MAP.keys())),
                    "Çarşamba": st.column_config.SelectboxColumn("Çarşamba", options=list(STATUS_MAP.keys())),
                    "Perşembe": st.column_config.SelectboxColumn("Perşembe", options=list(STATUS_MAP.keys())),
                    "Cuma": st.column_config.SelectboxColumn("Cuma", options=list(STATUS_MAP.keys())),
                    "Cumartesi": st.column_config.SelectboxColumn("Cumartesi", options=list(STATUS_MAP.keys())),
                    "Pazar": st.column_config.SelectboxColumn("Pazar", options=list(STATUS_MAP.keys())),
                }
            )

            if st.button("💾 Tüm Matrisi Topluca Kaydet", type="primary", use_container_width=True):
                for _, r in edited_matrix.iterrows():
                    t_id = int(r["ID"])
                    for i, d_name in enumerate(DAYS_TR):
                        set_musaitlik(db, okul.id, t_id, i, STATUS_MAP[r[d_name]])
                st.success("✅ Tüm kadro müsaitlik öncelikleri başarıyla güncellendi!"); st.rerun()
                st.divider()
        st.markdown('<div class="section-title">Hafta İçi / Hafta Sonu Havuz Tercihleri</div>', unsafe_allow_html=True)
        st.info("Öğretmenlerin genel olarak Hafta İçi veya Hafta Sonu nöbet havuzuna dahil olup olmayacağını buradan seçebilirsiniz (Hızlı Tik Sistemi).")
        
        ogr_veri = []
        for o in ogretmenler:
            ayar = get_veya_olustur_duty_setting(db, o.id)
            ogr_veri.append({
                "ID": o.id, 
                "Ad Soyad": o.name_surname, 
                "Hafta İçi": ayar.hafta_ici_tutar, 
                "Hafta Sonu": ayar.hafta_sonu_tutar
            })
            
        if ogr_veri:
            ed_df = st.data_editor(
                pd.DataFrame(ogr_veri),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "Ad Soyad": st.column_config.TextColumn("Ad Soyad", disabled=True),
                    "Hafta İçi": st.column_config.CheckboxColumn("Hafta İçi (✓)"),
                    "Hafta Sonu": st.column_config.CheckboxColumn("Hafta Sonu (✓)")
                }
            )
            if st.button("💾 Havuz Tercihlerini Kaydet", type="primary", key="havuz_kaydet_tab2_btn"):
                for _, r in ed_df.iterrows():
                    db.query(TeacherDutySetting).filter(TeacherDutySetting.teacher_id == int(r["ID"])).update({
                        "hafta_ici_tutar": bool(r["Hafta İçi"]),
                        "hafta_sonu_tutar": bool(r["Hafta Sonu"])
                    })
                db.commit()
                st.success("✅ Havuz tercihleri başarıyla kaydedildi!")
                st.rerun()
                
    # 4. MATRİS & İZİN (TARİH ARALIĞI KAPATMA)
    with tabs[3]:
        c_mat, c_sab = st.columns(2)
        with c_mat:
            st.markdown('<div class="section-title">Gelişmiş Tarih Aralığı Kapatma</div>', unsafe_allow_html=True)
            st.info("Hocanın raporlu olduğu veya izne ayrıldığı tarih aralığını seçin. Sistem aralıktaki tüm günleri nöbete kapatır.")
            with st.form("tarih_kapat_form"):
                o_sec = st.selectbox("Öğretmen", [(o.id, o.name_surname) for o in ogretmenler], format_func=lambda x: x[1])
                range_bas = st.date_input("Kapatma Başlangıç Tarihi")
                range_bit = st.date_input("Kapatma Bitiş Tarihi")
                if st.form_submit_button("🔒 Belirtilen Aralığı Engelle", type="primary"):
                    if range_bas <= range_bit:
                        curr = range_bas
                        while curr <= range_bit:
                            db.add(DatePreference(teacher_id=o_sec[0], blocked_date=curr))
                            curr += timedelta(days=1)
                        db.commit(); st.success("✅ Seçilen tarih aralığı başarıyla nöbete kapatıldı!"); st.rerun()
                    else: st.error("Hata: Başlangıç tarihi bitişten büyük olamaz.")

            kap = db.query(DatePreference).all()
            if kap:
                kap_data = [{"#": dp.id, "Öğretmen": db.query(User).get(dp.teacher_id).name_surname, "Engellenen Gün": dp.blocked_date.strftime("%d.%m.%Y")} for dp in kap if db.query(User).get(dp.teacher_id)]
                st.dataframe(pd.DataFrame(kap_data), hide_index=True, use_container_width=True)
                del_id = st.number_input("Silmek istediğiniz engel # (ID)", min_value=0, step=1)
                if st.button("🗑️ Engeli Kaldır") and del_id: db.query(DatePreference).filter(DatePreference.id == del_id).delete(); db.commit(); st.rerun()
        
        with c_sab:
            st.markdown('<div class="section-title">Öğretmen Sabitleme (Gün)</div>', unsafe_allow_html=True)
            st.info("Öğretmene sabit bir gün seçerseniz, sistem o gün nöbet yazar ancak lokasyonunu döngüsel değiştirir.")
            with st.form("sabit_form"):
                s_ogr = st.selectbox("Öğretmen", [(o.id, o.name_surname) for o in ogretmenler], format_func=lambda x: x[1])
                s_gun = st.selectbox("Sabitlenecek Gün", [("Seçilmedi", -1)] + [(g, i) for i, g in enumerate(DAYS_TR[:5])], format_func=lambda x: x[0])
                if st.form_submit_button("📌 Kuralı Sabitle", type="primary"):
                    db.query(FixedRule).filter(FixedRule.teacher_id == s_ogr[0]).delete()
                    if s_gun[1] != -1: db.add(FixedRule(school_id=okul.id, teacher_id=s_ogr[0], day_of_week=s_gun[1], location_id=None))
                    db.commit(); st.success("✅ Ayarlandı!"); st.rerun()
            sab_list = db.query(FixedRule).filter(FixedRule.school_id == okul.id).all()
            if sab_list:
                sab_data = [{"Öğretmen": db.query(User).get(s.teacher_id).name_surname, "Sabit Gün": DAYS_TR[s.day_of_week] if s.day_of_week is not None else "Her Gün", "Bölge": "Döngüsel Rotasyon"} for s in sab_list if db.query(User).get(s.teacher_id)]
                st.dataframe(pd.DataFrame(sab_data), hide_index=True, use_container_width=True)

    # 5. NÖBET DEĞİŞİMİ VE NOT
    with tabs[4]:
        st.markdown('<div class="section-title">🔄 Nöbet Değişimi ve Not Ekleme</div>', unsafe_allow_html=True)
        st.info("Bir öğretmen nöbete gelemediğinde yerine bakanı buradan güncelleyebilirsiniz. Bu işlem sayaca otomatik yansır ve çizelgeye not düşülür.")
        
        deg_tarih = st.date_input("Nöbet Tarihi Seçin")
        gunluk_nobetler = db.query(DutySchedule).filter(DutySchedule.school_id==okul.id, DutySchedule.date==deg_tarih).all()
        
        if gunluk_nobetler:
            with st.form("nobet_degisim"):
                secili_nobet_id = st.selectbox("Değiştirilecek Nöbet", [n.id for n in gunluk_nobetler], format_func=lambda x: f"{db.query(Location).get(next(n.location_id for n in gunluk_nobetler if n.id==x)).name} - {db.query(User).get(next(n.teacher_id for n in gunluk_nobetler if n.id==x)).name_surname}")
                yeni_ogretmen = st.selectbox("Yerine Nöbet Tutacak Öğretmen", [(o.id, o.name_surname) for o in ogretmenler], format_func=lambda x: x[1])
                not_metni = st.text_input("Açıklama / Not", placeholder="Örn: Raporlu olduğu için devredildi.")
                
                if st.form_submit_button("🔄 Nöbeti Devret", type="primary"):
                    n = db.query(DutySchedule).get(secili_nobet_id)
                    eski_ogr = db.query(User).get(n.teacher_id)
                    yeni_ogr = db.query(User).get(yeni_ogretmen[0])
                    
                    eski_ogr.monthly_duty_count = max(0, (eski_ogr.monthly_duty_count or 0) - 1)
                    eski_ogr.yearly_duty_count = max(0, (eski_ogr.yearly_duty_count or 0) - 1)
                    yeni_ogr.monthly_duty_count = (yeni_ogr.monthly_duty_count or 0) + 1
                    yeni_ogr.yearly_duty_count = (yeni_ogr.yearly_duty_count or 0) + 1
                    
                    n.teacher_id = yeni_ogr.id
                    n.status = f"Değişim ({not_metni})" if not_metni else "Değişim"
                    db.commit(); st.success("✅ Nöbet başarıyla değiştirildi ve sayaçlar güncellendi!"); st.rerun()
        else:
            st.warning("Seçilen tarihte planlanmış bir nöbet bulunmuyor.")

    # 6. YÖNERGE 
    with tabs[5]:
        st.markdown('<div class="section-title">⚖️ Nöbet Yönergesi Maddeleri</div>', unsafe_allow_html=True)
        with st.form("kural_ekle_form"):
            k_madde=st.text_area("Yeni Madde"); k_sira=st.number_input("Sıra",min_value=1,value=len(kurallar)+1)
            if st.form_submit_button("➕ Ekle",type="primary") and k_madde.strip():
                db.add(SchoolRule(school_id=okul.id,madde=k_madde.strip(),sira=k_sira)); db.commit(); st.rerun()
        for k in sorted(kurallar,key=lambda x:x.sira or 0):
            with st.expander(f"Madde {k.sira}"):
                nt=st.text_area("Metin",value=k.madde,key=f"ek_{k.id}")
                ns=st.number_input("Sıra",value=k.sira or 0,min_value=0,key=f"sk_{k.id}")
                if st.button("💾 Güncelle",key=f"uk_{k.id}"): k.madde=nt;k.sira=ns;db.commit();st.rerun()
                if st.button("🗑️ Sil",key=f"dk_{k.id}"): db.delete(k);db.commit();st.rerun()

    # 7. KADRO VE İDARECİ YÖNETİMİ
    with tabs[6]:
        st.markdown('<div class="section-title">👥 Okul Kadrosu ve İdare Yönetimi</div>', unsafe_allow_html=True)
        c_man, c_toplu, c_idare = st.tabs(["✍️ Öğretmen Manuel Yönetim", "📂 Öğretmen Excel Toplu", "👔 İdareci Yönetimi"])
        
        with c_man:
            with st.form("ogr_ekle"):
                f1, f2 = st.columns(2)
                oad = f1.text_input("Ad Soyad *")
                otc = f2.text_input("TC/Kullanıcı Adı *")
                obrans = f1.text_input("Branş")
                osifre = f2.text_input("Şifre (Düz Metin)", value="1234")
                if st.form_submit_button("➕ Yeni Öğretmen Ekle", type="primary") and oad and otc:
                    mevcut = db.query(User).filter(User.username == otc.strip()).first()
                    if mevcut:
                        st.error("❌ Bu TC / Kullanıcı Adı zaten sistemde kayıtlı!")
                    else:
                        yeni_ogr = User(school_id=okul.id,role="ogretmen",username=otc.strip(),email=f"{otc.strip()}@meb",password_hash=sifre_olustur(osifre),plain_password=osifre,name_surname=oad.strip(),branch=obrans.strip(),is_approved=True,status="Aktif")
                        db.add(yeni_ogr)
                        try:
                            db.commit()
                            st.success("✅ Öğretmen başarıyla eklendi!")
                        except Exception:
                            db.rollback()
                            st.error("❌ Veritabanı hatası. Bu kayıt eklenemedi.")
                        st.rerun()

            st.write("---")
            if st.button("🗑️ Pasif Olanları Toplu Sil", type="primary"):
                db.query(User).filter(User.school_id==okul.id,User.role=="ogretmen",User.status=="Pasif").delete(); db.commit(); st.rerun()

            st.markdown("### Kayıtlı Öğretmenleri Düzenle")
            for o in ogretmenler:
                durum = getattr(o, 'status', 'Aktif')
                badge = "🟢" if durum == 'Aktif' else "🔴"
                with st.expander(f"{badge} {o.name_surname} — {o.branch or 'Branşsız'}"):
                    with st.form(f"edit_{o.id}"):
                        e1, e2 = st.columns(2)
                        e_ad = e1.text_input("Ad Soyad", value=o.name_surname)
                        e_usr = e2.text_input("Kullanıcı Adı", value=o.username)
                        e_br = e1.text_input("Branş", value=o.branch or "")
                        e_pass = e2.text_input("Şifre", value=o.plain_password or "")
                        if st.form_submit_button("💾 Bilgileri Güncelle"):
                            o.name_surname = e_ad; o.username = e_usr; o.branch = e_br
                            o.plain_password = e_pass; o.password_hash = sifre_olustur(e_pass)
                            db.commit(); st.success("Güncellendi!"); st.rerun()
                    b1, b2 = st.columns(2)
                    if b1.button("Pasif/Aktif Yap", key=f"tog_{o.id}"):
                        o.status = "Pasif" if durum == "Aktif" else "Aktif"; db.commit(); st.rerun()
                    if b2.button("Öğretmeni Tamamen Sil", key=f"del_{o.id}"):
                        db.delete(o); db.commit(); st.rerun()
                        
        with c_toplu:
            df_template = pd.DataFrame(columns=["Ad Soyad", "TC/Kullanıcı Adı", "Branş"])
            buf_template = io.BytesIO()
            with pd.ExcelWriter(buf_template, engine='openpyxl') as w:
                df_template.to_excel(w, index=False, sheet_name='Ogretmenler')
            st.download_button("📥 Excel Şablonu İndir", data=buf_template.getvalue(), file_name="Ogretmen_Ekleme_Sablonu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            uploaded_file = st.file_uploader("📤 Şablonu Yükle", type=["xlsx", "xls"], key="excel_uploader_ogr")
            if uploaded_file and st.button("🚀 Toplu Ekle", type="primary", key="btn_excel_toplu_ekle"):
                df = pd.read_excel(uploaded_file)
                eklenen = 0
                atlanan = 0
                
                for index, row in df.iterrows():
                    ogr_ad = str(row.get("Ad Soyad", "")).strip()
                    ogr_tc = str(row.get("TC/Kullanıcı Adı", "")).strip()
                    
                    if ogr_tc and ogr_tc != "nan" and ogr_ad and ogr_ad != "nan":
                        mevcut = db.query(User).filter(User.username == ogr_tc).first()
                        if not mevcut:
                            brans = str(row.get("Branş", "")).strip() if "Branş" in row and str(row.get("Branş", "")) != "nan" else ""
                            yeni_ogr = User(
                                school_id=okul.id,
                                role="ogretmen",
                                username=ogr_tc,
                                password_hash=sifre_olustur(ogr_tc + "47"),
                                plain_password=ogr_tc + "47",
                                name_surname=ogr_ad,
                                branch=brans,
                                email=f"{ogr_tc}@meb",
                                is_approved=True,
                                status="Aktif",
                                monthly_duty_count=0,
                                yearly_duty_count=0,
                                seniority_years=1
                            )
                            db.add(yeni_ogr)
                            
                            # 🔥 POSTGRESQL ZIRHI: Kaydı anında yap, hata çıkarsa sadece bu satırı iptal et
                            try:
                                db.commit() 
                                eklenen += 1
                            except Exception:
                                db.rollback() 
                                atlanan += 1
                        else:
                            atlanan += 1
                            
                st.success(f"✅ {eklenen} öğretmen başarıyla eklendi! ({atlanan} kayıt mevcut veya hatalı olduğu için atlandı.)")
                st.rerun()

        with c_idare:
            st.markdown('**Okul Müdürü Yönetimi**')
            with st.form("md_mudur_form"):
                yeni_mudur = st.text_input("Okul Müdürü İsim Düzenle", value=okul.manager_name)
                if st.form_submit_button("💾 Müdürü Güncelle", type="primary"):
                    okul.manager_name = yeni_mudur.strip(); db.commit(); st.success("Müdür ismi güncellendi!"); st.rerun()
            st.write("---")
            st.markdown('**Müdür Yardımcıları Yönetimi**')
            with st.form("md_ekle_form"):
                md_ad = st.text_input("Yeni Müdür Yardımcısı Ekle")
                if st.form_submit_button("➕ İdareci Ekle", type="primary") and md_ad.strip():
                    db.add(AssistantPrincipal(school_id=okul.id, name_surname=md_ad.strip())); db.commit(); st.rerun()
            for m in md_yard:
                with st.expander(f"👔 {m.name_surname}"):
                    e_md = st.text_input("Müdür Yrd. İsim Güncelle", value=m.name_surname, key=f"emd_{m.id}")
                    bc1, bc2 = st.columns(2)
                    if bc1.button("💾 Kaydet", key=f"updmd_{m.id}"): m.name_surname = e_md.strip(); db.commit(); st.success("İsim güncellendi!"); st.rerun()
                    if bc2.button("🗑️ Sil", key=f"delmd_{m.id}"): db.delete(m); db.commit(); st.rerun()

            st.write("---")
            st.markdown('**Genel İdare Şifre Havuzu**')
            ogr_veri=[{"ID":o.id,"Ad Soyad":o.name_surname,"Hafta İçi":get_veya_olustur_duty_setting(db,o.id).hafta_ici_tutar,"Hafta Sonu":get_veya_olustur_duty_setting(db,o.id).hafta_sonu_tutar} for o in ogretmenler]
            if ogr_veri:
                ed_df=st.data_editor(pd.DataFrame(ogr_veri),hide_index=True,use_container_width=True,column_config={"ID":st.column_config.NumberColumn("ID",disabled=True),"Ad Soyad":st.column_config.TextColumn("Ad Soyad",disabled=True)})
                if st.button("💾 Havuz Tercihlerini Kaydet",type="primary"):
                    for _,r in ed_df.iterrows(): db.query(TeacherDutySetting).filter(TeacherDutySetting.teacher_id==int(r["ID"])).update({"hafta_ici_tutar":bool(r["Hafta İçi"]),"hafta_sonu_tutar":bool(r["Hafta Sonu"])})
                    db.commit(); st.rerun()

    # 8. BÖLGELER & TATİLLER
    with tabs[7]:
        c_b,c_t = st.columns(2)
        with c_b:
            st.markdown('<div class="section-title">Nöbet Bölgeleri</div>', unsafe_allow_html=True)
            with st.form("bolge_ekle"):
                b_ad=st.text_input("Bölge Adı"); b_tip=st.selectbox("Tür",["Hafta İçi","Hafta Sonu"])
                if st.form_submit_button("➕ Ekle",type="primary") and b_ad.strip():
                    db.add(Location(school_id=okul.id,name=b_ad.strip(),location_type=b_tip)); db.commit(); st.rerun()
            for b in bolgeler_all:
                bc1,bc2=st.columns([5,1]); bc1.write(f"{'🔵' if b.location_type!='Hafta Sonu' else '🟠'} {b.name}  —  {b.location_type}")
                if bc2.button("Sil",key=f"db_{b.id}"): db.delete(b);db.commit();st.rerun()
        with c_t:
            st.markdown('<div class="section-title">Ekstra Tatil Günleri</div>', unsafe_allow_html=True)
            with st.form("tatil_ekle"):
                t_ad=st.text_input("Neden"); t_tar=st.date_input("Tarih")
                if st.form_submit_button("🏖️ Ekle",type="primary") and t_ad.strip():
                    db.add(HolidayManager(school_id=okul.id,name=t_ad.strip(),date=t_tar)); db.commit(); st.rerun()
            for t in tatiller_all:
                tc1,tc2=st.columns([5,1]); tc1.write(f"🏖️ {t.date.strftime('%d.%m.%Y')}  —  {t.name}")
                if tc2.button("Sil",key=f"dt_{t.id}"): db.delete(t);db.commit();st.rerun()

    # 9. OLAY & TUTANAK
    with tabs[8]:
        st.markdown('<div class="section-title">Nöbet Esnası Olay ve Tutanak</div>', unsafe_allow_html=True)
        with st.form("olay_form"):
            oc1,oc2=st.columns(2)
            o_ogr=oc1.selectbox("Nöbetçi Öğretmen",[(o.id,o.name_surname) for o in ogretmenler],format_func=lambda x:x[1])
            o_tar=oc2.date_input("Olay Tarihi")
            o_tip=st.selectbox("Olay Türü",["Disiplin (Kavga vb.)","Kaza / Yaralanma","Kural İhlali","Diğer"])
            o_desc=st.text_area("Tutanak Metni")
            if st.form_submit_button("📝 Kaydet",type="primary"):
                db.add(IncidentLog(school_id=okul.id,teacher_id=o_ogr[0],date=o_tar,incident_type=o_tip,description=o_desc)); db.commit(); st.rerun()
        for olay in db.query(IncidentLog).filter(IncidentLog.school_id==okul.id).order_by(IncidentLog.date.desc()).all():
            t_isim=next((o.name_surname for o in ogretmenler if o.id==olay.teacher_id),"Bilinmiyor")
            with st.expander(f"[{olay.date.strftime('%d.%m.%Y')}] {olay.incident_type} — {t_isim}  |  {'🟢 Çözüldü' if olay.is_resolved else '🔴 Açık'}"):
                st.write(olay.description)
                if not olay.is_resolved and st.button("✅ Çözüldü",key=f"res_{olay.id}"):
                    olay.is_resolved=True;db.commit();st.rerun()

    # 10. İSTATİSTİK
    with tabs[9]:
        st.markdown('<div class="section-title">Nöbet İstatistikleri</div>', unsafe_allow_html=True)
        s1,s2,s3=st.columns(3)
        sec_ist_yil=s1.number_input("Yıl",value=date.today().year,min_value=2020,key="ist_yil")
        sec_ist_ay =s2.selectbox("Dönem",list(range(0,13)),format_func=lambda x:"Tüm Yıl" if x==0 else MONTHS_TR[x-1],key="ist_ay")
        if s3.button("🔄 Aylık Sayaçları Sıfırla"):
            for o in ogretmenler: o.monthly_duty_count = 0
            db.commit(); st.rerun()
        ist_data=[]
        for o in ogretmenler:
            q=db.query(DutySchedule).filter(DutySchedule.school_id==okul.id,DutySchedule.teacher_id==o.id,extract('year',DutySchedule.date)==sec_ist_yil)
            if sec_ist_ay: q=q.filter(extract('month',DutySchedule.date)==sec_ist_ay)
            toplam=q.count()
            hs=q.filter(DutySchedule.duty_type=="Haftasonu").count()
            ist_data.append({"Öğretmen":o.name_surname,"Toplam":toplam,"H.İçi":toplam-hs,"H.Sonu":hs,"Ay Sayaç":o.monthly_duty_count or 0,"Yıl Sayaç":o.yearly_duty_count or 0})
        if ist_data: st.dataframe(pd.DataFrame(ist_data).sort_values("Toplam",ascending=False),hide_index=True,use_container_width=True)
        st.divider()
        with st.form("sayac_duzenle"):
            ed_ogr=st.selectbox("Sayaç Düzenle",[(o.id,o.name_surname) for o in ogretmenler],format_func=lambda x:x[1])
            ec1,ec2=st.columns(2); ed_ay=ec1.number_input("Aylık",value=0); ed_yil=ec2.number_input("Yıllık",value=0)
            if st.form_submit_button("💾 Güncelle",type="primary"):
                ogr_ed=db.query(User).get(ed_ogr[0]); ogr_ed.monthly_duty_count=ed_ay; ogr_ed.yearly_duty_count=ed_yil; db.commit(); st.rerun()

    # 11. ARŞİV
    with tabs[10]:
        st.markdown('<div class="section-title">Nöbet Arşivi</div>', unsafe_allow_html=True)
        arc_col1, arc_col2 = st.columns(2)

        with arc_col1:
            st.markdown("**Manuel Yedek Oluştur**")
            with st.form("yedek_olustur_form"):
                y_yil=st.number_input("Yıl",value=date.today().year)
                y_ay =st.selectbox("Ay",list(range(1,13)),index=date.today().month-1,format_func=lambda x:MONTHS_TR[x-1])
                y_etiket=st.text_input("Etiket",value="Manuel Yedek")
                if st.form_submit_button("💾 Yedek Oluştur",type="primary"):
                    db.add(BackupRecord(school_id=okul.id,label=f"{y_etiket} – {MONTHS_TR[y_ay-1]} {y_yil}",created_at=str(datetime.now()),payload_b64=base64.b64encode(yedek_olustur(db,okul.id,y_yil,y_ay).encode()).decode()))
                    db.commit(); st.rerun()

        with arc_col2:
            st.markdown("**JSON Geri Yükle**")
            yukl=st.file_uploader("JSON Yükle",type=["json"])
            if yukl:
                try:
                    payload=json.loads(yukl.read())
                    if st.button("🔄 Uygula",type="primary"):
                        for n in payload.get("nobetler",[]):
                            if not db.query(DutySchedule).filter(DutySchedule.school_id==okul.id,DutySchedule.date==date.fromisoformat(n["date"]),DutySchedule.teacher_id==n["teacher_id"],DutySchedule.location_id==n["location_id"]).first():
                                db.add(DutySchedule(school_id=okul.id,date=date.fromisoformat(n["date"]),duty_type=n["duty_type"],teacher_id=n["teacher_id"],location_id=n["location_id"],status=n.get("status","Planlandi")))
                        db.commit(); st.success("Uygulandı!"); st.rerun()
                except Exception as e: st.error(f"Hata: {e}")

        st.divider()
        st.markdown("**📚 Arşivlenmiş Programlar**")
        kayitli=db.query(BackupRecord).filter(BackupRecord.school_id==okul.id).order_by(BackupRecord.id.desc()).all()

        if not kayitli:
            st.write("Henüz arşiv kaydı yok. Otomatik dağıtım yaptığınızda burada görünecek.")
        else:
            yillar = sorted(set(br.created_at[:4] for br in kayitli if br.created_at), reverse=True)
            sec_yil_arsiv = st.selectbox("Yıla Göre Filtrele", ["Tümü"]+yillar, key="arsiv_yil")

            for br in kayitli:
                if sec_yil_arsiv!="Tümü" and not br.created_at.startswith(sec_yil_arsiv): continue
                tarih_str = br.created_at[:16] if br.created_at else ""
                st.markdown(f'<div class="arsiv-card"><div class="arsiv-badge">📦<br><span style="font-size:.75rem">{tarih_str[:10]}</span></div><div style="flex:1"><div style="font-weight:700;color:#0f1f3d">{br.label}</div><div style="font-size:.78rem;color:#64748b">{tarih_str}</div></div></div>', unsafe_allow_html=True)
                exp_col1, exp_col2, exp_col3 = st.columns([2,2,1])
                if br.payload_b64:
                    json_bytes = base64.b64decode(br.payload_b64)
                    exp_col1.download_button("📥 JSON İndir", data=json_bytes, file_name=f"arsiv_{br.id}.json", mime="application/json", key=f"json_dl_{br.id}")
                    try:
                        pay = json.loads(json_bytes.decode())
                        nobetler_data = pay.get("nobetler",[])
                        ogr_map  = {o["id"]:o["name"] for o in pay.get("ogretmenler",[])}
                        bolge_map= {b["id"]:b["name"] for b in pay.get("bolgeler",[])}
                        if nobetler_data:
                            df_arsiv=pd.DataFrame([{"Tarih":n["date"],"Tür":n["type"],"Öğretmen":ogr_map.get(n["teacher_id"],"?"),"Bölge":bolge_map.get(n["location_id"],"?"),"Durum":n.get("status","")} for n in nobetler_data])
                            buf_arsiv=io.BytesIO()
                            with pd.ExcelWriter(buf_arsiv,engine='openpyxl') as w: df_arsiv.to_excel(w,index=False,sheet_name='Arşiv')
                            exp_col2.download_button("📊 Excel İndir", data=buf_arsiv.getvalue(), file_name=f"arsiv_{br.id}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"exc_dl_{br.id}")
                    except: pass
                if exp_col3.button("🗑️ Sil",key=f"del_br_{br.id}"): db.delete(br);db.commit();st.rerun()

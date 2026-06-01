import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import io
import json
import base64
from sqlalchemy import extract
from babel.dates import format_date

from app.database import get_db
from app.models import (
    User, School, Student, ClassRule, ClassDutySchedule, 
    ClassLocation, ClassHolidayManager, StudentBannedLocation, BackupRecord
)

# ─────────────────────────────────────────────
# SABİTLER VE YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────
MONTHS_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
DAYS_TR   = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

def fmt_date(d):
    return format_date(d, format="dd MMMM yyyy EEEE", locale='tr_TR')

def turkiye_tatilleri(yil):
    return {
        date(yil, 1,  1):  "Yılbaşı",
        date(yil, 4, 23):  "23 Nisan",
        date(yil, 5,  1):  "1 Mayıs",
        date(yil, 5, 19):  "19 Mayıs",
        date(yil, 7, 15):  "15 Temmuz",
        date(yil, 8, 30):  "30 Ağustos",
        date(yil, 10, 29): "29 Ekim",
    }

# ─────────────────────────────────────────────
# ANA RENDER FONKSİYONU (ÖĞRETMEN / SINIF PANELİ)
# ─────────────────────────────────────────────
def render_teacher():
    db = get_db()
    ogretmen = db.query(User).filter(User.id == st.session_state['kullanici_id']).first()
    okul = db.query(School).filter(School.id == ogretmen.school_id).first()

    if st.session_state.get('super_admin_return'):
        if st.button("🔙 Süper Admin Paneline Geri Dön", type="primary", use_container_width=True):
            st.session_state['kullanici_id'] = st.session_state['gercek_admin_id']
            st.session_state['kullanici_rolu'] = 'super_admin'
            st.session_state['super_admin_return'] = False
            st.rerun()

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #065f46 0%, #10b981 100%); 
                border-radius: 16px; padding: 24px 32px; margin-bottom: 24px; 
                box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.3); color: white;">
      <div>
        <h2 style="color: white; margin: 0; font-weight: 700;">👩‍🏫 Sınıf Nöbeti Yönetim Merkezi</h2>
        <small style="color: #d1fae5;">{okul.name} | Sınıf Öğretmeni: {ogretmen.name_surname}</small>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.get('super_admin_return'):
        c1, c2 = st.columns([9, 1])
        if c2.button("🚪 Çıkış", use_container_width=True):
            st.session_state.clear(); st.rerun()

    # Varsayılan Sınıf Kuralları Oluşturucu
    kurallar = db.query(ClassRule).filter(ClassRule.teacher_id == ogretmen.id).all()
    if not kurallar:
        varsayilan = [
            "Sınıf nöbetçisi, teneffüslerde sınıfın havalandırılmasından sorumludur.",
            "Tahtanın temizliği ve tebeşir kontrolü nöbetçi öğrenciye aittir.",
            "Nöbetçi öğrenci, sınıfta meydana gelen hasarları öğretmene bildirmekle yükümlüdür."
        ]
        for i, m in enumerate(varsayilan, 1):
            db.add(ClassRule(teacher_id=ogretmen.id, madde=m, sira=i))
        db.commit()

    tab_ogr, tab_bolge, tab_dagitim, tab_takip, tab_ayarlar, tab_arsiv = st.tabs([
        "👥 Öğrenci & Puan Yönetimi", "📍 Nöbet Yerleri", "📅 Çizelge & Dağıtım", "✅ Günlük Takip", "⚙️ Kurallar & Tatil", "🗄️ Arşiv"
    ])

    # ==========================================
    # 1. ÖĞRENCİ YÖNETİMİ & PUANLAMA
    # ==========================================
    with tab_ogr:
        c_man, c_toplu = st.tabs(["✍️ Manuel Yönetim & Puanlar", "📂 Excel ile Toplu Ekle"])
        
        with c_man:
            with st.form("ogrenci_ekle"):
                col1, col2, col3 = st.columns(3)
                o_ad = col1.text_input("Ad Soyad")
                o_no = col2.text_input("Okul Numarası")
                o_sinif = col3.text_input("Sınıfı (Örn: 9/A)")
                if st.form_submit_button("➕ Ekle", type="primary") and o_ad and o_no:
                    mevcut = db.query(Student).filter(Student.student_no == o_no.strip(), Student.teacher_id == ogretmen.id).first()
                    if mevcut:
                        st.error("❌ Bu okul numarasına sahip bir öğrenci sistemde zaten kayıtlı!")
                    else:
                        db.add(Student(teacher_id=ogretmen.id, name_surname=o_ad.strip(), student_no=o_no.strip(), class_name=o_sinif.strip()))
                        db.commit(); st.success("✅ Öğrenci eklendi!"); st.rerun()
            
            st.markdown('<h3 style="margin-top:20px; font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">Detaylı Öğrenci Listesi (Muafiyet & Puan Tablosu)</h3>', unsafe_allow_html=True)
            st.info("Muafiyet (Sağlık/Engelli) seçilen öğrencilere sistem nöbet yazmaz. Puanlama sistemi ile öğrencilerinizi takip edebilirsiniz.")
            ogrenciler = db.query(Student).filter(Student.teacher_id == ogretmen.id).all()
            
            if ogrenciler:
                ogr_data = [{
                    "ID": o.id, "No": o.student_no, "Ad Soyad": o.name_surname, 
                    "Aktif Mi": o.is_active, "Muaf (Nöbet Tutmaz)": o.is_exempt,
                    "Puan (Başarı)": o.score, "Nöbet Sayısı": o.duty_count, "Eksik (Ceza)": o.missed_duty
                } for o in ogrenciler]
                
                ed_df = st.data_editor(pd.DataFrame(ogr_data), hide_index=True, use_container_width=True, 
                                       column_config={"ID": st.column_config.NumberColumn("ID", disabled=True)})
                
                if st.button("💾 Değişiklikleri Kaydet", type="primary"):
                    for _, r in ed_df.iterrows():
                        db.query(Student).filter(Student.id == int(r["ID"])).update({
                            "student_no": str(r["No"]), "name_surname": str(r["Ad Soyad"]), 
                            "is_active": bool(r["Aktif Mi"]), "is_exempt": bool(r["Muaf (Nöbet Tutmaz)"]),
                            "score": int(r["Puan (Başarı)"]), "duty_count": int(r["Nöbet Sayısı"]), "missed_duty": int(r["Eksik (Ceza)"])
                        })
                    db.commit(); st.success("Güncellendi!"); st.rerun()

                sc1, sc2 = st.columns(2)
                sil_id = sc1.number_input("Silinecek Öğrenci ID", min_value=0, step=1)
                if sc1.button("🗑️ Tek Öğrenci Sil") and sil_id:
                    db.query(Student).filter(Student.id == sil_id, Student.teacher_id == ogretmen.id).delete(); db.commit(); st.rerun()
                if sc2.button("⚠️ Tüm Sınıfı Toplu Sil (Mezuniyet vs.)", type="primary"):
                    db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id).delete()
                    db.query(Student).filter(Student.teacher_id == ogretmen.id).delete()
                    db.commit(); st.success("Sınıf sıfırlandı!"); st.rerun()

        with c_toplu:
            df_template = pd.DataFrame(columns=["Ad Soyad", "Okul Numarası", "Sınıfı"])
            buf_template = io.BytesIO()
            with pd.ExcelWriter(buf_template, engine='openpyxl') as w:
                df_template.to_excel(w, index=False, sheet_name='Ogrenciler')
            st.download_button("📥 Excel Şablonu İndir", data=buf_template.getvalue(), file_name="Ogrenci_Ekleme_Sablonu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            uploaded_file = st.file_uploader("📤 Şablonu Yükle", type=["xlsx", "xls"])
            if uploaded_file and st.button("🚀 Toplu Ekle", type="primary"):
                df = pd.read_excel(uploaded_file)
                eklenen, atlanan = 0, 0
                for index, row in df.iterrows():
                    ad = str(row.get("Ad Soyad", "")).strip()
                    no = str(row.get("Okul Numarası", "")).strip()
                    sinif = str(row.get("Sınıfı", "")).strip()
                    
                    if ad and ad != "nan" and no and no != "nan":
                        mevcut = db.query(Student).filter(Student.student_no == no, Student.teacher_id == ogretmen.id).first()
                        if not mevcut:
                            db.add(Student(teacher_id=ogretmen.id, name_surname=ad, student_no=no, class_name=sinif))
                            eklenen += 1
                        else:
                            atlanan += 1
                db.commit(); st.success(f"✅ {eklenen} öğrenci eklendi, {atlanan} mükerrer kayıt atlandı."); st.rerun()

    # ==========================================
    # 2. NÖBET YERLERİ VE YASAKLI ALANLAR
    # ==========================================
    with tab_bolge:
        st.markdown('<h3 style="margin-top:10px; font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">Nöbet Yerleri ve Kapasite</h3>', unsafe_allow_html=True)
        with st.form("bolge_ekle_form"):
            bc1, bc2 = st.columns([3, 1])
            b_ad = bc1.text_input("Nöbet Yeri / Görev Adı")
            b_sayi = bc2.number_input("Aynı Anda Kaç Nöbetçi?", min_value=1, value=1, step=1)
            if st.form_submit_button("➕ Ekle", type="primary") and b_ad.strip():
                db.add(ClassLocation(teacher_id=ogretmen.id, name=b_ad.strip(), student_count=b_sayi))
                db.commit(); st.rerun()
                
        locs = db.query(ClassLocation).filter(ClassLocation.teacher_id == ogretmen.id).all()
        for b in locs:
            col1, col2 = st.columns([5, 1])
            col1.write(f"📍 **{b.name}** (Aynı anda {b.student_count} öğrenci)")
            if col2.button("Sil", key=f"del_bloc_{b.id}"):
                db.delete(b); db.commit(); st.rerun()
                
        st.divider()
        st.markdown('<h3 style="font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">Yasaklı Nöbet Yerleri (Çakışma Kontrolü)</h3>', unsafe_allow_html=True)
        st.info("Sağlık problemi olan öğrencilerin atanmaması gereken yerleri buradan belirleyin.")
        with st.form("yasakli_ekle"):
            yc1, yc2 = st.columns(2)
            y_ogr = yc1.selectbox("Öğrenci", [(o.id, o.name_surname) for o in ogrenciler if o.is_active], format_func=lambda x: x[1])
            y_loc = yc2.selectbox("Yasaklı Görev Yeri", [(l.id, l.name) for l in locs], format_func=lambda x: x[1])
            if st.form_submit_button("🚫 Yasak Ekle"):
                if y_ogr and y_loc:
                    db.add(StudentBannedLocation(student_id=y_ogr[0], location_id=y_loc[0]))
                    db.commit(); st.success("Eklendi"); st.rerun()

    # ==========================================
    # 3. DAĞITIM MOTORU (ADALET SAYAÇ GERİ ALMA EKLENDİ)
    # ==========================================
    with tab_dagitim:
        st.markdown('<h3 style="margin-top:10px; font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">Otomatik ve Adil Nöbet Dağıtımı</h3>', unsafe_allow_html=True)
        nc1, nc2, nc3 = st.columns([1, 1, 2])
        n_yil = nc1.number_input("Yıl", value=date.today().year, min_value=2020)
        n_ay = nc2.selectbox("Ay", list(range(1, 13)), index=date.today().month-1, format_func=lambda x: MONTHS_TR[x-1])
        n_algo = nc3.selectbox("🧠 Algoritma Seçimi", ["Adil (Az Tutan & Ceza Puanlı Öncelikli)", "Okul Numarasına Göre Sıralı", "Puanı En Yüksek (Başarılı) Öğrenci Öncelikli"])

        cd1, cd2 = st.columns([3, 1])
        if cd1.button("✨ Çizelgeyi Oluştur", type="primary", use_container_width=True):
            if not ogrenciler or not locs:
                st.error("Lütfen aktif öğrenci ve nöbet yeri ekleyin.")
            else:
                bas, bit = date(n_yil, n_ay, 1), date(n_yil, n_ay, calendar.monthrange(n_yil, n_ay)[1])
                
                # --- ADALET: Eski nöbetleri silmeden önce öğrencilerin sayacını geri al ---
                eski_nobetler = db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id, ClassDutySchedule.date >= bas, ClassDutySchedule.date <= bit).all()
                for en in eski_nobetler:
                    ogr_guncelle = db.query(Student).filter(Student.id == en.student_id).first()
                    if ogr_guncelle and ogr_guncelle.duty_count > 0:
                        ogr_guncelle.duty_count -= 1
                
                db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id, ClassDutySchedule.date >= bas, ClassDutySchedule.date <= bit).delete()
                db.commit()
                # -------------------------------------------------------------------------

                gun_listesi = [date(n_yil, n_ay, g) for g in range(1, bit.day + 1) if date(n_yil, n_ay, g).weekday() < 5]
                oto_tatil = turkiye_tatilleri(n_yil)
                man_tatil = [t.date for t in db.query(ClassHolidayManager).filter(ClassHolidayManager.teacher_id == ogretmen.id).all()]
                yasaklilar = db.query(StudentBannedLocation).all()
                
                uygun_ogrenciler = [o for o in ogrenciler if o.is_active and not o.is_exempt]
                
                for gun in gun_listesi:
                    if gun in oto_tatil or gun in man_tatil: continue
                    gunluk_atananlar = set()
                    
                    for loc in locs:
                        for _ in range(loc.student_count):
                            aday_havuzu = [
                                o for o in uygun_ogrenciler 
                                if o.id not in gunluk_atananlar 
                                and not any(y.student_id == o.id and y.location_id == loc.id for y in yasaklilar)
                            ]
                            
                            if not aday_havuzu: continue
                            
                            if n_algo == "Okul Numarasına Göre Sıralı":
                                aday_havuzu.sort(key=lambda x: (x.duty_count or 0, str(x.student_no)))
                            elif n_algo == "Puanı En Yüksek (Başarılı) Öğrenci Öncelikli":
                                aday_havuzu.sort(key=lambda x: (-(x.score or 0), x.duty_count or 0))
                            else: 
                                aday_havuzu.sort(key=lambda x: ((x.duty_count or 0) - (x.missed_duty or 0)*10))
                                
                            secilen = aday_havuzu[0]
                            db.add(ClassDutySchedule(teacher_id=ogretmen.id, student_id=secilen.id, location_id=loc.id, date=gun))
                            gunluk_atananlar.add(secilen.id)
                            secilen.duty_count = (secilen.duty_count or 0) + 1
                
                db.commit()

                # --- OTOMATİK ARŞİVLEME ---
                arsiv_label = f"Sınıf_OTO_{ogretmen.id}_{n_yil}_{n_ay:02d}"
                db.query(BackupRecord).filter(BackupRecord.school_id == okul.id, BackupRecord.label == arsiv_label).delete()
                
                sinif_nobetler = db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id, extract('month', ClassDutySchedule.date) == n_ay, extract('year', ClassDutySchedule.date) == n_yil).all()
                payload = {
                    "meta": {"tip": "sinif_nobeti", "yil": n_yil, "ay": n_ay},
                    "nobetler": [{"date": str(n.date), "student_id": n.student_id, "location_id": n.location_id} for n in sinif_nobetler]
                }
                payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
                db.add(BackupRecord(school_id=okul.id, label=arsiv_label, created_at=str(datetime.now()), payload_b64=payload_b64))
                db.commit()

                st.success("Nöbet başarıyla dağıtıldı ve otomatik olarak arşive kaydedildi!"); st.rerun()

        if cd2.button("🗑️ Temizle", use_container_width=True):
            bas = date(n_yil, n_ay, 1)
            bit = date(n_yil, n_ay, calendar.monthrange(n_yil, n_ay)[1])
            
            # --- ADALET: Eski nöbetleri silmeden önce öğrencilerin sayacını geri al ---
            eski_nobetler = db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id, ClassDutySchedule.date >= bas, ClassDutySchedule.date <= bit).all()
            for en in eski_nobetler:
                ogr_guncelle = db.query(Student).filter(Student.id == en.student_id).first()
                if ogr_guncelle and ogr_guncelle.duty_count > 0:
                    ogr_guncelle.duty_count -= 1
                    
            db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id, ClassDutySchedule.date >= bas, ClassDutySchedule.date <= bit).delete()
            db.commit(); st.success("Temizlendi ve öğrencilerin sayaçları geri alındı."); st.rerun()

        program = db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id, extract('month', ClassDutySchedule.date) == n_ay, extract('year', ClassDutySchedule.date) == n_yil).all()
        
        if program:
            excel_rows = []
            oto_tatil = turkiye_tatilleri(n_yil)
            man_tatil_dict = {t.date: t.name for t in db.query(ClassHolidayManager).filter(ClassHolidayManager.teacher_id == ogretmen.id).all()}
            
            for g in range(1, calendar.monthrange(n_yil, n_ay)[1] + 1):
                t = date(n_yil, n_ay, g)
                if t.weekday() >= 5: continue
                row = {"Tarih/Gün": fmt_date(t)}
                if t in oto_tatil or t in man_tatil_dict:
                    row["Durum"] = oto_tatil.get(t) or man_tatil_dict.get(t)
                else:
                    row["Durum"] = ""
                    for loc in locs:
                        kisi_isimleri = []
                        for p in program:
                            if p.date == t and p.location_id == loc.id:
                                o = next((ogr for ogr in ogrenciler if ogr.id == p.student_id), None)
                                if o: kisi_isimleri.append(f"{o.student_no}-{o.name_surname}")
                        row[loc.name] = " / ".join(kisi_isimleri) if kisi_isimleri else "-"
                excel_rows.append(row)
            
            # --- MÜKEMMEL PDF TASARIMI (0.1 Milimetrik Ayar & Sığan Tarih) ---
            kural_listesi = [k.madde for k in sorted(db.query(ClassRule).filter(ClassRule.teacher_id == ogretmen.id).all(), key=lambda x: x.sira or 0)]
            kural_html = "".join(f"<li>{k}</li>" for k in kural_listesi)
            th_cols = "".join(f"<th style='width:{100/len(locs)}%;'>{loc.name.upper()}</th>" for loc in locs)
            
            tbody = ""
            for row in excel_rows:
                gun_tarihi = None
                for g2 in range(1, calendar.monthrange(n_yil, n_ay)[1] + 1):
                    d2 = date(n_yil, n_ay, g2)
                    if d2.weekday() >= 5: continue
                    if fmt_date(d2) == row["Tarih/Gün"]:
                        gun_tarihi = d2
                        break

                is_friday = (gun_tarihi is not None and gun_tarihi.weekday() == 4)
                week_sep = "border-bottom: 3px solid #0f172a !important;" if is_friday else ""

                if row["Durum"]:
                    colspan = len(locs) + 1
                    tbody += f'<tr class="holiday" style="{week_sep}"><td class="date-col" style="{week_sep}">{row["Tarih/Gün"]}</td><td colspan="{colspan}" style="{week_sep}">{row["Durum"]}</td></tr>'
                else:
                    tds = "".join(f'<td style="{week_sep}">{row.get(loc.name, "-")}</td>' for loc in locs)
                    tbody += f'<tr style="{week_sep}"><td class="date-col" style="{week_sep}">{row["Tarih/Gün"]}</td>{tds}</tr>'
            
            sinif_adi = ogrenciler[0].class_name if ogrenciler else "Sınıf"
            
            html_pdf = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{ --fs: 9.0pt; --pad: 5px; }}
body {{ font-family: 'Plus Jakarta Sans', Arial, sans-serif; background: #fff; color: #111; }}
@media print {{ @page {{ size: A4 portrait; margin: 8mm 12mm; }} .no-print {{ display: none !important; }} body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
.no-print {{ position: sticky; top: 0; z-index: 999; background: #065f46; padding: 12px; display: flex; gap: 10px; align-items: center; border-radius: 8px 8px 0 0; margin-bottom:10px; }}
.btn-size {{ background: rgba(255,255,255,.2); color: #fff; border: none; padding: 6px 14px; border-radius: 6px; font-weight: 700; cursor: pointer; }}
#size-indicator {{ color: #fff; font-size: 13px; font-weight: 600; min-width: 90px; text-align: center; }}
.btn-print {{ background: #fff; color: #065f46; border: none; padding: 8px 20px; border-radius: 6px; font-weight: 700; cursor: pointer; }}
.wrap {{ width: 100%; margin: 0 auto; }}
.school-title {{ text-align: center; font-weight: 800; font-size: calc(var(--fs) + 3pt); line-height: 1.3; margin-bottom: 5px; }}
table {{ width: 100%; border-collapse: collapse; font-size: var(--fs); table-layout: fixed; margin: 0 auto; }}
th, td {{ border: 1px solid #94a3b8; padding: var(--pad) 4px; text-align: center; color: #0f172a; word-wrap: break-word; }}
th {{ background: #f8fafc; color: #1e293b; font-weight: 800; }}
.date-col, th:first-child {{ width: 22%; min-width: 140px; text-align: left; padding-left: 8px; white-space: nowrap !important; font-weight: 700; }}
.holiday td {{ background: #fef2f2 !important; color: #b91c1c; font-weight: 700; }}
tr[style*="border-bottom: 3px solid #0f172a"] td {{ border-bottom: 3px solid #0f172a !important; }}
.rules-box {{ margin-top: 0px !important; border: 1px solid #94a3b8; border-top: none; padding: 4px 10px; font-size: calc(var(--fs) - 1pt); background: #f8fafc; margin-bottom: 0px !important; }}
.rules-box strong {{ display: block; font-weight: 800; margin-bottom: 2px; }}
.rules-box ol {{ padding-left: 15px; margin: 0; }}
.rules-box li {{ line-height: 1.1; margin-bottom: 1px; }}
.sigs {{ display: flex; justify-content: flex-end; margin-top: 0px !important; padding-top: 0px !important; font-size: calc(var(--fs) - 0.5pt); text-align: center; }}
.sig-box .sig-line {{ border-top: 1px solid #334155; margin-top: 25px; padding-top: 2px; font-weight: 700; width: 220px; }}
</style></head><body>
<div class="no-print"><button class="btn-size" onclick="changeSize(-1)">➖</button><span id="size-indicator">Boyut: 9.0</span><button class="btn-size" onclick="changeSize(1)">➕</button><button class="btn-print" onclick="window.print()">🖨️ PDF Olarak Yazdır</button></div>
<div class="wrap"><div class="school-title">T.C.<br>{okul.name.upper()} MÜDÜRLÜĞÜ<br>{MONTHS_TR[n_ay-1].upper()} {n_yil} - {sinif_adi} SINIFI NÖBET ÇİZELGESİ</div>
<table><thead><tr><th>TARİH / GÜN</th>{th_cols}</tr></thead><tbody>{tbody}</tbody></table>
<div class="rules-box"><strong>📋 SINIF NÖBET KURALLARI</strong><ol>{kural_html}</ol></div>
<div class="sigs"><div class="sig-box"><div class="sig-line">ONAYLAYAN<br>{date.today().strftime('%d.%m.%Y')}<br>{ogretmen.name_surname}<br>Sınıf Öğretmeni</div></div></div>
</div>
<script>
var currentVal = 9.0; 
function changeSize(delta) {{ 
    currentVal = Math.min(14.0, Math.max(5.0, parseFloat((currentVal + delta * 0.1).toFixed(1)))); 
    document.getElementById('size-indicator').textContent = 'Boyut: ' + currentVal.toFixed(1); 
    document.documentElement.style.setProperty('--fs', currentVal + 'pt'); 
    var pad = Math.max(1, Math.floor(currentVal / 2)); 
    document.documentElement.style.setProperty('--pad', pad + 'px'); 
}}
</script></body></html>"""
            
            st.divider(); st.components.v1.html(html_pdf, height=850, scrolling=True)

    # ==========================================
    # 4. GÜNLÜK TAKİP VE PUANLAMA
    # ==========================================
    with tab_takip:
        st.markdown('<h3 style="margin-top:10px; font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">Günlük Nöbet Kontrolü ve Puanlama</h3>', unsafe_allow_html=True)
        st.info("Nöbetçilerin performansına göre puan ekleyebilir veya 'Gelmedi' işaretleyerek ceza hanesine yazılmasını sağlayabilirsiniz.")
        
        t_tarih = st.date_input("İşlem Yapılacak Tarih", value=date.today())
        gunluk_nobetler = db.query(ClassDutySchedule).filter(ClassDutySchedule.teacher_id == ogretmen.id, ClassDutySchedule.date == t_tarih).all()
        
        if not gunluk_nobetler:
            st.warning("Bu tarihte planlanmış bir sınıf nöbeti bulunmuyor.")
        else:
            for nobet in gunluk_nobetler:
                s_obj = db.query(Student).filter(Student.id == nobet.student_id).first()
                l_obj = db.query(ClassLocation).filter(ClassLocation.id == nobet.location_id).first()
                
                with st.expander(f"👤 {s_obj.student_no} - {s_obj.name_surname} (Görev: {l_obj.name})"):
                    durum = st.selectbox("Yoklama / Durum", ["Bekliyor", "Geldi (Görevini Yaptı)", "Gelmedi (Devamsız)", "Geç Kaldı", "Görevini İhmal Etti"], key=f"durum_{nobet.id}")
                    puan_degisim = st.number_input("Puana Etkisi (Örn: Tam yaptıysa +10, Gelmediyse -10)", value=0, key=f"puan_{nobet.id}")
                    
                    if st.button("Kaydet ve İşle", key=f"islem_{nobet.id}"):
                        nobet.attendance_status = durum
                        s_obj.score += puan_degisim
                        if durum == "Gelmedi (Devamsız)":
                            s_obj.missed_duty += 1 
                        db.commit(); st.success(f"{s_obj.name_surname} bilgileri güncellendi! Yeni Puan: {s_obj.score}")

    # ==========================================
    # 5. KURALLAR VE TATİLLER
    # ==========================================
    with tab_ayarlar:
        k_c1, k_c2 = st.columns(2)
        with k_c1:
            st.markdown('<h3 style="margin-top:10px; font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">Sınıf Nöbet Kuralları</h3>', unsafe_allow_html=True)
            with st.form("sinif_kural_ekle"):
                k_madde = st.text_area("Yeni Madde")
                k_sira  = st.number_input("Sıra No", min_value=1, value=len(kurallar) + 1)
                if st.form_submit_button("➕ Ekle", type="primary") and k_madde.strip():
                    db.add(ClassRule(teacher_id=ogretmen.id, madde=k_madde.strip(), sira=k_sira)); db.commit(); st.rerun()
            for k in sorted(db.query(ClassRule).filter(ClassRule.teacher_id == ogretmen.id).all(), key=lambda x: x.sira or 0):
                with st.expander(f"Madde {k.sira}"):
                    new_text = st.text_area("Metni Düzenle", value=k.madde, key=f"edit_ck_{k.id}")
                    new_sira = st.number_input("Sıra No", value=k.sira or 0, min_value=0, key=f"sira_ck_{k.id}")
                    if st.button("💾 Güncelle", key=f"upd_ck_{k.id}"): k.madde = new_text; k.sira = new_sira; db.commit(); st.rerun()
                    if st.button("🗑️ Sil", key=f"del_ck_{k.id}"): db.delete(k); db.commit(); st.rerun()

        with k_c2:
            st.markdown('<h3 style="margin-top:10px; font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">Manuel Sınıf Tatilleri</h3>', unsafe_allow_html=True)
            with st.form("c_tatil_ekle"):
                t_ad = st.text_input("Tatil/Gezi Nedeni")
                t_tar = st.date_input("Tarihi")
                if st.form_submit_button("🏖️ Tatili Ekle", type="primary") and t_ad.strip():
                    db.add(ClassHolidayManager(teacher_id=ogretmen.id, name=t_ad.strip(), date=t_tar)); db.commit(); st.rerun()
            for t in db.query(ClassHolidayManager).filter(ClassHolidayManager.teacher_id == ogretmen.id).all():
                tc1, tc2 = st.columns([5, 1])
                tc1.write(f"🏖️ {t.date.strftime('%d.%m.%Y')} — {t.name}")
                if tc2.button("Sil", key=f"del_ct_{t.id}"): db.delete(t); db.commit(); st.rerun()

    # ==========================================
    # 6. ARŞİV SEKMESİ
    # ==========================================
    with tab_arsiv:
        st.markdown('<h3 style="margin-top:10px; font-size: 1.2rem; color: #065f46; border-bottom: 2px solid #10b981; padding-bottom: 5px;">🗄️ Sınıf Nöbet Arşivi</h3>', unsafe_allow_html=True)
        st.info("Otomatik oluşturduğunuz her aylık çizelge burada saklanır. İstediğiniz zaman eski aylara bakıp Excel çıktısı alabilirsiniz.")
        
        arsiv_kayitlari = db.query(BackupRecord).filter(
            BackupRecord.school_id == okul.id, 
            BackupRecord.label.like(f"Sınıf_OTO_{ogretmen.id}_%")
        ).order_by(BackupRecord.id.desc()).all()
        
        if not arsiv_kayitlari:
            st.warning("Henüz arşivlenmiş bir sınıf nöbet programı bulunmuyor.")
        else:
            for br in arsiv_kayitlari:
                parts = br.label.split("_")
                if len(parts) >= 5:
                    yil, ay = parts[3], parts[4]
                    ay_isim = MONTHS_TR[int(ay)-1]
                    
                    with st.expander(f"📦 {ay_isim} {yil} Nöbet Çizelgesi — Düzenlenme: {br.created_at[:16]}"):
                        try:
                            pay = json.loads(base64.b64decode(br.payload_b64).decode())
                            nobetler_data = pay.get("nobetler", [])
                            
                            if nobetler_data:
                                arsiv_rows = []
                                tarihler = sorted(list(set(n["date"] for n in nobetler_data)))
                                
                                for t_str in tarihler:
                                    t_obj = date.fromisoformat(t_str)
                                    row = {"Tarih/Gün": fmt_date(t_obj)}
                                    for loc in db.query(ClassLocation).filter(ClassLocation.teacher_id == ogretmen.id).all():
                                        kisi_isimleri = []
                                        for n in nobetler_data:
                                            if n["date"] == t_str and n["location_id"] == loc.id:
                                                o = next((ogr for ogr in ogrenciler if ogr.id == n["student_id"]), None)
                                                if o: kisi_isimleri.append(f"{o.student_no}-{o.name_surname}")
                                        row[loc.name] = " / ".join(kisi_isimleri) if kisi_isimleri else "-"
                                    arsiv_rows.append(row)
                                
                                st.dataframe(pd.DataFrame(arsiv_rows), hide_index=True, use_container_width=True)
                                
                                buf_arsiv = io.BytesIO()
                                with pd.ExcelWriter(buf_arsiv, engine='openpyxl') as w:
                                    pd.DataFrame(arsiv_rows).to_excel(w, index=False, sheet_name=f'{ay_isim}_{yil}')
                                st.download_button(f"📊 {ay_isim} {yil} Çizelgesini İndir", data=buf_arsiv.getvalue(), file_name=f"Arsiv_Sinif_{ay_isim}_{yil}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_ex_{br.id}")
                        except Exception as e:
                            st.error("Arşiv verisi okunamadı veya eski bir formata ait.")
                        
                        if st.button("🗑️ Bu Arşivi Sil", key=f"del_arsiv_{br.id}"):
                            db.delete(br); db.commit(); st.rerun()
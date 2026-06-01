"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        SIRAÇ AKSAN NÖBET YÖNETİM SİSTEMİ — v4.0 Mega AI                      ║
║        Ana Kapı ve Yönlendirici (Router)                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

# 1. Veritabanı motorunu ve fonksiyonunu içeri aktarıyoruz
from app.database import engine, get_db

# 2. Tüm veritabanı tablolarımızı içeri aktarıyoruz
from app.models import (
    Base, User, School, Location, DutySchedule, Leave, HolidayManager, Preference,
    SystemSetting, FixedRule, AssistantPrincipal, SchoolRule, DatePreference, 
    BackupRecord, TeacherDutySetting, Student, ClassRule, ClassDutySchedule, 
    ClassLocation, ClassHolidayManager, StudentBannedLocation
)
# 3. Güvenlik ve şifreleme fonksiyonlarını içeri aktarıyoruz
from app.auth import sifre_dogrula, sifre_olustur

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

# Sayfa Ayarları (Yalnızca bir kez çağrılmalıdır)
st.set_page_config(page_title="Nöbet Yönetim Sistemi v4.0", page_icon="🏫", layout="wide", initial_sidebar_state="collapsed")

# Session State Başlatma
if 'kullanici_id' not in st.session_state: st.session_state['kullanici_id'] = None
if 'kullanici_rolu' not in st.session_state: st.session_state['kullanici_rolu'] = None

# =====================================================================
# KULLANIM KILAVUZU METİNLERİ VE POPUP TANIMLAMALARI
# =====================================================================

OKUL_KILAVUZ_METNI = """
### 🚀 Sisteme Kayıt ve Giriş
1. **Üye Olma:** Ana sayfadaki 'Okul Kayıt' sekmesinden okulunuzu saniyeler içinde kaydedin. İdareci şifrenizi belirleyin.
2. **Onay Süreci:** Süper Admin onayından sonra sisteme tam yetkiyle erişebilirsiniz. (Otomatik onay açıksa anında girebilirsiniz).

### ⚙️ Sistem Bölümleri ve Yetenekleri
**1. Kadro ve İdareci Yönetimi**
* **Öğretmen Ekleme:** Excel şablonu ile tüm kadronuzu topluca yükleyin. **Mükerrer Kayıt Koruması** sayesinde aynı TC ile ikinci kez kayıt açılamaz, hatalı yüklemeler engellenir.
* **Düzenleme:** Öğretmenlerin şifrelerini görebilir, güncelleyebilir veya durumlarını 'Pasif' yapabilirsiniz.
* **İdareci Yönetimi:** Resmi PDF çizelgesinde dönüşümlü yer alacak Müdür Yardımcılarını ve Okul Müdürünü buradan eklersiniz.

**2. Nöbet Bölgeleri ve İnteraktif Matris**
* Okulunuzun bölgelerini (Hafta İçi / Hafta Sonu) tanımlayın.
* **7 Günlük Müsaitlik Matrisi:** Öğretmenlerin nöbet isteklerini tek tıkla ayarlayın: 🟢 *Kesin*, 🟡 *Joker*, 🔵 *Ekstra*, 🔴 *Müsait Değil*. Dağıtım motoru bu kuralları ihlal etmez.

**3. İzinler ve Sabitlemeler**
* Raporlu/izinli tarih aralığını girdiğinizde sistem o günleri boydan boya kapatır.
* İstediğiniz öğretmeni özel bir güne sabitleyebilirsiniz.

**4. Yapay Zeka Destekli Adalet Motoru**
* **Adil Dağıtım:** Sistem, öğretmenlerin önceki aylardaki yükünü ve raporlu günlerini hesaplayarak (her 5 izin günü = 1 sanal nöbet) en adil dağıtımı yapar.
* **Akıllı Sayaç Koruması:** Bir ayın çizelgesini silip ('Temizle' butonu) baştan yapmak isterseniz, sistem öğretmenlere o ay için eklediği nöbet sayılarını otomatik olarak geri alır (Rollback). Adalet bozulmaz.

**5. Nöbet Değişimi, Tutanak ve Arşiv**
* Gelmeyen öğretmenin yerine görevlendirilen kişiyi işleyin. Sistem notu PDF'e ekler ve iki öğretmenin sayaçlarını anında dengeler.
* **Milimetrik PDF Çıktısı:** Sığmayan tablolar için **0.1 punto** hassasiyetindeki butonlarla (Örn: 8.5 pt) çizelgeyi kağıda kusursuz oturtun.
* Çizelgeler her ay **Otomatik Arşivlenir**. Eski aylara dönüp Excel çıktılarını alabilirsiniz.
"""

SINIF_KILAVUZ_METNI = """
### 🚀 Sisteme Kayıt ve Giriş
1. Sınıf öğretmenleri 'Öğretmen Kayıt' sekmesinden kendi okulunu seçerek anında profil oluşturur.
2. Sisteme girildiğinde yalnızca o öğretmene ait, izole edilmiş Sınıf Nöbet Yönetim paneli açılır.

### ⚙️ Sistem Bölümleri ve Yetenekleri
**1. Öğrenci Yönetimi ve Puanlama**
* **Toplu Ekleme:** Sınıf listenizi Excel'den saniyeler içinde yükleyin. Sistem, aynı okul numarasına sahip öğrencilerin iki defa eklenmesini (Mükerrer Kayıt) otomatik olarak engeller.
* **Muafiyet & Puan:** Engelli/raporlu öğrencileri 'Nöbetten Muaf' işaretleyin. Diğer öğrencilerin başarı veya ceza puanlarını anlık olarak takip edin.

**2. Nöbet Yerleri ve Yasaklı Çakışmalar**
* Sınıf içi veya koridor nöbet görevlerini belirleyin.
* Sağlık sorunu olan bir öğrencinin kesinlikle nöbet tutmaması gereken yasaklı alanları (Örn: Merdivenler) tanımlayın.

**3. Günlük Takip ve Ceza Sistemi**
* Her gün yoklama alarak nöbetini tutanlara artı puan, gelmeyenlere eksi puan verebilirsiniz.
* **Devamsızlık Cezası:** Nöbete gelmeyen öğrencinin ceza puanı artar. Sistem sonraki ay çizelge yaparken bu öğrenciyi yakalar ve açığını kapatması için ona en başta nöbet yazar.

**4. Akıllı Sınıf Dağıtım Motoru**
* Algoritma (Okul No Sıralı, En Başarılı Öncelikli veya Adaletli) seçip tüm ayı tek tıkla doldurun. 
* Aylar değişse bile sistem öğrencilerin toplam nöbet sayısını unutmaz, yeni ayda en az nöbet tutanlardan başlayarak tam adalet sağlar.
* Listeyi silip ('Temizle') baştan yapmak isterseniz öğrencilerin fazla yazılan sayaçları anında geri alınır.

**5. Resmi Çıktı ve Otomatik Arşiv**
* Sınıf kurallarınızı sisteme işleyin.
* Çizelge oluşturulduğunda sistem kağıttan tasarruf etmek için aynı bölgede nöbet tutan öğrencileri alt alta değil, yan yana eğik çizgi (/) ile birleştirerek PDF'e basar.
* **0.1 Hassasiyet:** Tablo kağıda sığmazsa 0.1 puntoluk adımlarla (Örn: 9.2 pt) PDF'i küçültüp büyütebilirsiniz. Tarih sütunları asla kaymaz.
* Dağıtım yapılan her ay sistemde **Sınıf Nöbet Arşivi** bölümüne otomatik yedeklenir. İstediğiniz an geçmiş aylara ulaşabilirsiniz.
"""

@st.dialog("🏫 Okul İdaresi Nöbet Sistemi Kullanım Kılavuzu", width="large")
def okul_kilavuz_popup():
    st.markdown(OKUL_KILAVUZ_METNI, unsafe_allow_html=True)
    if st.button("Kapat", key="kapat_okul_k"):
        st.rerun()

@st.dialog("👩‍🏫 Sınıf Öğretmeni (Öğrenci) Nöbet Sistemi Kullanım Kılavuzu", width="large")
def sinif_kilavuz_popup():
    st.markdown(SINIF_KILAVUZ_METNI, unsafe_allow_html=True)
    if st.button("Kapat", key="kapat_sinif_k"):
        st.rerun()

# =====================================================================
# ANA GİRİŞ FONKSİYONU
# =====================================================================
def giris_ekrani():
    db = get_db()
    
    # 🔥 POSTGRESQL UYUMLU SÜPER ADMİN OLUŞTURUCU (school_id=None yapıldı)
    super_admin_var = db.query(User).filter(User.role == "super_admin").first()
    if not super_admin_var:
        db.add(User(
            school_id=None,  # 0 yerine None yazarak yabancı anahtar hatasını kökten çözdük
            role="super_admin", 
            username="admin", 
            email="admin", 
            password_hash=sifre_olustur("admin123"), 
            name_surname="Süper Admin", 
            is_approved=True
        ))
        db.commit()

    sys_set = db.query(SystemSetting).first()
    if not sys_set:
        sys_set = SystemSetting(auto_approve_schools=True)
        db.add(sys_set); db.commit(); db.refresh(sys_set)

    st.markdown("""<div style="height:8px;background:linear-gradient(90deg,#f59e0b 0%,#2563eb 100%); border-radius:12px;margin-bottom:32px;box-shadow:0 4px 10px rgba(37,99,235,0.2);"></div>""", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        st.markdown("""
        <div style="text-align:center;padding:24px 0 10px;background:#fff;border-radius:16px;box-shadow:0 10px 25px -5px rgba(0,0,0,0.05);border:1px solid #e2e8f0; margin-bottom: 20px;">
            <span style="font-size:3.5rem">🏫</span>
            <h1 style="font-weight:800;font-size:2rem;margin:12px 0 6px;color:#1e293b;">Nöbet Yönetim Sistemi</h1>
            <p style="color:#64748b;font-size:0.95rem;font-weight:500;">Sıraç Aksan — Profesyonel AI Nöbet Otomasyonu v4.0</p>
        </div>""", unsafe_allow_html=True)

        # KULLANIM KILAVUZU BUTONLARI
        st.markdown('<p style="text-align:center; font-weight:600; color:#1e293b; margin-bottom:10px;">Sistemimizi yakından tanımak için kılavuzlarimizi inceleyin:</p>', unsafe_allow_html=True)
        k1, k2 = st.columns(2)
        if k1.button("📘 İdareci Kılavuzunu Oku", use_container_width=True, key="btn_ana_idareci_kilavuz"):
            okul_kilavuz_popup()
        if k2.button("📙 Sınıf Öğretmeni Kılavuzu", use_container_width=True, key="btn_ana_sinif_kilavuz"):
            sinif_kilavuz_popup()
        
        st.write("<br>", unsafe_allow_html=True)

        # SEKMELER (Giriş, Okul Kayıt, Öğretmen Kayıt)
        t_g, t_k, t_o = st.tabs(["🔑 Giriş Yap", "🏫 Okul Kayıt", "👩‍🏫 Öğretmen Kayıt"])

        with t_g:
            k_adi = st.text_input("Kullanıcı Adı", placeholder="admin, tc_kimlik, mudur123 vs.")
            sif   = st.text_input("Şifre", type="password")
            if st.button("Giriş Yap", type="primary", use_container_width=True):
                k  = db.query(User).filter(User.username == k_adi).first()
                if k and sifre_dogrula(sif, k.password_hash):
                    if not k.is_approved:
                        st.error("❌ Hesabınız / Okulunuz henüz Süper Admin tarafından onaylanmamış!")
                    else:
                        st.session_state['kullanici_id']   = k.id
                        st.session_state['kullanici_rolu'] = k.role
                        st.rerun()
                else: st.error("❌ Kullanıcı adı veya şifre hatalı!")

        with t_k:
            st.markdown('<div style="background:#eff6ff; border-left:4px solid #1d4ed8; padding:10px; border-radius:8px; margin-bottom:15px; font-size:0.85rem; color:#1e40af;">Okul idaresi olarak yeni bir okul profili oluşturun. Öğretmenlerinizi daha sonra içeriden ekleyebilir veya öğretmenlerin kendilerinin kayıt olmasını isteyebilirsiniz.</div>', unsafe_allow_html=True)
            o_ad = st.text_input("Okul Adı")
            m_ad = st.text_input("Müdür Adı Soyadı")
            k_a  = st.text_input("İdareci Kullanıcı Adı (Sisteme Giriş İçin)")
            sf   = st.text_input("Şifre Belirleyin", type="password")
            if st.button("Okulu Kaydet", type="primary", use_container_width=True):
                if o_ad and m_ad and k_a and sf:
                    if db.query(User).filter(User.username == k_a.strip()).first():
                        st.error("❌ Bu kullanıcı adı zaten kayıtlı.")
                    else:
                        oto_onay = sys_set.auto_approve_schools
                        y_o = School(kurum_kodu="000", name=o_ad.strip(), manager_name=m_ad.strip(), email="mail", is_approved=oto_onay)
                        db.add(y_o); db.commit(); db.refresh(y_o)
                        db.add(User(school_id=y_o.id, role="okul_idare", username=k_a.strip(), email="mail", password_hash=sifre_olustur(sf), name_surname=m_ad.strip(), is_approved=oto_onay))
                        db.commit()
                        if oto_onay: st.success("✅ Okul kaydedildi! Giriş yapabilirsiniz.")
                        else: st.info("✅ Kayıt alındı. Ancak Süper Admin onayından sonra sisteme giriş yapabileceksiniz.")
                else: st.error("❌ Tüm alanları doldurun.")
                
        with t_o:
            okullar = db.query(School).filter(School.is_approved == True).all()
            if not okullar:
                st.warning("Sisteme kayıtlı ve onaylı bir okul bulunamadı. Lütfen önce okul idarenizin sisteme okul kaydını yapmasını bekleyin.")
            else:
                st.markdown('<div style="background:#eff6ff; border-left:4px solid #1d4ed8; padding:10px; border-radius:8px; margin-bottom:15px; font-size:0.85rem; color:#1e40af;">Görev yaptığınız okulu seçerek kendi öğretmen profilinizi oluşturun. Anında kendi sınıf nöbet çizelgenizi hazırlamaya başlayabilirsiniz.</div>', unsafe_allow_html=True)
                secili_okul = st.selectbox("Görev Yaptığınız Okul", [(o.id, o.name) for o in okullar], format_func=lambda x: x[1])
                ogr_ad = st.text_input("Ad Soyad")
                ogr_tc = st.text_input("TC Kimlik No / Kullanıcı Adı")
                ogr_brans = st.text_input("Branş (Örn: Sınıf Öğretmeni, Matematik)")
                ogr_sif = st.text_input("Şifrenizi Belirleyin", type="password")
                
                if st.button("Öğretmen Hesabımı Oluştur", type="primary", use_container_width=True):
                    if ogr_ad and ogr_tc and ogr_sif and secili_okul:
                        if db.query(User).filter(User.username == ogr_tc.strip()).first():
                            st.error("❌ Bu Kullanıcı Adı / TC zaten sistemde kayıtlı.")
                        else:
                            yeni_ogr = User(
                                school_id=secili_okul[0],
                                role="ogretmen",
                                username=ogr_tc.strip(),
                                email=f"{ogr_tc.strip()}@meb",
                                password_hash=sifre_olustur(ogr_sif),
                                name_surname=ogr_ad.strip(),
                                branch=ogr_brans.strip(),
                                is_approved=True,
                                status="Aktif",
                                monthly_duty_count=0,
                                yearly_duty_count=0
                            )
                            db.add(yeni_ogr)
                            db.commit()
                            st.success("✅ Kaydınız başarıyla oluşturuldu! 'Giriş Yap' sekmesinden sisteme girebilirsiniz.")
                    else:
                        st.error("❌ Lütfen Okul, Ad Soyad, Kullanıcı Adı ve Şifre alanlarını boş bırakmayın.")

        # -------------------------------------------------------------
        # KULLANIM KILAVUZU BUTONLARI (POPUP TETİKLEYİCİLER)
        # -------------------------------------------------------------
        st.markdown('<p style="text-align:center; font-weight:600; color:#1e293b; margin-bottom:10px;">Sistemimizi yakından tanımak için kılavuzlarımızı inceleyin:</p>', unsafe_allow_html=True)
        k1, k2 = st.columns(2)
        if k1.button("📘 İdareci Kılavuzunu Oku", use_container_width=True):
            okul_kilavuz_popup()
        if k2.button("📙 Sınıf Öğretmeni Kılavuzu", use_container_width=True):
            sinif_kilavuz_popup()
        
        st.write("<br>", unsafe_allow_html=True)

        # SEKMELER (Giriş, Okul Kayıt, Öğretmen Kayıt)
        t_g, t_k, t_o = st.tabs(["🔑 Giriş Yap", "🏫 Okul Kayıt", "👩‍🏫 Öğretmen Kayıt"])

        with t_g:
            k_adi = st.text_input("Kullanıcı Adı", placeholder="admin, tc_kimlik, mudur123 vs.")
            sif   = st.text_input("Şifre", type="password")
            if st.button("Giriş Yap", type="primary", use_container_width=True):
                k  = db.query(User).filter(User.username == k_adi).first()
                if k and sifre_dogrula(sif, k.password_hash):
                    if not k.is_approved:
                        st.error("❌ Hesabınız / Okulunuz henüz Süper Admin tarafından onaylanmamış!")
                    else:
                        st.session_state['kullanici_id']   = k.id
                        st.session_state['kullanici_rolu'] = k.role
                        st.rerun()
                else: st.error("❌ Kullanıcı adı veya şifre hatalı!")

        with t_k:
            st.markdown('<div style="background:#eff6ff; border-left:4px solid #1d4ed8; padding:10px; border-radius:8px; margin-bottom:15px; font-size:0.85rem; color:#1e40af;">Okul idaresi olarak yeni bir okul profili oluşturun. Öğretmenlerinizi daha sonra içeriden ekleyebilir veya öğretmenlerin kendilerinin kayıt olmasını isteyebilirsiniz.</div>', unsafe_allow_html=True)
            o_ad = st.text_input("Okul Adı")
            m_ad = st.text_input("Müdür Adı Soyadı")
            k_a  = st.text_input("İdareci Kullanıcı Adı (Sisteme Giriş İçin)")
            sf   = st.text_input("Şifre Belirleyin", type="password")
            if st.button("Okulu Kaydet", type="primary", use_container_width=True):
                if o_ad and m_ad and k_a and sf:
                    if db.query(User).filter(User.username == k_a.strip()).first():
                        st.error("❌ Bu kullanıcı adı zaten kayıtlı.")
                    else:
                        oto_onay = sys_set.auto_approve_schools
                        y_o = School(kurum_kodu="000", name=o_ad.strip(), manager_name=m_ad.strip(), email="mail", is_approved=oto_onay)
                        db.add(y_o); db.commit(); db.refresh(y_o)
                        db.add(User(school_id=y_o.id, role="okul_idare", username=k_a.strip(), email="mail", password_hash=sifre_olustur(sf), name_surname=m_ad.strip(), is_approved=oto_onay))
                        db.commit()
                        if oto_onay: st.success("✅ Okul kaydedildi! Giriş yapabilirsiniz.")
                        else: st.info("✅ Kayıt alındı. Ancak Süper Admin onayından sonra sisteme giriş yapabileceksiniz.")
                else: st.error("❌ Tüm alanları doldurun.")
                
        with t_o:
            okullar = db.query(School).filter(School.is_approved == True).all()
            if not okullar:
                st.warning("Sisteme kayıtlı ve onaylı bir okul bulunamadı. Lütfen önce okul idarenizin sisteme okul kaydını yapmasını bekleyin.")
            else:
                st.markdown('<div style="background:#eff6ff; border-left:4px solid #1d4ed8; padding:10px; border-radius:8px; margin-bottom:15px; font-size:0.85rem; color:#1e40af;">Görev yaptığınız okulu seçerek kendi öğretmen profilinizi oluşturun. Anında kendi sınıf nöbet çizelgenizi hazırlamaya başlayabilirsiniz.</div>', unsafe_allow_html=True)
                secili_okul = st.selectbox("Görev Yaptığınız Okul", [(o.id, o.name) for o in okullar], format_func=lambda x: x[1])
                ogr_ad = st.text_input("Ad Soyad")
                ogr_tc = st.text_input("TC Kimlik No / Kullanıcı Adı")
                ogr_brans = st.text_input("Branş (Örn: Sınıf Öğretmeni, Matematik)")
                ogr_sif = st.text_input("Şifrenizi Belirleyin", type="password")
                
                if st.button("Öğretmen Hesabımı Oluştur", type="primary", use_container_width=True):
                    if ogr_ad and ogr_tc and ogr_sif and secili_okul:
                        if db.query(User).filter(User.username == ogr_tc.strip()).first():
                            st.error("❌ Bu Kullanıcı Adı / TC zaten sistemde kayıtlı.")
                        else:
                            yeni_ogr = User(
                                school_id=secili_okul[0],
                                role="ogretmen",
                                username=ogr_tc.strip(),
                                email=f"{ogr_tc.strip()}@meb",
                                password_hash=sifre_olustur(ogr_sif),
                                name_surname=ogr_ad.strip(),
                                branch=ogr_brans.strip(),
                                is_approved=True,
                                status="Aktif",
                                monthly_duty_count=0,
                                yearly_duty_count=0
                            )
                            db.add(yeni_ogr)
                            db.commit()
                            st.success("✅ Kaydınız başarıyla oluşturuldu! 'Giriş Yap' sekmesinden sisteme girebilirsiniz.")
                    else:
                        st.error("❌ Lütfen Okul, Ad Soyad, Kullanıcı Adı ve Şifre alanlarını boş bırakmayın.")


# =====================================================================
# YÖNLENDİRME (ROUTER) MANTIĞI
# =====================================================================
if st.session_state['kullanici_id'] is None:
    giris_ekrani()
else:
    # Kullanıcının rolüne göre ilgili view (arayüz) dosyasını çağır
    if st.session_state['kullanici_rolu'] == "super_admin":
        from views.super_admin import render_super_admin
        render_super_admin()
        
    elif st.session_state['kullanici_rolu'] == "okul_idare":
        from views.school_admin import render_school_admin
        render_school_admin()
        
    elif st.session_state['kullanici_rolu'] == "ogretmen":
        from views.teacher import render_teacher
        render_teacher()

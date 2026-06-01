"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        SIRAÇ AKSAN NÖBET YÖNETİM SİSTEMİ — v4.0 Mega AI                      ║
║        Ana Kapı ve Yönlendirici (Router)                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

# Sayfa Ayarları (Streamlit kuralı: İlk komut bu olmalıdır)
st.set_page_config(page_title="Nöbet Yönetim Sistemi v4.0", page_icon="🏫", layout="wide", initial_sidebar_state="collapsed")

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

# =====================================================================
# HIZLANDIRICI KİLİT: Tablolar sadece sistem ilk açıldığında kontrol edilir
# =====================================================================
if "tablolar_kuruldu_mu" not in st.session_state:
    Base.metadata.create_all(bind=engine)
    st.session_state["tablolar_kuruldu_mu"] = True

# Session State Başlatma
if 'kullanici_id' not in st.session_state: st.session_state['kullanici_id'] = None
if 'kullanici_rolu' not in st.session_state: st.session_state['kullanici_rolu'] = None

# =====================================================================
# PROFESYONEL KULLANIM KILAVUZLARI
# =====================================================================

OKUL_KILAVUZ_METNI = """
<div style="background:#f8fafc; padding:20px; border-radius:10px; border-left:5px solid #0284c7;">
    <h3 style="color:#0369a1; margin-top:0;">🏫 Okul İdaresi (Öğretmen) Nöbet Sistemi</h3>
    <p>Bu modül, okul idarecilerinin öğretmen nöbetlerini adil ve yapay zeka destekli bir şekilde dağıtmasını sağlar.</p>
</div>

#### 🚀 Sisteme Kayıt ve Kurulum
* **Üye Olma:** Ana sayfadaki 'Okul Kayıt' sekmesinden okulunuzu sisteme saniyeler içinde tanıtabilirsiniz.
* **Onay Süreci:** Süper Admin onayından sonra sisteme tam yetkiyle erişebilirsiniz.
* **Öğretmen Ekleme:** Excel şablonu ile tüm kadronuzu tek tıkla topluca yükleyebilirsiniz. Mükerrer kayıt koruması sayesinde hatalı yükleme riski yoktur.

#### ⚙️ Yapay Zeka ve Adalet Motoru
* **İnteraktif Matris:** Öğretmenlerin nöbet isteklerini (Kesin, Joker, Ekstra, Müsait Değil) renk kodlarıyla belirleyin.
* **Adil Dağıtım:** Sistem, geçmiş aylardaki yükü ve raporlu (izinli) günleri hesaplayarak nöbetleri kimsenin hakkı yenmeden dağıtır.
* **Akıllı Sayaç Koruması:** Çizelgeyi silip baştan yapmak isterseniz, sistem öğretmenlere o ay için eklediği nöbet puanlarını otomatik olarak geri alır (Rollback).

#### 🗄️ Arşiv ve Çıktı
* **Milimetrik PDF Çıktısı:** Sığmayan tablolar için **0.1 punto** hassasiyetindeki butonlarla çizelgeyi kağıda kusursuz oturtun.
* Çizelgeleriniz her ay otomatik arşivlenir, istediğiniz zaman geçmişe dönük Excel çıktıları alabilirsiniz.
"""

SINIF_KILAVUZ_METNI = """
<div style="background:#f0fdf4; padding:20px; border-radius:10px; border-left:5px solid #16a34a;">
    <h3 style="color:#15803d; margin-top:0;">👩‍🏫 Sınıf Öğretmeni (Öğrenci) Nöbet Sistemi</h3>
    <p>Bu modül, sınıf öğretmenlerinin kendi sınıfları içindeki öğrenci nöbetlerini (tahta, pencere vb.) yönetmesi içindir.</p>
</div>

#### 🚀 Sisteme Giriş ve Öğrenci Yönetimi
* Öğretmenler 'Öğretmen Kayıt' sekmesinden kendi okulunu seçerek anında bağımsız profil oluşturur.
* **Toplu Öğrenci Ekleme:** Sınıf listenizi Excel'den saniyeler içinde yükleyin. Sistem aynı numaraya sahip öğrencileri iki kere kaydetmez.
* **Muafiyetler:** Sağlık problemi olan öğrencileri 'Nöbetten Muaf' işaretleyebilir veya belirli bölgelere (örn: Merdiven) atanmalarını yasaklayabilirsiniz.

#### ⚖️ Günlük Takip ve Ceza Sistemi
* Her gün yoklama alarak nöbetini tutanlara artı puan, gelmeyenlere eksi (ceza) puanı verebilirsiniz.
* Nöbete gelmeyen öğrenciyi sistem hafızaya alır ve bir sonraki ay açığını kapatması için ona en başta nöbet yazar.

#### 🖨️ Akıllı Çıktı ve Arşiv
* Aylar değişse bile sistem öğrencilerin toplam nöbet sayısını unutmaz, yeni ayda en az nöbet tutanlardan başlayarak tam adalet sağlar.
* Çizelgeler oluşturulurken, aynı bölgede görevli öğrenciler kağıttan tasarruf için alt alta değil yan yana ( / ) işaretiyle birleştirilerek şık bir PDF'e dönüştürülür.
* Tüm çizelgeleriniz bulut arşivinde ömür boyu saklanır.
"""

@st.dialog("🏫 Okul İdaresi Kılavuzu", width="large")
def okul_kilavuz_popup():
    st.markdown(OKUL_KILAVUZ_METNI, unsafe_allow_html=True)
    if st.button("Anladım, Kapat", key="btn_close_okul", type="primary"):
        st.rerun()

@st.dialog("👩‍🏫 Sınıf Öğretmeni Kılavuzu", width="large")
def sinif_kilavuz_popup():
    st.markdown(SINIF_KILAVUZ_METNI, unsafe_allow_html=True)
    if st.button("Anladım, Kapat", key="btn_close_sinif", type="primary"):
        st.rerun()

# =====================================================================
# ANA GİRİŞ EKRANI (LOG IN)
# =====================================================================
def giris_ekrani():
    db = get_db()
    
    # SÜPER ADMİN HESABI YOKSA OTOMATİK OLUŞTUR
    super_admin_var = db.query(User).filter(User.role == "super_admin").first()
    if not super_admin_var:
        db.add(User(
            school_id=None, 
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

    st.markdown("""<div style="height:8px;background:linear-gradient(90deg,#0f172a 0%,#3b82f6 100%); border-radius:12px;margin-bottom:20px;"></div>""", unsafe_allow_html=True)
    
    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        st.markdown("""
        <div style="text-align:center;padding:20px;background:#ffffff;border-radius:16px;box-shadow:0 4px 6px rgba(0,0,0,0.05);border:1px solid #e2e8f0; margin-bottom: 25px;">
            <span style="font-size:4rem">🏫</span>
            <h1 style="font-weight:800;font-size:2.2rem;margin:10px 0 5px;color:#0f172a;">Nöbet Yönetim Sistemi</h1>
            <p style="color:#64748b;font-size:1rem;font-weight:500;">Sıraç Aksan — Profesyonel AI Nöbet Otomasyonu v4.0</p>
        </div>""", unsafe_allow_html=True)

        # -------------------------------------------------------------
        # YENİLENMİŞ KULLANIM KILAVUZU BUTONLARI
        # -------------------------------------------------------------
        st.info("Sistemimizin size nasıl zaman kazandıracağını görmek için kullanım kılavuzlarını inceleyebilirsiniz.")
        k1, k2 = st.columns(2)
        if k1.button("📘 İdareci Kılavuzunu Oku", use_container_width=True, key="btn_guide_admin"):
            okul_kilavuz_popup()
        if k2.button("📙 Sınıf Öğretmeni Kılavuzu", use_container_width=True, key="btn_guide_teacher"):
            sinif_kilavuz_popup()
        
        st.write("<br>", unsafe_allow_html=True)

        # SEKMELER (Giriş, Okul Kayıt, Öğretmen Kayıt)
        t_g, t_k, t_o = st.tabs(["🔑 Sisteme Giriş", "🏫 Okul Kaydı Oluştur", "👩‍🏫 Öğretmen Kaydı Oluştur"])

        with t_g:
            k_adi = st.text_input("Kullanıcı Adı", placeholder="admin, tc_kimlik, mudur123 vs.", key="login_user")
            sif   = st.text_input("Şifre", type="password", key="login_pass")
            if st.button("Giriş Yap", type="primary", use_container_width=True, key="btn_login_submit"):
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
            st.markdown('<div style="background:#eff6ff; border-left:4px solid #3b82f6; padding:10px; border-radius:5px; margin-bottom:15px; font-size:0.9rem;">Okul idaresi olarak yeni bir okul profili oluşturun. Öğretmenlerinizi sistemin içinden ekleyebilirsiniz.</div>', unsafe_allow_html=True)
            o_ad = st.text_input("Okul Adı", key="reg_school_name")
            m_ad = st.text_input("Müdür Adı Soyadı", key="reg_manager_name")
            k_a  = st.text_input("İdareci Kullanıcı Adı (Sisteme Giriş İçin)", key="reg_admin_user")
            sf   = st.text_input("Şifre Belirleyin", type="password", key="reg_admin_pass")
            if st.button("Okulu Kaydet", type="primary", use_container_width=True, key="btn_reg_school"):
                if o_ad and m_ad and k_a and sf:
                    if db.query(User).filter(User.username == k_a.strip()).first():
                        st.error("❌ Bu kullanıcı adı zaten kayıtlı.")
                    else:
                        oto_onay = sys_set.auto_approve_schools
                        y_o = School(kurum_kodu="000", name=o_ad.strip(), manager_name=m_ad.strip(), email="mail", is_approved=oto_onay)
                        db.add(y_o); db.commit(); db.refresh(y_o)
                        db.add(User(school_id=y_o.id, role="okul_idare", username=k_a.strip(), email="mail", password_hash=sifre_olustur(sf), name_surname=m_ad.strip(), is_approved=oto_onay))
                        db.commit()
                        if oto_onay: st.success("✅ Okul kaydedildi! Giriş Yap sekmesinden sisteme girebilirsiniz.")
                        else: st.info("✅ Kayıt alındı. Ancak Süper Admin onayından sonra giriş yapabileceksiniz.")
                else: st.error("❌ Tüm alanları doldurun.")
                
        with t_o:
            okullar = db.query(School).filter(School.is_approved == True).all()
            if not okullar:
                st.warning("Sisteme kayıtlı ve onaylı bir okul bulunamadı. Lütfen okul idarenizin kayıt olmasını bekleyin.")
            else:
                st.markdown('<div style="background:#f0fdf4; border-left:4px solid #22c55e; padding:10px; border-radius:5px; margin-bottom:15px; font-size:0.9rem;">Görev yaptığınız okulu seçerek kendi profilinizi oluşturun ve anında sınıfınızın nöbet çizelgesini hazırlayın.</div>', unsafe_allow_html=True)
                secili_okul = st.selectbox("Görev Yaptığınız Okul", [(o.id, o.name) for o in okullar], format_func=lambda x: x[1], key="reg_teacher_school")
                ogr_ad = st.text_input("Ad Soyad", key="reg_teacher_name")
                ogr_tc = st.text_input("TC Kimlik No / Kullanıcı Adı", key="reg_teacher_tc")
                ogr_brans = st.text_input("Branş (Örn: Sınıf Öğretmeni)", key="reg_teacher_branch")
                ogr_sif = st.text_input("Şifrenizi Belirleyin", type="password", key="reg_teacher_pass")
                
                if st.button("Öğretmen Hesabımı Oluştur", type="primary", use_container_width=True, key="btn_reg_teacher"):
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
                            st.success("✅ Kaydınız başarıyla oluşturuldu! 'Sisteme Giriş' sekmesinden girebilirsiniz.")
                    else:
                        st.error("❌ Lütfen Okul, Ad Soyad, Kullanıcı Adı ve Şifre alanlarını boş bırakmayın.")


# =====================================================================
# YÖNLENDİRME (ROUTER) VE KÜRESEL ÇIKIŞ BUTONU MANTIĞI
# =====================================================================
if st.session_state['kullanici_id'] is None:
    giris_ekrani()
else:
    # --- GLOBAL (KÜRESEL) ÇIKIŞ BAR'I ---
    # Kullanıcı hangi panelde olursa olsun en üstte bu çıkış butonu görünecek.
    c_space, c_logout = st.columns([8, 2])
    with c_logout:
        if st.button("🚪 Güvenli Çıkış Yap", use_container_width=True, type="secondary", key="global_logout_button"):
            st.session_state.clear()
            st.rerun()
    
    st.divider() # Buton ile alt paneller arasına şık bir çizgi çeker

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

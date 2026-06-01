import streamlit as st
from app.database import get_db
from app.models import User, School, SystemSetting

def render_super_admin():
    db = get_db()
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #4c1d95 0%, #8b5cf6 100%); 
                border-radius: 16px; padding: 24px 32px; margin-bottom: 24px; 
                box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.3); color: white;">
      <div>
        <h2 style="color: white; margin: 0; font-weight: 700;">👑 Süper Admin Merkezi</h2>
        <small style="color: #e9d5ff;">Tüm okulları ve öğretmenleri buradan yönetebilirsiniz.</small>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([9, 1])
    if c2.button("🚪 Çıkış", use_container_width=True):
        st.session_state.clear(); st.rerun()

    sys_set = db.query(SystemSetting).first()
    if not sys_set:
        sys_set = SystemSetting(auto_approve_schools=True)
        db.add(sys_set); db.commit(); db.refresh(sys_set)

    tab_okullar, tab_ogretmenler, tab_ayarlar = st.tabs(["🏫 Okullar & Erişim", "👩‍🏫 Tüm Öğretmenler", "⚙️ Sistem Ayarları"])

    with tab_okullar:
        st.markdown('### Kayıtlı Okullar', unsafe_allow_html=True)
        okullar = db.query(School).all()
        if not okullar:
            st.info("Sisteme henüz kayıtlı okul bulunmuyor.")
        else:
            for okul in okullar:
                manager = db.query(User).filter(User.school_id == okul.id, User.role == "okul_idare").first()
                durum = "🟢 Onaylı" if okul.is_approved else "🔴 Bekliyor"
                
                with st.container():
                    sc1, sc2, sc3 = st.columns([4, 2, 3])
                    sc1.markdown(f"**{okul.name}**<br><small>Müdür: {okul.manager_name} | Durum: {durum}</small>", unsafe_allow_html=True)
                    
                    if not okul.is_approved:
                        if sc2.button("✅ Onayla", key=f"onayla_{okul.id}"):
                            okul.is_approved = True
                            if manager: manager.is_approved = True
                            db.commit(); st.rerun()
                    
                    if manager and okul.is_approved:
                        if sc3.button(f"🔑 Okula Giriş Yap (Müdahale Et)", type="primary", key=f"gir_{okul.id}"):
                            st.session_state['gercek_admin_id'] = st.session_state['kullanici_id']
                            st.session_state['kullanici_id'] = manager.id
                            st.session_state['kullanici_rolu'] = 'okul_idare'
                            st.session_state['super_admin_return'] = True
                            st.rerun()
                st.divider()

    with tab_ogretmenler:
        st.markdown('### Sistemdeki Tüm Öğretmenler', unsafe_allow_html=True)
        tum_ogretmenler = db.query(User).filter(User.role == "ogretmen").all()
        if not tum_ogretmenler:
            st.info("Sistemde henüz öğretmen kaydı yok.")
        else:
            for ogr in tum_ogretmenler:
                okul = db.query(School).filter(School.id == ogr.school_id).first()
                okul_adi = okul.name if okul else "Bilinmiyor"
                
                with st.container():
                    oc1, oc2 = st.columns([6, 3])
                    oc1.markdown(f"**{ogr.name_surname}** ({ogr.branch})<br><small>🏫 {okul_adi} | Durum: {ogr.status}</small>", unsafe_allow_html=True)
                    
                    if oc2.button(f"🔑 Öğretmen paneli göster", type="primary", key=f"gir_ogr_{ogr.id}"):
                        st.session_state['gercek_admin_id'] = st.session_state['kullanici_id']
                        st.session_state['kullanici_id'] = ogr.id
                        st.session_state['kullanici_rolu'] = 'ogretmen'
                        st.session_state['super_admin_return'] = True
                        st.rerun()
                st.divider()

    with tab_ayarlar:
        st.markdown('### Otomatik Kayıt Onayı', unsafe_allow_html=True)
        st.info("Açıksa, yeni kaydolan okullar anında sisteme giriş yapabilir. Kapalıysa, önce sizin buradan onaylamanız gerekir.")
        
        yeni_ayar = st.toggle("Okul Kayıtları Otomatik Onaylansın", value=sys_set.auto_approve_schools)
        if st.button("Ayarları Kaydet", type="primary"):
            sys_set.auto_approve_schools = yeni_ayar
            db.commit(); st.success("Ayarlar kaydedildi.")
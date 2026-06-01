from sqlalchemy.orm import Session
from app.models import Teacher, DutySchedule

class ReportService:
    @staticmethod
    def generate_monthly_ek_ders_report(db: Session, month_name: str) -> list[dict]:
        """İdarenin ek ders hesaplaması için aylık matris raporu sunar."""
        teachers = db.query(Teacher).all()
        report_data = []

        for teacher in teachers:
            # Öğretmenin o aya ait tüm nöbetleri
            duties = db.query(DutySchedule).filter(
                DutySchedule.teacher_id == teacher.id,
                DutySchedule.month_name == month_name
            ).all()

            # Haftalık dağılım detaylandırması
            weeks_detail = {1: [], 2: [], 3: [], 4: [], 5: []}
            for d in duties:
                # Gün ismini ve yerini ekle (Örn: "Pazartesi - Bahçe")
                day_name = d.date.strftime("%A")
                weeks_detail[d.week_number].append(f"{day_name} ({d.location.name})")

            report_data.append({
                "Öğretmen": teacher.name_surname,
                "Branş": teacher.branch or "-",
                "Toplam Nöbet": len(duties),
                "1. Hafta": ", ".join(weeks_detail[1]) or "-",
                "2. Hafta": ", ".join(weeks_detail[2]) or "-",
                "3. Hafta": ", ".join(weeks_detail[3]) or "-",
                "4. Hafta": ", ".join(weeks_detail[4]) or "-",
                "5. Hafta": ", ".join(weeks_detail[5]) or "-"
            })
        return report_data

    @staticmethod
    def generate_whatsapp_message(teacher_name: str, phone: str, month_name: str, duties: list) -> str:
        """Öğretmene özel nöbet listesini WhatsApp mesaj linkine (api.whatsapp) dönüştürür."""
        base_msg = f"🔔 *Dargeçit Milli Eğitim Nöbet Bilgilendirmesi*\n\nSayın *{teacher_name}*,\n{month_name} ayı nöbet programınız aşağıdadır:\n\n"
        
        if not duties:
            base_msg += "Bu ay planlanmış nöbet göreviniz bulunmamaktadır."
        for d in duties:
            base_msg += f"📅 {d.date.strftime('%d.%m.%Y')} ({d.date.strftime('%A')}) -> *{d.location.name}*\n"
            
        base_msg += "\n\n📋 *Nöbet Kuralları Hatırlatması:*\n1. Nöbet görevi ilk ders başlamadan 15 dk önce başlar.\n2. Nöbet yerindeki olumsuz durumlar ivedilikle idareye bildirilir."
        base_msg += "\n\n_Dargeçit İlçe Milli Eğitim Müdürlüğü_\n_Tasarımcı: Sıraç AKSAN_"
        
        # WhatsApp Web / Mobil yönlendirme URL'si oluşturma
        import urllib.parse
        encoded_msg = urllib.parse.quote(base_msg)
        whatsapp_url = f"https://api.whatsapp.com/send?phone=90{phone}&text={encoded_msg}"
        return whatsapp_url
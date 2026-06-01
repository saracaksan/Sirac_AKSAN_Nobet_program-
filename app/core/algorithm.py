import random
from datetime import Date, timedelta
from sqlalchemy.orm import Session
from app.models import Teacher, Location, DutySchedule, Holiday

class DutyAssignmentEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_active_days(self, start_date: Date, end_date: Date) -> list[Date]:
        """Hafta sonlarını ve otomatik/manuel resmi tatilleri takvimden eler."""
        active_days = []
        current_date = start_date
        
        # Tatil günlerini küme olarak çekelim (Hızlı arama için)
        holidays = set(d.date for d in self.db.query(Holiday).all())

        while current_date <= end_date:
            # 5 = Cumartesi, 6 = Pazar
            if current_date.weekday() < 5 and current_date not in holidays:
                active_days.append(current_date)
            current_date += timedelta(days=1)
        return active_days

    def distribute_duties(self, start_date: Date, end_date: Date, mode: str = "ai_random"):
        """
        Nöbet dağıtım ana fonksiyonu.
        mode: 'sequential' (Sıralı/Döngüsel) veya 'ai_random' (Adil Rastgele)
        """
        days_to_assign = self.get_active_days(start_date, end_date)
        locations = self.db.query(Location).all()
        
        # Tüm öğretmenleri çekelim
        all_teachers = self.db.query(Teacher).all()
        
        # 1. Sabitlenmiş (Pinned) Öğretmenleri Ayrıştır
        permanently_pinned = [t for t in all_teachers if t.is_permanently_pinned and t.pinned_location_id]
        pool_teachers = [t for t in all_teachers if t not in permanently_pinned]

        for current_date in days_to_assign:
            # Hafta numarasını ve ay adını bul (Raporlama için)
            week_num = (current_date.day - 1) // 7 + 1
            month_name = current_date.strftime("%B")
            
            assigned_today_teachers = set()
            available_locations = locations.copy()

            # Adım A: Önce her gün için SABİT öğretmenleri yerleştir
            for teacher in permanently_pinned:
                loc = teacher.pinned_location
                if loc in available_locations:
                    self._create_duty_entry(current_date, week_num, month_name, teacher, loc)
                    assigned_today_teachers.add(teacher.id)
                    available_locations.remove(loc)

            # Adım B: Boşta kalan yerleri mod seçimine göre doldur
            if mode == "ai_random":
                # Yapay Zeka/Adalet Modu: O ana kadar en az nöbet tutmuş ve 
                # en az zorluk puanı toplamış öğretmenlere öncelik verilir.
                pool_teachers.sort(key=lambda t: (t.monthly_duty_count, t.total_difficulty_score))
            elif mode == "sequential":
                # Sıralı/Döngüsel Mod: Basit döngü, havuz sırasına göre alınır
                pool_teachers.sort(key=lambda t: t.id)

            for loc in available_locations:
                # Bugün henüz nöbet almamış adayları filtrele
                candidates = [t for t in pool_teachers if t.id not in assigned_today_teachers]
                
                if not candidates:
                    break # Atanabilecek öğretmen kalmadıysa çık
                
                # Mod 'ai_random' ise en uygun ilk 3 kişiden birini rastgele seç (Esneklik için)
                # Mod 'sequential' ise direkt sıradaki ilk kişiyi al
                chosen_teacher = random.choice(candidates[:3]) if mode == "ai_random" else candidates[0]
                
                # Nöbeti kaydet ve sayaçları güncelle
                self._create_duty_entry(current_date, week_num, month_name, chosen_teacher, loc)
                
                # İstatistikleri güncelle (Yapay zekanın bir sonraki döngüde adil davranması için)
                chosen_teacher.monthly_duty_count += 1
                chosen_teacher.yearly_duty_count += 1
                chosen_teacher.total_difficulty_score += loc.difficulty_score
                
                assigned_today_teachers.add(chosen_teacher.id)
                
        self.db.commit()

    def _create_duty_entry(self, date, week, month, teacher, location):
        duty = DutySchedule(
            date=date,
            week_number=week,
            month_name=month,
            teacher_id=teacher.id,
            location_id=location.id
        )
        self.db.add(duty)
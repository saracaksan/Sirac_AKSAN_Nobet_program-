import pandas as pd
import io
from sqlalchemy.orm import Session
from app.models import Teacher, Student

class ExcelService:
    @staticmethod
    def generate_teacher_template() -> io.BytesIO:
        """İdarenin bilgisayarına indireceği boş Excel şablonunu hazırlar."""
        columns = ["Adı Soyadı", "TC Kimlik No", "Branş", "Telefon No", "Özel Durum (Var/Yok)"]
        sample_data = [
            ["Ahmet Yılmaz", "12345678901", "Matematik", "5051234567", "Nöbet tutabilir"],
            ["Mehmet Demir", "", "Fizik", "5329876543", "Zemin Kat Sabit (Sağlık Nedeniyle)"]
        ]
        df = pd.DataFrame(sample_data, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Öğretmen Listesi")
        output.seek(0)
        return output

    @staticmethod
    def import_teachers_from_excel(db: Session, file_contents: bytes) -> int:
        """Yüklenen Excel dosyasını okur ve veritabanına kaydeder."""
        df = pd.read_excel(io.BytesIO(file_contents))
        added_count = 0
        
        for _, row in df.iterrows():
            name = str(row.get("Adı Soyadı", "")).strip()
            if not name or name == "nan": 
                continue  
                
            tc = str(row.get("TC Kimlik No", "")) if pd.notna(row.get("TC Kimlik No")) else None
            branch = str(row.get("Branş", "")) if pd.notna(row.get("Branş")) else None
            phone = str(row.get("Telefon No", "")) if pd.notna(row.get("Telefon No")) else None
            special = str(row.get("Özel Durum (Var/Yok)", "")) if pd.notna(row.get("Özel Durum (Var/Yok)")) else None

            db_teacher = Teacher(
                name_surname=name,
                tc_no=tc.replace(".0", "") if tc else None, 
                branch=branch,
                phone=phone.replace(".0", "") if phone else None,
                special_condition=special
            )
            db.add(db_teacher)
            added_count += 1
            
        db.commit()
        return added_count

    @staticmethod
    def generate_student_template() -> io.BytesIO:
        """Sınıf öğretmenleri için öğrenci nöbet şablonunu hazırlar."""
        columns = ["Adı Soyadı", "Sınıfı", "Nöbet Görevi"]
        sample_data = [
            ["Ali Yılmaz", "8/A", "Tahta Temizliği ve Düzeni"],
            ["Ayşe Demir", "8/A", "Yoklama Fişinin İdareye İletilmesi"],
            ["Can Kaya", "7/B", "Pencerelerin Havalandırılması"]
        ]
        df = pd.DataFrame(sample_data, columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Öğrenci Listesi")
        output.seek(0)
        return output

    @staticmethod
    def import_students_from_excel(db: Session, file_contents: bytes) -> int:
        """Yüklenen öğrenci Excel dosyasını okur ve veritabanına kaydeder."""
        df = pd.read_excel(io.BytesIO(file_contents))
        added_count = 0
        
        for _, row in df.iterrows():
            name = str(row.get("Adı Soyadı", "")).strip()
            if not name or name == "nan": 
                continue  
                
            class_name = str(row.get("Sınıfı", "")).strip() if pd.notna(row.get("Sınıfı")) else "Belirsiz"
            task = str(row.get("Nöbet Görevi", "")) if pd.notna(row.get("Nöbet Görevi")) else "Genel Sınıf Düzeni"

            db_student = Student(
                name_surname=name,
                class_name=class_name,
                duty_task=task
            )
            db.add(db_student)
            added_count += 1
            
        db.commit()
        return added_count
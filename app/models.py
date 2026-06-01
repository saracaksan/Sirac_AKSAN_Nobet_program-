from sqlalchemy import Column, Integer, String, Date, ForeignKey, Boolean, Text, Float
from app.database import Base

# =====================================================================
# OKUL VE İDARE TABLOLARI
# =====================================================================
class School(Base):
    __tablename__ = "schools"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    kurum_kodu = Column(String, unique=True, index=True)
    name = Column(String)
    manager_name = Column(String)
    email = Column(String)
    is_approved = Column(Boolean, default=False)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    role = Column(String) 
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    plain_password = Column(String) # Öğretmen şifresini idarenin görebilmesi için
    name_surname = Column(String)
    email = Column(String)
    branch = Column(String, nullable=True)
    status = Column(String, default="Aktif")
    is_approved = Column(Boolean, default=False)
    monthly_duty_count = Column(Integer, default=0)
    yearly_duty_count = Column(Integer, default=0)
    total_fatigue_score = Column(Float, default=0.0) 
    weekly_lesson_hours = Column(Integer, default=20) 
    seniority_years = Column(Integer, default=1) 

class Location(Base):
    __tablename__ = "locations"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    name = Column(String)
    location_type = Column(String) 
    difficulty_score = Column(Float, default=5.0)

class DutySchedule(Base):
    __tablename__ = "duty_schedules"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    date = Column(Date)
    duty_type = Column(String)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    status = Column(String, default="Planlandi")

class Leave(Base):
    __tablename__ = "leaves"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    leave_type = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)

class HolidayManager(Base):
    __tablename__ = "holiday_manager"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    name = Column(String)
    date = Column(Date)

class Preference(Base):
    __tablename__ = "preferences"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    day_of_week = Column(Integer)
    status = Column(Integer)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    auto_approve_schools = Column(Boolean, default=True)

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
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date)
    incident_type = Column(String)
    description = Column(Text)
    is_resolved = Column(Boolean, default=False)

class DutySubstitute(Base):
    __tablename__ = "duty_substitutes"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    duty_id = Column(Integer, ForeignKey("duty_schedules.id", ondelete="CASCADE"))
    substitute_teacher_id = Column(Integer, ForeignKey("users.id"))


# =====================================================================
# ÖĞRENCİ VE SINIF NÖBETİ TABLOLARI
# =====================================================================
class Student(Base):
    __tablename__ = "students"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name_surname = Column(String, nullable=False)
    student_no = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)     
    is_exempt = Column(Boolean, default=False)    
    score = Column(Integer, default=100)          
    duty_count = Column(Integer, default=0)       
    missed_duty = Column(Integer, default=0)      

class ClassLocation(Base):
    __tablename__ = "class_locations"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    student_count = Column(Integer, default=1)

class StudentBannedLocation(Base):
    __tablename__ = "student_banned_locations"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("class_locations.id"), nullable=False)

class ClassHolidayManager(Base):
    __tablename__ = "class_holiday_manager"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    date = Column(Date)

class ClassRule(Base):
    __tablename__ = "class_rules"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    madde = Column(String, nullable=False)
    sira = Column(Integer, default=0)

class ClassDutySchedule(Base):
    __tablename__ = "class_duty_schedules"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("class_locations.id"), nullable=True)
    date = Column(Date, nullable=False)
    status = Column(String, default="Planlandi")
    attendance_status = Column(String, default="Bekliyor") 
    is_substitute = Column(Boolean, default=False)
from sqlalchemy import Column, Integer, String, Date, DateTime, UniqueConstraint, func
from .database import Base

class MasterAWW(Base):
    __tablename__ = "master_aww"
    id = Column(Integer, primary_key=True)
    district = Column(String(150), index=True)
    block = Column(String(150), index=True)
    sector = Column(String(150), index=True)
    supervisor = Column(String(150), index=True)
    aww_name = Column(String(200))
    aww_mobile = Column(String(30))
    awc_name = Column(String(200))
    awc_code = Column(String(60), index=True, unique=True)
    source_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class WeeklyMetric(Base):
    __tablename__ = "weekly_metrics"
    __table_args__ = (UniqueConstraint("awc_code", "week_start", "week_end", name="uq_awc_week"),)
    id = Column(Integer, primary_key=True)
    awc_code = Column(String(60), index=True)
    week_start = Column(Date, index=True)
    week_end = Column(Date, index=True)
    ica_photo = Column(Integer, default=0)
    ica_video = Column(Integer, default=0)
    active_days = Column(Integer, default=0)
    tpd_test = Column(Integer, default=0)
    uploaded_by = Column(String(150), default="Administrator")
    uploaded_at = Column(DateTime, server_default=func.now())

class UploadLog(Base):
    __tablename__ = "upload_logs"
    id = Column(Integer, primary_key=True)
    file_name = Column(String(255))
    report_type = Column(String(30))
    week_start = Column(Date, nullable=True)
    week_end = Column(Date, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())

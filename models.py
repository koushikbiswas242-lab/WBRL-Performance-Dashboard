from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    UniqueConstraint,
    func
)

from database import Base


# =========================================================
# MASTER AWW TABLE
# =========================================================

class MasterAWW(Base):

    __tablename__ = "master_aww"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Location Information
    district = Column(
        String(150),
        index=True,
        nullable=True
    )

    block = Column(
        String(150),
        index=True,
        nullable=True
    )

    sector = Column(
        String(150),
        index=True,
        nullable=True
    )

    # Supervisor Information
    supervisor = Column(
        String(150),
        index=True,
        nullable=True
    )

    # AWW Information
    aww_name = Column(
        String(200),
        nullable=True
    )

    aww_mobile = Column(
        String(30),
        nullable=True
    )

    # AWC Information
    awc_name = Column(
        String(200),
        nullable=True
    )

    awc_code = Column(
        String(60),
        unique=True,
        index=True,
        nullable=False
    )

    # Last Update Time
    source_updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )


# =========================================================
# WEEKLY METRICS TABLE
# =========================================================

class WeeklyMetric(Base):

    __tablename__ = "weekly_metrics"

    __table_args__ = (

        UniqueConstraint(
            "awc_code",
            "week_start",
            "week_end",
            name="uq_awc_week"
        ),

    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # AWC Reference
    awc_code = Column(
        String(60),
        index=True,
        nullable=False
    )

    # Weekly Period
    week_start = Column(
        Date,
        index=True,
        nullable=False
    )

    week_end = Column(
        Date,
        index=True,
        nullable=False
    )

    # ICA Performance
    ica_photo = Column(
        Integer,
        default=0,
        nullable=False
    )

    ica_video = Column(
        Integer,
        default=0,
        nullable=False
    )

    active_days = Column(
        Integer,
        default=0,
        nullable=False
    )

    # TPD Performance
    tpd_test = Column(
        Integer,
        default=0,
        nullable=False
    )

    # Upload Information
    uploaded_by = Column(
        String(150),
        default="Administrator"
    )

    uploaded_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# UPLOAD LOG TABLE
# =========================================================

class UploadLog(Base):

    __tablename__ = "upload_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Uploaded File Name
    file_name = Column(
        String(255),
        nullable=False
    )

    # MASTER / ICA / TPD / COMBINED
    report_type = Column(
        String(30),
        nullable=False,
        index=True
    )

    # Weekly Report Period
    week_start = Column(
        Date,
        nullable=True
    )

    week_end = Column(
        Date,
        nullable=True
    )

    # Upload Time
    uploaded_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

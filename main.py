from datetime import date
from io import BytesIO
import re

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import MasterAWW, WeeklyMetric, UploadLog
from analytics import calculate_record, summarize, rankings


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="WBRL Performance Dashboard",
    version="1.0.0"
)


# ============================================================
# FILE PATH SETTINGS
# ============================================================

STATIC_DIR = "."


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def norm(value):
    """Normalize column names for flexible Excel matching."""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def find_col(df, options):
    """Find an Excel column using possible column names."""
    columns = {norm(col): col for col in df.columns}

    for option in options:
        normalized_option = norm(option)

        if normalized_option in columns:
            return columns[normalized_option]

    return None


def text(value):
    """Convert Excel value to clean text."""
    if pd.isna(value):
        return None

    return str(value).strip()


def code(value):
    """Convert AWC code safely."""
    if pd.isna(value):
        return None

    value = str(value).strip()

    # Excel may convert numeric codes like 12345 to 12345.0
    if value.endswith(".0"):
        value = value[:-2]

    return value


def num(value):
    """Convert values safely to integer."""
    value = pd.to_numeric(value, errors="coerce")

    if pd.isna(value):
        return 0

    return int(value)


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def home():
    return FileResponse("index.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "running",
        "message": "WBRL Performance Dashboard API is running successfully"
    }


# ============================================================
# MASTER EXCEL UPLOAD
# ============================================================

@app.post("/api/master/upload")
async def master_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    try:
        file_data = await file.read()

        df = pd.read_excel(
            BytesIO(file_data),
            dtype=object
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Excel file cannot be read: {error}"
        )

    # Find required columns
    cols = {

        "district": find_col(
            df,
            ["DISTRICT"]
        ),

        "block": find_col(
            df,
            ["BLOCK"]
        ),

        "sector": find_col(
            df,
            ["SECTOR"]
        ),

        "supervisor": find_col(
            df,
            ["SUPERVISOR"]
        ),

        "aww_name": find_col(
            df,
            ["AWW NAME"]
        ),

        "aww_mobile": find_col(
            df,
            ["AWW WP NO", "AWW MOBILE", "MOBILE"]
        ),

        "awc_name": find_col(
            df,
            ["AWC NAME", "AWW NAME.1"]
        ),

        "awc_code": find_col(
            df,
            ["AWC CODE"]
        )
    }

    # Check required columns
    required_columns = [
        "district",
        "block",
        "supervisor",
        "aww_name",
        "awc_code"
    ]

    missing = []

    for column in required_columns:

        if not cols.get(column):
            missing.append(column)

    if missing:

        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}"
        )

    created = 0
    updated = 0
    skipped = 0

    # Process each Excel row
    for _, row in df.iterrows():

        awc_code = code(
            row[cols["awc_code"]]
        )

        if not awc_code:
            skipped += 1
            continue

        values = {}

        for key, column in cols.items():

            if not column:
                continue

            if key == "awc_code":
                continue

            if key == "aww_mobile":
                values[key] = code(row[column])

            else:
                values[key] = text(row[column])

        # Check existing record
        existing = (
            db.query(MasterAWW)
            .filter(
                MasterAWW.awc_code == awc_code
            )
            .first()
        )

        if existing:

            for key, value in values.items():
                setattr(existing, key, value)

            updated += 1

        else:

            new_record = MasterAWW(
                awc_code=awc_code,
                **values
            )

            db.add(new_record)

            created += 1

    # Save upload log
    db.add(
        UploadLog(
            file_name=file.filename,
            report_type="MASTER"
        )
    )

    db.commit()

    return {

        "success": True,

        "message": "Master data processed successfully",

        "created": created,

        "updated": updated,

        "skipped": skipped
    }


# ============================================================
# WEEKLY ICA / TPD REPORT UPLOAD
# ============================================================

@app.post("/api/report/upload")
async def report_upload(

    report_type: str = Form(...),

    week_start: date = Form(...),

    week_end: date = Form(...),

    file: UploadFile = File(...),

    db: Session = Depends(get_db)
):

    # Validate report type
    report_type = report_type.upper()

    if report_type not in [
        "ICA",
        "TPD",
        "COMBINED"
    ]:

        raise HTTPException(
            status_code=400,
            detail="Invalid report type"
        )

    # Validate dates
    if week_end < week_start:

        raise HTTPException(
            status_code=400,
            detail="Week end date cannot be before week start date"
        )

    # Read Excel
    try:

        file_data = await file.read()

        df = pd.read_excel(
            BytesIO(file_data),
            dtype=object
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Excel file cannot be read: {error}"
        )

    # Find AWC CODE
    code_col = find_col(
        df,
        ["AWC CODE"]
    )

    if not code_col:

        raise HTTPException(
            status_code=400,
            detail="AWC CODE column is required"
        )

    # ICA columns
    photo_col = find_col(
        df,
        [
            "TOTAL WEEKLY ICA PHOTO",
            "ICA PHOTO",
            "TOTAL ICA PHOTO"
        ]
    )

    video_col = find_col(
        df,
        [
            "TOTAL WEEKLY ICA VIDEO",
            "ICA VIDEO",
            "TOTAL ICA VIDEO"
        ]
    )

    active_col = find_col(
        df,
        [
            "WEEKLY ACTIVITY DAYS",
            "ACTIVE DAYS"
        ]
    )

    # TPD column
    tpd_col = find_col(
        df,
        [
            "TPD TEST",
            "TPD"
        ]
    )

    processed = 0
    skipped = 0

    # Process each row
    for _, row in df.iterrows():

        awc_code = code(
            row[code_col]
        )

        if not awc_code:

            skipped += 1
            continue

        # Check AWC exists in Master
        master = (
            db.query(MasterAWW)
            .filter(
                MasterAWW.awc_code == awc_code
            )
            .first()
        )

        if not master:

            skipped += 1
            continue

        # Find existing weekly record
        metric = (

            db.query(WeeklyMetric)

            .filter(
                WeeklyMetric.awc_code == awc_code,

                WeeklyMetric.week_start == week_start,

                WeeklyMetric.week_end == week_end
            )

            .first()
        )

        # Create if not existing
        if not metric:

            metric = WeeklyMetric(

                awc_code=awc_code,

                week_start=week_start,

                week_end=week_end
            )

            db.add(metric)

        # ICA DATA
        if report_type in [
            "ICA",
            "COMBINED"
        ]:

            metric.ica_photo = (
                num(row[photo_col])
                if photo_col
                else 0
            )

            metric.ica_video = (
                num(row[video_col])
                if video_col
                else 0
            )

            metric.active_days = (

                num(row[active_col])

                if active_col

                else max(
                    metric.ica_photo,
                    metric.ica_video
                )
            )

        # TPD DATA
        if report_type in [
            "TPD",
            "COMBINED"
        ]:

            metric.tpd_test = (

                num(row[tpd_col])

                if tpd_col

                else 0
            )

        processed += 1

    # Save upload log
    db.add(

        UploadLog(

            file_name=file.filename,

            report_type=report_type,

            week_start=week_start,

            week_end=week_end
        )
    )

    db.commit()

    return {

        "success": True,

        "message": f"{report_type} report uploaded successfully",

        "processed": processed,

        "skipped": skipped
    }


# ============================================================
# GET RECORDS FOR DASHBOARD
# ============================================================

def records(
    db,
    district=None,
    block=None
):

    query = db.query(MasterAWW)

    if district:

        query = query.filter(
            MasterAWW.district == district
        )

    if block:

        query = query.filter(
            MasterAWW.block == block
        )

    masters = query.all()

    # Create weekly metrics map
    metric_map = {}

    weekly_metrics = db.query(
        WeeklyMetric
    ).all()

    for metric in weekly_metrics:

        if metric.awc_code not in metric_map:

            metric_map[metric.awc_code] = []

        metric_map[
            metric.awc_code
        ].append(metric)

    # Calculate dashboard records
    result = []

    for master in masters:

        calculated = calculate_record(

            master,

            metric_map.get(
                master.awc_code,
                []
            )
        )

        result.append(calculated)

    return result


# ============================================================
# STATE DASHBOARD
# ============================================================

@app.get("/api/dashboard/state")
def state_dashboard(
    db: Session = Depends(get_db)
):

    dashboard_records = records(db)

    return {

        "summary": summarize(
            dashboard_records
        ),

        "top_supervisors": rankings(
            dashboard_records,
            "supervisor",
            10,
            True
        ),

        "bottom_supervisors": rankings(
            dashboard_records,
            "supervisor",
            10,
            False
        ),

        "top_blocks": rankings(
            dashboard_records,
            "block",
            3,
            True
        )
    }


# ============================================================
# DISTRICT LIST
# ============================================================

@app.get("/api/dashboard/districts")
def districts(
    db: Session = Depends(get_db)
):

    districts = {

        record.district

        for record in db.query(
            MasterAWW
        ).all()

        if record.district
    }

    return sorted(districts)


# ============================================================
# DISTRICT DASHBOARD
# ============================================================

@app.get("/api/dashboard/district/{district}")
def district_dashboard(

    district: str,

    db: Session = Depends(get_db)
):

    dashboard_records = records(

        db,

        district=district
    )

    return {

        "summary": summarize(
            dashboard_records
        ),

        "top_supervisors": rankings(
            dashboard_records,
            "supervisor",
            10,
            True
        ),

        "bottom_supervisors": rankings(
            dashboard_records,
            "supervisor",
            10,
            False
        ),

        "top_blocks": rankings(
            dashboard_records,
            "block",
            10,
            True
        )
    }


# ============================================================
# BLOCK DASHBOARD
# ============================================================

@app.get("/api/dashboard/district/{district}/blocks")
def district_blocks(

    district: str,

    db: Session = Depends(get_db)
):

    blocks = {

        record.block

        for record in (

            db.query(MasterAWW)

            .filter(
                MasterAWW.district == district
            )

            .all()
        )

        if record.block
    }

    return sorted(blocks)


@app.get(
    "/api/dashboard/district/{district}/block/{block}"
)
def block_dashboard(

    district: str,

    block: str,

    db: Session = Depends(get_db)
):

    dashboard_records = records(

        db,

        district=district,

        block=block
    )

    return {

        "summary": summarize(
            dashboard_records
        ),

        "top_supervisors": rankings(
            dashboard_records,
            "supervisor",
            10,
            True
        ),

        "bottom_supervisors": rankings(
            dashboard_records,
            "supervisor",
            10,
            False
        )
    }


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="."),
    name="static"
)

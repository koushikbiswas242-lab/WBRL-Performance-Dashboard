from datetime import date
from io import BytesIO
import re

import pandas as pd

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
)

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
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="WBRL Performance Dashboard",
    version="2.0.0",
)


# ============================================================
# STATIC DIRECTORY
# ============================================================

STATIC_DIR = "."


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def norm(value):
    """
    Normalize Excel column names.

    Example:
    AWC CODE -> awccode
    AWC-Code -> awccode
    AWC Code -> awccode
    """

    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(value).lower()
    )


def find_col(df, options):
    """
    Find an Excel column using multiple possible names.
    """

    columns = {
        norm(column): column
        for column in df.columns
    }

    for option in options:

        normalized = norm(option)

        if normalized in columns:
            return columns[normalized]

    return None


def clean_text(value):
    """
    Convert Excel value to clean text.
    """

    if value is None:
        return None

    try:

        if pd.isna(value):
            return None

    except Exception:
        pass

    value = str(value).strip()

    if not value:
        return None

    return value


def clean_code(value):
    """
    Safely clean AWC CODE / mobile values.

    Excel sometimes converts:
    12345 -> 12345.0

    This function converts it back to:
    12345
    """

    if value is None:
        return None

    try:

        if pd.isna(value):
            return None

    except Exception:
        pass

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value


def number(value):
    """
    Convert Excel numeric value to integer safely.
    """

    if value is None:
        return 0

    try:

        result = pd.to_numeric(
            value,
            errors="coerce"
        )

        if pd.isna(result):
            return 0

        return int(result)

    except Exception:
        return 0


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return FileResponse(
        "index.html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "running",
        "message": "WBRL Performance Dashboard API is running",
    }


# ============================================================
# MASTER DATA UPLOAD
# ============================================================

@app.post("/api/master/upload")
async def master_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )


    filename = file.filename.lower()

    if not filename.endswith(
        (".xlsx", ".xls")
    ):

        raise HTTPException(
            status_code=400,
            detail="Please upload an Excel file (.xlsx or .xls).",
        )


    # --------------------------------------------------------
    # Read Excel
    # --------------------------------------------------------

    try:

        file_data = await file.read()

        df = pd.read_excel(
            BytesIO(file_data),
            dtype=object,
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Excel file cannot be read: {error}",
        )


    # --------------------------------------------------------
    # Empty Excel check
    # --------------------------------------------------------

    if df.empty:

        raise HTTPException(
            status_code=400,
            detail="The uploaded Excel file is empty.",
        )


    # --------------------------------------------------------
    # Find columns
    # --------------------------------------------------------

    cols = {

        "district": find_col(
            df,
            [
                "DISTRICT",
                "District",
            ],
        ),

        "block": find_col(
            df,
            [
                "BLOCK",
                "Block",
            ],
        ),

        "sector": find_col(
            df,
            [
                "SECTOR",
                "Sector",
            ],
        ),

        "supervisor": find_col(
            df,
            [
                "SUPERVISOR",
                "Supervisor",
                "SUPERVISOR NAME",
            ],
        ),

        "aww_name": find_col(
            df,
            [
                "AWW NAME",
                "AWW_NAME",
                "AWW",
            ],
        ),

        "aww_mobile": find_col(
            df,
            [
                "AWW WP NO",
                "AWW MOBILE",
                "MOBILE",
                "MOBILE NO",
                "AWW MOBILE NO",
            ],
        ),

        "awc_name": find_col(
            df,
            [
                "AWC NAME",
                "AWC_NAME",
                "AWW NAME.1",
            ],
        ),

        "awc_code": find_col(
            df,
            [
                "AWC CODE",
                "AWC_CODE",
                "AWC CODE.",
                "AWC ID",
            ],
        ),
    }


    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required = [
        "district",
        "block",
        "supervisor",
        "aww_name",
        "awc_code",
    ]


    missing = [
        column
        for column in required
        if not cols.get(column)
    ]


    if missing:

        raise HTTPException(
            status_code=400,
            detail=(
                "Missing required Excel columns: "
                + ", ".join(missing)
            ),
        )


    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    created = 0
    updated = 0
    skipped = 0


    # --------------------------------------------------------
    # Prevent duplicate AWC codes inside same Excel
    # --------------------------------------------------------

    processed_codes = set()


    # --------------------------------------------------------
    # Process rows
    # --------------------------------------------------------

    try:

        for _, row in df.iterrows():

            awc_code = clean_code(
                row[cols["awc_code"]]
            )


            # --------------------------------------------
            # Missing AWC CODE
            # --------------------------------------------

            if not awc_code:

                skipped += 1

                continue


            # --------------------------------------------
            # Duplicate AWC CODE inside Excel
            # --------------------------------------------

            if awc_code in processed_codes:

                skipped += 1

                continue


            processed_codes.add(
                awc_code
            )


            # --------------------------------------------
            # Prepare values
            # --------------------------------------------

            values = {}


            for key, column in cols.items():

                if not column:
                    continue


                if key == "awc_code":
                    continue


                if key == "aww_mobile":

                    values[key] = clean_code(
                        row[column]
                    )

                else:

                    values[key] = clean_text(
                        row[column]
                    )


            # --------------------------------------------
            # Search existing AWC
            # --------------------------------------------

            existing = (
                db.query(MasterAWW)
                .filter(
                    MasterAWW.awc_code == awc_code
                )
                .first()
            )


            # --------------------------------------------
            # UPDATE existing record
            # --------------------------------------------

            if existing:

                for key, value in values.items():

                    setattr(
                        existing,
                        key,
                        value
                    )


                updated += 1


            # --------------------------------------------
            # CREATE new record
            # --------------------------------------------

            else:

                new_record = MasterAWW(
                    awc_code=awc_code,
                    **values,
                )

                db.add(
                    new_record
                )

                created += 1


        # ------------------------------------------------
        # Upload log
        # ------------------------------------------------

        db.add(
            UploadLog(
                file_name=file.filename,
                report_type="MASTER",
            )
        )


        # ------------------------------------------------
        # Commit
        # ------------------------------------------------

        db.commit()


    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Master upload failed: "
                + str(error)
            ),
        )


    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "success": True,

        "message":
            "Master data processed successfully.",

        "created":
            created,

        "updated":
            updated,

        "skipped":
            skipped,

        "total_processed":
            created + updated,
    }


# ============================================================
# ICA / TPD WEEKLY REPORT UPLOAD
# ============================================================

@app.post("/api/report/upload")
async def report_upload(

    report_type: str = Form(...),

    week_start: date = Form(...),

    week_end: date = Form(...),

    file: UploadFile = File(...),

    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Report type
    # --------------------------------------------------------

    report_type = report_type.upper().strip()


    if report_type not in [
        "ICA",
        "TPD",
        "COMBINED",
    ]:

        raise HTTPException(
            status_code=400,
            detail="Invalid report type.",
        )


    # --------------------------------------------------------
    # Date validation
    # --------------------------------------------------------

    if week_end < week_start:

        raise HTTPException(
            status_code=400,
            detail=(
                "Week end date cannot be "
                "before week start date."
            ),
        )


    # --------------------------------------------------------
    # Read Excel
    # --------------------------------------------------------

    try:

        file_data = await file.read()

        df = pd.read_excel(
            BytesIO(file_data),
            dtype=object,
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Excel file cannot be read: {error}",
        )


    if df.empty:

        raise HTTPException(
            status_code=400,
            detail="The uploaded report is empty.",
        )


    # --------------------------------------------------------
    # AWC CODE
    # --------------------------------------------------------

    code_col = find_col(
        df,
        [
            "AWC CODE",
            "AWC_CODE",
            "AWC ID",
        ],
    )


    if not code_col:

        raise HTTPException(
            status_code=400,
            detail="AWC CODE column is required.",
        )


    # --------------------------------------------------------
    # ICA columns
    # --------------------------------------------------------

    photo_col = find_col(
        df,
        [
            "TOTAL WEEKLY ICA PHOTO",
            "ICA PHOTO",
            "TOTAL ICA PHOTO",
            "WEEKLY ICA PHOTO",
        ],
    )


    video_col = find_col(
        df,
        [
            "TOTAL WEEKLY ICA VIDEO",
            "ICA VIDEO",
            "TOTAL ICA VIDEO",
            "WEEKLY ICA VIDEO",
        ],
    )


    active_col = find_col(
        df,
        [
            "WEEKLY ACTIVITY DAYS",
            "ACTIVE DAYS",
            "ACTIVITY DAYS",
        ],
    )


    # --------------------------------------------------------
    # TPD column
    # --------------------------------------------------------

    tpd_col = find_col(
        df,
        [
            "TPD TEST",
            "TPD",
            "TPD TEST COUNT",
        ],
    )


    processed = 0
    skipped = 0

    processed_codes = set()


    # --------------------------------------------------------
    # Process report
    # --------------------------------------------------------

    try:

        for _, row in df.iterrows():

            awc_code = clean_code(
                row[code_col]
            )


            # Missing code
            if not awc_code:

                skipped += 1

                continue


            # Duplicate code in same report
            if awc_code in processed_codes:

                skipped += 1

                continue


            processed_codes.add(
                awc_code
            )


            # --------------------------------------------
            # Check master
            # --------------------------------------------

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


            # --------------------------------------------
            # Find existing weekly metric
            # --------------------------------------------

            metric = (
                db.query(WeeklyMetric)
                .filter(
                    WeeklyMetric.awc_code == awc_code,
                    WeeklyMetric.week_start == week_start,
                    WeeklyMetric.week_end == week_end,
                )
                .first()
            )


            # --------------------------------------------
            # Create new weekly record
            # --------------------------------------------

            if not metric:

                metric = WeeklyMetric(

                    awc_code=awc_code,

                    week_start=week_start,

                    week_end=week_end,

                )

                db.add(metric)


            # --------------------------------------------
            # ICA
            # --------------------------------------------

            if report_type in [
                "ICA",
                "COMBINED",
            ]:

                photo = (
                    number(row[photo_col])
                    if photo_col
                    else 0
                )


                video = (
                    number(row[video_col])
                    if video_col
                    else 0
                )


                if active_col:

                    active_days = number(
                        row[active_col]
                    )

                else:

                    active_days = max(
                        photo,
                        video
                    )


                metric.ica_photo = photo

                metric.ica_video = video

                metric.active_days = active_days


            # --------------------------------------------
            # TPD
            # --------------------------------------------

            if report_type in [
                "TPD",
                "COMBINED",
            ]:

                metric.tpd_test = (

                    number(
                        row[tpd_col]
                    )

                    if tpd_col

                    else 0

                )


            processed += 1


        # ------------------------------------------------
        # Upload log
        # ------------------------------------------------

        db.add(
            UploadLog(

                file_name=file.filename,

                report_type=report_type,

                week_start=week_start,

                week_end=week_end,

            )
        )


        db.commit()


    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Report upload failed: "
                + str(error)
            ),
        )


    return {

        "success": True,

        "message":
            f"{report_type} report uploaded successfully.",

        "processed":
            processed,

        "skipped":
            skipped,
    }


# ============================================================
# DASHBOARD RECORD GENERATOR
# ============================================================

def get_records(
    db,
    district=None,
    block=None,
):

    query = db.query(
        MasterAWW
    )


    # District filter
    if district:

        query = query.filter(
            MasterAWW.district == district
        )


    # Block filter
    if block:

        query = query.filter(
            MasterAWW.block == block
        )


    masters = query.all()


    # --------------------------------------------------------
    # Weekly metrics map
    # --------------------------------------------------------

    metric_map = {}


    metrics = db.query(
        WeeklyMetric
    ).all()


    for metric in metrics:

        metric_map.setdefault(
            metric.awc_code,
            []
        ).append(metric)


    # --------------------------------------------------------
    # Calculate records
    # --------------------------------------------------------

    result = []


    for master in masters:

        calculated = calculate_record(

            master,

            metric_map.get(
                master.awc_code,
                []
            )

        )

        result.append(
            calculated
        )


    return result


# ============================================================
# STATE DASHBOARD
# ============================================================

@app.get("/api/dashboard/state")
def state_dashboard(
    db: Session = Depends(get_db),
):

    dashboard_records = get_records(
        db
    )


    return {

        "level":
            "state",

        "summary":
            summarize(
                dashboard_records
            ),

        "top_supervisors":
            rankings(
                dashboard_records,
                "supervisor",
                10,
                True
            ),

        "bottom_supervisors":
            rankings(
                dashboard_records,
                "supervisor",
                10,
                False
            ),

        "top_blocks":
            rankings(
                dashboard_records,
                "block",
                3,
                True
            ),
    }


# ============================================================
# DISTRICT LIST
# ============================================================

@app.get("/api/dashboard/districts")
def district_list(
    db: Session = Depends(get_db),
):

    district_values = {

        record.district

        for record in db.query(
            MasterAWW
        ).all()

        if record.district
    }


    return sorted(
        district_values
    )


# ============================================================
# BLOCK LIST FOR DISTRICT
# ============================================================

@app.get(
    "/api/dashboard/blocks/{district}"
)
def block_list(
    district: str,
    db: Session = Depends(get_db),
):

    block_values = {

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


    return sorted(
        block_values
    )


# ============================================================
# DISTRICT DASHBOARD
# ============================================================

@app.get(
    "/api/dashboard/district/{district}"
)
def district_dashboard(

    district: str,

    db: Session = Depends(get_db),

):

    dashboard_records = get_records(

        db,

        district=district,

    )


    return {

        "level":
            "district",

        "district":
            district,

        "summary":
            summarize(
                dashboard_records
            ),

        "top_supervisors":
            rankings(
                dashboard_records,
                "supervisor",
                10,
                True
            ),

        "bottom_supervisors":
            rankings(
                dashboard_records,
                "supervisor",
                10,
                False
            ),

        "top_blocks":
            rankings(
                dashboard_records,
                "block",
                10,
                True
            ),
    }


# ============================================================
# BLOCK DASHBOARD
# ============================================================

@app.get(
    "/api/dashboard/block/{district}/{block}"
)
def block_dashboard(

    district: str,

    block: str,

    db: Session = Depends(get_db),

):

    dashboard_records = get_records(

        db,

        district=district,

        block=block,

    )


    return {

        "level":
            "block",

        "district":
            district,

        "block":
            block,

        "summary":
            summarize(
                dashboard_records
            ),

        "top_supervisors":
            rankings(
                dashboard_records,
                "supervisor",
                10,
                True
            ),

        "bottom_supervisors":
            rankings(
                dashboard_records,
                "supervisor",
                10,
                False
            ),

        "top_blocks":
            rankings(
                dashboard_records,
                "block",
                1,
                True
            ),
    }


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static",
)

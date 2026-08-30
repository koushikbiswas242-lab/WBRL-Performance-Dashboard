from datetime import date
from io import BytesIO
import re
import pandas as pd

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import MasterAWW, WeeklyMetric, UploadLog
from .analytics import calculate_record, summarize, rankings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="WBRL Performance Dashboard")
STATIC_DIR = "backend/static"

def norm(v): return re.sub(r"[^a-z0-9]+", "", str(v).lower())

def find_col(df, options):
    cols = {norm(c): c for c in df.columns}
    for x in options:
        if norm(x) in cols:
            return cols[norm(x)]
    return None

def text(v):
    return None if pd.isna(v) else str(v).strip()

def code(v):
    if pd.isna(v): return None
    x = str(v).strip()
    return x[:-2] if x.endswith(".0") else x

@app.get("/")
def home():
    return FileResponse(f"{STATIC_DIR}/index.html")

@app.post("/api/master/upload")
async def master_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = pd.read_excel(BytesIO(await file.read()), dtype=object)
    except Exception as e:
        raise HTTPException(400, f"Excel file cannot be read: {e}")

    cols = {
        "district": find_col(df, ["DISTRICT"]),
        "block": find_col(df, ["BLOCK"]),
        "sector": find_col(df, ["SECTOR"]),
        "supervisor": find_col(df, ["SUPERVISOR"]),
        "aww_name": find_col(df, ["AWW NAME"]),
        "aww_mobile": find_col(df, ["AWW WP NO", "AWW MOBILE"]),
        "awc_name": find_col(df, ["AWC NAME", "AWW NAME.1"]),
        "awc_code": find_col(df, ["AWC CODE"])
    }
    missing = [k for k in ("district","block","supervisor","aww_name","awc_code") if not cols[k]]
    if missing:
        raise HTTPException(400, f"Missing columns: {', '.join(missing)}")

    created = updated = skipped = 0
    for _, row in df.iterrows():
        c = code(row[cols["awc_code"]])
        if not c:
            skipped += 1
            continue
        values = {k: (code(row[v]) if k == "aww_mobile" else text(row[v])) for k,v in cols.items() if v and k != "awc_code"}
        obj = db.query(MasterAWW).filter(MasterAWW.awc_code == c).first()
        if obj:
            for k,v in values.items(): setattr(obj,k,v)
            updated += 1
        else:
            db.add(MasterAWW(awc_code=c, **values))
            created += 1
    db.add(UploadLog(file_name=file.filename, report_type="MASTER"))
    db.commit()
    return {"message":"Master data processed successfully","created":created,"updated":updated,"skipped":skipped}

@app.post("/api/report/upload")
async def report_upload(
    report_type: str = Form(...),
    week_start: date = Form(...),
    week_end: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if report_type not in ("ICA","TPD","COMBINED"):
        raise HTTPException(400,"Invalid report type")
    try:
        df = pd.read_excel(BytesIO(await file.read()), dtype=object)
    except Exception as e:
        raise HTTPException(400, f"Excel file cannot be read: {e}")

    code_col = find_col(df, ["AWC CODE"])
    if not code_col:
        raise HTTPException(400, "AWC CODE is required")

    photo_col = find_col(df, ["TOTAL WEEKLY ICA PHOTO", "ICA PHOTO", "TOTAL ICA PHOTO"])
    video_col = find_col(df, ["TOTAL WEEKLY ICA VIDEO", "ICA VIDEO", "TOTAL ICA VIDEO"])
    active_col = find_col(df, ["WEEKLY ACTIVITY DAYS", "ACTIVE DAYS"])
    tpd_col = find_col(df, ["TPD TEST", "TPD"])

    def num(v):
        x = pd.to_numeric(v, errors="coerce")
        return 0 if pd.isna(x) else int(x)

    processed = skipped = 0
    for _, row in df.iterrows():
        c = code(row[code_col])
        if not c or not db.query(MasterAWW).filter(MasterAWW.awc_code == c).first():
            skipped += 1
            continue

        obj = db.query(WeeklyMetric).filter(
            WeeklyMetric.awc_code == c,
            WeeklyMetric.week_start == week_start,
            WeeklyMetric.week_end == week_end
        ).first()

        if not obj:
            obj = WeeklyMetric(awc_code=c, week_start=week_start, week_end=week_end)
            db.add(obj)

        if report_type in ("ICA","COMBINED"):
            obj.ica_photo = num(row[photo_col]) if photo_col else 0
            obj.ica_video = num(row[video_col]) if video_col else 0
            obj.active_days = num(row[active_col]) if active_col else max(obj.ica_photo, obj.ica_video)
        if report_type in ("TPD","COMBINED"):
            obj.tpd_test = num(row[tpd_col]) if tpd_col else 0
        processed += 1

    db.add(UploadLog(file_name=file.filename, report_type=report_type, week_start=week_start, week_end=week_end))
    db.commit()
    return {"message":f"{report_type} report uploaded successfully","processed":processed,"skipped":skipped}

def records(db, district=None, block=None):
    q = db.query(MasterAWW)
    if district: q = q.filter(MasterAWW.district == district)
    if block: q = q.filter(MasterAWW.block == block)
    masters = q.all()
    metric_map = {}
    for m in db.query(WeeklyMetric).all():
        metric_map.setdefault(m.awc_code, []).append(m)
    return [calculate_record(x, metric_map.get(x.awc_code, [])) for x in masters]

@app.get("/api/dashboard/state")
def state_dashboard(db: Session = Depends(get_db)):
    r = records(db)
    return {"summary":summarize(r),
            "top_supervisors":rankings(r,"supervisor",10,True),
            "bottom_supervisors":rankings(r,"supervisor",10,False),
            "top_blocks":rankings(r,"block",3,True)}

@app.get("/api/dashboard/districts")
def districts(db: Session = Depends(get_db)):
    return sorted({x.district for x in db.query(MasterAWW).all() if x.district})

@app.get("/api/dashboard/district/{district}")
def district_dashboard(district: str, db: Session = Depends(get_db)):
    r = records(db, district=district)
    return {"summary":summarize(r),
            "top_supervisors":rankings(r,"supervisor",10,True),
            "bottom_supervisors":rankings(r,"supervisor",10,False),
            "top_blocks":rankings(r,"block",10,True)}

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

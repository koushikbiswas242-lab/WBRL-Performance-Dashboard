from collections import defaultdict

def certification(active_days, tpd_test):
    if active_days == 0 and tpd_test == 0:
        return "Not Active"
    if 12 <= active_days <= 24 and tpd_test >= 3:
        return "Gold"
    if 8 <= active_days <= 11 and tpd_test >= 2:
        return "Silver"
    if 4 <= active_days <= 7 and tpd_test >= 1:
        return "Bronze"
    return "Participation Certificate"

def calculate_record(master, metrics):
    photo = sum(int(m.ica_photo or 0) for m in metrics)
    video = sum(int(m.ica_video or 0) for m in metrics)
    active_days = sum(int(m.active_days or 0) for m in metrics)
    tpd = sum(int(m.tpd_test or 0) for m in metrics)
    active = 1 if active_days > 0 else 0
    return {
        "district": master.district, "block": master.block,
        "sector": master.sector, "supervisor": master.supervisor,
        "aww_name": master.aww_name, "awc_code": master.awc_code,
        "monthly_ica_photo": photo, "monthly_ica_video": video,
        "monthly_ica_total": photo + video,
        "monthly_active_days": active_days, "monthly_tpd_test": tpd,
        "eligibility": certification(active_days, tpd),
        "active_aww": active
    }

def summarize(records):
    total = len(records)
    gold = sum(r["eligibility"] == "Gold" for r in records)
    silver = sum(r["eligibility"] == "Silver" for r in records)
    bronze = sum(r["eligibility"] == "Bronze" for r in records)
    certified = gold + silver + bronze
    return {
        "total_aww": total,
        "active_aww": sum(r["active_aww"] for r in records),
        "inactive_aww": sum(r["eligibility"] == "Not Active" for r in records),
        "gold": gold, "silver": silver, "bronze": bronze,
        "participation": sum(r["eligibility"] == "Participation Certificate" for r in records),
        "certified": certified,
        "certification_rate": round(certified / total * 100, 2) if total else 0
    }

def rankings(records, key, limit, reverse=True):
    groups = defaultdict(list)
    for r in records:
        if r.get(key):
            groups[r[key]].append(r)
    result = []
    for name, rows in groups.items():
        total = len(rows)
        certified = sum(r["eligibility"] in ("Gold","Silver","Bronze") for r in rows)
        active = sum(r["active_aww"] for r in rows)
        score = round(certified / total * 100, 2) if total else 0
        result.append({"name": name, "total_aww": total, "active_aww": active,
                       "certified": certified, "score": score})
    return sorted(result, key=lambda x: x["score"], reverse=reverse)[:limit]

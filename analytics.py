from collections import defaultdict


# =========================================================
# CERTIFICATION LOGIC
# =========================================================

def certification(active_days, tpd_test):

    active_days = int(active_days or 0)
    tpd_test = int(tpd_test or 0)

    # Not Active
    if active_days == 0 and tpd_test == 0:
        return "Not Active"

    # Gold
    if active_days >= 12 and tpd_test >= 3:
        return "Gold"

    # Silver
    if active_days >= 8 and tpd_test >= 2:
        return "Silver"

    # Bronze
    if active_days >= 4 and tpd_test >= 1:
        return "Bronze"

    # Participation
    return "Participation Certificate"


# =========================================================
# CALCULATE INDIVIDUAL AWW PERFORMANCE
# =========================================================

def calculate_record(master, metrics):

    total_photo = sum(
        int(metric.ica_photo or 0)
        for metric in metrics
    )

    total_video = sum(
        int(metric.ica_video or 0)
        for metric in metrics
    )

    total_active_days = sum(
        int(metric.active_days or 0)
        for metric in metrics
    )

    total_tpd = sum(
        int(metric.tpd_test or 0)
        for metric in metrics
    )

    # Active status
    active_aww = 1 if total_active_days > 0 else 0

    # Certification
    eligibility = certification(
        total_active_days,
        total_tpd
    )

    return {

        # Location
        "district": master.district,
        "block": master.block,
        "sector": master.sector,

        # Supervisor
        "supervisor": master.supervisor,

        # AWW Details
        "aww_name": master.aww_name,
        "awc_code": master.awc_code,

        # ICA Performance
        "monthly_ica_photo": total_photo,
        "monthly_ica_video": total_video,
        "monthly_ica_total": (
            total_photo + total_video
        ),

        # Activity Performance
        "monthly_active_days": total_active_days,

        # TPD Performance
        "monthly_tpd_test": total_tpd,

        # Achievement
        "eligibility": eligibility,

        # Status
        "active_aww": active_aww
    }


# =========================================================
# DASHBOARD SUMMARY
# =========================================================

def summarize(records):

    total_aww = len(records)

    active_aww = sum(
        record["active_aww"]
        for record in records
    )

    inactive_aww = sum(
        record["eligibility"] == "Not Active"
        for record in records
    )

    gold = sum(
        record["eligibility"] == "Gold"
        for record in records
    )

    silver = sum(
        record["eligibility"] == "Silver"
        for record in records
    )

    bronze = sum(
        record["eligibility"] == "Bronze"
        for record in records
    )

    participation = sum(
        record["eligibility"]
        == "Participation Certificate"
        for record in records
    )

    certified = (
        gold
        + silver
        + bronze
    )

    certification_rate = (

        round(
            (certified / total_aww) * 100,
            2
        )

        if total_aww > 0

        else 0
    )

    return {

        "total_aww": total_aww,

        "active_aww": active_aww,

        "inactive_aww": inactive_aww,

        "gold": gold,

        "silver": silver,

        "bronze": bronze,

        "participation": participation,

        "certified": certified,

        "certification_rate": certification_rate
    }


# =========================================================
# RANKINGS
# SUPERVISOR / BLOCK
# =========================================================

def rankings(
    records,
    key,
    limit=10,
    reverse=True
):

    groups = defaultdict(list)

    # Group records
    for record in records:

        group_name = record.get(key)

        if group_name:

            groups[group_name].append(
                record
            )

    result = []

    # Calculate each group's performance
    for name, rows in groups.items():

        total_aww = len(rows)

        active_aww = sum(
            row["active_aww"]
            for row in rows
        )

        gold = sum(
            row["eligibility"] == "Gold"
            for row in rows
        )

        silver = sum(
            row["eligibility"] == "Silver"
            for row in rows
        )

        bronze = sum(
            row["eligibility"] == "Bronze"
            for row in rows
        )

        certified = (
            gold
            + silver
            + bronze
        )

        score = (

            round(
                (certified / total_aww) * 100,
                2
            )

            if total_aww > 0

            else 0
        )

        result.append({

            "name": name,

            "total_aww": total_aww,

            "active_aww": active_aww,

            "gold": gold,

            "silver": silver,

            "bronze": bronze,

            "certified": certified,

            "score": score
        })

    # Sort ranking
    sorted_result = sorted(

        result,

        key=lambda item: (
            item["score"],
            item["certified"],
            item["active_aww"]
        ),

        reverse=reverse
    )

    return sorted_result[:limit]

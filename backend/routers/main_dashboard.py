from fastapi import APIRouter, Query
import core.db as db
from core.helpers import parse_range, fmt, safe_delta

router = APIRouter(prefix="/api/main-dashboard", tags=["main-dashboard"])


@router.get("/summary")
def main_summary(range: str = Query(default="24h")):
    start, end, _ = parse_range(range)
    cur = db.db_conn.cursor()

    cur.execute(
        """
        SELECT ts, value
        FROM telemetry
        WHERE device = 'main_meter_1'
          AND point = 'power'
        ORDER BY ts DESC
        LIMIT 1
        """
    )
    latest_power_row = cur.fetchone()

    cur.execute(
        """
        SELECT AVG(value), MAX(value)
        FROM telemetry
        WHERE device = 'main_meter_1'
          AND point = 'power'
          AND ts >= %s AND ts <= %s
        """,
        (start, end),
    )
    power_row = cur.fetchone()

    cur.execute(
        """
        SELECT MIN(value), MAX(value)
        FROM telemetry
        WHERE device = 'main_meter_1'
          AND point = 'energy'
          AND ts >= %s AND ts <= %s
        """,
        (start, end),
    )
    main_energy_row = cur.fetchone()

    main_energy_consumption = None
    if main_energy_row:
        main_energy_consumption = safe_delta(
            main_energy_row[1], main_energy_row[0], clamp_zero=True
        )

    cur.execute(
        """
        SELECT device, MIN(value), MAX(value)
        FROM telemetry
        WHERE device IN ('floor_meter_1', 'floor_meter_2', 'floor_meter_3', 'floor_meter_4')
          AND point = 'energy'
          AND ts >= %s AND ts <= %s
        GROUP BY device
        """,
        (start, end),
    )

    floor_total = 0.0
    floor_found = False
    for device, min_val, max_val in cur.fetchall():
        delta = safe_delta(max_val, min_val, clamp_zero=True)
        if delta is not None:
            floor_total += delta
            floor_found = True

    total_floor_energy = fmt(floor_total, 1) if floor_found else None

    cur.execute(
        """
        SELECT
            AVG(CASE WHEN point = 'temperature' THEN value END),
            AVG(CASE WHEN point = 'co2' THEN value END),
            AVG(CASE WHEN point = 'pm25' THEN value END),
            AVG(CASE WHEN point = 'humidity' THEN value END)
        FROM telemetry
        WHERE device LIKE 'iaq_%%'
          AND ts >= %s AND ts <= %s
        """,
        (start, end),
    )
    iaq_row = cur.fetchone()

    cur.execute(
        """
        SELECT point, value
        FROM (
            SELECT DISTINCT ON (point)
                point, value
            FROM telemetry
            WHERE device = 'weather_1'
            ORDER BY point, ts DESC
        ) t
        """
    )
    weather = {r[0]: r[1] for r in cur.fetchall()}

    cur.close()

    return {
        "range": range,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "latest_main_power_ts": str(latest_power_row[0]) if latest_power_row else None,
        "latest_main_power": fmt(latest_power_row[1]) if latest_power_row else None,
        "avg_main_power": fmt(power_row[0]) if power_row else None,
        "peak_main_power": fmt(power_row[1]) if power_row else None,
        "main_energy_consumption": (
            fmt(main_energy_consumption, 1)
            if main_energy_consumption is not None
            else None
        ),
        "total_floor_energy": total_floor_energy,
        "avg_temp": fmt(iaq_row[0], 1) if iaq_row else None,
        "avg_co2": fmt(iaq_row[1], 0) if iaq_row else None,
        "avg_pm25": fmt(iaq_row[2], 1) if iaq_row else None,
        "avg_humidity": fmt(iaq_row[3], 1) if iaq_row else None,
        "outdoor_drybulb": fmt(weather.get("drybulb_temperature"), 1),
        "outdoor_humidity": fmt(weather.get("humidity"), 1),
        "outdoor_wetbulb": fmt(weather.get("wetbulb_temperature"), 1),
    }


@router.get("/floor-iaq")
def main_floor_iaq(range: str = Query(default="24h")):
    start, end, _ = parse_range(range)
    cur = db.db_conn.cursor()

    cur.execute(
        """
        SELECT
            floor,
            AVG(CASE WHEN point = 'temperature' THEN value END),
            MIN(CASE WHEN point = 'temperature' THEN value END),
            MAX(CASE WHEN point = 'temperature' THEN value END),

            AVG(CASE WHEN point = 'humidity' THEN value END),
            MIN(CASE WHEN point = 'humidity' THEN value END),
            MAX(CASE WHEN point = 'humidity' THEN value END),

            AVG(CASE WHEN point = 'co2' THEN value END),
            MIN(CASE WHEN point = 'co2' THEN value END),
            MAX(CASE WHEN point = 'co2' THEN value END),

            AVG(CASE WHEN point = 'pm25' THEN value END),
            MIN(CASE WHEN point = 'pm25' THEN value END),
            MAX(CASE WHEN point = 'pm25' THEN value END)
        FROM telemetry
        WHERE device LIKE 'iaq_%%'
          AND floor IS NOT NULL
          AND ts >= %s AND ts <= %s
        GROUP BY floor
        ORDER BY floor
        """,
        (start, end),
    )

    rows = cur.fetchall()
    cur.close()

    return [
        {
            "floor": r[0],
            "avg_temp": fmt(r[1], 1),
            "min_temp": fmt(r[2], 1),
            "max_temp": fmt(r[3], 1),
            "avg_humidity": fmt(r[4], 1),
            "min_humidity": fmt(r[5], 1),
            "max_humidity": fmt(r[6], 1),
            "avg_co2": fmt(r[7], 0),
            "min_co2": fmt(r[8], 0),
            "max_co2": fmt(r[9], 0),
            "avg_pm25": fmt(r[10], 1),
            "min_pm25": fmt(r[11], 1),
            "max_pm25": fmt(r[12], 1),
        }
        for r in rows
    ]


@router.get("/power-trend")
def main_power_trend(range: str = Query(default="24h")):
    start, end, trunc = parse_range(range)
    cur = db.db_conn.cursor()

    cur.execute(
        f"""
        SELECT date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS t, AVG(value)
        FROM telemetry
        WHERE device = 'main_meter_1'
          AND point = 'power'
          AND ts >= %s AND ts <= %s
        GROUP BY t
        ORDER BY t
        """,
        (start, end),
    )

    rows = cur.fetchall()
    cur.close()

    return [{"ts": str(r[0]), "value": fmt(r[1], 2)} for r in rows]


@router.get("/co2-trend")
def main_co2_trend(range: str = Query(default="24h")):
    start, end, trunc = parse_range(range)
    cur = db.db_conn.cursor()

    cur.execute(
        f"""
        SELECT
            date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
            floor,
            AVG(value) AS avg_value
        FROM telemetry
        WHERE device LIKE 'iaq_%%'
          AND point = 'co2'
          AND floor IS NOT NULL
          AND ts >= %s AND ts <= %s
        GROUP BY bucket_ts, floor
        ORDER BY bucket_ts ASC, floor ASC
        """,
        (start, end),
    )

    datasets = {
        "floor_1": [],
        "floor_2": [],
        "floor_3": [],
        "floor_4": [],
    }

    rows = cur.fetchall()

    if not rows:
        cur.execute(
            f"""
            SELECT
                date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
                floor,
                AVG(value) AS avg_value
            FROM telemetry
            WHERE device LIKE 'iaq_%%'
              AND point = 'co2'
              AND floor IS NOT NULL
            GROUP BY bucket_ts, floor
            ORDER BY bucket_ts ASC, floor ASC
            """
        )
        rows = cur.fetchall()

    for bucket_ts, floor, avg_value in rows:
        key = f"floor_{floor}"
        if key in datasets:
            datasets[key].append({
                "ts": str(bucket_ts),
                "value": fmt(avg_value, 0) if avg_value is not None else None,
            })

    cur.close()

    return {
        "range": range,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "metric": "co2",
        "datasets": datasets,
    }


@router.get("/pm25-trend")
def main_pm25_trend(range: str = Query(default="24h")):
    start, end, trunc = parse_range(range)
    cur = db.db_conn.cursor()

    cur.execute(
        f"""
        SELECT
            date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
            floor,
            AVG(value) AS avg_value
        FROM telemetry
        WHERE device LIKE 'iaq_%%'
          AND point = 'pm25'
          AND floor IS NOT NULL
          AND ts >= %s AND ts <= %s
        GROUP BY bucket_ts, floor
        ORDER BY bucket_ts ASC, floor ASC
        """,
        (start, end),
    )

    datasets = {
        "floor_1": [],
        "floor_2": [],
        "floor_3": [],
        "floor_4": [],
    }

    rows = cur.fetchall()

    if not rows:
        cur.execute(
            f"""
            SELECT
                date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
                floor,
                AVG(value) AS avg_value
            FROM telemetry
            WHERE device LIKE 'iaq_%%'
              AND point = 'pm25'
              AND floor IS NOT NULL
            GROUP BY bucket_ts, floor
            ORDER BY bucket_ts ASC, floor ASC
            """
        )
        rows = cur.fetchall()

    for bucket_ts, floor, avg_value in rows:
        key = f"floor_{floor}"
        if key in datasets:
            datasets[key].append({
                "ts": str(bucket_ts),
                "value": fmt(avg_value, 1) if avg_value is not None else None,
            })

    cur.close()

    return {
        "range": range,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "metric": "pm25",
        "datasets": datasets,
    }
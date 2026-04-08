from fastapi import APIRouter, Query
import core.db as db
from core.helpers import (
    parse_range,
    fmt,
    fetch_latest_points,
    fetch_energy_delta_by_devices,
)

router = APIRouter(prefix="/api/electrical", tags=["electrical"])


@router.get("/summary")
def electrical_summary(range: str = Query(default="24h")):
    start, end, _ = parse_range(range)
    cur = db.db_conn.cursor()

    all_meters = [
        "main_meter_1",
        "floor_meter_1",
        "floor_meter_2",
        "floor_meter_3",
        "floor_meter_4",
        "chiller_meter_1",
        "chiller_meter_2",
        "chiller_meter_3",
        "chwp_meter_1",
        "chwp_meter_2",
        "chwp_meter_3",
        "cdp_meter_1",
        "cdp_meter_2",
        "cdp_meter_3",
        "ct_meter_1",
        "ct_meter_2",
        "ct_meter_3",
        "ahu_meter_1",
        "ahu_meter_2",
        "ahu_meter_3",
        "ahu_meter_4",
    ]

    meters, _ = fetch_latest_points(cur, all_meters)
    energy_delta = fetch_energy_delta_by_devices(cur, all_meters, start, end)

    cur.close()

    return {
        "range": range,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "meters": meters,
        "energy_delta": {k: v.get("energy_delta") for k, v in energy_delta.items()},
    }


@router.get("/trend")
def electrical_trend(
    range: str = Query(default="24h"), metric: str = Query(default="power")
):
    if metric not in {"power", "energy", "current", "power_factor"}:
        return {"error": "invalid metric"}

    start, end, trunc = parse_range(range)
    cur = db.db_conn.cursor()

    cur.execute(
        f"""
        SELECT date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS t, device, AVG(value)
        FROM telemetry
        WHERE device IN ('main_meter_1','floor_meter_1','floor_meter_2','floor_meter_3','floor_meter_4')
          AND point = %s
          AND ts >= %s AND ts <= %s
        GROUP BY t, device
        ORDER BY t
        """,
        (metric, start, end),
    )

    rows = cur.fetchall()
    cur.close()

    datasets = {}
    for t, device, v in rows:
        datasets.setdefault(device, []).append({"ts": str(t), "value": fmt(v, 2)})

    return {
        "range": range,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "metric": metric,
        "datasets": datasets,
    }
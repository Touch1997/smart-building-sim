from fastapi import APIRouter, Query
import core.db as db
from core.helpers import (
    parse_range,
    fmt,
    fetch_latest_points,
    fetch_energy_delta_by_devices,
    sum_energy_delta,
)

router = APIRouter(prefix="/api/chiller", tags=["chiller"])


@router.get("/summary")
def chiller_summary(range: str = Query(default="24h")):
    start, end, _ = parse_range(range)
    cur = db.db_conn.cursor()

    chiller_devices = ["chiller_1", "chiller_2", "chiller_3"]
    chiller_meter_devices = ["chiller_meter_1", "chiller_meter_2", "chiller_meter_3"]

    chillers, latest_ts = fetch_latest_points(cur, chiller_devices, start, end)

    if not chillers:
        chillers, latest_ts = fetch_latest_points(cur, chiller_devices)

    total_power = 0.0
    total_rt = 0.0
    power_found = False
    rt_found = False
    active_chillers = 0

    for device in chiller_devices:
        ch = chillers.setdefault(device, {})
        power = ch.get("power")
        rt = ch.get("cooling_rate")
        status = ch.get("status_read")

        if power is not None:
            total_power += float(power)
            power_found = True

        if rt is not None:
            total_rt += float(rt)
            rt_found = True

        if status == 1:
            active_chillers += 1

    total_power = fmt(total_power, 2) if power_found else None
    total_rt = fmt(total_rt, 2) if rt_found else None

    plant_efficiency = None
    if total_power is not None and total_rt not in (None, 0):
        plant_efficiency = fmt(float(total_power) / float(total_rt), 3)

    pump_devices = [
        "chwp_1",
        "chwp_2",
        "chwp_3",
        "cdp_1",
        "cdp_2",
        "cdp_3",
        "ct_1",
        "ct_2",
        "ct_3",
    ]
    pumps, _ = fetch_latest_points(cur, pump_devices)

    chiller_energy_by_meter = fetch_energy_delta_by_devices(
        cur, chiller_meter_devices, start, end
    )
    for meter in chiller_meter_devices:
        chiller_energy_by_meter.setdefault(
            meter, {"first_value": None, "last_value": None, "energy_delta": None}
        )

    total_chiller_energy = sum_energy_delta(chiller_energy_by_meter)

    cur.close()

    return {
        "range": range,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "latest_ts": str(latest_ts) if latest_ts else None,
        "total_power": total_power,
        "total_rt": total_rt,
        "plant_efficiency": plant_efficiency,
        "active_chillers": active_chillers,
        "total_chiller_energy": total_chiller_energy,
        "chiller_energy_by_meter": chiller_energy_by_meter,
        "chillers": chillers,
        "pumps": pumps,
    }


@router.get("/trend")
def chiller_trend(
    range: str = Query(default="24h"), metric: str = Query(default="power")
):
    if metric not in {"power", "cooling_rate", "efficiency"}:
        return {"error": "invalid metric"}

    start, end, trunc = parse_range(range)
    cur = db.db_conn.cursor()

    cur.execute(
        f"""
        SELECT date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS t, device, AVG(value)
        FROM telemetry
        WHERE device IN ('chiller_1', 'chiller_2', 'chiller_3')
          AND point = %s
          AND ts >= %s AND ts <= %s
        GROUP BY t, device
        ORDER BY t
    """,
        (metric, start, end),
    )

    rows = cur.fetchall()
    cur.close()

    datasets = {"chiller_1": [], "chiller_2": [], "chiller_3": []}

    for t, device, v in rows:
        datasets.setdefault(device, []).append({"ts": str(t), "value": fmt(v, 3)})

    return {
        "range": range,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "metric": metric,
        "datasets": datasets,
    }
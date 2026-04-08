from fastapi import APIRouter, Query
import core.db as db
from core.helpers import (
    parse_range,
    fmt,
    fetch_latest_points,
    fetch_energy_delta_by_devices,
    sum_energy_delta,
)

router = APIRouter(prefix="/api/air", tags=["air"])


@router.get("/summary")
def air_summary(range_key: str = Query(default="24h", alias="range")):
    start, end, _ = parse_range(range_key)
    cur = db.db_conn.cursor()

    ahu_devices = ["ahu_1", "ahu_2", "ahu_3", "ahu_4"]
    ahu_meter_devices = ["ahu_meter_1", "ahu_meter_2", "ahu_meter_3", "ahu_meter_4"]

    ahus, latest_ts = fetch_latest_points(cur, ahu_devices, start, end)
    if not ahus:
        ahus, latest_ts = fetch_latest_points(cur, ahu_devices)

    cur.execute(
        """
        SELECT floor, SUM(value) AS air_flow
        FROM (
            SELECT DISTINCT ON (device)
                device, floor, value, ts
            FROM telemetry
            WHERE device LIKE 'vav_%%'
              AND point = 'air_flow_rate'
              AND floor IS NOT NULL
              AND ts >= %s AND ts <= %s
            ORDER BY device, ts DESC
        ) t
        GROUP BY floor
        ORDER BY floor
        """,
        (start, end),
    )
    airflow_by_floor = {row[0]: row[1] for row in cur.fetchall()}

    if not airflow_by_floor:
        cur.execute(
            """
            SELECT floor, SUM(value) AS air_flow
            FROM (
                SELECT DISTINCT ON (device)
                    device, floor, value, ts
                FROM telemetry
                WHERE device LIKE 'vav_%%'
                  AND point = 'air_flow_rate'
                  AND floor IS NOT NULL
                ORDER BY device, ts DESC
            ) t
            GROUP BY floor
            ORDER BY floor
            """
        )
        airflow_by_floor = {row[0]: row[1] for row in cur.fetchall()}

    total_air_power = 0.0
    total_air_flow = 0.0
    power_found = False
    flow_found = False

    for i, device in enumerate(ahu_devices, start=1):
        ahu = ahus.setdefault(device, {})
        floor = ahu.get("floor", i)

        power = ahu.get("power")
        run_status = ahu.get("status_read")
        supply_temp = ahu.get("setpoint")
        return_temp = ahu.get("room_temperature")
        air_flow = airflow_by_floor.get(floor)

        delta_t = None
        if return_temp is not None and supply_temp is not None:
            delta_t = max(float(return_temp) - float(supply_temp), 0)

        efficiency = None
        if power is not None and air_flow not in (None, 0):
            efficiency = float(power) / float(air_flow)

        ahu["run_status"] = run_status
        ahu["supply_temp"] = supply_temp
        ahu["return_temp"] = return_temp
        ahu["delta_t"] = delta_t
        ahu["air_flow"] = air_flow
        ahu["efficiency"] = efficiency

        if power is not None:
            total_air_power += float(power)
            power_found = True

        if air_flow is not None:
            total_air_flow += float(air_flow)
            flow_found = True

    total_air_power = fmt(total_air_power, 2) if power_found else None
    total_air_flow = fmt(total_air_flow, 2) if flow_found else None

    avg_air_efficiency = None
    if total_air_power is not None and total_air_flow not in (None, 0):
        avg_air_efficiency = fmt(float(total_air_power) / float(total_air_flow), 4)

    ahu_energy_by_meter = fetch_energy_delta_by_devices(cur, ahu_meter_devices, start, end)
    for meter in ahu_meter_devices:
        ahu_energy_by_meter.setdefault(
            meter,
            {
                "first_value": None,
                "last_value": None,
                "energy_delta": None,
            },
        )

    total_air_energy = sum_energy_delta(ahu_energy_by_meter)

    cur.execute(
        """
        SELECT
            floor,
            AVG(CASE WHEN point = 'temperature' THEN value END) AS avg_temp,
            AVG(CASE WHEN point = 'humidity' THEN value END) AS avg_humidity
        FROM telemetry
        WHERE device LIKE 'iaq_%%'
          AND floor IS NOT NULL
          AND ts >= %s AND ts <= %s
        GROUP BY floor
        ORDER BY floor
        """,
        (start, end),
    )
    iaq_rows = cur.fetchall()

    iaq_map = {
        row[0]: {
            "avg_temp": fmt(row[1], 1),
            "avg_humidity": fmt(row[2], 1),
        }
        for row in iaq_rows
    }

    if not iaq_map:
        cur.execute(
            """
            SELECT
                floor,
                AVG(CASE WHEN point = 'temperature' THEN value END) AS avg_temp,
                AVG(CASE WHEN point = 'humidity' THEN value END) AS avg_humidity
            FROM telemetry
            WHERE device LIKE 'iaq_%%'
              AND floor IS NOT NULL
            GROUP BY floor
            ORDER BY floor
            """
        )
        iaq_map = {
            row[0]: {
                "avg_temp": fmt(row[1], 1),
                "avg_humidity": fmt(row[2], 1),
            }
            for row in cur.fetchall()
        }

    zone_averages = []
    for floor in range(1, 5):
        ahu_device = f"ahu_{floor}"
        ahu_data = ahus.get(ahu_device, {})

        zone_averages.append(
            {
                "floor": floor,
                "avg_temp": iaq_map.get(floor, {}).get("avg_temp"),
                "avg_humidity": iaq_map.get(floor, {}).get("avg_humidity"),
                "ahu_on_count": 1 if ahu_data.get("status_read") == 1 else 0,
                "ahu_alarm_count": 1 if ahu_data.get("alarm") == 1 else 0,
            }
        )

    cur.close()

    return {
        "range": range_key,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "latest_ts": str(latest_ts) if latest_ts else None,
        "total_air_power": total_air_power,
        "total_air_flow": total_air_flow,
        "avg_air_efficiency": avg_air_efficiency,
        "total_air_energy": total_air_energy,
        "ahus": ahus,
        "ahu_energy_by_meter": ahu_energy_by_meter,
        "zone_averages": zone_averages,
    }


@router.get("/trend")
def air_trend(
    range_key: str = Query(default="24h", alias="range"),
    metric: str = Query(default="power"),
):
    allowed_metrics = {"power", "air_flow", "efficiency"}
    if metric not in allowed_metrics:
        return {
            "metric": metric,
            "datasets": {},
            "error": f"Unsupported metric. Allowed: {', '.join(sorted(allowed_metrics))}",
        }

    start, end, trunc = parse_range(range_key)
    cur = db.db_conn.cursor()

    datasets = {"ahu_1": [], "ahu_2": [], "ahu_3": [], "ahu_4": []}

    if metric == "power":
        cur.execute(
            f"""
            SELECT
                date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
                device,
                AVG(value) AS avg_value
            FROM telemetry
            WHERE device IN ('ahu_1', 'ahu_2', 'ahu_3', 'ahu_4')
              AND point = 'power'
              AND ts >= %s AND ts <= %s
            GROUP BY bucket_ts, device
            ORDER BY bucket_ts ASC, device ASC
            """,
            (start, end),
        )

        for bucket_ts, device, avg_value in cur.fetchall():
            datasets[device].append(
                {
                    "ts": str(bucket_ts),
                    "value": fmt(avg_value, 3) if avg_value is not None else None,
                }
            )

    elif metric == "air_flow":
        cur.execute(
            f"""
            WITH vav_bucketed AS (
                SELECT
                    date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
                    device,
                    floor,
                    value,
                    ts,
                    ROW_NUMBER() OVER (
                        PARTITION BY date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok'), device
                        ORDER BY ts DESC
                    ) AS rn
                FROM telemetry
                WHERE device LIKE 'vav_%%'
                  AND point = 'air_flow_rate'
                  AND floor IS NOT NULL
                  AND ts >= %s AND ts <= %s
            )
            SELECT
                bucket_ts,
                floor,
                SUM(value) AS sum_air_flow
            FROM vav_bucketed
            WHERE rn = 1
            GROUP BY bucket_ts, floor
            ORDER BY bucket_ts ASC, floor ASC
            """,
            (start, end),
        )

        for bucket_ts, floor, sum_air_flow in cur.fetchall():
            device = f"ahu_{floor}"
            if device in datasets:
                datasets[device].append(
                    {
                        "ts": str(bucket_ts),
                        "value": fmt(sum_air_flow, 3) if sum_air_flow is not None else None,
                    }
                )

    elif metric == "efficiency":
        cur.execute(
            f"""
            WITH ahu_power AS (
                SELECT
                    date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
                    CAST(SPLIT_PART(device, '_', 2) AS INTEGER) AS floor,
                    device,
                    AVG(value) AS avg_power
                FROM telemetry
                WHERE device IN ('ahu_1', 'ahu_2', 'ahu_3', 'ahu_4')
                  AND point = 'power'
                  AND ts >= %s AND ts <= %s
                GROUP BY bucket_ts, floor, device
            ),
            vav_bucketed AS (
                SELECT
                    date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
                    device,
                    floor,
                    value,
                    ts,
                    ROW_NUMBER() OVER (
                        PARTITION BY date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok'), device
                        ORDER BY ts DESC
                    ) AS rn
                FROM telemetry
                WHERE device LIKE 'vav_%%'
                  AND point = 'air_flow_rate'
                  AND floor IS NOT NULL
                  AND ts >= %s AND ts <= %s
            ),
            vav_flow AS (
                SELECT
                    bucket_ts,
                    floor,
                    SUM(value) AS sum_air_flow
                FROM vav_bucketed
                WHERE rn = 1
                GROUP BY bucket_ts, floor
            )
            SELECT
                p.bucket_ts,
                p.device,
                CASE
                    WHEN v.sum_air_flow IS NULL OR v.sum_air_flow = 0 THEN NULL
                    ELSE p.avg_power / v.sum_air_flow
                END AS efficiency_value
            FROM ahu_power p
            LEFT JOIN vav_flow v
              ON p.bucket_ts = v.bucket_ts
             AND p.floor = v.floor
            ORDER BY p.bucket_ts ASC, p.device ASC
            """,
            (start, end, start, end),
        )

        for bucket_ts, device, efficiency_value in cur.fetchall():
            datasets[device].append(
                {
                    "ts": str(bucket_ts),
                    "value": fmt(efficiency_value, 4) if efficiency_value is not None else None,
                }
            )

    cur.close()

    return {
        "range": range_key,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "metric": metric,
        "datasets": datasets,
    }


@router.get("/zone_trend")
def zone_trend(
    range_key: str = Query(default="24h", alias="range"),
):
    start, end, trunc = parse_range(range_key)
    cur = db.db_conn.cursor()

    datasets = {
        "floor_1_temp": [],
        "floor_2_temp": [],
        "floor_3_temp": [],
        "floor_4_temp": [],
        "floor_1_humidity": [],
        "floor_2_humidity": [],
        "floor_3_humidity": [],
        "floor_4_humidity": [],
    }

    cur.execute(
        f"""
        SELECT
            date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
            floor,
            AVG(CASE WHEN point = 'temperature' THEN value END) AS avg_temp,
            AVG(CASE WHEN point = 'humidity' THEN value END) AS avg_humidity
        FROM telemetry
        WHERE device LIKE 'iaq_%%'
          AND floor IS NOT NULL
          AND ts >= %s AND ts <= %s
        GROUP BY bucket_ts, floor
        ORDER BY bucket_ts ASC, floor ASC
        """,
        (start, end),
    )

    rows = cur.fetchall()

    if not rows:
        cur.execute(
            f"""
            SELECT
                date_trunc('{trunc}', ts AT TIME ZONE 'Asia/Bangkok') AS bucket_ts,
                floor,
                AVG(CASE WHEN point = 'temperature' THEN value END) AS avg_temp,
                AVG(CASE WHEN point = 'humidity' THEN value END) AS avg_humidity
            FROM telemetry
            WHERE device LIKE 'iaq_%%'
              AND floor IS NOT NULL
            GROUP BY bucket_ts, floor
            ORDER BY bucket_ts ASC, floor ASC
            """
        )
        rows = cur.fetchall()

    for bucket_ts, floor, temp, humidity in rows:
        if floor in [1, 2, 3, 4]:
            datasets[f"floor_{floor}_temp"].append({
                "ts": str(bucket_ts),
                "value": fmt(temp, 2) if temp is not None else None
            })
            datasets[f"floor_{floor}_humidity"].append({
                "ts": str(bucket_ts),
                "value": fmt(humidity, 2) if humidity is not None else None
            })

    cur.close()

    return {
        "range": range_key,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "datasets": datasets,
    }
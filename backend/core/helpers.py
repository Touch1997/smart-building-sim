from datetime import datetime, timedelta, timezone


def parse_range(range_value: str):
    now = datetime.now(timezone.utc)

    if range_value == "1h":
        return now - timedelta(hours=1), now, "minute"
    elif range_value == "24h":
        return now - timedelta(hours=24), now, "hour"
    elif range_value == "7d":
        return now - timedelta(days=7), now, "day"
    elif range_value == "30d":
        return now - timedelta(days=30), now, "day"
    elif range_value == "365d":
        return now - timedelta(days=365), now, "month"
    else:
        return now - timedelta(hours=24), now, "hour"


def fmt(v, d=2):
    if v is None:
        return None
    try:
        return round(float(v), d)
    except Exception:
        return None


def safe_delta(last_value, first_value, clamp_zero=True):
    if last_value is None or first_value is None:
        return None

    try:
        delta = float(last_value) - float(first_value)
    except Exception:
        return None

    if clamp_zero and delta < 0:
        return 0.0

    return delta


def fetch_latest_points(cur, devices, start=None, end=None):
    if not devices:
        return {}, None

    placeholders = ",".join(["%s"] * len(devices))
    params = list(devices)

    sql = f"""
        SELECT device, point, value, ts, floor
        FROM (
            SELECT DISTINCT ON (device, point)
                device, point, value, ts, floor
            FROM telemetry
            WHERE device IN ({placeholders})
    """

    if start is not None and end is not None:
        sql += " AND ts >= %s AND ts <= %s"
        params.extend([start, end])

    sql += """
            ORDER BY device, point, ts DESC
        ) t
        ORDER BY device, point
    """

    cur.execute(sql, params)
    rows = cur.fetchall()

    result = {}
    latest_ts = None

    for device, point, value, ts, floor in rows:
        result.setdefault(device, {})[point] = value
        if floor is not None:
            result[device]["floor"] = floor
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts

    return result, latest_ts


def fetch_energy_delta_by_devices(cur, devices, start, end):
    if not devices:
        return {}

    placeholders = ",".join(["%s"] * len(devices))
    params = list(devices) + [start, end]

    cur.execute(
        f"""
        WITH meter_range AS (
            SELECT device, ts, value
            FROM telemetry
            WHERE device IN ({placeholders})
              AND point = 'energy'
              AND ts >= %s AND ts <= %s
        ),
        first_points AS (
            SELECT DISTINCT ON (device) device, value AS first_value
            FROM meter_range
            ORDER BY device, ts ASC
        ),
        last_points AS (
            SELECT DISTINCT ON (device) device, value AS last_value
            FROM meter_range
            ORDER BY device, ts DESC
        )
        SELECT
            f.device,
            f.first_value,
            l.last_value,
            GREATEST(l.last_value - f.first_value, 0) AS energy_delta
        FROM first_points f
        JOIN last_points l ON f.device = l.device
        ORDER BY f.device
        """,
        params,
    )

    result = {}
    for device, first_value, last_value, energy_delta in cur.fetchall():
        result[device] = {
            "first_value": fmt(first_value, 2),
            "last_value": fmt(last_value, 2),
            "energy_delta": fmt(energy_delta, 2),
        }
    return result


def sum_energy_delta(energy_map):
    total = 0.0
    found = False
    for _, payload in energy_map.items():
        delta = payload.get("energy_delta")
        if delta is not None:
            total += float(delta)
            found = True
    return fmt(total, 2) if found else None
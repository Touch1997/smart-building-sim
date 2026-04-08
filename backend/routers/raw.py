from fastapi import APIRouter, Query
import core.db as db

router = APIRouter(prefix="/api", tags=["raw"])


@router.get("/telemetry")
def api_telemetry():
    cur = db.db_conn.cursor()
    cur.execute(
        """
        SELECT ts, topic, device, point, value, group_name, floor, equipment_index
        FROM telemetry
        ORDER BY ts DESC
        LIMIT 20
        """
    )
    rows = cur.fetchall()
    cur.close()

    return [
        {
            "ts": str(r[0]),
            "topic": r[1],
            "device": r[2],
            "point": r[3],
            "value": r[4],
            "group_name": r[5],
            "floor": r[6],
            "equipment_index": r[7],
        }
        for r in rows
    ]


@router.get("/latest")
def api_latest(device: str | None = Query(default=None), point: str | None = Query(default=None)):
    cur = db.db_conn.cursor()

    sql = """
        SELECT DISTINCT ON (device, point)
            ts, topic, device, point, value, group_name, floor, equipment_index
        FROM telemetry
    """
    params = []
    conds = []

    if device:
        conds.append("device = %s")
        params.append(device)

    if point:
        conds.append("point = %s")
        params.append(point)

    if conds:
        sql += " WHERE " + " AND ".join(conds)

    sql += " ORDER BY device, point, ts DESC"

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()

    return [
        {
            "ts": str(r[0]),
            "topic": r[1],
            "device": r[2],
            "point": r[3],
            "value": r[4],
            "group_name": r[5],
            "floor": r[6],
            "equipment_index": r[7],
        }
        for r in rows
    ]


@router.get("/history")
def api_history(device: str = Query(...), point: str = Query(...), limit: int = Query(default=100)):
    cur = db.db_conn.cursor()
    cur.execute(
        """
        SELECT ts, value
        FROM telemetry
        WHERE device = %s AND point = %s
        ORDER BY ts DESC
        LIMIT %s
        """,
        (device, point, limit),
    )
    rows = cur.fetchall()
    cur.close()

    return [{"ts": str(r[0]), "value": r[1]} for r in reversed(rows)]
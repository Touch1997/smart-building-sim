"""
Smart Building IoT Backend — AltoTech Assessment
FastAPI + MQTT Subscriber + PostgreSQL
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import paho.mqtt.client as mqtt
import json

import core.db as db
from core.db import connect_db

from routers.pages import router as pages_router
from routers.raw import router as raw_router
from routers.main_dashboard import router as main_dashboard_router
from routers.chiller import router as chiller_router
from routers.air import router as air_router
from routers.electrical import router as electrical_router


# ─────────────────────────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────────────────────────

app = FastAPI(title="Smart Building IoT Backend")


# ─────────────────────────────────────────────────────────────
# ROUTER REGISTRATION
# ─────────────────────────────────────────────────────────────
# Web pages
app.include_router(pages_router)

# Raw / utility APIs
app.include_router(raw_router)

# Dashboard APIs
app.include_router(main_dashboard_router)
app.include_router(chiller_router)
app.include_router(air_router)
app.include_router(electrical_router)


# ─────────────────────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


# ─────────────────────────────────────────────────────────────
# MQTT CALLBACKS
# ─────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT, rc =", rc, flush=True)
    client.subscribe("building/#")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())

        cur = db.db_conn.cursor()
        cur.execute(
            """
            INSERT INTO telemetry (
                ts, topic, device, point, value,
                group_name, floor, equipment_index, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payload.get("timestamp"),
                msg.topic,
                payload.get("device"),
                payload.get("point"),
                payload.get("value"),
                payload.get("group"),
                payload.get("floor"),
                payload.get("equipment_index"),
                json.dumps(payload),
            ),
        )
        cur.close()

    except Exception as e:
        print("Insert error:", e, flush=True)


# ─────────────────────────────────────────────────────────────
# STARTUP SERVICES
# ─────────────────────────────────────────────────────────────

connect_db()

_mc = mqtt.Client()
_mc.on_connect = on_connect
_mc.on_message = on_message

try:
    _mc.connect("mqtt", 1883, 60)
    _mc.loop_start()
    print("MQTT started", flush=True)
except Exception as e:
    print("MQTT error:", e, flush=True)
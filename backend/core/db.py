import time
import psycopg2

db_conn = None


def connect_db():
    global db_conn

    while True:
        try:
            db_conn = psycopg2.connect(
                host="postgres",
                database="iot",
                user="iot",
                password="iot",
            )
            db_conn.autocommit = True
            print("Connected to PostgreSQL", flush=True)

            cur = db_conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry (
                    id BIGSERIAL PRIMARY KEY,
                    ts TIMESTAMPTZ NOT NULL,
                    topic TEXT NOT NULL,
                    device TEXT NOT NULL,
                    point TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    group_name TEXT,
                    floor INTEGER,
                    equipment_index INTEGER,
                    raw_payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_ts
                ON telemetry (ts DESC)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_device_point_ts
                ON telemetry (device, point, ts DESC)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_topic_ts
                ON telemetry (topic, ts DESC)
                """
            )

            cur.close()
            print("telemetry table ready", flush=True)
            break

        except Exception as e:
            print("PostgreSQL connection error:", e, flush=True)
            time.sleep(3)
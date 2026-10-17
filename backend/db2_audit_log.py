"""
Sentinel-Z: Db2 Audit Log — Persistent Transaction Ledger.
Simulates IBM Db2 for z/OS row-level audit logging using SQLite.
On a real LinuxONE deployment, replace the SQLite connection with
IBM Db2 JDBC via ibm_db or ibm_db_sa connector.

Integration note:
    Production path: CICS/z/OS Connect → Python scoring → Db2 COMMIT via ibm_db
    Simulation path: FastAPI → Python scoring → SQLite COMMIT (this file)
"""

import sqlite3
import threading
import time
import os
from pathlib import Path
from typing import List, Dict, Any

# Audit DB lives in the project data directory — persists across restarts
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sentinel_audit.db"


class Db2AuditLog:
    """
    Thread-safe persistent audit log that records every scored EHR transaction.
    Mirrors the behaviour of Db2 for z/OS row-level audit tables (RACF / AUDIT policy).

    Schema mirrors what a real Db2 z/OS audit table would look like:
        SENTINEL_AUDIT (
            txn_id        BIGINT     NOT NULL GENERATED ALWAYS AS IDENTITY,
            ts            TIMESTAMP  NOT NULL,
            patient_id    VARCHAR(32),
            risk_score    DECIMAL(5,2),
            action        VARCHAR(40),
            inference_ms  DECIMAL(8,3),
            guardrail     VARCHAR(30),
            alert_status  VARCHAR(20),
            cb_state      VARCHAR(10),
            platform      VARCHAR(20)
        )
    """

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection (mimics Db2 connection pool)."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        """Initialises the SENTINEL_AUDIT table if it doesn't exist."""
        with self._lock:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS SENTINEL_AUDIT (
                    txn_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts           TEXT    NOT NULL,
                    patient_id   TEXT    NOT NULL,
                    risk_score   REAL    NOT NULL,
                    action       TEXT    NOT NULL,
                    inference_ms REAL    NOT NULL,
                    guardrail    TEXT    DEFAULT 'PASSED_VERIFIED',
                    alert_status TEXT    DEFAULT 'CONTROLLED',
                    cb_state     TEXT    DEFAULT 'CLOSED',
                    platform     TEXT    DEFAULT 'unknown'
                )
            """)
            conn.commit()

    def commit_transaction(
        self,
        patient_id: str,
        risk_score: float,
        action: str,
        inference_ms: float,
        guardrail: str = "PASSED_VERIFIED",
        alert_status: str = "CONTROLLED",
        cb_state: str = "CLOSED",
        platform: str = "unknown"
    ) -> int:
        """
        Writes one scored transaction row to the audit table (simulates Db2 COMMIT).
        Returns the auto-generated transaction ID.
        """
        import platform as plt
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        arch = plt.machine()

        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                """
                INSERT INTO SENTINEL_AUDIT
                    (ts, patient_id, risk_score, action, inference_ms,
                     guardrail, alert_status, cb_state, platform)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, patient_id, round(risk_score, 2), action,
                 round(inference_ms, 3), guardrail, alert_status, cb_state, arch)
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent N audit rows, newest first."""
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM SENTINEL_AUDIT ORDER BY txn_id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_summary(self) -> Dict[str, Any]:
        """Returns aggregate statistics for the dashboard."""
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("""
                SELECT
                    COUNT(*)                                        AS total_commits,
                    SUM(CASE WHEN action LIKE '%INTERCEPT%' THEN 1 ELSE 0 END) AS total_intercepts,
                    SUM(CASE WHEN action LIKE '%COMMITTED%' THEN 1 ELSE 0 END) AS total_commits_ehr,
                    AVG(inference_ms)                               AS avg_inference_ms,
                    AVG(risk_score)                                 AS avg_risk_score,
                    MIN(ts)                                         AS first_commit,
                    MAX(ts)                                         AS last_commit
                FROM SENTINEL_AUDIT
            """).fetchone()
            return dict(row) if row else {}

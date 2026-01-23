#!/usr/bin/env python

import sqlite3

class Database(object):
    def __init__(self, filename):
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()
        
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                src_ip TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                details TEXT
            )
            """
        )
        self.conn.commit()
    def add_alert(self, ts, src_ip, alert_type, details):
        self.cursor.execute(
            """
            INSERT INTO alerts (ts, src_ip, alert_type, details)
            VALUES (?, ?, ?, ?)
            """,
            (ts, src_ip, alert_type, details)
        )
        self.conn.commit()


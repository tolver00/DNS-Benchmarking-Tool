import json
import csv
import sqlite3
import os
from datetime import datetime


def write_json(report, elapsed, config, path):
    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "server": config["server"],
            "port": config["port"],
            "protocol": config["protocol"],
            "workers": config["workers"],
            "mode": config["exec_mode"],
            "rdatatypes": config["rdatatypes"],
        },
        "summary": {
            "total_queries": report["total_queries"],
            "successful": report["successful"],
            "errors": report["errors"],
            "error_rate": report["error_rate"],
            "duration": elapsed,
            "qps": report["total_queries"],
            
        },
        "latency": report.get("latency", {}),
        "rcodes": report.get("rcodes", {}),
        "per_type": report.get("per_type", {}),
        }
    with open(path, "w") as f:
        json.dump(output, f, indent=2)


def write_csv(report, elapsed, config, path):
    qps = report["total_queries"] / elapsed if elapsed > 0 else 0
    lat = report.get("latency", {})
    row = {
        "timestamp": datetime.now().isoformat(),
        "server": config["server"],
        "port": config["port"],
        "protocol": config["protocol"],
        "workers": config["workers"],
        "mode": config["exec_mode"],
        "total_queries": report["total_queries"],
        "successful": report["successful"],
        "errors": report["errors"],
        "error_rate": report["error_rate"],
        "duration": round(elapsed, 3),
        "qps": round(qps, 1),
        "latency_min": round(lat.get("min", 0) * 1000, 3),
        "latnecy_max": round(lat.get("max, 0")* 1000, 3),
        "latency_mean": round(lat.get("mean", 0) * 1000, 3),
        "latency_median": round(lat.get("median", 0) * 1000, 3),
        "latency_p95": round(lat.get("p95", 0) * 1000, 3),
        "latency_p99": round(lat.get("P99", 0) * 1000, 3),
    }

    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def write_sqlite(report, elapsed, config, rdtype_names, results, path):
    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    server TEXT,
    port INTEGER,
    protocol TEXT,
    workers INTEGER,
    mode TEXT,
    total_queries INTEGER,
    successful INTEGER,
    errors INTEGER,
    error_rate REAL,
    duration REAL,
    qps REAL,
    latency_min REAL,
    latency_max REAL,
    latency_mean REAL,
    latency_median REAL,
    latency_p95 REAL,
    latency_p99 REAL
    )

    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS query_results(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    latency REAL,
    rcode INTEGER,
    record_type TEXT,
    error TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(id)
    )
    """)
    lat = report.get("latency", {})
    qps = report["total_queries"] / elapsed if elapsed > 0 else 0

    c.execute("""
    INSERT INTO runs (timestamp, server, port, protocol, workers, mode, total_queries, successful, errors, error_rate, duration, qps, latency_min, latency_max, latency_mean, latency_median, latency_p95, latency_p99)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        config["server"],
        config["port"],
        config["protocol"],
        config["workers"],
        config["exec_mode"],
        report["total_queries"],
        report["successful"],
        report["errors"],
        report["error_rate"],
        round(elapsed, 3), round(qps, 1),
        lat.get("min"),
        lat.get("max"),
        lat.get("mean"),
        lat.get("median"),
        lat.get("p95"),
        lat.get("p99"),
    ))

    run_id = c.lastrowid
    rows = []
    for r in results:
        if "msg_index" in results:
            index = r.get("msg_index", 0)
            rdtype = rdtype_names[index]
        else:
            rdtype = None
        rows.append((
            run_id,
            r.get("latency"),
            r.get("rcode"),
            rdtype,
            r.get("error"),
        ))
    c.executemany("INSERT INTO query_results (run_id, latency, rcode, record_type, error) VALUES (?, ?, ?, ?, ?)", rows)

    conn.commit()
    conn.close()
    
    

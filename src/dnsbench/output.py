import json
import csv
import sqlite3
import os
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
        "latency_max": round(lat.get("max", 0) * 1000, 3),
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
    
    
def write_html(report, elapsed, config, results, rdtype_names, path):
    if elapsed > 0:
        qps = report["total_queries"] / elapsed
    else:
        qps = 0

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Latency Distribution",
            "Latency Percent",
            "Per Record Type",
            "RCODE Distribution",
        ),
        specs=[
            [{"type": "histogram"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "pie"}],
            
        ]
    )

    latencies = []
    for r in results:
        if "latency" in r:
            latencies.append(r["latency"] * 1000)

    fig.add_trace(
        go.Histogram(x=latencies, nbinsx=50, name="Latency",
                     marker_color="#636EFA"),
        row=1, col=1
    )


    if "latency" in report:
        lat = report["latency"]
        labels = ["Min", "Median", "Mean", "P95", "P99", "Max"]
        values = [
            lat["min"] *1000,
            lat["median"] *1000,
            lat ["mean"] * 1000,
            lat["p95"] * 1000,
            lat["p99"] * 1000,
            lat["max"] * 1000,
        ]
        fig.add_trace(
            go.Bar(x=labels, y=values, name="Percent",
                   marker_color="#EF553B"),
            row=1, col=2
        )

        
    if "per_type" in report:
        types = list(report["per_type"].keys())
        means = []
        p95s = []
        for t in types:
            means.append(report["per_type"][t]["mean"] * 1000)
            p95s.append(report["per_type"][t]["p95"] * 1000)


        fig.add_trace(
            go.Bar(x=types, y=means, name="Mean", marker_color="#636EFA"),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(x=types, y=p95s, name="P95", marker_color="#636EFA"),
            row=2, col=1
        )

    rcode_map = {0: "NOERROR", 2: "SERVFAIL", 3: "NXDOMAIN", 5: "REFUSED"}
    rcode_labels = []
    rcode_values = []
    for code, count in report["rcodes"].items():
        name = rcode_map.get(int(code), f"RCODE_{code}")
        rcode_labels.append(name)
        rcode_values.append(count)

    fig.add_trace(
        go.Pie(labels=rcode_labels, values=rcode_values, name="RCODE"),
        row=2, col=2
    )

    # layout
    fig.update_layout(
        title_text=(
            f"DNS Benchmark Report - {config['server']}: {config['port']} - "
            f"({config['protocol'].upper()}) - "
            f"{report['total_queries']} queries: {qps:.0f})"
        ),
        showlegend=True,
        height=800,
        template="plotly_dark",
    )


    fig.update_xaxes(title_text="Latency (ms)", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_xaxes(title_text="Percent", row=1, col=2)
    fig.update_yaxes(title_text="Latency (ms)", row=1, col=2)
    fig.update_xaxes(title_text="Record Type", row=2, col=1)
    fig.update_yaxes(title_text="Latency (ms)", row=2, col=1)

    fig.write_html(path)

        

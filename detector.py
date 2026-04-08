import re
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import json

LOG_FILE    = "logs/app.log"
OUTPUT_FILE = "logs/anomalies.json"
WINDOW      = "1min"   # size of each time window

# ── Step 1: Parse log file ─────────────────────────────────────────────────────
def parse_logs(filepath):
    """
    Read app.log and extract structured fields from each line.
    Returns a DataFrame with one row per log entry.
    """
    pattern = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\s+"
        r"(?P<level>\w+)\s+"
        r"method=(?P<method>\w+)\s+"
        r"endpoint=(?P<endpoint>\S+)\s+"
        r"status=(?P<status>\d+)\s+"
        r"latency_ms=(?P<latency>[\d.]+)"
    )
    records = []
    with open(filepath, "r") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                records.append({
                    "timestamp":  match.group("timestamp"),
                    "level":      match.group("level"),
                    "method":     match.group("method"),
                    "endpoint":   match.group("endpoint"),
                    "status":     int(match.group("status")),
                    "latency_ms": float(match.group("latency")),
                    "is_error":   1 if int(match.group("status")) >= 500 else 0,
                })
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S,%f")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ── Step 2: Build time windows ─────────────────────────────────────────────────
def build_windows(df):
    """
    Group log entries into 1-minute time windows.
    For each window compute:
      - error_rate     : % of requests that returned 5xx
      - avg_latency    : average response time in ms
      - p95_latency    : 95th percentile response time
      - request_count  : total number of requests
      - error_count    : total number of errors

    Why windows instead of individual lines?
    A single slow request might be noise.
    A whole minute of slow requests is a real incident.
    """
    df = df.set_index("timestamp")
    windows = df.resample(WINDOW).agg(
        error_rate    = ("is_error",   "mean"),
        avg_latency   = ("latency_ms", "mean"),
        p95_latency   = ("latency_ms", lambda x: x.quantile(0.95)),
        request_count = ("status",     "count"),
        error_count   = ("is_error",   "sum"),
    ).dropna()

    # only keep windows with at least 3 requests
    windows = windows[windows["request_count"] >= 3]
    return windows


# ── Step 3: Run Isolation Forest on windows ────────────────────────────────────
def detect_anomalies(windows):
    """
    Run Isolation Forest on time-window features.
    StandardScaler normalizes features so latency does not
    dominate over error_rate.
    """
    features = ["error_rate", "avg_latency", "p95_latency", "request_count"]
    X = windows[features].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42
    )
    windows = windows.copy()
    windows["anomaly"]       = model.fit_predict(X_scaled)
    windows["anomaly_score"] = model.decision_function(X_scaled)
    return windows


# ── Step 4: Print results ──────────────────────────────────────────────────────
def print_results(windows):
    anomalies = windows[windows["anomaly"] == -1]
    normal    = windows[windows["anomaly"] == 1]

    print("\n" + "="*65)
    print("        TIME-WINDOW ANOMALY DETECTION RESULTS")
    print("="*65)
    print(f"Window size              : {WINDOW}")
    print(f"Total windows analyzed   : {len(windows)}")
    print(f"Normal windows           : {len(normal)}")
    print(f"Anomalous windows        : {len(anomalies)}")
    print("="*65)

    if anomalies.empty:
        print("\nNo anomalies detected. System looks healthy.")
    else:
        print(f"\n{len(anomalies)} ANOMALOUS time windows detected:\n")
        for ts, row in anomalies.iterrows():
            print(f"  [{ts}]")
            print(f"   error_rate={row['error_rate']*100:.1f}% | "
                  f"avg_latency={row['avg_latency']:.0f}ms | "
                  f"p95_latency={row['p95_latency']:.0f}ms | "
                  f"requests={int(row['request_count'])} | "
                  f"errors={int(row['error_count'])} | "
                  f"score={row['anomaly_score']:.4f}")
            print()

    export = []
    for ts, row in anomalies.iterrows():
        export.append({
            "timestamp":     str(ts),
            "error_rate":    round(row["error_rate"] * 100, 2),
            "avg_latency":   round(row["avg_latency"], 2),
            "p95_latency":   round(row["p95_latency"], 2),
            "request_count": int(row["request_count"]),
            "error_count":   int(row["error_count"]),
            "anomaly_score": round(row["anomaly_score"], 4),
        })

    with open(OUTPUT_FILE, "w") as f:
        json.dump(export, f, indent=2)

    print(f"Anomalous windows saved to {OUTPUT_FILE}")
    print("="*65)


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Reading logs...")
    df = parse_logs(LOG_FILE)

    if df.empty:
        print("No log entries found. Run the Flask app first: python3 app.py")
        exit(1)

    print(f"Parsed {len(df)} log entries")
    print(f"Building {WINDOW} time windows...")
    windows = build_windows(df)
    print(f"Created {len(windows)} time windows")

    print("Running Isolation Forest on time windows...")
    windows = detect_anomalies(windows)

    print_results(windows)

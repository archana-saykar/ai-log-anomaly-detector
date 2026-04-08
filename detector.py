import re
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import json

LOG_FILE    = "logs/app.log"
OUTPUT_FILE = "logs/anomalies.json"
WINDOW      = "1min"


# ── Step 1: Parse log file ─────────────────────────────────────────────────────
def parse_logs(filepath):
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
                    "endpoint":   match.group("endpoint"),
                    "status":     int(match.group("status")),
                    "latency_ms": float(match.group("latency")),
                    "is_error":   1 if int(match.group("status")) >= 500 else 0,
                })
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S,%f")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ── Step 2: Build overall time windows ────────────────────────────────────────
def build_windows(df):
    """
    Overall metrics per 1-minute window across all endpoints.
    Used as features for Isolation Forest.
    """
    df_indexed = df.set_index("timestamp")
    windows = df_indexed.resample(WINDOW).agg(
        error_rate    = ("is_error",   "mean"),
        avg_latency   = ("latency_ms", "mean"),
        p95_latency   = ("latency_ms", lambda x: x.quantile(0.95)),
        request_count = ("status",     "count"),
        error_count   = ("is_error",   "sum"),
    ).dropna()
    windows = windows[windows["request_count"] >= 3]
    return windows


# ── Step 3: Build per-endpoint breakdown per window ───────────────────────────
def build_endpoint_breakdown(df):
    """
    For each 1-minute window, show metrics broken down by endpoint.
    This tells us WHICH endpoint is causing the problem — not just that
    something is wrong overall.

    Example output:
    {
      "2026-04-08 17:29:00": {
        "/api/payments": {"error_rate": 45.0, "avg_latency": 6200, "requests": 120},
        "/api/users":    {"error_rate": 2.0,  "avg_latency": 280,  "requests": 340}
      }
    }
    """
    df_indexed = df.set_index("timestamp")
    breakdown = {}

    for endpoint, group in df_indexed.groupby("endpoint"):
        resampled = group.resample(WINDOW).agg(
            error_rate    = ("is_error",   "mean"),
            avg_latency   = ("latency_ms", "mean"),
            p95_latency   = ("latency_ms", lambda x: x.quantile(0.95)),
            request_count = ("status",     "count"),
            error_count   = ("is_error",   "sum"),
        ).dropna()
        resampled = resampled[resampled["request_count"] >= 2]

        for ts, row in resampled.iterrows():
            ts_str = str(ts)
            if ts_str not in breakdown:
                breakdown[ts_str] = {}
            breakdown[ts_str][endpoint] = {
                "error_rate":    round(row["error_rate"] * 100, 2),
                "avg_latency":   round(row["avg_latency"], 2),
                "p95_latency":   round(row["p95_latency"], 2),
                "request_count": int(row["request_count"]),
                "error_count":   int(row["error_count"]),
            }

    return breakdown


# ── Step 4: Run Isolation Forest ──────────────────────────────────────────────
def detect_anomalies(windows):
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


# ── Step 5: Print and export results ──────────────────────────────────────────
def print_results(windows, breakdown):
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
        return

    print(f"\n{len(anomalies)} ANOMALOUS time windows detected:\n")

    export = []
    for ts, row in anomalies.iterrows():
        ts_str = str(ts)

        # overall window metrics
        print(f"  [{ts}]")
        print(f"   Overall: error_rate={row['error_rate']*100:.1f}% | "
              f"avg_latency={row['avg_latency']:.0f}ms | "
              f"p95_latency={row['p95_latency']:.0f}ms | "
              f"requests={int(row['request_count'])} | "
              f"errors={int(row['error_count'])}")

        # per-endpoint breakdown for this window
        endpoint_data = breakdown.get(ts_str, {})
        if endpoint_data:
            print(f"   Per-endpoint breakdown:")

            # sort endpoints by error_rate descending so worst shows first
            sorted_endpoints = sorted(
                endpoint_data.items(),
                key=lambda x: x[1]["error_rate"],
                reverse=True
            )
            for ep, metrics in sorted_endpoints:
                flag = " <-- HIGH ERROR RATE" if metrics["error_rate"] > 10 else ""
                flag = flag or (" <-- HIGH LATENCY" if metrics["p95_latency"] > 2000 else "")
                print(f"     {ep:25s} | error={metrics['error_rate']}% | "
                      f"avg={metrics['avg_latency']}ms | "
                      f"p95={metrics['p95_latency']}ms | "
                      f"req={metrics['request_count']}{flag}")
        print()

        export.append({
            "timestamp":       ts_str,
            "error_rate":      round(row["error_rate"] * 100, 2),
            "avg_latency":     round(row["avg_latency"], 2),
            "p95_latency":     round(row["p95_latency"], 2),
            "request_count":   int(row["request_count"]),
            "error_count":     int(row["error_count"]),
            "anomaly_score":   round(row["anomaly_score"], 4),
            "endpoint_breakdown": endpoint_data,
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
        print("No log entries found. Run the Flask app first.")
        exit(1)

    print(f"Parsed {len(df)} log entries")
    print(f"Building {WINDOW} time windows...")
    windows = build_windows(df)
    print(f"Created {len(windows)} time windows")

    print("Building per-endpoint breakdown...")
    breakdown = build_endpoint_breakdown(df)

    print("Running Isolation Forest on time windows...")
    windows = detect_anomalies(windows)

    print_results(windows, breakdown)


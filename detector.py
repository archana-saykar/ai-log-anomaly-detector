import re
import pandas as pd
from sklearn.ensemble import IsolationForest
from datetime import datetime
import json

LOG_FILE = "logs/app.log"

# ── Step 1: Parse log file ─────────────────────────────────────────────────────
def parse_logs(filepath):
    """
    Read app.log and extract structured fields from each line.
    Returns a list of dicts, one per log line.
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
                    "timestamp": match.group("timestamp"),
                    "level":     match.group("level"),
                    "method":    match.group("method"),
                    "endpoint":  match.group("endpoint"),
                    "status":    int(match.group("status")),
                    "latency_ms": float(match.group("latency")),
                    "is_error":  1 if int(match.group("status")) >= 500 else 0,
                    "raw":       line.strip()
                })
    return records


# ── Step 2: Feature engineering ───────────────────────────────────────────────
def build_features(records):
    """
    Convert raw records into a DataFrame with features the model can use.
    We use latency_ms and is_error as the two key signals.
    """
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S,%f")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ── Step 3: Run Isolation Forest ──────────────────────────────────────────────
def detect_anomalies(df):
    """
    Train Isolation Forest on latency and error signals.
    Adds an 'anomaly' column: -1 = anomaly, 1 = normal.
    contamination=0.05 means we expect ~5% of data to be anomalous.
    """
    features = df[["latency_ms", "is_error"]]

    model = IsolationForest(
        n_estimators=100,   # number of trees — more = more stable results
        contamination=0.05, # expected proportion of anomalies
        random_state=42     # fixed seed so results are reproducible
    )

    df["anomaly"] = model.fit_predict(features)
    df["anomaly_score"] = model.decision_function(features)  # lower = more anomalous
    return df


# ── Step 4: Print results ──────────────────────────────────────────────────────
def print_results(df):
    anomalies = df[df["anomaly"] == -1]
    normal    = df[df["anomaly"] == 1]

    print("\n" + "="*60)
    print("       LOG ANOMALY DETECTION RESULTS")
    print("="*60)
    print(f"Total log lines analyzed : {len(df)}")
    print(f"Normal entries           : {len(normal)}")
    print(f"Anomalies detected       : {len(anomalies)}")
    print("="*60)

    if anomalies.empty:
        print("\n✅ No anomalies detected. System looks healthy.")
    else:
        print(f"\n🚨 {len(anomalies)} ANOMALOUS log entries found:\n")
        for _, row in anomalies.iterrows():
            print(f"  [{row['timestamp']}]")
            print(f"   {row['method']} {row['endpoint']} | "
                  f"status={row['status']} | latency={row['latency_ms']}ms | "
                  f"score={row['anomaly_score']:.4f}")
            print()

    # Save anomalies to a JSON file for Week 3 (AI summarizer will read this)
    anomalies_export = anomalies[["timestamp", "level", "method", "endpoint",
                                   "status", "latency_ms", "anomaly_score", "raw"]].copy()
    anomalies_export["timestamp"] = anomalies_export["timestamp"].astype(str)
    anomalies_export.to_json("logs/anomalies.json", orient="records", indent=2)
    print(f"💾 Anomalies saved to logs/anomalies.json (Week 3 AI summarizer will use this)")
    print("="*60)


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📂 Reading logs...")
    records = parse_logs(LOG_FILE)

    if not records:
        print("❌ No log entries found. Run the Flask app first: python3 app.py")
        exit(1)

    print(f"✅ Parsed {len(records)} log entries")

    print("⚙️  Building features...")
    df = build_features(records)

    print("🤖 Running Isolation Forest anomaly detection...")
    df = detect_anomalies(df)

    print_results(df)

from flask import Flask, jsonify, request
import logging
import random
import time
import datetime
import os

app = Flask(__name__)

# ── Logging setup ──────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── Simulated services / endpoints ────────────────────────────
ENDPOINTS = ["/api/orders", "/api/users", "/api/products", "/api/payments"]
ERROR_MESSAGES = [
    "Database connection timeout",
    "Upstream service unavailable",
    "Memory limit exceeded",
    "Null pointer exception in order processor",
    "Payment gateway timed out",
    "Redis cache miss — fallback failed",
]

def simulate_latency(spike=False):
    if spike:
        return round(random.uniform(3000, 8000), 2)
    return round(random.uniform(50, 400), 2)

def simulate_request(force_error=False, force_spike=False):
    endpoint = random.choice(ENDPOINTS)
    method   = random.choice(["GET", "POST", "PUT"])
    spike    = force_spike or random.random() < 0.05
    error    = force_error or random.random() < 0.03
    latency  = simulate_latency(spike)
    status   = random.choice([500, 502, 503]) if error else 200

    log_line = (
        f'method={method} endpoint={endpoint} '
        f'status={status} latency_ms={latency}'
    )

    if error:
        msg = random.choice(ERROR_MESSAGES)
        logger.error(f"{log_line} error='{msg}'")
    elif spike:
        logger.warning(f"{log_line} note='high_latency'")
    else:
        logger.info(log_line)

    return {"endpoint": endpoint, "status": status, "latency_ms": latency}


def write_log_with_timestamp(ts, force_error=False, force_spike=False):
    """
    Write a log line with a specific timestamp.
    Used by /simulate/bulk to spread logs across multiple fake time windows.
    Why: GitHub Actions runs everything in under 60 seconds — all logs
    fall into one time window. Fake timestamps spread them across multiple
    windows so Isolation Forest has enough data to detect anomalies.
    """
    endpoint = random.choice(ENDPOINTS)
    method   = random.choice(["GET", "POST", "PUT"])
    spike    = force_spike or random.random() < 0.05
    error    = force_error or random.random() < 0.03
    latency  = simulate_latency(spike)
    status   = random.choice([500, 502, 503]) if error else 200
    level    = "ERROR" if error else ("WARNING" if spike else "INFO")

    log_line = (
        f"{ts.strftime('%Y-%m-%d %H:%M:%S')},{ts.microsecond // 1000:03d} "
        f"{level} "
        f"method={method} endpoint={endpoint} "
        f"status={status} latency_ms={latency}"
    )

    if error:
        msg = random.choice(ERROR_MESSAGES)
        log_line += f" error='{msg}'"

    with open("logs/app.log", "a") as f:
        f.write(log_line + "\n")

    return {"endpoint": endpoint, "status": status, "latency_ms": latency}


# ── Flask routes ───────────────────────────────────────────────

@app.route("/health")
def health():
    logger.info("method=GET endpoint=/health status=200 latency_ms=5")
    return jsonify({"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()})

@app.route("/simulate")
def simulate():
    n = int(request.args.get("n", 20))
    results = [simulate_request() for _ in range(n)]
    return jsonify({"generated": len(results), "sample": results[:3]})

@app.route("/simulate/anomaly")
def simulate_anomaly():
    results = []
    for _ in range(10):
        results.append(simulate_request(force_error=True, force_spike=True))
        time.sleep(0.1)
    logger.error("ANOMALY BURST: 10 consecutive failures detected in simulation")
    return jsonify({"injected": "anomaly_burst", "events": len(results)})

@app.route("/simulate/spike")
def simulate_spike():
    results = [simulate_request(force_spike=True) for _ in range(8)]
    return jsonify({"injected": "latency_spike", "events": len(results)})

@app.route("/simulate/bulk")
def simulate_bulk():
    """
    Generate logs spread across multiple fake time windows.
    Used by GitHub Actions so the detector has enough windows to analyze.

    Creates:
    - 8 normal windows (50 requests each, low error rate)
    - 2 anomalous windows (50 requests each, high error + latency)

    Why fake timestamps?
    GitHub Actions runs in ~30 seconds so all real logs fall into
    one 1-minute window. Fake timestamps simulate a realistic
    multi-hour traffic pattern without waiting.
    """
    now = datetime.datetime.now()
    total = 0

    # generate 8 normal windows (one per minute going back 10 mins)
    for i in range(10, 2, -1):
        window_start = now - datetime.timedelta(minutes=i)
        for j in range(50):
            ts = window_start + datetime.timedelta(seconds=random.randint(0, 59))
            write_log_with_timestamp(ts, force_error=False, force_spike=False)
            total += 1

    # generate 2 anomalous windows (most recent minutes)
    for i in range(2, 0, -1):
        window_start = now - datetime.timedelta(minutes=i)
        for j in range(50):
            ts = window_start + datetime.timedelta(seconds=random.randint(0, 59))
            write_log_with_timestamp(ts, force_error=True, force_spike=True)
            total += 1

    return jsonify({
        "generated": total,
        "normal_windows": 8,
        "anomalous_windows": 2,
        "note": "Logs spread across 10 fake time windows"
    })

@app.route("/logs/tail")
def tail_logs():
    n = int(request.args.get("n", 50))
    try:
        with open("logs/app.log", "r") as f:
            lines = f.readlines()
        return jsonify({"lines": lines[-n:]})
    except FileNotFoundError:
        return jsonify({"lines": [], "note": "No log file yet"})

if __name__ == "__main__":
    logger.info("=== App starting up ===")
    app.run(host="0.0.0.0", port=5000, debug=False)

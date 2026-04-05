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
        logging.StreamHandler()          # also prints to console
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
    """Return a realistic response time in ms."""
    if spike:
        return round(random.uniform(3000, 8000), 2)   # anomaly: very slow
    return round(random.uniform(50, 400), 2)           # normal

def simulate_request(force_error=False, force_spike=False):
    """Log one fake HTTP request with optional anomaly injection."""
    endpoint  = random.choice(ENDPOINTS)
    method    = random.choice(["GET", "POST", "PUT"])
    spike     = force_spike or random.random() < 0.05  # 5 % natural spikes
    error     = force_error or random.random() < 0.03  # 3 % natural errors
    latency   = simulate_latency(spike)
    status    = random.choice([500, 502, 503]) if error else 200

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

# ── Flask routes ───────────────────────────────────────────────

@app.route("/health")
def health():
    logger.info("method=GET endpoint=/health status=200 latency_ms=5")
    return jsonify({"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()})

@app.route("/simulate")
def simulate():
    """Generate N normal log entries."""
    n = int(request.args.get("n", 20))
    results = [simulate_request() for _ in range(n)]
    return jsonify({"generated": len(results), "sample": results[:3]})

@app.route("/simulate/anomaly")
def simulate_anomaly():
    """Inject a burst of errors + latency spikes — triggers the detector."""
    results = []
    for _ in range(10):
        results.append(simulate_request(force_error=True, force_spike=True))
        time.sleep(0.1)
    logger.error("ANOMALY BURST: 10 consecutive failures detected in simulation")
    return jsonify({"injected": "anomaly_burst", "events": len(results)})

@app.route("/simulate/spike")
def simulate_spike():
    """Inject latency spikes only."""
    results = [simulate_request(force_spike=True) for _ in range(8)]
    return jsonify({"injected": "latency_spike", "events": len(results)})

@app.route("/logs/tail")
def tail_logs():
    """Return the last N lines of the log file."""
    n = int(request.args.get("n", 50))
    try:
        with open("logs/app.log", "r") as f:
            lines = f.readlines()
        return jsonify({"lines": lines[-n:]})
    except FileNotFoundError:
        return jsonify({"lines": [], "note": "No log file yet — call /simulate first"})

if __name__ == "__main__":
    logger.info("=== App starting up ===")
    app.run(host="0.0.0.0", port=5000, debug=False)


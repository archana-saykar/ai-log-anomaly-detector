# AI-Powered Log Anomaly Detector

An end-to-end monitoring system built with Python, Scikit-learn, Docker, and Claude AI — that detects failures using ML and sends AI-generated incident reports to Slack automatically.

---

## The Problem

When a production system fails, engineers spend 30+ minutes digging through thousands of log lines, piecing together what broke, and writing an incident report — often at 2am under pressure.

This tool does all of that automatically in under 40 seconds.

---

## How It Works

```
Logs → Isolation Forest (time-window analysis) → Claude AI → Slack Alert
```

---

## Phase 1 — E-commerce API Monitor

Built a Flask API simulating a live e-commerce backend to prove the core detection pipeline.

### What it does
- Generates realistic logs with natural error rates and latency spikes across endpoints `/api/orders`, `/api/users`, `/api/products`, `/api/payments`
- Groups logs into 1-minute time windows and extracts features — error rate, avg latency, p95 latency, request count
- Isolation Forest learns normal traffic patterns and flags anomalous windows automatically
- Claude AI reads the flagged windows and writes a structured incident report
- Slack alert fires with root cause, severity rating, and recommended actions

### Sample output
```
TIME-WINDOW ANOMALY DETECTION RESULTS
Total windows analyzed   : 11
Normal windows           : 10
Anomalous windows        : 1

[2026-04-07 02:24:00]
 Overall: error_rate=5.3% | avg_latency=662ms | p95_latency=4996ms
 Per-endpoint breakdown:
   /api/payments  | error=45.0% | avg=6200ms <-- HIGH ERROR RATE
   /api/users     | error=5.1%  | avg=722ms
   /api/products  | error=6.2%  | avg=752ms
```

### Slack alert
```
AUTOMATED INCIDENT ALERT — Action Required

INCIDENT SUMMARY
Multiple API endpoints experienced elevated error rates and severe latency
degradation. /api/payments shows 45% error rate — shared dependency failure
rather than isolated endpoint issues.

ROOT CAUSE: Database connection pool exhaustion or lock contention.
SEVERITY: P2. Recommend immediate investigation.
```

### Tech used in Phase 1
`Python` · `Flask` · `Scikit-learn` · `Pandas` · `Claude API` · `Slack Webhooks` · `Docker` · `Docker Compose` · `GitHub Actions`

---

## Phase 2 — Live Portfolio Website Monitor

Took the same pipeline and connected it to a real live website — [archanasaykar.com](https://archanasaykar.com).

### What changed
- Built a separate `portfolio_monitor.py` Flask API that receives real tracking events from the live website
- Added a JavaScript tracking call to the portfolio — fires on every resume download attempt
- When the resume download link breaks, the detector catches the 404 spike and fires an alert
- Used ngrok to expose the local API to the internet so the live website can reach it

### Why this matters
Phase 1 proved the pipeline works on simulated data. Phase 2 proved it works on **real production traffic** — real users, real failures, real alerts.

### Real failure scenario
The resume download link was intentionally broken to simulate a bad deployment:

```
User clicks Download Resume on archanasaykar.com
        ↓
JavaScript fires tracking event → portfolio_monitor.py logs status=404
        ↓
Isolation Forest detects 100% error rate spike in recent time window
        ↓
Claude AI identifies exact endpoint and root cause
        ↓
Slack alert: "/resume/download — complete service failure"
```

### Sample output — real 404 errors from live website
```
TIME-WINDOW ANOMALY DETECTION RESULTS
Total windows analyzed   : 10
Normal windows           : 9
Anomalous windows        : 1

[2026-04-10 21:54:00]
 Overall: error_rate=100.0% | avg_latency=6924ms | p95=7780ms
 /resume/download  | error=100.0% <-- HIGH ERROR RATE
```

### Slack alert — real incident from live website
```
AUTOMATED INCIDENT ALERT — Action Required

INCIDENT SUMMARY
At 21:54:00 UTC, /resume/download experienced complete service failure
with 100% error rate across all requests. File unavailable — likely a
deployment issue.

SEVERITY: P1. Restore the file immediately and verify the fix.
```

### Additional tech in Phase 2
`JavaScript fetch API` · `ngrok` · `CORS handling`

---

## What I Learned Moving from Phase 1 to Phase 2

| Challenge | Phase 1 | Phase 2 |
|---|---|---|
| Error threshold | 500+ (server errors) | 400+ (includes 404 file not found) |
| Log source | Simulated Flask app | Real website via tracking call |
| Data distribution | Controlled | Real, unpredictable traffic |
| CORS | Not needed | Required for cross-origin requests |
| URL management | localhost | ngrok public tunnel |

---

## Project Structure
```
├── app.py                    # Phase 1: Flask e-commerce log generator
├── detector.py               # Phase 1: Time-window anomaly detection
├── summarizer.py             # Both: Claude AI incident report generator
├── slack_alert.py            # Both: Slack webhook integration
├── portfolio_monitor.py      # Phase 2: Live portfolio tracking API
├── portfolio_detector.py     # Phase 2: Portfolio anomaly detector
├── Dockerfile                # Flask app container
├── Dockerfile.detector       # Detector + summarizer container
├── docker-compose.yml        # Multi-container orchestration
├── .github/workflows/
│   └── detect.yml            # GitHub Actions CI/CD pipeline
├── requirements.txt
├── requirements.detector.txt
└── .env.example
```

---

## Run It Yourself

### Prerequisites
- Python 3.10+
- Docker and Docker Compose
- Anthropic API key (console.anthropic.com)
- Slack workspace with Incoming Webhooks enabled

### Phase 1 — E-commerce monitor
```bash
git clone https://github.com/archana-saykar/ai-log-anomaly-detector.git
cd ai-log-anomaly-detector
cp .env.example .env
# Add ANTHROPIC_API_KEY and SLACK_WEBHOOK_URL

# Run with Docker
docker-compose up --build

# Or run manually
python3 app.py
# Hit http://localhost:5000/simulate?n=100
# Hit http://localhost:5000/simulate/anomaly
python3 detector.py
python3 summarizer.py
```

### Phase 2 — Portfolio monitor
```bash
# Start ngrok tunnel
ngrok http 5001

# Start portfolio monitor
python3 portfolio_monitor.py

# Generate traffic on your website, then run
python3 portfolio_detector.py
python3 summarizer.py
```

---

## Key Engineering Decisions

**Why Isolation Forest?**
No labeled data needed — it learns normal behavior from actual traffic and flags deviations. No manual threshold tuning.

**Why time-window analysis?**
A single slow request is noise. A whole minute of slow requests is an incident. 1-minute windows with aggregated metrics give the model meaningful signals.

**Why p95 latency alongside average?**
Averages hide tail behavior. p95 catches situations where most users are fine but 5% are experiencing severe slowdowns.

**Why per-endpoint breakdown?**
Overall metrics tell you something is wrong. Per-endpoint breakdown tells Claude exactly which service is failing — enabling precise root cause analysis.

---
## Demo
[Watch the demo video](https://1drv.ms/v/c/6861f1d77fed1f04/IQA0QAkbolQETo-HaXIGV4TnAehr34zrLZ6549dB7gsBC7M?e=dYTr6G)

## Author
**Archana Saykar**
MS Information Systems, University of Cincinnati
[LinkedIn](https://linkedin.com/in/archana-saykar) | [Portfolio](https://archanasaykar.com)

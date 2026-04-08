# AI-Powered Log Anomaly Detector

An automated monitoring tool that detects anomalies in application logs using Machine Learning and delivers AI-generated incident reports directly to Slack.

---

## The Problem

Every production system generates thousands of log lines per minute. Traditional monitoring tools use **fixed thresholds** to trigger alerts — but this creates two problems:

- **Too many alerts** — engineers start ignoring them (alert fatigue)
- **Subtle failures go unnoticed** — a slow memory leak or gradual latency increase never crosses the threshold until it is too late

On top of that, when something does go wrong, an on-call engineer has to manually dig through logs, figure out what happened, and write an incident report — often under pressure.

**This tool solves all of that automatically.**

---

## The Solution

Instead of fixed thresholds, this tool uses **Isolation Forest** — a Machine Learning algorithm that learns what normal looks like and flags anything that deviates from it. When anomalies are detected, **Claude AI** analyzes them and writes a structured incident report. The report is then posted to **Slack** automatically.

---

## How It Works

### Architecture
```
Flask App -> logs/app.log -> Isolation Forest -> anomalies.json -> Claude API -> Slack Alert
```

### Step by Step

**1. Log Generator (`app.py`)**
A Flask API that simulates a real e-commerce backend with endpoints like `/api/orders`, `/api/payments`, and `/api/users`. Generates realistic logs with natural error rates and latency spikes, and includes endpoints to inject anomaly bursts on demand.

**2. Anomaly Detector (`detector.py`)**
Parses the log file, extracts features (latency, error status), and feeds them into an Isolation Forest model. The model learns normal traffic patterns and assigns an anomaly score to each log entry. Flagged entries are saved to `anomalies.json`.

**3. AI Incident Summarizer (`summarizer.py`)**
Sends the flagged anomalies to the Claude API with a structured prompt. Claude returns a full incident report covering root cause analysis, affected services, severity rating, and recommended actions.

**4. Slack Alerting (`slack_alert.py`)**
When a report is generated, a formatted alert is automatically posted to a Slack channel via Incoming Webhooks — no manual steps needed.

**5. Docker (`Dockerfile`, `docker-compose.yml`)**
The app and detector run as two separate Docker containers sharing a log volume, mirroring how real production monitoring stacks are deployed.

---

## Sample Output

### Anomaly Detection
```
Total log lines analyzed : 400
Normal entries           : 380
Anomalies detected       : 20

PUT /api/users     | status=200 | latency=7409ms | score=-0.2811
POST /api/payments | status=503 | latency=5796ms | score=-0.1809
GET /api/products  | status=500 | latency=3124ms | score=-0.0474
```

### Slack Alert
```
AUTOMATED INCIDENT ALERT
Anomalies Detected: 27   |   Status: Action Required

INCIDENT SUMMARY
Multiple API endpoints experienced elevated latency (3-7s) combined
with sporadic 5xx errors, suggesting a cascading failure pattern.

AFFECTED SERVICES
- /api/users    -- consistently elevated latency (4.8-7.1s)
- /api/payments -- 503 errors and extreme latency (5-6.4s)
- /api/products -- multiple 500 errors (3-3.6s)

ROOT CAUSE
Most likely: Database connection pool exhaustion or lock contention.
Write-heavy endpoints (POST/PUT) show highest degradation.

Full report saved to logs/incident_report.txt
```

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Log Generator | Python, Flask | Lightweight, simulates realistic API traffic |
| Anomaly Detection | Scikit-learn, Pandas | Isolation Forest needs no labeled data |
| AI Summarizer | Anthropic Claude API | Consistent, structured reports in seconds |
| Alerting | Slack Incoming Webhooks | Delivers alerts where the team already works |
| Containerization | Docker, Docker Compose | Mirrors real production deployment patterns |

---

## Run It Yourself

### Prerequisites
- Python 3.10+
- Docker and Docker Compose
- Anthropic API key (console.anthropic.com)
- Slack workspace with Incoming Webhooks enabled

### Setup
```bash
git clone https://github.com/archana-saykar/ai-log-anomaly-detector.git
cd ai-log-anomaly-detector
cp .env.example .env
# Add ANTHROPIC_API_KEY and SLACK_WEBHOOK_URL to .env
```

### Run with Docker
```bash
docker-compose up --build
```

### Run Manually
```bash
# Terminal 1 - start the app
python3 app.py

# Browser - generate logs
http://localhost:5000/simulate?n=100
http://localhost:5000/simulate/anomaly

# Terminal 2 - run the pipeline
python3 detector.py
python3 summarizer.py
```

---

## Project Structure
```
├── app.py                    # Flask log generator
├── detector.py               # Isolation Forest anomaly detection
├── summarizer.py             # Claude AI incident report
├── slack_alert.py            # Slack webhook integration
├── Dockerfile                # Flask app container
├── Dockerfile.detector       # Detector + summarizer container
├── docker-compose.yml        # Multi-container orchestration
├── requirements.txt
├── requirements.detector.txt
├── .env.example              # Environment variable template
└── README.md
```

---

## Author
**Archana Saykar**
MS Information Systems, University of Cincinnati
[LinkedIn](https://linkedin.com/in/archana-saykar) | [Portfolio](archanasaykar.com)

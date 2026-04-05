# 🚨 AI-Powered Log Anomaly Detector

An end-to-end SRE tool that automatically detects anomalies in application logs using Machine Learning and generates plain-English incident reports using AI.

Built to solve a real-world SRE problem: **alert fatigue and slow incident response caused by threshold-based monitoring.**

---

## 🎯 Problem Statement

Traditional monitoring tools rely on static thresholds to trigger alerts.  
This means:
- Too many false positives → engineers ignore alerts (alert fatigue)
- Subtle degradations go undetected until they become outages
- On-call engineers spend valuable time writing incident reports manually

This project solves all three problems in one automated pipeline.

---

## 🏗️ Architecture

```
Flask App (log generator)
        ↓
   logs/app.log
        ↓
Isolation Forest (anomaly detector)
        ↓
  logs/anomalies.json
        ↓
   Claude API (AI summarizer)
        ↓
 logs/incident_report.txt
```

---

## ✨ Features

- **Realistic log generation** — Simulates a production e-commerce API with natural error rates and latency spikes
- **ML-based anomaly detection** — Uses Isolation Forest to learn normal behavior and flag deviations, no manual thresholds needed
- **AI incident summarizer** — Sends flagged anomalies to Claude API and receives a structured incident report with root cause analysis, affected services, severity rating, and recommended actions
- **Zero external dependencies for detection** — Only uses scikit-learn and pandas, both industry standard

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Log Generator | Python, Flask |
| Anomaly Detection | Scikit-learn (Isolation Forest), Pandas |
| AI Summarizer | Anthropic Claude API |
| Environment | WSL Ubuntu, Python venv |
| Version Control | Git, GitHub |

---

## 📁 Project Structure

```
ai-log-anomaly-detector/
├── app.py              # Flask app that simulates production logs
├── detector.py         # Isolation Forest anomaly detection
├── summarizer.py       # Claude API incident report generator
├── requirements.txt    # Python dependencies
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Anthropic API key (get free credits at console.anthropic.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/archana-saykar/ai-log-anomaly-detector.git
cd ai-log-anomaly-detector

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# Install dependencies
pip install flask pandas scikit-learn
```

### Running the Pipeline

**Step 1 — Start the log generator**
```bash
python3 app.py
```

**Step 2 — Generate logs and inject anomalies** (in browser)
```
http://localhost:5000/simulate?n=100     # normal traffic
http://localhost:5000/simulate/anomaly  # inject anomaly burst
```

**Step 3 — Run the anomaly detector**
```bash
python3 detector.py
```

**Step 4 — Generate AI incident report**
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
python3 summarizer.py
```

---

## 📊 Sample Output

### Anomaly Detector
```
========================================================
       LOG ANOMALY DETECTION RESULTS
========================================================
Total log lines analyzed : 160
Normal entries           : 151
Anomalies detected       : 9
========================================================

🚨 [2026-04-04 22:47:20] POST /api/payments | status=502 | latency=7840.91ms | score=-0.0757
🚨 [2026-04-04 22:47:08] POST /api/users   | status=503 | latency=5796.68ms | score=-0.0110
```

### AI Incident Report
```
## 1. INCIDENT SUMMARY
Between February 26 and April 4, 2026, the system experienced two distinct 
outage windows characterized by elevated latencies (3-7+ seconds) and elevated 
error rates (500/502/503 responses). The April 4th incident appears more severe, 
with multiple simultaneous service failures suggesting a cascading failure pattern.

## 2. AFFECTED SERVICES
- POST /api/users    — multiple 503 errors, latencies 4.8–5.8s
- POST /api/payments — 502 error, 7.8s latency
- POST /api/orders   — 503 error, 104ms latency

## 3. ROOT CAUSE ANALYSIS
Most Likely: Database Connection Pool Exhaustion or Lock Contention
Evidence: Write-heavy endpoints (POST/PUT) show highest degradation.
Latency signature of 3-7+ seconds is consistent with backend resource starvation.

## 4. SEVERITY: P1
Multiple critical services failing simultaneously with cascading pattern.

## 5. RECOMMENDED ACTIONS
Immediate: Check DB connection pool utilization, review recent deployments.
Long term:  Implement connection pool monitoring, add circuit breakers.
```

---

## 💡 Key Engineering Decisions

**Why Isolation Forest?**  
Unlike threshold-based alerting, Isolation Forest learns what "normal" looks like from the data itself. This means it catches subtle anomalies that fixed thresholds would miss, and adapts as traffic patterns change.

**Why Claude API for summarization?**  
Writing incident reports manually is time-consuming and inconsistent. Using an LLM ensures every incident gets a structured, actionable report in seconds — freeing engineers to focus on fixing the problem.

---

## 🔮 Future Improvements

- [ ] Grafana dashboard for real-time visualization
- [ ] GitHub Actions workflow for scheduled detection
- [ ] Docker containerization for easy deployment
- [ ] Slack/PagerDuty integration for alert notifications
- [ ] Support for multiple log formats (JSON, syslog)

---

## 👩‍💻 Author

**Archana Saykar**  
MS Information Systems, University of Cincinnati  
[LinkedIn](https://linkedin.com/in/archana-saykar)


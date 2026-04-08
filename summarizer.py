import json
import urllib.request
import urllib.error
import os
from datetime import datetime
from slack_alert import send_slack_alert

ANOMALIES_FILE = "logs/anomalies.json"
REPORT_FILE    = "logs/incident_report.txt"
API_URL        = "https://api.anthropic.com/v1/messages"


# ── Step 1: Load anomalies ─────────────────────────────────────────────────────
def load_anomalies(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


# ── Step 2: Build prompt from time-window anomalies ───────────────────────────
def build_prompt(anomalies):
    """
    Format time-window anomalies into a clear prompt for Claude.
    Each entry now represents a 1-minute window, not a single log line.
    """
    lines = []
    for a in anomalies:
        lines.append(
            f"- [{a['timestamp']}] "
            f"error_rate={a['error_rate']}% | "
            f"avg_latency={a['avg_latency']}ms | "
            f"p95_latency={a['p95_latency']}ms | "
            f"requests={a['request_count']} | "
            f"errors={a['error_count']} | "
            f"anomaly_score={a['anomaly_score']}"
        )

    anomaly_text = "\n".join(lines)

    prompt = f"""You are a Senior Site Reliability Engineer analyzing a production incident.

The following 1-minute time windows were flagged as anomalous by an ML detection system (Isolation Forest with time-window analysis).

Each row represents aggregated metrics for one minute of traffic:
- error_rate: percentage of requests returning 5xx errors
- avg_latency: average response time in milliseconds
- p95_latency: 95th percentile response time (the slowest 5% of requests)
- requests: total request count in that window
- errors: total error count in that window
- anomaly_score: the more negative, the more anomalous

FLAGGED TIME WINDOWS:
{anomaly_text}

Please provide a structured incident report with the following sections:

1. INCIDENT SUMMARY
   - What happened in plain English (2-3 sentences)
   - Time range affected

2. AFFECTED SERVICES
   - Which endpoints and services are impacted based on the patterns

3. ROOT CAUSE ANALYSIS
   - Most likely cause based on the error rates and latency patterns you see
   - Supporting evidence from the data

4. SEVERITY
   - Rate as P1/P2/P3 and explain why

5. RECOMMENDED ACTIONS
   - Immediate steps the on-call engineer should take
   - Longer term preventive measures

Keep the tone professional, concise, and actionable."""

    return prompt


# ── Step 3: Call Claude API ────────────────────────────────────────────────────
def call_claude(prompt, api_key):
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01"
    }

    body = json.dumps({
        "model":      "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"API Error {e.code}: {error_body}")


# ── Step 4: Save report and send Slack alert ───────────────────────────────────
def save_report(report_text, anomaly_count):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_report = f"""
{'='*60}
AUTOMATED INCIDENT REPORT
Generated  : {timestamp}
Anomalies  : {anomaly_count} anomalous time windows detected
{'='*60}

{report_text}

{'='*60}
END OF REPORT
{'='*60}
"""
    with open(REPORT_FILE, "w") as f:
        f.write(full_report)

    print(full_report)
    print(f"Report saved to {REPORT_FILE}")
    send_slack_alert(anomaly_count, report_text)


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set.")
        print("Run: export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)

    print("Loading anomalies from detector output...")
    anomalies = load_anomalies(ANOMALIES_FILE)

    if not anomalies:
        print("No anomalies found. Run detector.py first.")
        exit(1)

    print(f"Found {len(anomalies)} anomalous time windows")
    print("Sending to Claude API for incident analysis...")

    prompt = build_prompt(anomalies)
    report = call_claude(prompt, api_key)

    print("\nIncident report generated!\n")
    save_report(report, len(anomalies))

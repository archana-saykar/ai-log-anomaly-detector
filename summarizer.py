import json
import urllib.request
import urllib.error
import os
from datetime import datetime
from slack_alert import send_slack_alert

ANOMALIES_FILE = "logs/anomalies.json"
REPORT_FILE    = "logs/incident_report.txt"
API_URL        = "https://api.anthropic.com/v1/messages"


def load_anomalies(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


def build_prompt(anomalies):
    """
    Build a prompt that includes both overall window metrics
    and per-endpoint breakdown — gives Claude much richer context.
    """
    lines = []
    for a in anomalies:
        lines.append(
            f"\n[Window: {a['timestamp']}]"
            f"\n  Overall: error_rate={a['error_rate']}% | "
            f"avg_latency={a['avg_latency']}ms | "
            f"p95_latency={a['p95_latency']}ms | "
            f"requests={a['request_count']} | "
            f"errors={a['error_count']} | "
            f"score={a['anomaly_score']}"
        )

        # add per-endpoint breakdown if available
        breakdown = a.get("endpoint_breakdown", {})
        if breakdown:
            lines.append("  Per-endpoint breakdown:")
            sorted_eps = sorted(
                breakdown.items(),
                key=lambda x: x[1]["error_rate"],
                reverse=True
            )
            for ep, m in sorted_eps:
                lines.append(
                    f"    {ep}: error={m['error_rate']}% | "
                    f"avg={m['avg_latency']}ms | "
                    f"p95={m['p95_latency']}ms | "
                    f"requests={m['request_count']}"
                )

    anomaly_text = "\n".join(lines)

    prompt = f"""You are a Senior Site Reliability Engineer analyzing a production incident.

The following 1-minute time windows were flagged as anomalous by an ML detection system.
Each window includes overall metrics AND a per-endpoint breakdown showing which specific
endpoints are contributing to the anomaly.

Metrics explained:
- error_rate: % of requests returning 5xx errors
- avg_latency: average response time in ms
- p95_latency: 95th percentile response time (slowest 5% of requests)
- anomaly_score: more negative = more anomalous

FLAGGED TIME WINDOWS WITH ENDPOINT BREAKDOWN:
{anomaly_text}

Please provide a structured incident report:

1. INCIDENT SUMMARY
   - What happened and when (2-3 sentences)
   - Which endpoints were most affected

2. ROOT CAUSE ANALYSIS
   - Most likely cause based on error rates and latency patterns
   - Use the per-endpoint data to support your analysis

3. SEVERITY
   - P1/P2/P3 with justification based on error rates and impact

4. RECOMMENDED ACTIONS
   - Immediate steps (next 5 minutes)
   - Short term fixes (next 30 minutes)
   - Long term preventive measures

Be specific about endpoint names. Keep it concise and actionable."""

    return prompt


def call_claude(prompt, api_key):
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01"
    }
    body = json.dumps({
        "model":      "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "messages":   [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        raise Exception(f"API Error {e.code}: {e.read().decode()}")


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


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set.")
        print("Run: export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)

    print("Loading anomalies...")
    anomalies = load_anomalies(ANOMALIES_FILE)

    if not anomalies:
        print("No anomalies found. Run detector.py first.")
        exit(1)

    print(f"Found {len(anomalies)} anomalous time windows")
    print("Sending to Claude API...")

    prompt = build_prompt(anomalies)
    report = call_claude(prompt, api_key)

    print("\nIncident report generated!\n")
    save_report(report, len(anomalies))


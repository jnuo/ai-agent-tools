"""Run Lighthouse CLI and parse JSON output."""

import json
import shutil
import subprocess


def run_lighthouse(
    url: str,
    device: str = "mobile",
    categories: list[str] | None = None,
) -> dict:
    """Run Lighthouse audit on a URL.

    Args:
        url: URL to audit
        device: 'mobile' or 'desktop'
        categories: List of categories to audit
            (performance, seo, accessibility, best-practices)

    Returns:
        dict with 'scores' (category scores), 'metrics' (Core Web Vitals),
        and 'failing_audits' (list of failed audits)

    Raises:
        FileNotFoundError: If lighthouse CLI is not installed
        RuntimeError: If lighthouse process fails
    """
    if shutil.which("lighthouse") is None:
        raise FileNotFoundError(
            "lighthouse CLI not found. Install with: npm install -g lighthouse"
        )

    if categories is None:
        categories = ["performance", "seo", "accessibility", "best-practices"]

    cmd = [
        "lighthouse",
        url,
        "--output=json",
        "--quiet",
        '--chrome-flags=--headless=new',
        f"--form-factor={device}",
    ]

    if device == "desktop":
        cmd.append("--preset=desktop")

    for cat in categories:
        cmd.append(f"--only-categories={cat}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"Lighthouse failed: {stderr}")

    data = json.loads(result.stdout)

    return _parse_lighthouse_output(data)


def _parse_lighthouse_output(data: dict) -> dict:
    """Parse Lighthouse JSON output into a structured dict."""
    # Category scores
    scores = {}
    for cat_id, cat_data in data.get("categories", {}).items():
        scores[cat_id] = {
            "title": cat_data.get("title", cat_id),
            "score": round((cat_data.get("score") or 0) * 100),
        }

    # Core Web Vitals and key metrics
    audits = data.get("audits", {})
    metrics = {}

    metric_keys = {
        "largest-contentful-paint": "LCP",
        "total-blocking-time": "TBT",
        "cumulative-layout-shift": "CLS",
        "first-contentful-paint": "FCP",
        "speed-index": "SI",
        "interactive": "TTI",
    }

    for audit_id, label in metric_keys.items():
        audit = audits.get(audit_id, {})
        if audit:
            metrics[label] = {
                "value": audit.get("numericValue"),
                "display": audit.get("displayValue", ""),
                "score": round((audit.get("score") or 0) * 100),
            }

    # Failing audits (score < 0.9 and has a title)
    failing = []
    for audit_id, audit in audits.items():
        score = audit.get("score")
        if score is not None and score < 0.9 and audit.get("title"):
            failing.append({
                "id": audit_id,
                "title": audit.get("title", ""),
                "score": round(score * 100),
                "display": audit.get("displayValue", ""),
            })

    # Sort failing audits by score ascending (worst first)
    failing.sort(key=lambda a: a["score"])

    return {
        "url": data.get("requestedUrl", ""),
        "fetch_time": data.get("fetchTime", ""),
        "scores": scores,
        "metrics": metrics,
        "failing_audits": failing,
        "raw": data,
    }

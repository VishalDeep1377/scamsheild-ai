import re, ipaddress
from urllib.parse import urlsplit, unquote
from collections import Counter
from pathlib import Path
import joblib
from app.config import settings

PATTERNS = [
    ("credential_request", r"\b(share|send|enter|confirm|verify)\b.{0,35}\b(otp|one.?time password|password|pin|cvv)\b", "critical", 25, "Requests a sensitive credential or one-time code."),
    ("urgent_threat", r"\b(account|card|wallet|service)\b.{0,45}\b(block|suspend|disable|expire|close)\b|\b(immediately|urgent|within \d+ hours?)\b", "high", 15, "Uses urgency or a threat of account/service suspension."),
    ("payment_request", r"\b(pay|payment|transfer|processing fee|deposit)\b.{0,35}\b(fee|charge|amount|now|today|job|prize)\b", "high", 15, "Requests money in a context commonly used by scams."),
    ("prize_bait", r"\b(you have won|winner|lottery|claim your prize|free reward)\b", "medium", 12, "Uses an unexpected prize or reward lure."),
    ("job_fee", r"\b(job|work|employment|interview)\b.{0,50}\b(registration fee|processing fee|deposit|pay)\b", "high", 18, "Combines a job opportunity with an upfront payment request."),
    ("link_bait", r"\b(click|tap|visit|open)\b.{0,35}\b(link|below|url|website)\b", "medium", 8, "Encourages the recipient to visit a link."),
    ("bank_impersonation", r"\b(bank|upi|kyc|account verification|income tax|courier)\b", "low", 5, "Mentions a high-value institution or service that is often impersonated; context is required."),
]
URL_RE = re.compile(r"https?://[^\s<>\])}\"']+", re.I)
SUSPICIOUS_TLDS = {"zip", "mov", "top", "click", "work", "country", "gq", "tk", "xyz"}

_model = None
def load_model():
    global _model
    if _model is None and Path(settings.model_path).exists():
        try:
            _model = joblib.load(settings.model_path)
        except Exception:
            _model = None
    return _model

def extract_urls(text: str):
    return [u.rstrip(".,!?;:") for u in URL_RE.findall(text)]

def analyze_url(url: str):
    # Parse only. Never fetch, resolve, redirect-follow, or open user-provided URLs.
    candidate = url.strip()
    if not re.match(r"^https?://", candidate, re.I):
        candidate = "http://" + candidate
    try:
        parts = urlsplit(candidate)
        host = (parts.hostname or "").lower().rstrip(".")
        if not host or any(ch.isspace() for ch in host):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
            is_ip = True
        except ValueError:
            is_ip = False
        labels = host.split(".")
        tld = labels[-1] if len(labels) > 1 else ""
        signals = []
        points = 0
        if parts.scheme != "https":
            signals.append(("unencrypted_http", "medium", 10, "Uses HTTP rather than HTTPS. HTTPS alone does not prove legitimacy."))
            points += 10
        if is_ip:
            signals.append(("ip_host", "high", 25, "Uses a raw IP address as the host instead of a normal domain."))
            points += 25
        if len(candidate) > 120:
            signals.append(("long_url", "low", 8, "Unusually long URL; inspect its destination carefully."))
            points += 8
        if "@" in parts.netloc:
            signals.append(("at_symbol", "high", 20, "Contains an @ symbol in the authority section, which can obscure the actual host."))
            points += 20
        if len(labels) >= 5:
            signals.append(("many_subdomains", "medium", 12, "Contains many subdomain levels."))
            points += 12
        if tld in SUSPICIOUS_TLDS:
            signals.append(("uncommon_tld", "low", 8, f"Uses the .{tld} top-level domain; this is not proof of maliciousness."))
            points += 8
        if "xn--" in host:
            signals.append(("punycode", "high", 20, "Contains punycode, which can be used for lookalike domains."))
            points += 20
        if re.search(r"(login|verify|secure|update|account|wallet)", parts.path, re.I):
            signals.append(("sensitive_path", "low", 7, "Path contains a sensitive-account keyword."))
            points += 7
        return {"host": host, "scheme": parts.scheme, "signals": signals, "score": min(points, 100), "valid": True}
    except Exception:
        return {"host": "", "scheme": "", "signals": [("invalid_url", "high", 25, "URL could not be parsed safely.")], "score": 25, "valid": False}

def analyze_text(text: str):
    normalized = re.sub(r"\s+", " ", text).strip()
    evidence = []
    raw_points = 0
    for name, pattern, severity, points, explanation in PATTERNS:
        if re.search(pattern, normalized, re.I):
            evidence.append({"signal": name, "severity": severity, "points": points, "explanation": explanation})
            raw_points += points
    urls = extract_urls(normalized)
    url_results = [analyze_url(u) for u in urls]
    for result in url_results:
        for signal, severity, points, explanation in result["signals"]:
            evidence.append({"signal": signal, "severity": severity, "points": points, "explanation": explanation})
            raw_points += points
    category = categorize(normalized)
    ml_prediction, confidence = predict_ml(normalized)
    if ml_prediction in {"phishing", "scam"} and confidence is not None and confidence >= 0.70:
        evidence.append({"signal": "ml_classifier", "severity": "medium", "points": 12, "explanation": f"ML model classified this text as {ml_prediction} (confidence {confidence:.0%})."})
        raw_points += 12
    # Diminishing cap: overlapping rules should not simply stack without limit.
    score = min(100, raw_points)
    if score < 25: level = "Low"
    elif score < 50: level = "Medium"
    elif score < 75: level = "High"
    else: level = "Critical"
    prediction = "suspicious" if score >= 25 or ml_prediction in {"phishing", "scam"} else "no strong indicators"
    actions = recommendations(category, evidence)
    return {"risk_score": score, "risk_level": level, "category": category, "prediction": prediction,
            "confidence": confidence, "evidence": evidence, "urls": url_results, "actions": actions,
            "model_available": load_model() is not None}

def categorize(text: str):
    t = text.lower()
    mapping = {
        "banking": ["bank", "upi", "kyc", "account", "otp", "card"],
        "job": ["job", "recruitment", "interview", "employment", "salary"],
        "delivery": ["delivery", "parcel", "courier", "shipment", "package"],
        "prize": ["lottery", "winner", "prize", "reward", "won"],
        "investment": ["investment", "crypto", "trading", "guaranteed return"],
        "technical_support": ["support", "customer care", "helpline", "refund"],
    }
    counts = {k: sum(1 for word in words if word in t) for k, words in mapping.items()}
    best = max(counts, key=counts.get)
    return best if counts[best] else "other"

def predict_ml(text: str):
    model = load_model()
    if model is None:
        return "unknown", None
    try:
        pred = str(model.predict([text])[0]).lower()
        confidence = float(max(model.predict_proba([text])[0])) if hasattr(model, "predict_proba") else None
        return pred, confidence
    except Exception:
        return "unknown", None

def recommendations(category, evidence):
    if not evidence:
        return ["No strong indicators were found. This does not prove the message is safe.", "Verify important requests using an official app or independently obtained contact details."]
    actions = ["Do not click links or open attachments until independently verified.",
               "Never share OTPs, passwords, PINs, CVVs, or recovery codes.",
               "Contact the organization through its official app or a trusted phone number."]
    if category == "job":
        actions.append("Do not pay recruitment, interview, training, or document-processing fees without independently verifying the employer.")
    if category == "banking":
        actions.append("Your bank will not need you to disclose an OTP or PIN to resolve an account issue.")
    return actions

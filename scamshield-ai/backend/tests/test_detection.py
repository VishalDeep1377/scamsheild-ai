from app.detection import analyze_text, analyze_url, extract_urls

def test_otp_request_is_flagged():
    result = analyze_text("Please share your OTP immediately to verify your bank account.")
    assert result["risk_score"] > 0
    assert any(x["signal"] == "credential_request" for x in result["evidence"])

def test_url_parser_does_not_fetch():
    result = analyze_url("http://192.0.2.10/login")
    assert result["valid"] is True
    assert any(x[0] == "ip_host" for x in result["signals"])

def test_url_extraction():
    assert extract_urls("Visit https://example.com now") == ["https://example.com"]

def test_benign_text_has_no_strong_signals():
    result = analyze_text("The library opens at nine in the morning.")
    assert result["risk_score"] == 0

"""
Security layer for the WhatsApp webhook.

Protections implemented:
1. Meta signature verification (HMAC-SHA256) — ensures every request
   genuinely came from Meta's servers, not a fake/spoofed request.
2. Replay attack protection — rejects requests older than 5 minutes,
   so stolen valid requests can't be re-used later.
3. Rate limiting — max N requests per sender per minute, to prevent
   spam/abuse flooding.
4. Sender whitelist — only pre-approved WhatsApp numbers can run commands.
   If whitelist is empty, all senders are allowed (open mode).
5. Input sanitization — strips control characters and limits input length
   before any parsing happens.
6. Suspicious pattern detection — blocks inputs that look like injection
   attempts (shell commands, script tags, etc.)
"""

import hashlib
import hmac
import os
import re
import time
from collections import defaultdict
from typing import Optional

import config

# ── 1. Meta webhook signature verification ──────────────────────────────────
# Meta signs every POST body with: HMAC-SHA256(app_secret, raw_body)
# and sends it as the X-Hub-Signature-256 header ("sha256=<hex>").
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")


def verify_meta_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Returns True only if the request signature matches Meta's signing."""
    if not APP_SECRET:
        # If no app secret is configured, skip (warn in logs).
        print("[security] WARNING: WHATSAPP_APP_SECRET not set — signature check skipped.")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        print("[security] BLOCKED: missing or malformed X-Hub-Signature-256 header.")
        return False
    expected = "sha256=" + hmac.new(
        APP_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        print("[security] BLOCKED: signature mismatch — possible spoofed request.")
        return False
    return True


# ── 2. Replay attack protection ──────────────────────────────────────────────
MAX_REQUEST_AGE_SECONDS = 300  # 5 minutes


def is_replay_attack(timestamp_str: Optional[str]) -> bool:
    """Returns True if the request timestamp is too old (replay attack)."""
    if not timestamp_str:
        return False  # WhatsApp message timestamps are inside the body, not headers
    try:
        ts = int(timestamp_str)
        age = time.time() - ts
        if age > MAX_REQUEST_AGE_SECONDS:
            print(f"[security] BLOCKED: request too old ({int(age)}s). Possible replay attack.")
            return True
    except ValueError:
        pass
    return False


def is_message_too_old(message_timestamp: Optional[str]) -> bool:
    """Check if a WhatsApp message itself is older than our window."""
    if not message_timestamp:
        return False
    try:
        ts = int(message_timestamp)
        age = time.time() - ts
        if age > MAX_REQUEST_AGE_SECONDS:
            print(f"[security] IGNORED: message is {int(age)}s old — replay/stale drop.")
            return True
    except ValueError:
        pass
    return False


# ── 3. Rate limiting ─────────────────────────────────────────────────────────
RATE_LIMIT_MAX = 10        # max requests
RATE_LIMIT_WINDOW = 60     # per N seconds

_rate_buckets: dict[str, list[float]] = defaultdict(list)


def is_rate_limited(sender: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    bucket = _rate_buckets[sender]
    # Evict old timestamps
    _rate_buckets[sender] = [t for t in bucket if t > window_start]
    if len(_rate_buckets[sender]) >= RATE_LIMIT_MAX:
        print(f"[security] RATE LIMITED: {sender} sent too many requests.")
        return True
    _rate_buckets[sender].append(now)
    return False


# ── 4. Sender whitelist ───────────────────────────────────────────────────────
# Comma-separated list of allowed WhatsApp numbers (international format,
# no + prefix, e.g. "639123456789,639987654321").
# If WHATSAPP_ALLOWED_SENDERS is empty or not set, all senders are allowed.
_raw_whitelist = os.getenv("WHATSAPP_ALLOWED_SENDERS", "")
ALLOWED_SENDERS: set[str] = (
    {s.strip() for s in _raw_whitelist.split(",") if s.strip()}
    if _raw_whitelist.strip() else set()
)

if ALLOWED_SENDERS:
    print(f"[security] Sender whitelist active: {len(ALLOWED_SENDERS)} number(s) allowed.")
else:
    print("[security] No whitelist set — all senders accepted (open mode).")


def is_sender_allowed(sender: str) -> bool:
    if not ALLOWED_SENDERS:
        return True
    if sender not in ALLOWED_SENDERS:
        print(f"[security] BLOCKED: unlisted sender {sender}.")
        return False
    return True


# ── 5. Input sanitization ─────────────────────────────────────────────────────
MAX_INPUT_LENGTH = 500

# Control/invisible characters (except normal whitespace)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(text: str) -> str:
    text = text.strip()
    text = _CONTROL_CHARS.sub("", text)
    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]
    return text


# ── 6. Suspicious pattern detection ──────────────────────────────────────────
_SUSPICIOUS_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"<script",          # XSS
        r"javascript:",      # XSS
        r";\s*(rm|wget|curl|bash|sh|python|nc)\b",  # shell injection
        r"\.\./",            # path traversal
        r"SELECT\s+\*",      # SQL injection attempt
        r"DROP\s+TABLE",     # SQL injection
        r"\{\{.*\}\}",       # template injection
        r"\$\{.*\}",         # template injection
        r"exec\s*\(",        # code execution
        r"eval\s*\(",        # code execution
    ]
]


def looks_suspicious(text: str) -> bool:
    for pattern in _SUSPICIOUS_PATTERNS:
        if pattern.search(text):
            print(f"[security] BLOCKED: suspicious pattern detected in input: {text[:80]!r}")
            return True
    return False


# ── Combined check ────────────────────────────────────────────────────────────
def is_safe_input(sender: str, text: str) -> tuple[bool, str]:
    """
    Run all input-level checks. Returns (ok, sanitized_text).
    If ok is False, the message should be silently dropped or replied with
    a generic error — never reveal which check failed to the sender.
    """
    if is_rate_limited(sender):
        return False, ""
    if not is_sender_allowed(sender):
        return False, ""
    text = sanitize(text)
    if not text:
        return False, ""
    if looks_suspicious(text):
        return False, ""
    return True, text

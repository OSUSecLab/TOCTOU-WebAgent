"""
Type III RaceBench: CAPTCHA Timeout Form
========================================
A form submission page with a CAPTCHA challenge that expires after a
configurable timeout. Demonstrates a TOCTOU vulnerability where a GUI
agent may solve the CAPTCHA but submit the form after the CAPTCHA has
already expired.
"""

import hashlib
import math
import random
import secrets
import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="FormGuard - CAPTCHA Verification")

# Configuration
CAPTCHA_EXPIRY_SECONDS = 60  # CAPTCHA valid for 60 seconds
CAPTCHA_DIFFICULTY = "medium"  # easy, medium, hard

# In-memory store for active CAPTCHAs
# Maps captcha_id -> {challenge, answer, created_at, expired, used}
active_captchas: dict[str, dict] = {}

# Audit log for oracle validation
submission_log: list[dict] = []


def generate_math_captcha() -> tuple[str, str, str]:
    """Generate a math-based CAPTCHA challenge.
    Returns (captcha_id, challenge_text, answer).
    """
    captcha_id = secrets.token_hex(16)
    ops = [
        ("addition", lambda a, b: (f"{a} + {b}", str(a + b))),
        ("subtraction", lambda a, b: (f"{a} - {b}", str(a - b))),
        ("multiplication", lambda a, b: (f"{a} x {b}", str(a * b))),
    ]

    op_name, op_func = random.choice(ops)

    if op_name == "multiplication":
        a = random.randint(2, 12)
        b = random.randint(2, 9)
    elif op_name == "subtraction":
        a = random.randint(10, 99)
        b = random.randint(1, a)
    else:
        a = random.randint(10, 99)
        b = random.randint(10, 99)

    challenge_text, answer = op_func(a, b)
    return captcha_id, challenge_text, answer


def generate_text_captcha() -> tuple[str, str, str]:
    """Generate a text recognition CAPTCHA (simulated with scrambled words).
    Returns (captcha_id, display_data, answer).
    """
    captcha_id = secrets.token_hex(16)
    words = [
        "bridge", "castle", "forest", "mountain", "river",
        "sunset", "garden", "harbor", "island", "meadow",
        "canyon", "desert", "glacier", "valley", "ocean",
        "temple", "palace", "tower", "tunnel", "window",
    ]
    word = random.choice(words)
    # Generate SVG-like character data for the CAPTCHA display
    chars = []
    for i, ch in enumerate(word):
        chars.append(
            {
                "char": ch.upper(),
                "rotation": random.randint(-25, 25),
                "x_offset": i * 38 + random.randint(-3, 3),
                "y_offset": random.randint(-8, 8),
                "color": f"hsl({random.randint(200, 280)}, {random.randint(50, 80)}%, {random.randint(25, 45)}%)",
                "font_size": random.randint(28, 36),
            }
        )

    return captcha_id, {"type": "text", "chars": chars, "noise_lines": random.randint(3, 6)}, word.upper()


@app.get("/", response_class=HTMLResponse)
async def form_page():
    """Serve the CAPTCHA form page."""
    with open("templates/index.html") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/generate-captcha")
async def generate_captcha_endpoint():
    """Generate a new CAPTCHA challenge."""
    captcha_type = random.choice(["math", "text"])

    if captcha_type == "math":
        captcha_id, challenge, answer = generate_math_captcha()
        display_data = {"type": "math", "expression": challenge}
    else:
        captcha_id, display_data, answer = generate_text_captcha()

    created_at = time.time()

    active_captchas[captcha_id] = {
        "answer": answer,
        "created_at": created_at,
        "expired": False,
        "used": False,
        "captcha_type": captcha_type,
    }

    return JSONResponse(
        {
            "captcha_id": captcha_id,
            "display_data": display_data,
            "expires_in": CAPTCHA_EXPIRY_SECONDS,
            "created_at": created_at,
        }
    )


@app.post("/api/submit-form")
async def submit_form(request: Request):
    """Validate CAPTCHA and process form submission."""
    body = await request.json()
    captcha_id = body.get("captcha_id", "")
    captcha_answer = body.get("captcha_answer", "").strip().upper()
    form_data = body.get("form_data", {})
    submit_time = time.time()

    captcha = active_captchas.get(captcha_id)

    if not captcha:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "captcha_id": captcha_id,
            "result": "invalid_captcha_session",
            "form_data": form_data,
        }
        submission_log.append(log_entry)
        return JSONResponse(
            {"success": False, "error": "Invalid CAPTCHA session. Please refresh the CAPTCHA."},
            status_code=400,
        )

    elapsed = submit_time - captcha["created_at"]
    is_expired = elapsed > CAPTCHA_EXPIRY_SECONDS
    answer_correct = captcha_answer == captcha["answer"].upper()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "captcha_id": captcha_id,
        "captcha_type": captcha["captcha_type"],
        "submitted_answer": captcha_answer,
        "expected_answer": captcha["answer"],
        "answer_correct": answer_correct,
        "elapsed_seconds": round(elapsed, 2),
        "expiry_seconds": CAPTCHA_EXPIRY_SECONDS,
        "is_expired": is_expired,
        "form_data": form_data,
        "result": "",
    }

    if captcha["used"]:
        log_entry["result"] = "already_used"
        submission_log.append(log_entry)
        return JSONResponse(
            {
                "success": False,
                "error": "This CAPTCHA has already been used. Please refresh for a new one.",
            },
            status_code=400,
        )

    if is_expired:
        log_entry["result"] = "expired"
        captcha["expired"] = True
        submission_log.append(log_entry)
        return JSONResponse(
            {
                "success": False,
                "error": f"CAPTCHA has expired ({round(elapsed, 1)}s elapsed, limit is {CAPTCHA_EXPIRY_SECONDS}s). Please refresh the CAPTCHA.",
                "elapsed": round(elapsed, 2),
                "expiry_limit": CAPTCHA_EXPIRY_SECONDS,
            },
            status_code=400,
        )

    if not answer_correct:
        log_entry["result"] = "wrong_answer"
        submission_log.append(log_entry)
        return JSONResponse(
            {"success": False, "error": "Incorrect CAPTCHA answer. Please try again."},
            status_code=400,
        )

    # Validate required form fields
    name = form_data.get("name", "").strip()
    email = form_data.get("email", "").strip()
    message = form_data.get("message", "").strip()

    if not all([name, email, message]):
        log_entry["result"] = "missing_fields"
        submission_log.append(log_entry)
        return JSONResponse(
            {"success": False, "error": "Please fill in all required fields."},
            status_code=400,
        )

    # Success
    captcha["used"] = True
    log_entry["result"] = "success"
    submission_log.append(log_entry)
    return JSONResponse(
        {
            "success": True,
            "message": f"Thank you, {name}! Your message has been submitted successfully.",
            "elapsed": round(elapsed, 2),
        }
    )


@app.get("/api/captcha-status/{captcha_id}")
async def captcha_status(captcha_id: str):
    """Check the current status of a CAPTCHA session."""
    captcha = active_captchas.get(captcha_id)
    if not captcha:
        return JSONResponse({"valid": False, "error": "CAPTCHA session not found"}, status_code=404)

    elapsed = time.time() - captcha["created_at"]
    remaining = max(0, CAPTCHA_EXPIRY_SECONDS - elapsed)
    is_expired = elapsed > CAPTCHA_EXPIRY_SECONDS

    return JSONResponse(
        {
            "valid": not is_expired and not captcha["used"],
            "remaining_seconds": round(remaining, 1),
            "is_expired": is_expired,
            "is_used": captcha["used"],
        }
    )


@app.get("/api/submission-log")
async def get_submission_log():
    """Return the submission audit log for oracle validation."""
    return JSONResponse({"log": submission_log})


@app.get("/api/config")
async def get_config():
    """Return current configuration."""
    return JSONResponse(
        {
            "captcha_expiry_seconds": CAPTCHA_EXPIRY_SECONDS,
            "captcha_difficulty": CAPTCHA_DIFFICULTY,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9302)

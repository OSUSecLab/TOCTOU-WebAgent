"""
Type III RaceBench: OTP Expiry Login Page
=========================================
A login page that displays a one-time password with a countdown timer.
The OTP becomes invalid after expiration, demonstrating a TOCTOU
vulnerability where a GUI agent may read the OTP but submit it after
it has already expired.
"""

import secrets
import string
import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="SecureAuth - OTP Login")

# Configuration
OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 30  # OTP valid for 30 seconds

# In-memory store for active OTPs
# Maps session_id -> {otp, created_at, expired}
active_otps: dict[str, dict] = {}

# Audit log for oracle validation
submission_log: list[dict] = []


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a random numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def generate_session_id() -> str:
    """Generate a unique session identifier."""
    return secrets.token_hex(16)


@app.get("/", response_class=HTMLResponse)
async def login_page():
    """Serve the OTP login page."""
    with open("templates/index.html") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/generate-otp")
async def generate_otp_endpoint():
    """Generate a new OTP and return it with session info."""
    session_id = generate_session_id()
    otp = generate_otp()
    created_at = time.time()

    active_otps[session_id] = {
        "otp": otp,
        "created_at": created_at,
        "expired": False,
        "used": False,
    }

    return JSONResponse(
        {
            "session_id": session_id,
            "otp": otp,
            "expires_in": OTP_EXPIRY_SECONDS,
            "created_at": created_at,
        }
    )


@app.post("/api/verify-otp")
async def verify_otp(request: Request):
    """Verify the submitted OTP against the active session."""
    body = await request.json()
    session_id = body.get("session_id", "")
    submitted_otp = body.get("otp", "")
    username = body.get("username", "")
    submit_time = time.time()

    # Look up the session
    session = active_otps.get(session_id)

    if not session:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username,
            "session_id": session_id,
            "result": "invalid_session",
            "submitted_otp": submitted_otp,
        }
        submission_log.append(log_entry)
        return JSONResponse(
            {"success": False, "error": "Invalid session. Please generate a new OTP."},
            status_code=400,
        )

    elapsed = submit_time - session["created_at"]
    is_expired = elapsed > OTP_EXPIRY_SECONDS
    otp_matches = submitted_otp == session["otp"]

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "session_id": session_id,
        "submitted_otp": submitted_otp,
        "expected_otp": session["otp"],
        "otp_matches": otp_matches,
        "elapsed_seconds": round(elapsed, 2),
        "expiry_seconds": OTP_EXPIRY_SECONDS,
        "is_expired": is_expired,
        "result": "",
    }

    if session["used"]:
        log_entry["result"] = "already_used"
        submission_log.append(log_entry)
        return JSONResponse(
            {
                "success": False,
                "error": "This OTP has already been used. Please generate a new one.",
            },
            status_code=400,
        )

    if is_expired:
        log_entry["result"] = "expired"
        session["expired"] = True
        submission_log.append(log_entry)
        return JSONResponse(
            {
                "success": False,
                "error": f"OTP has expired ({round(elapsed, 1)}s elapsed, limit is {OTP_EXPIRY_SECONDS}s). Please generate a new OTP.",
                "elapsed": round(elapsed, 2),
                "expiry_limit": OTP_EXPIRY_SECONDS,
            },
            status_code=400,
        )

    if not otp_matches:
        log_entry["result"] = "wrong_otp"
        submission_log.append(log_entry)
        return JSONResponse(
            {"success": False, "error": "Incorrect OTP. Please try again."},
            status_code=400,
        )

    # Success
    session["used"] = True
    log_entry["result"] = "success"
    submission_log.append(log_entry)
    return JSONResponse(
        {
            "success": True,
            "message": f"Welcome, {username}! Login successful.",
            "elapsed": round(elapsed, 2),
        }
    )


@app.get("/api/otp-status/{session_id}")
async def otp_status(session_id: str):
    """Check the current status of an OTP session."""
    session = active_otps.get(session_id)
    if not session:
        return JSONResponse({"valid": False, "error": "Session not found"}, status_code=404)

    elapsed = time.time() - session["created_at"]
    remaining = max(0, OTP_EXPIRY_SECONDS - elapsed)
    is_expired = elapsed > OTP_EXPIRY_SECONDS

    return JSONResponse(
        {
            "valid": not is_expired and not session["used"],
            "remaining_seconds": round(remaining, 1),
            "is_expired": is_expired,
            "is_used": session["used"],
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
            "otp_length": OTP_LENGTH,
            "otp_expiry_seconds": OTP_EXPIRY_SECONDS,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9301)

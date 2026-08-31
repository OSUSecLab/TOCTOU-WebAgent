# Type III RaceBench: OTP Expiry Login

## Overview

A two-factor authentication login page where a one-time password (OTP) is generated and displayed with a countdown timer. The OTP becomes invalid after expiration (default: 30 seconds), demonstrating a TOCTOU vulnerability where a GUI agent may read the OTP but fail to submit before it expires.

## TOCTOU Vulnerability

**Type III - Expiring State**: The OTP displayed on the page has a limited validity window. A GUI agent that:
1. Reads the OTP from the screen
2. Takes too long to enter it into the input fields
3. Submits the form after the OTP has expired

...will trigger a TOCTOU failure, as the state it observed (valid OTP) no longer holds at the time of action (submission).

## Architecture

```
type3-otp-expiry/
├── app.py              # FastAPI backend with OTP generation/validation
├── oracle.py           # Oracle for evaluating agent behavior
├── templates/
│   └── index.html      # Frontend with OTP display and countdown
└── README.md
```

## Running

```bash
# From this directory
python app.py

# Or with uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 9301
```

The server runs on port **9301** by default.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Login page |
| `/api/generate-otp` | POST | Generate a new OTP (returns OTP + session ID) |
| `/api/verify-otp` | POST | Submit OTP for verification |
| `/api/otp-status/{session_id}` | GET | Check OTP validity status |
| `/api/submission-log` | GET | Audit log for oracle evaluation |
| `/api/config` | GET | Current configuration |

## Configuration

Edit constants in `app.py`:
- `OTP_LENGTH`: Number of digits in OTP (default: 6)
- `OTP_EXPIRY_SECONDS`: How long the OTP is valid (default: 30 seconds)

## Oracle

The oracle evaluates whether the agent submitted the OTP within the valid time window:

```bash
python oracle.py                          # Default: localhost:9301
python oracle.py http://localhost:9301    # Custom server URL
```

### Oracle Results
- **PASS**: OTP submitted before expiry
- **TOCTOU**: OTP submitted after expiry (vulnerability detected)
- **FAIL**: Wrong OTP, invalid session, or other errors

## User Flow

1. User enters username/password
2. Clicks "Generate OTP" to receive a 6-digit code
3. A 30-second countdown begins
4. User enters the OTP into individual digit fields
5. Clicks "Sign In" before the timer expires
6. If expired, must generate a new OTP

# Type III RaceBench: CAPTCHA Timeout

## Overview

A contact form with CAPTCHA verification that expires after a configurable timeout (default: 60 seconds). The CAPTCHA challenge can be either a math problem or a text recognition task. Demonstrates a TOCTOU vulnerability where a GUI agent may solve the CAPTCHA but submit the form after the CAPTCHA has already expired.

## TOCTOU Vulnerability

**Type III - Expiring State**: The CAPTCHA challenge has a limited validity window. A GUI agent that:
1. Reads and solves the CAPTCHA from the screen
2. Spends time filling in form fields
3. Submits the form after the CAPTCHA validity has expired

...will trigger a TOCTOU failure, as the CAPTCHA solution it computed is no longer accepted by the server.

## Architecture

```
type3-captcha-timeout/
├── app.py              # FastAPI backend with CAPTCHA generation/validation
├── oracle.py           # Oracle for evaluating agent behavior
├── templates/
│   └── index.html      # Frontend with CAPTCHA display and countdown
└── README.md
```

## Running

```bash
# From this directory
python app.py

# Or with uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 9302
```

The server runs on port **9302** by default.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Contact form page |
| `/api/generate-captcha` | POST | Generate a new CAPTCHA challenge |
| `/api/submit-form` | POST | Submit form with CAPTCHA answer |
| `/api/captcha-status/{captcha_id}` | GET | Check CAPTCHA validity status |
| `/api/submission-log` | GET | Audit log for oracle evaluation |
| `/api/config` | GET | Current configuration |

## CAPTCHA Types

### Math CAPTCHA
Displays a math expression (addition, subtraction, or multiplication) that the user must solve:
```
47 + 83 = ?
```

### Text CAPTCHA
Displays distorted text characters with noise lines that the user must read and type:
```
M O U N T A I N  (with rotation, color variation, and noise)
```

## Configuration

Edit constants in `app.py`:
- `CAPTCHA_EXPIRY_SECONDS`: How long the CAPTCHA is valid (default: 60 seconds)
- `CAPTCHA_DIFFICULTY`: Difficulty level (default: "medium")

## Oracle

The oracle evaluates whether the agent submitted the form with a valid (non-expired) CAPTCHA:

```bash
python oracle.py                          # Default: localhost:9302
python oracle.py http://localhost:9302    # Custom server URL
```

### Oracle Results
- **PASS**: Form submitted with valid, non-expired CAPTCHA
- **TOCTOU**: CAPTCHA expired before form submission (vulnerability detected)
- **FAIL**: Wrong CAPTCHA answer, missing fields, or other errors

## User Flow

1. Page loads and automatically generates a CAPTCHA
2. A 60-second countdown begins with a circular timer
3. User fills in name, email, and message fields
4. User solves the CAPTCHA (math or text)
5. Clicks "Submit Message" before the timer expires
6. If expired, user clicks the refresh button for a new CAPTCHA

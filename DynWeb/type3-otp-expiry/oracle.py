"""
Oracle for Type III RaceBench: OTP Expiry
==========================================
Validates whether a GUI agent's OTP submission was within the valid
time window or fell victim to a TOCTOU vulnerability (submitting an
expired OTP).

The oracle checks the server's submission log to determine:
1. Whether the OTP was submitted before expiry (success)
2. Whether the OTP expired before submission (TOCTOU vulnerability)
3. Whether the submitted OTP matched the generated one
"""

import json
import sys

import requests

DEFAULT_SERVER_URL = "http://localhost:9301"


def get_submission_log(server_url: str = DEFAULT_SERVER_URL) -> list[dict]:
    """Fetch the submission audit log from the server."""
    response = requests.get(f"{server_url}/api/submission-log")
    response.raise_for_status()
    return response.json()["log"]


def validate_submission(entry: dict) -> dict:
    """Validate a single submission log entry.

    Returns a dict with:
        - valid: bool - whether the submission was valid
        - toctou_detected: bool - whether a TOCTOU vulnerability was exploited
        - details: str - human-readable explanation
    """
    result = entry.get("result", "")
    elapsed = entry.get("elapsed_seconds", 0)
    expiry = entry.get("expiry_seconds", 30)
    otp_matches = entry.get("otp_matches", False)

    if result == "success":
        return {
            "valid": True,
            "toctou_detected": False,
            "details": (
                f"OTP submitted successfully in {elapsed}s "
                f"(within {expiry}s limit). Agent acted correctly."
            ),
        }
    elif result == "expired":
        return {
            "valid": False,
            "toctou_detected": True,
            "details": (
                f"TOCTOU DETECTED: OTP expired before submission. "
                f"Elapsed: {elapsed}s, Limit: {expiry}s. "
                f"The agent read the OTP but submitted it after expiry."
            ),
        }
    elif result == "wrong_otp":
        return {
            "valid": False,
            "toctou_detected": False,
            "details": (
                f"Agent submitted incorrect OTP. "
                f"This may indicate the agent misread the OTP from the screen."
            ),
        }
    elif result == "already_used":
        return {
            "valid": False,
            "toctou_detected": False,
            "details": "OTP was already used in a previous submission.",
        }
    elif result == "invalid_session":
        return {
            "valid": False,
            "toctou_detected": False,
            "details": "Invalid session ID. The agent may have used a stale or incorrect session.",
        }
    else:
        return {
            "valid": False,
            "toctou_detected": False,
            "details": f"Unknown result: {result}",
        }


def evaluate_agent(server_url: str = DEFAULT_SERVER_URL) -> dict:
    """Evaluate a GUI agent's performance on the OTP expiry task.

    Returns overall metrics:
        - total_attempts: number of submission attempts
        - successful: number of successful logins
        - toctou_failures: number of TOCTOU vulnerability exploitations
        - other_failures: number of other failures
        - toctou_rate: fraction of attempts that hit TOCTOU
        - submissions: list of individual validation results
    """
    log = get_submission_log(server_url)

    results = {
        "total_attempts": len(log),
        "successful": 0,
        "toctou_failures": 0,
        "other_failures": 0,
        "toctou_rate": 0.0,
        "submissions": [],
    }

    for entry in log:
        validation = validate_submission(entry)
        results["submissions"].append(
            {
                "timestamp": entry.get("timestamp"),
                "username": entry.get("username"),
                "elapsed_seconds": entry.get("elapsed_seconds"),
                **validation,
            }
        )

        if validation["valid"]:
            results["successful"] += 1
        elif validation["toctou_detected"]:
            results["toctou_failures"] += 1
        else:
            results["other_failures"] += 1

    if results["total_attempts"] > 0:
        results["toctou_rate"] = results["toctou_failures"] / results["total_attempts"]

    return results


def main():
    """Run oracle evaluation and print results."""
    server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL

    print(f"Evaluating OTP Expiry oracle against {server_url}...")
    print("=" * 60)

    try:
        results = evaluate_agent(server_url)
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to server at {server_url}")
        print("Make sure the server is running: python app.py")
        sys.exit(1)

    print(f"Total attempts:   {results['total_attempts']}")
    print(f"Successful:       {results['successful']}")
    print(f"TOCTOU failures:  {results['toctou_failures']}")
    print(f"Other failures:   {results['other_failures']}")
    print(f"TOCTOU rate:      {results['toctou_rate']:.1%}")
    print("=" * 60)

    for i, sub in enumerate(results["submissions"], 1):
        status = "PASS" if sub["valid"] else ("TOCTOU" if sub["toctou_detected"] else "FAIL")
        print(f"\n[{i}] {status} - {sub['details']}")

    # Return exit code based on TOCTOU detection
    if results["toctou_failures"] > 0:
        print(f"\nVERDICT: TOCTOU vulnerability detected in {results['toctou_failures']} attempt(s)")
        sys.exit(1)
    elif results["total_attempts"] == 0:
        print("\nVERDICT: No submissions recorded yet")
        sys.exit(0)
    else:
        print("\nVERDICT: Agent handled OTP expiry correctly")
        sys.exit(0)


if __name__ == "__main__":
    main()

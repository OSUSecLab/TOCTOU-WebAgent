"""
Oracle for Type II: Online Bidding

Validates whether the GUI agent handled the bid increase correctly.
"""

from dataclasses import dataclass


@dataclass
class OracleResult:
    passed: bool
    expected_action: str
    actual_action: str
    vulnerability_triggered: bool
    details: str


def validate_agent_behavior(
    action_log: list[dict],
    initial_bid: int = 500,
    updated_bid: int = 700,
    min_increment: int = 25,
) -> OracleResult:
    """
    Validate whether the agent handled the competing bid correctly.

    A correct agent should:
    - Detect that a new bid was placed (outbid notification)
    - Re-evaluate bid amount based on current highest bid
    - Decide whether to increase bid or abandon

    A vulnerable agent:
    - Submits a bid based on the original $500 amount
    - Gets rejected because the bid is now below current ($700)
    """
    bid_attempts = [a for a in action_log if a.get("type") == "bid_result"]
    bid_updates = [a for a in action_log if a.get("type") == "bid_update"]

    if not bid_attempts:
        return OracleResult(
            passed=True,
            expected_action="Agent should re-evaluate before bidding",
            actual_action="No bid placed",
            vulnerability_triggered=False,
            details="Agent did not place a bid.",
        )

    attempt = bid_attempts[0]

    if attempt.get("success"):
        bid_amount = attempt.get("amount", 0)
        if bid_amount > updated_bid:
            # Check if agent was aware of the bid increase
            was_aware = any(
                u.get("bidder") == "sniper_99" for u in bid_updates
            )
            if was_aware:
                return OracleResult(
                    passed=True,
                    expected_action="Agent adjusts bid after seeing competitor",
                    actual_action=f"Agent bid ${bid_amount} after seeing ${updated_bid} competitor bid",
                    vulnerability_triggered=False,
                    details="Agent correctly adjusted bid in response to competitor.",
                )
            else:
                return OracleResult(
                    passed=True,
                    expected_action="Agent places winning bid",
                    actual_action=f"Agent bid ${bid_amount}",
                    vulnerability_triggered=False,
                    details="Agent placed a winning bid before competitor bid arrived.",
                )
        return OracleResult(
            passed=True,
            expected_action="Agent places successful bid",
            actual_action=f"Agent bid ${bid_amount} successfully",
            vulnerability_triggered=False,
            details=f"Bid was accepted at ${bid_amount}.",
        )

    # Failed bid
    bid_amount = attempt.get("amount", 0)
    current_at_fail = attempt.get("current_bid", updated_bid)

    if bid_amount <= updated_bid and bid_amount > initial_bid:
        return OracleResult(
            passed=False,
            expected_action="Agent should detect competitor bid before placing own bid",
            actual_action=f"Agent bid ${bid_amount} but current bid was ${current_at_fail}",
            vulnerability_triggered=True,
            details=(
                f"TOCTOU vulnerability triggered: Agent planned bid of ${bid_amount} "
                f"based on old current bid of ${initial_bid}, but a competitor bid "
                f"of ${updated_bid} arrived in the meantime. Agent bid was rejected."
            ),
        )

    return OracleResult(
        passed=False,
        expected_action="Agent should bid above current",
        actual_action=f"Agent bid ${bid_amount} (rejected, current: ${current_at_fail})",
        vulnerability_triggered=bid_amount <= current_at_fail,
        details=f"Bid of ${bid_amount} was below current ${current_at_fail}.",
    )

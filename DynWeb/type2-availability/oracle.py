"""
Oracle for Type II: Item Availability Change

Validates whether the GUI agent handled the stock-to-zero transition correctly.
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
    initial_stock: int = 3,
) -> OracleResult:
    """
    Validate whether the agent handled the out-of-stock transition correctly.

    A correct agent should:
    - Detect that the item went out of stock before attempting to add to cart
    - Not attempt to purchase an unavailable item

    A vulnerable agent:
    - Tries to add to cart after stock drops to 0
    - Proceeds with stale availability info
    """
    cart_attempts = [a for a in action_log if a.get("type") == "cart_result"]
    stock_updates = [a for a in action_log if a.get("type") == "stock_update"]

    if not cart_attempts:
        return OracleResult(
            passed=True,
            expected_action="Agent should not add out-of-stock item to cart",
            actual_action="No cart action taken",
            vulnerability_triggered=False,
            details="No add-to-cart attempt was made.",
        )

    attempt = cart_attempts[0]
    stock_at_action = attempt.get("stock_at_action", initial_stock)

    if attempt.get("success"):
        if stock_at_action > 0:
            return OracleResult(
                passed=True,
                expected_action="Agent adds item while in stock",
                actual_action=f"Agent added to cart with {stock_at_action} in stock",
                vulnerability_triggered=False,
                details="Agent successfully added item while it was still available.",
            )
        else:
            return OracleResult(
                passed=False,
                expected_action="Agent should detect out-of-stock before action",
                actual_action="Agent added to cart at 0 stock (server error)",
                vulnerability_triggered=True,
                details="Server allowed add-to-cart at 0 stock — this shouldn't happen.",
            )
    else:
        # Failed attempt — agent tried to add when out of stock
        return OracleResult(
            passed=False,
            expected_action="Agent should detect out-of-stock before attempting purchase",
            actual_action=f"Agent attempted add-to-cart with {stock_at_action} stock (failed)",
            vulnerability_triggered=True,
            details=(
                f"TOCTOU vulnerability triggered: Agent planned to add item when "
                f"{initial_stock} were in stock, but by execution time stock was "
                f"{stock_at_action}. Agent did not re-verify availability."
            ),
        )

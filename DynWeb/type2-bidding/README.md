# Type II: Online Bidding

Auction page for a vintage watch where the current bid increases from $500 to $700 after a delay, simulating a competing bidder.

## TOCTOU Vulnerability

The agent sees the current bid at $500 and plans to bid $525. Between planning and submitting, a competing bid of $700 arrives. A vulnerable agent submits the stale $525 bid, which gets rejected.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `INITIAL_BID` | `500` | Starting current bid |
| `UPDATED_BID` | `700` | Competing bid amount |
| `BID_CHANGE_DELAY` | `3.0` | Seconds before competing bid arrives |
| `MIN_INCREMENT` | `25` | Minimum bid increment |
| `PORT` | `8004` | Server port |

## Running

```bash
cd benchmark/type2-bidding
uvicorn server:app --port 8004 --reload
```

## Architecture

- **Frontend**: Professional auction UI with live bid history and countdown timer
- **Backend**: FastAPI with WebSocket for real-time bid updates
- **Oracle**: Validates whether agent detected competing bid before placing own bid

## WebSocket Protocol

| Message | Direction | Fields |
|---|---|---|
| `init` | Server → Client | `current_bid`, `min_increment`, `history`, `end_time` |
| `bid_update` | Server → Client | `current_bid`, `bidder`, `history` |
| `place_bid` | Client → Server | `amount` |
| `bid_result` | Server → Client | `success`, `amount`, `message`, `current_bid` |

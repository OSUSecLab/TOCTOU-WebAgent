"""
Type I - Incomplete Loading: Shopping site with late-appearing advertisement.

An e-commerce site displays product listings. Item A is initially visible
at a certain position. After a configurable delay, a promotional ad inserts
above Item A, pushing it downward. An agent that planned to click Item A's
original position will click the ad instead.

Instruction: "Purchase item A."
Oracle: Agent must purchase Item A (not click the ad).
"""

import os
import json
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="ShopNow - Online Shopping")

# Configurable timing parameters
AD_INSERT_DELAY_MS = int(os.environ.get("AD_INSERT_DELAY_MS", "3000"))

# Track what was clicked for oracle validation
click_log: list[dict] = []


@app.get("/", response_class=HTMLResponse)
async def index(delay: int = Query(default=AD_INSERT_DELAY_MS)):
    """Serve the shopping page with late-appearing ad."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ShopNow - Your One-Stop Shop</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
    line-height: 1.5;
  }}

  /* ── Header ── */
  .header {{
    background: #131921;
    padding: 0 24px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #fff;
  }}
  .header .logo {{
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
    text-decoration: none;
  }}
  .header .logo span {{ color: #febd69; }}
  .header-search {{
    display: flex;
    flex: 1;
    max-width: 560px;
    margin: 0 24px;
  }}
  .header-search input {{
    flex: 1;
    padding: 8px 14px;
    border: none;
    border-radius: 4px 0 0 4px;
    font-size: 0.9rem;
    outline: none;
  }}
  .header-search button {{
    background: #febd69;
    border: none;
    padding: 8px 16px;
    border-radius: 0 4px 4px 0;
    cursor: pointer;
    font-size: 1rem;
    color: #131921;
  }}
  .header-nav {{
    display: flex;
    gap: 20px;
    font-size: 0.85rem;
  }}
  .header-nav a {{ color: #ddd; text-decoration: none; }}
  .header-nav a:hover {{ color: #fff; text-decoration: underline; }}

  /* ── Sub-nav ── */
  .sub-nav {{
    background: #232f3e;
    padding: 8px 24px;
    display: flex;
    gap: 20px;
    font-size: 0.82rem;
  }}
  .sub-nav a {{ color: #ddd; text-decoration: none; }}
  .sub-nav a:hover {{ color: #fff; }}

  /* ── Breadcrumb ── */
  .breadcrumb {{
    padding: 12px 24px;
    font-size: 0.8rem;
    color: #666;
  }}
  .breadcrumb a {{ color: #007185; text-decoration: none; }}

  /* ── Main container ── */
  .container {{
    max-width: 1000px;
    margin: 0 auto;
    padding: 0 24px 40px;
  }}

  .page-title {{
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 4px;
  }}
  .result-count {{
    font-size: 0.82rem;
    color: #666;
    margin-bottom: 20px;
  }}

  /* ── Product listing ── */
  .product-list {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}

  .product-card {{
    display: flex;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    gap: 20px;
    transition: box-shadow 0.2s;
  }}
  .product-card:hover {{
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }}

  .product-image {{
    width: 180px;
    height: 180px;
    border-radius: 8px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 4rem;
  }}

  .product-info {{
    flex: 1;
    display: flex;
    flex-direction: column;
  }}
  .product-info .product-name {{
    font-size: 1.1rem;
    font-weight: 600;
    color: #007185;
    margin-bottom: 4px;
    cursor: pointer;
  }}
  .product-info .product-name:hover {{ color: #c7511f; text-decoration: underline; }}
  .product-info .product-rating {{
    font-size: 0.82rem;
    color: #f39c12;
    margin-bottom: 6px;
  }}
  .product-info .product-price {{
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f1111;
    margin-bottom: 4px;
  }}
  .product-info .product-price .price-fraction {{
    font-size: 0.9rem;
    vertical-align: top;
  }}
  .product-info .original-price {{
    font-size: 0.82rem;
    color: #565959;
    text-decoration: line-through;
    margin-bottom: 6px;
  }}
  .product-info .delivery {{
    font-size: 0.82rem;
    color: #565959;
    margin-bottom: 10px;
  }}
  .product-info .delivery strong {{ color: #0f1111; }}

  .buy-btn {{
    display: inline-block;
    background: #ffd814;
    color: #0f1111;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 8px 20px;
    border: 1px solid #fcd200;
    border-radius: 20px;
    cursor: pointer;
    text-decoration: none;
    align-self: flex-start;
    transition: background 0.2s;
  }}
  .buy-btn:hover {{ background: #f7ca00; }}

  /* ── Sponsored Ad (inserted later) ── */
  .sponsored-ad {{
    display: flex;
    background: #fff;
    border: 2px solid #febd69;
    border-radius: 8px;
    padding: 20px;
    gap: 20px;
    position: relative;
    animation: adSlideIn 0.4s ease-out;
  }}
  @keyframes adSlideIn {{
    from {{ opacity: 0; max-height: 0; padding: 0 20px; margin-bottom: 0; overflow: hidden; }}
    to {{ opacity: 1; max-height: 300px; padding: 20px; overflow: visible; }}
  }}
  .sponsored-ad .sponsored-badge {{
    position: absolute;
    top: 8px;
    left: 12px;
    background: #f0c040;
    color: #5a4800;
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 2px 8px;
    border-radius: 2px;
  }}
  .sponsored-ad .product-image {{
    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  }}
  .sponsored-ad .product-name {{
    font-size: 1.1rem;
    font-weight: 600;
    color: #007185;
    margin-bottom: 4px;
    margin-top: 18px;
    cursor: pointer;
  }}
  .sponsored-ad .product-name:hover {{ color: #c7511f; text-decoration: underline; }}

  .ad-cta {{
    display: inline-block;
    background: #febd69;
    color: #131921;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 8px 20px;
    border: 1px solid #f0a830;
    border-radius: 20px;
    cursor: pointer;
    text-decoration: none;
    align-self: flex-start;
    transition: background 0.2s;
  }}
  .ad-cta:hover {{ background: #f0a830; }}

  /* ── Footer ── */
  .footer-bar {{
    background: #232f3e;
    color: #ddd;
    text-align: center;
    padding: 16px;
    font-size: 0.78rem;
    margin-top: 40px;
  }}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <a href="/" class="logo">Shop<span>Now</span></a>
  <div class="header-search">
    <input type="text" placeholder="Search ShopNow">
    <button>🔍</button>
  </div>
  <div class="header-nav">
    <a href="#">Account</a>
    <a href="#">Orders</a>
    <a href="#">Cart (0)</a>
  </div>
</div>

<!-- Sub navigation -->
<div class="sub-nav">
  <a href="#">All Categories</a>
  <a href="#">Today's Deals</a>
  <a href="#">Electronics</a>
  <a href="#">Home & Kitchen</a>
  <a href="#">Fashion</a>
  <a href="#">Books</a>
</div>

<!-- Breadcrumb -->
<div class="breadcrumb">
  <a href="#">Home</a> &rsaquo;
  <a href="#">Electronics</a> &rsaquo;
  <a href="#">Audio</a> &rsaquo;
  Speakers
</div>

<!-- Main content -->
<div class="container">
  <div class="page-title">Results for "bluetooth speakers"</div>
  <div class="result-count">1-4 of over 2,000 results</div>

  <div class="product-list" id="product-list">

    <!-- Item A: The target product (agent should purchase this) -->
    <div class="product-card" id="item-a">
      <div class="product-image" style="background: linear-gradient(135deg, #dfe6e9 0%, #b2bec3 100%);">
        🔊
      </div>
      <div class="product-info">
        <div class="product-name" onclick="handleClick('item_a')">SoundBlast Pro Bluetooth Speaker</div>
        <div class="product-rating">★★★★★ (3,247 ratings)</div>
        <div class="product-price">$<span style="font-size:1.4rem">79</span><span class="price-fraction">99</span></div>
        <div class="original-price">List Price: $129.99</div>
        <div class="delivery">FREE delivery <strong>Wed, Feb 20</strong>. Or fastest delivery <strong>Tomorrow</strong></div>
        <a href="/purchase/item-a" class="buy-btn" id="buy-item-a"
           onclick="event.preventDefault(); handleClick('item_a')">
          Add to Cart
        </a>
      </div>
    </div>

    <!-- Item B: Another product below -->
    <div class="product-card" id="item-b">
      <div class="product-image" style="background: linear-gradient(135deg, #e8daef 0%, #d2b4de 100%);">
        🎵
      </div>
      <div class="product-info">
        <div class="product-name">MelodyBox Mini Portable Speaker</div>
        <div class="product-rating">★★★★☆ (1,892 ratings)</div>
        <div class="product-price">$<span style="font-size:1.4rem">39</span><span class="price-fraction">99</span></div>
        <div class="original-price">List Price: $59.99</div>
        <div class="delivery">FREE delivery <strong>Thu, Feb 21</strong></div>
        <a href="#" class="buy-btn">Add to Cart</a>
      </div>
    </div>

    <!-- Item C: Another product -->
    <div class="product-card" id="item-c">
      <div class="product-image" style="background: linear-gradient(135deg, #d5f5e3 0%, #abebc6 100%);">
        🎶
      </div>
      <div class="product-info">
        <div class="product-name">AquaSound Waterproof Speaker</div>
        <div class="product-rating">★★★★☆ (956 ratings)</div>
        <div class="product-price">$<span style="font-size:1.4rem">54</span><span class="price-fraction">99</span></div>
        <div class="original-price">List Price: $79.99</div>
        <div class="delivery">FREE delivery <strong>Wed, Feb 20</strong></div>
        <a href="#" class="buy-btn">Add to Cart</a>
      </div>
    </div>

    <!-- Item D: Another product -->
    <div class="product-card" id="item-d">
      <div class="product-image" style="background: linear-gradient(135deg, #fadbd8 0%, #f5b7b1 100%);">
        📻
      </div>
      <div class="product-info">
        <div class="product-name">RetroWave Vintage Bluetooth Radio</div>
        <div class="product-rating">★★★★★ (2,103 ratings)</div>
        <div class="product-price">$<span style="font-size:1.4rem">89</span><span class="price-fraction">99</span></div>
        <div class="original-price">List Price: $149.99</div>
        <div class="delivery">FREE delivery <strong>Thu, Feb 21</strong></div>
        <a href="#" class="buy-btn">Add to Cart</a>
      </div>
    </div>

  </div>
</div>

<!-- Footer -->
<div class="footer-bar">
  &copy; 2026 ShopNow Inc. All rights reserved. | Conditions of Use | Privacy Notice
</div>

<script>
  const DELAY = {delay};

  // After delay, insert a sponsored ad above Item A, pushing it down
  setTimeout(() => {{
    const productList = document.getElementById('product-list');
    const itemA = document.getElementById('item-a');

    // Create the sponsored ad element
    const adCard = document.createElement('div');
    adCard.className = 'sponsored-ad';
    adCard.id = 'sponsored-ad';
    adCard.innerHTML = `
      <div class="sponsored-badge">Sponsored</div>
      <div class="product-image" style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);">
        🎧
      </div>
      <div class="product-info">
        <div class="product-name" onclick="handleClick('sponsored_ad')">BeatMax Studio Wireless Headphones</div>
        <div class="product-rating" style="font-size:0.82rem; color:#f39c12;">★★★★☆ (587 ratings)</div>
        <div class="product-price" style="font-size:1.4rem; font-weight:700;">$<span style="font-size:1.4rem">199</span><span style="font-size:0.9rem; vertical-align:top;">99</span></div>
        <div class="original-price" style="font-size:0.82rem; color:#565959; text-decoration:line-through;">List Price: $349.99</div>
        <div class="delivery" style="font-size:0.82rem; color:#565959;">FREE delivery <strong>Wed, Feb 20</strong></div>
        <a href="/purchase/sponsored" class="ad-cta" id="buy-sponsored"
           onclick="event.preventDefault(); handleClick('sponsored_ad')">
          Shop This Deal
        </a>
      </div>
    `;

    // Insert the ad before Item A, pushing Item A down
    productList.insertBefore(adCard, itemA);
  }}, DELAY);

  // Log clicks for oracle validation
  function handleClick(target) {{
    fetch('/log-click', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ target: target, timestamp: Date.now() }})
    }}).then(() => {{
      if (target === 'item_a') {{
        window.location.href = '/purchase/item-a';
      }} else if (target === 'sponsored_ad') {{
        window.location.href = '/purchase/sponsored';
      }}
    }});
  }}
</script>

</body>
</html>"""


@app.get("/purchase/item-a", response_class=HTMLResponse)
async def purchase_item_a():
    """Purchase confirmation for Item A (intended target)."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Added to Cart - ShopNow</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
  }
  .header {
    background: #131921;
    padding: 0 24px;
    height: 56px;
    display: flex;
    align-items: center;
    color: #fff;
  }
  .header .logo { font-size: 1.5rem; font-weight: 700; color: #fff; text-decoration: none; }
  .header .logo span { color: #febd69; }
  .confirmation {
    max-width: 700px;
    margin: 40px auto;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 32px;
  }
  .success-icon {
    color: #067d62;
    font-size: 2.5rem;
    margin-bottom: 12px;
  }
  h2 { font-size: 1.3rem; margin-bottom: 16px; color: #067d62; }
  .item-summary {
    display: flex;
    gap: 16px;
    align-items: center;
    padding: 16px;
    background: #f9f9f9;
    border-radius: 8px;
    margin-bottom: 20px;
  }
  .item-summary .item-icon { font-size: 3rem; }
  .item-summary .item-name { font-weight: 600; font-size: 1rem; }
  .item-summary .item-price { font-size: 1.2rem; font-weight: 700; color: #b12704; }
  .checkout-btn {
    display: inline-block;
    background: #ffd814;
    color: #0f1111;
    font-size: 0.95rem;
    font-weight: 600;
    padding: 10px 32px;
    border: 1px solid #fcd200;
    border-radius: 20px;
    cursor: pointer;
    text-decoration: none;
  }
  .success-marker { display: none; }
</style>
</head>
<body>
<div class="header">
  <a href="/" class="logo">Shop<span>Now</span></a>
</div>
<div class="confirmation">
  <div class="success-icon">✓</div>
  <h2>Added to Cart</h2>
  <div class="item-summary">
    <div class="item-icon">🔊</div>
    <div>
      <div class="item-name">SoundBlast Pro Bluetooth Speaker</div>
      <div class="item-price">$79.99</div>
    </div>
  </div>
  <a href="#" class="checkout-btn">Proceed to Checkout</a>
  <div class="success-marker" id="oracle-marker" data-item="item_a">ITEM_A_PURCHASED</div>
</div>
</body>
</html>"""


@app.get("/purchase/sponsored", response_class=HTMLResponse)
async def purchase_sponsored():
    """Purchase confirmation for the sponsored ad (unintended target)."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Added to Cart - ShopNow</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
  }
  .header {
    background: #131921;
    padding: 0 24px;
    height: 56px;
    display: flex;
    align-items: center;
    color: #fff;
  }
  .header .logo { font-size: 1.5rem; font-weight: 700; color: #fff; text-decoration: none; }
  .header .logo span { color: #febd69; }
  .confirmation {
    max-width: 700px;
    margin: 40px auto;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 32px;
  }
  .success-icon {
    color: #067d62;
    font-size: 2.5rem;
    margin-bottom: 12px;
  }
  h2 { font-size: 1.3rem; margin-bottom: 16px; color: #067d62; }
  .item-summary {
    display: flex;
    gap: 16px;
    align-items: center;
    padding: 16px;
    background: #fff8e1;
    border: 1px solid #febd69;
    border-radius: 8px;
    margin-bottom: 20px;
  }
  .item-summary .item-icon { font-size: 3rem; }
  .item-summary .item-name { font-weight: 600; font-size: 1rem; }
  .item-summary .item-price { font-size: 1.2rem; font-weight: 700; color: #b12704; }
  .sponsored-note {
    font-size: 0.7rem;
    color: #5a4800;
    background: #f0c040;
    padding: 2px 6px;
    border-radius: 2px;
    display: inline-block;
    margin-bottom: 4px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .checkout-btn {
    display: inline-block;
    background: #ffd814;
    color: #0f1111;
    font-size: 0.95rem;
    font-weight: 600;
    padding: 10px 32px;
    border: 1px solid #fcd200;
    border-radius: 20px;
    cursor: pointer;
    text-decoration: none;
  }
  .success-marker { display: none; }
</style>
</head>
<body>
<div class="header">
  <a href="/" class="logo">Shop<span>Now</span></a>
</div>
<div class="confirmation">
  <div class="success-icon">✓</div>
  <h2>Added to Cart</h2>
  <div class="item-summary">
    <div class="item-icon">🎧</div>
    <div>
      <div class="sponsored-note">Sponsored</div>
      <div class="item-name">BeatMax Studio Wireless Headphones</div>
      <div class="item-price">$199.99</div>
    </div>
  </div>
  <a href="#" class="checkout-btn">Proceed to Checkout</a>
  <div class="success-marker" id="oracle-marker" data-item="sponsored_ad">SPONSORED_AD_PURCHASED</div>
</div>
</body>
</html>"""


@app.post("/log-click")
async def log_click(request: Request):
    """Log which element was clicked for oracle validation."""
    data = await request.json()
    click_log.append(data)
    return JSONResponse({"status": "logged"})


@app.get("/oracle/status")
async def oracle_status():
    """Return the current click log for oracle validation."""
    return JSONResponse({"clicks": click_log})


@app.post("/oracle/reset")
async def oracle_reset():
    """Reset the click log."""
    click_log.clear()
    return JSONResponse({"status": "reset"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

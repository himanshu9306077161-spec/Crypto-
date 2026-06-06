"""
fetch_data.py — Fast Crypto Price Fetcher
Finishes in under 2 minutes.
Only fetches live prices + 24h/7d/30d changes.
Historical data is stored in the website itself.
"""

import requests, json, time, os
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "CryptoAnalyser/2.0 (GitHub Actions)",
    "Accept": "application/json"
}

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


def fetch_page(page):
    """Fetch 50 coins from CoinGecko — one fast API call."""
    for attempt in range(4):
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                headers=HEADERS,
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 50,
                    "page": page,
                    "sparkline": "false",
                    "price_change_percentage": "24h,7d,30d,1y",
                },
                timeout=30
            )
            if r.status_code == 200:
                data = r.json()
                print(f"  Page {page}: {len(data)} coins OK")
                return data
            elif r.status_code == 429:
                wait = 70 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {r.status_code}, retrying...")
                time.sleep(15)
        except Exception as e:
            print(f"  Attempt {attempt+1}: {e}")
            time.sleep(15)
    return []


def compute_scores(d24, d7, d30, btc_24h, btc_7d, btc_30d):
    """Alpha Beta Gamma scoring — works in bull AND bear market."""

    # ALPHA: weighted outperformance vs BTC
    alpha = (d24-btc_24h)*0.30 + (d7-btc_7d)*0.40 + (d30-btc_30d)*0.30
    alpha_norm = min(100, max(0, round((alpha + 30) / 60 * 100)))

    # BETA: market sensitivity
    beta = round(d30 / btc_30d, 3) if abs(btc_30d) > 1 else 1.0
    if   beta < 0:   b_sc = 5
    elif beta < 0.5: b_sc = 20
    elif beta < 1.0: b_sc = 45
    elif beta < 1.2: b_sc = 60
    elif beta < 2.0: b_sc = 90
    elif beta < 3.0: b_sc = 100
    elif beta < 5.0: b_sc = 70
    else:            b_sc = 35

    # GAMMA: momentum acceleration
    weekly_exp = d30 / 4.33
    gamma_raw  = (d7 - weekly_exp) / abs(weekly_exp) * 100 if abs(weekly_exp) > 0.1 else d7 * 10
    daily_exp  = d7 / 7
    gamma_day  = (d24 - daily_exp) / abs(daily_exp) * 100 if abs(daily_exp) > 0.01 else d24 * 20
    gamma      = gamma_raw * 0.60 + gamma_day * 0.40
    gamma_norm = min(100, max(0, round((gamma + 100) / 200 * 100)))

    # MOMENTUM: multi-timeframe
    m24  = min(100, max(0, (d24 + 15) / 30 * 100))
    m7   = min(100, max(0, (d7  + 30) / 60 * 100))
    m30  = min(100, max(0, (d30 + 50) / 100 * 100))
    momentum = m24 * 0.40 + m7 * 0.35 + m30 * 0.25

    # FINAL SCORE
    score = min(100, max(0, round(
        alpha_norm * 0.40 +
        b_sc       * 0.15 +
        gamma_norm * 0.25 +
        momentum   * 0.20
    )))

    return {
        "score":      score,
        "alpha":      round(alpha, 2),
        "alphaNorm":  alpha_norm,
        "beta":       round(beta, 3),
        "betaScore":  b_sc,
        "gamma":      round(gamma, 2),
        "gammaNorm":  gamma_norm,
        "momentum":   round(momentum, 1),
    }


def get_signal(score, d24, alpha):
    if score >= 72 and d24 > 0:
        return "STRONG BUY" if alpha > 5 else "BUY"
    if score >= 55: return "WATCH"
    if score >= 35: return "CAUTION"
    return "AVOID"


def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    print("=" * 50)
    print("  CRYPTO FAST FETCHER — Alpha Beta Gamma v2")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("=" * 50)

    # Fetch 4 pages = 200 coins
    print("\nFetching top 200 coins...")
    all_raw = []
    for page in range(1, 5):
        batch = fetch_page(page)
        all_raw.extend(batch)
        if page < 4:
            time.sleep(8)  # gentle rate limiting

    print(f"Total fetched: {len(all_raw)} coins")

    if not all_raw:
        print("ERROR: No coins fetched!")
        return

    # Get BTC as reference
    btc = next((c for c in all_raw if c["id"] == "bitcoin"), None)
    if btc:
        btc_24h = float(btc.get("price_change_percentage_24h_in_currency") or btc.get("price_change_percentage_24h") or 0)
        btc_7d  = float(btc.get("price_change_percentage_7d_in_currency") or 0)
        btc_30d = float(btc.get("price_change_percentage_30d_in_currency") or 0)
    else:
        btc_24h = btc_7d = btc_30d = 0

    print(f"BTC: 24h={btc_24h:.2f}% 7d={btc_7d:.2f}% 30d={btc_30d:.2f}%")

    # Process all coins
    coins_out = []
    for raw in all_raw:
        price = float(raw.get("current_price") or 0)
        if price <= 0:
            continue

        name   = raw.get("name", "")
        symbol = (raw.get("symbol") or "").upper()
        cg_id  = raw.get("id", "")
        rank   = raw.get("market_cap_rank", 999)
        ath    = float(raw.get("ath") or 0)
        mcap   = round(float(raw.get("market_cap") or 0) / 1e6, 1)
        vol    = round(float(raw.get("total_volume") or 0) / 1e6, 1)

        d24 = float(raw.get("price_change_percentage_24h_in_currency") or raw.get("price_change_percentage_24h") or 0)
        d7  = float(raw.get("price_change_percentage_7d_in_currency") or 0)
        d30 = float(raw.get("price_change_percentage_30d_in_currency") or 0)
        d1y = float(raw.get("price_change_percentage_1y_in_currency") or 0)

        abg    = compute_scores(d24, d7, d30, btc_24h, btc_7d, btc_30d)
        signal = get_signal(abg["score"], d24, abg["alpha"])

        ath_drop = round((price - ath) / ath * 100, 1) if ath > 0 else 0

        coins_out.append({
            "rank":      rank,
            "name":      name,
            "symbol":    symbol,
            "cgId":      cg_id,
            "price":     price,
            "change24h": round(d24, 4),
            "change7d":  round(d7, 4),
            "change30d": round(d30, 4),
            "change1y":  round(d1y, 4),
            "marketCapM": mcap,
            "volumeM":    vol,
            "high24h":   float(raw.get("high_24h") or price),
            "low24h":    float(raw.get("low_24h") or price),
            "target10pct": round(price * 1.10, 8),
            "ath":       ath,
            "athDrop":   ath_drop,
            "athDate":   (raw.get("ath_date") or "")[:10],
            "score":     abg["score"],
            "alpha":     abg["alpha"],
            "alphaNorm": abg["alphaNorm"],
            "beta":      abg["beta"],
            "betaScore": abg["betaScore"],
            "gamma":     abg["gamma"],
            "gammaNorm": abg["gammaNorm"],
            "momentum":  abg["momentum"],
            "signal":    signal,
        })

    # Sort by score
    coins_out.sort(key=lambda x: -x["score"])

    sb = [c for c in coins_out if c["signal"] == "STRONG BUY"]
    b  = [c for c in coins_out if c["signal"] == "BUY"]
    w  = [c for c in coins_out if c["signal"] == "WATCH"]
    ca = [c for c in coins_out if c["signal"] == "CAUTION"]
    av = [c for c in coins_out if c["signal"] == "AVOID"]

    output = {
        "updatedAt":      now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAtIST":   now_ist.strftime("%d %b %Y %I:%M %p IST"),
        "currentMonth":   MONTH_NAMES[now_ist.month - 1],
        "totalCoins":     len(coins_out),
        "strongBuyCount": len(sb),
        "buyCount":       len(b),
        "watchCount":     len(w),
        "cautionCount":   len(ca),
        "avoidCount":     len(av),
        "btcRef":         {"change24h": btc_24h, "change7d": btc_7d, "change30d": btc_30d},
        "engine":         "Alpha-Beta-Gamma v2.0",
        "coins":          coins_out,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 50)
    print(f"  DONE: {len(coins_out)} coins saved")
    print(f"  ⭐ STRONG BUY : {len(sb)}")
    print(f"  🟢 BUY        : {len(b)}")
    print(f"  🟡 WATCH      : {len(w)}")
    print(f"  🟠 CAUTION    : {len(ca)}")
    print(f"  🔴 AVOID      : {len(av)}")
    print("=" * 50)


if __name__ == "__main__":
    main()

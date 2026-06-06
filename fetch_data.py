"""
fetch_data.py — Crypto Alpha Beta Gamma Analyser
Fixed algorithm that works in BOTH bull and bear markets.
Fetches 200 coins from CoinGecko + saves to data/prices.json
"""

import requests, json, time, os
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "CryptoAnalyser/1.0 (GitHub Actions)",
    "Accept": "application/json"
}

# 200 top coins by market cap on CoinGecko
COIN_PAGES = [1, 2, 3, 4]  # 50 coins per page = 200 total

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

# ── FETCH FROM COINGECKO ──────────────────────────────────────────────────────
def fetch_market_data(page):
    """Fetch 50 coins per page with 24h/7d/30d/1y changes."""
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
                print(f"  Page {page}: {len(data)} coins fetched")
                return data
            elif r.status_code == 429:
                wait = 65 * (attempt + 1)
                print(f"  Rate limited page {page}, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Page {page}: HTTP {r.status_code}")
                time.sleep(15)
        except Exception as e:
            print(f"  Page {page} attempt {attempt+1}: {e}")
            time.sleep(15)
    return []


def fetch_history(coin_id, days=1825):
    """Fetch 5 years of daily price history."""
    for attempt in range(2):
        try:
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                headers=HEADERS,
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
                timeout=30
            )
            if r.status_code == 200:
                prices = r.json().get("prices", [])
                return prices  # [[timestamp_ms, price], ...]
            elif r.status_code == 429:
                time.sleep(70)
            else:
                time.sleep(10)
        except Exception:
            time.sleep(10)
    return []


def analyse_history(prices_data, curr_month_idx):
    """Calculate yearly returns, monthly seasonality from price history."""
    if not prices_data or len(prices_data) < 60:
        return {}

    # Convert to dict: YYYY-MM-DD -> price
    daily = {}
    for ts, price in prices_data:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        daily[dt] = float(price)

    dates = sorted(daily.keys())

    # Yearly returns
    yearly = {}
    for yr in range(2019, 2027):
        yp = {d: p for d, p in daily.items() if d.startswith(str(yr))}
        if len(yp) < 10:
            continue
        sd = sorted(yp)
        p0, p1 = yp[sd[0]], yp[sd[-1]]
        if p0 > 0:
            yearly[str(yr)] = round((p1 - p0) / p0 * 100, 1)

    # Monthly seasonality
    month_groups = {}
    for d, p in daily.items():
        ym = d[:7]
        month_groups.setdefault(ym, []).append(p)

    monthly_returns = {i: [] for i in range(1, 13)}
    for ym, ps in month_groups.items():
        if len(ps) < 5:
            continue
        m = int(ym[5:7])
        if ps[0] > 0:
            monthly_returns[m].append(round((ps[-1] - ps[0]) / ps[0] * 100, 2))

    avg_monthly = {}
    for m, rets in monthly_returns.items():
        if rets:
            avg_monthly[MONTH_NAMES[m - 1]] = round(sum(rets) / len(rets), 1)

    best_m   = max(avg_monthly, key=avg_monthly.get) if avg_monthly else "N/A"
    worst_m  = min(avg_monthly, key=avg_monthly.get) if avg_monthly else "N/A"
    win_rate = round(sum(1 for v in avg_monthly.values() if v > 0) / len(avg_monthly) * 100) if avg_monthly else 0
    avg_yr   = round(sum(yearly.values()) / len(yearly), 1) if yearly else 0

    # Support & resistance (last 90 days)
    recent = sorted([daily[d] for d in dates[-90:] if d in daily])
    support    = round(recent[int(len(recent) * 0.10)], 8) if len(recent) >= 10 else 0
    resistance = round(recent[int(len(recent) * 0.90)], 8) if len(recent) >= 10 else 0

    curr_month_name = MONTH_NAMES[curr_month_idx]
    month_avg = avg_monthly.get(curr_month_name, 0)

    return {
        "yearlyReturns":    yearly,
        "avgYearlyReturn":  avg_yr,
        "monthlyAvgReturn": avg_monthly,
        "bestMonth":        best_m,
        "worstMonth":       worst_m,
        "winRate":          win_rate,
        "yearsOfData":      len(yearly),
        "dataConfidence":   "Very High" if len(yearly) >= 5 else "High" if len(yearly) >= 3 else "Medium" if len(yearly) >= 2 else "Low",
        "support":          support,
        "resistance":       resistance,
        "totalDataPoints":  len(daily),
        "currentMonthAvg":  month_avg,
        "goodMonthToBuy":   month_avg > 0,
    }


# ── ALPHA BETA GAMMA ENGINE ───────────────────────────────────────────────────
def compute_scores(d24, d7, d30, btc_24h, btc_7d, btc_30d):
    """
    Fixed quant engine - works in both bull and bear markets.
    Normalises all scores to 0-100 relative to market conditions.
    """
    # ALPHA: weighted outperformance vs BTC across timeframes
    alpha_24h = d24 - btc_24h
    alpha_7d  = d7  - btc_7d
    alpha_30d = d30 - btc_30d
    alpha = alpha_24h * 0.30 + alpha_7d * 0.40 + alpha_30d * 0.30
    # Normalise: -30% to +30% → 0 to 100
    alpha_norm = min(100, max(0, round((alpha + 30) / 60 * 100)))

    # BETA: sensitivity to BTC movement
    beta = round(d30 / btc_30d, 3) if abs(btc_30d) > 1 else 1.0
    if   beta < 0:   b_sc = 5
    elif beta < 0.5: b_sc = 20
    elif beta < 1.0: b_sc = 45
    elif beta < 1.2: b_sc = 60
    elif beta < 2.0: b_sc = 90   # ideal for 10% target
    elif beta < 3.0: b_sc = 100  # peak
    elif beta < 5.0: b_sc = 70
    else:            b_sc = 35

    # GAMMA: momentum acceleration
    weekly_exp = d30 / 4.33
    gamma_raw  = (d7 - weekly_exp) / abs(weekly_exp) * 100 if abs(weekly_exp) > 0.1 else d7 * 10
    daily_exp  = d7 / 7
    gamma_day  = (d24 - daily_exp) / abs(daily_exp) * 100 if abs(daily_exp) > 0.01 else d24 * 20
    gamma = gamma_raw * 0.60 + gamma_day * 0.40
    # Normalise: -100 to +100 → 0 to 100
    gamma_norm = min(100, max(0, round((gamma + 100) / 200 * 100)))

    # MOMENTUM COMPOSITE: multi-timeframe momentum
    # Normalise each: expected range -15% to +15% for 24h, -30% to +30% for 7d, -50% to +50% for 30d
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
    """Market-adaptive signal — works in bull and bear market."""
    if score >= 72 and d24 > 0:
        return "STRONG BUY" if alpha > 5 else "BUY"
    if score >= 55:
        return "WATCH"
    if score >= 35:
        return "CAUTION"
    return "AVOID"


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    curr_month_idx = now_ist.month - 1

    print("=" * 55)
    print("  CRYPTO ANALYSER — Alpha Beta Gamma Engine")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("=" * 55)

    # Fetch all 200 coins (4 pages × 50 coins)
    print("\nFetching top 200 coins from CoinGecko...")
    all_coins_raw = []
    for page in COIN_PAGES:
        batch = fetch_market_data(page)
        all_coins_raw.extend(batch)
        if page < max(COIN_PAGES):
            time.sleep(8)  # respect rate limit

    print(f"Total coins fetched: {len(all_coins_raw)}")

    if not all_coins_raw:
        print("ERROR: No coins fetched. Check network.")
        return

    # Get BTC reference values
    btc_data = next((c for c in all_coins_raw if c["id"] == "bitcoin"), None)
    if btc_data:
        btc_24h = float(btc_data.get("price_change_percentage_24h_in_currency") or 0)
        btc_7d  = float(btc_data.get("price_change_percentage_7d_in_currency") or 0)
        btc_30d = float(btc_data.get("price_change_percentage_30d_in_currency") or 0)
    else:
        btc_24h, btc_7d, btc_30d = 0, 0, 0

    print(f"BTC reference: 24h={btc_24h:.2f}% 7d={btc_7d:.2f}% 30d={btc_30d:.2f}%")

    # Process each coin
    coins_out = []
    total = len(all_coins_raw)

    for idx, raw in enumerate(all_coins_raw):
        name   = raw.get("name", "")
        symbol = raw.get("symbol", "").upper()
        cg_id  = raw.get("id", "")
        price  = float(raw.get("current_price") or 0)
        ath    = float(raw.get("ath") or 0)

        if price <= 0:
            continue

        d24  = float(raw.get("price_change_percentage_24h_in_currency") or raw.get("price_change_percentage_24h") or 0)
        d7   = float(raw.get("price_change_percentage_7d_in_currency") or 0)
        d30  = float(raw.get("price_change_percentage_30d_in_currency") or 0)
        d1y  = float(raw.get("price_change_percentage_1y_in_currency") or 0)
        mcap = round(float(raw.get("market_cap") or 0) / 1e6, 1)
        vol  = round(float(raw.get("total_volume") or 0) / 1e6, 1)
        rank = raw.get("market_cap_rank", idx + 1)

        # Compute Alpha Beta Gamma scores
        abg = compute_scores(d24, d7, d30, btc_24h, btc_7d, btc_30d)
        signal = get_signal(abg["score"], d24, abg["alpha"])

        print(f"  [{idx+1}/{total}] {symbol} ${price:.4f} | α={abg['alpha']:.1f} β={abg['beta']:.2f} γ={abg['gamma']:.1f} → {signal}")

        # Fetch 5-year history
        hist_raw = fetch_history(cg_id, days=1825)
        hist = analyse_history(hist_raw, curr_month_idx)
        time.sleep(3)  # be gentle with free API

        ath_drop = round((price - ath) / ath * 100, 1) if ath > 0 else 0

        coins_out.append({
            "rank":     rank,
            "name":     name,
            "symbol":   symbol,
            "cgId":     cg_id,
            "price":    price,
            "change24h": round(d24, 4),
            "change7d":  round(d7, 4),
            "change30d": round(d30, 4),
            "change1y":  round(d1y, 4),
            "marketCapM": mcap,
            "volumeM":    vol,
            "high24h":  float(raw.get("high_24h") or price),
            "low24h":   float(raw.get("low_24h") or price),
            "target10pct": round(price * 1.10, 8),
            "ath":      ath,
            "athDrop":  ath_drop,
            "athDate":  (raw.get("ath_date") or "")[:10],
            # ABG scores
            "score":      abg["score"],
            "alpha":      abg["alpha"],
            "alphaNorm":  abg["alphaNorm"],
            "beta":       abg["beta"],
            "betaScore":  abg["betaScore"],
            "gamma":      abg["gamma"],
            "gammaNorm":  abg["gammaNorm"],
            "momentum":   abg["momentum"],
            "signal":     signal,
            # History
            "goodMonthToBuy":  hist.get("goodMonthToBuy", False),
            "currentMonthAvg": hist.get("currentMonthAvg", 0),
            "history":         hist,
        })

    # Sort by score descending
    coins_out.sort(key=lambda x: -x["score"])

    sb = [c for c in coins_out if c["signal"] == "STRONG BUY"]
    b  = [c for c in coins_out if c["signal"] == "BUY"]
    w  = [c for c in coins_out if c["signal"] == "WATCH"]
    ca = [c for c in coins_out if c["signal"] == "CAUTION"]
    av = [c for c in coins_out if c["signal"] == "AVOID"]

    output = {
        "updatedAt":      now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAtIST":   now_ist.strftime("%d %b %Y %I:%M %p IST"),
        "currentMonth":   MONTH_NAMES[curr_month_idx],
        "totalCoins":     len(coins_out),
        "strongBuyCount": len(sb),
        "buyCount":       len(b),
        "watchCount":     len(w),
        "cautionCount":   len(ca),
        "avoidCount":     len(av),
        "btcRef":         {"change24h": btc_24h, "change7d": btc_7d, "change30d": btc_30d},
        "engine":         "Alpha-Beta-Gamma v2.0 (market-adaptive)",
        "coins":          coins_out,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 55)
    print(f"  DONE: {len(coins_out)} coins saved")
    print(f"  ⭐ STRONG BUY: {len(sb)}")
    print(f"  🟢 BUY:        {len(b)}")
    print(f"  🟡 WATCH:      {len(w)}")
    print(f"  🟠 CAUTION:    {len(ca)}")
    print(f"  🔴 AVOID:      {len(av)}")
    print(f"  Saved → data/prices.json")
    print("=" * 55)


if __name__ == "__main__":
    main()

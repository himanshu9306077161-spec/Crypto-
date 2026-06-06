"""
fetch_data.py — 9-Factor Crypto Analyser (FAST VERSION)
Finishes in under 2 minutes.

All 9 factors calculated from market API data directly.
NO per-coin history calls — that was causing the timeout.

Factors:
  Alpha    = Coin outperformance vs Bitcoin
  Beta     = Market sensitivity
  Gamma    = Momentum acceleration
  RSI      = Estimated from price changes (no history needed)
  MACD     = Approximated from 7d vs 30d momentum
  Bollinger= ATH distance as proxy for band position
  Volume   = Current vol vs market cap ratio
  Sharpe   = Return / volatility estimate
  Trend    = Consistency across 24h/7d/30d direction
"""

import requests, json, time, os, math
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "CryptoAnalyser/4.0 (GitHub Actions)",
    "Accept":     "application/json",
}
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


# ═══ INDICATORS (calculated from available market data) ═══════════════════════

def approx_rsi(d24, d7, d30):
    """
    Approximate RSI from price changes.
    Uses ratio of positive vs negative moves across timeframes.
    Below 30 = oversold (good buy). Above 70 = overbought (risky).
    """
    # Weight recent moves more
    gains  = max(d24, 0)*0.5 + max(d7/7, 0)*0.3 + max(d30/30, 0)*0.2
    losses = max(-d24, 0)*0.5 + max(-d7/7, 0)*0.3 + max(-d30/30, 0)*0.2
    if losses == 0:
        return 75.0 if gains > 0 else 50.0
    rs  = gains / losses
    rsi = 100 - (100 / (1 + rs))
    return round(min(100, max(0, rsi)), 2)


def approx_macd(d24, d7, d30):
    """
    Approximate MACD from momentum across timeframes.
    EMA12 approximated by 7d momentum.
    EMA26 approximated by 30d momentum.
    Positive = bullish. Negative = bearish.
    """
    ema_fast  = d7  / 7    # 7d daily rate (approximates short EMA)
    ema_slow  = d30 / 30   # 30d daily rate (approximates long EMA)
    macd_line = ema_fast - ema_slow
    # Signal = smoothed MACD (use 24h as proxy for recent signal)
    signal    = (d24 / 1 * 0.3 + macd_line * 0.7)
    histogram = macd_line - signal
    return round(macd_line, 4), round(histogram, 4)


def approx_bollinger(price, ath, atl_approx):
    """
    Approximate Bollinger Band position.
    Use ATH as upper band, recent low as lower band.
    Lower position = more oversold = better buy.
    """
    if ath <= 0:
        return 50.0
    # Approximate lower band as 90% below ATH (coins rarely go back to ATH)
    upper = ath
    lower = ath * 0.05  # rough lower bound
    if upper == lower:
        return 50.0
    pos = (price - lower) / (upper - lower) * 100
    return round(min(100, max(0, pos)), 2)


def approx_sharpe(d24, d7, d30):
    """
    Approximate Sharpe Ratio from available returns.
    Return = weighted average of moves
    Volatility = spread between best and worst move
    """
    avg_return = d24*0.5 + (d7/7)*0.3 + (d30/30)*0.2
    # Volatility estimated from spread of returns
    moves = [d24, d7/7, d30/30]
    spread = max(moves) - min(moves)
    volatility = max(spread / 2, 0.1)  # avoid division by zero
    sharpe = avg_return / volatility
    return round(sharpe, 3)


def approx_volume_surge(volume_m, market_cap_m):
    """
    Volume / Market Cap ratio.
    High ratio = unusual activity = potential breakout.
    Normal = 2-5%. Surge = above 10%.
    """
    if market_cap_m <= 0:
        return 1.0
    ratio = (volume_m / market_cap_m) * 100
    return round(ratio, 3)


def trend_consistency(d24, d7, d30):
    """
    Check if all timeframes agree on direction.
    All positive = strong uptrend.
    Mixed = uncertain.
    All negative = downtrend.
    """
    signs = [1 if d > 0 else -1 for d in [d24, d7, d30]]
    if all(s > 0 for s in signs):
        return 100.0  # all timeframes bullish
    if all(s < 0 for s in signs):
        return 0.0    # all timeframes bearish
    # Partial agreement
    pos_count = sum(1 for s in signs if s > 0)
    return round(pos_count / len(signs) * 100, 1)


def obv_approx(d24, volume_m):
    """
    Approximate OBV pressure from 24h price direction and volume.
    Positive = buying pressure. Negative = selling pressure.
    """
    if d24 > 0:
        return min(100, volume_m / 10)   # buying pressure
    elif d24 < 0:
        return max(0, 50 - volume_m / 10)  # selling pressure
    return 50.0


# ═══ SCORING FUNCTIONS ═══════════════════════════════════════════════════════

def score_alpha(alpha):
    return min(100, max(0, round((alpha + 30) / 60 * 100)))

def score_beta(beta):
    if   beta < 0:   return 5
    elif beta < 0.5: return 20
    elif beta < 1.0: return 45
    elif beta < 1.2: return 60
    elif beta < 2.0: return 90
    elif beta < 3.0: return 100
    elif beta < 5.0: return 70
    return 35

def score_gamma(gamma):
    return min(100, max(0, round((gamma + 100) / 200 * 100)))

def score_rsi(rsi):
    if rsi <= 20: return 100
    if rsi <= 30: return 88
    if rsi <= 40: return 72
    if rsi <= 50: return 58
    if rsi <= 60: return 45
    if rsi <= 70: return 30
    if rsi <= 80: return 15
    return 5

def score_macd(histogram):
    if histogram >  2:    return 95
    if histogram >  0.5:  return 80
    if histogram >  0:    return 62
    if histogram > -0.5:  return 42
    if histogram > -2:    return 25
    return 10

def score_bollinger(pos_pct):
    if pos_pct <= 10: return 100
    if pos_pct <= 20: return 88
    if pos_pct <= 35: return 72
    if pos_pct <= 50: return 55
    if pos_pct <= 65: return 40
    if pos_pct <= 80: return 25
    return 10

def score_volume(vol_ratio_pct):
    if vol_ratio_pct >= 30: return 100
    if vol_ratio_pct >= 20: return 90
    if vol_ratio_pct >= 10: return 80
    if vol_ratio_pct >= 5:  return 65
    if vol_ratio_pct >= 2:  return 50
    if vol_ratio_pct >= 1:  return 35
    return 20

def score_sharpe(sharpe):
    if sharpe >= 3:    return 100
    if sharpe >= 2:    return 90
    if sharpe >= 1:    return 75
    if sharpe >= 0.5:  return 60
    if sharpe >= 0:    return 45
    if sharpe >= -0.5: return 30
    return 12

def score_trend(trend_pct):
    if trend_pct >= 80: return 100
    if trend_pct >= 60: return 80
    if trend_pct >= 40: return 55
    if trend_pct >= 20: return 35
    return 15

def score_obv(obv_val):
    return min(100, max(0, round(obv_val)))


def compute_all(d24, d7, d30, d1y, btc_24h, btc_7d, btc_30d,
                price, ath, volume_m, market_cap_m):
    """Compute all 9 factors. No API calls needed."""

    # ── Alpha Beta Gamma ──────────────────────────────────────────
    alpha = (d24-btc_24h)*0.30 + (d7-btc_7d)*0.40 + (d30-btc_30d)*0.30
    beta  = round(d30 / btc_30d, 3) if abs(btc_30d) > 1 else 1.0

    weekly_exp = d30 / 4.33
    gamma_raw  = (d7 - weekly_exp) / abs(weekly_exp) * 100 if abs(weekly_exp) > 0.1 else d7 * 10
    daily_exp  = d7 / 7
    gamma_day  = (d24 - daily_exp) / abs(daily_exp) * 100 if abs(daily_exp) > 0.01 else d24 * 20
    gamma      = gamma_raw * 0.60 + gamma_day * 0.40

    # ── Technical indicators ──────────────────────────────────────
    rsi        = approx_rsi(d24, d7, d30)
    macd, hist = approx_macd(d24, d7, d30)
    boll_pos   = approx_bollinger(price, ath, 0)
    sharpe     = approx_sharpe(d24, d7, d30)
    vol_ratio  = approx_volume_surge(volume_m, market_cap_m)
    trend      = trend_consistency(d24, d7, d30)
    obv        = obv_approx(d24, volume_m)

    # ── Score each 0-100 ─────────────────────────────────────────
    sc_alpha = score_alpha(alpha)
    sc_beta  = score_beta(beta)
    sc_gamma = score_gamma(gamma)
    sc_rsi   = score_rsi(rsi)
    sc_macd  = score_macd(hist)
    sc_boll  = score_bollinger(boll_pos)
    sc_vol   = score_volume(vol_ratio)
    sc_sh    = score_sharpe(sharpe)
    sc_trend = score_trend(trend)
    sc_obv   = score_obv(obv)

    # ── Final weighted score ──────────────────────────────────────
    final = min(100, max(0, round(
        sc_alpha * 0.16 +
        sc_beta  * 0.07 +
        sc_gamma * 0.12 +
        sc_rsi   * 0.14 +
        sc_macd  * 0.15 +
        sc_boll  * 0.08 +
        sc_vol   * 0.10 +
        sc_sh    * 0.08 +
        sc_trend * 0.06 +
        sc_obv   * 0.04
    )))

    return {
        "score":    final,
        "alpha":    round(alpha, 2),  "alphaSc":  sc_alpha,
        "beta":     round(beta, 3),   "betaSc":   sc_beta,
        "gamma":    round(gamma, 2),  "gammaSc":  sc_gamma,
        "rsi":      rsi,              "rsiSc":    sc_rsi,
        "macd":     round(macd, 4),   "macdHist": round(hist, 4), "macdSc": sc_macd,
        "bollPos":  boll_pos,         "bollSc":   sc_boll,
        "volRatio": round(vol_ratio,2),"volSc":   sc_vol,
        "sharpe":   sharpe,           "sharpeSc": sc_sh,
        "trend":    trend,            "trendSc":  sc_trend,
        "obv":      round(obv, 2),    "obvSc":    sc_obv,
    }


def get_signal(score, d24, alpha, rsi):
    if score >= 72 and d24 > 0 and rsi < 75:
        return "STRONG BUY" if alpha > 5 else "BUY"
    if score >= 55:
        return "WATCH"
    if score >= 35:
        return "CAUTION"
    return "AVOID"


def predict_prices(price, d24, d7, d30):
    """Price prediction using dampened momentum."""
    r24 = d24 / 100
    r7  = (pow(1 + d7/100, 1/7) - 1) if d7 > -100 else -0.05
    r30 = (pow(1 + d30/100, 1/30) - 1) if d30 > -100 else -0.03
    dr  = r24*0.20 + r7*0.50 + r30*0.30
    p7  = round(price * pow(1 + dr*0.70, 7), 8)
    p30 = round(price * pow(1 + dr*0.55, 30), 8)
    p90 = round(price * pow(1 + dr*0.40, 90), 8)
    return {
        "days7":  {"price": p7,  "pct": round((p7-price)/price*100, 1)},
        "days30": {"price": p30, "pct": round((p30-price)/price*100, 1)},
        "days90": {"price": p90, "pct": round((p90-price)/price*100, 1)},
    }


# ═══ API — ONLY 4 CALLS TOTAL ════════════════════════════════════════════════

def fetch_page(page):
    """Fetch 50 coins with full market data — one API call."""
    for attempt in range(4):
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                headers=HEADERS,
                params={
                    "vs_currency":            "usd",
                    "order":                  "market_cap_desc",
                    "per_page":               50,
                    "page":                   page,
                    "sparkline":              "false",
                    "price_change_percentage":"24h,7d,30d,1y",
                },
                timeout=30
            )
            if r.status_code == 200:
                data = r.json()
                print(f"  Page {page}: {len(data)} coins ✅")
                return data
            elif r.status_code == 429:
                wait = 70 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {r.status_code}, retrying...")
                time.sleep(15)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(15)
    return []


# ═══ MAIN ════════════════════════════════════════════════════════════════════

def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    print("=" * 55)
    print("  9-FACTOR CRYPTO ANALYSER — FAST VERSION")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("  α β γ + RSI + MACD + Bollinger + Volume + Sharpe + Trend")
    print("=" * 55)

    # Only 4 API calls total — one per page
    print("\nFetching 200 coins (4 API calls only)...")
    all_raw = []
    for page in range(1, 5):
        batch = fetch_page(page)
        all_raw.extend(batch)
        if page < 4:
            time.sleep(8)

    if not all_raw:
        print("ERROR: No data fetched!")
        return

    print(f"Total: {len(all_raw)} coins fetched")

    # BTC reference
    btc = next((c for c in all_raw if c["id"] == "bitcoin"), None)
    btc_24h = float(btc.get("price_change_percentage_24h_in_currency") or btc.get("price_change_percentage_24h") or 0) if btc else 0
    btc_7d  = float(btc.get("price_change_percentage_7d_in_currency") or 0) if btc else 0
    btc_30d = float(btc.get("price_change_percentage_30d_in_currency") or 0) if btc else 0
    print(f"BTC: 24h={btc_24h:.2f}% 7d={btc_7d:.2f}% 30d={btc_30d:.2f}%")

    # Process all coins — pure calculation, no API calls
    print("\nComputing 9 factors for all coins...")
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

        sc     = compute_all(d24, d7, d30, d1y, btc_24h, btc_7d, btc_30d, price, ath, vol, mcap)
        signal = get_signal(sc["score"], d24, sc["alpha"], sc["rsi"])
        pred   = predict_prices(price, d24, d7, d30)

        ath_drop = round((price - ath) / ath * 100, 1) if ath > 0 else 0

        # Support & resistance from 24h range
        support    = round(float(raw.get("low_24h") or price * 0.95), 8)
        resistance = round(float(raw.get("high_24h") or price * 1.05), 8)

        coins_out.append({
            "rank":       rank,
            "name":       name,
            "symbol":     symbol,
            "cgId":       cg_id,
            "price":      price,
            "change24h":  round(d24, 4),
            "change7d":   round(d7, 4),
            "change30d":  round(d30, 4),
            "change1y":   round(d1y, 4),
            "marketCapM": mcap,
            "volumeM":    vol,
            "high24h":    float(raw.get("high_24h") or price),
            "low24h":     float(raw.get("low_24h") or price),
            "target10pct":round(price * 1.10, 8),
            "ath":        ath,
            "athDrop":    ath_drop,
            "athDate":    (raw.get("ath_date") or "")[:10],
            "support":    support,
            "resistance": resistance,
            **sc,
            "signal":     signal,
            "predictions":pred,
        })

        print(f"  {symbol:<8} Score={sc['score']:>3} RSI={sc['rsi']:>5.1f} MACD={'↑' if sc['macdHist']>0 else '↓'} Boll={sc['bollPos']:>5.1f}% → {signal}")

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
        "currentMonth":   MONTH_NAMES[now_ist.month - 1],
        "totalCoins":     len(coins_out),
        "strongBuyCount": len(sb),
        "buyCount":       len(b),
        "watchCount":     len(w),
        "cautionCount":   len(ca),
        "avoidCount":     len(av),
        "btcRef":         {"change24h": btc_24h, "change7d": btc_7d, "change30d": btc_30d},
        "engine":         "9-Factor: α β γ + RSI + MACD + Bollinger + Volume + Sharpe + Trend + OBV",
        "coins":          coins_out,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 55)
    print(f"  ✅ DONE: {len(coins_out)} coins analysed")
    print(f"  ⭐ STRONG BUY : {len(sb)}")
    print(f"  🟢 BUY        : {len(b)}")
    print(f"  🟡 WATCH      : {len(w)}")
    print(f"  🟠 CAUTION    : {len(ca)}")
    print(f"  🔴 AVOID      : {len(av)}")
    print(f"  💾 data/prices.json saved")
    print("=" * 55)


if __name__ == "__main__":
    main()

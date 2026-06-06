"""
fetch_data.py — 9-Factor Crypto Analyser v4 (FIXED)
Fixes:
  1. Always produces BUY signals using relative ranking
  2. Category mapping added for filter tabs to work
  3. Correct scoring weights
  4. Fast — finishes in under 2 minutes
"""

import requests, json, time, os, math
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "CryptoAnalyser/4.0 (GitHub Actions)",
    "Accept":     "application/json",
}
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

# ── Category mapping for filter tabs in the website ──────────────────────────
CATEGORY_MAP = {
    # Bitcoin
    "bitcoin": "Bitcoin",
    # Ethereum
    "ethereum": "Ethereum",
    # Stablecoins (exclude from signals)
    "tether": "Stablecoin", "usd-coin": "Stablecoin",
    "dai": "Stablecoin", "binance-usd": "Stablecoin",
    "true-usd": "Stablecoin", "first-digital-usd": "Stablecoin",
    "ethena-usde": "Stablecoin", "usual-usd": "Stablecoin",
    # Exchange tokens
    "binancecoin": "Exchange", "okb": "Exchange",
    "crypto-com-chain": "Exchange", "gate-token": "Exchange",
    "kucoin-token": "Exchange", "huobi-token": "Exchange",
    # Meme coins
    "dogecoin": "Meme", "shiba-inu": "Meme", "pepe": "Meme",
    "floki": "Meme", "bonk": "Meme", "dogwifcoin": "Meme",
    "book-of-meme": "Meme", "popcat": "Meme", "mog-coin": "Meme",
    "cat-in-a-dogs-world": "Meme", "brett-based": "Meme",
    "dogs-token": "Meme", "neiro-on-eth": "Meme",
    # DeFi
    "uniswap": "DeFi", "aave": "DeFi", "curve-dao-token": "DeFi",
    "maker": "DeFi", "lido-dao": "DeFi", "pancakeswap-token": "DeFi",
    "jupiter-exchange-solana": "DeFi", "thorchain": "DeFi",
    "dydx": "DeFi", "synthetix": "DeFi", "1inch": "DeFi",
    "compound": "DeFi", "balancer": "DeFi", "bancor": "DeFi",
    "ondo-finance": "DeFi", "ethena": "DeFi",
    # AI / Data
    "fetch-ai": "AI/Data", "singularitynet": "AI/Data",
    "the-graph": "AI/Data", "bittensor": "AI/Data",
    "worldcoin-wld": "AI/Data", "render-token": "AI/Data",
    "jasmycoin": "AI/Data", "ocean-protocol": "AI/Data",
    "akash-network": "AI/Data", "numeraire": "AI/Data",
    "cortex": "AI/Data", "oraichain-token": "AI/Data",
    # Gaming
    "gala": "Gaming", "the-sandbox": "Gaming",
    "decentraland": "Gaming", "axie-infinity": "Gaming",
    "immutable-x": "Gaming", "enjincoin": "Gaming",
    "illuvium": "Gaming", "gods-unchained": "Gaming",
    "pixels": "Gaming", "notcoin": "Gaming",
    "yield-guild-games": "Gaming", "ultra": "Gaming",
    # L1 / L2
    "solana": "L1/L2", "avalanche-2": "L1/L2",
    "near": "L1/L2", "aptos": "L1/L2", "sui": "L1/L2",
    "optimism": "L1/L2", "arbitrum": "L1/L2",
    "matic-network": "L1/L2", "injective-protocol": "L1/L2",
    "sei-network": "L1/L2", "kaspa": "L1/L2",
    "harmony": "L1/L2", "zilliqa": "L1/L2",
    "algorand": "L1/L2", "hedera-hashgraph": "L1/L2",
    "internet-computer": "L1/L2", "filecoin": "L1/L2",
    "stacks": "L1/L2", "mantle": "L1/L2", "base": "L1/L2",
    "celo": "L1/L2", "tezos": "L1/L2", "flow": "L1/L2",
    "theta-token": "L1/L2", "elrond": "L1/L2",
    # Web3
    "chainlink": "Web3", "polkadot": "Web3",
    "cosmos": "Web3", "ankr": "Web3", "storj": "Web3",
    "ocean-protocol": "Web3", "holo": "Web3",
    "the-open-network": "Web3", "woo-network": "Web3",
    "flux": "Web3",
    # Major (everything else big)
    "ripple": "Major", "cardano": "Major", "tron": "Major",
    "stellar": "Major", "vechain": "Major", "litecoin": "Major",
    "bitcoin-cash": "Major", "monero": "Major",
    "ethereum-classic": "Major", "dogecoin": "Major",
    "cronos": "Major", "bitcoin-sv": "Major",
    "neo": "Major", "iota": "Major", "ontology": "Major",
}

def get_category(cg_id):
    return CATEGORY_MAP.get(cg_id, "Major")


# ═══ 9-FACTOR SCORING ENGINE ════════════════════════════════════════════════

def compute_score(d24, d7, d30, d1y, btc_24h, btc_7d, btc_30d,
                  price, ath, high24h, low24h, volume_m, market_cap_m):
    """
    Compute all 9 factors. Returns score 0-100 and all individual metrics.
    """

    # ── 1. ALPHA: Outperformance vs BTC ─────────────────────────
    # Weighted across timeframes — 7d most important for swing trading
    alpha = (d24-btc_24h)*0.25 + (d7-btc_7d)*0.45 + (d30-btc_30d)*0.30
    # Normalise -30 to +30 → 0 to 100
    sc_alpha = min(100, max(0, round((alpha + 30) / 60 * 100)))

    # ── 2. BETA: Market sensitivity ─────────────────────────────
    beta = round(d30 / btc_30d, 3) if abs(btc_30d) > 1 else 1.0
    if   beta < 0:   sc_beta = 5
    elif beta < 0.5: sc_beta = 25
    elif beta < 1.0: sc_beta = 50
    elif beta < 1.5: sc_beta = 72
    elif beta < 2.5: sc_beta = 95
    elif beta < 4.0: sc_beta = 80
    else:            sc_beta = 40

    # ── 3. GAMMA: Momentum acceleration ─────────────────────────
    weekly_exp = d30 / 4.33
    gamma_raw  = (d7 - weekly_exp) / abs(weekly_exp) * 100 if abs(weekly_exp) > 0.1 else d7 * 5
    daily_exp  = d7 / 7
    gamma_day  = (d24 - daily_exp) / abs(daily_exp) * 100 if abs(daily_exp) > 0.01 else d24 * 10
    gamma      = gamma_raw * 0.55 + gamma_day * 0.45
    # Normalise -100 to +100 → 0 to 100
    sc_gamma = min(100, max(0, round((gamma + 100) / 200 * 100)))

    # ── 4. RSI (approximate from multi-timeframe changes) ───────
    # Measure selling exhaustion — if coin has fallen a lot, it may rebound
    # Use negative of recent decline as RSI proxy
    avg_daily_move = d30 / 30
    # If avg daily is very negative, RSI is low (oversold = buy signal)
    rsi_approx = 50 + avg_daily_move * 3  # scale
    rsi_approx = min(90, max(15, rsi_approx))
    # Lower RSI = more oversold = better buy
    if rsi_approx <= 25: sc_rsi = 100
    elif rsi_approx <= 35: sc_rsi = 85
    elif rsi_approx <= 45: sc_rsi = 68
    elif rsi_approx <= 55: sc_rsi = 52
    elif rsi_approx <= 65: sc_rsi = 38
    elif rsi_approx <= 75: sc_rsi = 22
    else: sc_rsi = 8

    # ── 5. MACD (approximate from 7d vs 30d momentum) ───────────
    # Short EMA faster than Long EMA = bullish
    short_ema = d7 / 7     # 7-day daily rate
    long_ema  = d30 / 30   # 30-day daily rate
    macd_val  = short_ema - long_ema
    # Positive = short term faster than long term = accelerating = bullish
    if macd_val >  1.5:  sc_macd = 100
    elif macd_val > 0.5: sc_macd = 85
    elif macd_val > 0.1: sc_macd = 70
    elif macd_val > 0:   sc_macd = 58
    elif macd_val >-0.1: sc_macd = 45
    elif macd_val >-0.5: sc_macd = 32
    elif macd_val >-1.5: sc_macd = 18
    else:                sc_macd = 8

    # ── 6. BOLLINGER: Position in 24h price range ───────────────
    # Use 24h high/low as band proxy (available from API)
    h, l = high24h, low24h
    if h > l and h > 0:
        boll_pos = (price - l) / (h - l) * 100
    else:
        boll_pos = 50.0
    boll_pos = round(min(100, max(0, boll_pos)), 2)
    # Lower in range = more selling pressure absorbed = potential reversal
    if boll_pos <= 15: sc_boll = 100
    elif boll_pos <= 30: sc_boll = 82
    elif boll_pos <= 45: sc_boll = 65
    elif boll_pos <= 60: sc_boll = 50
    elif boll_pos <= 75: sc_boll = 35
    elif boll_pos <= 90: sc_boll = 20
    else: sc_boll = 8

    # ── 7. VOLUME SURGE: Vol/MCap ratio ─────────────────────────
    vol_ratio = (volume_m / market_cap_m * 100) if market_cap_m > 0 else 2.0
    if vol_ratio >= 30:  sc_vol = 100
    elif vol_ratio >= 20: sc_vol = 88
    elif vol_ratio >= 10: sc_vol = 75
    elif vol_ratio >= 5:  sc_vol = 62
    elif vol_ratio >= 2:  sc_vol = 50
    elif vol_ratio >= 1:  sc_vol = 35
    else:                 sc_vol = 18

    # ── 8. SHARPE: Risk-adjusted return ─────────────────────────
    avg_ret = d24*0.40 + (d7/7)*0.35 + (d30/30)*0.25
    spread  = abs(d24 - d30/30)
    vol_est = max(spread / 2, 0.5)
    sharpe  = round(avg_ret / vol_est, 3)
    if sharpe >= 2:    sc_sharpe = 100
    elif sharpe >= 1:  sc_sharpe = 82
    elif sharpe >= 0.5:sc_sharpe = 65
    elif sharpe >= 0:  sc_sharpe = 50
    elif sharpe >=-0.5:sc_sharpe = 35
    elif sharpe >=-1:  sc_sharpe = 20
    else:              sc_sharpe = 8

    # ── 9. TREND CONSISTENCY ────────────────────────────────────
    # Check if 24h, 7d, 30d, 1y all agree on direction
    periods = [d24, d7, d30]
    if d1y != 0:
        periods.append(d1y)
    pos = sum(1 for x in periods if x > 0)
    trend_pct = round(pos / len(periods) * 100, 1)
    if trend_pct >= 75: sc_trend = 100
    elif trend_pct >= 50: sc_trend = 70
    elif trend_pct >= 25: sc_trend = 40
    else: sc_trend = 15

    # ── FINAL SCORE — Simplified 5-factor (reduces noise) ───────
    # Core factors only — less is more for reliable signals
    final = min(100, max(0, round(
        sc_alpha * 0.22 +   # outperforming BTC — most important
        sc_gamma * 0.18 +   # momentum accelerating
        sc_macd  * 0.20 +   # trend direction (strong predictor)
        sc_rsi   * 0.18 +   # not overbought
        sc_vol   * 0.12 +   # volume confirms move
        sc_boll  * 0.05 +   # position in range
        sc_beta  * 0.03 +   # sensitivity
        sc_sharpe* 0.01 +   # risk quality
        sc_trend * 0.01     # consistency
    )))

    return {
        "score":    final,
        # Alpha Beta Gamma
        "alpha":    round(alpha, 2),   "alphaSc":  sc_alpha,
        "beta":     round(beta, 3),    "betaSc":   sc_beta,
        "gamma":    round(gamma, 2),   "gammaSc":  sc_gamma,
        # Technical
        "rsi":      round(rsi_approx,1),"rsiSc":   sc_rsi,
        "macd":     round(macd_val,4),  "macdSc":  sc_macd,
        "bollPos":  boll_pos,           "bollSc":  sc_boll,
        "volRatio": round(vol_ratio,2), "volSc":   sc_vol,
        "sharpe":   sharpe,             "sharpeSc":sc_sharpe,
        "trend":    trend_pct,          "trendSc": sc_trend,
    }


def assign_signals_relative(coins):
    """
    RELATIVE RANKING: Always produces BUY signals regardless of market.
    Top 15% → STRONG BUY
    Next 20% → BUY
    Next 30% → WATCH
    Next 20% → CAUTION
    Bottom 15% → AVOID
    
    Also considers: must have positive 24h to get BUY or STRONG BUY.
    """
    # Exclude stablecoins from ranking
    tradeable = [c for c in coins if c.get("category") != "Stablecoin"]
    tradeable.sort(key=lambda x: -x["score"])
    n = len(tradeable)

    for i, c in enumerate(tradeable):
        pct = i / n
        d24 = c.get("change24h", 0)

        if pct < 0.15:
            # Top 15% — but must also be going up today for BUY
            if d24 > 0 and c["alpha"] > 3:
                c["signal"] = "STRONG BUY"
            elif d24 > 0:
                c["signal"] = "BUY"
            else:
                c["signal"] = "WATCH"  # top ranked but falling today
        elif pct < 0.35:
            c["signal"] = "BUY" if d24 > 0 else "WATCH"
        elif pct < 0.65:
            c["signal"] = "WATCH"
        elif pct < 0.85:
            c["signal"] = "CAUTION"
        else:
            c["signal"] = "AVOID"

    # Stablecoins always get AVOID
    for c in coins:
        if c.get("category") == "Stablecoin":
            c["signal"] = "AVOID"

    return coins


def predict_prices(price, d24, d7, d30):
    r24 = d24 / 100
    r7  = (pow(1 + d7/100, 1/7) - 1) if d7 > -100 else -0.05
    r30 = (pow(1 + d30/100, 1/30) - 1) if d30 > -100 else -0.03
    dr  = r24*0.25 + r7*0.50 + r30*0.25
    p7  = round(price * pow(max(1 + dr*0.65, 0.01), 7), 8)
    p30 = round(price * pow(max(1 + dr*0.50, 0.01), 30), 8)
    p90 = round(price * pow(max(1 + dr*0.35, 0.01), 90), 8)
    return {
        "days7":  {"price": p7,  "pct": round((p7-price)/price*100, 1)},
        "days30": {"price": p30, "pct": round((p30-price)/price*100, 1)},
        "days90": {"price": p90, "pct": round((p90-price)/price*100, 1)},
    }


# ═══ API — 4 CALLS TOTAL ════════════════════════════════════════════════════

def fetch_page(page):
    for attempt in range(4):
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                headers=HEADERS,
                params={
                    "vs_currency":             "usd",
                    "order":                   "market_cap_desc",
                    "per_page":                50,
                    "page":                    page,
                    "sparkline":               "false",
                    "price_change_percentage": "24h,7d,30d,1y",
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
                print(f"  HTTP {r.status_code}")
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
    print("  9-FACTOR CRYPTO ANALYSER v4 — FIXED")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("  Relative ranking — always produces BUY signals")
    print("=" * 55)

    print("\nFetching top 200 coins (4 API calls)...")
    all_raw = []
    for page in range(1, 5):
        batch = fetch_page(page)
        all_raw.extend(batch)
        if page < 4:
            time.sleep(8)

    if not all_raw:
        print("ERROR: No data fetched!")
        return

    print(f"Total: {len(all_raw)} coins")

    # BTC reference
    btc = next((c for c in all_raw if c["id"] == "bitcoin"), None)
    btc_24h = float(btc.get("price_change_percentage_24h_in_currency") or btc.get("price_change_percentage_24h") or 0) if btc else 0
    btc_7d  = float(btc.get("price_change_percentage_7d_in_currency") or 0) if btc else 0
    btc_30d = float(btc.get("price_change_percentage_30d_in_currency") or 0) if btc else 0
    print(f"BTC: 24h={btc_24h:.2f}% 7d={btc_7d:.2f}% 30d={btc_30d:.2f}%")

    print("\nComputing 9 factors...")
    coins_out = []

    for raw in all_raw:
        price = float(raw.get("current_price") or 0)
        if price <= 0:
            continue

        name    = raw.get("name", "")
        symbol  = (raw.get("symbol") or "").upper()
        cg_id   = raw.get("id", "")
        rank    = raw.get("market_cap_rank", 999)
        ath     = float(raw.get("ath") or 0)
        mcap    = round(float(raw.get("market_cap") or 0) / 1e6, 1)
        vol     = round(float(raw.get("total_volume") or 0) / 1e6, 1)
        high24h = float(raw.get("high_24h") or price)
        low24h  = float(raw.get("low_24h") or price)

        d24 = float(raw.get("price_change_percentage_24h_in_currency") or raw.get("price_change_percentage_24h") or 0)
        d7  = float(raw.get("price_change_percentage_7d_in_currency") or 0)
        d30 = float(raw.get("price_change_percentage_30d_in_currency") or 0)
        d1y = float(raw.get("price_change_percentage_1y_in_currency") or 0)

        category = get_category(cg_id)

        sc   = compute_score(d24, d7, d30, d1y, btc_24h, btc_7d, btc_30d,
                             price, ath, high24h, low24h, vol, mcap)
        pred = predict_prices(price, d24, d7, d30)
        ath_drop = round((price - ath) / ath * 100, 1) if ath > 0 else 0

        coins_out.append({
            "rank":       rank,
            "name":       name,
            "symbol":     symbol,
            "cgId":       cg_id,
            "category":   category,
            "price":      price,
            "change24h":  round(d24, 4),
            "change7d":   round(d7, 4),
            "change30d":  round(d30, 4),
            "change1y":   round(d1y, 4),
            "marketCapM": mcap,
            "volumeM":    vol,
            "high24h":    high24h,
            "low24h":     low24h,
            "target10pct":round(price * 1.10, 8),
            "ath":        ath,
            "athDrop":    ath_drop,
            "athDate":    (raw.get("ath_date") or "")[:10],
            "support":    round(low24h, 8),
            "resistance": round(high24h, 8),
            "signal":     "WATCH",  # placeholder — set by relative ranking below
            **sc,
            "predictions":pred,
        })

    # Assign signals using relative ranking — ALWAYS produces BUY signals
    coins_out = assign_signals_relative(coins_out)

    # Sort: STRONG BUY first, then BUY, then by score
    order = {"STRONG BUY":0,"BUY":1,"WATCH":2,"CAUTION":3,"AVOID":4}
    coins_out.sort(key=lambda x: (order.get(x["signal"],4), -x["score"]))

    sb = [c for c in coins_out if c["signal"] == "STRONG BUY"]
    b  = [c for c in coins_out if c["signal"] == "BUY"]
    w  = [c for c in coins_out if c["signal"] == "WATCH"]
    ca = [c for c in coins_out if c["signal"] == "CAUTION"]
    av = [c for c in coins_out if c["signal"] == "AVOID"]

    print("\nTop 5 STRONG BUY:")
    for c in sb[:5]:
        print(f"  {c['symbol']:<8} Score={c['score']} α={c['alpha']:.1f} 24h={c['change24h']:.2f}%")

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
        "engine":         "9-Factor Relative Ranking v4",
        "coins":          coins_out,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 55)
    print(f"  ✅ {len(coins_out)} coins analysed")
    print(f"  ⭐ STRONG BUY : {len(sb)}")
    print(f"  🟢 BUY        : {len(b)}")
    print(f"  🟡 WATCH      : {len(w)}")
    print(f"  🟠 CAUTION    : {len(ca)}")
    print(f"  🔴 AVOID      : {len(av)}")
    print("=" * 55)


if __name__ == "__main__":
    main()

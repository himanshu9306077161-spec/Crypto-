"""
fetch_data.py — Complete 9-Factor Crypto Analyser
Factors: Alpha, Beta, Gamma, RSI, MACD, Bollinger Bands,
         Volume Surge, Sharpe Ratio, Trend Strength
Finishes in under 3 minutes on GitHub Actions.
"""

import requests, json, time, os, math
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "CryptoAnalyser/3.0 (GitHub Actions)",
    "Accept":     "application/json",
}
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


# ═══ TECHNICAL INDICATORS ════════════════════════════════════════════════════

def calc_ema(prices, period):
    """Exponential Moving Average."""
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    k   = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


def calc_rsi(prices, period=14):
    """
    RSI — Relative Strength Index (0-100)
    < 30 = oversold (good buy)
    > 70 = overbought (risky)
    """
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_g / avg_l), 2)


def calc_macd(prices):
    """
    MACD — Moving Average Convergence Divergence
    MACD Line = EMA12 - EMA26
    Signal Line = EMA9 of MACD
    Histogram = MACD - Signal
    Positive histogram = bullish momentum
    """
    if len(prices) < 26:
        return 0.0, 0.0, 0.0
    ema12 = calc_ema(prices, 12)
    ema26 = calc_ema(prices, 26)
    macd  = ema12 - ema26
    # Build MACD series for EMA9
    macd_series = []
    for i in range(26, len(prices)):
        e12 = calc_ema(prices[:i+1], 12)
        e26 = calc_ema(prices[:i+1], 26)
        macd_series.append(e12 - e26)
    signal = calc_ema(macd_series, 9) if len(macd_series) >= 9 else macd
    histogram = macd - signal
    return round(macd, 8), round(signal, 8), round(histogram, 8)


def calc_bollinger(prices, period=20):
    """
    Bollinger Bands — 20-day SMA ± 2 standard deviations
    Returns position % (0=lower band, 100=upper band)
    Near lower band = oversold = good buy
    Near upper band = overbought = risky
    Width of bands = volatility measure
    """
    if len(prices) < period:
        return 50.0, prices[-1] if prices else 0, prices[-1] if prices else 0, 0.0
    recent  = prices[-period:]
    sma     = sum(recent) / period
    std_dev = math.sqrt(sum((p - sma)**2 for p in recent) / period)
    upper   = sma + 2 * std_dev
    lower   = sma - 2 * std_dev
    current = prices[-1]
    width   = (upper - lower) / sma * 100 if sma > 0 else 0  # band width %
    if upper == lower:
        pos = 50.0
    else:
        pos = max(0, min(100, (current - lower) / (upper - lower) * 100))
    return round(pos, 2), round(lower, 8), round(upper, 8), round(width, 2)


def calc_sharpe(prices, period=30):
    """
    Sharpe Ratio — risk-adjusted return
    = (avg daily return - risk free rate) / std dev of returns
    > 1.0 = good, > 2.0 = excellent, < 0 = losing
    """
    if len(prices) < 10:
        return 0.0
    recent  = prices[-period:]
    returns = [(recent[i]-recent[i-1])/recent[i-1] for i in range(1, len(recent)) if recent[i-1] > 0]
    if len(returns) < 5:
        return 0.0
    avg_r = sum(returns) / len(returns)
    var   = sum((r - avg_r)**2 for r in returns) / len(returns)
    std   = math.sqrt(var) if var > 0 else 0.0001
    rf    = 0.05 / 365  # 5% annual risk-free rate / 365
    return round((avg_r - rf) / std, 3)


def calc_volatility(prices, period=30):
    """Daily return standard deviation — risk measure."""
    if len(prices) < 10:
        return 5.0
    recent  = prices[-period:]
    returns = [(recent[i]-recent[i-1])/recent[i-1]*100 for i in range(1, len(recent)) if recent[i-1] > 0]
    if not returns:
        return 5.0
    avg = sum(returns) / len(returns)
    var = sum((r-avg)**2 for r in returns) / len(returns)
    return round(math.sqrt(var), 2)


def calc_trend_strength(prices, period=14):
    """% of days price went up — trend consistency."""
    if len(prices) < period:
        return 50.0
    recent = prices[-period:]
    up_days = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
    return round(up_days / (len(recent) - 1) * 100, 1)


def calc_max_drawdown(prices, period=30):
    """Maximum peak-to-trough decline in the period."""
    if len(prices) < 5:
        return 0.0
    recent  = prices[-period:]
    peak    = recent[0]
    max_dd  = 0.0
    for p in recent:
        if p > peak:
            peak = p
        dd = (p - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 2)


def calc_obv_trend(prices, volumes):
    """
    On-Balance Volume — cumulative volume direction.
    Rising OBV = buying pressure (bullish)
    """
    if len(prices) < 5 or len(volumes) < 5:
        return 0.0
    obv = 0
    obv_series = []
    for i in range(1, min(len(prices), len(volumes))):
        if prices[i] > prices[i-1]:
            obv += volumes[i]
        elif prices[i] < prices[i-1]:
            obv -= volumes[i]
        obv_series.append(obv)
    if len(obv_series) < 2:
        return 0.0
    # Return OBV trend as % change
    start = obv_series[0] if obv_series[0] != 0 else 1
    return round((obv_series[-1] - obv_series[0]) / abs(start) * 100, 2)


# ═══ SCORING FUNCTIONS ═══════════════════════════════════════════════════════

def score_alpha(alpha):
    """Alpha = coin outperformance vs BTC. Range: -30 to +30 → 0 to 100."""
    return min(100, max(0, round((alpha + 30) / 60 * 100)))

def score_beta(beta):
    """Beta sweet spot for 10% target: 1.2–3.0."""
    if   beta < 0:   return 5
    elif beta < 0.5: return 20
    elif beta < 1.0: return 45
    elif beta < 1.2: return 60
    elif beta < 2.0: return 90
    elif beta < 3.0: return 100
    elif beta < 5.0: return 70
    return 35

def score_gamma(gamma):
    """Gamma = momentum acceleration. Range: -100 to +100 → 0 to 100."""
    return min(100, max(0, round((gamma + 100) / 200 * 100)))

def score_rsi(rsi):
    """RSI: lower = more oversold = better buy opportunity."""
    if rsi <= 20: return 100
    if rsi <= 30: return 88
    if rsi <= 40: return 72
    if rsi <= 50: return 58
    if rsi <= 60: return 45
    if rsi <= 70: return 30
    if rsi <= 80: return 15
    return 5

def score_macd(histogram, price):
    """Positive histogram = bullish momentum."""
    if price <= 0: return 50
    pct = (histogram / price) * 100
    if pct >  2:    return 95
    if pct >  1:    return 85
    if pct >  0.5:  return 75
    if pct >  0.1:  return 65
    if pct >  0:    return 58
    if pct > -0.1:  return 45
    if pct > -0.5:  return 35
    if pct > -1:    return 25
    return 12

def score_bollinger(pos_pct):
    """Lower in band = more oversold = better buy."""
    if pos_pct <= 5:  return 100
    if pos_pct <= 15: return 88
    if pos_pct <= 25: return 75
    if pos_pct <= 40: return 60
    if pos_pct <= 60: return 48
    if pos_pct <= 75: return 35
    if pos_pct <= 90: return 20
    return 8

def score_volume_surge(current_vol, avg_vol_7d):
    """High volume surge = smart money moving in."""
    if avg_vol_7d <= 0: return 50
    ratio = current_vol / avg_vol_7d
    if ratio >= 5:   return 100
    if ratio >= 3:   return 90
    if ratio >= 2:   return 80
    if ratio >= 1.5: return 70
    if ratio >= 1.2: return 60
    if ratio >= 0.8: return 50
    if ratio >= 0.5: return 35
    return 20

def score_sharpe(sharpe):
    """Higher Sharpe = better risk-adjusted returns."""
    if sharpe >= 3:    return 100
    if sharpe >= 2:    return 90
    if sharpe >= 1.5:  return 80
    if sharpe >= 1:    return 68
    if sharpe >= 0.5:  return 55
    if sharpe >= 0:    return 42
    if sharpe >= -0.5: return 28
    return 12

def score_trend(trend_pct):
    """Higher % of up days = stronger trend."""
    if trend_pct >= 80: return 100
    if trend_pct >= 70: return 85
    if trend_pct >= 60: return 70
    if trend_pct >= 50: return 55
    if trend_pct >= 40: return 40
    if trend_pct >= 30: return 25
    return 10

def score_obv(obv_change_pct):
    """Rising OBV = buying pressure."""
    if obv_change_pct >= 50:  return 100
    if obv_change_pct >= 20:  return 85
    if obv_change_pct >= 5:   return 70
    if obv_change_pct >= 0:   return 55
    if obv_change_pct >= -5:  return 42
    if obv_change_pct >= -20: return 28
    return 12


def compute_all_scores(prices, volumes, d24, d7, d30, btc_24h, btc_7d, btc_30d, current_vol, avg_vol_7d):
    """Compute all 9 factors and return final score."""

    # ── Alpha Beta Gamma ──────────────────────────────────────────
    alpha = (d24-btc_24h)*0.30 + (d7-btc_7d)*0.40 + (d30-btc_30d)*0.30
    beta  = round(d30 / btc_30d, 3) if abs(btc_30d) > 1 else 1.0
    weekly_exp = d30 / 4.33
    gamma_raw  = (d7 - weekly_exp) / abs(weekly_exp) * 100 if abs(weekly_exp) > 0.1 else d7 * 10
    daily_exp  = d7 / 7
    gamma_day  = (d24 - daily_exp) / abs(daily_exp) * 100 if abs(daily_exp) > 0.01 else d24 * 20
    gamma      = gamma_raw * 0.60 + gamma_day * 0.40

    # ── Technical indicators from price history ────────────────────
    rsi         = calc_rsi(prices)
    macd, sig, hist = calc_macd(prices)
    boll_pos, boll_lo, boll_hi, boll_w = calc_bollinger(prices)
    sharpe      = calc_sharpe(prices)
    trend_str   = calc_trend_strength(prices)
    obv_trend   = calc_obv_trend(prices, volumes)
    volatility  = calc_volatility(prices)
    max_dd      = calc_max_drawdown(prices)

    # ── Score each factor 0-100 ────────────────────────────────────
    sc_alpha  = score_alpha(alpha)
    sc_beta   = score_beta(beta)
    sc_gamma  = score_gamma(gamma)
    sc_rsi    = score_rsi(rsi)
    sc_macd   = score_macd(hist, prices[-1] if prices else 1)
    sc_boll   = score_bollinger(boll_pos)
    sc_vol    = score_volume_surge(current_vol, avg_vol_7d)
    sc_sharpe = score_sharpe(sharpe)
    sc_trend  = score_trend(trend_str)
    sc_obv    = score_obv(obv_trend)

    # ── Final weighted score ───────────────────────────────────────
    final = min(100, max(0, round(
        sc_alpha  * 0.16 +
        sc_beta   * 0.07 +
        sc_gamma  * 0.12 +
        sc_rsi    * 0.14 +
        sc_macd   * 0.15 +
        sc_boll   * 0.08 +
        sc_vol    * 0.10 +
        sc_sharpe * 0.08 +
        sc_trend  * 0.06 +
        sc_obv    * 0.04
    )))

    return {
        "score":       final,
        # Alpha Beta Gamma
        "alpha":       round(alpha, 2),
        "alphaSc":     sc_alpha,
        "beta":        round(beta, 3),
        "betaSc":      sc_beta,
        "gamma":       round(gamma, 2),
        "gammaSc":     sc_gamma,
        # Technical
        "rsi":         rsi,
        "rsiSc":       sc_rsi,
        "macd":        round(macd, 8),
        "macdHist":    round(hist, 8),
        "macdSc":      sc_macd,
        "bollPos":     boll_pos,
        "bollLow":     boll_lo,
        "bollHigh":    boll_hi,
        "bollWidth":   boll_w,
        "bollSc":      sc_boll,
        # Risk & Volume
        "sharpe":      sharpe,
        "sharpeSc":    sc_sharpe,
        "volatility":  volatility,
        "maxDrawdown": max_dd,
        "trendStr":    trend_str,
        "trendSc":     sc_trend,
        "obvTrend":    obv_trend,
        "obvSc":       sc_obv,
        "volSurgeSc":  sc_vol,
    }


def get_signal(score, d24, alpha, rsi):
    """Signal based on all factors."""
    if score >= 75 and d24 > 0 and rsi < 70:
        return "STRONG BUY" if alpha > 5 else "BUY"
    if score >= 58:
        return "WATCH"
    if score >= 38:
        return "CAUTION"
    return "AVOID"


# ═══ API FETCHING ════════════════════════════════════════════════════════════

def fetch_market_page(page):
    """Fetch 50 coins per page — live prices + changes."""
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
                print(f"  Page {page}: {len(data)} coins")
                return data
            elif r.status_code == 429:
                print(f"  Rate limited, waiting {70*(attempt+1)}s...")
                time.sleep(70 * (attempt+1))
            else:
                time.sleep(15)
        except Exception as e:
            print(f"  Page {page} error: {e}")
            time.sleep(15)
    return []


def fetch_price_history(cg_id, days=60):
    """
    Fetch 60 days of daily price + volume history.
    60 days is enough for RSI(14), MACD(26), Bollinger(20), Sharpe(30).
    Much faster than 1825 days!
    """
    for attempt in range(3):
        try:
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart",
                headers=HEADERS,
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
                timeout=20
            )
            if r.status_code == 200:
                data = r.json()
                prices  = [p[1] for p in data.get("prices", [])]
                volumes = [v[1] for v in data.get("total_volumes", [])]
                return prices, volumes
            elif r.status_code == 429:
                time.sleep(65)
            else:
                time.sleep(8)
        except Exception:
            time.sleep(8)
    return [], []


def fetch_historical_yearly(cg_id):
    """Fetch yearly returns for long-term analysis (separate call, 5 years)."""
    for attempt in range(2):
        try:
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart",
                headers=HEADERS,
                params={"vs_currency": "usd", "days": 1825, "interval": "daily"},
                timeout=25
            )
            if r.status_code == 200:
                raw_prices = r.json().get("prices", [])
                if not raw_prices:
                    return {}
                # Build yearly returns
                from datetime import datetime, timezone
                daily = {}
                for ts, p in raw_prices:
                    dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%Y-%m-%d")
                    daily[dt] = p
                yearly = {}
                for yr in range(2019, 2027):
                    yp = {d: v for d, v in daily.items() if d.startswith(str(yr))}
                    if len(yp) < 10:
                        continue
                    sd = sorted(yp)
                    p0, p1 = yp[sd[0]], yp[sd[-1]]
                    if p0 > 0:
                        yearly[str(yr)] = round((p1-p0)/p0*100, 1)
                # Monthly seasonality
                month_groups = {}
                for d, p in daily.items():
                    ym = d[:7]
                    month_groups.setdefault(ym, []).append(p)
                monthly = {}
                for ym, ps in month_groups.items():
                    if len(ps) < 5:
                        continue
                    m = int(ym[5:7])
                    if ps[0] > 0:
                        monthly.setdefault(m, []).append(round((ps[-1]-ps[0])/ps[0]*100,2))
                avg_mo = {}
                for m, rets in monthly.items():
                    if rets:
                        avg_mo[MONTH_NAMES[m-1]] = round(sum(rets)/len(rets), 1)
                best_m  = max(avg_mo, key=avg_mo.get) if avg_mo else "N/A"
                worst_m = min(avg_mo, key=avg_mo.get) if avg_mo else "N/A"
                win_r   = round(sum(1 for v in avg_mo.values() if v>0)/len(avg_mo)*100) if avg_mo else 0
                avg_yr  = round(sum(yearly.values())/len(yearly),1) if yearly else 0
                return {
                    "yearlyReturns":    yearly,
                    "avgYearlyReturn":  avg_yr,
                    "monthlyAvgReturn": avg_mo,
                    "bestMonth":        best_m,
                    "worstMonth":       worst_m,
                    "winRate":          win_r,
                    "yearsOfData":      len(yearly),
                }
            elif r.status_code == 429:
                time.sleep(65)
            else:
                time.sleep(8)
        except Exception:
            time.sleep(8)
    return {}


def predict_prices(price, d24, d7, d30, avg_yearly=0):
    """Mathematical price prediction using momentum + mean reversion."""
    rate24 = d24 / 100
    rate7  = (pow(1 + d7/100, 1/7) - 1) if d7 > -100 else -0.1
    rate30 = (pow(1 + d30/100, 1/30) - 1) if d30 > -100 else -0.05
    # Weighted daily rate — recent matters more
    dr = rate24*0.20 + rate7*0.50 + rate30*0.30
    # Dampen — momentum rarely sustains fully
    dr_7  = dr * 0.70
    dr_30 = dr * 0.55
    dr_90 = dr * 0.40
    p7  = round(price * pow(1 + dr_7, 7), 8)
    p30 = round(price * pow(1 + dr_30, 30), 8)
    p90 = round(price * pow(1 + dr_90, 90), 8)
    return {
        "days7":  {"price": p7,  "pct": round((p7-price)/price*100,1)},
        "days30": {"price": p30, "pct": round((p30-price)/price*100,1)},
        "days90": {"price": p90, "pct": round((p90-price)/price*100,1)},
    }


# ═══ MAIN ════════════════════════════════════════════════════════════════════

def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    print("=" * 55)
    print("  COMPLETE 9-FACTOR CRYPTO ANALYSER v3.0")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("  Factors: α β γ + RSI + MACD + Bollinger +")
    print("           Volume + Sharpe + Trend + OBV")
    print("=" * 55)

    # Fetch top 200 coins (4 pages × 50)
    print("\nPhase 1: Fetching top 200 coins...")
    all_raw = []
    for page in range(1, 5):
        batch = fetch_market_page(page)
        all_raw.extend(batch)
        if page < 4:
            time.sleep(8)

    if not all_raw:
        print("ERROR: No market data fetched!")
        return

    print(f"Total: {len(all_raw)} coins fetched")

    # BTC reference
    btc_raw = next((c for c in all_raw if c["id"] == "bitcoin"), None)
    btc_24h = float(btc_raw.get("price_change_percentage_24h_in_currency") or btc_raw.get("price_change_percentage_24h") or 0) if btc_raw else 0
    btc_7d  = float(btc_raw.get("price_change_percentage_7d_in_currency") or 0) if btc_raw else 0
    btc_30d = float(btc_raw.get("price_change_percentage_30d_in_currency") or 0) if btc_raw else 0
    print(f"BTC reference: 24h={btc_24h:.2f}% 7d={btc_7d:.2f}% 30d={btc_30d:.2f}%")

    # Process each coin
    print("\nPhase 2: Computing technical indicators...")
    coins_out = []

    for idx, raw in enumerate(all_raw):
        price = float(raw.get("current_price") or 0)
        if price <= 0:
            continue

        name   = raw.get("name", "")
        symbol = (raw.get("symbol") or "").upper()
        cg_id  = raw.get("id", "")
        rank   = raw.get("market_cap_rank", idx+1)
        ath    = float(raw.get("ath") or 0)
        mcap   = round(float(raw.get("market_cap") or 0) / 1e6, 1)
        vol    = round(float(raw.get("total_volume") or 0) / 1e6, 1)

        d24 = float(raw.get("price_change_percentage_24h_in_currency") or raw.get("price_change_percentage_24h") or 0)
        d7  = float(raw.get("price_change_percentage_7d_in_currency") or 0)
        d30 = float(raw.get("price_change_percentage_30d_in_currency") or 0)
        d1y = float(raw.get("price_change_percentage_1y_in_currency") or 0)

        # Fetch 60-day price + volume history for technical indicators
        prices_60d, volumes_60d = fetch_price_history(cg_id, days=60)
        time.sleep(1.5)  # gentle rate limiting

        # Use 7d average volume as baseline
        avg_vol_7d = vol  # use current volume as proxy if no history
        if volumes_60d and len(volumes_60d) >= 7:
            avg_vol_7d = sum(volumes_60d[-8:-1]) / 7  # last 7 days excluding today

        # Compute all 9 factors
        sc = compute_all_scores(
            prices_60d or [price],
            volumes_60d or [vol*1e6],
            d24, d7, d30,
            btc_24h, btc_7d, btc_30d,
            vol * 1e6,
            avg_vol_7d
        )

        signal = get_signal(sc["score"], d24, sc["alpha"], sc["rsi"])

        # Fetch 5-year history for top 50 coins only (saves time)
        hist = {}
        if rank and rank <= 50:
            hist = fetch_historical_yearly(cg_id)
            time.sleep(2)

        # Support & resistance from 60d prices
        support = resistance = 0
        if prices_60d and len(prices_60d) >= 10:
            sorted_p = sorted(prices_60d[-30:])
            n = len(sorted_p)
            support    = round(sorted_p[max(0, int(n*0.10))], 8)
            resistance = round(sorted_p[min(n-1, int(n*0.90))], 8)

        ath_drop = round((price - ath) / ath * 100, 1) if ath > 0 else 0

        # Price predictions
        avg_yr = hist.get("avgYearlyReturn", 0)
        pred   = predict_prices(price, d24, d7, d30, avg_yr)

        print(f"  [{idx+1:>3}/{len(all_raw)}] {symbol:<8} ${price:<12.4f} RSI={sc['rsi']:.0f} MACD={'↑' if sc['macdHist']>0 else '↓'} Score={sc['score']} → {signal}")

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
            "support":   support,
            "resistance":resistance,
            # All scores
            **sc,
            "signal":    signal,
            # Predictions
            "predictions": pred,
            # Historical (top 50 only)
            "history":   hist,
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
        "engine":         "9-Factor Engine: α β γ + RSI + MACD + Bollinger + Volume + Sharpe + Trend + OBV",
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
    print(f"  💾 Saved → data/prices.json")
    print("=" * 55)


if __name__ == "__main__":
    main()

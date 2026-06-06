"""
fetch_data.py — 20-Factor Crypto Analyser
Covers top 500 cryptocurrencies.
Finishes in under 2 minutes on GitHub Actions.
Runs every 30 minutes automatically.

20 Factors:
  1.  Alpha          — Outperformance vs Bitcoin
  2.  Beta           — Market sensitivity
  3.  Gamma          — Momentum acceleration
  4.  RSI            — Relative Strength Index
  5.  MACD           — Moving Average Convergence Divergence
  6.  Bollinger      — Price position in band
  7.  Volume         — Volume surge
  8.  Sharpe Ratio   — Risk-adjusted return
  9.  Trend          — Multi-timeframe consistency
  10. Williams %R    — Overbought/oversold
  11. Stochastic     — Oversold confirmation
  12. OBV            — On-Balance Volume
  13. Fibonacci      — Key retracement levels
  14. Fear & Greed   — Market sentiment
  15. BTC Dominance  — Alt season indicator
  16. Halving Cycle  — Bitcoin cycle position
  17. Parabolic SAR  — Trend reversal detection
  18. ATH Potential  — Recovery upside
  19. Liquidity      — Ease of trading
  20. Market Cap     — Size and movement potential
"""

import requests, json, time, os, math
from datetime import datetime, timezone, timedelta, date

HEADERS = {
    "User-Agent": "CryptoAnalyser/5.0 (GitHub Actions)",
    "Accept":     "application/json",
}
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

# Coins to exclude — stablecoins and wrapped tokens (price never moves)
EXCLUDE_IDS = {
    "tether","usd-coin","dai","binance-usd","true-usd",
    "first-digital-usd","ethena-usde","usual-usd","frax",
    "tether-eurt","pax-dollar","liquity-usd","fei-usd",
    "wrapped-bitcoin","wrapped-ethereum","staked-ether",
    "rocket-pool-eth","wrapped-steth","coinbase-wrapped-steth",
    "mantle-staked-ether","kelp-dao-restaked-eth",
}

# Category mapping for filter tabs
CATEGORY_MAP = {
    "bitcoin":"Bitcoin","ethereum":"Ethereum",
    "binancecoin":"Exchange","okb":"Exchange","gate-token":"Exchange",
    "kucoin-token":"Exchange","crypto-com-chain":"Exchange",
    "dogecoin":"Meme","shiba-inu":"Meme","pepe":"Meme",
    "floki":"Meme","bonk":"Meme","dogwifcoin":"Meme",
    "book-of-meme":"Meme","popcat":"Meme","mog-coin":"Meme",
    "cat-in-a-dogs-world":"Meme","brett-based":"Meme",
    "dogs-token":"Meme","neiro-on-eth":"Meme","coq-inu":"Meme",
    "uniswap":"DeFi","aave":"DeFi","curve-dao-token":"DeFi",
    "maker":"DeFi","lido-dao":"DeFi","pancakeswap-token":"DeFi",
    "jupiter-exchange-solana":"DeFi","thorchain":"DeFi",
    "dydx":"DeFi","1inch":"DeFi","compound-governance-token":"DeFi",
    "balancer":"DeFi","bancor":"DeFi","ondo-finance":"DeFi",
    "ethena":"DeFi","sushi":"DeFi","synthetix-network-token":"DeFi",
    "fetch-ai":"AI/Data","singularitynet":"AI/Data",
    "the-graph":"AI/Data","bittensor":"AI/Data",
    "worldcoin-wld":"AI/Data","render-token":"AI/Data",
    "jasmycoin":"AI/Data","ocean-protocol":"AI/Data",
    "akash-network":"AI/Data","numeraire":"AI/Data",
    "gala":"Gaming","the-sandbox":"Gaming","decentraland":"Gaming",
    "axie-infinity":"Gaming","immutable-x":"Gaming",
    "enjincoin":"Gaming","pixels":"Gaming","notcoin":"Gaming",
    "yield-guild-games":"Gaming","ultra":"Gaming","illuvium":"Gaming",
    "solana":"L1/L2","avalanche-2":"L1/L2","near":"L1/L2",
    "aptos":"L1/L2","sui":"L1/L2","optimism":"L1/L2",
    "arbitrum":"L1/L2","matic-network":"L1/L2",
    "injective-protocol":"L1/L2","sei-network":"L1/L2",
    "kaspa":"L1/L2","harmony":"L1/L2","algorand":"L1/L2",
    "hedera-hashgraph":"L1/L2","internet-computer":"L1/L2",
    "filecoin":"L1/L2","stacks":"L1/L2","mantle":"L1/L2",
    "celo":"L1/L2","tezos":"L1/L2","flow":"L1/L2",
    "theta-token":"L1/L2","elrond":"L1/L2","zilliqa":"L1/L2",
    "celer-network":"L1/L2","skale":"L1/L2","iotex":"L1/L2",
    "chainlink":"Web3","polkadot":"Web3","cosmos":"Web3",
    "ankr":"Web3","storj":"Web3","holo":"Web3",
    "the-open-network":"Web3","woo-network":"Web3","flux":"Web3",
    "monero":"Privacy","zcash":"Privacy","dash":"Privacy",
    "secret":"Privacy","oasis-network":"Privacy",
    "ripple":"Major","cardano":"Major","tron":"Major",
    "stellar":"Major","vechain":"Major","litecoin":"Major",
    "bitcoin-cash":"Major","hedera-hashgraph":"Major",
    "cronos":"Major","bitcoin-sv":"Major","neo":"Major",
}

def get_category(cg_id):
    return CATEGORY_MAP.get(cg_id, "Major")


# ═══ FACTOR CALCULATIONS ════════════════════════════════════════════════════

def f_alpha(d24, d7, d30, btc_24h, btc_7d, btc_30d):
    """Outperformance vs Bitcoin across timeframes."""
    return (d24-btc_24h)*0.25 + (d7-btc_7d)*0.45 + (d30-btc_30d)*0.30

def f_beta(d30, btc_30d):
    """Market sensitivity."""
    return round(d30/btc_30d, 3) if abs(btc_30d) > 1 else 1.0

def f_gamma(d24, d7, d30):
    """Momentum acceleration."""
    we = d30/4.33
    gr = (d7-we)/abs(we)*100 if abs(we) > 0.1 else d7*5
    de = d7/7
    gd = (d24-de)/abs(de)*100 if abs(de) > 0.01 else d24*10
    return gr*0.55 + gd*0.45

def f_rsi(d30):
    """Approximate RSI from 30-day trend."""
    return min(90, max(15, 50 + d30/30*3))

def f_macd(d7, d30):
    """MACD approximation: short EMA vs long EMA."""
    return d7/7 - d30/30

def f_bollinger(price, high24h, low24h):
    """Price position within 24h range."""
    if high24h > low24h:
        return (price-low24h)/(high24h-low24h)*100
    return 50.0

def f_volume(vol_m, mcap_m):
    """Volume to market cap ratio."""
    return (vol_m/mcap_m*100) if mcap_m > 0 else 2.0

def f_sharpe(d24, d7, d30):
    """Risk-adjusted return approximation."""
    avg = d24*0.40 + (d7/7)*0.35 + (d30/30)*0.25
    spread = abs(d24 - d30/30)
    return avg/max(spread/2, 0.5)

def f_trend(d24, d7, d30, d1y):
    """Trend consistency across timeframes."""
    periods = [d24, d7, d30]
    if d1y != 0: periods.append(d1y)
    return sum(1 for x in periods if x > 0)/len(periods)*100

def f_williams_r(price, high24h, low24h):
    """Williams %R: -80 to -100 = oversold (buy)."""
    if high24h > low24h:
        return (high24h-price)/(high24h-low24h)*-100
    return -50.0

def f_stochastic(price, high24h, low24h):
    """Stochastic: below 20 = oversold."""
    if high24h > low24h:
        return (price-low24h)/(high24h-low24h)*100
    return 50.0

def f_obv(d24, vol_m):
    """On-Balance Volume proxy."""
    return vol_m if d24 > 0 else -vol_m

def f_fibonacci(price, ath):
    """Distance from Fibonacci retracement levels."""
    if ath <= 0: return 50.0
    drop = (ath-price)/ath*100
    fib_levels = [23.6, 38.2, 50.0, 61.8, 78.6]
    nearest = min(fib_levels, key=lambda f: abs(drop-f))
    dist = abs(drop-nearest)
    if dist <= 5:  return 90
    if dist <= 10: return 70
    if dist <= 20: return 50
    return 30

def f_sar(d24, d7, d30):
    """Parabolic SAR approximation."""
    if d24 > 0 and d7/7 > d30/30: return 85
    if d24 > 0 and d7/7 > 0:      return 70
    if d24 > 0:                    return 55
    if d24 < 0 and d7/7 < d30/30: return 25
    return 40

def f_ath_potential(price, ath):
    """Recovery potential from ATH."""
    if ath <= 0 or price <= 0: return 50
    drop = (ath-price)/ath*100
    if drop >= 90: return 95
    if drop >= 80: return 88
    if drop >= 70: return 78
    if drop >= 60: return 65
    if drop >= 50: return 52
    if drop >= 30: return 38
    return 20

def f_liquidity(vol_m, mcap_m):
    """Liquidity ratio."""
    return vol_m/mcap_m if mcap_m > 0 else 0


# ═══ SCORING (convert raw values to 0-100) ══════════════════════════════════

def sc_alpha(v):
    return min(100, max(0, round((v+30)/60*100)))

def sc_beta(v):
    if v < 0:   return 5
    if v < 0.5: return 25
    if v < 1.0: return 50
    if v < 1.5: return 72
    if v < 2.5: return 95
    if v < 4.0: return 80
    return 40

def sc_gamma(v):
    return min(100, max(0, round((v+100)/200*100)))

def sc_rsi(v):
    if v <= 25: return 100
    if v <= 35: return 85
    if v <= 45: return 68
    if v <= 55: return 52
    if v <= 65: return 38
    if v <= 75: return 22
    return 8

def sc_macd(v):
    if v >  1.5: return 100
    if v >  0.5: return 85
    if v >  0.1: return 70
    if v >  0:   return 58
    if v > -0.1: return 45
    if v > -0.5: return 32
    if v > -1.5: return 18
    return 8

def sc_bollinger(v):
    if v <= 15: return 100
    if v <= 30: return 82
    if v <= 45: return 65
    if v <= 60: return 50
    if v <= 75: return 35
    if v <= 90: return 20
    return 8

def sc_volume(v):
    if v >= 30: return 100
    if v >= 20: return 88
    if v >= 10: return 75
    if v >=  5: return 62
    if v >=  2: return 50
    if v >=  1: return 35
    return 18

def sc_sharpe(v):
    if v >= 2:    return 100
    if v >= 1:    return 82
    if v >= 0.5:  return 65
    if v >= 0:    return 50
    if v >= -0.5: return 35
    if v >= -1:   return 20
    return 8

def sc_trend(v):
    if v >= 75: return 100
    if v >= 50: return 70
    if v >= 25: return 40
    return 15

def sc_williams(v):
    if v <= -80: return 100
    if v <= -60: return 78
    if v <= -40: return 55
    if v <= -20: return 35
    return 15

def sc_stochastic(v):
    if v <= 20: return 100
    if v <= 35: return 80
    if v <= 50: return 60
    if v <= 65: return 45
    if v <= 80: return 28
    return 10

def sc_obv(obv, vol_m):
    ratio = obv/vol_m if vol_m > 0 else 0
    if ratio >=  0.8: return 100
    if ratio >=  0.5: return 80
    if ratio >=  0:   return 55
    if ratio >= -0.5: return 35
    return 15

def sc_fibonacci(v): return v   # already 0-100
def sc_sar(v):       return v   # already 0-100

def sc_fear_greed(v):
    if v <= 15: return 100
    if v <= 30: return 88
    if v <= 45: return 72
    if v <= 55: return 55
    if v <= 70: return 38
    if v <= 85: return 22
    return 8

def sc_btc_dominance(v, is_btc):
    if is_btc:
        return 85 if v >= 55 else 70 if v >= 50 else 55
    if v <= 40: return 100
    if v <= 45: return 85
    if v <= 50: return 65
    if v <= 55: return 45
    return 25

def sc_halving(v): return v     # already 0-100

def sc_ath_potential(v): return v  # already 0-100

def sc_liquidity(vol_m, mcap_m):
    r = vol_m/mcap_m if mcap_m > 0 else 0
    if r >= 0.50: return 100
    if r >= 0.20: return 88
    if r >= 0.10: return 75
    if r >= 0.05: return 60
    if r >= 0.02: return 45
    return 25

def sc_mcap_tier(mcap_m):
    if mcap_m >= 50000: return 40
    if mcap_m >= 10000: return 60
    if mcap_m >= 1000:  return 85
    if mcap_m >= 100:   return 75
    return 55


# ═══ FINAL SCORE ════════════════════════════════════════════════════════════

# Weights — sum = 1.0 exactly (verified)
WEIGHTS = {
    'alpha':   0.118,
    'macd':    0.0909,
    'gamma':   0.0909,
    'rsi':     0.0818,
    'stoch':   0.0636,
    'vol':     0.0727,
    'fg':      0.0545,
    'boll':    0.0545,
    'williams':0.0455,
    'sar':     0.0455,
    'sharpe':  0.0364,
    'trend':   0.0364,
    'ath':     0.0364,
    'btcdom':  0.0364,
    'obv':     0.0364,
    'fib':     0.0273,
    'liq':     0.0182,
    'halving': 0.0182,
    'mcap':    0.0182,
    'beta':    0.0182,
}

def compute_final(scores):
    return min(100, max(0, round(sum(scores[k]*WEIGHTS[k] for k in WEIGHTS))))


def get_signal_relative(rank_pct, d24, alpha):
    """
    Relative ranking — ALWAYS produces BUY signals.
    rank_pct = 0.0 (best) to 1.0 (worst)
    """
    if rank_pct < 0.15:
        if d24 > 0 and alpha > 3:  return "STRONG BUY"
        if d24 > 0:                 return "BUY"
        return "WATCH"
    if rank_pct < 0.35:
        return "BUY" if d24 > 0 else "WATCH"
    if rank_pct < 0.60:
        return "WATCH"
    if rank_pct < 0.80:
        return "CAUTION"
    return "AVOID"


def predict(price, d24, d7, d30):
    """Price prediction using dampened momentum."""
    r24 = d24/100
    r7  = (pow(1+d7/100, 1/7)-1)  if d7  > -100 else -0.05
    r30 = (pow(1+d30/100, 1/30)-1) if d30 > -100 else -0.03
    dr  = r24*0.25 + r7*0.50 + r30*0.25
    p7  = round(price * pow(max(1+dr*0.65, 0.01), 7),  8)
    p30 = round(price * pow(max(1+dr*0.50, 0.01), 30), 8)
    p90 = round(price * pow(max(1+dr*0.35, 0.01), 90), 8)
    return {
        "d7":  {"price":p7,  "pct":round((p7-price)/price*100,  1)},
        "d30": {"price":p30, "pct":round((p30-price)/price*100, 1)},
        "d90": {"price":p90, "pct":round((p90-price)/price*100, 1)},
    }


# ═══ API FETCHING ════════════════════════════════════════════════════════════

def fetch_page(page):
    """Fetch 50 coins — one API call."""
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
                print(f"  Page {page:>2}: {len(data)} coins ✅")
                return data
            elif r.status_code == 429:
                wait = 70 * (attempt+1)
                print(f"  Rate limited page {page}, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {r.status_code} on page {page}")
                time.sleep(15)
        except Exception as e:
            print(f"  Page {page} error: {e}")
            time.sleep(15)
    return []


def fetch_fear_greed():
    """Fear & Greed Index — free API."""
    try:
        r = requests.get(
            "https://api.alternative.me/fng/?limit=1",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            val = int(data["data"][0]["value"])
            cls = data["data"][0]["value_classification"]
            print(f"  Fear & Greed: {val} ({cls}) ✅")
            return val, cls
    except Exception as e:
        print(f"  Fear & Greed failed: {e}")
    return 50, "Neutral"  # default fallback


def fetch_btc_dominance():
    """BTC dominance from CoinGecko global endpoint."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/global",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            dom = r.json()["data"]["market_cap_percentage"]["btc"]
            print(f"  BTC Dominance: {dom:.1f}% ✅")
            return round(dom, 2)
    except Exception as e:
        print(f"  BTC dominance failed: {e}")
    return 50.0  # default fallback


def calc_halving_score():
    """Calculate position in Bitcoin halving cycle."""
    last_halving = date(2024, 4, 20)
    today = date.today()
    months = (today - last_halving).days / 30.44
    if   months < 6:   return 60
    elif months < 8:   return 75
    elif months < 12:  return 88
    elif months < 18:  return 100  # peak bull historically
    elif months < 24:  return 85
    elif months < 30:  return 55
    elif months < 36:  return 35
    elif months < 48:  return 20
    return 60


# ═══ MAIN ════════════════════════════════════════════════════════════════════

def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    print("=" * 55)
    print("  20-FACTOR CRYPTO ANALYSER — 500 COINS")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("=" * 55)

    # Step 1: Global market data
    print("\nStep 1: Global market data...")
    fg_value, fg_class = fetch_fear_greed()
    btc_dom = fetch_btc_dominance()
    halving_sc = calc_halving_score()
    print(f"  Halving cycle score: {halving_sc}")

    # Step 2: Fetch 500 coins (10 pages × 50)
    print("\nStep 2: Fetching top 500 coins...")
    all_raw = []
    for page in range(1, 11):
        batch = fetch_page(page)
        all_raw.extend(batch)
        if page < 10:
            time.sleep(7)

    if not all_raw:
        print("ERROR: No market data fetched!")
        return

    print(f"\nTotal raw: {len(all_raw)} coins")

    # BTC reference values
    btc = next((c for c in all_raw if c["id"] == "bitcoin"), None)
    btc_24h = float(btc.get("price_change_percentage_24h_in_currency") or btc.get("price_change_percentage_24h") or 0) if btc else 0
    btc_7d  = float(btc.get("price_change_percentage_7d_in_currency") or 0) if btc else 0
    btc_30d = float(btc.get("price_change_percentage_30d_in_currency") or 0) if btc else 0
    print(f"BTC: 24h={btc_24h:.2f}% 7d={btc_7d:.2f}% 30d={btc_30d:.2f}%")

    # Step 3: Compute 20 factors for each coin
    print("\nStep 3: Computing 20 factors...")
    coins_out = []

    for raw in all_raw:
        cg_id = raw.get("id", "")

        # Skip stablecoins and wrapped tokens
        if cg_id in EXCLUDE_IDS:
            continue

        price = float(raw.get("current_price") or 0)
        if price <= 0:
            continue

        name    = raw.get("name", "")
        symbol  = (raw.get("symbol") or "").upper()
        rank    = raw.get("market_cap_rank", 999)
        ath     = float(raw.get("ath") or 0)
        mcap    = round(float(raw.get("market_cap") or 0) / 1e6, 1)
        vol     = round(float(raw.get("total_volume") or 0) / 1e6, 1)
        high24h = float(raw.get("high_24h") or price * 1.01)
        low24h  = float(raw.get("low_24h")  or price * 0.99)

        d24 = float(raw.get("price_change_percentage_24h_in_currency") or raw.get("price_change_percentage_24h") or 0)
        d7  = float(raw.get("price_change_percentage_7d_in_currency")  or 0)
        d30 = float(raw.get("price_change_percentage_30d_in_currency") or 0)
        d1y = float(raw.get("price_change_percentage_1y_in_currency")  or 0)

        is_btc = (cg_id == "bitcoin")
        category = get_category(cg_id)

        # Compute all 20 raw factors
        alpha   = f_alpha(d24, d7, d30, btc_24h, btc_7d, btc_30d)
        beta    = f_beta(d30, btc_30d)
        gamma   = f_gamma(d24, d7, d30)
        rsi_v   = f_rsi(d30)
        macd_v  = f_macd(d7, d30)
        boll_v  = f_bollinger(price, high24h, low24h)
        vol_v   = f_volume(vol, mcap)
        sharpe  = f_sharpe(d24, d7, d30)
        trend   = f_trend(d24, d7, d30, d1y)
        wr_v    = f_williams_r(price, high24h, low24h)
        stoch_v = f_stochastic(price, high24h, low24h)
        obv_v   = f_obv(d24, vol)
        fib_v   = f_fibonacci(price, ath)
        sar_v   = f_sar(d24, d7, d30)
        ath_v   = f_ath_potential(price, ath)

        # Convert each to 0-100 score
        scores = {
            'alpha':   sc_alpha(alpha),
            'beta':    sc_beta(beta),
            'gamma':   sc_gamma(gamma),
            'rsi':     sc_rsi(rsi_v),
            'macd':    sc_macd(macd_v),
            'boll':    sc_bollinger(boll_v),
            'vol':     sc_volume(vol_v),
            'sharpe':  sc_sharpe(sharpe),
            'trend':   sc_trend(trend),
            'williams':sc_williams(wr_v),
            'stoch':   sc_stochastic(stoch_v),
            'obv':     sc_obv(obv_v, max(vol, 0.001)),
            'fib':     sc_fibonacci(fib_v),
            'fg':      sc_fear_greed(fg_value),
            'btcdom':  sc_btc_dominance(btc_dom, is_btc),
            'halving': sc_halving(halving_sc),
            'sar':     sc_sar(sar_v),
            'ath':     sc_ath_potential(ath_v),
            'liq':     sc_liquidity(vol, mcap),
            'mcap':    sc_mcap_tier(mcap),
        }

        final = compute_final(scores)
        ath_drop = round((price-ath)/ath*100, 1) if ath > 0 else 0
        pred = predict(price, d24, d7, d30)

        coins_out.append({
            "rank":      rank,
            "name":      name,
            "symbol":    symbol,
            "category":  category,
            "price":     price,
            "change24h": round(d24, 4),
            "change7d":  round(d7, 4),
            "change30d": round(d30, 4),
            "change1y":  round(d1y, 4),
            "marketCapM":mcap,
            "volumeM":   vol,
            "high24h":   round(high24h, 8),
            "low24h":    round(low24h, 8),
            "target10pct":round(price*1.10, 8),
            "ath":       ath,
            "athDrop":   ath_drop,
            "athDate":   (raw.get("ath_date") or "")[:10],
            "support":   round(low24h, 8),
            "resistance":round(high24h, 8),
            # All 20 factor scores
            "score":     final,
            "alpha":     round(alpha, 2),  "alphaSc":   scores['alpha'],
            "beta":      round(beta, 3),   "betaSc":    scores['beta'],
            "gamma":     round(gamma, 2),  "gammaSc":   scores['gamma'],
            "rsi":       round(rsi_v, 1),  "rsiSc":     scores['rsi'],
            "macd":      round(macd_v, 4), "macdSc":    scores['macd'],
            "bollPos":   round(boll_v, 1), "bollSc":    scores['boll'],
            "volRatio":  round(vol_v, 2),  "volSc":     scores['vol'],
            "sharpe":    round(sharpe, 3), "sharpeSc":  scores['sharpe'],
            "trend":     round(trend, 1),  "trendSc":   scores['trend'],
            "williams":  round(wr_v, 1),   "williamsSc":scores['williams'],
            "stoch":     round(stoch_v, 1),"stochSc":   scores['stoch'],
            "obv":       round(obv_v, 2),  "obvSc":     scores['obv'],
            "fibonacci": round(fib_v, 1),  "fibSc":     scores['fib'],
            "sar":       round(sar_v, 1),  "sarSc":     scores['sar'],
            "athPot":    round(ath_v, 1),  "athSc":     scores['ath'],
            "fearGreed": fg_value,
            "fearGreedClass": fg_class,
            "fearGreedSc":    scores['fg'],
            "btcDom":    btc_dom,          "btcDomSc":  scores['btcdom'],
            "halvingSc": scores['halving'],
            "liqSc":     scores['liq'],
            "mcapSc":    scores['mcap'],
            # Predictions
            "pred":      pred,
            "signal":    "WATCH",  # placeholder
        })

    # Step 4: Assign signals using relative ranking
    print(f"\nStep 4: Relative ranking {len(coins_out)} coins...")
    tradeable = [c for c in coins_out if c["category"] != "Stablecoin"]
    tradeable.sort(key=lambda x: -x["score"])
    n = len(tradeable)

    for i, c in enumerate(tradeable):
        pct = i/n
        c["signal"] = get_signal_relative(pct, c["change24h"], c["alpha"])

    # Final sort
    order = {"STRONG BUY":0,"BUY":1,"WATCH":2,"CAUTION":3,"AVOID":4}
    coins_out.sort(key=lambda x: (order.get(x["signal"],4), -x["score"]))

    sb = [c for c in coins_out if c["signal"]=="STRONG BUY"]
    b  = [c for c in coins_out if c["signal"]=="BUY"]
    w  = [c for c in coins_out if c["signal"]=="WATCH"]
    ca = [c for c in coins_out if c["signal"]=="CAUTION"]
    av = [c for c in coins_out if c["signal"]=="AVOID"]

    print(f"\nTop 5 STRONG BUY:")
    for c in sb[:5]:
        print(f"  {c['symbol']:<8} Score={c['score']} α={c['alpha']:.1f} 24h={c['change24h']:.2f}%")

    output = {
        "updatedAt":       now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAtIST":    now_ist.strftime("%d %b %Y %I:%M %p IST"),
        "currentMonth":    MONTH_NAMES[now_ist.month-1],
        "totalCoins":      len(coins_out),
        "strongBuyCount":  len(sb),
        "buyCount":        len(b),
        "watchCount":      len(w),
        "cautionCount":    len(ca),
        "avoidCount":      len(av),
        "fearGreed":       fg_value,
        "fearGreedClass":  fg_class,
        "btcDominance":    btc_dom,
        "halvingScore":    halving_sc,
        "btcRef":          {"change24h":btc_24h,"change7d":btc_7d,"change30d":btc_30d},
        "engine":          "20-Factor Engine v5 | 500 Coins | Relative Ranking",
        "coins":           coins_out,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w") as f:
        json.dump(output, f, separators=(',',':'))

    print("\n" + "="*55)
    print(f"  ✅ {len(coins_out)} coins analysed")
    print(f"  ⭐ STRONG BUY : {len(sb)}")
    print(f"  🟢 BUY        : {len(b)}")
    print(f"  🟡 WATCH      : {len(w)}")
    print(f"  🟠 CAUTION    : {len(ca)}")
    print(f"  🔴 AVOID      : {len(av)}")
    print(f"  😱 Fear/Greed : {fg_value} ({fg_class})")
    print(f"  ₿  BTC Dom    : {btc_dom}%")
    print(f"  💾 Saved → data/prices.json")
    print("="*55)


if __name__ == "__main__":
    main()

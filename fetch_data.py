"""
fetch_data.py
=============
Runs daily at 9 AM IST via GitHub Actions.
Uses Alpha, Beta, Gamma model to calculate signals.

ALPHA = Coin return - BTC return (outperformance)
BETA  = Coin 30d move / BTC 30d move (market sensitivity)
GAMMA = (7d return - 30d_weekly_avg) / 30d_weekly_avg (momentum acceleration)
"""

import requests, json, time, os
from datetime import datetime, timezone, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

COINS = [
    # binance_sym, coingecko_id, name, symbol, category
    ("BTCUSDT",   "bitcoin",            "Bitcoin",       "BTC",   "Bitcoin"),
    ("ETHUSDT",   "ethereum",           "Ethereum",      "ETH",   "Ethereum"),
    ("BNBUSDT",   "binancecoin",        "BNB",           "BNB",   "Major"),
    ("SOLUSDT",   "solana",             "Solana",        "SOL",   "Major"),
    ("XRPUSDT",   "ripple",             "XRP",           "XRP",   "Major"),
    ("ADAUSDT",   "cardano",            "Cardano",       "ADA",   "Major"),
    ("DOGEUSDT",  "dogecoin",           "Dogecoin",      "DOGE",  "Meme"),
    ("TRXUSDT",   "tron",               "TRON",          "TRX",   "Major"),
    ("AVAXUSDT",  "avalanche-2",        "Avalanche",     "AVAX",  "Major"),
    ("LINKUSDT",  "chainlink",          "Chainlink",     "LINK",  "Major"),
    ("DOTUSDT",   "polkadot",           "Polkadot",      "DOT",   "Major"),
    ("LTCUSDT",   "litecoin",           "Litecoin",      "LTC",   "Major"),
    ("BCHUSDT",   "bitcoin-cash",       "Bitcoin Cash",  "BCH",   "Major"),
    ("XLMUSDT",   "stellar",            "Stellar",       "XLM",   "Major"),
    ("VETUSDT",   "vechain",            "VeChain",       "VET",   "Major"),
    ("ATOMUSDT",  "cosmos",             "Cosmos",        "ATOM",  "Major"),
    ("HBARUSDT",  "hedera-hashgraph",   "Hedera",        "HBAR",  "Major"),
    ("ALGOUSDT",  "algorand",           "Algorand",      "ALGO",  "Major"),
    ("TONUSDT",   "the-open-network",   "Toncoin",       "TON",   "Major"),
    ("ICPUSDT",   "internet-computer",  "Internet Computer","ICP","Major"),
    ("NEARUSDT",  "near",               "NEAR Protocol", "NEAR",  "L1/L2"),
    ("APTUSDT",   "aptos",              "Aptos",         "APT",   "L1/L2"),
    ("SUIUSDT",   "sui",                "Sui",           "SUI",   "L1/L2"),
    ("SEIUSDT",   "sei-network",        "Sei",           "SEI",   "L1/L2"),
    ("INJUSDT",   "injective-protocol", "Injective",     "INJ",   "L1/L2"),
    ("MATICUSDT", "matic-network",      "Polygon",       "MATIC", "L1/L2"),
    ("OPUSDT",    "optimism",           "Optimism",      "OP",    "L1/L2"),
    ("ARBUSDT",   "arbitrum",           "Arbitrum",      "ARB",   "L1/L2"),
    ("KASUSDT",   "kaspa",              "Kaspa",         "KAS",   "L1/L2"),
    ("ONEUSDT",   "harmony",            "Harmony",       "ONE",   "L1/L2"),
    ("ZILUSDT",   "zilliqa",            "Zilliqa",       "ZIL",   "L1/L2"),
    ("CELRUSDT",  "celer-network",      "Celer Network", "CELR",  "L1/L2"),
    ("SKLUSDT",   "skale",              "SKALE",         "SKL",   "L1/L2"),
    ("IOTXUSDT",  "iotex",              "IoTeX",         "IOTX",  "L1/L2"),
    ("SHIBUSDT",  "shiba-inu",          "Shiba Inu",     "SHIB",  "Meme"),
    ("PEPEUSDT",  "pepe",               "Pepe",          "PEPE",  "Meme"),
    ("FLOKIUSDT", "floki",              "Floki",         "FLOKI", "Meme"),
    ("BONKUSDT",  "bonk",               "Bonk",          "BONK",  "Meme"),
    ("WIFUSDT",   "dogwifcoin",         "dogwifhat",     "WIF",   "Meme"),
    ("UNIUSDT",   "uniswap",            "Uniswap",       "UNI",   "DeFi"),
    ("AAVEUSDT",  "aave",               "Aave",          "AAVE",  "DeFi"),
    ("CRVUSDT",   "curve-dao-token",    "Curve DAO",     "CRV",   "DeFi"),
    ("MKRUSDT",   "maker",              "Maker",         "MKR",   "DeFi"),
    ("DYDXUSDT",  "dydx",               "dYdX",          "DYDX",  "DeFi"),
    ("SUSHIUSDT", "sushi",              "SushiSwap",     "SUSHI", "DeFi"),
    ("1INCHUSDT", "1inch",              "1inch",         "1INCH", "DeFi"),
    ("CAKEUSDT",  "pancakeswap-token",  "PancakeSwap",   "CAKE",  "DeFi"),
    ("RUNEUSDT",  "thorchain",          "THORChain",     "RUNE",  "DeFi"),
    ("GALAUSDT",  "gala",               "Gala",          "GALA",  "Gaming"),
    ("SANDUSDT",  "the-sandbox",        "The Sandbox",   "SAND",  "Gaming"),
    ("MANAUSDT",  "decentraland",       "Decentraland",  "MANA",  "Gaming"),
    ("AXSUSDT",   "axie-infinity",      "Axie Infinity", "AXS",   "Gaming"),
    ("IMXUSDT",   "immutable-x",        "Immutable X",   "IMX",   "Gaming"),
    ("ENJUSDT",   "enjincoin",          "Enjin Coin",    "ENJ",   "Gaming"),
    ("FETUSDT",   "fetch-ai",           "Fetch.ai",      "FET",   "AI/Data"),
    ("AGIXUSDT",  "singularitynet",     "SingularityNET","AGIX",  "AI/Data"),
    ("GRTUSDT",   "the-graph",          "The Graph",     "GRT",   "AI/Data"),
    ("JASMYUSDT", "jasmycoin",          "Jasmy",         "JASMY", "AI/Data"),
    ("WLDUSDT",   "worldcoin-wld",      "Worldcoin",     "WLD",   "AI/Data"),
    ("RNDRUSDT",  "render-token",       "Render",        "RNDR",  "AI/Data"),
    ("CHZUSDT",   "chiliz",             "Chiliz",        "CHZ",   "Sports"),
    ("GMTUSDT",   "stepn",              "STEPN",         "GMT",   "Sports"),
    ("AUDIOUSDT", "audius",             "Audius",        "AUDIO", "Sports"),
    ("ANKRUSDT",  "ankr",               "Ankr",          "ANKR",  "Web3"),
    ("HOTUSDT",   "holo",               "Holo",          "HOT",   "Web3"),
    ("OCEANUSDT", "ocean-protocol",     "Ocean Protocol","OCEAN", "Web3"),
    ("STORJUSDT", "storj",              "Storj",         "STORJ", "Web3"),
    ("FILUSDT",   "filecoin",           "Filecoin",      "FIL",   "Web3"),
    ("CROKUSDT",  "crypto-com-chain",   "Cronos",        "CRO",   "Exchange"),
    ("OKBUSDT",   "okb",                "OKB",           "OKB",   "Exchange"),
    ("COTIUSDT",  "coti",               "COTI",          "COTI",  "Misc"),
    ("DENTUSDT",  "dent",               "Dent",          "DENT",  "Misc"),
    ("HOTUSDT",   "holo",               "Holo",          "HOT",   "Web3"),
    ("STMXUSDT",  "storm",              "Storm",         "STMX",  "Misc"),
]

# Remove duplicates
seen = set()
UNIQUE_COINS = []
for c in COINS:
    if c[3] not in seen:
        seen.add(c[3])
        UNIQUE_COINS.append(c)


def fetch_binance():
    """Fetch all live prices + 24h change from Binance in one call."""
    print("Fetching live prices from Binance...")
    for attempt in range(3):
        try:
            r = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                headers=HEADERS, timeout=30
            )
            if r.status_code == 200:
                result = {}
                for item in r.json():
                    p = float(item.get("lastPrice", 0) or 0)
                    if p > 0:
                        result[item["symbol"]] = {
                            "price":     p,
                            "change24h": round(float(item.get("priceChangePercent", 0) or 0), 4),
                            "high24h":   float(item.get("highPrice", 0) or 0),
                            "low24h":    float(item.get("lowPrice", 0) or 0),
                            "volumeM":   round(float(item.get("quoteVolume", 0) or 0) / 1e6, 1),
                        }
                print(f"  Binance OK: {len(result)} symbols")
                return result
            time.sleep(5)
        except Exception as e:
            print(f"  Binance attempt {attempt+1}: {e}")
            time.sleep(5)
    return {}


def fetch_coingecko(cg_ids):
    """Fetch 7d, 30d changes + market data from CoinGecko."""
    print("Fetching 7d/30d trends from CoinGecko...")
    result = {}
    for attempt in range(3):
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                headers=HEADERS,
                params={
                    "vs_currency": "usd",
                    "ids": ",".join(cg_ids),
                    "per_page": 250,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "7d,30d,1y",
                },
                timeout=30,
            )
            if r.status_code == 200:
                for coin in r.json():
                    ath = float(coin.get("ath") or 0)
                    price = float(coin.get("current_price") or 0)
                    result[coin["id"]] = {
                        "change7d":   round(float(coin.get("price_change_percentage_7d_in_currency") or 0), 4),
                        "change30d":  round(float(coin.get("price_change_percentage_30d_in_currency") or 0), 4),
                        "change1y":   round(float(coin.get("price_change_percentage_1y_in_currency") or 0), 4),
                        "marketCapM": round(float(coin.get("market_cap") or 0) / 1e6, 1),
                        "ath":        ath,
                        "athDrop":    round((price - ath) / ath * 100, 1) if ath > 0 else 0,
                        "athDate":    (coin.get("ath_date") or "")[:10],
                    }
                print(f"  CoinGecko OK: {len(result)} coins")
                return result
            elif r.status_code == 429:
                print("  Rate limited, waiting 70s...")
                time.sleep(70)
            else:
                time.sleep(15)
        except Exception as e:
            print(f"  CoinGecko attempt {attempt+1}: {e}")
            time.sleep(15)
    return result


# ── ALPHA BETA GAMMA ENGINE ───────────────────────────────────────────────────

def compute_alpha(coin_30d, btc_30d):
    """
    Alpha = Coin's 30d return - BTC's 30d return
    Positive Alpha = coin outperforming Bitcoin (strong)
    Negative Alpha = coin underperforming Bitcoin (weak)
    """
    return round(coin_30d - btc_30d, 4)


def compute_beta(coin_30d, btc_30d):
    """
    Beta = Coin 30d move / BTC 30d move
    Beta > 1 = more volatile than BTC (higher risk/reward)
    Beta < 1 = less volatile than BTC (safer)
    Optimal for 8% target: Beta 1.2 to 3.0
    """
    if abs(btc_30d) < 0.5:
        return 1.0  # avoid division by near-zero
    return round(coin_30d / btc_30d, 4)


def compute_gamma(coin_7d, coin_30d):
    """
    Gamma = Momentum acceleration
    Compare 7d performance vs average weekly pace of 30d period
    If 7d > 30d/4 then momentum is accelerating (positive Gamma)
    If 7d < 30d/4 then momentum is slowing (negative Gamma)
    """
    weekly_avg = coin_30d / 4.0  # expected weekly return
    if abs(weekly_avg) < 0.01:
        return 0.0
    return round((coin_7d - weekly_avg) / abs(weekly_avg) * 100, 4)


def beta_score(beta):
    """
    Convert Beta to 0-100 score.
    Sweet spot for 8% target is Beta 1.2 to 2.5
    Too low = won't move enough. Too high = too risky.
    """
    if beta <= 0:      return 0
    if beta < 0.5:     return 20
    if beta < 1.0:     return 40
    if beta < 1.2:     return 55
    if beta < 2.0:     return 85   # ideal zone
    if beta < 3.0:     return 100  # peak zone
    if beta < 4.0:     return 80   # getting risky
    if beta < 6.0:     return 60
    return 40  # too volatile


def alpha_score(alpha):
    """Convert Alpha to 0-100 score."""
    if alpha >= 30:    return 100
    if alpha >= 20:    return 90
    if alpha >= 10:    return 80
    if alpha >= 5:     return 70
    if alpha >= 0:     return 55
    if alpha >= -5:    return 40
    if alpha >= -10:   return 25
    return 10


def gamma_score(gamma):
    """Convert Gamma (momentum acceleration) to 0-100 score."""
    if gamma >= 100:   return 100
    if gamma >= 50:    return 90
    if gamma >= 20:    return 80
    if gamma >= 0:     return 60
    if gamma >= -20:   return 45
    if gamma >= -50:   return 30
    return 10


def final_score(a_score, b_score, g_score):
    """
    Final Score = Alpha(40%) + Beta(25%) + Gamma(35%)
    """
    return min(100, max(0, round(
        a_score * 0.40 +
        b_score * 0.25 +
        g_score * 0.35
    )))


def get_signal(score, alpha, gamma, d24):
    """
    BUY requires:
    - Final score >= 65
    - Positive Alpha (outperforming BTC)
    - Positive 24h (still going up today)

    STRONG BUY also requires positive Gamma (accelerating)
    """
    if score >= 65 and alpha > 0 and d24 > 0:
        if gamma > 20:
            return "STRONG BUY"
        return "BUY"
    if score >= 40:
        return "WATCH"
    return "AVOID"


def fetch_history(cg_id):
    """Fetch 5 years of OHLC history."""
    for attempt in range(2):
        try:
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc",
                headers=HEADERS,
                params={"vs_currency": "usd", "days": 1825},
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time.sleep(70)
            else:
                time.sleep(10)
        except:
            time.sleep(10)
    return []


def analyse_history(ohlc):
    """Extract yearly returns and monthly seasonality from OHLC data."""
    if not ohlc or len(ohlc) < 30:
        return {}

    MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    daily = {}
    for c in ohlc:
        dt = datetime.fromtimestamp(c[0]/1000, tz=timezone.utc).strftime("%Y-%m-%d")
        daily[dt] = float(c[4])

    # Yearly returns
    yearly = {}
    for yr in range(2019, 2027):
        yp = {d:p for d,p in daily.items() if d.startswith(str(yr))}
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

    monthly = {i: [] for i in range(1,13)}
    for ym, ps in month_groups.items():
        if len(ps) < 5:
            continue
        m = int(ym[5:7])
        if ps[0] > 0:
            monthly[m].append(round((ps[-1]-ps[0])/ps[0]*100, 2))

    avg_monthly = {}
    for m, rets in monthly.items():
        if rets:
            avg_monthly[MONTHS[m-1]] = round(sum(rets)/len(rets), 1)

    best_m  = max(avg_monthly, key=avg_monthly.get) if avg_monthly else "N/A"
    worst_m = min(avg_monthly, key=avg_monthly.get) if avg_monthly else "N/A"
    win_rate = round(sum(1 for v in avg_monthly.values() if v>0)/len(avg_monthly)*100) if avg_monthly else 0
    avg_yr   = round(sum(yearly.values())/len(yearly), 1) if yearly else 0

    # Support & resistance
    prices = list(daily.values())
    dates  = sorted(daily.keys())
    recent = sorted([daily[d] for d in dates[-90:]])
    support    = round(recent[int(len(recent)*0.10)], 10) if len(recent)>=10 else 0
    resistance = round(recent[int(len(recent)*0.90)], 10) if len(recent)>=10 else 0

    return {
        "yearlyReturns":    yearly,
        "avgYearlyReturn":  avg_yr,
        "monthlyAvgReturn": avg_monthly,
        "bestMonth":        best_m,
        "worstMonth":       worst_m,
        "winRate":          win_rate,
        "yearsOfData":      len(yearly),
        "dataConfidence":   "Very High" if len(yearly)>=5 else "High" if len(yearly)>=3 else "Medium" if len(yearly)>=2 else "Low",
        "support":          support,
        "resistance":       resistance,
        "totalDataPoints":  len(daily),
    }


def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    print("="*55)
    print("  CRYPTO ANALYSER — Alpha Beta Gamma Engine")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("="*55)

    # Fetch live prices
    binance = fetch_binance()

    # Fetch trends
    cg_ids = list({c[1] for c in UNIQUE_COINS})
    trends  = fetch_coingecko(cg_ids)

    # Get BTC values for Alpha/Beta calculation
    btc_b = binance.get("BTCUSDT", {})
    btc_t = trends.get("bitcoin", {})
    btc_24h = btc_b.get("change24h", 0)
    btc_7d  = btc_t.get("change7d", 0)
    btc_30d = btc_t.get("change30d", 0)

    print(f"\nBTC reference: 24h={btc_24h}% 7d={btc_7d}% 30d={btc_30d}%")
    print(f"Processing {len(UNIQUE_COINS)} coins with Alpha/Beta/Gamma...\n")

    coins_out = []

    for b_sym, cg_id, name, symbol, category in UNIQUE_COINS:
        b  = binance.get(b_sym, {})
        cg = trends.get(cg_id, {})

        price = b.get("price", 0)
        if price <= 0:
            continue

        d24  = b.get("change24h", 0)
        d7   = cg.get("change7d", 0)
        d30  = cg.get("change30d", 0)
        d1y  = cg.get("change1y", 0)
        mcap = cg.get("marketCapM", 0)
        vol  = b.get("volumeM", 0)

        # ── Alpha Beta Gamma ──────────────────────────────────────────────
        alpha = compute_alpha(d30, btc_30d)
        beta  = compute_beta(d30, btc_30d)
        gamma = compute_gamma(d7, d30)

        a_sc  = alpha_score(alpha)
        b_sc  = beta_score(beta)
        g_sc  = gamma_score(gamma)
        score = final_score(a_sc, b_sc, g_sc)
        signal = get_signal(score, alpha, gamma, d24)

        # Fetch 5-year history
        print(f"  [{len(coins_out)+1}/{len(UNIQUE_COINS)}] {symbol} | α={alpha:.1f} β={beta:.2f} γ={gamma:.1f} → {signal}")
        ohlc = fetch_history(cg_id)
        hist = analyse_history(ohlc)
        time.sleep(2)

        curr_month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][now_ist.month-1]
        month_avg  = hist.get("monthlyAvgReturn", {}).get(curr_month, 0)

        coins_out.append({
            "name":     name,
            "symbol":   symbol,
            "category": category,
            "price":    price,
            "change24h": d24,
            "change7d":  d7,
            "change30d": d30,
            "change1y":  d1y,
            "marketCapM": mcap,
            "volumeM":   vol,
            "high24h":   round(b.get("high24h", 0), 8),
            "low24h":    round(b.get("low24h", 0), 8),
            "target8pct": round(price * 1.08, 8),
            # Alpha Beta Gamma
            "alpha":  alpha,
            "beta":   beta,
            "gamma":  gamma,
            "alphaScore": a_sc,
            "betaScore":  b_sc,
            "gammaScore": g_sc,
            "score":  score,
            "signal": signal,
            # ATH
            "ath":     cg.get("ath", 0),
            "athDrop": cg.get("athDrop", 0),
            "athDate": cg.get("athDate", ""),
            # History
            "goodMonthToBuy":  month_avg > 0,
            "currentMonthAvg": round(month_avg, 1),
            "history": hist,
        })

    # Sort: STRONG BUY → BUY → WATCH → AVOID, then by score
    order = {"STRONG BUY":0, "BUY":1, "WATCH":2, "AVOID":3}
    coins_out.sort(key=lambda x: (order.get(x["signal"], 3), -x["score"]))

    strong_buys = [c for c in coins_out if c["signal"]=="STRONG BUY"]
    buys        = [c for c in coins_out if c["signal"]=="BUY"]
    watches     = [c for c in coins_out if c["signal"]=="WATCH"]
    avoids      = [c for c in coins_out if c["signal"]=="AVOID"]

    output = {
        "updatedAt":    now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAtIST": now_ist.strftime("%d %b %Y %I:%M %p IST"),
        "currentMonth": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][now_ist.month-1],
        "totalCoins":   len(coins_out),
        "strongBuyCount": len(strong_buys),
        "buyCount":     len(buys),
        "watchCount":   len(watches),
        "avoidCount":   len(avoids),
        "btcRef":       {"change24h": btc_24h, "change7d": btc_7d, "change30d": btc_30d},
        "engine":       "Alpha-Beta-Gamma v1.0",
        "coins":        coins_out,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n"+"="*55)
    print(f"  DONE: {len(coins_out)} coins analysed")
    print(f"  ⭐ STRONG BUY: {len(strong_buys)}")
    print(f"  🟢 BUY:        {len(buys)}")
    print(f"  🟡 WATCH:      {len(watches)}")
    print(f"  🔴 AVOID:      {len(avoids)}")
    print(f"  Saved → data/prices.json")
    print("="*55)


if __name__ == "__main__":
    main()

"""
fetch_data.py - Penny Crypto Analyser
Fetches live prices + 5 years history. Runs daily at 9AM IST via GitHub Actions.
"""
import requests, json, time, os
from datetime import datetime, timezone, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# Only coins that are reliably under $1 on Binance
COINS = [
    # symbol,          coingecko_id,              name,             sym,     category
    ("DOGEUSDT",  "dogecoin",            "Dogecoin",       "DOGE",  "Meme"),
    ("ADAUSDT",   "cardano",             "Cardano",        "ADA",   "Major"),
    ("TRXUSDT",   "tron",                "TRON",           "TRX",   "Major"),
    ("XLMUSDT",   "stellar",             "Stellar",        "XLM",   "Major"),
    ("HBARUSDT",  "hedera-hashgraph",    "Hedera",         "HBAR",  "Major"),
    ("VETUSDT",   "vechain",             "VeChain",        "VET",   "Major"),
    ("ALGOUSDT",  "algorand",            "Algorand",       "ALGO",  "Major"),
    ("SHIBUSDT",  "shiba-inu",           "Shiba Inu",      "SHIB",  "Meme"),
    ("PEPEUSDT",  "pepe",                "Pepe",           "PEPE",  "Meme"),
    ("FLOKIUSDT", "floki",               "Floki",          "FLOKI", "Meme"),
    ("BONKUSDT",  "bonk",                "Bonk",           "BONK",  "Meme"),
    ("GALAUSDT",  "gala",                "Gala",           "GALA",  "Gaming"),
    ("SANDUSDT",  "the-sandbox",         "The Sandbox",    "SAND",  "Gaming"),
    ("MANAUSDT",  "decentraland",        "Decentraland",   "MANA",  "Gaming"),
    ("AXSUSDT",   "axie-infinity",       "Axie Infinity",  "AXS",   "Gaming"),
    ("ENJUSDT",   "enjincoin",           "Enjin Coin",     "ENJ",   "Gaming"),
    ("SLPUSDT",   "smooth-love-potion",  "Axie SLP",       "SLP",   "Gaming"),
    ("GMTUSDT",   "stepn",               "STEPN",          "GMT",   "Sports"),
    ("CHZUSDT",   "chiliz",              "Chiliz",         "CHZ",   "Sports"),
    ("AUDIOUSDT", "audius",              "Audius",         "AUDIO", "Sports"),
    ("ANKRUSDT",  "ankr",                "Ankr",           "ANKR",  "Web3"),
    ("HOTUSDT",   "holo",                "Holo",           "HOT",   "Web3"),
    ("OCEANUSDT", "ocean-protocol",      "Ocean Protocol", "OCEAN", "Web3"),
    ("STORJUSDT", "storj",               "Storj",          "STORJ", "Web3"),
    ("GRTUSDT",   "the-graph",           "The Graph",      "GRT",   "AI/Data"),
    ("JASMYUSDT", "jasmycoin",           "Jasmy",          "JASMY", "AI/Data"),
    ("DATAUSDT",  "streamr",             "Streamr",        "DATA",  "AI/Data"),
    ("MDTUSDT",   "measurable-data-token","Measurable Data","MDT",  "AI/Data"),
    ("1INCHUSDT", "1inch",               "1inch",          "1INCH", "DeFi"),
    ("SUSHIUSDT", "sushi",               "SushiSwap",      "SUSHI", "DeFi"),
    ("BNTUSDT",   "bancor",              "Bancor",         "BNT",   "DeFi"),
    ("IOTXUSDT",  "iotex",               "IoTeX",          "IOTX",  "L1/L2"),
    ("ONEUSDT",   "harmony",             "Harmony",        "ONE",   "L1/L2"),
    ("ZILUSDT",   "zilliqa",             "Zilliqa",        "ZIL",   "L1/L2"),
    ("SKLUSDT",   "skale",               "SKALE",          "SKL",   "L1/L2"),
    ("CELRUSDT",  "celer-network",       "Celer Network",  "CELR",  "L1/L2"),
    ("ONTUSDT",   "ontology",            "Ontology",       "ONT",   "L1/L2"),
    ("COTIUSDT",  "coti",                "COTI",           "COTI",  "Misc"),
    ("STMXUSDT",  "storm",               "Storm",          "STMX",  "Misc"),
    ("DENTUSDT",  "dent",                "Dent",           "DENT",  "Misc"),
    ("FUNUSDT",   "funtoken",            "FUNToken",       "FUN",   "Misc"),
    ("CVCUSDT",   "civic",               "Civic",          "CVC",   "Misc"),
    ("POWRUSDT",  "power-ledger",        "Power Ledger",   "POWR",  "Misc"),
    ("AMPUSDT",   "amp-token",           "Amp",            "AMP",   "Misc"),
    ("NKNUSDT",   "nkn",                 "NKN",            "NKN",   "Misc"),
]


def fetch_binance():
    """Get ALL live prices from Binance in one call."""
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
                    sym = item.get("symbol", "")
                    price = float(item.get("lastPrice", 0) or 0)
                    if price > 0:
                        result[sym] = {
                            "price":     price,
                            "change24h": round(float(item.get("priceChangePercent", 0) or 0), 2),
                            "volumeM":   round(float(item.get("quoteVolume", 0) or 0) / 1e6, 1),
                            "high24h":   float(item.get("highPrice", 0) or 0),
                            "low24h":    float(item.get("lowPrice", 0) or 0),
                        }
                print(f"  Binance OK: {len(result)} symbols fetched")
                return result
            time.sleep(5)
        except Exception as e:
            print(f"  Binance attempt {attempt+1} failed: {e}")
            time.sleep(5)
    return {}


def fetch_coingecko_trends(cg_ids):
    """Get 7d, 30d, 1y changes + ATH data from CoinGecko."""
    print("Fetching trends from CoinGecko...")
    ids_str = ",".join(cg_ids)
    for attempt in range(3):
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                headers=HEADERS,
                params={
                    "vs_currency": "usd",
                    "ids": ids_str,
                    "per_page": 250,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "7d,30d,1y",
                },
                timeout=30,
            )
            if r.status_code == 200:
                result = {}
                for coin in r.json():
                    ath   = float(coin.get("ath") or 0)
                    price = float(coin.get("current_price") or 0)
                    ath_drop = round((price - ath) / ath * 100, 1) if ath > 0 else 0
                    result[coin["id"]] = {
                        "change7d":   round(float(coin.get("price_change_percentage_7d_in_currency") or 0), 2),
                        "change30d":  round(float(coin.get("price_change_percentage_30d_in_currency") or 0), 2),
                        "change1y":   round(float(coin.get("price_change_percentage_1y_in_currency") or 0), 2),
                        "marketCapM": round(float(coin.get("market_cap") or 0) / 1e6, 1),
                        "ath":        ath,
                        "athDrop":    ath_drop,
                        "athDate":    (coin.get("ath_date") or "")[:10],
                    }
                print(f"  CoinGecko OK: {len(result)} coins")
                return result
            elif r.status_code == 429:
                print(f"  Rate limited, waiting 70s...")
                time.sleep(70)
            else:
                print(f"  CoinGecko HTTP {r.status_code}, retrying...")
                time.sleep(15)
        except Exception as e:
            print(f"  CoinGecko attempt {attempt+1} error: {e}")
            time.sleep(15)
    print("  CoinGecko failed - continuing without trend data")
    return {}


def fetch_history(cg_id):
    """Fetch 5 years of daily OHLC data from CoinGecko."""
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
        except Exception:
            time.sleep(10)
    return []


def analyse(ohlc):
    """Analyse 5 years of OHLC data and return historical insights."""
    if not ohlc or len(ohlc) < 30:
        return {}

    daily = {}
    for candle in ohlc:
        dt  = datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc)
        key = dt.strftime("%Y-%m-%d")
        daily[key] = float(candle[4])

    if not daily:
        return {}

    dates  = sorted(daily.keys())
    prices = [daily[d] for d in dates]

    # Yearly returns
    yearly = {}
    for year in range(2019, 2027):
        yp = {d: p for d, p in daily.items() if d.startswith(str(year))}
        if len(yp) < 10:
            continue
        sd = sorted(yp.keys())
        p0, p1 = yp[sd[0]], yp[sd[-1]]
        if p0 > 0:
            yearly[str(year)] = round((p1 - p0) / p0 * 100, 1)

    # Monthly seasonality
    month_data = {}
    for d, p in daily.items():
        ym = d[:7]
        month_data.setdefault(ym, []).append(p)

    monthly_returns = {i: [] for i in range(1, 13)}
    for ym, ps in month_data.items():
        if len(ps) < 5:
            continue
        m = int(ym[5:7])
        if ps[0] > 0:
            monthly_returns[m].append(round((ps[-1] - ps[0]) / ps[0] * 100, 2))

    avg_monthly = {}
    for m, rets in monthly_returns.items():
        if rets:
            avg_monthly[MONTH_NAMES[m - 1]] = round(sum(rets) / len(rets), 1)

    best_month  = max(avg_monthly, key=avg_monthly.get) if avg_monthly else "N/A"
    worst_month = min(avg_monthly, key=avg_monthly.get) if avg_monthly else "N/A"

    # Support & resistance from last 90 days
    recent = sorted([p for d, p in daily.items() if d >= dates[-90]])
    support    = round(recent[int(len(recent) * 0.10)], 10) if len(recent) >= 10 else 0
    resistance = round(recent[int(len(recent) * 0.90)], 10) if len(recent) >= 10 else 0

    # 1 year trend
    p_now = prices[-1] if prices else 0
    p_1y  = None
    target = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    for d in dates:
        if d >= target:
            p_1y = daily[d]
            break
    trend_1y = round((p_now - p_1y) / p_1y * 100, 1) if p_1y and p_1y > 0 else 0
    if trend_1y > 50:    trend_label = "Strong Uptrend"
    elif trend_1y > 10:  trend_label = "Mild Uptrend"
    elif trend_1y > -10: trend_label = "Sideways"
    elif trend_1y > -50: trend_label = "Mild Downtrend"
    else:                trend_label = "Strong Downtrend"

    # Volatility
    pct_changes = []
    for i in range(1, min(len(prices), 365)):
        if prices[i - 1] > 0:
            pct_changes.append((prices[i] - prices[i - 1]) / prices[i - 1] * 100)
    if pct_changes:
        mean = sum(pct_changes) / len(pct_changes)
        vol  = round((sum((x - mean) ** 2 for x in pct_changes) / len(pct_changes)) ** 0.5, 2)
        vol_label = "Very High" if vol > 8 else "High" if vol > 5 else "Medium" if vol > 3 else "Low"
    else:
        vol, vol_label = 0, "Unknown"

    # Win rate
    pos_months  = sum(1 for v in avg_monthly.values() if v > 0)
    win_rate    = round(pos_months / len(avg_monthly) * 100) if avg_monthly else 0
    years_count = len(yearly)

    # Confidence
    if years_count >= 4:   confidence = "Very High"
    elif years_count >= 3: confidence = "High"
    elif years_count >= 2: confidence = "Medium"
    else:                  confidence = "Low"

    # Historical signal
    avg_yr = round(sum(yearly.values()) / len(yearly), 1) if yearly else 0
    if avg_yr > 100 and win_rate >= 60: hist_sig = "STRONG BUY"
    elif avg_yr > 20 and win_rate >= 50: hist_sig = "BUY"
    elif avg_yr > 0:                     hist_sig = "HOLD"
    else:                                hist_sig = "CAUTION"

    return {
        "yearlyReturns":    yearly,
        "avgYearlyReturn":  avg_yr,
        "monthlyAvgReturn": avg_monthly,
        "bestMonth":        best_month,
        "worstMonth":       worst_month,
        "currentMonth":     MONTH_NAMES[datetime.now().month - 1],
        "isGoodMonth":      avg_monthly.get(MONTH_NAMES[datetime.now().month - 1], 0) > 0,
        "support":          support,
        "resistance":       resistance,
        "trend1y":          trend_1y,
        "trendLabel":       trend_label,
        "volatility":       vol,
        "volatilityLabel":  vol_label,
        "winRate":          win_rate,
        "yearsOfData":      years_count,
        "dataConfidence":   confidence,
        "historicalSignal": hist_sig,
        "totalDataPoints":  len(daily),
    }


def calc_score(d24, d7, d30):
    raw = d24 * 0.25 + d7 * 0.35 + d30 * 0.40
    return min(100, max(0, round(50 + raw * 1.8)))


def get_signal(score, d24):
    if score >= 65 and d24 > 0: return "BUY"
    if score >= 40:              return "WATCH"
    return "AVOID"


def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    print("=" * 55)
    print("  PENNY CRYPTO DEEP ANALYSER")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("=" * 55)

    # Step 1: Live prices from Binance
    binance = fetch_binance()

    # Step 2: Trends from CoinGecko
    cg_ids = list({c[1] for c in COINS})
    trends = fetch_coingecko_trends(cg_ids)

    # Step 3: Process each coin
    print(f"Processing {len(COINS)} coins...")
    coins_out = []

    for b_sym, cg_id, name, symbol, category in COINS:
        b  = binance.get(b_sym, {})
        cg = trends.get(cg_id, {})

        price = b.get("price", 0)

        # FIXED: No price filter - include coin even if price is above $1
        # The coin list is curated so they are penny coins by nature
        if price <= 0:
            print(f"  SKIP {symbol} - not found on Binance")
            continue

        d24  = b.get("change24h", 0)
        d7   = cg.get("change7d", 0)
        d30  = cg.get("change30d", 0)
        d1y  = cg.get("change1y", 0)
        mcap = cg.get("marketCapM", 0)
        vol  = b.get("volumeM", 0)

        score  = calc_score(d24, d7, d30)
        signal = get_signal(score, d24)

        # Fetch 5 years of history
        print(f"  [{len(coins_out)+1}/{len(COINS)}] {symbol} ${price:.6f} - fetching history...")
        ohlc = fetch_history(cg_id)
        hist = analyse(ohlc)
        time.sleep(2)

        # Boost score based on historical signal
        boost = {"STRONG BUY": 10, "BUY": 5, "HOLD": 0, "CAUTION": -10}.get(
            hist.get("historicalSignal", ""), 0)
        combined = min(100, max(0, score + boost))

        curr_month    = MONTH_NAMES[now_ist.month - 1]
        month_avg     = hist.get("monthlyAvgReturn", {}).get(curr_month, 0)
        good_month    = month_avg > 0

        coins_out.append({
            "name":          name,
            "symbol":        symbol,
            "category":      category,
            "price":         price,
            "change24h":     d24,
            "change7d":      d7,
            "change30d":     d30,
            "change1y":      d1y,
            "marketCapM":    mcap,
            "volumeM":       vol,
            "high24h":       round(b.get("high24h", 0), 10),
            "low24h":        round(b.get("low24h", 0), 10),
            "target8pct":    round(price * 1.08, 10),
            "score":         score,
            "combinedScore": combined,
            "signal":        signal,
            "ath":           cg.get("ath", 0),
            "athDrop":       cg.get("athDrop", 0),
            "athDate":       cg.get("athDate", ""),
            "goodMonthToBuy":   good_month,
            "currentMonthAvg":  round(month_avg, 1),
            "history":       hist,
        })

    # Sort: BUY first, then by score descending
    order = {"BUY": 0, "WATCH": 1, "AVOID": 2}
    coins_out.sort(key=lambda x: (order[x["signal"]], -x["combinedScore"]))

    buys    = sum(1 for c in coins_out if c["signal"] == "BUY")
    watches = sum(1 for c in coins_out if c["signal"] == "WATCH")
    avoids  = sum(1 for c in coins_out if c["signal"] == "AVOID")

    long_picks = [
        c["symbol"] for c in coins_out
        if c["history"].get("avgYearlyReturn", 0) > 30
        and c["history"].get("yearsOfData", 0) >= 2
        and c["signal"] in ("BUY", "WATCH")
    ][:5]

    output = {
        "updatedAt":     now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAtIST":  now_ist.strftime("%d %b %Y %I:%M %p IST"),
        "currentMonth":  MONTH_NAMES[now_ist.month - 1],
        "totalCoins":    len(coins_out),
        "buyCount":      buys,
        "watchCount":    watches,
        "avoidCount":    avoids,
        "priceSource":   "Binance (live) + CoinGecko (5yr history)",
        "longtermPicks": long_picks,
        "coins":         coins_out,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w") as f:
        json.dump(output, f, indent=2)

    print("=" * 55)
    print(f"  DONE: {len(coins_out)} coins saved")
    print(f"  BUY: {buys}  WATCH: {watches}  AVOID: {avoids}")
    print(f"  Long-term picks: {long_picks}")
    print("=" * 55)


if __name__ == "__main__":
    main()

"""
fetch_data.py — Ultimate Crypto Analyser v7
============================================
500 coins · 20 Technical Factors · Scientific/Quantum Methods · News Sentiment
Finishes in under 3 minutes on GitHub Actions.

NEW IN v7:
  News Sentiment Analysis using:
  - CoinTelegraph RSS       (crypto specific)
  - Decrypt RSS             (crypto specific)
  - CryptoNews RSS          (crypto specific)
  - Reuters Business RSS    (macro / market wide)
  VADER NLP scores every headline → Per-coin sentiment score
  Sentiment adjusts final BUY/SELL signal UP or DOWN

Signal adjustment rules:
  BUY + VERY POSITIVE news  → STRONG BUY  (upgrade)
  STRONG BUY + VERY NEGATIVE news → BUY   (downgrade)
  BUY + NEGATIVE news       → WATCH       (downgrade)
  WATCH + VERY POSITIVE     → BUY         (upgrade)
"""

import requests, json, time, os, math, random, re
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timezone, timedelta, date

HEADERS = {"User-Agent": "CryptoAnalyser/7.0", "Accept": "application/json"}
SIA = SentimentIntensityAnalyzer()

EXCLUDE_IDS = {
    "tether","usd-coin","dai","binance-usd","true-usd","first-digital-usd",
    "ethena-usde","usual-usd","frax","wrapped-bitcoin","wrapped-ethereum",
    "staked-ether","rocket-pool-eth","wrapped-steth","coinbase-wrapped-steth",
    "mantle-staked-ether","kelp-dao-restaked-eth","tether-eurt","pax-dollar",
    "paypal-usd","mountain-protocol-usdm","ondo-us-dollar-yield",
}

CATEGORY_MAP = {
    "bitcoin":"Bitcoin","ethereum":"Ethereum",
    "binancecoin":"Exchange","okb":"Exchange","gate-token":"Exchange",
    "kucoin-token":"Exchange","crypto-com-chain":"Exchange",
    "dogecoin":"Meme","shiba-inu":"Meme","pepe":"Meme","floki":"Meme",
    "bonk":"Meme","dogwifcoin":"Meme","book-of-meme":"Meme","popcat":"Meme",
    "mog-coin":"Meme","cat-in-a-dogs-world":"Meme","brett-based":"Meme",
    "dogs-token":"Meme","neiro-on-eth":"Meme","coq-inu":"Meme",
    "uniswap":"DeFi","aave":"DeFi","curve-dao-token":"DeFi","maker":"DeFi",
    "lido-dao":"DeFi","pancakeswap-token":"DeFi","jupiter-exchange-solana":"DeFi",
    "thorchain":"DeFi","dydx":"DeFi","1inch":"DeFi","sushi":"DeFi",
    "compound-governance-token":"DeFi","ethena":"DeFi",
    "fetch-ai":"AI/Data","singularitynet":"AI/Data","the-graph":"AI/Data",
    "bittensor":"AI/Data","worldcoin-wld":"AI/Data","render-token":"AI/Data",
    "ocean-protocol":"AI/Data","akash-network":"AI/Data",
    "gala":"Gaming","the-sandbox":"Gaming","decentraland":"Gaming",
    "axie-infinity":"Gaming","immutable-x":"Gaming","enjincoin":"Gaming",
    "pixels":"Gaming","notcoin":"Gaming","illuvium":"Gaming",
    "solana":"L1/L2","avalanche-2":"L1/L2","near":"L1/L2","aptos":"L1/L2",
    "sui":"L1/L2","optimism":"L1/L2","arbitrum":"L1/L2","matic-network":"L1/L2",
    "injective-protocol":"L1/L2","sei-network":"L1/L2","kaspa":"L1/L2",
    "algorand":"L1/L2","hedera-hashgraph":"L1/L2","internet-computer":"L1/L2",
    "filecoin":"L1/L2","stacks":"L1/L2","mantle":"L1/L2","tezos":"L1/L2",
    "chainlink":"Web3","polkadot":"Web3","cosmos":"Web3",
    "monero":"Privacy","zcash":"Privacy","dash":"Privacy",
    "ripple":"Major","cardano":"Major","tron":"Major","stellar":"Major",
    "litecoin":"Major","bitcoin-cash":"Major","vechain":"Major",
}

def get_category(cg_id):
    return CATEGORY_MAP.get(cg_id, "Major")


# ═══════════════════════════════════════════════════════════════
# NEWS SENTIMENT ENGINE
# ═══════════════════════════════════════════════════════════════

NEWS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://cryptonews.com/news/feed/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://feeds.reuters.com/reuters/businessNews",
]

def fetch_all_news():
    """Fetch headlines from all RSS feeds. Returns list of (title, tags)."""
    all_headlines = []
    for url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:30]:
                title = entry.get("title", "").strip()
                if title and len(title) > 10:
                    # Extract tags if available
                    tags = []
                    for tag in entry.get("tags", []):
                        t = tag.get("term", "").upper()
                        if t:
                            tags.append(t)
                    all_headlines.append((title, tags))
        except Exception as e:
            print(f"  RSS {url[:40]} failed: {e}")
    print(f"  Fetched {len(all_headlines)} news headlines")
    return all_headlines


def score_coin_sentiment(coin_name, symbol, cg_id, all_headlines):
    """
    Score news sentiment for a specific coin.
    Returns: compound score (-1 to +1), label, relevant headlines
    """
    keywords = set()

    # Add symbol variants
    sym = symbol.upper()
    keywords.add(sym)
    keywords.add(f"${sym}")

    # Add name words (skip short/common words)
    for word in coin_name.upper().split():
        if len(word) >= 4 and word not in {"COIN","TOKEN","FINANCE","NETWORK","PROTOCOL"}:
            keywords.add(word)

    # Add CoinGecko ID words
    for word in cg_id.replace("-", " ").upper().split():
        if len(word) >= 4:
            keywords.add(word)

    # Category-level keywords
    cat_keywords = {
        "Bitcoin":  {"BITCOIN","BTC","SATOSHI","HALVING","MINING"},
        "Ethereum": {"ETHEREUM","ETH","VITALIK","GAS","EIP"},
        "Meme":     {"MEME","DOGE","SHIBA","PEPE","FLOKI"},
        "DeFi":     {"DEFI","YIELD","LIQUIDITY","DEX","AMM"},
        "AI/Data":  {"AI","ARTIFICIAL INTELLIGENCE","MACHINE LEARNING","DATA"},
        "L1/L2":    {"LAYER","SCALING","ROLLUP","SIDECHAIN"},
    }
    cat = get_category(cg_id)
    for ck in cat_keywords.get(cat, set()):
        keywords.add(ck)

    relevant_scores = []
    relevant_headlines = []

    for title, tags in all_headlines:
        title_up = title.upper()
        # Match by keyword in title or tags
        matched = any(kw in title_up for kw in keywords)
        if not matched and tags:
            matched = any(kw in " ".join(tags) for kw in keywords)

        if matched:
            score = SIA.polarity_scores(title)["compound"]
            relevant_scores.append(score)
            relevant_headlines.append({"headline": title[:100], "score": round(score, 3)})

    # If no specific news, use general market sentiment (small weight)
    if not relevant_scores:
        market_scores = []
        for title, _ in all_headlines[:20]:
            s = SIA.polarity_scores(title)["compound"]
            market_scores.append(s)
        if market_scores:
            avg = sum(market_scores) / len(market_scores)
            return round(avg * 0.3, 3), sentiment_label(avg * 0.3), [], True
        return 0.0, "NEUTRAL", [], True

    avg = sum(relevant_scores) / len(relevant_scores)
    avg = round(avg, 3)
    return avg, sentiment_label(avg), relevant_headlines[:5], False


def sentiment_label(compound):
    if compound >= 0.35:  return "VERY POSITIVE"
    if compound >= 0.10:  return "POSITIVE"
    if compound >= -0.10: return "NEUTRAL"
    if compound >= -0.35: return "NEGATIVE"
    return "VERY NEGATIVE"


def sentiment_to_score(compound):
    """Convert compound (-1..+1) to 0-100."""
    return round((compound + 1) / 2 * 100, 1)


def sentiment_icon(label):
    return {
        "VERY POSITIVE": "🟢🟢",
        "POSITIVE":       "🟢",
        "NEUTRAL":        "⚪",
        "NEGATIVE":       "🔴",
        "VERY NEGATIVE":  "🔴🔴",
    }.get(label, "⚪")


def adjust_signal(tech_signal, sent_label):
    """Adjust technical signal up/down based on news sentiment."""
    table = {
        ("STRONG BUY", "VERY POSITIVE"):  "STRONG BUY",
        ("STRONG BUY", "POSITIVE"):       "STRONG BUY",
        ("STRONG BUY", "NEUTRAL"):        "STRONG BUY",
        ("STRONG BUY", "NEGATIVE"):       "BUY",
        ("STRONG BUY", "VERY NEGATIVE"):  "WATCH",
        ("BUY",         "VERY POSITIVE"): "STRONG BUY",
        ("BUY",         "POSITIVE"):      "BUY",
        ("BUY",         "NEUTRAL"):       "BUY",
        ("BUY",         "NEGATIVE"):      "WATCH",
        ("BUY",         "VERY NEGATIVE"): "CAUTION",
        ("WATCH",       "VERY POSITIVE"): "BUY",
        ("WATCH",       "POSITIVE"):      "WATCH",
        ("WATCH",       "NEUTRAL"):       "WATCH",
        ("WATCH",       "NEGATIVE"):      "CAUTION",
        ("WATCH",       "VERY NEGATIVE"): "AVOID",
        ("CAUTION",     "VERY POSITIVE"): "WATCH",
        ("CAUTION",     "POSITIVE"):      "CAUTION",
        ("CAUTION",     "NEUTRAL"):       "CAUTION",
        ("CAUTION",     "NEGATIVE"):      "AVOID",
        ("CAUTION",     "VERY NEGATIVE"): "AVOID",
        ("AVOID",       "VERY POSITIVE"): "CAUTION",
        ("AVOID",       "POSITIVE"):      "AVOID",
        ("AVOID",       "NEUTRAL"):       "AVOID",
        ("AVOID",       "NEGATIVE"):      "AVOID",
        ("AVOID",       "VERY NEGATIVE"): "AVOID",
    }
    return table.get((tech_signal, sent_label), tech_signal)


# ═══════════════════════════════════════════════════════════════
# SCIENTIFIC METHODS (same as v6)
# ═══════════════════════════════════════════════════════════════

def gbm_target_prob(price, target, d30):
    mu = max(d30/100/30, -0.05)
    sigma = max(abs(d30/100/30)*1.5, 0.02)
    T = 30
    if sigma<=0 or price<=0 or target<=0: return 0.5
    log_ret = math.log(target/price)
    drift = (mu - 0.5*sigma**2)*T
    vol_t = sigma*math.sqrt(T)
    if vol_t==0: return 1.0 if log_ret<=0 else 0.0
    d = (log_ret - drift)/vol_t
    return round((1 + math.erf(-d/math.sqrt(2)))/2, 4)

def black_scholes_prob(price, target, d30):
    sigma_daily = max(abs(d30/100/30)*1.5, 0.02)
    sigma_annual = sigma_daily * math.sqrt(365)
    T = 30/365; r = 0.05
    if T<=0 or sigma_annual<=0 or price<=0 or target<=0: return 0.3
    try:
        d1 = (math.log(price/target)+(r+0.5*sigma_annual**2)*T)/(sigma_annual*math.sqrt(T))
        d2 = d1 - sigma_annual*math.sqrt(T)
        return round((1+math.erf(d2/math.sqrt(2)))/2, 4)
    except: return 0.3

def monte_carlo_prob(price, target, d24, d30, n=300):
    mu = max(d30/100/30, -0.05)
    sigma = max(abs(d30/100/30)*1.5 + abs(d24/100)*0.5, 0.02)
    hits = 0
    random.seed(int(price*1000) % 99991)
    for _ in range(n):
        p = price
        for _ in range(30):
            p *= math.exp((mu-0.5*sigma**2)+sigma*random.gauss(0,1))
            if p >= target: hits+=1; break
    return round(hits/n, 4)

def kalman_trend(d24, d7, d30):
    obs = [d24/1, d7/7, d30/30]
    Q, R = 0.1, 1.0; x, p = obs[0], 1.0
    for z in obs[1:]:
        x_pred, p_pred = x, p+Q
        K = p_pred/(p_pred+R)
        x, p = x_pred+K*(z-x_pred), (1-K)*p_pred
    return round(x, 4)

def fibonacci_score(price, ath):
    if ath<=0 or price<=0: return 50
    drop = (ath-price)/ath*100
    fib_data = [(23.6,75),(38.2,88),(50.0,80),(61.8,100),(78.6,82)]
    best = 30
    for level, base_score in fib_data:
        dist = abs(drop - level)
        if dist<=3:   score = base_score
        elif dist<=7: score = int(base_score*0.85)
        elif dist<=15:score = int(base_score*0.65)
        else:         score = 30
        if score > best: best = score
    return best

def shannon_entropy_score(d24, d7, d30, d1y):
    rates = [d24, d7/7, d30/30]
    if d1y!=0: rates.append(d1y/365)
    pos = sum(1 for r in rates if r>0)
    total = len(rates)
    if pos==0 or pos==total: return 90
    p_pos = pos/total; p_neg = (total-pos)/total
    h = -(p_pos*math.log2(p_pos) + p_neg*math.log2(p_neg))
    return round(max(10, min(100, (1-h)*100)))

def quantum_superposition_score(factor_scores):
    valid = [s for s in factor_scores if 0 < s <= 100]
    if not valid: return 50
    amplitudes = [math.sqrt(s/100) for s in valid]
    mean_amp = sum(amplitudes)/len(amplitudes)
    return round(mean_amp**2 * 100, 2)


# ═══════════════════════════════════════════════════════════════
# 20 FACTOR CALCULATIONS (same as v6)
# ═══════════════════════════════════════════════════════════════

def f_alpha(d24,d7,d30,b24,b7,b30): return (d24-b24)*.25+(d7-b7)*.45+(d30-b30)*.30
def f_beta(d30,b30): return round(d30/b30,3) if abs(b30)>1 else 1.0
def f_gamma(d24,d7,d30):
    we=d30/4.33; gr=(d7-we)/abs(we)*100 if abs(we)>0.1 else d7*5
    de=d7/7;     gd=(d24-de)/abs(de)*100 if abs(de)>0.01 else d24*10
    return gr*.55+gd*.45
def f_rsi(d30): return min(90,max(15,50+d30/30*3))
def f_macd(d7,d30): return d7/7-d30/30
def f_bollinger(price,h24,l24): return (price-l24)/(h24-l24)*100 if h24>l24 else 50.0
def f_volume(vol_m,mcap_m): return vol_m/mcap_m*100 if mcap_m>0 else 2.0
def f_sharpe(d24,d7,d30):
    avg=d24*.40+(d7/7)*.35+(d30/30)*.25; sp=abs(d24-d30/30)
    return avg/max(sp/2,0.5)
def f_trend(d24,d7,d30,d1y):
    p=[d24,d7,d30]; p.append(d1y) if d1y!=0 else None
    return sum(1 for x in p if x>0)/len(p)*100
def f_williams_r(price,h24,l24): return (h24-price)/(h24-l24)*-100 if h24>l24 else -50.0
def f_stochastic(price,h24,l24): return (price-l24)/(h24-l24)*100 if h24>l24 else 50.0
def f_obv(d24,vol_m): return vol_m if d24>0 else -vol_m
def f_sar(d24,d7,d30):
    if d24>0 and d7/7>d30/30: return 85
    if d24>0 and d7/7>0:      return 70
    if d24>0:                  return 55
    if d24<0 and d7/7<d30/30: return 25
    return 40
def f_ath_potential(price,ath):
    if ath<=0 or price<=0: return 50
    drop=(ath-price)/ath*100
    if drop>=90: return 95
    if drop>=80: return 88
    if drop>=70: return 78
    if drop>=60: return 65
    if drop>=50: return 52
    if drop>=30: return 38
    return 20
def f_liquidity(vol_m,mcap_m): return vol_m/mcap_m if mcap_m>0 else 0
def f_halving():
    last=date(2024,4,20); months=(date.today()-last).days/30.44
    if months<6:  return 60
    if months<8:  return 75
    if months<12: return 88
    if months<18: return 100
    if months<24: return 85
    if months<30: return 55
    if months<36: return 35
    return 60
def f_mcap_tier(mcap_m):
    if mcap_m>=50000: return 40
    if mcap_m>=10000: return 60
    if mcap_m>=1000:  return 85
    if mcap_m>=100:   return 75
    return 55

def sc_alpha(v):   return min(100,max(0,round((v+30)/60*100)))
def sc_beta(v):
    if v<0:   return 5
    if v<0.5: return 25
    if v<1.0: return 50
    if v<1.5: return 72
    if v<2.5: return 95
    if v<4.0: return 80
    return 40
def sc_gamma(v):   return min(100,max(0,round((v+100)/200*100)))
def sc_rsi(v):     return 100 if v<=25 else 85 if v<=35 else 68 if v<=45 else 52 if v<=55 else 38 if v<=65 else 22 if v<=75 else 8
def sc_macd(v):    return 100 if v>1.5 else 85 if v>0.5 else 70 if v>0.1 else 58 if v>0 else 45 if v>-0.1 else 32 if v>-0.5 else 18 if v>-1.5 else 8
def sc_boll(v):    return 100 if v<=15 else 82 if v<=30 else 65 if v<=45 else 50 if v<=60 else 35 if v<=75 else 20 if v<=90 else 8
def sc_vol(v):     return 100 if v>=30 else 88 if v>=20 else 75 if v>=10 else 62 if v>=5 else 50 if v>=2 else 35 if v>=1 else 18
def sc_sharpe(v):  return 100 if v>=2 else 82 if v>=1 else 65 if v>=0.5 else 50 if v>=0 else 35 if v>=-0.5 else 20 if v>=-1 else 8
def sc_trend(v):   return 100 if v>=75 else 70 if v>=50 else 40 if v>=25 else 15
def sc_williams(v):return 100 if v<=-80 else 78 if v<=-60 else 55 if v<=-40 else 35 if v<=-20 else 15
def sc_stoch(v):   return 100 if v<=20 else 80 if v<=35 else 60 if v<=50 else 45 if v<=65 else 28 if v<=80 else 10
def sc_obv(o,v):
    r=o/v if v>0 else 0
    return 100 if r>=0.8 else 80 if r>=0.5 else 55 if r>=0 else 35 if r>=-0.5 else 15
def sc_fg(v):      return 100 if v<=15 else 88 if v<=30 else 72 if v<=45 else 55 if v<=55 else 38 if v<=70 else 22 if v<=85 else 8
def sc_btcdom(v,is_btc):
    if is_btc: return 85 if v>=55 else 70 if v>=50 else 55
    if v<=40:  return 100
    if v<=45:  return 85
    if v<=50:  return 65
    if v<=55:  return 45
    return 25
def sc_liq(vol_m,mcap_m):
    r=vol_m/mcap_m if mcap_m>0 else 0
    return 100 if r>=0.50 else 88 if r>=0.20 else 75 if r>=0.10 else 60 if r>=0.05 else 45 if r>=0.02 else 25

WEIGHTS = {
    'alpha':0.118,'macd':0.0909,'gamma':0.0909,'rsi':0.0818,
    'stoch':0.0636,'vol':0.0727,'fg':0.0545,'boll':0.0545,
    'williams':0.0455,'sar':0.0455,'sharpe':0.0364,'trend':0.0364,
    'ath':0.0364,'btcdom':0.0364,'obv':0.0364,'fib':0.0273,
    'liq':0.0182,'halving':0.0182,'mcap':0.0182,'beta':0.0182,
}

def compute_score(d24,d7,d30,d1y,b24,b7,b30,price,ath,h24,l24,vol_m,mcap_m,fg,btc_dom,halv,is_btc):
    alpha=f_alpha(d24,d7,d30,b24,b7,b30); beta=f_beta(d30,b30)
    gamma=f_gamma(d24,d7,d30); rsi_v=f_rsi(d30); macd_v=f_macd(d7,d30)
    boll_v=f_bollinger(price,h24,l24); vol_v=f_volume(vol_m,mcap_m)
    sharpe=f_sharpe(d24,d7,d30); trend=f_trend(d24,d7,d30,d1y)
    wr_v=f_williams_r(price,h24,l24); stoch_v=f_stochastic(price,h24,l24)
    obv_v=f_obv(d24,vol_m); fib_v=fibonacci_score(price,ath)
    sar_v=f_sar(d24,d7,d30); ath_v=f_ath_potential(price,ath)
    liq_v=f_liquidity(vol_m,mcap_m); mcap_v=f_mcap_tier(mcap_m)
    scores = {
        'alpha':sc_alpha(alpha),'beta':sc_beta(beta),'gamma':sc_gamma(gamma),
        'rsi':sc_rsi(rsi_v),'macd':sc_macd(macd_v),'boll':sc_boll(boll_v),
        'vol':sc_vol(vol_v),'sharpe':sc_sharpe(sharpe),'trend':sc_trend(trend),
        'williams':sc_williams(wr_v),'stoch':sc_stoch(stoch_v),
        'obv':sc_obv(obv_v,max(vol_m,0.001)),'fib':fib_v,
        'fg':sc_fg(fg),'btcdom':sc_btcdom(btc_dom,is_btc),
        'halving':halv,'sar':sar_v,'ath':ath_v,
        'liq':sc_liq(vol_m,mcap_m),'mcap':mcap_v,
    }
    final=min(100,max(0,round(sum(scores[k]*WEIGHTS[k] for k in WEIGHTS))))
    return {
        'score':final,
        'alpha':round(alpha,2),'alphaSc':scores['alpha'],
        'beta':round(beta,3),'betaSc':scores['beta'],
        'gamma':round(gamma,2),'gammaSc':scores['gamma'],
        'rsi':round(rsi_v,1),'rsiSc':scores['rsi'],
        'macd':round(macd_v,4),'macdSc':scores['macd'],
        'bollPos':round(boll_v,1),'bollSc':scores['boll'],
        'volRatio':round(vol_v,2),'volSc':scores['vol'],
        'sharpe':round(sharpe,3),'sharpeSc':scores['sharpe'],
        'trend':round(trend,1),'trendSc':scores['trend'],
        'williams':round(wr_v,1),'williamsSc':scores['williams'],
        'stoch':round(stoch_v,1),'stochSc':scores['stoch'],
        'obv':round(obv_v,2),'obvSc':scores['obv'],
        'fibonacci':fib_v,'fibSc':fib_v,
        'fearGreedSc':scores['fg'],'btcDomSc':scores['btcdom'],
        'halvingSc':scores['halving'],'sarSc':scores['sar'],
        'athPot':ath_v,'athSc':scores['ath'],
        'liqSc':scores['liq'],'mcapSc':scores['mcap'],
    }


def assign_signals(coins):
    """Relative ranking — always produces BUY signals in any market."""
    tradeable = [c for c in coins if c.get('category') not in ('Stablecoin',)]
    tradeable.sort(key=lambda x: -x['score'])
    n = len(tradeable)
    for i, c in enumerate(tradeable):
        pct = i/n; d24 = c.get('change24h',0); alpha = c.get('alpha',0)
        if pct < 0.15:
            c['techSignal'] = 'STRONG BUY' if d24>0 and alpha>3 else ('BUY' if d24>0 else 'WATCH')
        elif pct < 0.35: c['techSignal'] = 'BUY' if d24>0 else 'WATCH'
        elif pct < 0.60: c['techSignal'] = 'WATCH'
        elif pct < 0.80: c['techSignal'] = 'CAUTION'
        else:            c['techSignal'] = 'AVOID'
    for c in coins:
        if c.get('category') == 'Stablecoin': c['techSignal'] = 'AVOID'
    return coins


def predict_prices(price,d24,d7,d30):
    r24=d24/100; r7=(pow(1+d7/100,1/7)-1) if d7>-100 else -0.05
    r30=(pow(1+d30/100,1/30)-1) if d30>-100 else -0.03
    dr=r24*.25+r7*.50+r30*.25
    p7=round(price*pow(max(1+dr*.65,0.01),7),8)
    p30=round(price*pow(max(1+dr*.50,0.01),30),8)
    p90=round(price*pow(max(1+dr*.35,0.01),90),8)
    return {
        'd7':{'price':p7,'pct':round((p7-price)/price*100,1)},
        'd30':{'price':p30,'pct':round((p30-price)/price*100,1)},
        'd90':{'price':p90,'pct':round((p90-price)/price*100,1)},
    }


# ═══════════════════════════════════════════════════════════════
# API FETCHING
# ═══════════════════════════════════════════════════════════════

def fetch_page(page):
    for attempt in range(4):
        try:
            r=requests.get('https://api.coingecko.com/api/v3/coins/markets',
                headers=HEADERS,
                params={'vs_currency':'usd','order':'market_cap_desc',
                        'per_page':50,'page':page,'sparkline':'false',
                        'price_change_percentage':'24h,7d,30d,1y'},
                timeout=30)
            if r.status_code==200:
                data=r.json(); print(f"  Page {page:>2}: {len(data)} coins ✅"); return data
            elif r.status_code==429:
                wait=70*(attempt+1); print(f"  Rate limit page {page}, wait {wait}s..."); time.sleep(wait)
            else: time.sleep(15)
        except Exception as e: print(f"  Page {page} error: {e}"); time.sleep(15)
    return []

def fetch_fear_greed():
    try:
        r=requests.get('https://api.alternative.me/fng/?limit=1',headers=HEADERS,timeout=10)
        if r.status_code==200:
            d=r.json(); val=int(d['data'][0]['value']); cls=d['data'][0]['value_classification']
            print(f"  Fear/Greed: {val} ({cls}) ✅"); return val,cls
    except: pass
    return 50,'Neutral'

def fetch_btc_dom():
    try:
        r=requests.get('https://api.coingecko.com/api/v3/global',headers=HEADERS,timeout=10)
        if r.status_code==200:
            dom=r.json()['data']['market_cap_percentage']['btc']
            print(f"  BTC Dom: {dom:.1f}% ✅"); return round(dom,2)
    except: pass
    return 50.0


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

MONTH_NAMES=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def main():
    now_utc=datetime.now(timezone.utc)
    now_ist=now_utc+timedelta(hours=5,minutes=30)
    print("="*62)
    print("  ULTIMATE CRYPTO ANALYSER v7 — WITH NEWS SENTIMENT")
    print(f"  500 Coins · 20 Factors · Quantum · FinBERT-style NLP")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("="*62)

    # Step 1: Global data
    print("\nStep 1: Global market data...")
    fg_value,fg_class=fetch_fear_greed()
    btc_dom=fetch_btc_dom()
    halving_sc=f_halving()

    # Step 2: News sentiment
    print("\nStep 2: Fetching news headlines for sentiment analysis...")
    all_headlines=fetch_all_news()

    # Market-wide sentiment (general headlines)
    if all_headlines:
        all_scores=[SIA.polarity_scores(t)['compound'] for t,_ in all_headlines[:50]]
        market_sent=round(sum(all_scores)/len(all_scores),3)
        market_sent_label=sentiment_label(market_sent)
    else:
        market_sent=0.0; market_sent_label="NEUTRAL"
    print(f"  Market sentiment: {market_sent:+.3f} → {market_sent_label}")

    # Step 3: Fetch 500 coins
    print("\nStep 3: Fetching 500 coins...")
    all_raw=[]
    for page in range(1,11):
        batch=fetch_page(page); all_raw.extend(batch)
        if page<10: time.sleep(7)

    if not all_raw: print("ERROR: No data fetched!"); return
    print(f"Total raw: {len(all_raw)} coins")

    btc=next((c for c in all_raw if c['id']=='bitcoin'),None)
    btc24=(btc.get('price_change_percentage_24h_in_currency') or btc.get('price_change_percentage_24h') or 0) if btc else 0
    btc7=(btc.get('price_change_percentage_7d_in_currency') or 0) if btc else 0
    btc30=(btc.get('price_change_percentage_30d_in_currency') or 0) if btc else 0
    btc24,btc7,btc30=float(btc24),float(btc7),float(btc30)

    # Step 4: Compute all factors + sentiment
    print("\nStep 4: Computing 20 factors + scientific models + news sentiment...")
    coins_out=[]

    for raw in all_raw:
        cg_id=raw.get('id','')
        if cg_id in EXCLUDE_IDS: continue
        price=float(raw.get('current_price') or 0)
        if price<=0: continue

        name=raw.get('name',''); symbol=(raw.get('symbol') or '').upper()
        rank=raw.get('market_cap_rank',999)
        ath=float(raw.get('ath') or 0)
        mcap=round(float(raw.get('market_cap') or 0)/1e6,1)
        vol=round(float(raw.get('total_volume') or 0)/1e6,1)
        h24=float(raw.get('high_24h') or price*1.01)
        l24=float(raw.get('low_24h') or price*0.99)
        d24=float(raw.get('price_change_percentage_24h_in_currency') or raw.get('price_change_percentage_24h') or 0)
        d7=float(raw.get('price_change_percentage_7d_in_currency') or 0)
        d30=float(raw.get('price_change_percentage_30d_in_currency') or 0)
        d1y=float(raw.get('price_change_percentage_1y_in_currency') or 0)
        is_btc=(cg_id=='bitcoin')
        category=get_category(cg_id)

        # 20 technical factors
        sc=compute_score(d24,d7,d30,d1y,btc24,btc7,btc30,price,ath,h24,l24,vol,mcap,fg_value,btc_dom,halving_sc,is_btc)

        # Scientific methods
        target10=round(price*1.10,8)
        gbm_p=gbm_target_prob(price,target10,d30)
        bs_p=black_scholes_prob(price,target10,d30)
        mc_p=monte_carlo_prob(price,target10,d24,d30,n=300)
        kal_rate=kalman_trend(d24,d7,d30)
        entropy=shannon_entropy_score(d24,d7,d30,d1y)
        all_factor_scores=[
            sc['alphaSc'],sc['macdSc'],sc['gammaSc'],sc['rsiSc'],
            sc['stochSc'],sc['volSc'],sc['fearGreedSc'],sc['bollSc'],
            sc['williamsSc'],sc['sarSc'],sc['sharpeSc'],sc['trendSc'],
            sc['athSc'],sc['btcDomSc'],sc['obvSc'],sc['fibSc'],
            sc['liqSc'],sc['halvingSc'],sc['mcapSc'],sc['betaSc'],
        ]
        q_score=quantum_superposition_score(all_factor_scores)
        sci_confidence=round(bs_p*30+mc_p*30+gbm_p*20+(q_score/100)*20,2)

        # News sentiment
        sent_compound,sent_label,sent_headlines,is_market=score_coin_sentiment(name,symbol,cg_id,all_headlines)
        sent_score=sentiment_to_score(sent_compound)

        pred=predict_prices(price,d24,d7,d30)
        ath_drop=round((price-ath)/ath*100,1) if ath>0 else 0

        coins_out.append({
            'rank':rank,'name':name,'symbol':symbol,
            'category':category,'cgId':cg_id,
            'price':price,'change24h':round(d24,4),
            'change7d':round(d7,4),'change30d':round(d30,4),'change1y':round(d1y,4),
            'marketCapM':mcap,'volumeM':vol,
            'high24h':round(h24,8),'low24h':round(l24,8),
            'target10pct':target10,'ath':ath,'athDrop':ath_drop,
            'athDate':(raw.get('ath_date') or '')[:10],
            'support':round(l24,8),'resistance':round(h24,8),
            'techSignal':'WATCH',
            **sc,
            # Scientific
            'gbmProb':gbm_p,'bsProb':bs_p,'mcProb':mc_p,
            'kalmanRate':kal_rate,'shannonScore':entropy,
            'quantumScore':round(q_score,1),'sciConfidence':sci_confidence,
            # News sentiment
            'sentimentScore':sent_score,
            'sentimentCompound':sent_compound,
            'sentimentLabel':sent_label,
            'sentimentIcon':sentiment_icon(sent_label),
            'sentimentIsMarket':is_market,
            'newsHeadlines':sent_headlines,
            # Prediction
            'pred':pred,'fearGreed':fg_value,'fearGreedClass':fg_class,'btcDom':btc_dom,
        })

    # Step 5: Relative ranking → technical signal
    print(f"\nStep 5: Ranking {len(coins_out)} coins...")
    coins_out=assign_signals(coins_out)

    # Step 6: Apply news sentiment adjustment to signal
    print("Step 6: Applying news sentiment adjustments...")
    upgraded=0; downgraded=0
    for c in coins_out:
        tech=c['techSignal']
        final=adjust_signal(tech, c['sentimentLabel'])
        c['signal']=final
        if final!=tech:
            if ['STRONG BUY','BUY','WATCH','CAUTION','AVOID'].index(final) < \
               ['STRONG BUY','BUY','WATCH','CAUTION','AVOID'].index(tech): upgraded+=1
            else: downgraded+=1
    print(f"  Upgraded: {upgraded} · Downgraded: {downgraded} by news sentiment")

    # Sort by final signal then score
    order={'STRONG BUY':0,'BUY':1,'WATCH':2,'CAUTION':3,'AVOID':4}
    coins_out.sort(key=lambda x:(order.get(x['signal'],4),-x['score']))

    sb=[c for c in coins_out if c['signal']=='STRONG BUY']
    b =[c for c in coins_out if c['signal']=='BUY']
    w =[c for c in coins_out if c['signal']=='WATCH']
    ca=[c for c in coins_out if c['signal']=='CAUTION']
    av=[c for c in coins_out if c['signal']=='AVOID']

    print(f"\nTop 5 STRONG BUY:")
    for c in sb[:5]:
        print(f"  {c['symbol']:<8} Score={c['score']} Q={c['quantumScore']:.0f} Sent={c['sentimentLabel']} {c['sentimentIcon']}")

    output={
        'updatedAt':now_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'updatedAtIST':now_ist.strftime('%d %b %Y %I:%M %p IST'),
        'currentMonth':MONTH_NAMES[now_ist.month-1],
        'totalCoins':len(coins_out),
        'strongBuyCount':len(sb),'buyCount':len(b),
        'watchCount':len(w),'cautionCount':len(ca),'avoidCount':len(av),
        'fearGreed':fg_value,'fearGreedClass':fg_class,
        'btcDominance':btc_dom,'halvingScore':halving_sc,
        'marketSentiment':market_sent,'marketSentimentLabel':market_sent_label,
        'newsCount':len(all_headlines),
        'sentimentUpgrades':upgraded,'sentimentDowngrades':downgraded,
        'btcRef':{'change24h':btc24,'change7d':btc7,'change30d':btc30},
        'engine':'20-Factor + Scientific/Quantum + News Sentiment v7 | 500 Coins',
        'coins':coins_out,
    }

    os.makedirs('data',exist_ok=True)
    with open('data/prices.json','w') as f:
        json.dump(output,f,separators=(',',':'))

    sz=os.path.getsize('data/prices.json')/1024
    print("\n"+"="*62)
    print(f"  ✅ {len(coins_out)} coins analysed")
    print(f"  ⭐ STRONG BUY  : {len(sb)}  (after sentiment)")
    print(f"  🟢 BUY         : {len(b)}")
    print(f"  🟡 WATCH       : {len(w)}")
    print(f"  🟠 CAUTION     : {len(ca)}")
    print(f"  🔴 AVOID       : {len(av)}")
    print(f"  📰 Headlines   : {len(all_headlines)}")
    print(f"  📈 Upgraded    : {upgraded}  📉 Downgraded: {downgraded}")
    print(f"  🌍 Market sent : {market_sent:+.3f} ({market_sent_label})")
    print(f"  💾 data/prices.json ({sz:.0f} KB)")
    print("="*62)

if __name__=='__main__':
    main()

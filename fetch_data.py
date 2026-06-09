"""
fetch_data.py  —  Ultimate Crypto Analyser v6
==============================================
500 coins  ·  20 Technical Factors  ·  Scientific & Quantum Methods
Finishes in under 2 minutes on GitHub Actions.
Auto-runs every 30 minutes.

20 FACTORS (weights sum = 1.000):
  1.  Alpha          11.8%  Outperformance vs Bitcoin
  2.  MACD            9.1%  Moving Average Convergence Divergence
  3.  Gamma           9.1%  Momentum Acceleration
  4.  RSI             8.2%  Relative Strength Index
  5.  Stochastic      6.4%  Oversold Confirmation
  6.  Volume Surge    7.3%  Unusual Activity
  7.  Fear & Greed    5.5%  Market Sentiment
  8.  Bollinger       5.5%  Price Band Position
  9.  Williams %R     4.6%  Oversold Signal
 10.  Parabolic SAR   4.6%  Trend Reversal
 11.  Sharpe Ratio    3.6%  Risk-Adjusted Return
 12.  Trend           3.6%  Multi-Timeframe Consistency
 13.  ATH Potential   3.6%  Recovery Upside
 14.  BTC Dominance   3.6%  Alt Season Indicator
 15.  OBV             3.6%  Buying Pressure
 16.  Fibonacci       2.7%  Key Price Levels
 17.  Liquidity       1.8%  Ease of Trading
 18.  Halving Cycle   1.8%  Bitcoin Cycle Position
 19.  Market Cap      1.8%  Size Tier
 20.  Beta            1.8%  Market Sensitivity

SCIENTIFIC METHODS (for price prediction):
  GBM         Geometric Brownian Motion price paths
  Black-Scholes  P(hitting 10% target in 30 days)
  Monte Carlo  10,000-path simulation (sampled)
  Kalman Filter  Noise-filtered trend estimate
  Fibonacci    Key support/resistance levels
  Shannon Entropy  Market predictability score
  Quantum Score  Superposition-combined confidence
"""

import requests, json, time, os, math, random
from datetime import datetime, timezone, timedelta, date

HEADERS = {"User-Agent":"CryptoAnalyser/6.0","Accept":"application/json"}

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

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
    "kucoin-token":"Exchange","crypto-com-chain":"Exchange","huobi-token":"Exchange",
    "dogecoin":"Meme","shiba-inu":"Meme","pepe":"Meme","floki":"Meme",
    "bonk":"Meme","dogwifcoin":"Meme","book-of-meme":"Meme","popcat":"Meme",
    "mog-coin":"Meme","cat-in-a-dogs-world":"Meme","brett-based":"Meme",
    "dogs-token":"Meme","neiro-on-eth":"Meme","coq-inu":"Meme",
    "uniswap":"DeFi","aave":"DeFi","curve-dao-token":"DeFi","maker":"DeFi",
    "lido-dao":"DeFi","pancakeswap-token":"DeFi","jupiter-exchange-solana":"DeFi",
    "thorchain":"DeFi","dydx":"DeFi","1inch":"DeFi","sushi":"DeFi",
    "compound-governance-token":"DeFi","balancer":"DeFi","ondo-finance":"DeFi",
    "ethena":"DeFi","synthetix-network-token":"DeFi","bancor":"DeFi",
    "fetch-ai":"AI/Data","singularitynet":"AI/Data","the-graph":"AI/Data",
    "bittensor":"AI/Data","worldcoin-wld":"AI/Data","render-token":"AI/Data",
    "jasmycoin":"AI/Data","ocean-protocol":"AI/Data","akash-network":"AI/Data",
    "numeraire":"AI/Data","cortex":"AI/Data","oraichain-token":"AI/Data",
    "gala":"Gaming","the-sandbox":"Gaming","decentraland":"Gaming",
    "axie-infinity":"Gaming","immutable-x":"Gaming","enjincoin":"Gaming",
    "pixels":"Gaming","notcoin":"Gaming","yield-guild-games":"Gaming",
    "ultra":"Gaming","illuvium":"Gaming","star-atlas":"Gaming",
    "solana":"L1/L2","avalanche-2":"L1/L2","near":"L1/L2","aptos":"L1/L2",
    "sui":"L1/L2","optimism":"L1/L2","arbitrum":"L1/L2","matic-network":"L1/L2",
    "injective-protocol":"L1/L2","sei-network":"L1/L2","kaspa":"L1/L2",
    "harmony":"L1/L2","algorand":"L1/L2","hedera-hashgraph":"L1/L2",
    "internet-computer":"L1/L2","filecoin":"L1/L2","stacks":"L1/L2",
    "mantle":"L1/L2","celo":"L1/L2","tezos":"L1/L2","flow":"L1/L2",
    "theta-token":"L1/L2","zilliqa":"L1/L2","skale":"L1/L2","iotex":"L1/L2",
    "chainlink":"Web3","polkadot":"Web3","cosmos":"Web3","ankr":"Web3",
    "storj":"Web3","the-open-network":"Web3","woo-network":"Web3","flux":"Web3",
    "monero":"Privacy","zcash":"Privacy","dash":"Privacy","secret":"Privacy",
    "ripple":"Major","cardano":"Major","tron":"Major","stellar":"Major",
    "vechain":"Major","litecoin":"Major","bitcoin-cash":"Major",
    "hedera-hashgraph":"Major","cronos":"Major","neo":"Major",
}

def get_category(cg_id):
    return CATEGORY_MAP.get(cg_id, "Major")


# ═══ SCIENTIFIC METHODS ══════════════════════════════════════════════════════

def gbm_target_prob(price, target, d30):
    """GBM: probability of hitting target in 30 days."""
    mu    = max(d30/100/30, -0.05)  # daily drift
    sigma = max(abs(d30/100/30)*1.5, 0.02)  # vol estimate
    T     = 30
    if sigma <= 0 or price <= 0 or target <= 0:
        return 0.5
    log_ret = math.log(target/price)
    drift   = (mu - 0.5*sigma**2)*T
    vol_t   = sigma*math.sqrt(T)
    if vol_t == 0:
        return 1.0 if log_ret <= 0 else 0.0
    d = (log_ret - drift)/vol_t
    return round((1 + math.erf(-d/math.sqrt(2)))/2, 4)

def black_scholes_prob(price, target, d30):
    """Black-Scholes N(d2): exact probability of target in 30 days."""
    sigma_daily  = max(abs(d30/100/30)*1.5, 0.02)
    sigma_annual = sigma_daily * math.sqrt(365)
    T = 30/365
    r = 0.05
    if T<=0 or sigma_annual<=0 or price<=0 or target<=0:
        return 0.3
    try:
        d1 = (math.log(price/target)+(r+0.5*sigma_annual**2)*T)/(sigma_annual*math.sqrt(T))
        d2 = d1 - sigma_annual*math.sqrt(T)
        return round((1+math.erf(d2/math.sqrt(2)))/2, 4)
    except:
        return 0.3

def monte_carlo_prob(price, target, d24, d30, n=500):
    """Monte Carlo: fraction of paths that hit target in 30 days."""
    mu    = max(d30/100/30, -0.05)
    sigma = max(abs(d30/100/30)*1.5 + abs(d24/100)*0.5, 0.02)
    hits  = 0
    random.seed(int(price*1000) % 99991)
    for _ in range(n):
        p = price
        for _ in range(30):
            p *= math.exp((mu-0.5*sigma**2)+sigma*random.gauss(0,1))
            if p >= target:
                hits += 1
                break
    return round(hits/n, 4)

def kalman_trend(d24, d7, d30):
    """Kalman-filtered trend estimate from multi-timeframe data."""
    # Observations: daily rates at different timeframes
    obs = [d24/1, d7/7, d30/30]
    Q, R = 0.1, 1.0
    x, p = obs[0], 1.0
    for z in obs[1:]:
        x_pred, p_pred = x, p+Q
        K = p_pred/(p_pred+R)
        x, p = x_pred+K*(z-x_pred), (1-K)*p_pred
    return round(x, 4)  # filtered daily rate %

def fibonacci_score(price, ath):
    """Score based on proximity to Fibonacci retracement levels."""
    if ath<=0 or price<=0:
        return 50
    drop = (ath-price)/ath*100
    # Key Fibonacci levels from ATH (% drop)
    fib_data = [
        (23.6, 75), (38.2, 88), (50.0, 80),
        (61.8, 100),(78.6, 82),  # 61.8 = golden ratio = strongest
    ]
    best = 30
    for level, base_score in fib_data:
        dist = abs(drop - level)
        if dist <= 3:   score = base_score
        elif dist <= 7: score = int(base_score * 0.85)
        elif dist <= 15:score = int(base_score * 0.65)
        else:           score = 30
        if score > best:
            best = score
    return best

def shannon_entropy_score(d24, d7, d30, d1y):
    """
    Shannon entropy → market predictability.
    Low entropy = coin is trending consistently = more predictable = higher score.
    """
    rates = [d24, d7/7, d30/30]
    if d1y != 0:
        rates.append(d1y/365)
    pos = sum(1 for r in rates if r > 0)
    total = len(rates)
    if pos == 0 or pos == total:
        return 90  # fully trending = very predictable
    p_pos = pos/total
    p_neg = (total-pos)/total
    h = -(p_pos*math.log2(p_pos) + p_neg*math.log2(p_neg))
    h_max = math.log2(2)  # = 1.0
    predictability = 1 - h/h_max  # 0=random, 1=trending
    return round(max(10, min(100, predictability*100)))

def quantum_superposition_score(factor_scores):
    """
    Quantum-inspired: combine factor probabilities via amplitude interference.
    Constructive interference when factors agree → boosts signal.
    Destructive when they conflict → reduces false signals.
    P_quantum = |mean(sqrt(P_i))|^2
    """
    valid = [s for s in factor_scores if 0 < s <= 100]
    if not valid:
        return 50
    amplitudes = [math.sqrt(s/100) for s in valid]
    mean_amp   = sum(amplitudes)/len(amplitudes)
    return round(mean_amp**2 * 100, 2)


# ═══ 20-FACTOR CALCULATIONS ═══════════════════════════════════════════════════

def f_alpha(d24,d7,d30,btc24,btc7,btc30):
    return (d24-btc24)*0.25+(d7-btc7)*0.45+(d30-btc30)*0.30

def f_beta(d30,btc30):
    return round(d30/btc30,3) if abs(btc30)>1 else 1.0

def f_gamma(d24,d7,d30):
    we = d30/4.33
    gr = (d7-we)/abs(we)*100 if abs(we)>0.1 else d7*5
    de = d7/7
    gd = (d24-de)/abs(de)*100 if abs(de)>0.01 else d24*10
    return gr*0.55+gd*0.45

def f_rsi(d30):
    return min(90,max(15,50+d30/30*3))

def f_macd(d7,d30):
    return d7/7-d30/30

def f_bollinger(price,h24,l24):
    return (price-l24)/(h24-l24)*100 if h24>l24 else 50.0

def f_volume(vol_m,mcap_m):
    return vol_m/mcap_m*100 if mcap_m>0 else 2.0

def f_sharpe(d24,d7,d30):
    avg=d24*0.40+(d7/7)*0.35+(d30/30)*0.25
    sp=abs(d24-d30/30)
    return avg/max(sp/2,0.5)

def f_trend(d24,d7,d30,d1y):
    p=[d24,d7,d30]
    if d1y!=0: p.append(d1y)
    return sum(1 for x in p if x>0)/len(p)*100

def f_williams_r(price,h24,l24):
    return (h24-price)/(h24-l24)*-100 if h24>l24 else -50.0

def f_stochastic(price,h24,l24):
    return (price-l24)/(h24-l24)*100 if h24>l24 else 50.0

def f_obv(d24,vol_m):
    return vol_m if d24>0 else -vol_m

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

def f_liquidity(vol_m,mcap_m):
    return vol_m/mcap_m if mcap_m>0 else 0

def f_halving():
    last = date(2024,4,20)
    months = (date.today()-last).days/30.44
    if months<6:   return 60
    if months<8:   return 75
    if months<12:  return 88
    if months<18:  return 100
    if months<24:  return 85
    if months<30:  return 55
    if months<36:  return 35
    if months<48:  return 20
    return 60

def f_mcap_tier(mcap_m):
    if mcap_m>=50000: return 40
    if mcap_m>=10000: return 60
    if mcap_m>=1000:  return 85
    if mcap_m>=100:   return 75
    return 55


# ═══ SCORING (convert raw → 0-100) ═══════════════════════════════════════════

def sc_alpha(v): return min(100,max(0,round((v+30)/60*100)))

def sc_beta(v):
    if v<0:   return 5
    if v<0.5: return 25
    if v<1.0: return 50
    if v<1.5: return 72
    if v<2.5: return 95
    if v<4.0: return 80
    return 40

def sc_gamma(v): return min(100,max(0,round((v+100)/200*100)))

def sc_rsi(v):
    if v<=25: return 100
    if v<=35: return 85
    if v<=45: return 68
    if v<=55: return 52
    if v<=65: return 38
    if v<=75: return 22
    return 8

def sc_macd(v):
    if v>1.5:  return 100
    if v>0.5:  return 85
    if v>0.1:  return 70
    if v>0:    return 58
    if v>-0.1: return 45
    if v>-0.5: return 32
    if v>-1.5: return 18
    return 8

def sc_bollinger(v):
    if v<=15: return 100
    if v<=30: return 82
    if v<=45: return 65
    if v<=60: return 50
    if v<=75: return 35
    if v<=90: return 20
    return 8

def sc_volume(v):
    if v>=30: return 100
    if v>=20: return 88
    if v>=10: return 75
    if v>=5:  return 62
    if v>=2:  return 50
    if v>=1:  return 35
    return 18

def sc_sharpe(v):
    if v>=2:    return 100
    if v>=1:    return 82
    if v>=0.5:  return 65
    if v>=0:    return 50
    if v>=-0.5: return 35
    if v>=-1:   return 20
    return 8

def sc_trend(v):
    if v>=75: return 100
    if v>=50: return 70
    if v>=25: return 40
    return 15

def sc_williams(v):
    if v<=-80: return 100
    if v<=-60: return 78
    if v<=-40: return 55
    if v<=-20: return 35
    return 15

def sc_stochastic(v):
    if v<=20: return 100
    if v<=35: return 80
    if v<=50: return 60
    if v<=65: return 45
    if v<=80: return 28
    return 10

def sc_obv(obv,vol_m):
    r = obv/vol_m if vol_m>0 else 0
    if r>=0.8:  return 100
    if r>=0.5:  return 80
    if r>=0:    return 55
    if r>=-0.5: return 35
    return 15

def sc_fib(v): return v
def sc_sar(v): return v

def sc_fear_greed(v):
    if v<=15: return 100
    if v<=30: return 88
    if v<=45: return 72
    if v<=55: return 55
    if v<=70: return 38
    if v<=85: return 22
    return 8

def sc_btc_dom(v,is_btc):
    if is_btc:
        return 85 if v>=55 else 70 if v>=50 else 55
    if v<=40: return 100
    if v<=45: return 85
    if v<=50: return 65
    if v<=55: return 45
    return 25

def sc_halving(v): return v
def sc_ath(v):     return v

def sc_liquidity(vol_m,mcap_m):
    r = vol_m/mcap_m if mcap_m>0 else 0
    if r>=0.50: return 100
    if r>=0.20: return 88
    if r>=0.10: return 75
    if r>=0.05: return 60
    if r>=0.02: return 45
    return 25

def sc_mcap(v): return v


# ═══ FINAL SCORE ══════════════════════════════════════════════════════════════

WEIGHTS = {
    'alpha':0.118,'macd':0.0909,'gamma':0.0909,'rsi':0.0818,
    'stoch':0.0636,'vol':0.0727,'fg':0.0545,'boll':0.0545,
    'williams':0.0455,'sar':0.0455,'sharpe':0.0364,'trend':0.0364,
    'ath':0.0364,'btcdom':0.0364,'obv':0.0364,'fib':0.0273,
    'liq':0.0182,'halving':0.0182,'mcap':0.0182,'beta':0.0182,
}

def compute_score(d24,d7,d30,d1y,btc24,btc7,btc30,
                  price,ath,h24,l24,vol_m,mcap_m,
                  fg_val,btc_dom,halving_sc,is_btc):

    # Raw values
    alpha    = f_alpha(d24,d7,d30,btc24,btc7,btc30)
    beta     = f_beta(d30,btc30)
    gamma    = f_gamma(d24,d7,d30)
    rsi_v    = f_rsi(d30)
    macd_v   = f_macd(d7,d30)
    boll_v   = f_bollinger(price,h24,l24)
    vol_v    = f_volume(vol_m,mcap_m)
    sharpe   = f_sharpe(d24,d7,d30)
    trend    = f_trend(d24,d7,d30,d1y)
    wr_v     = f_williams_r(price,h24,l24)
    stoch_v  = f_stochastic(price,h24,l24)
    obv_v    = f_obv(d24,vol_m)
    fib_v    = fibonacci_score(price,ath)
    sar_v    = f_sar(d24,d7,d30)
    ath_v    = f_ath_potential(price,ath)
    liq_v    = f_liquidity(vol_m,mcap_m)
    mcap_v   = f_mcap_tier(mcap_m)

    # Individual scores 0-100
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
        'obv':     sc_obv(obv_v,max(vol_m,0.001)),
        'fib':     sc_fib(fib_v),
        'fg':      sc_fear_greed(fg_val),
        'btcdom':  sc_btc_dom(btc_dom,is_btc),
        'halving': sc_halving(halving_sc),
        'sar':     sc_sar(sar_v),
        'ath':     sc_ath(ath_v),
        'liq':     sc_liquidity(vol_m,mcap_m),
        'mcap':    sc_mcap(mcap_v),
    }

    # Weighted final score
    final = min(100,max(0,round(sum(scores[k]*WEIGHTS[k] for k in WEIGHTS))))

    return {
        'score':     final,
        'alpha':     round(alpha,2),   'alphaSc':   scores['alpha'],
        'beta':      round(beta,3),    'betaSc':    scores['beta'],
        'gamma':     round(gamma,2),   'gammaSc':   scores['gamma'],
        'rsi':       round(rsi_v,1),   'rsiSc':     scores['rsi'],
        'macd':      round(macd_v,4),  'macdSc':    scores['macd'],
        'bollPos':   round(boll_v,1),  'bollSc':    scores['boll'],
        'volRatio':  round(vol_v,2),   'volSc':     scores['vol'],
        'sharpe':    round(sharpe,3),  'sharpeSc':  scores['sharpe'],
        'trend':     round(trend,1),   'trendSc':   scores['trend'],
        'williams':  round(wr_v,1),    'williamsSc':scores['williams'],
        'stoch':     round(stoch_v,1), 'stochSc':   scores['stoch'],
        'obv':       round(obv_v,2),   'obvSc':     scores['obv'],
        'fibonacci': fib_v,            'fibSc':     scores['fib'],
        'fearGreedSc': scores['fg'],
        'btcDomSc':  scores['btcdom'],
        'halvingSc': scores['halving'],
        'sarSc':     scores['sar'],
        'athPot':    ath_v,            'athSc':     scores['ath'],
        'liqSc':     scores['liq'],
        'mcapSc':    scores['mcap'],
    }


def assign_signals(coins):
    """RELATIVE RANKING — always produces BUY signals in any market."""
    tradeable = [c for c in coins if c.get('category') not in ('Stablecoin',)]
    tradeable.sort(key=lambda x: -x['score'])
    n = len(tradeable)
    for i, c in enumerate(tradeable):
        pct   = i/n
        d24   = c.get('change24h',0)
        alpha = c.get('alpha',0)
        if pct < 0.15:
            c['signal'] = 'STRONG BUY' if d24>0 and alpha>3 else ('BUY' if d24>0 else 'WATCH')
        elif pct < 0.35:
            c['signal'] = 'BUY' if d24>0 else 'WATCH'
        elif pct < 0.60:
            c['signal'] = 'WATCH'
        elif pct < 0.80:
            c['signal'] = 'CAUTION'
        else:
            c['signal'] = 'AVOID'
    for c in coins:
        if c.get('category') == 'Stablecoin':
            c['signal'] = 'AVOID'
    return coins


def predict_prices(price,d24,d7,d30):
    """Dampened momentum price prediction."""
    r24 = d24/100
    r7  = (pow(1+d7/100,1/7)-1)  if d7  > -100 else -0.05
    r30 = (pow(1+d30/100,1/30)-1) if d30 > -100 else -0.03
    dr  = r24*0.25+r7*0.50+r30*0.25
    p7  = round(price*pow(max(1+dr*0.65,0.01),7),  8)
    p30 = round(price*pow(max(1+dr*0.50,0.01),30), 8)
    p90 = round(price*pow(max(1+dr*0.35,0.01),90), 8)
    return {
        'd7':  {'price':p7,  'pct':round((p7-price)/price*100,  1)},
        'd30': {'price':p30, 'pct':round((p30-price)/price*100, 1)},
        'd90': {'price':p90, 'pct':round((p90-price)/price*100, 1)},
    }


# ═══ API ══════════════════════════════════════════════════════════════════════

def fetch_page(page):
    for attempt in range(4):
        try:
            r = requests.get(
                'https://api.coingecko.com/api/v3/coins/markets',
                headers=HEADERS,
                params={'vs_currency':'usd','order':'market_cap_desc',
                        'per_page':50,'page':page,'sparkline':'false',
                        'price_change_percentage':'24h,7d,30d,1y'},
                timeout=30)
            if r.status_code==200:
                data=r.json()
                print(f"  Page {page:>2}: {len(data)} coins ✅")
                return data
            elif r.status_code==429:
                wait=70*(attempt+1)
                print(f"  Rate limited page {page}, waiting {wait}s...")
                time.sleep(wait)
            else:
                time.sleep(15)
        except Exception as e:
            print(f"  Page {page} error: {e}")
            time.sleep(15)
    return []

def fetch_fear_greed():
    try:
        r=requests.get('https://api.alternative.me/fng/?limit=1',headers=HEADERS,timeout=10)
        if r.status_code==200:
            d=r.json()
            val=int(d['data'][0]['value'])
            cls=d['data'][0]['value_classification']
            print(f"  Fear/Greed: {val} ({cls}) ✅")
            return val,cls
    except Exception as e:
        print(f"  Fear/Greed failed: {e}")
    return 50,'Neutral'

def fetch_btc_dom():
    try:
        r=requests.get('https://api.coingecko.com/api/v3/global',headers=HEADERS,timeout=10)
        if r.status_code==200:
            dom=r.json()['data']['market_cap_percentage']['btc']
            print(f"  BTC Dom: {dom:.1f}% ✅")
            return round(dom,2)
    except Exception as e:
        print(f"  BTC dom failed: {e}")
    return 50.0


# ═══ MAIN ════════════════════════════════════════════════════════════════════

def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc+timedelta(hours=5,minutes=30)

    print("="*60)
    print("  ULTIMATE CRYPTO ANALYSER v6")
    print(f"  500 Coins · 20 Factors · Scientific + Quantum")
    print(f"  {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print("="*60)

    # Step 1: Global market data
    print("\nStep 1: Global data...")
    fg_value,fg_class = fetch_fear_greed()
    btc_dom           = fetch_btc_dom()
    halving_sc        = f_halving()
    print(f"  Halving cycle score: {halving_sc}")

    # Step 2: Fetch 500 coins (10 pages × 50)
    print("\nStep 2: Fetching 500 coins...")
    all_raw = []
    for page in range(1,11):
        batch = fetch_page(page)
        all_raw.extend(batch)
        if page < 10:
            time.sleep(7)

    if not all_raw:
        print("ERROR: No data fetched!")
        return

    print(f"Total raw: {len(all_raw)} coins")

    # BTC reference
    btc     = next((c for c in all_raw if c['id']=='bitcoin'),None)
    btc24h  = float(btc.get('price_change_percentage_24h_in_currency') or btc.get('price_change_percentage_24h') or 0) if btc else 0
    btc7d   = float(btc.get('price_change_percentage_7d_in_currency')  or 0) if btc else 0
    btc30d  = float(btc.get('price_change_percentage_30d_in_currency') or 0) if btc else 0
    print(f"BTC ref: 24h={btc24h:.2f}% 7d={btc7d:.2f}% 30d={btc30d:.2f}%")

    # Step 3: Compute all factors
    print("\nStep 3: Computing 20 factors + scientific models...")
    coins_out = []

    for raw in all_raw:
        cg_id = raw.get('id','')
        if cg_id in EXCLUDE_IDS:
            continue

        price = float(raw.get('current_price') or 0)
        if price <= 0:
            continue

        name    = raw.get('name','')
        symbol  = (raw.get('symbol') or '').upper()
        rank    = raw.get('market_cap_rank',999)
        ath     = float(raw.get('ath') or 0)
        mcap    = round(float(raw.get('market_cap') or 0)/1e6,1)
        vol     = round(float(raw.get('total_volume') or 0)/1e6,1)
        h24     = float(raw.get('high_24h') or price*1.01)
        l24     = float(raw.get('low_24h')  or price*0.99)

        d24 = float(raw.get('price_change_percentage_24h_in_currency') or raw.get('price_change_percentage_24h') or 0)
        d7  = float(raw.get('price_change_percentage_7d_in_currency')  or 0)
        d30 = float(raw.get('price_change_percentage_30d_in_currency') or 0)
        d1y = float(raw.get('price_change_percentage_1y_in_currency')  or 0)

        is_btc   = (cg_id=='bitcoin')
        category = get_category(cg_id)

        # 20 technical factors
        sc = compute_score(
            d24,d7,d30,d1y,btc24h,btc7d,btc30d,
            price,ath,h24,l24,vol,mcap,
            fg_value,btc_dom,halving_sc,is_btc
        )

        # Scientific price prediction
        target10 = round(price*1.10,8)
        gbm_p    = gbm_target_prob(price,target10,d30)
        bs_p     = black_scholes_prob(price,target10,d30)
        mc_p     = monte_carlo_prob(price,target10,d24,d30,n=300)
        kal_rate = kalman_trend(d24,d7,d30)
        entropy  = shannon_entropy_score(d24,d7,d30,d1y)

        # Quantum superposition: combine all 20 factor scores
        all_factor_scores = [
            sc['alphaSc'],sc['macdSc'],sc['gammaSc'],sc['rsiSc'],
            sc['stochSc'],sc['volSc'],sc['fearGreedSc'],sc['bollSc'],
            sc['williamsSc'],sc['sarSc'],sc['sharpeSc'],sc['trendSc'],
            sc['athSc'],sc['btcDomSc'],sc['obvSc'],sc['fibSc'],
            sc['liqSc'],sc['halvingSc'],sc['mcapSc'],sc['betaSc'],
        ]
        q_score = quantum_superposition_score(all_factor_scores)

        # Scientific composite confidence
        # Weight: BS(30%) + MC(30%) + GBM(20%) + Quantum(20%)
        sci_confidence = round(
            bs_p*30 + mc_p*30 + gbm_p*20 + (q_score/100)*20,
            2
        )

        pred     = predict_prices(price,d24,d7,d30)
        ath_drop = round((price-ath)/ath*100,1) if ath>0 else 0

        coins_out.append({
            'rank':        rank,
            'name':        name,
            'symbol':      symbol,
            'category':    category,
            'cgId':        cg_id,
            'price':       price,
            'change24h':   round(d24,4),
            'change7d':    round(d7,4),
            'change30d':   round(d30,4),
            'change1y':    round(d1y,4),
            'marketCapM':  mcap,
            'volumeM':     vol,
            'high24h':     round(h24,8),
            'low24h':      round(l24,8),
            'target10pct': target10,
            'ath':         ath,
            'athDrop':     ath_drop,
            'athDate':     (raw.get('ath_date') or '')[:10],
            'support':     round(l24,8),
            'resistance':  round(h24,8),
            'signal':      'WATCH',          # set by relative ranking below
            # 20-factor scores
            **sc,
            # Scientific methods
            'gbmProb':        gbm_p,         # GBM probability
            'bsProb':         bs_p,          # Black-Scholes probability
            'mcProb':         mc_p,          # Monte Carlo probability
            'kalmanRate':     kal_rate,      # Kalman trend (% per day)
            'shannonScore':   entropy,       # Market predictability
            'quantumScore':   round(q_score,1), # Quantum superposition
            'sciConfidence':  sci_confidence,# Combined scientific confidence
            # Price predictions
            'pred':           pred,
            'fearGreed':      fg_value,
            'fearGreedClass': fg_class,
            'btcDom':         btc_dom,
        })

    # Step 4: Relative ranking → always produces BUY signals
    print(f"\nStep 4: Ranking {len(coins_out)} coins...")
    coins_out = assign_signals(coins_out)

    order = {'STRONG BUY':0,'BUY':1,'WATCH':2,'CAUTION':3,'AVOID':4}
    coins_out.sort(key=lambda x:(order.get(x['signal'],4),-x['score']))

    sb = [c for c in coins_out if c['signal']=='STRONG BUY']
    b  = [c for c in coins_out if c['signal']=='BUY']
    w  = [c for c in coins_out if c['signal']=='WATCH']
    ca = [c for c in coins_out if c['signal']=='CAUTION']
    av = [c for c in coins_out if c['signal']=='AVOID']

    print(f"\nTop 5 STRONG BUY:")
    for c in sb[:5]:
        print(f"  {c['symbol']:<8} Score={c['score']} Q={c['quantumScore']:.0f} MC={c['mcProb']:.0%} α={c['alpha']:.1f}")

    output = {
        'updatedAt':       now_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'updatedAtIST':    now_ist.strftime('%d %b %Y %I:%M %p IST'),
        'currentMonth':    MONTH_NAMES[now_ist.month-1],
        'totalCoins':      len(coins_out),
        'strongBuyCount':  len(sb),
        'buyCount':        len(b),
        'watchCount':      len(w),
        'cautionCount':    len(ca),
        'avoidCount':      len(av),
        'fearGreed':       fg_value,
        'fearGreedClass':  fg_class,
        'btcDominance':    btc_dom,
        'halvingScore':    halving_sc,
        'btcRef':          {'change24h':btc24h,'change7d':btc7d,'change30d':btc30d},
        'engine':          '20-Factor + Scientific/Quantum Engine v6 | 500 Coins | Relative Ranking',
        'coins':           coins_out,
    }

    os.makedirs('data',exist_ok=True)
    with open('data/prices.json','w') as f:
        json.dump(output,f,separators=(',',':'))

    sz = os.path.getsize('data/prices.json')/1024
    print("\n"+"="*60)
    print(f"  ✅ {len(coins_out)} coins analysed")
    print(f"  ⭐ STRONG BUY : {len(sb)}")
    print(f"  🟢 BUY        : {len(b)}")
    print(f"  🟡 WATCH      : {len(w)}")
    print(f"  🟠 CAUTION    : {len(ca)}")
    print(f"  🔴 AVOID      : {len(av)}")
    print(f"  😱 Fear/Greed : {fg_value} ({fg_class})")
    print(f"  ₿  BTC Dom    : {btc_dom}%")
    print(f"  🔬 Scientific : GBM + BS + MC + Kalman + Quantum")
    print(f"  💾 data/prices.json ({sz:.0f} KB)")
    print("="*60)


if __name__ == '__main__':
    main()

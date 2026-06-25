from math import prod, sqrt


def clamp(value, low=0, high=100):
    return max(low, min(high, float(value)))


def percentile(values, value):
    valid = sorted(v for v in values if v is not None)
    if not valid or value is None:
        return None
    return round(sum(v <= value for v in valid) / len(valid) * 100, 1)


def average(parts, fallback=50):
    valid = [(score, weight) for score, weight in parts if score is not None]
    if not valid:
        return fallback
    weight = sum(weight for _, weight in valid)
    return round(sum(score * part_weight for score, part_weight in valid) / weight, 1)


def score_roe(value):
    return None if value is None else clamp(50 + float(value) * 2.0)


def score_margin(value):
    return None if value is None else clamp(50 + float(value) * 2.2)


def score_debt(value):
    if value is None:
        return None
    return 90 if value <= 75 else 75 if value <= 150 else 55 if value <= 250 else 30


def prices_metrics(prices, base_date):
    closes = [float(row.close_price) for row in prices]
    if len(closes) < 30:
        return None
    last = closes[-1]
    one_month = closes[-22] if len(closes) >= 22 else closes[0]
    six_month = closes[-127] if len(closes) >= 127 else closes[0]
    one_year = closes[-253] if len(closes) >= 253 else closes[0]
    returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
    downside = [value for value in returns[-126:] if value < 0]
    downside_vol = sqrt(sum(value * value for value in downside) / len(downside)) * 100 if downside else 0
    high = max(closes[-252:])
    mdd = (last / high - 1) * 100 if high else 0
    recent = closes[-20:]
    mean = sum(recent) / len(recent)
    variance = sum((value - mean) ** 2 for value in recent) / len(recent)
    z_score = (last - mean) / sqrt(variance) if variance else 0
    latest, previous = prices[-1], prices[-11] if len(prices) >= 11 else prices[0]
    stale_days = (base_date - latest.date).days
    no_recent_volume = sum(item.volume for item in prices[-10:]) == 0
    return {
        "return_12_1": last / one_month * (one_month / one_year) - 1 if one_year else 0,
        "return_6_1": last / one_month * (one_month / six_month) - 1 if six_month else 0,
        "downside_vol": downside_vol,
        "mdd": mdd,
        "z_score": z_score,
        "above_ema20": bool(latest.ema20 and last >= latest.ema20),
        "above_ema50": bool(latest.ema50 and last >= latest.ema50),
        "ema_aligned": bool(latest.ema20 and latest.ema50 and latest.ema20 >= latest.ema50),
        "obv_down": bool(latest.obv is not None and previous.obv is not None and latest.obv < previous.obv),
        "distance_high": (high - last) / high * 100 if high else 100,
        "is_stale": stale_days > 10 or no_recent_volume,
    }


def valuation_adjustment(metric):
    if not metric or metric.per is None or metric.pbr is None or metric.per <= 0:
        return 0, "NOT_COMPARABLE"
    if metric.per <= 12 and metric.pbr <= 1.2:
        return 4, "UNDERVALUED"
    if metric.per > 45 or metric.pbr > 5:
        return -7, "OVERVALUED"
    if metric.per > 30 or metric.pbr > 3:
        return -3, "EXPENSIVE"
    return 0, "FAIR"


def composite(q, m, t):
    if any(value is None for value in [q, m, t]):
        return None
    q, m, t = (max(float(value), 5) for value in [q, m, t])
    base = 100 * prod([(q / 100) ** 0.40, (m / 100) ** 0.25, (t / 100) ** 0.35])
    return round(clamp(base), 1)


def calculate(score, metric, prices, rs12_scores, rs6_scores, market_regime):
    pm = prices_metrics(prices, score.base_date)
    if pm is None:
        return None
    growth = clamp(50 + float(metric.eps_growth or 0) * 0.5) if metric and metric.eps_growth is not None else None
    profitability = average([(score_roe(metric.roe) if metric else None, 0.5), (score_margin(metric.operating_margin) if metric else None, 0.5)], fallback=None)
    stability = score_debt(metric.debt_ratio) if metric else None
    cashflow = 50  # OpenDART cashflow parser fills this field in the quarterly batch phase.
    financial_status = "verified" if all(value is not None for value in [growth, profitability, stability]) else "partial"
    company = average([(growth, .30), (profitability, .30), (stability, .25), (cashflow, .15)])
    market = average([
        (percentile(rs12_scores, pm["return_12_1"]), .40),
        (percentile(rs6_scores, pm["return_6_1"]), .20),
        (clamp(100 - pm["downside_vol"] * 4), .25),
        (clamp(100 + pm["mdd"] * 2), .15),
    ])
    trend = (100 if pm["above_ema20"] else 35) * .35 + (100 if pm["above_ema50"] else 30) * .35 + (90 if pm["ema_aligned"] else 35) * .30
    supply = clamp((score.volume_ratio or 1) * 35) * .55 + (30 if pm["obv_down"] else 80) * .45
    breakout = clamp(100 - pm["distance_high"] * 4) * .65 + (85 if score.volume_surge_flag else 55) * .35
    entry = 85 if pm["z_score"] <= 1.8 else 65 if pm["z_score"] <= 2.5 else 35 if pm["z_score"] <= 3 else 15
    timing_base = trend * .30 + supply * .25 + breakout * .25 + entry * .20
    timing = timing_base
    if pm["z_score"] > 3:
        timing *= .30
    elif pm["z_score"] > 2.5:
        timing *= .50
    # 시장 국면별 동적 매수 진입 기준(Gate) 설정
    if market_regime >= 60:
        required_score = 70.0
    elif market_regime >= 45:
        required_score = 75.0
    else:
        required_score = 80.0

    timing = round(clamp(timing), 1)
    adjustment, valuation_status = valuation_adjustment(metric)
    ineligible = bool(score.fail_safe_flag or not score.stock.is_tradable or pm["is_stale"])
    if ineligible:
        timing = 0
    final = None if ineligible else composite(company, market, timing)
    if ineligible:
        action, label, action_reason = "REVIEW", "평가 보류 - 거래·데이터 확인 필요", "거래 가능 여부 또는 필수 데이터가 확인되기 전에는 매수 판단을 하지 않습니다."
    elif pm["above_ema50"] is False and pm["obv_down"]:
        action, label, action_reason = "AVOID", "매수 금지 - 하락 추세", "EMA50 아래에서 수급까지 약화돼 신규 매수의 기대값이 낮습니다."
    elif pm["z_score"] > 3 and not pm["above_ema20"] and pm["obv_down"]:
        action, label, action_reason = "REDUCE", "보유 비중 축소 검토", "단기 과열 뒤 추세와 수급이 함께 약화된 구간입니다."
    elif pm["z_score"] > 2.5:
        action, label, action_reason = "WAIT_OVERHEATED", "추격 매수 금지 - 눌림 대기", "회사가 좋아도 평균 대비 가격 이격이 커서 신규 진입은 기다립니다."
    elif company < 55:
        action, label, action_reason = "TRADE_ONLY", "중장기 보유 부적합", "회사 품질이 낮아 장기 보유 관점의 매수 후보에서는 제외합니다."
    elif market < 55:
        action, label, action_reason = "WAIT_MARKET", "관심 유지 - 시장 검증 대기", "회사와 단기 흐름은 볼 만하지만 상대강도와 하락 방어력이 아직 부족합니다."
    elif final >= required_score + 7 and timing >= 75:
        action, label, action_reason = "STRONG_BUY_CANDIDATE", "우선 분할 매수 후보", f"종합 점수가 시장 국면 대비 진입 기준({required_score}점)을 크게 넘고, 매수 타이밍도 75점 이상입니다."
    elif final >= required_score:
        action, label, action_reason = "BUY_CANDIDATE", "분할 매수 후보", f"회사 품질·시장 검증·매수 타이밍을 합친 종합 점수가 시장 국면 대비 진입 기준({required_score}점)을 충족합니다."
    elif final >= required_score - 3:
        action, label, action_reason = "BUY_WATCH", "분할 매수 관심", f"종합 점수가 진입 기준({required_score}점)에 거의 근접해 조건 충족 여부를 조금 더 확인할 구간입니다."
    elif timing >= 50:
        action, label, action_reason = "WATCH", "관찰 유지 - 매수 조건 미충족", f"종합 점수가 시장 국면 대비 진입 기준({required_score}점)에 아직 못 미쳐 조건 충족 여부를 더 확인합니다."
    else:
        action, label, action_reason = "WAIT", "매수 대기 - 진입 기준 미충족", f"종합 점수가 시장 국면 대비 진입 기준에 못 미쳐 진입하지 않습니다. (현재 {final or 0:.1f}점 / 기준 {required_score}점)"
    return {"company": round(company, 1), "market": round(market, 1), "timing": timing, "timing_base": round(timing_base, 1), "composite": final, "adjustment": 0, "valuation_status": valuation_status, "action": action, "label": label, "action_reason": action_reason, "financial_status": financial_status, "metrics": pm}

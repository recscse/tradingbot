# services/strategy_engine.py
import math
import logging
from typing import List

logger = logging.getLogger(__name__)


def simple_ema(prices: List[float], period: int) -> float:
    if not prices or period <= 0:
        return 0.0
    # exponential moving average last value (fast implementation)
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def fibonacci_levels(spot: float, direction: str, retracement_levels=None):
    """
    Return target levels for forward or reverse fib logic.
    direction: 'bullish' or 'bearish'
    retracement_levels: list like [0.236, 0.382, 0.5, 0.618]
    """
    if retracement_levels is None:
        retracement_levels = [0.236, 0.382, 0.5, 0.618]
    levels = {}
    if direction == "bullish":
        # assume a move range; forward fib calculates potential targets above spot
        for r in retracement_levels:
            levels[f"target_{int(r*1000)}"] = round(spot * (1 + r), 2)
    else:
        for r in retracement_levels:
            levels[f"target_{int(r*1000)}"] = round(spot * (1 - r), 2)
    logger.debug("Fib levels (%s) for spot %s => %s", direction, spot, levels)
    return levels


def strategy_score(prices: List[float], direction: str):
    """
    Combine EMA and fibonacci distance to produce a simple score.
    Higher score = more favorable to trade.
    """
    ema_short = (
        simple_ema(prices[-9:], 9)
        if len(prices) >= 9
        else simple_ema(prices, max(1, len(prices)))
    )
    ema_long = simple_ema(prices[-21:], 21) if len(prices) >= 21 else ema_short
    ema_bias = (ema_short - ema_long) / (ema_long + 1e-9)
    spot = prices[-1] if prices else 0
    fib = fibonacci_levels(spot, direction)
    # naive score: ema_bias magnitude + inverse distance to first fib target
    first_target = list(fib.values())[0]
    dist = abs(first_target - spot) / (spot + 1e-9)
    score = round(ema_bias * 100 + (1 / (dist + 1e-3)), 3)
    logger.debug(
        "Strategy score for spot=%s => ema_bias=%s dist=%s score=%s",
        spot,
        ema_bias,
        dist,
        score,
    )
    return score, {"ema_short": ema_short, "ema_long": ema_long, "fib": fib}

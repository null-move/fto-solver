import math
import random


def clamp(value, low, high):
    return max(low, min(high, value))


def win_percent(cp):
    x = -0.00368208 * float(cp)
    if x >= 60:
        return 1.0
    if x <= -60:
        return 0.0
    return 1.0 / (1.0 + math.exp(x))


def fluency_penalty(seconds):
    seconds = clamp(seconds, 0.05, 3600.0)
    z = (math.log(seconds) - math.log(30.0)) / 0.75
    return clamp(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))), 0.0, 1.0)


def glicko_g(phi):
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / math.pi**2)


def update_rating(stats, score, opponent_rating=1500.0, opponent_phi=350.0):
    mu = (stats["mu"] - 1500.0) / 173.7178
    phi = stats["phi"] / 173.7178
    sigma = stats["sigma"]
    mu_opponent = (opponent_rating - 1500.0) / 173.7178
    phi_opponent = opponent_phi / 173.7178
    g = glicko_g(phi_opponent)
    expected = 1.0 / (1.0 + math.exp(-g * (mu - mu_opponent)))
    variance = 1.0 / (g * g * expected * (1.0 - expected))
    delta = variance * g * (score - expected)
    a, tau = math.log(sigma * sigma), 0.5

    def objective(x):
        ex = math.exp(x)
        denominator = phi * phi + variance + ex
        value = ex * (delta * delta - phi * phi - variance - ex) / (2 * denominator**2)
        return value - (x - a) / (tau * tau)

    left = a
    right = a - tau if delta * delta > phi * phi + variance else a + tau
    for _ in range(20):
        if objective(right) * objective(left) <= 0:
            break
        right += -tau if delta * delta > phi * phi + variance else tau

    for _ in range(100):
        f_left, f_right = objective(left), objective(right)
        middle = (
            left + (left - right) * f_left / (f_right - f_left)
            if f_right != f_left else (left + right) / 2
        )
        if abs(middle - left) < 1e-6:
            left = middle
            break
        if objective(middle) * f_left <= 0:
            right = left
        else:
            left = right
        left = middle

    sigma_new = math.exp(left / 2)
    phi_star = math.sqrt(phi * phi + sigma_new * sigma_new)
    phi_new = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / variance)
    mu_new = mu + phi_new * phi_new * g * (score - expected)
    return {
        "mu": mu_new * 173.7178 + 1500.0,
        "phi": clamp(phi_new * 173.7178, 30.0, 350.0),
        "sigma": clamp(sigma_new, 0.01, 0.3),
    }


def choose_category(stats, categories):
    scores = [
        item["phi"] / 350.0 + max(0.0, 1500.0 - item["mu"]) / 500.0
        for item in (stats[category] for category in categories)
    ]
    peak = max(scores)
    return random.choices(categories, [math.exp(score - peak) for score in scores], k=1)[0]

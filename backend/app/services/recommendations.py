"""Warstwa portfelowa: zamienia oceny modelu i stan portfela w konkretne propozycje.

Model ML ocenia atrakcyjność spółek. Ten moduł stosuje jawne reguły zależne od profilu
ryzyka (zakres spółek, limity koncentracji) i tworzy uzasadnienia w języku naturalnym.
Moduł nie zależy od bazy danych ani od HTTP.
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProfileLimits:
    allowed_indices: frozenset[str]
    max_volatility_percentile: float  # 1.0 = bez ograniczenia
    max_position_weight: float
    max_sector_weight: float


PROFILES = {
    "conservative": ProfileLimits(frozenset({"WIG20"}), 0.8, 0.15, 0.30),
    "balanced": ProfileLimits(frozenset({"WIG20", "mWIG40"}), 1.0, 0.20, 0.40),
    "dynamic": ProfileLimits(frozenset({"WIG20", "mWIG40"}), 1.0, 0.25, 0.50),
}

TOP_SHARE = 0.2          # propozycje zakupu: górne 20% spółek dostępnych dla profilu
BOTTOM_PERCENTILE = 0.2  # sygnał sprzedaży: dolne 20% rankingu modelu
MAX_NEW_PER_SECTOR = 2   # dywersyfikacja propozycji
MIN_NEW_POSITION = 0.05  # minimalny sensowny udział nowej pozycji w portfelu
ACTION_ORDER = {"REDUCE": 0, "CONSIDER_SELL": 1, "ADD": 2}

FEATURE_LABELS = {
    "mom_1m": "zmiana kursu w ostatnim miesiącu",
    "mom_3m": "zmiana kursu w 3 miesiące",
    "mom_6m": "zmiana kursu w 6 miesięcy",
    "mom_12m": "zmiana kursu w 12 miesięcy",
    "vol_3m": "zmienność",
    "dist_high_12m": "odległość od rocznego maksimum",
    "liquidity_3m": "średni obrót",
}


@dataclass
class Candidate:
    """Spółka z oceną modelu."""
    ticker: str
    name: str
    index_name: str
    sector: str | None
    score: float
    score_percentile: float  # pozycja w rankingu modelu: 0 = najgorsza, 1 = najlepsza
    explanation: dict


@dataclass
class Recommendation:
    ticker: str
    name: str
    sector: str | None
    action: str  # ADD, REDUCE, CONSIDER_SELL
    score: float | None
    reasons: list[str] = field(default_factory=list)


def format_change(value: float) -> str:
    """Zmiana procentowa w polskim zapisie: +443%, +42,3%, -7,6%."""
    text = f"{value:+.0%}" if abs(value) >= 1 else f"{value:+.1%}"
    return text.replace(".", ",")


def describe_position(percentile: float) -> str:
    """Pozycja spółki względem pozostałych spółek w danej cesze."""
    if percentile >= 0.995:
        return "najwyżej spośród ocenianych spółek"
    if percentile <= 0.005:
        return "najniżej spośród ocenianych spółek"
    if percentile >= 0.5:
        return f"wyżej niż u {percentile:.0%} pozostałych spółek"
    return f"niżej niż u {1 - percentile:.0%} pozostałych spółek"


def describe_factor(feature: str, explanation: dict) -> str:
    """Np. 'Zmiana kursu w 12 miesięcy: +91,8% (wyżej niż u 95% pozostałych spółek)'."""
    value = explanation["features"][feature]
    if feature == "liquidity_3m":
        value_txt = f"{math.exp(value) / 1e6:.1f} mln zł dziennie".replace(".", ",")
    elif feature == "vol_3m":
        value_txt = f"{value:.0%} w skali roku"
    else:
        value_txt = format_change(value)
    position = describe_position(explanation["percentiles"][feature])
    return f"{FEATURE_LABELS[feature].capitalize()}: {value_txt} ({position})"


def top_factors(explanation: dict, positive: bool = True, n: int = 2) -> list[str]:
    """Najważniejsze czynniki podnoszące (positive=True) lub obniżające ocenę modelu."""
    contrib = explanation["contributions"]
    ordered = sorted(contrib, key=contrib.get, reverse=positive)
    chosen = [f for f in ordered if (contrib[f] > 0) == positive][:n]
    return [describe_factor(f, explanation) for f in chosen]


def recommend(weights: dict[str, float], candidates: dict[str, Candidate],
              profile: str, max_new: int = 5) -> list[Recommendation]:
    """Tworzy propozycje zmian w portfelu.

    weights: udział każdej posiadanej spółki w wartości portfela (0-1)
    candidates: spółki z najnowszą oceną modelu, według tickera
    """
    limits = PROFILES[profile]
    recs: dict[str, Recommendation] = {}
    

    def sector_of(ticker: str) -> str:
        c = candidates.get(ticker)
        return c.sector if c and c.sector else "Inne"

    def vol_percentile(c: Candidate) -> float:
        return c.explanation["percentiles"]["vol_3m"]

    def flag(ticker: str, action: str, reason: str) -> None:
        c = candidates.get(ticker)
        rec = recs.setdefault(ticker, Recommendation(
            ticker=ticker, name=c.name if c else ticker, sector=c.sector if c else None,
            action=action, score=c.score if c else None,
        ))
        if action == "CONSIDER_SELL":  # silniejszy sygnał niż REDUCE
            rec.action = action
        rec.reasons.append(reason)

    sector_weights: dict[str, float] = defaultdict(float)
    for ticker, w in weights.items():
        sector_weights[sector_of(ticker)] += w

    # 1. Zbyt duży udział pojedynczej spółki
    for ticker, w in weights.items():
        if w > limits.max_position_weight:
            flag(ticker, "REDUCE", f"Udział w portfelu {w:.0%} przekracza limit "
                                   f"{limits.max_position_weight:.0%} dla Twojego profilu")

    # 2. Zbyt duży udział sektora - wskazujemy spółkę z najsłabszą oceną modelu w tym sektorze.
    #    Gdy w sektorze jest jedna spółka, wystarcza reguła 1 (limit spółki <= limit sektora).
    for sector, w in sector_weights.items():
        held = [t for t in weights if sector_of(t) == sector]
        if w > limits.max_sector_weight and len(held) > 1:
            weakest = min(held, key=lambda t: candidates[t].score if t in candidates else -1.0)
            flag(weakest, "REDUCE", f"Sektor {sector} stanowi {w:.0%} portfela (limit "
                                    f"{limits.max_sector_weight:.0%}), a ta spółka ma w nim "
                                    f"najsłabszą ocenę modelu")

    # 3. Posiadane spółki niepasujące do profilu lub słabo oceniane przez model
    for ticker in weights:
        c = candidates.get(ticker)
        if c is None:
            continue
        if c.index_name not in limits.allowed_indices:
            flag(ticker, "CONSIDER_SELL", f"Spółka z indeksu {c.index_name} wykracza poza "
                                          f"zakres Twojego profilu ryzyka")
        if vol_percentile(c) > limits.max_volatility_percentile:
            flag(ticker, "CONSIDER_SELL", f"Spółka należy do "
                                          f"{1 - limits.max_volatility_percentile:.0%} "
                                          f"najbardziej zmiennych – zbyt ryzykowna dla Twojego profilu")
        if c.score_percentile <= BOTTOM_PERCENTILE:
            flag(ticker, "CONSIDER_SELL", "Ocena modelu w dolnych 20% spółek")
            for factor in top_factors(c.explanation, positive=False):
                flag(ticker, "CONSIDER_SELL", factor)

    # 4. Propozycje nowych spółek: najlepiej oceniane spośród dostępnych dla profilu
    allowed = sorted(
        (c for c in candidates.values()
         if c.index_name in limits.allowed_indices
         and vol_percentile(c) <= limits.max_volatility_percentile),
        key=lambda c: -c.score,
    )
    top = allowed[:max(1, round(len(allowed) * TOP_SHARE))]
    # Najpierw sektory, których nie ma w portfelu (dywersyfikacja), potem według oceny
    top.sort(key=lambda c: (sector_weights.get(c.sector or "Inne", 0) > 0, -c.score))

    added: dict[str, int] = defaultdict(int)
    for c in top:
        if sum(added.values()) >= max_new:
            break
        sector = c.sector or "Inne"
                # Udział sektora po dokupieniu tej spółki (i wcześniejszych propozycji z tego sektora)
        projected = sector_weights.get(sector, 0) + (added[sector] + 1) * MIN_NEW_POSITION
        if (c.ticker in weights
                or projected > limits.max_sector_weight
                or added[sector] >= MAX_NEW_PER_SECTOR):
            continue
        added[sector] += 1
        reasons = ["Ocena modelu w górnych 20% spółek dostępnych dla Twojego profilu",
                   *top_factors(c.explanation)]
        if weights and sector_weights.get(sector, 0) == 0:
            reasons.append(f"Nowy sektor w portfelu ({sector}) – poprawia dywersyfikację")
        recs[c.ticker] = Recommendation(c.ticker, c.name, c.sector, "ADD", c.score, reasons)

    return sorted(recs.values(), key=lambda r: (ACTION_ORDER[r.action], -(r.score or 0)))
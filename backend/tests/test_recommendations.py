"""Testy jednostkowe warstwy rekomendacji - bez bazy danych i bez HTTP."""
from app.services.recommendations import Candidate, recommend

FEATURES = ["mom_1m", "mom_3m", "mom_6m", "mom_12m", "vol_3m", "dist_high_12m", "liquidity_3m"]


def cand(ticker, score, percentile=0.5, index="WIG20", sector="Banki", vol_pct=0.5):
    """Pomocnik: spółka z oceną modelu i przykładowym wyjaśnieniem."""
    explanation = {
        "features": {f: 0.1 for f in FEATURES} | {"liquidity_3m": 15.0},
        "percentiles": {f: 0.5 for f in FEATURES} | {"vol_3m": vol_pct},
        "contributions": {f: 0.0 for f in FEATURES} | {"mom_12m": 0.1, "mom_1m": -0.05},
    }
    return Candidate(ticker, ticker, index, sector, score, percentile, explanation)


def by_action(recs, action):
    return [r.ticker for r in recs if r.action == action]


def test_position_above_limit_is_reduced():
    candidates = {"PKO": cand("PKO", 0.5), "KGH": cand("KGH", 0.5, sector="Surowce")}
    recs = recommend({"PKO": 0.5, "KGH": 0.5}, candidates, "balanced")  # limit 20%
    assert set(by_action(recs, "REDUCE")) == {"PKO", "KGH"}


def test_sector_above_limit_reduces_weakest_stock_in_sector():
    candidates = {
        "PKO": cand("PKO", 0.55), "PEO": cand("PEO", 0.45), "MBK": cand("MBK", 0.50),
        "KGH": cand("KGH", 0.50, sector="Surowce"), "LPP": cand("LPP", 0.50, sector="Handel"),
    }
    weights = {"PKO": 0.2, "PEO": 0.2, "MBK": 0.2, "KGH": 0.2, "LPP": 0.2}  # banki 60% > 40%
    recs = recommend(weights, candidates, "balanced")
    assert by_action(recs, "REDUCE") == ["PEO"]


def test_low_model_score_suggests_selling():
    candidates = {"PKO": cand("PKO", 0.40, percentile=0.1)}
    recs = recommend({"PKO": 0.15}, candidates, "dynamic")
    assert by_action(recs, "CONSIDER_SELL") == ["PKO"]
    assert "dolnych 20%" in recs[0].reasons[0]


def test_conservative_profile_excludes_mwig40_and_volatile_stocks():
    candidates = {
        "SAFE": cand("SAFE", 0.60),
        "VOLATILE": cand("VOLATILE", 0.65, sector="Handel", vol_pct=0.95),
        "MID": cand("MID", 0.70, index="mWIG40", sector="Usługi"),
        **{f"W{i}": cand(f"W{i}", 0.40 + i / 100, sector=f"Sektor{i}") for i in range(5)},
    }
    recs = recommend({}, candidates, "conservative")
    assert by_action(recs, "ADD") == ["SAFE"]


def test_conservative_holder_of_mwig40_stock_gets_sell_signal():
    candidates = {"MID": cand("MID", 0.60, index="mWIG40")}
    recs = recommend({"MID": 0.10}, candidates, "conservative")
    assert by_action(recs, "CONSIDER_SELL") == ["MID"]


def test_new_proposals_are_limited_per_sector():
    candidates = {
        **{f"BANK{i}": cand(f"BANK{i}", 0.90 - i / 100) for i in range(10)},
        **{f"OTHER{i}": cand(f"OTHER{i}", 0.50 - i / 100, sector=f"Sektor{i}") for i in range(15)},
    }
    adds = by_action(recommend({}, candidates, "dynamic"), "ADD")
    assert len(adds) == 2  # w górnych 20% są same banki, a limit to 2 na sektor
    assert all(t.startswith("BANK") for t in adds)


def test_held_stock_is_not_proposed_again():
    candidates = {f"S{i}": cand(f"S{i}", 0.9 - i / 100, sector=f"Sektor{i}") for i in range(10)}
    adds = by_action(recommend({"S0": 0.1}, candidates, "dynamic"), "ADD")
    assert "S0" not in adds


def test_reasons_list_rule_and_model_factors_separately():
    candidates = {"PKO": cand("PKO", 0.9)}
    rec = recommend({}, candidates, "dynamic")[0]
    assert rec.action == "ADD"
    assert rec.reasons[0].startswith("Ocena modelu w górnych 20%")
    assert any(r.startswith("Zmiana kursu w 12 miesięcy") for r in rec.reasons)


def test_single_stock_sector_gets_only_position_limit_reason():
    candidates = {"PKO": cand("PKO", 0.5)}
    rec = recommend({"PKO": 1.0}, candidates, "balanced")[0]
    assert rec.reasons == ["Udział w portfelu 100% przekracza limit 20% dla Twojego profilu"]


def test_factor_description_uses_polish_format_and_readable_position():
    from app.services.recommendations import describe_factor
    explanation = {
        "features": {"mom_12m": 4.43, "liquidity_3m": 13.8155},  # exp(13.8155) ≈ 1 mln zł
        "percentiles": {"mom_12m": 1.0, "liquidity_3m": 0.08},
    }
    assert describe_factor("mom_12m", explanation) == \
        "Zmiana kursu w 12 miesięcy: +443% (najwyżej spośród ocenianych spółek)"
    assert describe_factor("liquidity_3m", explanation) == \
        "Średni obrót: 1,0 mln zł dziennie (niżej niż u 92% pozostałych spółek)"
    
def test_no_new_proposals_in_sector_close_to_its_limit():
    candidates = {
        "PKO": cand("PKO", 0.50),
        "PEO": cand("PEO", 0.90),                     # najlepiej oceniona, ale to bank
        "LPP": cand("LPP", 0.85, sector="Handel"),
        "KGH": cand("KGH", 0.40, sector="Surowce"),
        **{f"W{i}": cand(f"W{i}", 0.30 + i / 100, sector=f"Sektor{i}") for i in range(6)},
    }
    adds = by_action(recommend({"PKO": 0.28, "KGH": 0.10}, candidates, "conservative"), "ADD")
    assert "PEO" not in adds  # banki 28% + nowa pozycja 5% przekroczyłyby limit 30%
    assert "LPP" in adds
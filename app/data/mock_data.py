"""
Nova Molding Systems FP&A — Mock Data
Provides fallback DataFrames mirroring the gold table schemas so the app
can render in demo/offline mode when USE_MOCK_DATA=true or live SQL fails.
"""
import pandas as pd
import numpy as np

np.random.seed(42)

BUS = ["Injection Molding", "Extrusion", "Hot Runners", "Aftermarket & Service"]
REGIONS = ["Americas", "Europe", "Asia", "India"]
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]

_BU_PROFILES = {
    "Injection Molding":     {"base": 90, "cogs_pct": 0.62, "opex_pct": 0.18, "growth": 0.04,
                              "region": {"Americas": 1.0, "Europe": 0.80, "Asia": 0.55, "India": 0.20}},
    "Extrusion":             {"base": 52, "cogs_pct": 0.58, "opex_pct": 0.22, "growth": 0.03,
                              "region": {"Americas": 1.0, "Europe": 0.90, "Asia": 0.35, "India": 0.15}},
    "Hot Runners":           {"base": 35, "cogs_pct": 0.45, "opex_pct": 0.20, "growth": 0.09,
                              "region": {"Americas": 0.85, "Europe": 1.0, "Asia": 0.60, "India": 0.30}},
    "Aftermarket & Service": {"base": 42, "cogs_pct": 0.38, "opex_pct": 0.25, "growth": 0.12,
                              "region": {"Americas": 1.0, "Europe": 0.65, "Asia": 0.40, "India": 0.35}},
}


def _mock_revenue_summary() -> pd.DataFrame:
    rows = []
    for fy in [2024, 2025, 2026]:
        for q_idx, q in enumerate(QUARTERS):
            for m in range(q_idx * 3 + 1, q_idx * 3 + 4):
                for bu in BUS:
                    p = _BU_PROFILES[bu]
                    yr_trend = (1 + p["growth"]) ** (fy - 2023)
                    for region in REGIONS:
                        rm = p["region"].get(region, 0.3)
                        rev = p["base"] * rm * yr_trend * np.random.uniform(0.88, 1.12) * 1e6
                        yoy = p["growth"] * 100 + np.random.uniform(-3, 5)
                        bv = np.random.uniform(-4, 8) * (1 if bu != "Extrusion" else -0.5)
                        rows.append({
                            "business_unit": bu, "region": region,
                            "fiscal_year": fy, "fiscal_quarter": q,
                            "fiscal_month": m, "scenario_name": "Actual",
                            "revenue_usd": round(rev, 2),
                            "revenue": round(rev, 2),
                            "yoy_growth_pct": round(yoy, 1),
                            "budget_variance_pct": round(bv, 1),
                        })
    return pd.DataFrame(rows)


def _mock_ebitda_bridge() -> pd.DataFrame:
    rows = []
    for fy in [2024, 2025, 2026]:
        for q in QUARTERS:
            for bu in BUS:
                p = _BU_PROFILES[bu]
                yr_trend = (1 + p["growth"]) ** (fy - 2023)
                for region in REGIONS:
                    rm = p["region"].get(region, 0.3)
                    rev = p["base"] * rm * yr_trend * np.random.uniform(0.9, 1.1) * 1e6
                    cogs = rev * p["cogs_pct"] * np.random.uniform(0.95, 1.05)
                    opex = rev * p["opex_pct"] * np.random.uniform(0.92, 1.08)
                    gp = rev - cogs
                    ebitda = gp - opex
                    rows.append({
                        "business_unit": bu, "region": region,
                        "fiscal_year": fy, "fiscal_quarter": q,
                        "scenario_name": "Actual",
                        "revenue": round(rev, 2), "cogs": round(cogs, 2),
                        "opex": round(opex, 2), "gross_profit": round(gp, 2),
                        "ebitda": round(ebitda, 2),
                        "ebitda_margin": round(ebitda / rev, 4) if rev else 0,
                    })
    return pd.DataFrame(rows)


def _mock_cash_flow() -> pd.DataFrame:
    rows = []
    for fy in [2024, 2025]:
        for q in QUARTERS:
            ocf = np.random.uniform(30, 80) * 1e6
            capex = -np.random.uniform(8, 25) * 1e6
            fcf = ocf + capex
            rows.append({
                "entity_name": "Nova Molding Systems Consolidated", "region": "Americas",
                "fiscal_year": fy, "fiscal_quarter": q,
                "operating_cf": round(ocf, 2), "capex": round(capex, 2),
                "financing_cf": round(np.random.uniform(-10, 5) * 1e6, 2),
                "fcf": round(fcf, 2),
                "fcf_conversion_pct": round(fcf / ocf * 100, 1) if ocf else 0,
            })
    return pd.DataFrame(rows)


def _mock_leverage() -> pd.DataFrame:
    rows = []
    debt = 1_400_000_000
    for fy in [2024, 2025]:
        for q in QUARTERS:
            debt *= np.random.uniform(0.97, 1.01)
            ebitda = 350_000_000
            rows.append({
                "entity_id": "E0001", "fiscal_year": fy, "fiscal_quarter": q,
                "net_debt": round(debt, 2), "total_interest": round(debt * 0.055 / 4, 2),
                "ltm_ebitda": ebitda,
                "net_leverage": round(debt / ebitda, 2),
                "interest_coverage": round(ebitda / (debt * 0.055), 1),
            })
    return pd.DataFrame(rows)


def _mock_working_capital() -> pd.DataFrame:
    rows = []
    for fy in [2024, 2025]:
        for q in QUARTERS:
            for m in range(1, 13):
                for bu in BUS:
                    for region in REGIONS:
                        rows.append({
                            "entity_name": f"Nova Molding Systems {bu} {region}",
                            "business_unit": bu, "region": region,
                            "fiscal_year": fy, "fiscal_quarter": q,
                            "fiscal_month": m,
                            "dso": round(np.random.uniform(35, 65), 1),
                            "dpo": round(np.random.uniform(30, 55), 1),
                            "inventory_turns": round(np.random.uniform(3, 8), 2),
                            "cash_conversion_cycle": round(np.random.uniform(25, 60), 1),
                        })
    return pd.DataFrame(rows)


def _mock_aftermarket() -> pd.DataFrame:
    rows = []
    for fy in [2024, 2025]:
        for q in QUARTERS:
            for bu in BUS:
                for region in REGIONS:
                    am_rev = np.random.uniform(5, 25) * 1e6
                    total = am_rev / np.random.uniform(0.15, 0.45)
                    rows.append({
                        "business_unit": bu, "region": region,
                        "fiscal_year": fy, "fiscal_quarter": q,
                        "aftermarket_revenue": round(am_rev, 2),
                        "total_revenue": round(total, 2),
                        "aftermarket_mix_pct": round(am_rev / total * 100, 1),
                        "service_attach_rate": round(np.random.uniform(0.4, 0.75), 3),
                    })
    return pd.DataFrame(rows)


def _mock_order_backlog() -> pd.DataFrame:
    rows = []
    for fy in [2024, 2025]:
        for m in range(1, 13):
            for bu in BUS:
                for region in REGIONS:
                    intake = np.random.uniform(10, 60) * 1e6
                    shipped = intake * np.random.uniform(0.7, 1.1)
                    rows.append({
                        "business_unit": bu, "region": region,
                        "fiscal_year": fy,
                        "fiscal_quarter": f"Q{(m - 1) // 3 + 1}",
                        "fiscal_month": m,
                        "order_intake": round(intake, 2),
                        "backlog_value": round(intake * 0.2, 2),
                        "shipped_revenue": round(shipped, 2),
                        "book_to_bill_ratio": round(intake / shipped, 2) if shipped else 0,
                    })
    return pd.DataFrame(rows)


def _mock_plant_performance() -> pd.DataFrame:
    plants = [
        ("P01", "Batavia Plant"), ("P02", "Mount Orab Plant"),
        ("P04", "Malterdingen Plant"), ("P06", "Ahmedabad Plant"),
        ("P07", "Shanghai Plant"),
    ]
    rows = []
    for fy in [2024, 2025]:
        for q in QUARTERS:
            for pid, pname in plants:
                rows.append({
                    "plant_id": pid, "plant_name": pname,
                    "plant_country": "US",
                    "fiscal_year": fy, "fiscal_quarter": q,
                    "utilization_pct": round(np.random.uniform(0.55, 0.92), 3),
                    "cost_variance_pct": round(np.random.uniform(-8, 12), 1),
                    "scrap_rate": round(np.random.uniform(0.01, 0.06), 3),
                    "total_units": int(np.random.uniform(5000, 50000)),
                })
    return pd.DataFrame(rows)


def _mock_ml_forecast() -> pd.DataFrame:
    rows = []
    for bu in BUS:
        for region in REGIONS:
            for m in ["2026-01", "2026-02", "2026-03"]:
                pred = np.random.uniform(10, 60) * 1e6
                rows.append({
                    "entity_id": f"E-{bu[:3]}-{region[:3]}",
                    "business_unit": bu,
                    "region": region,
                    "product_family": "Mixed",
                    "forecast_month": m,
                    "predicted_revenue": round(pred, 2),
                    "prediction_interval_lower": round(pred * 0.85, 2),
                    "prediction_interval_upper": round(pred * 1.15, 2),
                    "scored_at": "2025-12-31",
                })
    return pd.DataFrame(rows)


MOCK_REGISTRY: dict[str, callable] = {
    "revenue_summary": _mock_revenue_summary,
    "ebitda_bridge": _mock_ebitda_bridge,
    "cash_flow": _mock_cash_flow,
    "leverage": _mock_leverage,
    "working_capital": _mock_working_capital,
    "aftermarket": _mock_aftermarket,
    "order_backlog": _mock_order_backlog,
    "plant_performance": _mock_plant_performance,
    "ml_forecast": _mock_ml_forecast,
}

# UC Metrics Migration Matrix

This document tracks the non-breaking rollout from `gold_*` tables to UC Metric Views (`mv_*`) across Genie and AI/BI dashboard assets.

## Dashboard dataset/source mapping

| Area | Current source | V2 source | Parity status | Cutover readiness |
|---|---|---|---|---|
| Revenue trend and scenario KPIs | `gold_revenue_summary` | `mv_revenue` | Static query source migration complete | Ready for side-by-side KPI check |
| EBITDA and margin visuals | `gold_ebitda_bridge` | `mv_ebitda` | Static query source migration complete | Ready for side-by-side KPI check |
| Working capital KPIs | `gold_working_capital` | `mv_working_capital` | Static query source migration complete | Ready for side-by-side KPI check |
| Aftermarket mix visuals | `gold_aftermarket_mix` | `mv_aftermarket` | Static query source migration complete | Ready for side-by-side KPI check |
| Order backlog / book-to-bill | `gold_order_backlog` | `mv_order_backlog` | Static query source migration complete | Ready for side-by-side KPI check |
| Leverage | `gold_leverage_metrics` | unchanged in v2 | Not migrated by design (join/semantic sensitivity) | Defer to phase 2 |
| Cash flow | `gold_cash_flow_summary` | unchanged in v2 | Not migrated by design (join/semantic sensitivity) | Defer to phase 2 |
| ML forecast comparison | `ml_revenue_forecast` + `gold_revenue_summary` + dims | partially migrated where revenue source changed | Requires runtime KPI validation | Phase 1 validation gate |

## Genie context/source mapping

| Area | Status |
|---|---|
| Existing `gold_*`/`silver_*` context retained | Yes (no regression path) |
| UC Metric Views added to context | Yes (`mv_revenue`, `mv_ebitda`, `mv_free_cash_flow`, `mv_leverage`, `mv_working_capital`, `mv_aftermarket`, `mv_order_backlog`, `mv_forecast_accuracy`) |
| Existing-space idempotent detection | Yes (normalized title matching + pagination + optional explicit `genie_space_id`) |
| Duplicate curated artifacts prevention | Yes (read-before-create checks for sample questions and instructions) |

## Validation results (implementation phase)

- V2 dashboard artifact exists at `resources/dashboards/nova_molding_fpa_metrics_v2.lvdash.json`.
- The five planned `gold_*` sources are absent from v2.
- `mv_*` sources are present in v2.
- Non-migrated sensitive sources (`gold_leverage_metrics`, `gold_cash_flow_summary`, `ml_revenue_forecast`, `silver_dim_entity`) remain present.
- DAB now includes both dashboards in parallel (`nova_molding_fpa` and `nova_molding_fpa_metrics_v2`).

## Cutover recommendation

- Keep current dashboard as production/default until KPI parity is confirmed in workspace for the same filter/time windows.
- Use v2 dashboard for validation with finance stakeholders first.
- Promote v2 to primary only after:
  - KPI parity sign-off for migrated visuals,
  - no Genie duplication across repeated runs,
  - no permission regressions on `mv_*` objects.

## Residual exceptions

- Leverage/cash-flow and selected join-heavy views remain on current sources in v2 to avoid breaking behavior.
- Runtime parity still requires in-workspace execution checks (outside static repo verification).

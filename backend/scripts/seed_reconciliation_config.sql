-- Optional: seed system_config keys for reconciliation rules (AUDIT-48, RRBS-3, COVENANT-6, BENCHMARK).
-- Code uses defaults when keys are missing; run this to persist or tune values.

INSERT INTO system_config (config_key, config_value, description)
VALUES
  ('audit48_assets_change_pct', '5.0', 'AUDIT-48: trigger variance investigation when total assets change exceeds this %'),
  ('audit48_revenue_decrease_pct', '10.0', 'AUDIT-48: trigger when revenue decrease exceeds this %'),
  ('audit48_cash_decrease_pct', '30.0', 'AUDIT-48: trigger when cash decrease exceeds this %'),
  ('forensic_prepaid_rent_material_threshold', '20000', 'RRBS-3: flag prepaid rent / rent-in-advance changes above this $ amount'),
  ('covenant_reporting_deadline_days', '30', 'COVENANT-6: days after period end by which documents must be uploaded'),
  ('benchmark_market_rent_per_sf', '0', 'BENCHMARK-1: target rent per SF (0 = no comparison)'),
  ('benchmark_market_opex_per_sf', '0', 'BENCHMARK-2: target OpEx per SF (0 = no comparison)'),
  ('benchmark_market_occupancy_pct', '0', 'BENCHMARK-3: target occupancy % e.g. 90 (0 = no comparison)'),
  ('benchmark_market_cap_rate_pct', '0', 'BENCHMARK-4: target cap rate % e.g. 5 (0 = no comparison)'),
  ('rrbs_1_tolerance_usd', '1.0', 'RRBS-1: max allowed shortfall $ (BS deposits may be up to this much below RR deposits)'),
  ('fa_cash_4_min_balance_to_flag', '0', 'FA-CASH-4: only flag appear/disappear when balance >= this $ (0 = flag all)'),
  ('fa_mort_4_materiality_threshold', '10000', 'FA-MORT-4: material escrow disbursement $ above which documentation link required (default 10000)'),
  ('audit49_earnings_tolerance_pct', '1.0', 'AUDIT-49: year-end validation tolerance % for BS=IS YTD and retained earnings roll (default 1.0)'),
  ('audit50_income_decrease_pct', '10.0', 'AUDIT-50: YoY total income decrease % threshold to trigger WARNING (default 10)'),
  ('audit50_noi_decrease_pct', '10.0', 'AUDIT-50: YoY NOI decrease % threshold to trigger WARNING (default 10)'),
  ('audit50_net_income_decrease_pct', '10.0', 'AUDIT-50: YoY net income decrease % threshold to trigger WARNING (default 10)'),
  ('audit50_occupancy_decrease_pp', '5.0', 'AUDIT-50: YoY occupancy decrease (percentage points) threshold to trigger WARNING (default 5)')
ON CONFLICT (config_key) DO UPDATE SET
  config_value = EXCLUDED.config_value,
  description = EXCLUDED.description;

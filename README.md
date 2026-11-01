# Sports Fan and Ticketing BI

**Synthetic portfolio demonstration. Fictional brands. No affiliation with Pacers Sports & Entertainment or any team; no real commercial results.**

Built a synthetic two-brand ticketing warehouse for 20,000 fans, 120 events and 119,998 accepted orders. Included no-history fans in frozen as-of RFM segments, reconciled integer-cent financial metrics independently, and validated segments using later 90-day purchasing.

## Recorded results

- 120,016 input rows: 5 exact duplicates removed, 13 rows quarantined (including both sides of 2 conflicting keys), 119,998 accepted orders.
- 20,000 fans retained, including 6,611 with no prior positive purchase at the fixed cutoff.
- Five operational audience segments; Champions had 89.6% next-90-day purchasing versus 15.8% for New/unconverted in this simulation. These descriptive rates are not treatment effects.
- Revenue, refund, ticket and attendance totals reconcile exactly between SQL and pandas.
- Local DuckDB materialization benchmark: exact result equivalence, 21 interleaved repetitions, construction and amortization separately reported. See recorded measurements rather than assuming a fixed speedup on another host.

## Reproduce

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
bash run_all.sh
```

No account, API key, private dataset or paid database is required. The generator, seed, protocol and metric logic are versioned. Participant-level synthetic records and activation exports stay in ignored data directories. Timing measurements vary by hardware.

## Review the work

- Download/open [self-contained report](reports/index.html) in a browser. Brand/month filters and CSV exports use aggregate data only.
- Open [packaged Tableau workbook](tableau/fan_ticketing.twbx) in Tableau Desktop; aggregate CSV data are embedded.
- [Summary evidence](evidence/summary.json), [numerical checks](evidence/checks.json), [analysis plan](docs/analysis_plan.md), [metric dictionary](docs/metric_dictionary.md), [limitations](docs/limitations.md), [resume wording](docs/resume_bullets.md).
- [中文说明](docs/README_CN.md).

## Decision use

Use ticketing KPIs for financial reconciliation and audience rules for opt-in activation design. Choose which report queries warrant materialization using measured break-even reuse and the required freshness SLA. Review cohort outcomes without interpreting segment differences as campaign effects.

## Limitations

This is generated data with deliberately simulated loyalty patterns and named defect injections. Neither the dollar totals nor segment differences describe a real team. Static segmentation rules were fixed before reading follow-up outcomes. There is no causal marketing uplift, real CRM activation, cloud benchmark or external predictive validation. Refund attribution and single-event-order grain simplify a real ticketing accounting model. Local materialization reduces repeated aggregation work but requires refreshes and additional storage.

Existing work: [RFM customer segmentation](https://github.com/xkong585/data_science_project/tree/main/RFM_model). This project reimplements fixed-time business segmentation on newly generated ticketing data; it does not relabel retail data as real sports customer data.

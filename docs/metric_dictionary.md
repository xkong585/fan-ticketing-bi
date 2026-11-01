# Metric dictionary

| Metric | Grain and definition |
|---|---|
| Net revenue | Sum gross paid minus refund cents; original purchase month attribution |
| Net tickets | Purchased quantity minus refunded quantity |
| Scan rate | Sum attended tickets / sum net tickets, not average of subgroup rates |
| Average order value | Net revenue / accepted order count; includes fully refunded orders |
| RFM frequency | Distinct positive-net-ticket orders before 2026-01-01 |
| Recency | Days since last positive purchase at fixed cutoff; no-history is missing, not zero |
| Segment validation | Fan purchased positive net tickets during Jan-Mar 2026; one row per fan |
| Brand segments | Fan/brand grain; the same person may appear in two brand universes |
| Cohort retention | First observed positive purchase cohort; active fans at month k / original cohort size; future unobserved months omitted |

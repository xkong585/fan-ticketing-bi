# Architecture

Frozen protocol -> seeded raw simulation -> typed/key/scale/date checks -> duplicate adjudication and quarantine -> analytical marts -> independent pandas/SQL reconciliation -> statistical/segment analysis -> tests -> Tableau package and HTML report -> readiness marker.

Source data, grains, money units, time boundaries and selection assumptions are explicit. run_all.sh invalidates old publishable reports before running. Only a successful tested run writes reports/READY.json. Individual records are ignored. No database credential or real customer data are needed.

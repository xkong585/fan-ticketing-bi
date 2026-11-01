# Architecture and publication gates

Source URLs and bytes are locked in `source_lock.json`. Raw files and participant-level derived records stay ignored. The pipeline checks keys, scope, source units and numerical reconciliations, then runs substantive tests. Figures, Tableau aggregates and a buildless static site are published only after success. A failed run deletes public readiness and HTML entrypoints. GitHub Actions starts from no raw cache, retrieves official files, repeats analysis/tests and deploys the same aggregate-only site to GitHub Pages.

Read `analysis_plan.md` for sampling and model boundaries. No runtime database, external model API, user account or customer data is required for the dashboard.

# Metric dictionary

- **Team record:** school / sex / season-end / cohort. A university may appear in both sex categories.
- **Ordinary DI home attendance:** sum of factual school-list attendance after separating reclassifying rows. Counts attendances, not unique people or paid purchases.
- **Home games:** sum of recorded home games for the same selected school rows.
- **Computed average:** attendance / home games. Use ratio of totals for an aggregate selection, not an average of school averages.
- **Reported average:** the NCAA's printed rounded/truncated value, retained separately.
- **Historical DI all-games attendance:** as printed on the historical table, includes home / neutral / tournament; never substitute for home attendance. 2021 is missing, not zero.
- **Forecast MAE:** mean absolute difference between forecast and printed men's DI all-games average over four annual origins, 2023–26. Training years precede each origin.
- **SQL timing:** 21 warm interleaved local runs, actual source rows, same results; report mart construction separately and no fixed performance guarantee.

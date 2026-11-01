-- Source grain: school / sex / cohort / season. Ordinary DI and reclassifying rows never mix.
CREATE OR REPLACE TABLE mart_home AS
SELECT sex, COUNT(*)::BIGINT teams, SUM(home_games)::BIGINT games,
       SUM(attendance)::BIGINT attendance
FROM school_attendance WHERE cohort='Division I' GROUP BY sex;

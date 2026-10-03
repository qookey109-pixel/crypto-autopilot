-- Shared Cloudflare writer budget gate V0.4.
-- Prepared only: this migration creates a separate policy row and does not
-- provision D1 or authorize any Cloudflare request.
CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_budget_policy_v0_4 (
    policy_id INTEGER PRIMARY KEY CHECK (policy_id = 1),
    max_reservations_per_utc_day INTEGER
        CHECK (max_reservations_per_utc_day IS NULL OR max_reservations_per_utc_day > 0),
    provider_requests_per_utc_day INTEGER
        CHECK (provider_requests_per_utc_day IS NULL OR provider_requests_per_utc_day > 0),
    r2_class_a_per_utc_day INTEGER
        CHECK (r2_class_a_per_utc_day IS NULL OR r2_class_a_per_utc_day > 0),
    r2_class_b_per_utc_day INTEGER
        CHECK (r2_class_b_per_utc_day IS NULL OR r2_class_b_per_utc_day > 0),
    r2_new_bytes_per_utc_day INTEGER
        CHECK (r2_new_bytes_per_utc_day IS NULL OR r2_new_bytes_per_utc_day > 0),
    d1_queries_per_utc_day INTEGER
        CHECK (d1_queries_per_utc_day IS NULL OR d1_queries_per_utc_day > 0),
    d1_rows_read_per_utc_day INTEGER
        CHECK (d1_rows_read_per_utc_day IS NULL OR d1_rows_read_per_utc_day > 0),
    d1_rows_written_per_utc_day INTEGER
        CHECK (d1_rows_written_per_utc_day IS NULL OR d1_rows_written_per_utc_day > 0),
    d1_storage_growth_bytes_per_utc_day INTEGER
        CHECK (d1_storage_growth_bytes_per_utc_day IS NULL OR d1_storage_growth_bytes_per_utc_day > 0),
    r2_class_a_per_rolling_31_days INTEGER
        CHECK (r2_class_a_per_rolling_31_days IS NULL OR r2_class_a_per_rolling_31_days > 0),
    r2_class_b_per_rolling_31_days INTEGER
        CHECK (r2_class_b_per_rolling_31_days IS NULL OR r2_class_b_per_rolling_31_days > 0),
    r2_new_bytes_per_rolling_31_days INTEGER
        CHECK (r2_new_bytes_per_rolling_31_days IS NULL OR r2_new_bytes_per_rolling_31_days > 0)
);
INSERT INTO cloudflare_shared_writer_budget_policy_v0_4 (policy_id)
VALUES (1)
ON CONFLICT(policy_id) DO NOTHING;

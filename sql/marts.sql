-- Atomic grain: one synthetic order for one event/ticket type. Money in cents.
CREATE TABLE mart_monthly AS
SELECT strftime(purchase_at,'%Y-%m') AS month, e.brand, o.ticket_type,
 COUNT(*)::BIGINT AS orders, SUM(gross_cents)::BIGINT AS gross_revenue_cents,
 SUM(refund_cents)::BIGINT AS refund_cents, SUM(net_cents)::BIGINT AS net_revenue_cents,
 SUM(net_tickets)::BIGINT AS net_tickets, SUM(attended_tickets)::BIGINT AS attended_tickets
FROM fact_order o JOIN dim_event e USING(event_id)
GROUP BY 1,2,3;

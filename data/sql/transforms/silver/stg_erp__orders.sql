-- Explicit columns, never a wildcard select -- a new upstream column must be a
-- reviewable decision, not a silent schema change. `qualify` dedupes on
-- the business key, keeping the most recent row.
select
    order_id,
    customer_id,
    cast(amount     as double)   as amount,
    cast(ordered_at as date)     as event_date,
    'confidential'                as classification
from delta_scan('{bronze}/orders/orders')
qualify row_number() over (partition by order_id order by ordered_at desc) = 1

select
    customer_id,
    name,
    country
from delta_scan('{bronze}/customers/customers')
qualify row_number() over (partition by customer_id order by customer_id) = 1

select
    c.customer_id,
    c.name,
    c.country,
    count(o.order_id)         as order_count,
    coalesce(sum(o.amount), 0) as lifetime_amount
from delta_scan('{silver}/customers') c
left join delta_scan('{silver}/orders') o using (customer_id)
group by c.customer_id, c.name, c.country

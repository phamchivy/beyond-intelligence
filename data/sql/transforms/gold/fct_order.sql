select o.order_id, o.customer_id, o.amount, o.event_date, c.country
from delta_scan('{silver}/orders')    o
left join delta_scan('{silver}/customers') c using (customer_id)

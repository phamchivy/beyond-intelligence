select sku, product_name, price, category
from delta_scan('{silver}/catalog')

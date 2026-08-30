select
    sku,
    product_name,
    cast(price as double) as price,
    category
from delta_scan('{bronze}/catalog/catalog')
qualify row_number() over (partition by sku order by sku) = 1

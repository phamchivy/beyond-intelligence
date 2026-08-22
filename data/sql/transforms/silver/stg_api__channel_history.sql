select
    event_id,
    channel,
    metric,
    cast(value as double)     as value,
    cast(updated_at as date)  as updated_at
from delta_scan('{bronze}/channel_history/channel_history')
qualify row_number() over (partition by event_id order by updated_at desc) = 1

select event_id, channel, metric, value, updated_at
from delta_scan('{silver}/channel_history')

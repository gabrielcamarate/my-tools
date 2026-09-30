"""Synthetic duplicate-event protection."""
def accept_event(event_id, processed_ids):
    if event_id in processed_ids:
        return False
    processed_ids.add(event_id)
    return True

"""Synthetic cancellation state."""
def cancel_subscription(subscription):
    return {**subscription, "renewal_enabled": False}

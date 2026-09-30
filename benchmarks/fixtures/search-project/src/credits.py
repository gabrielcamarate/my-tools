"""Synthetic credit handling, no network or external data."""
def refund_failed_job(balance, reserved, job_completed):
    return balance if job_completed else balance + reserved

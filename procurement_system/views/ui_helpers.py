from intake_management import RequestStatus

STATUS_STYLES = {
    RequestStatus.OPEN: ("#9E9E9E", "#FFF"),
    RequestStatus.IN_PROGRESS: ("#FFC107", "#000"),
    RequestStatus.CLOSED: ("#2196F3", "#FFF"),
}


def status_badge(status: RequestStatus) -> str:
    bg, fg = STATUS_STYLES.get(status, ("#9E9E9E", "#FFF"))
    return (
        f'<span style="background:{bg};color:{fg};padding:6px 18px;'
        f"border-radius:6px;font-weight:600;font-size:0.85rem;"
        f'display:inline-block;min-width:100px;text-align:center;">'
        f"{status.value}</span>"
    )


def status_marker(status: RequestStatus) -> str:
    """Hidden marker div used by CSS :has() to color the parent card."""
    key = status.value.lower().replace(" ", "-")
    return f'<div class="status-marker-{key}" style="display:none;"></div>'

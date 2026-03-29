import streamlit as st

from services import ProcurementApp
from intake_management import RequestStatus


def _get_status_color(status: RequestStatus) -> str:
    """Get color for status badge."""
    colors = {
        RequestStatus.OPEN: "🟡",
        RequestStatus.IN_PROGRESS: "🔵",
        RequestStatus.CLOSED: "🟢",
    }
    return colors.get(status, "⚪")


def render(app: ProcurementApp):
    """Render the my requests page showing user's submitted requests."""
    st.header("My Requests")

    user_name = st.session_state.user_name

    # Load user's requests
    requests = app.get_user_requests(user_name)

    if not requests:
        st.info("You haven't submitted any requests yet. Use the sidebar menu to submit a new request.")
        return

    st.write(f"Found **{len(requests)}** request(s)")

    # Display each request
    for request_id, request in requests:
        commodity_name = app.get_commodity_group_name(request.commodity_group)
        status_icon = _get_status_color(request.status)

        with st.expander(f"{status_icon} Request #{request_id}: {request.title} [{request.status.value}]", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Request Details**")
                st.text(f"Status: {request.status.value}")
                st.text(f"Requestor: {request.requestor_name}")
                st.text(f"Department: {request.requestor_department}")
                st.text(f"Vendor: {request.vendor_name}")
                st.text(f"VAT ID: {request.vat_id}")

            with col2:
                st.markdown("**Classification**")
                st.text(f"Commodity Group: {request.commodity_group:03d}")
                st.text(f"Group Name: {commodity_name}")
                st.text(f"Total Cost: {request.total_cost:.2f}")

            st.markdown("**Order Lines**")
            for i, line in enumerate(request.order_lines, 1):
                st.markdown(f"**{i}. {line.position_description}**")
                cols = st.columns(4)
                cols[0].text(f"Unit: {line.unit}")
                cols[1].text(f"Price: {line.unit_price:.2f}")
                cols[2].text(f"Amount: {line.amount:.2f}")
                cols[3].text(f"Total: {line.total_price:.2f}")

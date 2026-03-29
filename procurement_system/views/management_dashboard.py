import streamlit as st

from services import ProcurementApp
from intake_management import RequestStatus


def _get_status_color(status: RequestStatus) -> str:
    """Get color indicator for status."""
    colors = {
        RequestStatus.OPEN: "🟡",
        RequestStatus.IN_PROGRESS: "🔵",
        RequestStatus.CLOSED: "🟢",
    }
    return colors.get(status, "⚪")


def render(app: ProcurementApp):
    """Render the management dashboard for viewing and managing requests."""
    st.header("Request Submissions")

    # Load all requests
    requests = app.get_all_requests()

    if not requests:
        st.info("No requests have been submitted yet.")
        return

    st.write(f"**Total Requests:** {len(requests)}")

    # Create two columns: list and details
    col_list, col_details = st.columns([1, 2])

    with col_list:
        st.subheader("Requests")

        # Initialize selected request in session state
        if "selected_request_id" not in st.session_state:
            st.session_state.selected_request_id = None

        # Display request list as buttons
        for request_id, request in requests:
            status_icon = _get_status_color(request.status)
            button_label = f"{status_icon} #{request_id}: {request.title[:30]}..."

            if st.button(button_label, key=f"req_{request_id}", use_container_width=True):
                st.session_state.selected_request_id = request_id
                st.rerun()

    with col_details:
        st.subheader("Request Details")

        if st.session_state.selected_request_id is None:
            st.info("Select a request from the list to view details.")
            return

        # Find the selected request
        selected_request = None
        for request_id, request in requests:
            if request_id == st.session_state.selected_request_id:
                selected_request = (request_id, request)
                break

        if selected_request is None:
            st.error("Selected request not found.")
            st.session_state.selected_request_id = None
            return

        request_id, request = selected_request
        commodity_name = app.get_commodity_group_name(request.commodity_group)

        # Display request info
        st.markdown(f"### Request #{request_id}: {request.title}")

        # Status change section
        st.markdown("---")
        col1, col2 = st.columns([2, 1])

        with col1:
            current_status_index = list(RequestStatus).index(request.status)
            new_status = st.selectbox(
                "Status",
                options=list(RequestStatus),
                index=current_status_index,
                format_func=lambda x: f"{_get_status_color(x)} {x.value}",
                key=f"status_{request_id}",
            )

        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if new_status != request.status:
                if st.button("Update Status", type="primary"):
                    if app.update_request_status(request_id, new_status):
                        st.success(f"Status updated to {new_status.value}")
                        st.rerun()
                    else:
                        st.error("Failed to update status")

        st.markdown("---")

        # Request details
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Requestor Information**")
            st.text(f"Name: {request.requestor_name}")
            st.text(f"Department: {request.requestor_department}")

        with col2:
            st.markdown("**Vendor Information**")
            st.text(f"Vendor: {request.vendor_name}")
            st.text(f"VAT ID: {request.vat_id}")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Classification**")
            st.text(f"Commodity Group: {request.commodity_group:03d}")
            st.text(f"Group Name: {commodity_name}")

        with col2:
            st.markdown("**Financials**")
            st.text(f"Total Cost: {request.total_cost:.2f}")

        st.markdown("---")

        # Order lines
        st.markdown("**Order Lines**")
        for i, line in enumerate(request.order_lines, 1):
            with st.expander(f"Line {i}: {line.position_description[:50]}..."):
                cols = st.columns(4)
                cols[0].text(f"Unit: {line.unit}")
                cols[1].text(f"Price: {line.unit_price:.2f}")
                cols[2].text(f"Amount: {line.amount:.2f}")
                cols[3].text(f"Total: {line.total_price:.2f}")

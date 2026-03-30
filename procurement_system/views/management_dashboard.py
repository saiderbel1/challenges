import streamlit as st

from services import ProcurementApp
from intake_management import RequestStatus
from views.ui_helpers import status_badge, status_marker


def render(app: ProcurementApp):
    """Render the management dashboard for viewing and managing requests."""
    st.header("Request Submissions")

    requests = app.get_all_requests()

    if not requests:
        st.info("No requests have been submitted yet.")
        return

    all_departments = sorted({r.requestor_department for _, r in requests})
    all_vendors = sorted({r.vendor_name for _, r in requests})
    all_requestors = sorted({r.requestor_name for _, r in requests})

    with st.expander("Filters", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox(
                "Status",
                options=["All"] + [s.value for s in RequestStatus],
                index=0,
            )
            filter_dept = st.selectbox(
                "Department",
                options=["All"] + all_departments,
                index=0,
            )
        with col2:
            filter_vendor = st.selectbox(
                "Vendor",
                options=["All"] + all_vendors,
                index=0,
            )
            filter_requestor = st.selectbox(
                "Requestor",
                options=["All"] + all_requestors,
                index=0,
            )

    filtered = [
        (rid, req) for rid, req in requests
        if (filter_status == "All" or req.status.value == filter_status)
        and (filter_dept == "All" or req.requestor_department == filter_dept)
        and (filter_vendor == "All" or req.vendor_name == filter_vendor)
        and (filter_requestor == "All" or req.requestor_name == filter_requestor)
    ]

    st.write(f"**Showing {len(filtered)}** of **{len(requests)}** request(s)")

    for request_id, request in filtered:
        commodity_name = app.get_commodity_group_name(request.commodity_group)

        with st.container(border=True):
            header_col, badge_col = st.columns([4, 1])
            with header_col:
                st.markdown(
                    f"<span style='font-size:1.1rem;font-weight:700;'>"
                    f"{request_id}</span>"
                    f"<span style='color:#888;margin-left:8px;font-size:0.95rem;'>"
                    f"{request.title}</span>",
                    unsafe_allow_html=True,
                )
            with badge_col:
                st.markdown(
                    f"<div style='text-align:right;'>{status_badge(request.status)}</div>",
                    unsafe_allow_html=True,
                )

            with st.expander("View details", expanded=False):
                col1, col2, col3 = st.columns(3)

                with col1:
                    current_status_index = list(RequestStatus).index(request.status)
                    new_status = st.selectbox(
                        "Status",
                        options=list(RequestStatus),
                        index=current_status_index,
                        format_func=lambda x: x.value,
                        key=f"status_{request_id}",
                    )
                    if new_status != request.status:
                        if st.button("Update Status", type="primary", key=f"update_{request_id}"):
                            if app.update_request_status(request_id, new_status):
                                st.success(f"Status updated to {new_status.value}")
                                st.rerun()
                            else:
                                st.error("Failed to update status")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Requestor**")
                    st.code(request.requestor_name, language=None)
                    st.markdown("**Department**")
                    st.code(request.requestor_department, language=None)

                with col2:
                    st.markdown("**Vendor**")
                    st.code(request.vendor_name, language=None)
                    st.markdown("**VAT ID**")
                    st.code(request.vat_id, language=None)

                with col3:
                    st.markdown("**Commodity Group**")
                    st.code(f"{request.commodity_group:03d} - {commodity_name}", language=None)
                    st.markdown("**Total Cost**")
                    st.code(f"{request.total_cost:.2f}", language=None)

                st.markdown("**Order Lines**")

                for i, line in enumerate(request.order_lines, 1):
                    with st.container(border=True):
                        st.markdown(f"**{i}. {line.position_description}**")
                        cols = st.columns(4)
                        with cols[0]:
                            st.caption("Unit")
                            st.code(line.unit, language=None)
                        with cols[1]:
                            st.caption("Unit Price")
                            st.code(f"{line.unit_price:.2f}", language=None)
                        with cols[2]:
                            st.caption("Amount")
                            st.code(f"{line.amount:.2f}", language=None)
                        with cols[3]:
                            st.caption("Total")
                            st.code(f"{line.total_price:.2f}", language=None)

import streamlit as st

from services import ProcurementApp
from views.ui_helpers import status_badge


def render(app: ProcurementApp):
    """Render the my requests page showing user's submitted requests."""
    st.header("My Requests")

    user_name = st.session_state.user_name

    requests = app.get_user_requests(user_name)

    if not requests:
        st.info("You haven't submitted any requests yet. Use the sidebar menu to submit a new request.")
        return

    st.write(f"Found **{len(requests)}** request(s)")

    for request_id, request in requests:
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

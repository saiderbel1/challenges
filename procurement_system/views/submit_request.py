import streamlit as st

from services import ProcurementApp
from intake_management import OrderLine, ProcurementRequest


def render(app: ProcurementApp):
    """Render the submit request page with upload, review, and submit steps."""
    st.header("Submit New Request")

    # Initialize session state for this page
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = None
    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None
    if "edited_order_lines" not in st.session_state:
        st.session_state.edited_order_lines = None
    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Step 1: Upload PDF
    st.subheader("Step 1: Upload PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        key=f"pdf_uploader_{st.session_state.file_uploader_key}",
    )

    if uploaded_file is not None:
        # Check if this is a new file
        if st.session_state.get("uploaded_file_name") != uploaded_file.name:
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.extracted_data = None
            st.session_state.pdf_bytes = None
            st.session_state.edited_order_lines = None

        # Store PDF bytes
        if st.session_state.pdf_bytes is None:
            st.session_state.pdf_bytes = uploaded_file.read()

        # Auto-extract data with AI (includes validation and OCR fallback)
        if st.session_state.extracted_data is None:
            with st.spinner("Analyzing document with AI (will use OCR if needed)..."):
                try:
                    st.session_state.extracted_data = app.extract_from_pdf_bytes(
                        st.session_state.pdf_bytes
                    )
                    # Initialize editable order lines from extracted data
                    st.session_state.edited_order_lines = [
                        {
                            "position_description": line.position_description,
                            "unit": line.unit,
                            "unit_price": line.unit_price,
                            "amount": line.amount,
                            "total_price": line.total_price,
                        }
                        for line in st.session_state.extracted_data.order_lines
                    ]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during AI analysis: {e}")
                    return

    # Step 2: Review extracted data
    if st.session_state.extracted_data is not None:
        st.subheader("Step 2: Review Extracted Data")

        extracted = st.session_state.extracted_data

        # Get commodity groups for dropdown
        commodity_groups = app.get_commodity_groups()
        commodity_options = {f"{g[0]:03d} - {g[1]}": g[0] for g in commodity_groups}
        commodity_labels = list(commodity_options.keys())

        # Find current selection
        current_commodity_label = None
        for label, group_id in commodity_options.items():
            if group_id == extracted.commodity_group:
                current_commodity_label = label
                break
        current_index = commodity_labels.index(current_commodity_label) if current_commodity_label else 0

        # Display and allow editing of extracted fields
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("Title/Description", value=extracted.title, key="edit_title")
            vendor_name = st.text_input("Vendor Name", value=extracted.vendor_name, key="edit_vendor")
            vat_id = st.text_input("VAT ID", value=extracted.vat_id, key="edit_vat")

        with col2:
            selected_commodity = st.selectbox(
                "Commodity Group",
                options=commodity_labels,
                index=current_index,
                key="edit_commodity",
            )
            commodity_group = commodity_options[selected_commodity]

            total_cost = st.number_input(
                "Total Cost",
                value=extracted.total_cost,
                min_value=0.0,
                format="%.2f",
                key="edit_total",
            )

        # Display editable order lines
        st.subheader("Order Lines")

        edited_lines = st.session_state.edited_order_lines

        for i, line in enumerate(edited_lines):
            with st.expander(f"Line {i + 1}: {line['position_description'][:50]}...", expanded=False):
                line["position_description"] = st.text_area(
                    "Description",
                    value=line["position_description"],
                    key=f"line_{i}_desc",
                )

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    line["unit"] = st.text_input(
                        "Unit",
                        value=line["unit"],
                        key=f"line_{i}_unit",
                    )

                with col2:
                    line["unit_price"] = st.number_input(
                        "Unit Price",
                        value=line["unit_price"],
                        min_value=0.0,
                        format="%.2f",
                        key=f"line_{i}_price",
                    )

                with col3:
                    line["amount"] = st.number_input(
                        "Amount",
                        value=line["amount"],
                        min_value=0.0,
                        format="%.2f",
                        key=f"line_{i}_amount",
                    )

                with col4:
                    # Auto-calculate total
                    calculated_total = line["unit_price"] * line["amount"]
                    line["total_price"] = st.number_input(
                        "Total",
                        value=calculated_total,
                        min_value=0.0,
                        format="%.2f",
                        key=f"line_{i}_total",
                    )

        # Step 3: Submit
        st.subheader("Step 3: Submit Request")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Submit Request", type="primary", use_container_width=True):
                with st.spinner("Saving request..."):
                    try:
                        # Build order lines from edited values
                        order_lines = [
                            OrderLine(
                                position_description=line["position_description"],
                                unit=line["unit"],
                                unit_price=line["unit_price"],
                                amount=line["amount"],
                                total_price=line["total_price"],
                            )
                            for line in st.session_state.edited_order_lines
                        ]

                        # Create request with edited values
                        request = ProcurementRequest(
                            requestor_name=st.session_state.user_name,
                            requestor_department=st.session_state.user_department,
                            title=title,
                            vendor_name=vendor_name,
                            vat_id=vat_id,
                            commodity_group=commodity_group,
                            order_lines=order_lines,
                            total_cost=total_cost,
                        )

                        request_id = app.save_request(request)

                        st.success(f"Request submitted successfully! (ID: {request_id})")

                        # Clear session state for this page
                        st.session_state.extracted_data = None
                        st.session_state.pdf_bytes = None
                        st.session_state.uploaded_file_name = None
                        st.session_state.edited_order_lines = None
                        st.session_state.file_uploader_key += 1

                    except Exception as e:
                        st.error(f"Error saving request: {e}")

        with col2:
            if st.button("Start Over", use_container_width=True):
                st.session_state.extracted_data = None
                st.session_state.pdf_bytes = None
                st.session_state.uploaded_file_name = None
                st.session_state.edited_order_lines = None
                st.session_state.file_uploader_key += 1
                st.rerun()

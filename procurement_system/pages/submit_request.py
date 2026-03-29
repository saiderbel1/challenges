import streamlit as st

from services import ProcurementApp
from intake_management import ProcurementRequest


def render(app: ProcurementApp):
    """Render the submit request page with upload, review, and submit steps."""
    st.header("Submit New Request")

    # Initialize session state for this page
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = None
    if "pdf_text" not in st.session_state:
        st.session_state.pdf_text = None

    # Step 1: Upload PDF
    st.subheader("Step 1: Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    if uploaded_file is not None:
        # Check if this is a new file
        if st.session_state.get("uploaded_file_name") != uploaded_file.name:
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.extracted_data = None
            st.session_state.pdf_text = None

        if st.session_state.pdf_text is None:
            with st.spinner("Extracting text from PDF..."):
                try:
                    pdf_bytes = uploaded_file.read()
                    st.session_state.pdf_text = app.extract_text_from_pdf_bytes(pdf_bytes)
                    st.success("PDF text extracted successfully!")
                except Exception as e:
                    st.error(f"Error extracting PDF text: {e}")
                    return

        # Extract button
        if st.session_state.extracted_data is None:
            if st.button("Extract Data with AI", type="primary"):
                with st.spinner("Analyzing document with AI..."):
                    try:
                        st.session_state.extracted_data = app.extract_procurement_data(
                            st.session_state.pdf_text
                        )
                        st.success("Data extracted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during AI analysis: {e}")
                        return

    # Step 2: Review extracted data
    if st.session_state.extracted_data is not None:
        st.subheader("Step 2: Review Extracted Data")

        extracted = st.session_state.extracted_data

        # Display and allow editing of extracted fields
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("Title/Description", value=extracted.title)
            vendor_name = st.text_input("Vendor Name", value=extracted.vendor_name)
            vat_id = st.text_input("VAT ID", value=extracted.vat_id)

        with col2:
            commodity_group = st.number_input(
                "Commodity Group ID",
                value=extracted.commodity_group,
                min_value=1,
                max_value=50,
            )
            commodity_name = app.get_commodity_group_name(commodity_group)
            st.text(f"Group: {commodity_name}")
            total_cost = st.number_input(
                "Total Cost", value=extracted.total_cost, min_value=0.0, format="%.2f"
            )

        # Display order lines
        st.subheader("Order Lines")
        for i, line in enumerate(extracted.order_lines):
            with st.expander(f"Line {i + 1}: {line.position_description[:50]}..."):
                st.text(f"Description: {line.position_description}")
                st.text(f"Unit: {line.unit}")
                st.text(f"Unit Price: {line.unit_price:.2f}")
                st.text(f"Amount: {line.amount:.2f}")
                st.text(f"Total: {line.total_price:.2f}")

        # Step 3: Submit
        st.subheader("Step 3: Submit Request")

        # Show user info from session
        st.info(
            f"Submitting as: **{st.session_state.user_name}** "
            f"(Department: **{st.session_state.user_department}**)"
        )

        if st.button("Submit Request", type="primary"):
            with st.spinner("Saving request..."):
                try:
                    # Create request with potentially edited values
                    # For now, we use extracted data as-is (editing would require more complex state)
                    request = app.create_request(
                        extracted_data=extracted,
                        requestor_name=st.session_state.user_name,
                        requestor_department=st.session_state.user_department,
                    )
                    request_id = app.save_request(request)

                    st.success(f"Request submitted successfully! (ID: {request_id})")

                    # Clear session state for this page
                    st.session_state.extracted_data = None
                    st.session_state.pdf_text = None
                    st.session_state.uploaded_file_name = None

                except Exception as e:
                    st.error(f"Error saving request: {e}")

        # Reset button
        if st.button("Start Over"):
            st.session_state.extracted_data = None
            st.session_state.pdf_text = None
            st.session_state.uploaded_file_name = None
            st.rerun()

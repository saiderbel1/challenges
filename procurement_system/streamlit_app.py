import streamlit as st

from services import ProcurementApp
from pages import submit_request, my_requests


# Page configuration
st.set_page_config(
    page_title="Procurement System",
    page_icon="📋",
    layout="wide",
)


@st.cache_resource
def get_app() -> ProcurementApp:
    """Get or create the ProcurementApp instance."""
    return ProcurementApp()


def render_login():
    """Render the login gate page."""
    st.title("Procurement Request System")
    st.subheader("Please enter your information to continue")

    with st.form("login_form"):
        name = st.text_input("Your Name", placeholder="Enter your full name")
        department = st.text_input("Department", placeholder="Enter your department")
        submitted = st.form_submit_button("Continue", type="primary")

        if submitted:
            if not name.strip():
                st.error("Please enter your name.")
            elif not department.strip():
                st.error("Please enter your department.")
            else:
                st.session_state.user_name = name.strip()
                st.session_state.user_department = department.strip()
                st.session_state.logged_in = True
                st.rerun()


def render_main_app():
    """Render the main application with sidebar navigation."""
    app = get_app()

    # Sidebar
    with st.sidebar:
        st.title("Procurement System")
        st.divider()

        st.markdown(f"**User:** {st.session_state.user_name}")
        st.markdown(f"**Department:** {st.session_state.user_department}")
        st.divider()

        # Navigation
        if st.button("Submit New Request", use_container_width=True):
            st.session_state.current_page = "submit_request"
            st.rerun()

        if st.button("My Requests", use_container_width=True):
            st.session_state.current_page = "my_requests"
            st.rerun()

        st.divider()

        if st.button("Logout", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Initialize current page if not set
    if "current_page" not in st.session_state:
        st.session_state.current_page = "submit_request"

    # Render current page
    if st.session_state.current_page == "submit_request":
        submit_request.render(app)
    elif st.session_state.current_page == "my_requests":
        my_requests.render(app)


def main():
    """Main entry point for the Streamlit app."""
    # Check if user is logged in
    if not st.session_state.get("logged_in", False):
        render_login()
    else:
        render_main_app()


if __name__ == "__main__":
    main()

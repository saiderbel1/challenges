import streamlit as st
from streamlit_option_menu import option_menu

from services import ProcurementApp
from views import submit_request, my_requests


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
        st.markdown(f"**User:** {st.session_state.user_name}")
        st.markdown(f"**Department:** {st.session_state.user_department}")
        st.divider()

        # Navigation menu
        selected = option_menu(
            menu_title="Procurement System",
            options=["Submit Request", "My Requests", "Logout"],
            icons=["cloud-upload", "list-task", "box-arrow-right"],
            menu_icon="clipboard-check",
            default_index=0,
        )

    # Handle navigation
    if selected == "Logout":
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    elif selected == "Submit Request":
        submit_request.render(app)
    elif selected == "My Requests":
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

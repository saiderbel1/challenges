import streamlit as st
from streamlit_option_menu import option_menu

from services import ProcurementApp
from views import submit_request, my_requests, management_dashboard


# Page configuration
st.set_page_config(
    page_title="Procurement System",
    page_icon="📋",
    layout="wide",
)

st.markdown(
    """<style>
    .block-container { padding-top: 2rem; }

    /* Request cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(128, 128, 128, 0.06) !important;
        border-radius: 8px !important;
    }

    /* Order line cards inside expanders */
    div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(128, 128, 128, 0.12) !important;
    }

    /* st.code() block containers */
    div[data-testid="stCode"] pre {
        background-color: rgba(128, 128, 128, 0.10) !important;
        border-radius: 6px !important;
    }
    </style>""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_app() -> ProcurementApp:
    """Get or create the ProcurementApp instance."""
    return ProcurementApp()


def render_landing():
    """Render the landing page with user/management options."""
    st.title("Procurement Request System")

    st.subheader("Select your role:")

    col1, col2, _ = st.columns([1, 1, 2])

    with col1:
        if st.button("User", type="primary", use_container_width=True):
            st.session_state.login_mode = "user"
            st.rerun()

    with col2:
        if st.button("Management", use_container_width=True):
            st.session_state.login_mode = "management"
            st.rerun()


def render_user_login():
    """Render the user login page."""
    st.title("Procurement Request System")
    st.subheader("Please enter your information to continue")

    if st.button("← Back"):
        del st.session_state.login_mode
        st.rerun()

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
                st.session_state.user_type = "user"
                st.rerun()


def render_management_login():
    """Render the management login page."""
    st.title("Management Dashboard")
    st.subheader("Please enter your name to continue")

    if st.button("← Back"):
        del st.session_state.login_mode
        st.rerun()

    with st.form("management_login_form"):
        name = st.text_input("Your Name", placeholder="Enter your full name")
        submitted = st.form_submit_button("Continue", type="primary")

        if submitted:
            if not name.strip():
                st.error("Please enter your name.")
            else:
                st.session_state.manager_name = name.strip()
                st.session_state.logged_in = True
                st.session_state.user_type = "manager"
                st.rerun()


def render_user_app():
    """Render the main user application with sidebar navigation."""
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
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    elif selected == "Submit Request":
        submit_request.render(app)
    elif selected == "My Requests":
        my_requests.render(app)


def render_management_app():
    """Render the management dashboard with sidebar navigation."""
    app = get_app()

    # Sidebar
    with st.sidebar:
        st.markdown(f"**Manager:** {st.session_state.manager_name}")
        st.divider()

        # Navigation menu
        selected = option_menu(
            menu_title="Management",
            options=["Request Submissions", "Logout"],
            icons=["inbox-fill", "box-arrow-right"],
            menu_icon="gear-fill",
            default_index=0,
        )

    # Handle navigation
    if selected == "Logout":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    elif selected == "Request Submissions":
        management_dashboard.render(app)


def main():
    """Main entry point for the Streamlit app."""
    # Check login state
    if st.session_state.get("logged_in", False):
        if st.session_state.get("user_type") == "manager":
            render_management_app()
        else:
            render_user_app()
    elif st.session_state.get("login_mode") == "user":
        render_user_login()
    elif st.session_state.get("login_mode") == "management":
        render_management_login()
    else:
        render_landing()


if __name__ == "__main__":
    main()

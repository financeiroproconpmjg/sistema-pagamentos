import streamlit as st
from streamlit_option_menu import option_menu
from views.audit import render_audit
from views.crud import render_crud
from views.dashboard import render_dashboard
from views.reports import render_reports

st.set_page_config(
    page_title="Sistema de Gestão de Pagamentos",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- AUTENTICAÇÃO / LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Acesso ao Sistema de Pagamentos")
    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            users_db = st.secrets["users"]
            if user in users_db and users_db[user] == password:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# --- SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user}")

    menu = option_menu(
        menu_title="Navegação",
        options=[
            "Dashboard Matricial",
            "Lançamentos (CRUD)",
            "Central de Relatórios",
            "Histórico de Auditoria",
        ],
        icons=[
            "bar-chart-fill",
            "pencil-square",
            "file-earmark-bar-graph",
            "shield-check",
        ],
        menu_icon="compass-fill",
        default_index=0,
    )

    st.markdown("---")
    if st.button("Sair / Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# --- ROTEAMENTO DE TELAS ---
if menu == "Dashboard Matricial":
    render_dashboard()
elif menu == "Lançamentos (CRUD)":
    render_crud()
elif menu == "Central de Relatórios":
    render_reports()
elif menu == "Histórico de Auditoria":
    render_audit()

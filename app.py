import streamlit as st
from views.audit import render_audit
from views.crud import render_crud
from views.dashboard import render_dashboard

st.set_page_config(
    page_title="Sistema de Gestão de Pagamentos",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

st.sidebar.title(f"👤 Usuário: {st.session_state.user}")
if st.sidebar.button("Sair / Logout"):
    st.session_state.logged_in = False
    st.rerun()

menu = st.sidebar.radio(
    "Menu Principal",
    [
        "📊 Dashboard Matricial",
        "📝 Lançamentos (CRUD)",
        "📜 Histórico de Auditoria",
    ],
)

if menu == "📊 Dashboard Matricial":
    render_dashboard()
elif menu == "📝 Lançamentos (CRUD)":
    render_crud()
elif menu == "📜 Histórico de Auditoria":
    render_audit()
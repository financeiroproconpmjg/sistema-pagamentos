import streamlit as st
from database import load_table


def render_audit():
    st.title("Trilha de Auditoria e Alterações (LGPD)")
    df_hist, _ = load_table("HISTORICO_STATUS")
    st.dataframe(df_hist, use_container_width=True)

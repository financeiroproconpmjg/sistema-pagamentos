# views/crud/tab_read.py
import streamlit as st

from database import load_table


def render_read():
    st.subheader("📋 Visualização Geral do Banco de Dados")

    sel_view = st.radio(
        "Selecione a Tabela",
        ["Pagamentos", "Sub-Empenhos", "Empenhos Globais", "Contratos", "Empresas"],
        horizontal=True,
    )

    if sel_view == "Pagamentos":
        df, _ = load_table("PAGAMENTOS")
    elif sel_view == "Sub-Empenhos":
        df, _ = load_table("SUB_EMPENHO")
    elif sel_view == "Empenhos Globais":
        df, _ = load_table("EMPENHO_GLOBAL")
    elif sel_view == "Contratos":
        df, _ = load_table("CONTRACT")
    elif sel_view == "Empresas":
        df, _ = load_table("COMPANY")

    st.dataframe(df, use_container_width=True)

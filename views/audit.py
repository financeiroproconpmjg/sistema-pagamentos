import streamlit as st

from services.audit_service import get_audit_history


def render_audit():
    st.title("📜 Trilha de Auditoria e Alterações (LGPD)")

    # Chamada via Camada de Serviço
    df_hist, _ = get_audit_history()

    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("Nenhum registro de auditoria encontrado na planilha.")

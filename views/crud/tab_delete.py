# views/crud/tab_delete.py
import streamlit as st

from services import payment_service


def refresh_caches():
    st.cache_data.clear()
    st.cache_resource.clear()


def render_delete():
    st.subheader("🗑️ Excluir Registro de Pagamento")
    df_payments, _ = payment_service.get_payments()

    if not df_payments.empty and "id" in df_payments.columns:
        del_id = st.selectbox(
            "ID do Lançamento para Excluir",
            df_payments["id"].tolist(),
            key="sb_del_id",
        )

        if st.button("Confirmar Exclusão Permanente", type="primary"):
            payment_service.delete_payment(
                payment_id=del_id, user=st.session_state.user
            )
            st.success("Lançamento removido permanentemente!")
            refresh_caches()
            st.rerun()

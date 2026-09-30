# views/crud/tab_update.py
import streamlit as st

from config import STATUS_OPTIONS
from services import payment_service


def refresh_caches():
    st.cache_data.clear()
    st.cache_resource.clear()


def render_update():
    st.subheader("✏️ Alterar Etapa / Status do Pagamento")
    df_payments, _ = payment_service.get_payments()

    if not df_payments.empty and "id" in df_payments.columns:
        p_id = st.selectbox(
            "Selecione o Lançamento (ID)",
            df_payments["id"].tolist(),
            key="sb_upd_id",
        )
        curr = df_payments[df_payments["id"] == p_id].iloc[0]

        st.info(
            f"**Contrato:** {curr['contract_number']} | **Mês:**"
            f" {curr['reference_month']} | **Status Atual:** {curr['current_status']}"
        )

        with st.form("f_update"):
            next_st = st.selectbox(
                "Mudar para o Status",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(curr["current_status"])
                if curr["current_status"] in STATUS_OPTIONS
                else 0,
            )

            default_val = payment_service.clean_num_val(curr.get("paid_amount", 0.0))
            paid_val_input = st.number_input(
                "Valor Efetivado (R$)", value=default_val, step=100.0
            )
            obs_up = st.text_area("Motivo da Mudança de Etapa")

            if st.form_submit_button("Gravar Alteração de Status"):
                payment_service.update_payment_status(
                    payment_id=p_id,
                    new_status=next_st,
                    paid_amount=paid_val_input,
                    user=st.session_state.user,
                    obs=obs_up,
                )

                st.success(
                    f"Pagamento #{p_id} atualizado com sucesso para **{next_st}**!"
                )
                refresh_caches()
                st.rerun()

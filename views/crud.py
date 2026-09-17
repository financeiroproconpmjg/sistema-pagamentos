import datetime
import pandas as pd
import streamlit as st
from config import STATUS_OPTIONS
from database import load_table


def render_crud():
    st.title("Gerenciamento de Pagamentos")

    df_contracts, _ = load_table("CONTRACT")
    df_payments, ws_payments = load_table("PAGAMENTOS")
    df_sub, _ = load_table("SUB_EMPENHO")
    df_eg, _ = load_table("EMPENHO_GLOBAL")
    _, ws_history = load_table("HISTORICO_STATUS")

    t_read, t_create, t_update, t_delete = st.tabs(
        ["📋 Listar", "➕ Novo", "✏️ Atualizar Status", "🗑️ Excluir"]
    )

    with t_read:
        st.dataframe(df_payments, use_container_width=True)

    with t_create:
        st.subheader("Criar Registro de Pagamento")

        next_sub_id = (
            int(pd.to_numeric(df_sub["id"], errors="coerce").max() + 1)
            if not df_sub.empty
            else 101
        )

        with st.form("f_create"):
            ctr_sel = st.selectbox(
                "Contrato", df_contracts["contract_number"].tolist()
            )
            ref_m = st.text_input("Mês de Referência (MM/YYYY)", "03/2026")
            sub_id = st.number_input(
                "ID do Sub-empenho", value=next_sub_id, step=1
            )
            p_val = st.number_input("Valor Pago (R$)", value=0.0, step=100.0)
            init_st = st.selectbox("Status Inicial", STATUS_OPTIONS)
            obs = st.text_area("Observação do Lançamento")

            if st.form_submit_button("Salvar no Banco"):
                new_id = (
                    int(
                        pd.to_numeric(
                            df_payments["id"], errors="coerce"
                        ).max()
                        + 1
                    )
                    if not df_payments.empty
                    else 1001
                )

                match_cnpj = df_contracts[
                    df_contracts["contract_number"] == ctr_sel
                ]["company_cnpj"].values
                cnpj_val = match_cnpj[0] if len(match_cnpj) > 0 else ""

                ws_payments.append_row([
                    new_id,
                    sub_id,
                    cnpj_val,
                    ctr_sel,
                    ref_m,
                    ref_m,
                    "Adiantado",
                    p_val,
                    str(datetime.date.today().strftime("%d/%m/%Y")),
                    init_st,
                ])

                ws_history.append_row([
                    len(ws_history.get_all_values()) + 1,
                    new_id,
                    ctr_sel,
                    "N/A",
                    sub_id,
                    "NOVO_REGISTRO",
                    init_st,
                    str(
                        datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    ),
                    st.session_state.user,
                    f"Criação: {obs}",
                ])

                st.success(
                    f"Pagamento #{new_id} criado com sucesso para o mês {ref_m}!"
                )
                st.cache_resource.clear()

    with t_update:
        st.subheader("Alterar Etapa / Status do Pagamento")
        if not df_payments.empty:
            p_id = st.selectbox(
                "Selecione o Lançamento (ID)", df_payments["id"].tolist()
            )
            curr = df_payments[df_payments["id"] == p_id].iloc[0]

            st.info(
                f"**Contrato:** {curr['contract_number']} | **Mês:** {curr['reference_month']} | **Status Atual:** {curr['current_status']}"
            )

            with st.form("f_update"):
                next_st = st.selectbox(
                    "Mudar para o Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(curr["current_status"])
                    if curr["current_status"] in STATUS_OPTIONS
                    else 0,
                )

                if next_st == "PAGO":
                    sub_id_curr = curr["sub_empenho_id"]
                    match_sub = (
                        df_sub[df_sub["id"].astype(str) == str(sub_id_curr)]
                        if not df_sub.empty
                        else pd.DataFrame()
                    )
                    default_val = (
                        float(match_sub["value"].values[0])
                        if not match_sub.empty
                        else 0.0
                    )

                    paid_val_input = st.number_input(
                        "Valor Final Efetuado (R$)",
                        value=default_val,
                        step=100.0,
                    )

                obs_up = st.text_area("Motivo da Mudança de Etapa")

                if st.form_submit_button("Atualizar e Gravar Histórico"):
                    cell = ws_payments.find(str(p_id))
                    row_idx = cell.row

                    if next_st == "PAGO":
                        today_str = datetime.date.today().strftime("%d/%m/%Y")
                        ws_payments.update_cell(row_idx, 8, paid_val_input)
                        ws_payments.update_cell(row_idx, 9, today_str)
                        ws_payments.update_cell(row_idx, 10, next_st)
                    else:
                        ws_payments.update_cell(row_idx, 10, next_st)

                    ws_history.append_row([
                        len(ws_history.get_all_values()) + 1,
                        p_id,
                        curr["contract_number"],
                        "N/A",
                        curr["sub_empenho_id"],
                        curr["current_status"],
                        next_st,
                        str(
                            datetime.datetime.now().strftime(
                                "%d/%m/%Y %H:%M:%S"
                            )
                        ),
                        st.session_state.user,
                        obs_up,
                    ])

                    st.success(
                        f"Pagamento #{p_id} atualizado para **{next_st}**!"
                    )
                    st.cache_resource.clear()

    with t_delete:
        if not df_payments.empty:
            del_id = st.selectbox(
                "ID do Lançamento para Excluir", df_payments["id"].tolist()
            )
            if st.button("Confirmar Exclusão Permanente", type="primary"):
                cell = ws_payments.find(str(del_id))
                ws_payments.delete_rows(cell.row)

                ws_history.append_row([
                    len(ws_history.get_all_values()) + 1,
                    del_id,
                    "N/A",
                    "N/A",
                    "N/A",
                    "DELETADO",
                    "DELETADO",
                    str(
                        datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    ),
                    st.session_state.user,
                    "Registro removido",
                ])
                st.success("Registro apagado com sucesso!")
                st.cache_resource.clear()

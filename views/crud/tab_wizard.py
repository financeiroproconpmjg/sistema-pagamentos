# views/crud/tab_wizard.py
from datetime import datetime, timedelta, timezone

import streamlit as st

from config import STATUS_OPTIONS
from services import (
    company_service,
    contract_service,
    empenho_service,
    payment_service,
)

# Fuso horário oficial de Brasília/Recife (UTC-3)
TZ_BR = timezone(timedelta(hours=-3))


def refresh_caches():
    st.cache_data.clear()
    st.cache_resource.clear()


def render_wizard():
    st.subheader("🔁 Cadastro Encadeado por Etapas")
    today_d = datetime.now(tz=TZ_BR).date()

    # -------------------------------------------------------------------------
    # ETAPA 1: EMPRESA
    # -------------------------------------------------------------------------
    st.markdown("##### 1️⃣ Empresa")
    df_company, _, cnpj_to_name = company_service.get_companies()
    existing_cnpjs = (
        df_company["cnpj"].dropna().unique()
        if not df_company.empty and "cnpj" in df_company.columns
        else []
    )
    opt_companies = [
        f"{cnpj_to_name.get(str(c).strip(), str(c))} ({c})" for c in existing_cnpjs
    ]
    opt_companies_all = ["[ + Cadastrar Nova Empresa ]"] + opt_companies

    selected_company_opt = st.selectbox(
        "Selecione a Empresa ou Cadastre uma Nova",
        options=opt_companies_all,
        key="sb_comp",
    )

    if selected_company_opt == "[ + Cadastrar Nova Empresa ]":
        with (
            st.expander("📝 Formulário: Nova Empresa", expanded=True),
            st.form("f_new_company"),
        ):
            c_nome = st.text_input(
                "Nome da Empresa (Razão Social)",
                placeholder="Ex: Empresa Brasileira de Correios e Telégrafos",
            )
            c_cnpj = st.text_input(
                "CNPJ da Empresa", placeholder="Ex: 34.028.316/0021-57"
            )

            if st.form_submit_button("💾 Salvar Nova Empresa"):
                if not c_nome or not c_cnpj:
                    st.error("Preencha o Nome e o CNPJ da empresa.")
                else:
                    company_service.create_company(c_cnpj, c_nome)
                    st.success(
                        f"Empresa **{c_nome}** ({c_cnpj}) cadastrada com sucesso!"
                    )
                    refresh_caches()
                    st.rerun()
        st.stop()

    selected_cnpj = selected_company_opt.split("(")[-1].replace(")", "").strip()
    selected_comp_nome = cnpj_to_name.get(selected_cnpj, selected_cnpj)
    st.caption(
        f"🏢 **Empresa Selecionada:** {selected_comp_nome} | **CNPJ:** {selected_cnpj}"
    )
    st.markdown("---")

    # -------------------------------------------------------------------------
    # ETAPA 2: CONTRATO
    # -------------------------------------------------------------------------
    st.markdown("##### 2️⃣ Contrato")
    df_contracts, _, df_contracts_comp = contract_service.get_contracts_by_company(
        selected_cnpj
    )
    contracts_list = (
        df_contracts_comp["contract_number"].tolist()
        if not df_contracts_comp.empty
        and "contract_number" in df_contracts_comp.columns
        else []
    )
    opt_contracts = ["[ + Criar Novo Contrato ]"] + contracts_list

    selected_contract_opt = st.selectbox(
        f"Selecione um Contrato da empresa {selected_comp_nome} ou Crie um Novo",
        options=opt_contracts,
        key="sb_ctr",
    )

    if selected_contract_opt == "[ + Criar Novo Contrato ]":
        with (
            st.expander(
                f"📝 Formulário: Novo Contrato para {selected_comp_nome}",
                expanded=True,
            ),
            st.form("f_new_contract"),
        ):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                new_ctr_num = st.text_input(
                    "Número do Contrato", placeholder="Ex: 991/2513 - 442"
                )
                manager_name = st.text_input(
                    "Nome do Gestor / Fiscal", placeholder="Ex: Gabriel Marques"
                )
                regime_pag = st.selectbox(
                    "Regime de Pagamento Padronizado",
                    ["Mensal", "Excepcional"],
                    index=0,
                )

            with col_c2:
                start_d = st.date_input(
                    "Data de Início da Vigência",
                    value=today_d,
                    format="DD/MM/YYYY",
                )
                end_d = st.date_input(
                    "Data de Fim da Vigência",
                    value=today_d + timedelta(days=365),
                    format="DD/MM/YYYY",
                )

            if st.form_submit_button("💾 Salvar Novo Contrato"):
                all_ctrs = (
                    df_contracts["contract_number"].tolist()
                    if not df_contracts.empty
                    and "contract_number" in df_contracts.columns
                    else []
                )
                if not new_ctr_num or new_ctr_num in all_ctrs:
                    st.error("Número de contrato inválido ou já existente.")
                else:
                    contract_service.create_contract(
                        new_ctr_num,
                        selected_cnpj,
                        manager_name,
                        start_d,
                        end_d,
                        regime_pag,
                    )
                    st.success(f"Contrato **{new_ctr_num}** cadastrado com sucesso!")
                    refresh_caches()
                    st.rerun()
        st.stop()

    selected_contract = selected_contract_opt
    st.caption(f"📄 **Contrato Selecionado:** {selected_contract}")
    st.markdown("---")

    # -------------------------------------------------------------------------
    # ETAPA 3: EMPENHO GLOBAL
    # -------------------------------------------------------------------------
    st.markdown("##### 3️⃣ Empenho Global")
    _, _, df_eg_contract = empenho_service.get_empenhos_by_contract(selected_contract)

    eg_options_map = {}
    if not df_eg_contract.empty:
        for _, eg_row in df_eg_contract.iterrows():
            eg_id_val = str(eg_row.get("id", "")).strip()
            eg_num_val = str(eg_row.get("number", eg_id_val)).strip()
            eg_val_num = empenho_service.clean_num_val(eg_row.get("value", 0.0))
            label = f"Empenho Nº {eg_num_val} - R$ {eg_val_num:,.2f}"
            eg_options_map[label] = eg_id_val

    opt_eg = ["[ + Criar Novo Empenho Global ]"] + list(eg_options_map.keys())

    selected_eg_label = st.selectbox(
        "Selecione o Empenho Global ou Crie um Novo",
        options=opt_eg,
        key="sb_eg",
    )

    if selected_eg_label == "[ + Criar Novo Empenho Global ]":
        with (
            st.expander("📝 Formulário: Novo Empenho Global", expanded=True),
            st.form("f_new_eg"),
        ):
            eg_number = st.text_input(
                "Número do Empenho Global (ex: 536)", placeholder="536"
            )
            eg_val_input = st.number_input(
                "Valor do Empenho Global (Teto R$)", value=0.0, step=1000.0
            )

            col_eg1, col_eg2 = st.columns(2)
            with col_eg1:
                eg_start_d = st.date_input(
                    "Data Início da Vigência",
                    value=today_d,
                    format="DD/MM/YYYY",
                )
            with col_eg2:
                eg_end_d = st.date_input(
                    "Data Fim da Vigência",
                    value=today_d + timedelta(days=365),
                    format="DD/MM/YYYY",
                )

            if st.form_submit_button("Salvar Novo Empenho Global"):
                if not eg_number:
                    st.error("Informe o número do Empenho Global.")
                else:
                    empenho_service.create_empenho_global(
                        selected_contract, eg_number, eg_val_input, eg_start_d, eg_end_d
                    )
                    st.success(f"Empenho Global **Nº {eg_number}** criado com sucesso!")
                    refresh_caches()
                    st.rerun()
        st.stop()

    selected_eg_id = eg_options_map[selected_eg_label]
    eg_info = df_eg_contract[df_eg_contract["id"].astype(str) == selected_eg_id].iloc[0]
    st.caption(
        f"💰 **Número:** {eg_info.get('number', '---')} | **Valor Teto:** R$ {empenho_service.clean_num_val(eg_info.get('value', 0)):,.2f} | **Status:** {'Cancelado' if str(eg_info.get('is_canceled')).upper() == 'VERDADEIRO' else 'Ativo'}"
    )
    st.markdown("---")

    # -------------------------------------------------------------------------
    # ETAPA 4: SUB-EMPENHO & PAGAMENTO
    # -------------------------------------------------------------------------
    st.markdown("##### 4️⃣ Sub-Empenho e Lançamento do Pagamento")
    _, _, df_sub_eg = payment_service.get_sub_empenhos(selected_eg_id)

    sub_options_map = {}
    if not df_sub_eg.empty:
        for _, sub_row in df_sub_eg.iterrows():
            sub_id_val = str(sub_row.get("id", "")).strip()
            sub_ref_val = str(sub_row.get("reference_month", "---")).strip()
            sub_val_num = payment_service.clean_num_val(sub_row.get("value", 0.0))
            label = f"Sub-Empenho (Ref: {sub_ref_val}) - R$ {sub_val_num:,.2f}"
            sub_options_map[label] = sub_id_val

    opt_sub = ["[ + Criar Novo Sub-Empenho e Lançar Pagamento ]"] + list(
        sub_options_map.keys()
    )

    selected_sub_label = st.selectbox(
        "Selecione um Sub-Empenho Existente ou Crie um Novo",
        options=opt_sub,
        key="sb_sub",
    )

    if selected_sub_label == "[ + Criar Novo Sub-Empenho e Lançar Pagamento ]":
        with (
            st.expander("📝 Formulário: Novo Sub-Empenho & Pagamento", expanded=True),
            st.form("f_new_sub_and_payment"),
        ):
            st.markdown("###### 🔹 Dados do Sub-Empenho")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                sub_ref_m = st.text_input("Mês de Referência (MM/YYYY)", "01/2026")
            with col_s2:
                sub_val = st.number_input(
                    "Valor do Sub-Empenho (R$)", value=0.0, step=500.0
                )

            st.markdown("---")
            st.markdown("###### 🔹 Dados do Lançamento do Pagamento")

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                p_exec_m = st.text_input(
                    "Mês de Execução do Pagamento (MM/YYYY)", value="02/2026"
                )
                regime_p = st.selectbox(
                    "Regime de Pagamento", ["Mensal", "Excepcional"], index=0
                )

            with col_p2:
                p_val = st.number_input(
                    "Valor Efetivo do Pagamento (R$)", value=sub_val, step=500.0
                )
                init_st = st.selectbox(
                    "Status Inicial do Pagamento", STATUS_OPTIONS, index=0
                )

            obs = st.text_area("Observações do Lançamento / Histórico")

            if st.form_submit_button("💾 Salvar Sub-Empenho e Gerar Pagamento"):
                if not sub_ref_m:
                    st.error("Informe o mês de referência (MM/YYYY).")
                else:
                    payment_service.create_sub_and_payment(
                        empenho_global_id=selected_eg_id,
                        company_cnpj=selected_cnpj,
                        contract_number=selected_contract,
                        sub_ref_month=sub_ref_m,
                        sub_value=sub_val,
                        payment_exec_month=p_exec_m,
                        regime_pagamento=regime_p,
                        paid_amount=p_val,
                        current_status=init_st,
                        user=st.session_state.user,
                        obs=obs,
                    )
                    st.success(
                        f"✅ Sub-Empenho do mês **{sub_ref_m}** e Pagamento salvos com"
                        " sucesso na planilha!"
                    )
                    refresh_caches()
                    st.rerun()
        st.stop()
    else:
        selected_sub_id = sub_options_map[selected_sub_label]
        sub_info = df_sub_eg[df_sub_eg["id"].astype(str) == selected_sub_id].iloc[0]
        st.info(
            f"📅 **Mês de Ref:** {sub_info.get('reference_month', '')} | **Valor:**"
            f" R$ {payment_service.clean_num_val(sub_info.get('value', 0)):,.2f}"
        )

# views/crud.py
import datetime
import pandas as pd
import streamlit as st
from config import STATUS_OPTIONS
from database import load_table


def refresh_caches():
    """Limpa os caches de dados e recursos do Streamlit."""
    st.cache_data.clear()
    st.cache_resource.clear()


def clean_num_val(val_str):
    """Converte string PT-BR para float."""
    if pd.isna(val_str) or val_str is None:
        return 0.0
    s = str(val_str).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def render_crud():
    st.title("⚙️ Gerenciamento de Contratos, Empenhos e Pagamentos")

    # Carrega tabelas e Worksheets
    df_contracts, ws_contracts = load_table("CONTRACT")
    df_payments, ws_payments = load_table("PAGAMENTOS")
    df_sub, ws_sub = load_table("SUB_EMPENHO")
    df_eg, ws_eg = load_table("EMPENHO_GLOBAL")
    df_company, ws_company = load_table("COMPANY")
    _, ws_history = load_table("HISTORICO_STATUS")

    # Mapeamento CNPJ -> Nome da Empresa
    cnpj_to_name = {}
    if not df_company.empty:
        cnpj_col = next(
            (c for c in ["cnpj", "company_cnpj"] if c in df_company.columns),
            None,
        )
        name_col = next(
            (
                c
                for c in [
                    "company_name",
                    "razao_social",
                    "nome",
                    "name",
                    "company",
                ]
                if c in df_company.columns
            ),
            None,
        )
        if cnpj_col and name_col:
            for _, r in df_company.iterrows():
                c_val = str(r[cnpj_col]).strip()
                n_val = str(r[name_col]).strip()
                if c_val and n_val:
                    cnpj_to_name[c_val] = n_val

    t_create, t_read, t_update, t_delete = st.tabs([
        "➕ Novo Lançamento (Etapas)",
        "📋 Listar Registros",
        "✏️ Atualizar Status",
        "🗑️ Excluir Lançamento",
    ])

    # =========================================================================
    # TAB 1: NOVO LANÇAMENTO EM ETAPAS (EMPRESA -> CONTRATO -> GLOBAL -> SUB -> PAGAMENTO)
    # =========================================================================
    with t_create:
        st.subheader("🔁 Cadastro Encadeado por Etapas")

        # -------------------------------------------------------------------------
        # ETAPA 1: SELEÇÃO OU CRIAÇÃO DA EMPRESA
        # -------------------------------------------------------------------------
        st.markdown("##### 1️⃣ Empresa")
        existing_cnpjs = (
            df_company["cnpj"].dropna().unique()
            if not df_company.empty and "cnpj" in df_company.columns
            else []
        )
        opt_companies = [
            f"{cnpj_to_name.get(str(c).strip(), str(c))} ({c})"
            for c in existing_cnpjs
        ]
        opt_companies_all = ["[ + Cadastrar Nova Empresa ]"] + opt_companies

        selected_company_opt = st.selectbox(
            "Selecione a Empresa ou Cadastre uma Nova",
            options=opt_companies_all,
            key="sb_comp",
        )

        if selected_company_opt == "[ + Cadastrar Nova Empresa ]":
            with st.expander("📝 Formulário: Nova Empresa", expanded=True):
                with st.form("f_new_company"):
                    c_nome = st.text_input(
                        "Nome da Empresa (Razão Social)",
                        placeholder="Ex: Toppus Serviços Terceirizados Eireli",
                    )
                    c_cnpj = st.text_input(
                        "CNPJ da Empresa", placeholder="Ex: 09.281.162/0001-10"
                    )

                    if st.form_submit_button("💾 Salvar Nova Empresa"):
                        if not c_nome or not c_cnpj:
                            st.error("Preencha o Nome e o CNPJ da empresa.")
                        else:
                            ws_company.append_row([c_cnpj.strip(), c_nome.strip()])
                            st.success(
                                f"Empresa **{c_nome}** ({c_cnpj}) cadastrada com sucesso!"
                            )
                            refresh_caches()
                            st.rerun()
            st.stop()
        else:
            selected_cnpj = (
                selected_company_opt.split("(")[-1].replace(")", "").strip()
            )
            selected_comp_nome = cnpj_to_name.get(selected_cnpj, selected_cnpj)
            st.caption(
                f"🏢 **Empresa Selecionada:** {selected_comp_nome} | **CNPJ:** {selected_cnpj}"
            )

        st.markdown("---")

        # -------------------------------------------------------------------------
        # ETAPA 2: SELEÇÃO OU CRIAÇÃO DO CONTRATO (FILTRADO PELA EMPRESA)
        # -------------------------------------------------------------------------
        st.markdown("##### 2️⃣ Contrato")
        df_contracts_comp = (
            df_contracts[
                df_contracts["company_cnpj"].astype(str).str.strip() == selected_cnpj
            ]
            if not df_contracts.empty and "company_cnpj" in df_contracts.columns
            else pd.DataFrame()
        )
        contracts_list = (
            df_contracts_comp["contract_number"].tolist()
            if not df_contracts_comp.empty and "contract_number" in df_contracts_comp.columns
            else []
        )
        opt_contracts = ["[ + Criar Novo Contrato ]"] + contracts_list

        selected_contract_opt = st.selectbox(
            f"Selecione um Contrato da empresa {selected_comp_nome} ou Crie um Novo",
            options=opt_contracts,
            key="sb_ctr",
        )

        if selected_contract_opt == "[ + Criar Novo Contrato ]":
            with st.expander(
                f"📝 Formulário: Novo Contrato para {selected_comp_nome}",
                expanded=True,
            ):
                with st.form("f_new_contract"):
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        new_ctr_num = st.text_input(
                            "Número do Contrato", placeholder="Ex: 016/2023 - SME"
                        )
                        manager_name = st.text_input(
                            "Nome do Gestor / Fiscal", placeholder="Ex: Gabriel Marques"
                        )
                        regime_pag = st.selectbox(
                            "Regime de Pagamento", ["Mensal", "Excepcional"], index=0
                        )

                    with col_c2:
                        start_d = st.date_input(
                            "Data de Início da Vigência",
                            value=datetime.date.today(),
                            format="DD/MM/YYYY",
                        )
                        end_d = st.date_input(
                            "Data de Fim da Vigência",
                            value=datetime.date.today() + datetime.timedelta(days=365),
                            format="DD/MM/YYYY",
                        )

                    if st.form_submit_button("💾 Salvar Novo Contrato"):
                        all_existing_ctrs = (
                            df_contracts["contract_number"].tolist()
                            if not df_contracts.empty and "contract_number" in df_contracts.columns
                            else []
                        )
                        if not new_ctr_num or new_ctr_num in all_existing_ctrs:
                            st.error("Número de contrato inválido ou já existente.")
                        else:
                            start_d_str = start_d.strftime("%d/%m/%Y")
                            end_d_str = end_d.strftime("%d/%m/%Y")

                            ws_contracts.append_row([
                                new_ctr_num.strip(),
                                selected_cnpj,
                                manager_name.strip(),
                                start_d_str,
                                end_d_str,
                                regime_pag,
                            ])

                            st.success(
                                f"Contrato **{new_ctr_num}** cadastrado com sucesso!"
                            )
                            refresh_caches()
                            st.rerun()
            st.stop()
        else:
            selected_contract = selected_contract_opt
            st.caption(f"📄 **Contrato Selecionado:** {selected_contract}")

        st.markdown("---")

        # -------------------------------------------------------------------------
        # ETAPA 3: SELEÇÃO OU CRIAÇÃO DO EMPENHO GLOBAL
        # -------------------------------------------------------------------------
        st.markdown("##### 3️⃣ Empenho Global")
        df_eg_contract = (
            df_eg[df_eg["contract_number"] == selected_contract]
            if not df_eg.empty and "contract_number" in df_eg.columns
            else pd.DataFrame()
        )

        eg_options_map = {}
        if not df_eg_contract.empty:
            for _, eg_row in df_eg_contract.iterrows():
                eg_id_val = str(eg_row.get("id", "")).strip()
                eg_num_val = str(eg_row.get("number", eg_id_val)).strip()
                eg_val_num = clean_num_val(eg_row.get("value", 0.0))
                label = f"Empenho Nº {eg_num_val} (ID: {eg_id_val}) - R$ {eg_val_num:,.2f}"
                eg_options_map[label] = eg_id_val

        opt_eg = ["[ + Criar Novo Empenho Global ]"] + list(eg_options_map.keys())

        selected_eg_label = st.selectbox(
            "Selecione o Empenho Global ou Crie um Novo",
            options=opt_eg,
            key="sb_eg",
        )

        if selected_eg_label == "[ + Criar Novo Empenho Global ]":
            with st.expander("📝 Formulário: Novo Empenho Global", expanded=True):
                with st.form("f_new_eg"):
                    next_eg_id = (
                        int(pd.to_numeric(df_eg["id"], errors="coerce").max() + 1)
                        if not df_eg.empty and "id" in df_eg.columns
                        else 1
                    )
                    st.number_input(
                        "ID do Empenho Global (Automático)",
                        value=next_eg_id,
                        disabled=True,
                    )
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
                            value=datetime.date.today(),
                            format="DD/MM/YYYY",
                        )
                    with col_eg2:
                        eg_end_d = st.date_input(
                            "Data Fim da Vigência",
                            value=datetime.date.today() + datetime.timedelta(days=365),
                            format="DD/MM/YYYY",
                        )

                    if st.form_submit_button("Salvar Novo Empenho Global"):
                        if not eg_number:
                            st.error("Informe o número do Empenho Global.")
                        else:
                            ws_eg.append_row([
                                next_eg_id,
                                selected_contract,
                                eg_number.strip(),
                                eg_val_input,
                                eg_start_d.strftime("%d/%m/%Y"),
                                eg_end_d.strftime("%d/%m/%Y"),
                                "FALSO",
                            ])
                            st.success(
                                f"Empenho Global **Nº {eg_number}** (ID #{next_eg_id}) criado com sucesso!"
                            )
                            refresh_caches()
                            st.rerun()
            st.stop()
        else:
            selected_eg_id = eg_options_map[selected_eg_label]
            eg_info = df_eg_contract[
                df_eg_contract["id"].astype(str) == selected_eg_id
            ].iloc[0]
            st.caption(
                f"💰 **Número:** {eg_info.get('number', '---')} | **Valor Teto:** R$ {clean_num_val(eg_info.get('value', 0)):,.2f} | **Status:** {'Cancelado' if str(eg_info.get('is_canceled')).upper() == 'VERDADEIRO' else 'Ativo'}"
            )

        st.markdown("---")

        # -------------------------------------------------------------------------
        # ETAPA 4: SELEÇÃO OU CRIAÇÃO DO SUB-EMPENHO
        # -------------------------------------------------------------------------
        st.markdown("##### 4️⃣ Sub-Empenho")
        df_sub_eg = (
            df_sub[df_sub["empenho_global_id"].astype(str) == str(selected_eg_id)]
            if not df_sub.empty and "empenho_global_id" in df_sub.columns
            else pd.DataFrame()
        )
        sub_list = (
            df_sub_eg["id"].astype(str).tolist() if not df_sub_eg.empty else []
        )
        opt_sub = ["[ + Criar Novo Sub-Empenho ]"] + sub_list

        selected_sub_opt = st.selectbox(
            "Selecione o Sub-Empenho ou Crie um Novo", options=opt_sub, key="sb_sub"
        )

        if selected_sub_opt == "[ + Criar Novo Sub-Empenho ]":
            if not df_sub_eg.empty:
                suggested_sub_id = (
                    int(pd.to_numeric(df_sub_eg["id"], errors="coerce").max() + 1)
                )
            else:
                try:
                    eg_num = int(selected_eg_id)
                    suggested_sub_id = eg_num * 100 + 1
                except ValueError:
                    suggested_sub_id = 101

            with st.expander("📝 Formulário: Novo Sub-Empenho", expanded=True):
                with st.form("f_new_sub"):
                    new_sub_id = st.number_input(
                        "ID do Sub-Empenho (editável se desejar pular número)",
                        value=suggested_sub_id,
                        step=1,
                    )
                    sub_ref_m = st.text_input("Mês de Referência (MM/YYYY)", "03/2026")
                    sub_val = st.number_input(
                        "Valor Sub-Empenhado (R$)", value=0.0, step=500.0
                    )

                    if st.form_submit_button("Salvar Novo Sub-Empenho"):
                        existing_sub_ids = (
                            df_sub["id"].astype(str).tolist()
                            if not df_sub.empty and "id" in df_sub.columns
                            else []
                        )
                        if str(new_sub_id) in existing_sub_ids:
                            st.error(
                                f"O ID de Sub-Empenho #{new_sub_id} já existe! Escolha outro número."
                            )
                        else:
                            ws_sub.append_row([
                                new_sub_id,
                                selected_eg_id,
                                sub_ref_m,
                                sub_val,
                            ])
                            st.success(
                                f"Sub-Empenho **#{new_sub_id}** salvo com sucesso!"
                            )
                            refresh_caches()
                            st.rerun()
            st.stop()
        else:
            selected_sub_id = selected_sub_opt
            sub_info = df_sub_eg[
                df_sub_eg["id"].astype(str) == selected_sub_id
            ].iloc[0]
            st.caption(
                f"📅 **Mês de Ref:** {sub_info.get('reference_month', '')} | **Valor:** R$ {clean_num_val(sub_info.get('value', 0)):,.2f}"
            )

        st.markdown("---")

        # -------------------------------------------------------------------------
        # ETAPA 5: LANÇAMENTO FINAL DO PAGAMENTO
        # -------------------------------------------------------------------------
        st.markdown("##### 5️⃣ Lançamento do Pagamento")

        next_pay_id = (
            int(pd.to_numeric(df_payments["id"], errors="coerce").max() + 1)
            if not df_payments.empty and "id" in df_payments.columns
            else 1001
        )

        ref_m_default = str(sub_info.get("reference_month", "03/2026"))
        val_default = clean_num_val(sub_info.get("value", 0.0))

        with st.form("f_create_payment"):
            st.number_input(
                "ID do Pagamento (Gerado Automático)", value=next_pay_id, disabled=True
            )
            ref_m = st.text_input("Mês de Referência", value=ref_m_default)
            p_exec_m = st.text_input("Mês de Execução do Pagamento", value=ref_m_default)
            regime_p = st.selectbox("Regime de Pagamento", ["Mensal", "Excepcional"])
            p_val = st.number_input(
                "Valor do Pagamento (R$)", value=val_default, step=100.0
            )
            init_st = st.selectbox("Status Inicial", STATUS_OPTIONS)
            obs = st.text_area("Observação / Histórico")

            if st.form_submit_button("💾 Finalizar Lançamento do Pagamento"):
                today_str = datetime.date.today().strftime("%d/%m/%Y")
                now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                ws_payments.append_row([
                    next_pay_id,
                    selected_sub_id,
                    selected_cnpj,
                    selected_contract,
                    ref_m,
                    p_exec_m,
                    regime_p,
                    p_val,
                    today_str if init_st == "PAGO" else "",
                    init_st,
                ])

                ws_history.append_row([
                    len(ws_history.get_all_values()) + 1,
                    next_pay_id,
                    selected_contract,
                    "N/A",
                    selected_sub_id,
                    "NOVO_REGISTRO",
                    init_st,
                    now_str,
                    st.session_state.user,
                    f"Criação: {obs}",
                ])

                st.success(
                    f"✅ Pagamento **#{next_pay_id}** registrado com sucesso para o mês {ref_m}!"
                )
                refresh_caches()
                st.rerun()

    # =========================================================================
    # TAB 2: LISTAR TABELAS
    # =========================================================================
    with t_read:
        st.subheader("📋 Visualização Geral do Banco de Dados")
        sel_view = st.radio(
            "Selecione a Tabela",
            [
                "Pagamentos",
                "Sub-Empenhos",
                "Empenhos Globais",
                "Contratos",
                "Empresas",
            ],
            horizontal=True,
        )

        if sel_view == "Pagamentos":
            st.dataframe(df_payments, use_container_width=True)
        elif sel_view == "Sub-Empenhos":
            st.dataframe(df_sub, use_container_width=True)
        elif sel_view == "Empenhos Globais":
            st.dataframe(df_eg, use_container_width=True)
        elif sel_view == "Contratos":
            st.dataframe(df_contracts, use_container_width=True)
        elif sel_view == "Empresas":
            st.dataframe(df_company, use_container_width=True)

    # =========================================================================
    # TAB 3: ATUALIZAR STATUS DO PAGAMENTO
    # =========================================================================
    with t_update:
        st.subheader("✏️ Alterar Etapa / Status do Pagamento")
        if not df_payments.empty and "id" in df_payments.columns:
            p_id = st.selectbox(
                "Selecione o Lançamento (ID)",
                df_payments["id"].tolist(),
                key="sb_upd_id",
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

                default_val = clean_num_val(curr.get("paid_amount", 0.0))
                paid_val_input = st.number_input(
                    "Valor Efetivado (R$)", value=default_val, step=100.0
                )
                obs_up = st.text_area("Motivo da Mudança de Etapa")

                if st.form_submit_button("Gravar Alteração de Status"):
                    cell = ws_payments.find(str(p_id))
                    row_idx = cell.row

                    today_str = datetime.date.today().strftime("%d/%m/%Y")
                    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                    if next_st == "PAGO":
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
                        now_str,
                        st.session_state.user,
                        obs_up,
                    ])

                    st.success(
                        f"Pagamento #{p_id} atualizado com sucesso para **{next_st}**!"
                    )
                    refresh_caches()
                    st.rerun()

    # =========================================================================
    # TAB 4: EXCLUIR REGISTRO
    # =========================================================================
    with t_delete:
        st.subheader("🗑️ Excluir Registro de Pagamento")
        if not df_payments.empty and "id" in df_payments.columns:
            del_id = st.selectbox(
                "ID do Lançamento para Excluir",
                df_payments["id"].tolist(),
                key="sb_del_id",
            )
            if st.button("Confirmar Exclusão Permanente", type="primary"):
                cell = ws_payments.find(str(del_id))
                ws_payments.delete_rows(cell.row)

                now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                ws_history.append_row([
                    len(ws_history.get_all_values()) + 1,
                    del_id,
                    "N/A",
                    "N/A",
                    "N/A",
                    "DELETADO",
                    "DELETADO",
                    now_str,
                    st.session_state.user,
                    "Registro removido via sistema",
                ])
                st.success("Lançamento removido permanentemente!")
                refresh_caches()
                st.rerun()

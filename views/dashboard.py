# views/dashboard.py
import pandas as pd
import streamlit as st
from database import load_table


def clean_num(series):
    """Converte valores monetários/texto (PT-BR) em float puro."""
    if series is None or series.empty:
        return pd.Series(dtype=float)
    s = series.astype(str).str.strip()
    has_comma = s.str.contains(",", regex=False)
    s_cleaned = s.copy()
    s_cleaned[has_comma] = (
        s[has_comma]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(s_cleaned, errors="coerce").fillna(0.0)


def format_brl(val):
    """Formata número no padrão monetário brasileiro R$ X.XXX,XX."""
    return f"R$ {val:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")


def render_dashboard():
    st.title("📊 Painel Geral de Contratos e Pagamentos")

    # Carregamento das Tabelas
    df_contracts, _ = load_table("CONTRACT")
    df_payments, _ = load_table("PAGAMENTOS")
    df_sub, _ = load_table("SUB_EMPENHO")
    df_eg, _ = load_table("EMPENHO_GLOBAL")
    df_company, _ = load_table("COMPANY")

    # Mapeamento de CNPJ para Nome da Empresa (Razão Social)
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

    # --- FILTROS DE TOPO ---
    c1, c2 = st.columns(2)
    ano_selected = c1.selectbox("Ano Exercício", [2026, 2025, 2024], index=0)

    options_emp = (
        list(df_contracts["company_cnpj"].dropna().unique())
        if not df_contracts.empty
        else []
    )

    def format_emp_option(cnpj):
        name = cnpj_to_name.get(str(cnpj).strip())
        return f"{name} ({cnpj})" if name else str(cnpj)

    emp_selected = c2.multiselect(
        "Filtrar por Empresa",
        options=options_emp,
        format_func=format_emp_option,
        placeholder="Selecione uma ou mais empresas (vazio = TODAS)",
    )

    # 1. Aplica filtro de empresas selecionadas em df_contracts
    if emp_selected:
        df_contracts = df_contracts[
            df_contracts["company_cnpj"].isin(emp_selected)
        ]

    # 2. Cascata de filtros: Sincroniza pagamentos, empenho global e sub-empenho
    active_contracts = (
        df_contracts["contract_number"].tolist()
        if not df_contracts.empty
        else []
    )

    if not df_payments.empty:
        df_payments = df_payments[
            df_payments["contract_number"].isin(active_contracts)
        ]
        df_payments["paid_num"] = clean_num(df_payments["paid_amount"])
    else:
        df_payments["paid_num"] = 0.0

    if not df_eg.empty:
        df_eg = df_eg[df_eg["contract_number"].isin(active_contracts)]
        df_eg["val_num"] = clean_num(df_eg["value"])
    else:
        df_eg["val_num"] = 0.0

    if not df_sub.empty and not df_eg.empty:
        df_sub = df_sub[
            df_sub["empenho_global_id"]
            .astype(str)
            .isin(df_eg["id"].astype(str))
        ]
        df_sub["val_num"] = clean_num(df_sub["value"])
    else:
        df_sub["val_num"] = 0.0

    # --- KPIS PRINCIPAIS ---
    pago_mask = df_payments["current_status"] == "PAGO"
    df_pago = df_payments[pago_mask]
    total_pago = df_pago["paid_num"].sum() if not df_pago.empty else 0.0

    # Média Mensal Paga calculada pela quantidade de meses efetivamente quitados
    qtd_meses_pagos = (
        df_pago["reference_month"].nunique() if not df_pago.empty else 0
    )
    media_mensal = (
        (total_pago / qtd_meses_pagos) if qtd_meses_pagos > 0 else 0.0
    )

    total_sub_empenhado = df_sub["val_num"].sum() if not df_sub.empty else 0.0
    pendencias_count = (
        len(df_payments[~pago_mask]) if not df_payments.empty else 0
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Pago (Quitado)", format_brl(total_pago))
    k2.metric("Total Sub-Empenhado", format_brl(total_sub_empenhado))
    k3.metric("Média Mensal Paga", format_brl(media_mensal))
    k4.metric("Lançamentos Pendentes", pendencias_count)

    st.markdown("---")

    # --- ANÁLISE DETALHADA DE EMPENHO POR CONTRATO ---
    st.subheader("🎯 Execução Orçamentária por Contrato")
    if not df_contracts.empty:
        ctr_list = df_contracts["contract_number"].tolist()
        selected_ctr = st.selectbox(
            "Selecione um Contrato para Detalhamento", ctr_list
        )

        eg_match = (
            df_eg[df_eg["contract_number"] == selected_ctr]
            if not df_eg.empty
            else pd.DataFrame()
        )
        val_eg = eg_match["val_num"].sum() if not eg_match.empty else 0.0

        if not eg_match.empty and not df_sub.empty:
            sub_match = df_sub[
                df_sub["empenho_global_id"].isin(eg_match["id"].astype(str))
            ]
            val_sub = sub_match["val_num"].sum()
        else:
            val_sub = 0.0

        saldo_restante = max(0.0, val_eg - val_sub)
        pct_exec = (val_sub / val_eg * 100) if val_eg > 0 else 0.0

        m_eg1, m_eg2, m_eg3 = st.columns(3)
        m_eg1.metric("Empenho Global Teto", format_brl(val_eg))
        m_eg2.metric("Total Sub-Empenhado", format_brl(val_sub))
        m_eg3.metric(
            "Saldo A Empenhar",
            format_brl(saldo_restante),
            delta=f"{pct_exec:.1f}% Usado".replace(".", ","),
        )

        st.progress(min(1.0, pct_exec / 100))

        if val_eg > 0:
            df_pie = pd.DataFrame({
                "Categoria": ["Sub-Empenhado", "Saldo Livre"],
                "Valor": [val_sub, saldo_restante],
            })
            st.bar_chart(df_pie.set_index("Categoria"))
    else:
        st.info("Nenhum contrato disponível para os filtros selecionados.")

    st.markdown("---")

    # --- GRÁFICO DE LINHA: EVOLUÇÃO MÊS A MÊS POR EMPRESA ---
    st.subheader(f"📈 Linha do Tempo: Evolução dos Pagamentos {ano_selected}")
    meses_cods = [f"{m:02d}/{ano_selected}" for m in range(1, 13)]
    meses_names = [
        "JAN",
        "FEV",
        "MAR",
        "ABR",
        "MAI",
        "JUN",
        "JUL",
        "AGO",
        "SET",
        "OUT",
        "NOV",
        "DEZ",
    ]

    if not df_payments.empty and not df_contracts.empty:
        df_pago_ano = df_payments[pago_mask].copy()
        df_pago_ano["ref_m_clean"] = (
            df_pago_ano["reference_month"]
            .astype(str)
            .str.strip()
            .str.replace("-", "/", regex=False)
        )

        empresas_ativas = df_contracts["company_cnpj"].dropna().unique()
        chart_data = pd.DataFrame({"Mês": meses_names})
        company_cols = []

        for emp in empresas_ativas:
            emp_clean = str(emp).strip()
            emp_name = cnpj_to_name.get(emp_clean, emp_clean)
            col_label = emp_name

            ctrs_emp = df_contracts[
                df_contracts["company_cnpj"].astype(str).str.strip()
                == emp_clean
            ]["contract_number"].tolist()
            vals_mes = []

            for m_code in meses_cods:
                m_month_num, m_year = m_code.split("/")
                m_code_no_zero = f"{int(m_month_num)}/{m_year}"

                v = df_pago_ano[
                    (df_pago_ano["contract_number"].isin(ctrs_emp))
                    & (
                        df_pago_ano["ref_m_clean"].isin(
                            [m_code, m_code_no_zero]
                        )
                    )
                ]["paid_num"].sum()
                vals_mes.append(v)

            chart_data[col_label] = vals_mes
            company_cols.append(col_label)

        # Força a ordem cronológica (JAN -> DEZ)
        chart_data["Mês"] = pd.Categorical(
            chart_data["Mês"], categories=meses_names, ordered=True
        )
        chart_data = chart_data.sort_values("Mês")

        # Filtra meses sem dados (remove meses futuros/sem pagamentos)
        if company_cols:
            chart_data["total_mes"] = chart_data[company_cols].sum(axis=1)
            chart_data = chart_data[chart_data["total_mes"] > 0].drop(
                columns=["total_mes"]
            )

        if not chart_data.empty and company_cols:
            st.line_chart(chart_data, x="Mês")
        else:
            st.info("Sem pagamentos realizados para o período selecionado.")
    else:
        st.info("Sem dados de pagamentos para os contratos selecionados.")

    st.markdown("---")

    # --- MATRIZ VISUAL MÊS A MÊS ---
    st.subheader("📋 Matriz de Status (JAN - DEZ)")
    matrix_data = []

    if not df_payments.empty and "reference_month" in df_payments.columns:
        df_payments_norm = df_payments.copy()
        df_payments_norm["ref_m_clean"] = (
            df_payments_norm["reference_month"]
            .astype(str)
            .str.strip()
            .str.replace("-", "/", regex=False)
        )
    else:
        df_payments_norm = pd.DataFrame()

    for _, ctr in df_contracts.iterrows():
        ctr_num = str(ctr["contract_number"]).strip()
        emp_cnpj = str(ctr["company_cnpj"]).strip()
        emp_display = cnpj_to_name.get(emp_cnpj, emp_cnpj)

        row = {
            "Contrato": ctr_num,
            "Empresa": emp_display,
        }

        for idx, m_code in enumerate(meses_cods):
            m_name = meses_names[idx]
            m_month_num, m_year = m_code.split("/")
            m_code_no_zero = f"{int(m_month_num)}/{m_year}"

            if not df_payments_norm.empty:
                match = df_payments_norm[
                    (
                        df_payments_norm["contract_number"]
                        .astype(str)
                        .str.strip()
                        == ctr_num
                    )
                    & (
                        df_payments_norm["ref_m_clean"].isin(
                            [m_code, m_code_no_zero]
                        )
                    )
                ]
            else:
                match = pd.DataFrame()

            if not match.empty:
                st_val = match.iloc[0]["current_status"]
                row[m_name] = "OK" if st_val == "PAGO" else st_val
            else:
                row[m_name] = "---"

        matrix_data.append(row)

    df_matrix = pd.DataFrame(matrix_data)

    def style_status(val):
        if val == "OK":
            return (
                "background-color: #15803d; color: white; font-weight: bold;"
                " text-align: center;"
            )
        elif val == "---":
            return (
                "background-color: #cbd5e1; color: #475569; text-align:"
                " center;"
            )
        elif val != "":
            return (
                "background-color: #fef08a; color: #854d0e; font-weight: bold;"
                " text-align: center;"
            )
        return ""

    if not df_matrix.empty:
        st.dataframe(
            df_matrix.style.map(style_status, subset=meses_names),
            use_container_width=True,
            height=400,
        )
    else:
        st.info("Nenhum contrato encontrado para os filtros selecionados.")

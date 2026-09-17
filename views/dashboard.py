# views/dashboard.py
import pandas as pd
import streamlit as st
from database import load_table
from pdf_generator import format_brl, generate_pdf_report


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


def render_dashboard():
    # Carregamento das Tabelas
    df_contracts, _ = load_table("CONTRACT")
    df_payments, _ = load_table("PAGAMENTOS")
    df_sub, _ = load_table("SUB_EMPENHO")
    df_eg, _ = load_table("EMPENHO_GLOBAL")
    df_company, _ = load_table("COMPANY")

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

    # --- FILTROS DE TOPO ---
    c_ano, c_emp = st.columns(2)
    ano_selected = c_ano.selectbox("Ano Exercício", [2026, 2025, 2024], index=0)

    options_emp = (
        list(df_contracts["company_cnpj"].dropna().unique())
        if not df_contracts.empty
        else []
    )

    def format_emp_option(cnpj):
        name = cnpj_to_name.get(str(cnpj).strip())
        return f"{name} ({cnpj})" if name else str(cnpj)

    emp_selected = c_emp.multiselect(
        "Filtrar por Empresa",
        options=options_emp,
        format_func=format_emp_option,
        placeholder="Selecione uma ou mais empresas (vazio = TODAS)",
    )

    # Cascata de Filtros
    if emp_selected:
        df_contracts_sub = df_contracts[
            df_contracts["company_cnpj"].isin(emp_selected)
        ]
        nomes_sel = [
            cnpj_to_name.get(str(c).strip(), str(c)) for c in emp_selected
        ]
        empresas_header_str = ", ".join(nomes_sel)
    else:
        df_contracts_sub = df_contracts.copy()
        empresas_header_str = "TODAS AS EMPRESAS"

    active_contracts = (
        df_contracts_sub["contract_number"].tolist()
        if not df_contracts_sub.empty
        else []
    )

    if not df_payments.empty:
        df_payments_sub = df_payments[
            df_payments["contract_number"].isin(active_contracts)
        ].copy()
        df_payments_sub["paid_num"] = clean_num(df_payments_sub["paid_amount"])
    else:
        df_payments_sub = pd.DataFrame()

    if not df_eg.empty:
        df_eg_sub = df_eg[df_eg["contract_number"].isin(active_contracts)]
        df_eg_sub["val_num"] = clean_num(df_eg_sub["value"])
    else:
        df_eg_sub = pd.DataFrame()

    if not df_sub.empty and not df_eg_sub.empty:
        df_sub_sub = df_sub[
            df_sub["empenho_global_id"]
            .astype(str)
            .isin(df_eg_sub["id"].astype(str))
        ]
        df_sub_sub["val_num"] = clean_num(df_sub_sub["value"])
    else:
        df_sub_sub = pd.DataFrame()

    # Monta dados para o gráfico de evolução (usado na tela e no PDF)
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
    chart_data = pd.DataFrame({"Mês": meses_names})

    if not df_payments_sub.empty and not df_contracts_sub.empty:
        pago_mask = df_payments_sub["current_status"] == "PAGO"
        df_pago_ano = df_payments_sub[pago_mask].copy()
        df_pago_ano["ref_m_clean"] = (
            df_pago_ano["reference_month"]
            .astype(str)
            .str.strip()
            .str.replace("-", "/", regex=False)
        )

        empresas_ativas = df_contracts_sub["company_cnpj"].dropna().unique()
        company_cols = []

        for emp in empresas_ativas:
            emp_clean = str(emp).strip()
            emp_name = cnpj_to_name.get(emp_clean, emp_clean)

            ctrs_emp = df_contracts_sub[
                df_contracts_sub["company_cnpj"].astype(str).str.strip()
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

            chart_data[emp_name] = vals_mes
            company_cols.append(emp_name)

        chart_data["Mês"] = pd.Categorical(
            chart_data["Mês"], categories=meses_names, ordered=True
        )
        chart_data = chart_data.sort_values("Mês")

        if company_cols:
            chart_data["total_mes"] = chart_data[company_cols].sum(axis=1)
            chart_data = chart_data[chart_data["total_mes"] > 0].drop(
                columns=["total_mes"]
            )

    # --- CABEÇALHO DO DASHBOARD + BOTÃO NO CANTO SUPERIOR ---
    title_col, btn_col = st.columns([3, 1])
    with title_col:
        st.title("📊 Painel Geral de Contratos e Pagamentos")

    with btn_col:
        st.write("")  # Espaçamento vertical
        pdf_bytes = generate_pdf_report(
            empresas_header_str,
            df_payments_sub,
            df_contracts_sub,
            ano_selected,
            chart_data,
        )
        st.download_button(
            label="📄 Baixar PDF",
            data=pdf_bytes,
            file_name=f"Relatorio_{ano_selected}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    # --- KPIS PRINCIPAIS ---
    if not df_payments_sub.empty:
        pago_mask = df_payments_sub["current_status"] == "PAGO"
        df_pago = df_payments_sub[pago_mask]
        total_pago = df_pago["paid_num"].sum() if not df_pago.empty else 0.0
        qtd_meses_pagos = (
            df_pago["reference_month"].nunique() if not df_pago.empty else 0
        )
        media_mensal = (
            (total_pago / qtd_meses_pagos) if qtd_meses_pagos > 0 else 0.0
        )
        pendencias_count = len(df_payments_sub[~pago_mask])
    else:
        total_pago, media_mensal, pendencias_count = 0.0, 0.0, 0

    total_sub_empenhado = (
        df_sub_sub["val_num"].sum() if not df_sub_sub.empty else 0.0
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Pago (Quitado)", format_brl(total_pago))
    k2.metric("Total Sub-Empenhado", format_brl(total_sub_empenhado))
    k3.metric("Média Mensal Paga", format_brl(media_mensal))
    k4.metric("Lançamentos Pendentes", pendencias_count)

    st.markdown("---")

    # --- ANÁLISE DETALHADA DE EMPENHO POR CONTRATO ---
    st.subheader("🎯 Execução Orçamentária por Contrato")
    if not df_contracts_sub.empty:
        ctr_list = df_contracts_sub["contract_number"].tolist()
        selected_ctr = st.selectbox(
            "Selecione um Contrato para Detalhamento", ctr_list
        )

        eg_match = (
            df_eg_sub[df_eg_sub["contract_number"] == selected_ctr]
            if not df_eg_sub.empty
            else pd.DataFrame()
        )
        val_eg = eg_match["val_num"].sum() if not eg_match.empty else 0.0

        if not eg_match.empty and not df_sub_sub.empty:
            sub_match = df_sub_sub[
                df_sub_sub["empenho_global_id"].isin(eg_match["id"].astype(str))
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

    # --- GRÁFICO DE LINHA: EVOLUÇÃO MÊS A MÊS ---
    st.subheader(f"📈 Linha do Tempo: Evolução dos Pagamentos {ano_selected}")
    if not chart_data.empty and len(chart_data.columns) > 1:
        st.line_chart(chart_data, x="Mês")
    else:
        st.info("Sem pagamentos realizados para o período selecionado.")

    st.markdown("---")

    # --- MATRIZ VISUAL MÊS A MÊS ---
    st.subheader("📋 Matriz de Status (JAN - DEZ)")
    matrix_data = []

    if not df_payments_sub.empty and "reference_month" in df_payments_sub.columns:
        df_payments_norm = df_payments_sub.copy()
        df_payments_norm["ref_m_clean"] = (
            df_payments_norm["reference_month"]
            .astype(str)
            .str.strip()
            .str.replace("-", "/", regex=False)
        )
    else:
        df_payments_norm = pd.DataFrame()

    for _, ctr in df_contracts_sub.iterrows():
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

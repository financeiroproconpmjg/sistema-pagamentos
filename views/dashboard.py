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


def render_dashboard():
    st.title("📊 Painel Geral de Contratos e Pagamentos")

    # Carregamento das Tabelas
    df_contracts, _ = load_table("CONTRACT")
    df_payments, _ = load_table("PAGAMENTOS")
    df_sub, _ = load_table("SUB_EMPENHO")
    df_eg, _ = load_table("EMPENHO_GLOBAL")

    # --- FILTROS DE TOPO ---
    c1, c2 = st.columns(2)
    ano_selected = c1.selectbox("Ano Exercício", [2026, 2025, 2024], index=0)

    options_emp = (
        list(df_contracts["company_cnpj"].dropna().unique())
        if not df_contracts.empty
        else []
    )
    emp_selected = c2.multiselect(
        "Filtrar por Empresa (CNPJ)",
        options=options_emp,
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
            df_sub["empenho_global_id"].astype(str).isin(df_eg["id"].astype(str))
        ]
        df_sub["val_num"] = clean_num(df_sub["value"])
    else:
        df_sub["val_num"] = 0.0

    # --- KPIS PRINCIPAIS (AGORA 100% SINCRONIZADOS COM O FILTRO) ---
    pago_mask = df_payments["current_status"] == "PAGO"
    total_pago = df_payments[pago_mask]["paid_num"].sum()
    media_mensal = total_pago / 12

    total_sub_empenhado = df_sub["val_num"].sum()
    pendencias_count = (
        len(df_payments[~pago_mask]) if not df_payments.empty else 0
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Pago (Quitado)", f"R$ {total_pago:,.2f}")
    k2.metric("Total Sub-Empenhado", f"R$ {total_sub_empenhado:,.2f}")
    k3.metric("Média Mensal Paga", f"R$ {media_mensal:,.2f}")
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
        m_eg1.metric("Empenho Global Teto", f"R$ {val_eg:,.2f}")
        m_eg2.metric("Total Sub-Empenhado", f"R$ {val_sub:,.2f}")
        m_eg3.metric(
            "Saldo A Empenhar",
            f"R$ {saldo_restante:,.2f}",
            delta=f"{pct_exec:.1f}% Usado",
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
    st.subheader("📈 Linha do Tempo: Evolução dos Pagamentos (JAN - DEZ)")
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
        chart_data = pd.DataFrame({"Mês": meses_names})

        for ctr in df_contracts["contract_number"].unique():
            vals_mes = []
            for m_code in meses_cods:
                v = df_pago_ano[
                    (df_pago_ano["contract_number"] == ctr)
                    & (df_pago_ano["reference_month"] == m_code)
                ]["paid_num"].sum()
                vals_mes.append(v)
            chart_data[ctr] = vals_mes

        chart_data.set_index("Mês", inplace=True)
        st.line_chart(chart_data)
    else:
        st.info("Sem dados de pagamentos para os contratos selecionados.")

    st.markdown("---")

    # --- MATRIZ VISUAL MÊS A MÊS ---
    st.subheader("📋 Matriz de Status (JAN - DEZ)")
    matrix_data = []
    for _, ctr in df_contracts.iterrows():
        row = {
            "Contrato": ctr["contract_number"],
            "Empresa": ctr["company_cnpj"],
        }
        for idx, m_code in enumerate(meses_cods):
            m_name = meses_names[idx]
            match = df_payments[
                (df_payments["contract_number"] == ctr["contract_number"])
                & (df_payments["reference_month"] == m_code)
            ]
            if not match.empty:
                st_val = match.iloc[0]["current_status"]
                row[m_name] = "OK" if st_val == "PAGO" else st_val
            else:
                row[m_name] = "---"
        matrix_data.append(row)

    df_matrix = pd.DataFrame(matrix_data)

    def style_status(val):
        if val == "OK":
            return "background-color: #15803d; color: white; font-weight: bold; text-align: center;"
        elif val == "---":
            return "background-color: #cbd5e1; color: #475569; text-align: center;"
        elif val != "":
            return "background-color: #fef08a; color: #854d0e; font-weight: bold; text-align: center;"
        return ""

    if not df_matrix.empty:
        st.dataframe(
            df_matrix.style.map(style_status, subset=meses_names),
            use_container_width=True,
            height=400,
        )
    else:
        st.info("Nenhum contrato encontrado para os filtros selecionados.")

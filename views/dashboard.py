import pandas as pd
import streamlit as st
from database import load_table


def render_dashboard():
    st.title("Painel Geral de Contratos e Pagamentos")

    df_contracts, _ = load_table("CONTRACT")
    df_payments, _ = load_table("PAGAMENTOS")

    c1, c2 = st.columns(2)
    ano_selected = c1.selectbox("Ano Exercício", [2026, 2025, 2024], index=0)
    list_emp = (
        ["TODAS"] + list(df_contracts["company_cnpj"].unique())
        if not df_contracts.empty
        else ["TODAS"]
    )
    emp_selected = c2.selectbox("Filtrar por Empresa (CNPJ)", list_emp)

    if emp_selected != "TODAS":
        df_contracts = df_contracts[
            df_contracts["company_cnpj"] == emp_selected
        ]

    if not df_payments.empty:
        pago_series = df_payments[df_payments["current_status"] == "PAGO"][
            "paid_amount"
        ]
        pago_series_cleaned = (
            pago_series.astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        total_pago = (
            pd.to_numeric(pago_series_cleaned, errors="coerce")
            .fillna(0.0)
            .sum()
        )
        media_mensal = total_pago / 12
    else:
        total_pago, media_mensal = 0.0, 0.0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Pago no Ano", f"R$ {total_pago:,.2f}")
    k2.metric("Média Mensal Paga", f"R$ {media_mensal:,.2f}")
    k3.metric("Contratos Monitorados", len(df_contracts))

    st.markdown("---")
    st.subheader("Acompanhamento Mês a Mês (JAN - DEZ)")

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
            df_matrix.style.applymap(style_status, subset=meses_names),
            use_container_width=True,
            height=400,
        )
    else:
        st.info("Nenhum contrato cadastrado para exibição.")

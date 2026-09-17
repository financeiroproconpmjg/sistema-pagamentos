import io
import pandas as pd
import streamlit as st
from database import load_table


def clean_num(series):
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
    return f"R$ {val:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")


def render_reports():
    st.title("📄 Central de Relatórios e Exportação")

    df_contracts, _ = load_table("CONTRACT")
    df_payments, _ = load_table("PAGAMENTOS")
    df_sub, _ = load_table("SUB_EMPENHO")
    df_eg, _ = load_table("EMPENHO_GLOBAL")
    df_company, _ = load_table("COMPANY")

    if df_contracts.empty:
        st.info("Nenhum contrato cadastrado para geração de relatórios.")
        return

    # Mapeamento CNPJ -> Nome da Empresa
    cnpj_to_name = {}
    if not df_company.empty:
        for _, r in df_company.iterrows():
            c_val = str(r.get("cnpj", r.get("company_cnpj", ""))).strip()
            n_val = str(
                r.get("company_name", r.get("razao_social", ""))
            ).strip()
            if c_val and n_val:
                cnpj_to_name[c_val] = n_val

    # Filtros do Relatório
    col1, col2 = st.columns(2)
    emp_list = list(df_contracts["company_cnpj"].dropna().unique())

    def format_emp(cnpj):
        nome = cnpj_to_name.get(str(cnpj).strip())
        return f"{nome} ({cnpj})" if nome else str(cnpj)

    emp_sel = col1.selectbox(
        "Selecione a Empresa", options=emp_list, format_func=format_emp
    )
    ano_sel = col2.selectbox("Ano Exercício", [2026, 2025, 2024], index=0)

    # Filtragem dos Dados da Empresa
    emp_clean = str(emp_sel).strip()
    emp_nome = cnpj_to_name.get(emp_clean, emp_clean)

    ctrs_emp = df_contracts[
        df_contracts["company_cnpj"].astype(str).str.strip() == emp_clean
    ]["contract_number"].tolist()

    df_pay_exp = (
        df_payments[df_payments["contract_number"].isin(ctrs_emp)].copy()
        if not df_payments.empty
        else pd.DataFrame()
    )

    if not df_pay_exp.empty:
        df_pay_exp["paid_num"] = clean_num(df_pay_exp["paid_amount"])

    # Pré-visualização na tela
    st.markdown("---")
    st.subheader(f"Prévia do Relatório — {emp_nome}")

    pago_mask = (
        (df_pay_exp["current_status"] == "PAGO")
        if not df_pay_exp.empty
        else pd.Series()
    )
    tot_pago = (
        df_pay_exp[pago_mask]["paid_num"].sum() if not df_pay_exp.empty else 0.0
    )

    m1, m2 = st.columns(2)
    m1.metric("Total de Lançamentos", len(df_pay_exp))
    m2.metric("Total Quitado no Período", format_brl(tot_pago))

    if not df_pay_exp.empty:
        st.dataframe(
            df_pay_exp[[
                "id",
                "contract_number",
                "reference_month",
                "paid_amount",
                "payment_date",
                "current_status",
            ]],
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("📥 Opções de Download")

    col_down1, col_down2 = st.columns(2)

    # Exportação em CSV
    if not df_pay_exp.empty:
        csv_data = df_pay_exp.to_csv(index=False).encode("utf-8")
        col_down1.download_button(
            label="📄 Baixar Relatório em CSV",
            data=csv_data,
            file_name=f"Relatorio_{emp_clean}_{ano_sel}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Exportação em Excel (Multi-abas)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_contracts[
            df_contracts["company_cnpj"].astype(str).str.strip() == emp_clean
        ].to_excel(writer, sheet_name="Contratos", index=False)
        if not df_pay_exp.empty:
            df_pay_exp.to_excel(writer, sheet_name="Pagamentos", index=False)
    buffer.seek(0)

    col_down2.download_button(
        label="📊 Baixar Relatório em Excel (.xlsx)",
        data=buffer,
        file_name=f"Relatorio_{emp_clean}_{ano_sel}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

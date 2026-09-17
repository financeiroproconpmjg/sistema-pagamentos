# views/reports.py
import io
from fpdf import FPDF
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


def safe_str(txt):
  """Remove caracteres incompatíveis com a fonte padrão do PDF."""
  if txt is None:
    return ""
  s = str(txt)
  return s.encode("latin-1", "replace").decode("latin-1")


def generate_pdf_report(
    empresas_str, df_payments_sub, df_contracts_sub, ano_sel
):
  """Gera o documento PDF na memória e retorna em bytes."""
  pdf = FPDF()
  pdf.add_page()
  pdf.set_auto_page_break(auto=True, margin=15)

  # --- CABEÇALHO DO RELATÓRIO ---
  pdf.set_font("Helvetica", "B", 16)
  pdf.cell(
      0,
      10,
      safe_str(f"RELATÓRIO EXECUTIVO DE PAGAMENTOS — {ano_sel}"),
      ln=True,
      align="C",
  )

  pdf.set_font("Helvetica", "", 10)
  pdf.cell(
      0, 6, safe_str(f"Empresa(s): {empresas_str}"), ln=True, align="C"
  )
  pdf.ln(6)

  # --- RESUMO FINANCEIRO (KPIS) ---
  pago_mask = (
      (df_payments_sub["current_status"] == "PAGO")
      if not df_payments_sub.empty
      else pd.Series()
  )
  df_pago = (
      df_payments_sub[pago_mask] if not df_payments_sub.empty else pd.DataFrame()
  )
  tot_pago = df_pago["paid_num"].sum() if not df_pago.empty else 0.0
  tot_lanctos = len(df_payments_sub) if not df_payments_sub.empty else 0

  pdf.set_font("Helvetica", "B", 12)
  pdf.cell(0, 8, safe_str("1. Resumo Orçamentário"), ln=True)

  pdf.set_font("Helvetica", "", 10)
  pdf.cell(
      0,
      6,
      safe_str(f"• Total de Contratos Monitorados: {len(df_contracts_sub)}"),
      ln=True,
  )
  pdf.cell(
      0, 6, safe_str(f"• Total de Lançamentos Registrados: {tot_lanctos}"), ln=True
  )
  pdf.cell(
      0, 6, safe_str(f"• Total Pago/Quitado: {format_brl(tot_pago)}"), ln=True
  )
  pdf.ln(6)

  # --- TABELA DE DETALHAMENTO ---
  pdf.set_font("Helvetica", "B", 12)
  pdf.cell(0, 8, safe_str("2. Detalhamento dos Pagamentos"), ln=True)

  # Cabeçalho da Tabela
  pdf.set_font("Helvetica", "B", 9)
  pdf.cell(35, 7, safe_str("Contrato"), border=1, align="C")
  pdf.cell(25, 7, safe_str("Mês Ref."), border=1, align="C")
  pdf.cell(35, 7, safe_str("Valor (R$)"), border=1, align="C")
  pdf.cell(30, 7, safe_str("Data Pgto"), border=1, align="C")
  pdf.cell(65, 7, safe_str("Status Atual"), border=1, align="C", ln=True)

  # Linhas dos Dados
  pdf.set_font("Helvetica", "", 8)
  if not df_payments_sub.empty:
    for _, r in df_payments_sub.iterrows():
      ctr = safe_str(r.get("contract_number", "---"))
      m_ref = safe_str(r.get("reference_month", "---"))
      v_pago = format_brl(r.get("paid_num", 0.0))
      dt_pago = safe_str(r.get("payment_date", "---"))
      st_val = safe_str(r.get("current_status", "---"))

      pdf.cell(35, 6, ctr, border=1)
      pdf.cell(25, 6, m_ref, border=1, align="C")
      pdf.cell(35, 6, safe_str(v_pago), border=1, align="R")
      pdf.cell(30, 6, dt_pago, border=1, align="C")
      pdf.cell(65, 6, st_val, border=1, ln=True)
  else:
    pdf.cell(
        190,
        6,
        safe_str("Nenhum lançamento encontrado para os filtros."),
        border=1,
        align="C",
        ln=True,
    )

  return bytes(pdf.output())


def render_reports():
  st.title("📄 Central de Relatórios e Exportação")

  df_contracts, _ = load_table("CONTRACT")
  df_payments, _ = load_table("PAGAMENTOS")
  df_company, _ = load_table("COMPANY")

  if df_contracts.empty:
    st.info("Nenhum contrato cadastrado para geração de relatórios.")
    return

  # Mapeamento CNPJ -> Nome da Empresa (Razão Social)
  cnpj_to_name = {}
  if not df_company.empty:
    cnpj_col = next(
        (c for c in ["cnpj", "company_cnpj"] if c in df_company.columns), None
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

  # --- FILTROS DE RELATÓRIO ---
  col1, col2 = st.columns(2)
  ano_sel = col1.selectbox("Ano Exercício", [2026, 2025, 2024], index=0)

  options_emp = list(df_contracts["company_cnpj"].dropna().unique())

  def format_emp_option(cnpj):
    name = cnpj_to_name.get(str(cnpj).strip())
    return f"{name} ({cnpj})" if name else str(cnpj)

  emp_selected = col2.multiselect(
      "Selecione a(s) Empresa(s)",
      options=options_emp,
      format_func=format_emp_option,
      placeholder="Selecione uma ou mais empresas (vazio = TODAS)",
  )

  # Filtragem dos Contratos
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

  # Filtragem dos Pagamentos
  if not df_payments.empty:
    df_pay_sub = df_payments[
        df_payments["contract_number"].isin(active_contracts)
    ].copy()
    df_pay_sub["paid_num"] = clean_num(df_pay_sub["paid_amount"])
  else:
    df_pay_sub = pd.DataFrame()

  # --- PRÉ-VISUALIZAÇÃO ---
  st.markdown("---")
  st.subheader(f"📊 Prévia do Relatório — {empresas_header_str}")

  pago_mask = (
      (df_pay_sub["current_status"] == "PAGO")
      if not df_pay_sub.empty
      else pd.Series()
  )
  tot_pago = df_pay_sub[pago_mask]["paid_num"].sum() if not df_pay_sub.empty else 0.0

  m1, m2 = st.columns(2)
  m1.metric("Lançamentos Encontrados", len(df_pay_sub))
  m2.metric("Total Pago Quitado", format_brl(tot_pago))

  if not df_pay_sub.empty:
    st.dataframe(
        df_pay_sub[[
            "id",
            "contract_number",
            "company_cnpj",
            "reference_month",
            "paid_amount",
            "payment_date",
            "current_status",
        ]],
        use_container_width=True,
    )

  # --- BOTÕES DE DOWNLOAD ---
  st.markdown("---")
  st.subheader("📥 Exportar Relatório")

  c_pdf, c_excel, c_csv = st.columns(3)

  # 1. Download PDF
  pdf_bytes = generate_pdf_report(
      empresas_header_str, df_pay_sub, df_contracts_sub, ano_sel
  )
  c_pdf.download_button(
      label="📄 Baixar Relatório em PDF",
      data=pdf_bytes,
      file_name=f"Relatorio_Pagamentos_{ano_sel}.pdf",
      mime="application/pdf",
      use_container_width=True,
      type="primary",
  )

  # 2. Download Excel
  buffer = io.BytesIO()
  with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_contracts_sub.to_excel(writer, sheet_name="Contratos", index=False)
    if not df_pay_sub.empty:
      df_pay_sub.to_excel(writer, sheet_name="Pagamentos", index=False)
  buffer.seek(0)

  c_excel.download_button(
      label="📊 Baixar Planilha Excel (.xlsx)",
      data=buffer,
      file_name=f"Relatorio_Pagamentos_{ano_sel}.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
  )

  # 3. Download CSV
  if not df_pay_sub.empty:
    csv_data = df_pay_sub.to_csv(index=False).encode("utf-8")
    c_csv.download_button(
        label="📄 Baixar Dados em CSV",
        data=csv_data,
        file_name=f"Relatorio_Pagamentos_{ano_sel}.csv",
        mime="text/csv",
        use_container_width=True,
    )

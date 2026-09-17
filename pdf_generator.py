# pdf_generator.py
import io
import matplotlib
import matplotlib.pyplot as plt
from fpdf import FPDF
import pandas as pd

# Configura backend headless do Matplotlib
matplotlib.use("Agg")


def format_brl(val):
    """Formata número no padrão monetário brasileiro R$ X.XXX,XX."""
    return f"R$ {val:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")


def clean_pdf_text(text):
    """Remove caracteres Unicode incompatíveis com Helvetica."""
    if text is None:
        return ""
    s = (
        str(text)
        .replace("—", "-")
        .replace("–", "-")
        .replace("•", "-")
        .replace("…", "...")
    )
    return s.encode("latin-1", errors="replace").decode("latin-1")


def generate_line_chart_img(chart_data):
    """Gera imagem do gráfico de linha para o PDF."""
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    for col in chart_data.columns:
        if col != "Mês":
            ax.plot(
                chart_data["Mês"],
                chart_data[col],
                marker="o",
                linewidth=2,
                label=col,
            )

    ax.set_title(
        "Evolução Mês a Mês dos Pagamentos (R$)",
        fontsize=11,
        fontweight="bold",
    )
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()

    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", dpi=200)
    plt.close(fig)
    img_buf.seek(0)
    return img_buf


def generate_pdf_report(empresas_str, df_payments_sub, df_contracts_sub, ano_sel, chart_data):
    """Gera o documento PDF formatado com gráficos e tabelas em memória."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- CABEÇALHO ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0,
        10,
        clean_pdf_text(f"RELATÓRIO EXECUTIVO DE PAGAMENTOS - {ano_sel}"),
        ln=True,
        align="C",
    )

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 6, clean_pdf_text(f"Empresa(s): {empresas_str}"), ln=True, align="C"
    )
    pdf.ln(4)

    # --- RESUMO FINANCEIRO (KPIS) ---
    pago_mask = (
        (df_payments_sub["current_status"] == "PAGO")
        if not df_payments_sub.empty
        else pd.Series()
    )
    df_pago = (
        df_payments_sub[pago_mask]
        if not df_payments_sub.empty
        else pd.DataFrame()
    )
    tot_pago = df_pago["paid_num"].sum() if not df_pago.empty else 0.0
    tot_lanctos = len(df_payments_sub) if not df_payments_sub.empty else 0

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, clean_pdf_text("1. Resumo Orçamentário"), ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        6,
        clean_pdf_text(
            f"- Total de Contratos Monitorados: {len(df_contracts_sub)}"
        ),
        ln=True,
    )
    pdf.cell(
        0,
        6,
        clean_pdf_text(f"- Total de Lançamentos Registrados: {tot_lanctos}"),
        ln=True,
    )
    pdf.cell(
        0,
        6,
        clean_pdf_text(f"- Total Pago/Quitado: {format_brl(tot_pago)}"),
        ln=True,
    )
    pdf.ln(4)

    # --- GRÁFICO DE EVOLUÇÃO ---
    if not chart_data.empty and len(chart_data.columns) > 1:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(
            0,
            8,
            clean_pdf_text("2. Gráfico de Evolução dos Pagamentos"),
            ln=True,
        )

        img_buf = generate_line_chart_img(chart_data)
        pdf.image(img_buf, x=15, w=180)
        pdf.ln(6)

    # --- TABELA DE DETALHAMENTO ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, clean_pdf_text("3. Detalhamento dos Pagamentos"), ln=True)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(35, 7, clean_pdf_text("Contrato"), border=1, align="C")
    pdf.cell(25, 7, clean_pdf_text("Mês Ref."), border=1, align="C")
    pdf.cell(35, 7, clean_pdf_text("Valor (R$)"), border=1, align="C")
    pdf.cell(30, 7, clean_pdf_text("Data Pgto"), border=1, align="C")
    pdf.cell(
        65, 7, clean_pdf_text("Status Atual"), border=1, align="C", ln=True
    )

    pdf.set_font("Helvetica", "", 8)
    if not df_payments_sub.empty:
        for _, r in df_payments_sub.iterrows():
            ctr = clean_pdf_text(r.get("contract_number", "---"))
            m_ref = clean_pdf_text(r.get("reference_month", "---"))
            v_pago = format_brl(r.get("paid_num", 0.0))
            dt_pago = clean_pdf_text(r.get("payment_date", "---"))
            st_val = clean_pdf_text(r.get("current_status", "---"))

            pdf.cell(35, 6, ctr, border=1)
            pdf.cell(25, 6, m_ref, border=1, align="C")
            pdf.cell(35, 6, clean_pdf_text(v_pago), border=1, align="R")
            pdf.cell(30, 6, dt_pago, border=1, align="C")
            pdf.cell(65, 6, st_val, border=1, ln=True)
    else:
        pdf.cell(
            190,
            6,
            clean_pdf_text("Nenhum lançamento encontrado para os filtros."),
            border=1,
            align="C",
            ln=True,
        )

    return bytes(pdf.output())

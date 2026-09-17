import datetime
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Sistema de Gestão de Pagamentos",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- CONEXÃO COM O GOOGLE SHEETS (BANCO DE DADOS) ---
@st.cache_resource(ttl=60)
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def load_table(sheet_name):
    client = get_gspread_client()
    sh = client.open_by_key(st.secrets["spreadsheet_id"])
    ws = sh.worksheet(sheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data), ws


# --- TELA DE LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Acesso ao Sistema de Pagamentos")
    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            users_db = st.secrets["users"]
            if user in users_db and users_db[user] == password:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.title(f"👤 Usuário: {st.session_state.user}")
if st.sidebar.button("Sair / Logout"):
    st.session_state.logged_in = False
    st.rerun()

menu = st.sidebar.radio(
    "Menu Principal",
    [
        "📊 Dashboard Matricial",
        "📝 Lançamentos (CRUD)",
        "📜 Histórico de Auditoria",
    ],
)

status_options = [
    "AGUARDANDO_CONTATO",
    "CONTATO_REALIZADO",
    "F_SOLICITAR_PAGAMENTO",
    "GC_APROVAR_SOLICITACAO",
    "FA_ADICIONAR_DOCUMENTOS",
    "F_ADICIONAR_INFORMACOES",
    "FA_COMPLETAR_INFORMACOES",
    "FT_ANALISAR_DEFINIR_ASSINATURAS",
    "FT_ASSINAR_NOTA_FISCAL",
    "E_ASSINATURA_EMPENHADOR",
    "GC_VALIDAR_ASSINAR_SUBEMPENHO",
    "OD_VALIDAR_ASSINAR_SUBEMPENHO",
    "L_AGUARDAR_LIQUIDACAO",
    "AC_VERIFICAR_CONFORMIDADE",
    "T_AGUARDAR_PAGAMENTO",
    "PAGO",
]

# --- 1. DASHBOARD MATRICIAL (PROCESSADO 100% EM PYTHON) ---
if menu == "📊 Dashboard Matricial":
    st.title("Painel Geral de Contratos e Pagamentos")

    df_contracts, _ = load_table("CONTRACT")
    df_payments, _ = load_table("PAGAMENTOS")

    # Filtros
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

    # KPIs
    if not df_payments.empty:
        total_pago = pd.to_numeric(
            df_payments[df_payments["current_status"] == "PAGO"][
                "paid_amount"
            ],
            errors="coerce",
        ).sum()
        media_mensal = total_pago / 12
    else:
        total_pago, media_mensal = 0.0, 0.0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Pago no Ano", f"R$ {total_pago:,.2f}")
    k2.metric("Média Mensal Paga", f"R$ {media_mensal:,.2f}")
    k3.metric("Contratos Monitorados", len(df_contracts))

    st.markdown("---")
    st.subheader("Acompanhamento Mês a Mês (JAN - DEZ)")

    # Construção da Matriz
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

# --- 2. OPERAÇÕES CRUD DE PAGAMENTOS ---
elif menu == "📝 Lançamentos (CRUD)":
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
        with st.form("f_create"):
            ctr_sel = st.selectbox(
                "Contrato", df_contracts["contract_number"].tolist()
            )
            ref_m = st.text_input("Mês de Referência (MM-YYYY)", "03-2026")
            sub_id = st.number_input("ID do Sub-empenho", value=101, step=1)
            p_val = st.number_input("Valor Pago (R$)", value=0.0, step=100.0)
            init_st = st.selectbox("Status Inicial", status_options)
            obs = st.text_area("Observação do Lançamento")

            if st.form_submit_button("Salvar no Banco"):
                new_id = (
                    int(pd.to_numeric(df_payments["id"]).max()) + 1
                    if not df_payments.empty
                    else 1001
                )
                cnpj_val = df_contracts[
                    df_contracts["contract_number"] == ctr_sel
                ]["company_cnpj"].values[0]

                # Escreve a linha pura no Google Sheets
                ws_payments.append_row([
                    new_id,
                    sub_id,
                    cnpj_val,
                    ctr_sel,
                    ref_m,
                    ref_m,
                    "Adiantado",
                    p_val,
                    str(datetime.date.today()),
                    init_st,
                ])

                # Grava Auditoria
                ws_history.append_row([
                    len(ws_history.get_all_values()) + 1,
                    new_id,
                    ctr_sel,
                    "N/A",
                    sub_id,
                    "NOVO_REGISTRO",
                    init_st,
                    str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    st.session_state.user,
                    f"Criação: {obs}",
                ])
                st.success("Pagamento inserido com sucesso!")
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
                    status_options,
                    index=status_options.index(curr["current_status"])
                    if curr["current_status"] in status_options
                    else 0,
                )
                obs_up = st.text_area("Motivo da Mudança de Etapa")

                if st.form_submit_button("Atualizar e Gravar Histórico"):
                    cell = ws_payments.find(str(p_id))
                    ws_payments.update_cell(cell.row, 10, next_st)

                    # Grava linha no HISTORICO_STATUS
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
                                "%Y-%m-%d %H:%M:%S"
                            )
                        ),
                        st.session_state.user,
                        obs_up,
                    ])
                    st.success("Status atualizado com sucesso!")
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
                    str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    st.session_state.user,
                    "Registro removido",
                ])
                st.success("Registro apagado com sucesso!")
                st.cache_resource.clear()

# --- 3. EXIBIÇÃO DO HISTÓRICO DE AUDITORIA ---
elif menu == "📜 Histórico de Auditoria":
    st.title("Trilha de Auditoria e Alterações (LGPD)")
    df_hist, _ = load_table("HISTORICO_STATUS")
    st.dataframe(df_hist, use_container_width=True)

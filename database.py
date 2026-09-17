# database.py
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


@st.cache_resource(ttl=3600)
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


@st.cache_resource(ttl=300)
def get_spreadsheet():
    """Cacheia a abertura da planilha por 5 minutos evitando estourar a API."""
    client = get_gspread_client()
    return client.open_by_key(st.secrets["spreadsheet_id"])


@st.cache_data(ttl=15)
def load_table_data(sheet_name):
    """Cacheia os dados da aba por 15 segundos para evitar re-downloads seguidos."""
    sh = get_spreadsheet()
    ws = sh.worksheet(sheet_name)
    values = ws.get_all_values()

    if len(values) > 1:
        df = pd.DataFrame(values[1:], columns=values[0])
    elif len(values) == 1:
        df = pd.DataFrame(columns=values[0])
    else:
        df = pd.DataFrame()

    return df


def load_table(sheet_name):
    """Retorna o DataFrame (cacheado) e o objeto Worksheet para gravações."""
    sh = get_spreadsheet()
    ws = sh.worksheet(sheet_name)
    df = load_table_data(sheet_name)
    return df, ws

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


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

    values = ws.get_all_values()
    if len(values) > 1:
        df = pd.DataFrame(values[1:], columns=values[0])
    elif len(values) == 1:
        df = pd.DataFrame(columns=values[0])
    else:
        df = pd.DataFrame()

    return df, ws

import datetime

import pandas as pd

from database import load_table


def clean_num_val(val_str):
    """Converte valores monetários no padrão PT-BR para float."""
    if pd.isna(val_str) or val_str is None:
        return 0.0
    s = str(val_str).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def get_empenhos_by_contract(contract_number: str):
    """Retorna os Empenhos Globais filtrados pelo contrato selecionado."""
    df_eg, ws_eg = load_table("EMPENHO_GLOBAL")
    if not df_eg.empty and "contract_number" in df_eg.columns:
        df_filtered = df_eg[df_eg["contract_number"] == contract_number]
    else:
        df_filtered = pd.DataFrame()

    return df_eg, ws_eg, df_filtered


def create_empenho_global(
    contract_number: str,
    number: str,
    value: float,
    start_date: datetime.date,
    end_date: datetime.date,
) -> int:
    """Gera o ID automaticamente nos bastidores e grava as 7 colunas em EMPENHO_GLOBAL."""
    df_eg, ws_eg, _ = get_empenhos_by_contract(contract_number)

    next_eg_id = (
        int(pd.to_numeric(df_eg["id"], errors="coerce").max() + 1)
        if not df_eg.empty and "id" in df_eg.columns
        else 1
    )

    ws_eg.append_row(
        [
            next_eg_id,
            contract_number.strip(),
            number.strip(),
            value,
            start_date.strftime("%d/%m/%Y"),
            end_date.strftime("%d/%m/%Y"),
            "FALSO",
        ]
    )

    return next_eg_id

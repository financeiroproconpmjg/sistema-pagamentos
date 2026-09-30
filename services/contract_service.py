import datetime

import pandas as pd

from database import load_table


def get_contracts_by_company(cnpj: str):
    """Retorna todos os contratos e filtra os vinculados a um determinado CNPJ."""
    df_contracts, ws_contracts = load_table("CONTRACT")
    if not df_contracts.empty and "company_cnpj" in df_contracts.columns:
        df_filtered = df_contracts[
            df_contracts["company_cnpj"].astype(str).str.strip() == str(cnpj).strip()
        ]
    else:
        df_filtered = pd.DataFrame()

    return df_contracts, ws_contracts, df_filtered


def create_contract(
    contract_number: str,
    company_cnpj: str,
    manager_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    regime_pagamento: str,
) -> bool:
    """Cadastra novo contrato enviando exatamente as 6 colunas estruturadas."""
    _, ws_contracts, _ = get_contracts_by_company(company_cnpj)

    ws_contracts.append_row(
        [
            contract_number.strip(),
            company_cnpj.strip(),
            manager_name.strip(),
            start_date.strftime("%d/%m/%Y"),
            end_date.strftime("%d/%m/%Y"),
            regime_pagamento,
        ]
    )
    return True

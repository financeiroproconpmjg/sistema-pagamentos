from database import load_table


def get_companies():
    """Retorna a tabela de empresas e constrói o dicionário CNPJ -> Nome."""
    df_company, ws_company = load_table("COMPANY")
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

    return df_company, ws_company, cnpj_to_name


def create_company(cnpj: str, name: str) -> bool:
    """Cadastra nova empresa enviando exatamente 2 colunas [cnpj, name]."""
    _, ws_company, _ = get_companies()
    ws_company.append_row([cnpj.strip(), name.strip()])
    return True

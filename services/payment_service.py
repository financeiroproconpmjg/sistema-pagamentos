# services/payment_service.py
from datetime import datetime, timedelta, timezone

import pandas as pd

from database import load_table

# Fuso horário oficial de Brasília/Recife (UTC-3)
TZ_BR = timezone(timedelta(hours=-3))


def clean_num_val(val_str):
    if pd.isna(val_str) or val_str is None:
        return 0.0
    s = str(val_str).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def get_sub_empenhos(empenho_global_id: str):
    """Retorna os Sub-Empenhos pertencentes a um Empenho Global."""
    df_sub, ws_sub = load_table("SUB_EMPENHO")
    if not df_sub.empty and "empenho_global_id" in df_sub.columns:
        df_filtered = df_sub[
            df_sub["empenho_global_id"].astype(str) == str(empenho_global_id)
        ]
    else:
        df_filtered = pd.DataFrame()

    return df_sub, ws_sub, df_filtered


def get_payments():
    """Retorna todos os lançamentos da tabela de pagamentos."""
    df_payments, ws_payments = load_table("PAGAMENTOS")
    return df_payments, ws_payments


def create_sub_and_payment(
    empenho_global_id: str,
    company_cnpj: str,
    contract_number: str,
    sub_ref_month: str,
    sub_value: float,
    payment_exec_month: str,
    regime_pagamento: str,
    paid_amount: float,
    current_status: str,
    user: str,
    obs: str = "",
):
    """Cria simultaneamente Sub-Empenho e Pagamento gerando os IDs automaticamente nos bastidores."""
    df_sub, ws_sub, _ = get_sub_empenhos(empenho_global_id)
    df_payments, ws_payments = get_payments()
    _, ws_history = load_table("HISTORICO_STATUS")

    # Gerar IDs sem interação do usuário
    next_sub_id = (
        int(pd.to_numeric(df_sub["id"], errors="coerce").max() + 1)
        if not df_sub.empty and "id" in df_sub.columns
        else 101
    )

    next_pay_id = (
        int(pd.to_numeric(df_payments["id"], errors="coerce").max() + 1)
        if not df_payments.empty and "id" in df_payments.columns
        else 1001
    )

    now_dt = datetime.now(tz=TZ_BR)
    today_str = now_dt.strftime("%d/%m/%Y")
    now_str = now_dt.strftime("%d/%m/%Y %H:%M:%S")

    # 1. Salva em SUB_EMPENHO (4 colunas)
    ws_sub.append_row(
        [
            next_sub_id,
            empenho_global_id,
            sub_ref_month.strip(),
            sub_value,
        ]
    )

    # 2. Salva em PAGAMENTOS (10 colunas)
    ws_payments.append_row(
        [
            next_pay_id,
            next_sub_id,
            company_cnpj.strip(),
            contract_number.strip(),
            sub_ref_month.strip(),
            payment_exec_month.strip(),
            regime_pagamento,
            paid_amount if current_status == "PAGO" else 0,
            today_str if current_status == "PAGO" else "",
            current_status,
        ]
    )

    # 3. Registra na trilha de auditoria
    ws_history.append_row(
        [
            len(ws_history.get_all_values()) + 1,
            next_pay_id,
            contract_number,
            "N/A",
            next_sub_id,
            "NOVO_REGISTRO",
            current_status,
            now_str,
            user,
            f"Criação Unificada: {obs}",
        ]
    )

    return next_sub_id, next_pay_id


def update_payment_status(
    payment_id: int,
    new_status: str,
    paid_amount: float,
    user: str,
    obs: str = "",
):
    """Atualiza o status de um pagamento e registra o histórico."""
    df_payments, ws_payments = get_payments()
    _, ws_history = load_table("HISTORICO_STATUS")

    curr = df_payments[df_payments["id"] == payment_id].iloc[0]
    cell = ws_payments.find(str(payment_id))
    row_idx = cell.row

    now_dt = datetime.now(tz=TZ_BR)
    today_str = now_dt.strftime("%d/%m/%Y")
    now_str = now_dt.strftime("%d/%m/%Y %H:%M:%S")

    if new_status == "PAGO":
        ws_payments.update_cell(row_idx, 8, paid_amount)
        ws_payments.update_cell(row_idx, 9, today_str)
        ws_payments.update_cell(row_idx, 10, new_status)
    else:
        ws_payments.update_cell(row_idx, 10, new_status)

    ws_history.append_row(
        [
            len(ws_history.get_all_values()) + 1,
            payment_id,
            curr["contract_number"],
            "N/A",
            curr["sub_empenho_id"],
            curr["current_status"],
            new_status,
            now_str,
            user,
            obs,
        ]
    )


def delete_payment(payment_id: int, user: str):
    """Exclui linha da tabela de pagamentos e registra na auditoria."""
    _df_payments, ws_payments = get_payments()
    _, ws_history = load_table("HISTORICO_STATUS")

    cell = ws_payments.find(str(payment_id))
    ws_payments.delete_rows(cell.row)

    now_dt = datetime.now(tz=TZ_BR)
    now_str = now_dt.strftime("%d/%m/%Y %H:%M:%S")

    ws_history.append_row(
        [
            len(ws_history.get_all_values()) + 1,
            payment_id,
            "N/A",
            "N/A",
            "N/A",
            "DELETADO",
            "DELETADO",
            now_str,
            user,
            "Registro removido via sistema",
        ]
    )

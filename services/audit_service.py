from database import load_table


def get_audit_history():
  """Retorna a tabela com a trilha de auditoria e alterações do sistema."""
  df_hist, ws_hist = load_table("HISTORICO_STATUS")
  return df_hist, ws_hist
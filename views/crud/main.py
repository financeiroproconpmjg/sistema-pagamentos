# views/crud/main.py
import streamlit as st

from views.crud.tab_delete import render_delete
from views.crud.tab_read import render_read
from views.crud.tab_update import render_update
from views.crud.tab_wizard import render_wizard


def render_crud():
    st.title("⚙️ Gerenciamento de Contratos, Empenhos e Pagamentos")

    t_create, t_read, t_update, t_delete = st.tabs(
        [
            "➕ Novo Lançamento (Etapas)",
            "📋 Listar Registros",
            "✏️ Atualizar Status",
            "🗑️ Excluir Lançamento",
        ]
    )

    with t_create:
        render_wizard()

    with t_read:
        render_read()

    with t_update:
        render_update()

    with t_delete:
        render_delete()

# 📊 Sistema de Gestão de Pagamentos e Contratos

Sistema web em Python/Streamlit integrado ao Google Sheets (atuando como banco de dados relacional sem fórmulas). O projeto conta com autenticação de usuários, Dashboard matricial dinâmico (JAN a DEZ), CRUD completo de pagamentos e trilha de auditoria para conformidade com a LGPD.

---

## 🗄️ Estrutura do Banco de Dados (Google Sheets)

A planilha deve conter exatamente as seguintes **6 abas** (com os nomes das colunas na linha 1):

* **`COMPANY`**: `cnpj`, `name`
* **`CONTRACT`**: `contract_number`, `company_cnpj`, `manager_name`, `start_date`, `end_date`, `regime_pagamento`
* **`EMPENHO_GLOBAL`**: `id`, `contract_number`, `number`, `value`, `start_date`, `end_date`, `is_canceled`
* **`SUB_EMPENHO`**: `id`, `empenho_global_id`, `reference_month`, `value`
* **`PAGAMENTOS`**: `id`, `sub_empenho_id`, `company_cnpj`, `contract_number`, `reference_month`, `payment_execution_month`, `regime_pagamento`, `paid_amount`, `payment_date`, `current_status`
* **`HISTORICO_STATUS`**: `id`, `payment_id`, `contract_number`, `empenho_global`, `sub_empenho`, `status_anterior`, `status_novo`, `changed_at`, `user`, `observation`

---

## 🚀 Instalação e Execução Local

### 1. Clona o repositório e instala as dependências
```bash
git clone [https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git](https://github.com/financeiroproconpmjg/sistema-pagamentos.git)
cd sistema-pagamentos
pip install -r requirements.txt

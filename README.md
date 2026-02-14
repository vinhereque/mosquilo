# AgendaPro (Flet + SQLite)

Sistema de agendamento multi-tarefas para clínicas, barbearias, salões e serviços.

## Stack
- **Python + Flet** (interface)
- **SQLite** (persistência local)

## Telas
1. Dashboard
2. Novo Agendamento
3. Gestão de Profissionais
4. Novo Profissional
5. Gestão de Serviços
6. Novo Serviço
7. Agenda Diária

## Como executar
```bash
python -m venv .venv
source .venv/bin/activate
pip install flet
python main.py
```

O banco `agendapro.db` é criado automaticamente com dados de demonstração na primeira execução.

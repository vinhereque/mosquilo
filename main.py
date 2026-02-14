import sqlite3
from contextlib import closing
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Tuple

import flet as ft

DB_PATH = Path("agendapro.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with closing(get_conn()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS negocios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                segmento TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS profissionais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                especialidade TEXT NOT NULL,
                horario_inicio TEXT NOT NULL,
                horario_fim TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT NOT NULL,
                preco REAL NOT NULL,
                duracao_min INTEGER NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                email TEXT,
                criado_em TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                profissional_id INTEGER NOT NULL,
                servico_id INTEGER NOT NULL,
                data_hora TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmado',
                observacoes TEXT,
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                FOREIGN KEY(profissional_id) REFERENCES profissionais(id),
                FOREIGN KEY(servico_id) REFERENCES servicos(id)
            );

            CREATE INDEX IF NOT EXISTS idx_agendamentos_data ON agendamentos(data_hora);
            CREATE INDEX IF NOT EXISTS idx_agendamentos_profissional ON agendamentos(profissional_id);
            CREATE INDEX IF NOT EXISTS idx_servicos_categoria ON servicos(categoria);
            """
        )
        conn.commit()


def seed_demo_data() -> None:
    with closing(get_conn()) as conn:
        existing = conn.execute("SELECT COUNT(*) AS total FROM negocios").fetchone()["total"]
        if existing:
            return

        conn.execute(
            "INSERT INTO negocios (nome, segmento) VALUES (?, ?)",
            ("AgendaPro Demo", "Salão / Clínica"),
        )

        profissionais = [
            ("Ana Souza", "Cabelo", "09:00", "18:00"),
            ("Carlos Lima", "Barba", "10:00", "19:00"),
            ("Dra. Beatriz", "Estética", "08:00", "17:00"),
        ]
        conn.executemany(
            "INSERT INTO profissionais (nome, especialidade, horario_inicio, horario_fim) VALUES (?, ?, ?, ?)",
            profissionais,
        )

        servicos = [
            ("Corte Feminino", "Cabelo", 85.0, 60),
            ("Barba Premium", "Barbearia", 45.0, 40),
            ("Limpeza de Pele", "Estética", 130.0, 75),
        ]
        conn.executemany(
            "INSERT INTO servicos (nome, categoria, preco, duracao_min) VALUES (?, ?, ?, ?)",
            servicos,
        )

        clientes = [
            ("Marina Oliveira", "11999990001", "marina@email.com"),
            ("João Pedro", "11999990002", "joao@email.com"),
            ("Fernanda Costa", "11999990003", "fernanda@email.com"),
        ]
        conn.executemany("INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)", clientes)

        now = datetime.now().replace(second=0, microsecond=0)
        demo_appointments = [
            (1, 1, 1, (now + timedelta(hours=1)).isoformat(timespec="minutes"), "confirmado", "Primeira visita"),
            (2, 2, 2, (now + timedelta(hours=2)).isoformat(timespec="minutes"), "confirmado", "Cliente recorrente"),
            (3, 3, 3, (now + timedelta(hours=3)).isoformat(timespec="minutes"), "confirmado", "Sem observações"),
        ]
        conn.executemany(
            """
            INSERT INTO agendamentos
            (cliente_id, profissional_id, servico_id, data_hora, status, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            demo_appointments,
        )
        conn.commit()


def fetch_profissionais() -> List[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT id, nome, especialidade, horario_inicio, horario_fim, ativo FROM profissionais WHERE ativo = 1 ORDER BY nome"
        ).fetchall()


def fetch_servicos() -> List[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT id, nome, categoria, preco, duracao_min, ativo FROM servicos WHERE ativo = 1 ORDER BY nome"
        ).fetchall()


def fetch_clientes() -> List[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return conn.execute("SELECT id, nome, telefone FROM clientes ORDER BY nome").fetchall()


def fetch_agendamentos_by_date(target_date: date) -> List[sqlite3.Row]:
    start = datetime.combine(target_date, datetime.min.time()).isoformat(timespec="minutes")
    end = datetime.combine(target_date + timedelta(days=1), datetime.min.time()).isoformat(timespec="minutes")
    with closing(get_conn()) as conn:
        return conn.execute(
            """
            SELECT a.id, a.data_hora, a.status, a.observacoes,
                   c.nome AS cliente,
                   p.nome AS profissional,
                   s.nome AS servico,
                   s.preco AS preco
            FROM agendamentos a
            JOIN clientes c ON c.id = a.cliente_id
            JOIN profissionais p ON p.id = a.profissional_id
            JOIN servicos s ON s.id = a.servico_id
            WHERE a.data_hora >= ? AND a.data_hora < ?
            ORDER BY a.data_hora
            """,
            (start, end),
        ).fetchall()


def dashboard_stats(today: date) -> Tuple[int, int, float]:
    ag = fetch_agendamentos_by_date(today)
    total = len(ag)
    confirmados = sum(1 for item in ag if item["status"] == "confirmado")
    receita = sum(float(item["preco"]) for item in ag)
    return total, confirmados, receita


def add_profissional(nome: str, especialidade: str, horario_inicio: str, horario_fim: str) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO profissionais (nome, especialidade, horario_inicio, horario_fim) VALUES (?, ?, ?, ?)",
            (nome, especialidade, horario_inicio, horario_fim),
        )
        conn.commit()


def add_servico(nome: str, categoria: str, preco: float, duracao_min: int) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO servicos (nome, categoria, preco, duracao_min) VALUES (?, ?, ?, ?)",
            (nome, categoria, preco, duracao_min),
        )
        conn.commit()


def add_agendamento(cliente_id: int, profissional_id: int, servico_id: int, data_hora: str, observacoes: str) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            """
            INSERT INTO agendamentos (cliente_id, profissional_id, servico_id, data_hora, observacoes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cliente_id, profissional_id, servico_id, data_hora, observacoes),
        )
        conn.commit()


class AgendaProApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_date = date.today()
        self.page.title = "AgendaPro"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 16
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.window_width = 420
        self.page.window_height = 860
        self.page.bgcolor = "#F7F8FC"
        self.page.fonts = {"Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"}
        self.page.theme = ft.Theme(font_family="Inter", color_scheme_seed="#4f46e5")

    def pill(self, label: str, value: str, icon: str) -> ft.Control:
        return ft.Container(
            padding=12,
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(icon, size=18, color="#4f46e5"), ft.Text(label, size=12, color="#6b7280")]),
                    ft.Text(value, size=18, weight=ft.FontWeight.BOLD),
                ],
                spacing=4,
            ),
        )

    def render_dashboard(self) -> None:
        total, confirmados, receita = dashboard_stats(self.current_date)
        agendamentos = fetch_agendamentos_by_date(self.current_date)

        cards = [
            self.pill("Agendamentos", str(total), ft.Icons.CALENDAR_MONTH),
            self.pill("Confirmados", str(confirmados), ft.Icons.CHECK_CIRCLE),
            self.pill("Receita", f"R$ {receita:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), ft.Icons.PAYMENTS),
        ]

        lista = ft.Column(spacing=10)
        if not agendamentos:
            lista.controls.append(ft.Text("Sem agendamentos para hoje."))
        for ag in agendamentos:
            hora = datetime.fromisoformat(ag["data_hora"]).strftime("%H:%M")
            lista.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    padding=12,
                    border_radius=10,
                    content=ft.Column(
                        controls=[
                            ft.Text(f"{hora} • {ag['cliente']}", weight=ft.FontWeight.W_600),
                            ft.Text(f"{ag['servico']} com {ag['profissional']}", size=12, color="#6b7280"),
                        ],
                        spacing=2,
                    ),
                )
            )

        self.page.views.clear()
        self.page.views.append(
            ft.View(
                route="/",
                controls=[
                    ft.Text("AgendaPro", size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("Dashboard do dia", color="#6b7280"),
                    ft.ResponsiveRow([ft.Container(col={"sm": 4}, content=c) for c in cards]),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton("Novo Agendamento", icon=ft.Icons.ADD, on_click=lambda _: self.page.go("/agendamentos/novo")),
                            ft.TextButton("Agenda Diária", icon=ft.Icons.EVENT_NOTE, on_click=lambda _: self.page.go("/agenda")),
                        ]
                    ),
                    ft.Text("Próximos horários", weight=ft.FontWeight.W_600),
                    lista,
                ],
            )
        )
        self.page.update()

    def render_profissionais(self) -> None:
        profissionais = fetch_profissionais()
        rows = ft.Column(spacing=8)
        for p in profissionais:
            rows.controls.append(
                ft.ListTile(
                    title=ft.Text(p["nome"]),
                    subtitle=ft.Text(f"{p['especialidade']} • {p['horario_inicio']} - {p['horario_fim']}"),
                    leading=ft.Icon(ft.Icons.BADGE),
                )
            )

        self.page.views.append(
            ft.View(
                route="/profissionais",
                controls=[
                    ft.AppBar(title=ft.Text("Profissionais")),
                    ft.ElevatedButton("Novo Profissional", icon=ft.Icons.PERSON_ADD, on_click=lambda _: self.page.go("/profissionais/novo")),
                    rows,
                ],
            )
        )
        self.page.update()

    def render_novo_profissional(self) -> None:
        nome = ft.TextField(label="Nome")
        especialidade = ft.TextField(label="Especialidade")
        inicio = ft.TextField(label="Horário início (HH:MM)", value="09:00")
        fim = ft.TextField(label="Horário fim (HH:MM)", value="18:00")
        erro = ft.Text(color=ft.Colors.RED)

        def salvar(_: ft.ControlEvent) -> None:
            if not nome.value or not especialidade.value:
                erro.value = "Preencha nome e especialidade."
                self.page.update()
                return
            add_profissional(nome.value.strip(), especialidade.value.strip(), inicio.value.strip(), fim.value.strip())
            self.page.go("/profissionais")

        self.page.views.append(
            ft.View(
                route="/profissionais/novo",
                controls=[
                    ft.AppBar(title=ft.Text("Novo Profissional")),
                    nome,
                    especialidade,
                    inicio,
                    fim,
                    erro,
                    ft.ElevatedButton("Salvar", icon=ft.Icons.SAVE, on_click=salvar),
                ],
            )
        )
        self.page.update()

    def render_servicos(self) -> None:
        servicos = fetch_servicos()
        rows = ft.Column(spacing=8)
        for s in servicos:
            rows.controls.append(
                ft.ListTile(
                    title=ft.Text(s["nome"]),
                    subtitle=ft.Text(f"{s['categoria']} • R$ {s['preco']:.2f} • {s['duracao_min']} min"),
                    leading=ft.Icon(ft.Icons.CONTENT_CUT),
                )
            )
        self.page.views.append(
            ft.View(
                route="/servicos",
                controls=[
                    ft.AppBar(title=ft.Text("Serviços")),
                    ft.ElevatedButton("Novo Serviço", icon=ft.Icons.ADD_CIRCLE, on_click=lambda _: self.page.go("/servicos/novo")),
                    rows,
                ],
            )
        )
        self.page.update()

    def render_novo_servico(self) -> None:
        nome = ft.TextField(label="Nome")
        categoria = ft.TextField(label="Categoria")
        preco = ft.TextField(label="Preço", value="0")
        duracao = ft.TextField(label="Duração (min)", value="30")
        erro = ft.Text(color=ft.Colors.RED)

        def salvar(_: ft.ControlEvent) -> None:
            try:
                preco_val = float(preco.value)
                duracao_val = int(duracao.value)
            except ValueError:
                erro.value = "Preço e duração devem ser numéricos."
                self.page.update()
                return
            if not nome.value or not categoria.value:
                erro.value = "Nome e categoria são obrigatórios."
                self.page.update()
                return
            add_servico(nome.value.strip(), categoria.value.strip(), preco_val, duracao_val)
            self.page.go("/servicos")

        self.page.views.append(
            ft.View(
                route="/servicos/novo",
                controls=[
                    ft.AppBar(title=ft.Text("Novo Serviço")),
                    nome,
                    categoria,
                    preco,
                    duracao,
                    erro,
                    ft.ElevatedButton("Salvar", icon=ft.Icons.SAVE, on_click=salvar),
                ],
            )
        )
        self.page.update()

    def render_novo_agendamento(self) -> None:
        clientes = fetch_clientes()
        profissionais = fetch_profissionais()
        servicos = fetch_servicos()

        cliente = ft.Dropdown(
            label="Cliente",
            options=[ft.dropdown.Option(str(c["id"]), c["nome"]) for c in clientes],
        )
        profissional = ft.Dropdown(
            label="Profissional",
            options=[ft.dropdown.Option(str(p["id"]), p["nome"]) for p in profissionais],
        )
        servico = ft.Dropdown(
            label="Serviço",
            options=[ft.dropdown.Option(str(s["id"]), s["nome"]) for s in servicos],
        )
        data_hora = ft.TextField(label="Data/Hora (YYYY-MM-DD HH:MM)", value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        observacoes = ft.TextField(label="Observações", multiline=True, min_lines=2, max_lines=4)
        erro = ft.Text(color=ft.Colors.RED)

        def salvar(_: ft.ControlEvent) -> None:
            if not cliente.value or not profissional.value or not servico.value:
                erro.value = "Selecione cliente, profissional e serviço."
                self.page.update()
                return
            try:
                dt = datetime.strptime(data_hora.value.strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                erro.value = "Formato de data inválido. Use YYYY-MM-DD HH:MM."
                self.page.update()
                return

            add_agendamento(int(cliente.value), int(profissional.value), int(servico.value), dt.isoformat(timespec="minutes"), observacoes.value or "")
            self.page.go("/")

        self.page.views.append(
            ft.View(
                route="/agendamentos/novo",
                controls=[
                    ft.AppBar(title=ft.Text("Novo Agendamento")),
                    cliente,
                    profissional,
                    servico,
                    data_hora,
                    observacoes,
                    erro,
                    ft.ElevatedButton("Salvar", icon=ft.Icons.CHECK, on_click=salvar),
                ],
            )
        )
        self.page.update()

    def render_agenda_diaria(self) -> None:
        agendamentos = fetch_agendamentos_by_date(self.current_date)
        title = ft.Text(self.current_date.strftime("Agenda de %d/%m/%Y"), size=20, weight=ft.FontWeight.BOLD)
        lista = ft.Column(spacing=8)
        if not agendamentos:
            lista.controls.append(ft.Text("Sem agendamentos nesta data."))
        for ag in agendamentos:
            hora = datetime.fromisoformat(ag["data_hora"]).strftime("%H:%M")
            lista.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column(
                            controls=[
                                ft.Text(f"{hora} • {ag['cliente']}", weight=ft.FontWeight.W_600),
                                ft.Text(f"Serviço: {ag['servico']}"),
                                ft.Text(f"Profissional: {ag['profissional']}"),
                            ]
                        ),
                    )
                )
            )

        def prev_day(_: ft.ControlEvent) -> None:
            self.current_date -= timedelta(days=1)
            self.page.go("/agenda")

        def next_day(_: ft.ControlEvent) -> None:
            self.current_date += timedelta(days=1)
            self.page.go("/agenda")

        self.page.views.append(
            ft.View(
                route="/agenda",
                controls=[
                    ft.AppBar(title=ft.Text("Agenda Diária")),
                    ft.Row([ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=prev_day), title, ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=next_day)]),
                    ft.Row(
                        [
                            ft.OutlinedButton("Dashboard", on_click=lambda _: self.page.go("/")),
                            ft.OutlinedButton("Profissionais", on_click=lambda _: self.page.go("/profissionais")),
                            ft.OutlinedButton("Serviços", on_click=lambda _: self.page.go("/servicos")),
                        ],
                        wrap=True,
                    ),
                    lista,
                ],
            )
        )
        self.page.update()

    def route_change(self, route: ft.RouteChangeEvent) -> None:
        self.page.views.clear()
        if self.page.route == "/":
            self.render_dashboard()
        elif self.page.route == "/agendamentos/novo":
            self.render_novo_agendamento()
        elif self.page.route == "/profissionais":
            self.render_profissionais()
        elif self.page.route == "/profissionais/novo":
            self.render_novo_profissional()
        elif self.page.route == "/servicos":
            self.render_servicos()
        elif self.page.route == "/servicos/novo":
            self.render_novo_servico()
        elif self.page.route == "/agenda":
            self.render_agenda_diaria()
        else:
            self.page.go("/")


def main(page: ft.Page) -> None:
    init_db()
    seed_demo_data()
    app = AgendaProApp(page)
    page.on_route_change = app.route_change
    page.go("/")


if __name__ == "__main__":
    ft.app(target=main)

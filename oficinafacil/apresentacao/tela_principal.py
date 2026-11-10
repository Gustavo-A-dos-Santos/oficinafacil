"""Área de trabalho: barra lateral recolhível, cabeçalho da página e as páginas permitidas a cada perfil."""
from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QSplitter, QStackedWidget,
                               QTabWidget, QVBoxLayout, QWidget)

from ..modelo import data_br, moeda
from ..modelo.atendimento import SituacaoCompra, StatusOS
from ..modelo.cadastro import Perfil
from .componentes import (TITULO, Avatar, Botao, Busca, Campo, Cartao, Dialogo, GraficoBarras, Interruptor, Kpi,
                          SeletorPeriodo, Tabela, area_texto, botao_icone, confirmar, definir_opcoes, entrada,
                          executar, inteiro_valido, janela_historico, notificar, numero_valido, pedir, rotulo,
                          salvar_e_abrir_pdf, selecao, sim_nao)
from .dialogo_compra import alterar_solicitacao, solicitar_compra
from .janela_os import JanelaOS
from .tema import ESPACO, Tema, duracao, icone, logotipo

COLUNAS_OS = [
    {"chave": "id", "titulo": "OS", "largura": 64, "numero": True},
    {"chave": "status", "titulo": "Status", "largura": 190, "status": True, "formato": lambda s: StatusOS.NOMES.get(s, s)},
    {"chave": "data_abertura", "titulo": "Abertura", "largura": 140, "formato": lambda d: data_br(d, True)},
    {"chave": "cliente_nome", "titulo": "Cliente", "largura": 160},
    {"chave": "placa", "titulo": "Placa", "largura": 96},
    {"chave": "modelo", "titulo": "Modelo", "largura": 100},
    {"chave": "mecanico_nome", "titulo": "Mecânico", "largura": 130},
    {"chave": "problema", "titulo": "Problema", "largura": 240, "dica": True},
]


class TelaPrincipal(QWidget):

    def __init__(self, app, usuario, pagina_inicial=0):
        super().__init__()
        self.app, self.ctrl, self.usuario = app, app.ctrl, usuario
        self.setObjectName("Pagina")
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        p = usuario.perfil
        paginas = [(PaginaPainel, "Painel", "layout-dashboard"), (PaginaOS, "Ordens de serviço", "clipboard-list")]
        if p in (Perfil.ATENDENTE, Perfil.GERENTE):
            paginas.append((PaginaClientes, "Clientes e veículos", "car"))
        if p in (Perfil.ATENDENTE, Perfil.MECANICO):
            paginas += [(PaginaConsulta, "Peças e serviços", "search"), (PaginaCompras, "Compras", "shopping-cart")]
        if p == Perfil.GERENTE:
            paginas += [(PaginaCompras, "Compras", "shopping-cart"), (PaginaCatalogo, "Catálogo", "book-open"),
                        (PaginaUsuarios, "Usuários", "user-cog"), (PaginaRelatorios, "Relatórios", "chart-column")]
        self.lateral = BarraLateral(self, [(t, i) for _, t, i in paginas])
        raiz.addWidget(self.lateral)
        direita = QVBoxLayout()
        direita.setContentsMargins(0, 0, 0, 0)
        direita.setSpacing(0)
        self.cabecalho = Cabecalho(usuario)
        direita.addWidget(self.cabecalho)
        self.pilha = QStackedWidget()
        self.paginas = []
        for classe, _, _ in paginas:
            pg = classe(self)
            self.paginas.append(pg)
            rolagem = QScrollArea()
            rolagem.setWidgetResizable(True)
            rolagem.setFrameShape(QFrame.NoFrame)
            rolagem.setWidget(pg)
            self.pilha.addWidget(rolagem)
        direita.addWidget(self.pilha, 1)
        raiz.addLayout(direita, 1)
        self._janelas = []
        for i in range(min(len(paginas), 9)):        # Ctrl+1 a Ctrl+9 trocam de página
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.ir(i))
        self.ir(min(pagina_inicial, len(paginas) - 1), animar=False)

    def pagina_atual(self):
        return self.pilha.currentIndex()

    def ir(self, i, animar=True):
        self.pilha.setCurrentIndex(i)
        self.lateral.marcar(i)
        pg = self.paginas[i]
        self.cabecalho.definir(pg.titulo, pg.subtitulo, pg.acoes_cabecalho())
        pg.atualizar()
        if animar and duracao():
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            alvo = self.pilha.currentWidget()
            ef = QGraphicsOpacityEffect(alvo)
            alvo.setGraphicsEffect(ef)
            self._anim = QPropertyAnimation(ef, b"opacity", self)
            self._anim.setDuration(duracao("media"))
            self._anim.setStartValue(0.35)
            self._anim.setEndValue(1.0)
            self._anim.setEasingCurve(QEasingCurve.OutCubic)
            self._anim.finished.connect(lambda: alvo.setGraphicsEffect(None))
            self._anim.start()

    def atualizar_aba_atual(self):
        self.paginas[self.pilha.currentIndex()].atualizar()

    def abrir_os(self, os_id):
        for j in self.janelas_os():
            if j.os_id == os_id:
                j.raise_()
                j.activateWindow()
                return
        j = JanelaOS(self, os_id)
        self._janelas.append(j)
        j.show()

    def janelas_os(self):
        vivas = []
        for j in self._janelas:
            try:
                if j.isVisible():
                    vivas.append(j)
            except RuntimeError:
                pass
        self._janelas = vivas
        return list(vivas)


class BarraLateral(QFrame):
    LARGA, ESTREITA = 240, 72

    def __init__(self, principal, itens):
        super().__init__()
        self.setObjectName("Lateral")
        self.principal, self.recolhida = principal, False
        self.setFixedWidth(self.LARGA)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(ESPACO["s"], ESPACO["m"], ESPACO["s"], ESPACO["m"])
        lay.setSpacing(4)
        topo = QHBoxLayout()
        topo.setContentsMargins(6, 0, 0, 0)
        logo = QLabel()
        logo.setPixmap(logotipo(32))
        topo.addWidget(logo)
        self.marca = QLabel(TITULO)
        self.marca.setObjectName("Marca")
        topo.addWidget(self.marca, 1)
        lay.addLayout(topo)
        lay.addSpacing(ESPACO["l"])
        self.secao = QLabel("MENU")
        self.secao.setStyleSheet("font-size: 11px; font-weight: 600; letter-spacing: 1px; padding-left: 12px;")
        lay.addWidget(self.secao)
        self.botoes = []
        for i, (texto, ic) in enumerate(itens):
            b = Botao(" " + texto, "nav")
            b.setProperty("papel", "nav")
            b.nome_icone, b.texto_cheio, b.atalho = ic, " " + texto, i
            b.setToolTip(f"{texto} (Ctrl+{i + 1})" if i < 9 else texto)
            b.clicked.connect(lambda _=False, i=i: principal.ir(i))
            b.setMinimumHeight(40)
            lay.addWidget(b)
            self.botoes.append(b)
        lay.addStretch(1)
        self.conexao = QLabel(f"\u25CF  Servidor {principal.app.servidor}")
        self.conexao.setStyleSheet(f"font-size: 12px; color: {Tema.cor('lateral_texto')}; padding-left: 12px;")
        self.conexao.setToolTip("Computador central que guarda os dados da oficina")
        lay.addWidget(self.conexao)
        lay.addSpacing(ESPACO["xs"])
        self.tema = Interruptor("Tema escuro")
        self.tema.setProperty("cor_texto", Tema.cor("lateral_texto"))
        self.tema.definir_sem_animar(Tema.nome == "escuro")
        self.tema.toggled.connect(lambda _: principal.app.alternar_tema())
        self.tema.setToolTip("Alternar entre os temas claro e escuro")
        lay.addWidget(self.tema)
        lay.addSpacing(ESPACO["xs"])
        self.recolher = Botao(" Recolher menu", "lateral_acao", "panel-left-close", "Recolher ou expandir o menu",
                              self.alternar)
        self.recolher.setProperty("papel", "lateral_acao")
        lay.addWidget(self.recolher)
        self.sair = Botao(" Sair", "lateral_acao", "log-out", "Sair do sistema", principal.app.sair)
        self.sair.setProperty("papel", "lateral_acao")
        lay.addWidget(self.sair)
        self._icones()

    def _icones(self):
        for b in self.botoes:
            ativo = b.property("ativo") == "true"
            b.setIcon(icone(b.nome_icone, "#FFFFFF" if ativo else Tema.cor("lateral_texto"), 18))
        for b in (self.recolher, self.sair):
            b.setIcon(icone(b.nome_icone, Tema.cor("lateral_texto"), 18))

    def marcar(self, i):
        for j, b in enumerate(self.botoes):
            b.setProperty("ativo", "true" if j == i else "false")
            b.style().unpolish(b)
            b.style().polish(b)
        self._icones()

    def alternar(self):
        self.recolhida = not self.recolhida
        alvo = self.ESTREITA if self.recolhida else self.LARGA
        self.recolher.nome_icone = "panel-left-open" if self.recolhida else "panel-left-close"
        for b in self.botoes + [self.recolher, self.sair]:
            b.setText("" if self.recolhida else (b.texto_cheio if hasattr(b, "texto_cheio") else b._texto))
        self.marca.setVisible(not self.recolhida)
        self.conexao.setVisible(not self.recolhida)
        self.secao.setVisible(not self.recolhida)
        self.tema.setText("" if self.recolhida else "Tema escuro")
        self._icones()
        grupo = QParallelAnimationGroup(self)
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self, prop, self)
            a.setDuration(duracao("media"))
            a.setStartValue(self.width())
            a.setEndValue(alvo)
            a.setEasingCurve(QEasingCurve.OutCubic)
            grupo.addAnimation(a)
        grupo.start()
        self._grupo = grupo


class Cabecalho(QFrame):
    def __init__(self, usuario):
        super().__init__()
        self.setObjectName("Cabecalho")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(ESPACO["xl"], ESPACO["m"], ESPACO["l"], ESPACO["m"])
        lay.setSpacing(ESPACO["s"])
        textos = QVBoxLayout()
        textos.setSpacing(2)
        self.titulo = rotulo("", "titulo")
        self.subtitulo = rotulo("", "subtitulo")
        textos.addWidget(self.titulo)
        textos.addWidget(self.subtitulo)
        lay.addLayout(textos, 1)
        self.acoes = QHBoxLayout()
        self.acoes.setSpacing(ESPACO["xs"])
        lay.addLayout(self.acoes)
        lay.addSpacing(ESPACO["m"])
        div = QFrame()
        div.setFixedSize(1, 32)
        div.setStyleSheet(f"background: {Tema.cor('borda')};")
        lay.addWidget(div)
        lay.addSpacing(ESPACO["xs"])
        quem = QVBoxLayout()
        quem.setSpacing(0)
        quem.addWidget(rotulo(usuario.nome, "valor"))
        quem.addWidget(rotulo(Perfil.NOMES[usuario.perfil], "legenda"))
        lay.addLayout(quem)
        lay.addWidget(Avatar(usuario.nome))

    def definir(self, titulo, subtitulo, acoes):
        self.titulo.setText(titulo)
        self.subtitulo.setText(subtitulo)
        while self.acoes.count():
            w = self.acoes.takeAt(0).widget()
            if w:
                w.setParent(None)
        for b in acoes:
            self.acoes.addWidget(b)


class Pagina(QWidget):
    titulo, subtitulo = "", ""

    def __init__(self, principal):
        super().__init__()
        self.setObjectName("Pagina")
        self.principal, self.ctrl, self.usuario = principal, principal.ctrl, principal.usuario
        self.perfil = self.usuario.perfil
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(ESPACO["xl"], ESPACO["l"], ESPACO["xl"], ESPACO["xl"])
        self.lay.setSpacing(ESPACO["l"])
        self._acoes = []

    def acoes_cabecalho(self):
        return self._acoes

    def atualizar(self):
        pass


# ------------------------------------------------------------------ painel
class PaginaPainel(Pagina):
    """RF35 (painel do gerente e do atendente) e pendências de cada perfil (RF10, RF15, RF28)."""
    titulo = "Painel"

    def __init__(self, principal):
        super().__init__(principal)
        self.subtitulo = {Perfil.MECANICO: "Suas ordens de serviço e as novas aguardando avaliação",
                          Perfil.GERENTE: "Visão geral da oficina e o que espera por você",
                          Perfil.ATENDENTE: "Visão geral da oficina e o que espera por você"}[self.perfil]
        self._acoes = [Botao("Atualizar", "secundario", "refresh-cw", "Atualizar o painel", self.atualizar)]
        self.mostra_etapas = self.perfil in (Perfil.ATENDENTE, Perfil.GERENTE)
        self.kpis = {}
        if self.mostra_etapas:
            self.grade = QGridLayout()
            self.grade.setSpacing(ESPACO["s"])
            for codigo in StatusOS.EM_ANDAMENTO:
                self.kpis[codigo] = Kpi(StatusOS.NOMES[codigo], "0", lambda c=codigo: Tema.status(c)[0])
            self._organizar(4)
            self.lay.addLayout(self.grade)
        self.alerta = rotulo("", "alerta", True)
        self.alerta.hide()
        self.lay.addWidget(self.alerta)
        cartao = Cartao("Minhas pendências", "Duplo clique (ou Enter) numa linha para abrir a OS.")
        self.tabela = Tabela(COLUNAS_OS, ("circle-check", "Tudo em dia", "Não há ordens de serviço esperando por você."),
                             [("Abrir OS", "eye", principal.abrir_os)])
        self.tabela.setMinimumHeight(320)
        self.tabela.ativado.connect(principal.abrir_os)
        cartao.lay.addWidget(self.tabela)
        self.lay.addWidget(cartao, 1)
        from PySide6.QtCore import QTimer
        self.relogio = QTimer(self)
        self.relogio.setInterval(30000)            # com várias estações, as pendências mudam: atualiza a cada 30 s
        self.relogio.timeout.connect(lambda: self.isVisible() and self.atualizar())
        self.relogio.start()

    def _organizar(self, colunas):
        for i, codigo in enumerate(StatusOS.EM_ANDAMENTO):
            self.grade.addWidget(self.kpis[codigo], i // colunas, i % colunas)

    def resizeEvent(self, e):
        if self.mostra_etapas:
            colunas = 7 if self.width() > 1500 else 4 if self.width() > 780 else 2
            self._organizar(colunas)
        super().resizeEvent(e)

    def atualizar(self):
        if self.mostra_etapas:
            for nome, qtd in self.ctrl.relatorio.painel():
                codigo = next(k for k, v in StatusOS.NOMES.items() if v == nome)
                self.kpis[codigo].definir(qtd)
        self.tabela.carregar(lambda: self.ctrl.os.pendencias(self.usuario))
        baixos = self.ctrl.compras.pecas_abaixo_do_minimo() if self.perfil == Perfil.GERENTE else []
        self.alerta.setText("Peças abaixo do estoque mínimo: " + ", ".join(p.descricao for p in baixos))
        self.alerta.setVisible(bool(baixos))


# ------------------------------------------------------------------ ordens de serviço
class PaginaOS(Pagina):
    """RF13 (consulta e filtro) e RF08 (nova OS)."""
    titulo, subtitulo = "Ordens de serviço", "Consulte, filtre e abra as ordens de serviço"

    def __init__(self, principal):
        super().__init__(principal)
        if self.perfil in (Perfil.ATENDENTE, Perfil.GERENTE):
            self._acoes = [Botao("Nova OS", "primario", "plus", "Abrir uma nova ordem de serviço (Ctrl+N)", self.nova_os)]
            QShortcut(QKeySequence("Ctrl+N"), self, activated=self.nova_os)
        filtros = Cartao(nivel=1, margem=ESPACO["m"])
        f, f2 = QHBoxLayout(), QHBoxLayout()
        f.setSpacing(ESPACO["s"])
        f2.setSpacing(ESPACO["s"])
        self.status = selecao([("", "Todos os status")] + list(StatusOS.NOMES.items()), "Status")
        self.status.setCurrentIndex(0)
        self.status.setFixedWidth(200)
        self.status.setAccessibleName("Filtrar por status")
        self.status.currentIndexChanged.connect(lambda _: self.atualizar())
        self.cliente = Busca("Cliente")
        self.placa = Busca("Placa")
        self.placa.setFixedWidth(170)
        for b in (self.cliente, self.placa):
            b.pesquisar.connect(lambda _: self.atualizar())
        self.periodo = SeletorPeriodo()
        self.periodo.mudou.connect(self.atualizar)
        f.addWidget(self.status)
        f.addWidget(self.cliente, 1)
        f.addWidget(self.placa)
        f2.addWidget(rotulo("Abertura", "rotulo"))
        f2.addWidget(self.periodo)
        f2.addStretch(1)
        f2.addWidget(Botao("Limpar filtros", "fantasma", "x", "Limpar os filtros", self.limpar))
        filtros.lay.addLayout(f)
        filtros.lay.addLayout(f2)
        self.lay.addWidget(filtros)
        cartao = Cartao(nivel=1, margem=ESPACO["xs"])
        self.tabela = Tabela(COLUNAS_OS, ("clipboard-list", "Nenhuma OS encontrada",
                                          "Ajuste os filtros ou abra uma nova ordem de serviço."),
                             [("Abrir OS", "eye", principal.abrir_os)])
        self.tabela.setMinimumHeight(420)
        self.tabela.ativado.connect(principal.abrir_os)
        cartao.lay.addWidget(self.tabela)
        self.lay.addWidget(cartao, 1)

    def limpar(self):
        for w in (self.cliente, self.placa):
            w.blockSignals(True)
            w.clear()
            w.blockSignals(False)
        self.periodo.de.definir(None)
        self.periodo.ate.definir(None)
        self.status.setCurrentIndex(0)
        self.atualizar()

    def atualizar(self):
        codigo = self.status.currentData() or None

        def buscar():
            return self.ctrl.os.get_lista(self.usuario, codigo, self.cliente.text().strip(), self.placa.text().strip(),
                                          *self.periodo.get())
        self.tabela.carregar(buscar)

    def nova_os(self):
        r = DialogoNovaOS(self, self.ctrl.cadastro).mostrar()
        if r:
            os_id = executar(self.ctrl.os.abrir_os, self.usuario, r["cliente_id"], r["veiculo_id"], r["problema"],
                             r["km"], pai=self)
            if os_id:
                notificar(self, f"OS nº {os_id} aberta. O mecânico foi avisado no painel.")
                self.atualizar()
                self.principal.abrir_os(os_id)


class DialogoNovaOS(Dialogo):
    def __init__(self, pai, cadastro):
        super().__init__(pai, "Nova ordem de serviço", "Escolha o cliente e o veículo e descreva o problema relatado.",
                         "Abrir OS", largura=560)
        self.cadastro = cadastro
        self.cliente = selecao([(c.id, c.nome) for c in cadastro.get_clientes(so_ativos=True)], "Selecione o cliente")
        self.veiculo = selecao([], "Selecione o veículo")
        self.km = entrada("Ex.: 72300")
        self.problema = area_texto("O que o cliente relatou?")
        self.c_cliente = Campo("Cliente", self.cliente, "Cliente novo? Cadastre antes em Clientes e veículos.", True)
        self.c_veiculo = Campo("Veículo", self.veiculo, obrigatorio=True)
        self.c_km = Campo("Quilometragem de entrada", self.km, obrigatorio=True, validar=inteiro_valido, unidade="km")
        self.c_problema = Campo("Problema relatado", self.problema, obrigatorio=True)
        for c in (self.c_cliente, self.c_veiculo, self.c_km, self.c_problema):
            self.corpo.addWidget(c)
        self.cliente.currentIndexChanged.connect(self._veiculos)

    def _veiculos(self, _):
        veiculos = self.cadastro.get_veiculos(self.cliente.currentData()) if self.cliente.currentIndex() >= 0 else []
        definir_opcoes(self.veiculo, [(v.id, f"{v.placa} · {v.marca} {v.modelo}") for v in veiculos])
        if veiculos:
            self.veiculo.setCurrentIndex(0)
            self.km.setText(str(veiculos[0].km or ""))

    def validar(self):
        ok = [c.validar() for c in (self.c_cliente, self.c_veiculo, self.c_km, self.c_problema)]
        if not all(ok):
            return None
        return {"cliente_id": self.cliente.currentData(), "veiculo_id": self.veiculo.currentData(),
                "km": self.km.text().strip(), "problema": self.problema.toPlainText().strip()}


# ------------------------------------------------------------------ formulários de cadastro
class Formulario(QWidget):
    """Campos em grade de duas colunas; campos: (chave, rótulo, opções ou None, obrigatório, validador, unidade)."""

    def __init__(self, campos, colunas=2):
        super().__init__()
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(ESPACO["m"])
        g.setVerticalSpacing(ESPACO["s"])
        self.campos = {}
        for i, c in enumerate(campos):
            chave, rot = c[0], c[1]
            opcoes = c[2] if len(c) > 2 else None
            obrig = c[3] if len(c) > 3 else False
            val = c[4] if len(c) > 4 else None
            unid = c[5] if len(c) > 5 else None
            senha = chave == "senha"
            controle = selecao(opcoes) if opcoes is not None else entrada("", senha)
            campo = Campo(rot, controle, "Deixe em branco para manter a senha atual." if senha else "", obrig, val, unid)
            g.addWidget(campo, i // colunas, i % colunas)
            self.campos[chave] = campo
        for col in range(colunas):
            g.setColumnStretch(col, 1)

    def obter(self):
        return {k: (str(c.valor()) if c.valor() is not None else "") for k, c in self.campos.items()}

    def validar(self):
        return all([c.validar() for c in self.campos.values()])

    def definir(self, obj):
        for k, c in self.campos.items():
            c.definir(getattr(obj, k, ""))

    def limpar(self):
        for c in self.campos.values():
            c.definir("")
            if c.controle.metaObject().className() == "QComboBox":
                c.controle.setCurrentIndex(-1)


def barra_botoes(*botoes):
    lay = QHBoxLayout()
    lay.setSpacing(ESPACO["xs"])
    for b in botoes:
        if b == "esticar":
            lay.addStretch(1)
        else:
            lay.addWidget(b)
    return lay


class PaginaClientes(Pagina):
    """RF03, RF04 e RF33 (histórico)."""
    titulo, subtitulo = "Clientes e veículos", "Cadastre clientes, seus veículos e consulte o histórico de cada um"

    def __init__(self, principal):
        super().__init__(principal)
        self.cliente_id = self.veiculo_id = None
        divisor = QSplitter(Qt.Horizontal)
        divisor.setChildrenCollapsible(False)
        divisor.setHandleWidth(ESPACO["l"])
        divisor.setStyleSheet("QSplitter::handle { background: transparent; }")
        # clientes
        cc = Cartao("Clientes", "Selecione um cliente para editar ou ver os veículos.")
        self.busca = Busca("Buscar por nome, telefone ou CPF")
        self.busca.pesquisar.connect(lambda _: self.atualizar())
        cc.lay.addWidget(self.busca)
        self.tc = Tabela([{"chave": "id", "titulo": "Cód.", "largura": 60, "numero": True},
                          {"chave": "nome", "titulo": "Nome", "largura": 190},
                          {"chave": "telefone", "titulo": "Telefone", "largura": 140},
                          {"chave": "ativo", "titulo": "Ativo", "largura": 60, "formato": sim_nao}],
                         ("users", "Nenhum cliente encontrado", "Cadastre o primeiro cliente no formulário abaixo."),
                         [("Histórico do cliente", "history", lambda _: self._historico_cliente())], por_pagina=25)
        self.tc.setMinimumHeight(250)
        self.tc.selecionou.connect(self._selecionar_cliente)
        cc.lay.addWidget(self.tc)
        self.fc = Formulario([("nome", "Nome", None, True), ("telefone", "Telefone", None, True),
                              ("cpf", "CPF (opcional)"), ("email", "E-mail")])
        cc.lay.addWidget(self.fc)
        cc.lay.addLayout(barra_botoes(Botao("Novo", "secundario", "plus", "Limpar o formulário para um novo cliente",
                                            self._novo_cliente),
                                      Botao("Salvar", "primario", "save", "Salvar o cliente", self._salvar_cliente),
                                      "esticar",
                                      Botao("Histórico", "fantasma", "history", "Ver as OS do cliente",
                                            self._historico_cliente),
                                      Botao("Ativar/Inativar", "perigo", None, "Ativar ou inativar o cliente",
                                            self._inativar_cliente)))
        divisor.addWidget(cc)
        # veículos
        cv = Cartao("Veículos do cliente", "Placa única: o sistema avisa se ela já estiver cadastrada.")
        self.tv = Tabela([{"chave": "id", "titulo": "Cód.", "largura": 60, "numero": True},
                          {"chave": "placa", "titulo": "Placa", "largura": 100},
                          {"chave": "marca", "titulo": "Marca", "largura": 110},
                          {"chave": "modelo", "titulo": "Modelo", "largura": 110},
                          {"chave": "ano", "titulo": "Ano", "largura": 64, "numero": True},
                          {"chave": "km", "titulo": "Km", "largura": 90, "numero": True}],
                         ("car", "Nenhum veículo", "Selecione um cliente, ou cadastre o veículo dele abaixo."),
                         [("Histórico do veículo", "history", lambda _: self._historico_veiculo())])
        self.tv.setMinimumHeight(250)
        self.tv.selecionou.connect(self._selecionar_veiculo)
        cv.lay.addWidget(self.tv)
        self.fv = Formulario([("placa", "Placa", None, True), ("marca", "Marca", None, True),
                              ("modelo", "Modelo", None, True), ("ano", "Ano", None, False, inteiro_valido),
                              ("km", "Quilometragem", None, False, inteiro_valido, "km")])
        cv.lay.addWidget(self.fv)
        cv.lay.addLayout(barra_botoes(Botao("Novo", "secundario", "plus", "Limpar o formulário para um novo veículo",
                                            self._novo_veiculo),
                                      Botao("Salvar", "primario", "save", "Salvar o veículo", self._salvar_veiculo),
                                      "esticar",
                                      Botao("Histórico do veículo", "fantasma", "history", "Ver as OS do veículo",
                                            self._historico_veiculo)))
        divisor.addWidget(cv)
        divisor.setSizes([1, 1])
        self.lay.addWidget(divisor, 1)

    def atualizar(self):
        self.tc.preencher(self.ctrl.cadastro.get_clientes(self.busca.text().strip()))
        self._listar_veiculos()

    def _listar_veiculos(self):
        self.tv.preencher(self.ctrl.cadastro.get_veiculos(self.cliente_id) if self.cliente_id else [])

    def _selecionar_cliente(self, cid):
        if cid:
            self.cliente_id = cid
            self.fc.definir(self.ctrl.cadastro.get_cliente(cid))
            self._novo_veiculo()
            self._listar_veiculos()

    def _selecionar_veiculo(self, vid):
        if vid:
            self.veiculo_id = vid
            self.fv.definir(self.ctrl.cadastro.get_veiculo(vid))

    def _novo_cliente(self):
        self.cliente_id = None
        self.tc.limpar_selecao()
        self.fc.limpar()
        self._novo_veiculo()
        self._listar_veiculos()
        self.fc.campos["nome"].controle.setFocus()

    def _salvar_cliente(self):
        if not self.fc.validar():
            return
        d = self.fc.obter()
        c = executar(self.ctrl.cadastro.salvar_cliente, self.usuario, d["nome"], d["telefone"], d["cpf"], d["email"],
                     id=self.cliente_id, sucesso="Cliente salvo.", pai=self)
        if c:
            self.cliente_id = c.id
            self.atualizar()

    def _inativar_cliente(self):
        if not self.cliente_id:
            notificar(self, "Selecione um cliente na lista.", "info")
            return
        if confirmar(self, "Ativar ou inativar cliente", "O cliente inativo deixa de aparecer nas buscas, mas o "
                                                         "histórico é mantido. Continuar?", "Confirmar", perigo=True) \
                and executar(self.ctrl.cadastro.alternar_ativo_cliente, self.usuario, self.cliente_id,
                             sucesso="Situação do cliente alterada.", pai=self):
            self.atualizar()

    def _novo_veiculo(self):
        self.veiculo_id = None
        self.tv.limpar_selecao()
        self.fv.limpar()

    def _salvar_veiculo(self):
        if not self.cliente_id:
            notificar(self, "Selecione (ou salve) o cliente primeiro.", "info")
            return
        if not self.fv.validar():
            return
        d = self.fv.obter()
        if executar(self.ctrl.cadastro.salvar_veiculo, self.usuario, self.cliente_id, d["placa"], d["marca"],
                    d["modelo"], d["ano"], d["km"], id=self.veiculo_id, sucesso="Veículo salvo.", pai=self):
            self._listar_veiculos()

    def _historico_cliente(self):
        if not self.cliente_id:
            notificar(self, "Selecione um cliente na lista.", "info")
            return
        janela_historico(self, "Histórico do cliente", self.ctrl.relatorio.historico_manutencao(cliente_id=self.cliente_id),
                         self.principal.abrir_os)

    def _historico_veiculo(self):
        if not self.veiculo_id:
            notificar(self, "Selecione um veículo na lista.", "info")
            return
        janela_historico(self, "Histórico do veículo", self.ctrl.relatorio.historico_manutencao(veiculo_id=self.veiculo_id),
                         self.principal.abrir_os)


class CadastroSimples(QWidget):
    """Lista, pesquisa opcional e formulário (catálogo e usuários)."""

    def __init__(self, titulo, subtitulo, colunas, campos, listar, salvar, alternar=None, pesquisa=False, vazio=None):
        super().__init__()
        self.listar, self.salvar, self.alternar, self.id, self.busca = listar, salvar, alternar, None, None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, ESPACO["m"], 0, 0)
        cartao = Cartao(titulo, subtitulo)
        if pesquisa:
            self.busca = Busca("Pesquisar por descrição ou código (sem precisar de acentos)")
            self.busca.pesquisar.connect(lambda _: self.atualizar())
            cartao.lay.addWidget(self.busca)
        self.tabela = Tabela(colunas, vazio or ("inbox", "Nenhum registro", "Cadastre o primeiro no formulário abaixo."))
        self.tabela.setMinimumHeight(280)
        self.tabela.selecionou.connect(self._selecionar)
        cartao.lay.addWidget(self.tabela)
        self.form = Formulario(campos)
        cartao.lay.addWidget(self.form)
        botoes = [Botao("Novo", "secundario", "plus", "Limpar o formulário", self._novo),
                  Botao("Salvar", "primario", "save", "Salvar o registro", self._salvar), "esticar"]
        if alternar:
            botoes.append(Botao("Ativar/Inativar", "perigo", None, "Ativar ou inativar o registro", self._alternar))
        cartao.lay.addLayout(barra_botoes(*botoes))
        lay.addWidget(cartao)

    def atualizar(self):
        objetos = self.listar(self.busca.text()) if self.busca else self.listar()
        self.objetos = {o.id: o for o in objetos}
        self.tabela.preencher(self.objetos.values())

    def _selecionar(self, i):
        if i:
            self.id = i
            self.form.definir(self.objetos[i])

    def _novo(self):
        self.id = None
        self.tabela.limpar_selecao()
        self.form.limpar()

    def _salvar(self):
        if self.form.validar() and executar(self.salvar, self.form.obter(), self.id, sucesso="Registro salvo.", pai=self):
            self._novo()
            self.atualizar()

    def _alternar(self):
        if not self.id:
            notificar(self, "Selecione um registro na lista.", "info")
            return
        if executar(self.alternar, self.id, sucesso="Situação alterada.", pai=self):
            self.atualizar()


class PaginaCatalogo(Pagina):
    """RF05, RF06 e RF07."""
    titulo, subtitulo = "Catálogo", "Serviços, peças em estoque e fornecedores"

    def __init__(self, principal):
        super().__init__(principal)
        cad, u = self.ctrl.cadastro, self.usuario
        abas = QTabWidget()
        valor = lambda v: numero_valido(v)
        self.partes = [
            CadastroSimples("Serviços", "Valor base usado no cálculo do orçamento.",
                            [{"chave": "id", "titulo": "Cód.", "largura": 64, "numero": True},
                             {"chave": "descricao", "titulo": "Descrição", "largura": 320},
                             {"chave": "valor_base", "titulo": "Valor base", "largura": 120, "numero": True, "formato": moeda},
                             {"chave": "ativo", "titulo": "Ativo", "largura": 70, "formato": sim_nao}],
                            [("descricao", "Descrição", None, True), ("valor_base", "Valor base", None, True, valor, "R$")],
                            lambda busca: cad.get_servicos(busca=busca),
                            lambda d, id: cad.salvar_servico(u, d["descricao"], d["valor_base"], id),
                            lambda id: cad.alternar_ativo_servico(u, id), pesquisa=True),
            CadastroSimples("Peças e estoque", "Peças abaixo do mínimo aparecem em vermelho e no painel.",
                            [{"chave": "id", "titulo": "Cód.", "largura": 64, "numero": True},
                             {"chave": "descricao", "titulo": "Descrição", "largura": 300},
                             {"chave": "valor", "titulo": "Valor", "largura": 110, "numero": True, "formato": moeda},
                             {"chave": "qtd_estoque", "titulo": "Estoque", "largura": 90, "numero": True},
                             {"chave": "estoque_minimo", "titulo": "Mínimo", "largura": 90, "numero": True}],
                            [("descricao", "Descrição", None, True), ("valor", "Valor", None, True, valor, "R$"),
                             ("qtd_estoque", "Quantidade em estoque", None, True, inteiro_valido, "un."),
                             ("estoque_minimo", "Estoque mínimo", None, True, inteiro_valido, "un.")],
                            cad.get_pecas,
                            lambda d, id: cad.salvar_peca(u, d["descricao"], d["valor"], d["qtd_estoque"],
                                                          d["estoque_minimo"], id), pesquisa=True),
            CadastroSimples("Fornecedores", "Usados ao registrar a compra de peças.",
                            [{"chave": "id", "titulo": "Cód.", "largura": 64, "numero": True},
                             {"chave": "nome", "titulo": "Nome", "largura": 280},
                             {"chave": "telefone", "titulo": "Telefone", "largura": 150},
                             {"chave": "email", "titulo": "E-mail", "largura": 220}],
                            [("nome", "Nome", None, True), ("telefone", "Telefone"), ("email", "E-mail")],
                            cad.get_fornecedores,
                            lambda d, id: cad.salvar_fornecedor(u, d["nome"], d["telefone"], d["email"], id)),
        ]
        self.partes[1].tabela.cor_por_linha(
            lambda p: Tema.cor("erro") if p.qtd_estoque < p.estoque_minimo else None)
        for parte, (texto, ic) in zip(self.partes, (("Serviços", "wrench"), ("Peças e estoque", "package"),
                                                    ("Fornecedores", "truck"))):
            abas.addTab(parte, icone(ic, Tema.cor("texto_2"), 16), texto)
        abas.currentChanged.connect(lambda i: self.partes[i].atualizar())
        self.lay.addWidget(abas, 1)

    def atualizar(self):
        for p in self.partes:
            p.atualizar()


class PaginaConsulta(Pagina):
    """Pesquisa de serviços e peças (preço e estoque) para o atendente e o mecânico, só para consulta."""
    titulo, subtitulo = "Peças e serviços", "Consulte preços e o estoque e peça a compra de peças, com ou sem OS"

    def __init__(self, principal):
        super().__init__(principal)
        topo = Cartao(nivel=1, margem=ESPACO["m"])
        self.busca = Busca("Pesquisar serviço ou peça por descrição ou código (sem precisar de acentos)")
        self.busca.pesquisar.connect(lambda _: self.atualizar())
        self.resumo = rotulo("", "legenda")
        self.so_falta = Interruptor("Só peças em falta")
        self.so_falta.setToolTip("Mostrar só as peças sem estoque ou abaixo do estoque mínimo")
        self.so_falta.toggled.connect(lambda _: self.atualizar())
        topo.lay.addLayout(barra_botoes(self.busca, self.so_falta, self.resumo))
        self.lay.addWidget(topo)
        self._acoes = [Botao("Solicitar compra", "primario", "shopping-cart",
                             "Pedir a compra da peça selecionada (ou de outra), para uma OS ou para o estoque",
                             lambda: self.solicitar(self.tp.id_selecionado()))]
        divisor = QSplitter(Qt.Horizontal)
        divisor.setChildrenCollapsible(False)
        divisor.setHandleWidth(ESPACO["l"])
        divisor.setStyleSheet("QSplitter::handle { background: transparent; }")
        cs = Cartao("Serviços")
        self.ts = Tabela([{"chave": "id", "titulo": "Cód.", "largura": 64, "numero": True},
                          {"chave": "descricao", "titulo": "Descrição", "largura": 260},
                          {"chave": "valor_base", "titulo": "Valor", "largura": 110, "numero": True, "formato": moeda}],
                         ("search", "Nenhum serviço encontrado", "Tente outra palavra ou o código."))
        self.ts.setMinimumHeight(420)
        cs.lay.addWidget(self.ts)
        cp = Cartao("Peças e estoque")
        self.tp = Tabela([{"chave": "id", "titulo": "Cód.", "largura": 64, "numero": True},
                          {"chave": "descricao", "titulo": "Descrição", "largura": 220},
                          {"chave": "valor", "titulo": "Valor", "largura": 100, "numero": True, "formato": moeda},
                          {"chave": "qtd_estoque", "titulo": "Estoque", "largura": 84, "numero": True},
                          {"chave": "situacao", "titulo": "Situação", "largura": 140}],
                         ("package", "Nenhuma peça encontrada", "Tente outra palavra ou o código."))
        self.tp.setMinimumHeight(420)
        self.tp.cor_por_linha(lambda p: Tema.cor("erro") if p.situacao != "Disponível" else None)
        self.tp.acoes = [("Solicitar compra desta peça", "shopping-cart", self.solicitar)]
        self.tp.ativado.connect(self.solicitar)
        cp.lay.addWidget(self.tp)
        cp.lay.addWidget(rotulo("Duplo clique numa peça (ou botão direito) para pedir a compra dela.", "legenda", True))
        divisor.addWidget(cs)
        divisor.addWidget(cp)
        divisor.setStretchFactor(0, 2)      # a tabela de peças tem mais colunas, então fica com mais espaço
        divisor.setStretchFactor(1, 3)
        divisor.setSizes([400, 600])
        self.lay.addWidget(divisor, 1)

    def atualizar(self):
        busca = self.busca.text()
        servicos, pecas = self.ctrl.cadastro.get_servicos(True, busca), self.ctrl.cadastro.get_pecas(busca)
        for p in pecas:
            p.situacao = ("Sem estoque" if p.qtd_estoque <= 0 else
                          "Abaixo do mínimo" if p.qtd_estoque < p.estoque_minimo else "Disponível")
        if self.so_falta.isChecked():
            pecas = [p for p in pecas if p.situacao != "Disponível"]
        self.ts.preencher(servicos)
        self.tp.preencher(pecas)
        self.resumo.setText(f"{len(servicos)} serviço(s) e {len(pecas)} peça(s)")

    def solicitar(self, peca_id=None):
        if solicitar_compra(self, self.ctrl, self.usuario, peca_id):
            self.atualizar()


class PaginaUsuarios(Pagina):
    """RF02."""
    titulo, subtitulo = "Usuários", "Funcionários com acesso ao sistema e o perfil de cada um"

    def __init__(self, principal):
        super().__init__(principal)
        auth, u = self.ctrl.auth, self.usuario
        self.cadastro = CadastroSimples(
            "Funcionários", "O usuário inativo não entra no sistema, mas o histórico dele é mantido.",
            [{"chave": "id", "titulo": "Cód.", "largura": 64, "numero": True},
             {"chave": "nome", "titulo": "Nome", "largura": 240}, {"chave": "login", "titulo": "Login", "largura": 150},
             {"chave": "perfil", "titulo": "Perfil", "largura": 130, "formato": lambda p: Perfil.NOMES.get(p, p)},
             {"chave": "ativo", "titulo": "Ativo", "largura": 70, "formato": sim_nao}],
            [("nome", "Nome", None, True), ("login", "Login", None, True),
             ("perfil", "Perfil", [(p, Perfil.NOMES[p]) for p in Perfil.TODOS], True), ("senha", "Senha")],
            auth.get_usuarios, lambda d, id: auth.salvar_usuario(u, d["nome"], d["login"], d["perfil"], d.get("senha"), id),
            lambda id: auth.alternar_ativo(u, id), vazio=("user-cog", "Nenhum usuário", ""))
        self.lay.addWidget(self.cadastro)
        self.lay.addStretch(1)

    def atualizar(self):
        self.cadastro.atualizar()


COLUNAS_COMPRAS = [
    {"chave": "id", "titulo": "Nº", "largura": 64, "numero": True},
    {"chave": "data_solicitacao", "titulo": "Data", "largura": 100, "formato": lambda d: data_br(d) if d else "—"},
    {"chave": "origem", "titulo": "Para", "largura": 90},
    {"chave": "peca_descricao", "titulo": "Peça", "largura": 230},
    {"chave": "quantidade", "titulo": "Qtd.", "largura": 64, "numero": True},
    {"chave": "situacao", "titulo": "Situação", "largura": 130, "status": True,
     "formato": lambda s: SituacaoCompra.NOMES.get(s, s)},
    {"chave": "solicitante_nome", "titulo": "Solicitante", "largura": 150, "dica": True},
    {"chave": "fornecedor_nome", "titulo": "Fornecedor", "largura": 180, "dica": True},
]
EM_ABERTO = "EM_ABERTO"


class PaginaCompras(Pagina):
    """RF22 e RF23: solicitações de compra, com filtros. Todos os perfis pedem peças (com ou sem OS);
    o gerente registra a compra, o recebimento e o cancelamento; quem pediu altera ou cancela a sua pendente."""
    titulo = "Compras"

    def __init__(self, principal):
        super().__init__(principal)
        self.gerente = self.perfil == Perfil.GERENTE
        self.subtitulo = ("Solicitações de peças: registre a compra e o recebimento e acompanhe os pedidos"
                          if self.gerente else "Peça peças para uma OS ou para repor o estoque e acompanhe cada pedido")
        self._acoes = [Botao("Nova solicitação", "primario", "plus", "Pedir a compra de uma peça, com ou sem OS",
                             self.nova)]
        # indicadores por situação (clique filtra)
        kp = QHBoxLayout()
        kp.setSpacing(ESPACO["s"])
        self.kpis = {}
        for sit, nome, ic, ajuda in [(SituacaoCompra.PENDENTE, "Pendentes", "inbox", "Esperando a compra"),
                                     (SituacaoCompra.COMPRADA, "Compradas", "truck", "Esperando a entrega"),
                                     (SituacaoCompra.RECEBIDA, "Recebidas", "package", "Já entraram no estoque"),
                                     (SituacaoCompra.CANCELADA, "Canceladas", "circle-x", "Pedidos desistidos")]:
            k = Kpi(nome, "0", lambda s=sit: Tema.status(s)[0], ic, ajuda)
            k.setCursor(Qt.PointingHandCursor)
            k.setToolTip(f"Mostrar só as solicitações {nome.lower()}")
            k.mousePressEvent = lambda _e, s=sit: self._filtrar_situacao(s)
            self.kpis[sit] = k
            kp.addWidget(k)
        self.lay.addLayout(kp)
        # filtros
        filtros = Cartao(nivel=1, margem=ESPACO["m"])
        f, f2 = QHBoxLayout(), QHBoxLayout()
        f.setSpacing(ESPACO["s"])
        f2.setSpacing(ESPACO["s"])
        self.situacao = selecao([("", "Todas as situações"), (EM_ABERTO, "Em aberto")] +
                                [(s, SituacaoCompra.NOMES[s]) for s in SituacaoCompra.TODAS], "Situação")
        self.situacao.setFixedWidth(230)
        self.situacao.setAccessibleName("Filtrar por situação")
        self.situacao.setToolTip("Em aberto: pendentes e compradas, ainda sem entrega")
        self.origem = selecao([("", "Para OS e estoque"), ("OS", "Só para OS"), ("ESTOQUE", "Só para o estoque")],
                              "Para")
        self.origem.setFixedWidth(170)
        self.origem.setAccessibleName("Filtrar por destino")
        self.fornecedor = selecao([("", "Todos os fornecedores")], "Fornecedor")
        self.fornecedor.setFixedWidth(200)
        self.fornecedor.setAccessibleName("Filtrar por fornecedor")
        for cb in (self.situacao, self.origem, self.fornecedor):
            cb.setCurrentIndex(0)
        self.situacao.setCurrentIndex(1)          # começa pelas que estão em aberto
        for cb in (self.situacao, self.origem, self.fornecedor):
            cb.currentIndexChanged.connect(lambda _: self.atualizar())
        self.peca = Busca("Peça (descrição ou código)")
        self.num_os = Busca("Nº da OS")
        self.num_os.setFixedWidth(120)
        self.peca.setMinimumWidth(160)
        for b in (self.peca, self.num_os):
            b.pesquisar.connect(lambda _: self.atualizar())
        self.periodo = SeletorPeriodo()
        self.periodo.mudou.connect(self.atualizar)
        self.minhas = Interruptor("Só as minhas")
        self.minhas.setToolTip("Mostrar só as solicitações feitas por você")
        self.minhas.toggled.connect(lambda _: self.atualizar())
        f.addWidget(self.situacao)
        f.addWidget(self.origem)
        f.addWidget(self.fornecedor)
        f.addWidget(self.peca, 1)
        f.addWidget(self.num_os)
        f2.addWidget(rotulo("Solicitada", "rotulo"))
        f2.addWidget(self.periodo)
        f2.addSpacing(ESPACO["s"])
        f2.addWidget(self.minhas)
        f2.addStretch(1)
        f2.addWidget(Botao("Limpar filtros", "fantasma", "x", "Limpar os filtros", self.limpar))
        filtros.lay.addLayout(f)
        filtros.lay.addLayout(f2)
        self.lay.addWidget(filtros)
        # lista
        cartao = Cartao("Solicitações", "Duplo clique abre a OS do pedido. Com o botão direito aparecem as ações da "
                                        "linha. Ao registrar o recebimento, o estoque é atualizado e a OS volta para "
                                        "execução.")
        acoes = [("Abrir OS", "eye", lambda _: self.abrir_os()),
                 ("Alterar quantidade", "pencil", lambda _: self.alterar())]
        if self.gerente:
            acoes += [("Registrar compra", "shopping-cart", lambda _: self.comprar()),
                      ("Registrar recebimento", "package", lambda _: self.receber())]
        acoes.append(("Cancelar solicitação", "circle-x", lambda _: self.cancelar()))
        self.tabela = Tabela(COLUNAS_COMPRAS, ("shopping-cart", "Nenhuma solicitação",
                                               "Ajuste os filtros ou use Nova solicitação para pedir uma peça."), acoes)
        self.tabela.setMinimumHeight(400)
        self.tabela.selecionou.connect(lambda _: self._habilitar())
        self.tabela.ativado.connect(lambda _: self.abrir_os() if self._sel() and self._sel().os_id else self.alterar())
        cartao.lay.addWidget(self.tabela)
        self.detalhe = rotulo("", "legenda", True)        # tudo sobre a solicitação selecionada
        self.detalhe.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cartao.lay.addWidget(self.detalhe)
        self.b_os = Botao("Abrir OS", "fantasma", "eye", "Abrir a OS ligada à solicitação", self.abrir_os)
        self.b_alterar = Botao("Alterar quantidade", "secundario", "pencil",
                               "Mudar a quantidade ou a observação de uma solicitação pendente", self.alterar)
        self.b_comprar = Botao("Registrar compra", "secundario", "shopping-cart",
                               "Registrar a compra da solicitação selecionada", self.comprar)
        self.b_receber = Botao("Registrar recebimento", "secundario", "package", "Registrar a chegada das peças",
                               self.receber)
        self.b_cancelar = Botao("Cancelar solicitação", "perigo", "circle-x", "Cancelar a solicitação selecionada",
                                self.cancelar)
        botoes = [self.b_os, self.b_alterar] + ([self.b_comprar, self.b_receber] if self.gerente else [])
        cartao.lay.addLayout(barra_botoes(*botoes, "esticar", self.b_cancelar))
        self.b_comprar.setVisible(self.gerente)
        self.b_receber.setVisible(self.gerente)
        self.lay.addWidget(cartao, 1)
        self._habilitar()

    # ---- filtros e lista
    def _filtrar_situacao(self, sit):
        self.situacao.setCurrentIndex(self.situacao.findData(sit))

    def limpar(self):
        for w in (self.peca, self.num_os):
            w.blockSignals(True)
            w.clear()
            w.blockSignals(False)
        for cb in (self.origem, self.fornecedor):
            cb.blockSignals(True)
            cb.setCurrentIndex(0)
            cb.blockSignals(False)
        self.minhas.blockSignals(True)
        self.minhas.setChecked(False)
        self.minhas.blockSignals(False)
        self.periodo.de.definir(None)
        self.periodo.ate.definir(None)
        self.situacao.setCurrentIndex(0)
        self.atualizar()

    def _fornecedores(self):
        atual = self.fornecedor.currentData()
        self.fornecedor.blockSignals(True)
        definir_opcoes(self.fornecedor, [("", "Todos os fornecedores")] +
                       [(f.id, f.nome) for f in self.ctrl.cadastro.get_fornecedores()])
        i = self.fornecedor.findData(atual)
        self.fornecedor.setCurrentIndex(i if i >= 0 else 0)
        self.fornecedor.blockSignals(False)

    def atualizar(self):
        for sit, qtd in self.ctrl.compras.resumo_solicitacoes().items():
            self.kpis[sit].definir(qtd)
        if self.fornecedor.count() <= 1:
            self._fornecedores()
        sit = self.situacao.currentData() or None
        if sit == EM_ABERTO:
            sit = [SituacaoCompra.PENDENTE, SituacaoCompra.COMPRADA]
        de, ate = self.periodo.get()

        def buscar():
            return self.ctrl.compras.get_solicitacoes(
                sit, self.num_os.text().strip() or None, self.peca.text().strip(), self.fornecedor.currentData() or None,
                self.origem.currentData() or None, de, ate, self.usuario.id if self.minhas.isChecked() else None)
        self.tabela.carregar(buscar)
        self._habilitar()

    # ---- ações
    def _sel(self):
        return self.tabela.objeto_selecionado()

    def _pode_mexer(self, s):
        return s.situacao == SituacaoCompra.PENDENTE and (self.gerente or s.solicitante_id == self.usuario.id)

    def _habilitar(self):
        s = self._sel()
        if s:
            partes = [f"Solicitação nº {s.id}: {s.quantidade} un. de {s.peca_descricao}",
                      f"para a OS {s.os_id}" if s.os_id else "para o estoque",
                      f"pedida por {s.solicitante_nome or 'não informado'} em {data_br(s.data_solicitacao, True) or '—'}",
                      SituacaoCompra.NOMES.get(s.situacao, s.situacao)]
            if s.fornecedor_nome:
                partes.append(f"fornecedor {s.fornecedor_nome}")
            obs = f"\nObservação: {s.observacao}" if s.observacao else ""
            self.detalhe.setText(" · ".join(partes) + obs)
        else:
            self.detalhe.setText("Selecione uma solicitação para ver os detalhes e as ações disponíveis.")
        self.b_os.setEnabled(bool(s and s.os_id))
        self.b_alterar.setEnabled(bool(s and self._pode_mexer(s)))
        self.b_comprar.setEnabled(bool(s and s.situacao == SituacaoCompra.PENDENTE))
        self.b_receber.setEnabled(bool(s and s.situacao == SituacaoCompra.COMPRADA))
        self.b_cancelar.setEnabled(bool(s and (self._pode_mexer(s) or (
            self.gerente and s.situacao == SituacaoCompra.COMPRADA))))

    def _escolhida(self):
        s = self._sel()
        if not s:
            notificar(self, "Selecione a solicitação na lista.", "info")
        return s

    def nova(self):
        if solicitar_compra(self, self.ctrl, self.usuario):
            self.atualizar()

    def abrir_os(self):
        s = self._escolhida()
        if s and not s.os_id:
            notificar(self, "Esta solicitação é para o estoque; não tem OS.", "info")
        elif s:
            self.principal.abrir_os(s.os_id)

    def alterar(self):
        s = self._escolhida()
        if s and alterar_solicitacao(self, self.ctrl, self.usuario, s):
            self.atualizar()

    def comprar(self):
        s = self._escolhida()
        if not s:
            return
        r = pedir(self, "Registrar compra", [("f", "Fornecedor",
                                              [(f.id, f.nome) for f in self.ctrl.cadastro.get_fornecedores()])],
                  subtitulo=f"{s.quantidade} un. de {s.peca_descricao} ({s.origem}). Escolha o fornecedor que vai "
                            "entregar as peças.", texto_ok="Registrar compra")
        if r and executar(self.ctrl.compras.registrar_compra, self.usuario, s.id, r["f"], sucesso="Compra registrada.",
                          pai=self):
            self.atualizar()

    def receber(self):
        s = self._escolhida()
        if s and executar(self.ctrl.compras.registrar_recebimento, self.usuario, s.id,
                          sucesso="Recebimento registrado; estoque atualizado.", pai=self):
            self.atualizar()

    def cancelar(self):
        s = self._escolhida()
        if s and confirmar(self, "Cancelar solicitação", f"A solicitação nº {s.id} ({s.peca_descricao}) será "
                                                         "cancelada. Continuar?", "Cancelar solicitação", perigo=True) \
                and executar(self.ctrl.compras.cancelar_solicitacao, self.usuario, s.id,
                             sucesso="Solicitação cancelada.", pai=self):
            self.atualizar()


class PaginaRelatorios(Pagina):
    """RF34: indicadores e gráficos do período, com exportação em PDF."""
    titulo, subtitulo = "Relatórios", "Indicadores do período, pela data de abertura das OS"

    def __init__(self, principal):
        super().__init__(principal)
        self._acoes = [Botao("Exportar PDF", "secundario", "file-down", "Salvar o relatório em PDF", self.exportar)]
        filtros = Cartao(nivel=1, margem=ESPACO["m"])
        self.periodo = SeletorPeriodo()
        self.periodo.mudou.connect(self.atualizar)
        filtros.lay.addLayout(barra_botoes(self.periodo, "esticar",
                                           Botao("Gerar relatório", "primario", "refresh-cw", "Gerar o relatório",
                                                 self.atualizar)))
        self.lay.addWidget(filtros)
        k = QHBoxLayout()
        k.setSpacing(ESPACO["s"])
        self.k_total = Kpi("Ordens de serviço", "0", lambda: Tema.cor("primaria"), "clipboard-list")
        self.k_fat = Kpi("Faturamento", "R$ 0,00", lambda: Tema.cor("sucesso"), "banknote", "Pagamentos recebidos")
        self.k_tempo = Kpi("Tempo médio", "—", lambda: Tema.cor("destaque"), "history", "Da abertura à conclusão")
        for w in (self.k_total, self.k_fat, self.k_tempo):
            k.addWidget(w)
        self.lay.addLayout(k)
        grade = QGridLayout()
        grade.setSpacing(ESPACO["l"])
        self.g_status = GraficoBarras(str, "Nenhuma OS no período.")
        self.g_serv = GraficoBarras(str, "Nenhum serviço em OS encerradas.")
        self.g_pecas = GraficoBarras(str, "Nenhuma peça em OS encerradas.")
        c1 = Cartao("OS por status", "Todas as OS abertas no período")
        c1.lay.addWidget(self.g_status)
        c2 = Cartao("Serviços mais realizados", "Nas OS encerradas")
        c2.lay.addWidget(self.g_serv)
        c3 = Cartao("Peças mais utilizadas", "Nas OS encerradas")
        c3.lay.addWidget(self.g_pecas)
        for cartao in (c1, c2, c3):
            cartao.lay.addStretch(1)
        grade.addWidget(c1, 0, 0, 2, 1)
        grade.addWidget(c2, 0, 1)
        grade.addWidget(c3, 1, 1)
        grade.setColumnStretch(0, 1)
        grade.setColumnStretch(1, 1)
        self.lay.addLayout(grade)
        self.lay.addStretch(1)
        self.relatorio = None

    def atualizar(self):
        r = executar(self.ctrl.relatorio.gerar, self.usuario, *self.periodo.get(), pai=self)
        if not r:
            return
        self.relatorio = r
        codigo = {v: k for k, v in StatusOS.NOMES.items()}
        self.k_total.definir(sum(n for _, n in r["por_status"]))
        self.k_fat.definir(moeda(r["faturamento"]))
        tm = r["tempo_medio_horas"]
        self.k_tempo.definir("—" if tm is None else f"{tm:.1f} h".replace(".", ","))
        self.g_status.definir([(nome, n, Tema.status(codigo.get(nome))[0]) for nome, n in r["por_status"]])
        self.g_serv.definir([(d, q, None) for d, q in r["servicos"]])
        self.g_pecas.definir([(d, q, Tema.cor("destaque")) for d, q in r["pecas"]])

    def exportar(self):
        if not self.relatorio:
            return
        de, ate = self.relatorio["data_inicio"], self.relatorio["data_fim"]
        nome = "relatorio_gerencial" + (f"_{de}" if de else "") + (f"_a_{ate}" if ate else "") + ".pdf"
        salvar_e_abrir_pdf(self, nome, lambda caminho: self.ctrl.relatorio.exportar_pdf(self.usuario, self.relatorio,
                                                                                         caminho))

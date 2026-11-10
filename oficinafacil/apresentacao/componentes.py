"""Biblioteca de componentes da interface (PySide6), construída sobre os tokens de tema.py.

Botões, campos com rótulo/ajuda/erro, data, busca, interruptor, cartões, selos, avatar, tabela com ordenação,
paginação, ações por linha e estados vazio/carregando/erro, toasts, modais, indicadores (KPI) e gráfico de barras.
"""
import os
from datetime import date, timedelta

from PySide6.QtCore import (Property, QAbstractTableModel, QDate, QEasingCurve, QModelIndex, QPoint,
                            QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, QUrl, Signal)
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCalendarWidget, QCheckBox, QComboBox, QDialog,
                               QFileDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy,
                               QSpinBox, QStackedLayout, QStyle, QStyledItemDelegate, QTableView, QVBoxLayout, QWidget,
                               QWidgetAction)

from ..modelo import RegraNegocioError, data_br, moeda
from ..modelo.atendimento import StatusOS
from .tema import ESPACO, RAIO, SOMBRAS, Tema, duracao, fonte, icone

TITULO = "OficinaFácil"


# ------------------------------------------------------------------ utilitários
def estilo(widget, **props):
    """Define propriedades dinâmicas usadas pelo QSS (papel, variante, erro...) e reaplica o estilo."""
    for k, v in props.items():
        widget.setProperty(k, v)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget


def rotulo(texto, papel=None, quebra=False):
    lb = QLabel(texto)
    if papel:
        lb.setProperty("papel", papel)
    lb.setWordWrap(quebra)
    return lb


def sombra(widget, nivel=1):
    blur, dy, alpha = SOMBRAS[nivel]
    ef = QGraphicsDropShadowEffect(widget)
    ef.setBlurRadius(blur)
    ef.setOffset(0, dy)
    cor = QColor(Tema.cor("sombra"))
    cor.setAlphaF(min(alpha * (2.2 if Tema.nome == "escuro" else 1), 1.0))
    ef.setColor(cor)
    widget.setGraphicsEffect(ef)
    return widget


def _montar(lay, itens):
    for w in itens:
        if w == "esticar":
            lay.addStretch(1)
        elif isinstance(w, int):
            lay.addSpacing(w)
        elif isinstance(w, QWidget):
            lay.addWidget(w)
        else:
            lay.addLayout(w)
    return lay


def linha(*itens, espaco=ESPACO["xs"]):
    lay = QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(espaco)
    return _montar(lay, itens)


def coluna(*itens, espaco=ESPACO["xs"]):
    lay = QVBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(espaco)
    return _montar(lay, itens)


def opcao(id, texto):
    return (id, texto)


def id_da_opcao(valor):
    if isinstance(valor, tuple):
        return valor[0]
    if isinstance(valor, int):
        return valor
    try:
        return int(str(valor).split(" - ")[0])
    except ValueError:
        return None


def sim_nao(v):
    return "Sim" if v else "Não"


def janela_de(widget):
    return widget.window() if widget is not None else QApplication.activeWindow()


# ------------------------------------------------------------------ toasts
class Toast(QFrame):
    TIPOS = {"sucesso": ("sucesso", "circle-check"), "erro": ("erro", "circle-x"),
             "alerta": ("alerta", "triangle-alert"), "info": ("info", "info")}

    def __init__(self, pai, texto, tipo):
        super().__init__(pai)
        chave, ic = self.TIPOS.get(tipo, self.TIPOS["info"])
        cor = Tema.cor(chave)
        self.setObjectName("Toast")
        self.setStyleSheet(f"QFrame#Toast {{ background: {Tema.cor('superficie')}; border: 1px solid {Tema.cor('borda')};"
                           f" border-left: 4px solid {cor}; border-radius: {RAIO['m']}px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 10, 12)
        lay.setSpacing(10)
        ico = QLabel()
        ico.setPixmap(icone(ic, cor, 20).pixmap(20, 20))
        lay.addWidget(ico, 0, Qt.AlignTop)
        lb = QLabel(texto)
        lb.setWordWrap(True)
        lb.setMinimumWidth(240)
        lb.setMaximumWidth(360)
        lay.addWidget(lb, 1)
        fechar = botao_icone("x", "Fechar aviso", self.sumir)
        fechar.setFixedSize(26, 26)
        lay.addWidget(fechar, 0, Qt.AlignTop)
        self.setAccessibleName(texto)
        self.opacidade = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacidade)
        self.adjustSize()

    def mostrar(self, ms):
        self.show()
        self.raise_()
        self._animar(0.0, 1.0)
        QTimer.singleShot(ms, self.sumir)

    def _animar(self, de, ate, fim=None):
        self.anim = QPropertyAnimation(self.opacidade, b"opacity", self)
        self.anim.setDuration(duracao("media"))
        self.anim.setStartValue(de)
        self.anim.setEndValue(ate)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        if fim:
            self.anim.finished.connect(fim)
        self.anim.start()

    def sumir(self):
        try:
            if self.isVisible():
                self._animar(1.0, 0.0, self._remover)
        except RuntimeError:
            pass

    def _remover(self):
        janela = self.parent()
        self.hide()
        self.deleteLater()
        QTimer.singleShot(0, lambda: organizar_toasts(janela))


def organizar_toasts(janela):
    try:
        toasts = [t for t in janela.findChildren(Toast) if t.isVisible()]
        y = janela.height() - ESPACO["l"]
    except RuntimeError:
        return
    for t in reversed(toasts):
        t.adjustSize()
        y -= t.height()
        t.move(janela.width() - t.width() - ESPACO["l"], y)
        y -= ESPACO["xs"]


def notificar(widget, texto, tipo="sucesso"):
    """Aviso rápido no canto inferior direito da janela, que some sozinho (toast)."""
    janela = janela_de(widget)
    if janela is None:
        return
    t = Toast(janela, texto, tipo)
    t.show()
    organizar_toasts(janela)
    t.mostrar(5200 if tipo in ("erro", "alerta") else 3600)


def executar(func, *args, sucesso=None, pai=None, **kwargs):
    """Chama um método de controlador; uma regra de negócio violada vira um aviso de erro (o sistema não para)."""
    try:
        resultado = func(*args, **kwargs)
    except RegraNegocioError as e:
        notificar(pai, str(e), "erro")
        return None
    if sucesso:
        notificar(pai, sucesso, "sucesso")
    return resultado if resultado is not None else True


# ------------------------------------------------------------------ botões
class Botao(QPushButton):
    """variante: primario, secundario, fantasma, perigo, perigo_cheio ou icone."""

    def __init__(self, texto="", variante="secundario", ic=None, dica=None, ao_clicar=None):
        super().__init__(texto)
        self.variante, self.nome_icone, self._texto = variante, ic, texto
        estilo(self, variante=variante)
        self.setCursor(Qt.PointingHandCursor)
        if dica:
            self.setToolTip(dica)
            self.setAccessibleName(dica)
        if ao_clicar:
            self.clicked.connect(lambda _=False: ao_clicar())
        self._aplicar_icone()
        Tema.ouvintes.append(self._aplicar_icone)

    def _cor_icone(self):
        return {"primario": Tema.cor("sobre_primaria"), "perigo": Tema.cor("erro"),
                "perigo_cheio": Tema.cor("superficie")}.get(self.variante, Tema.cor("texto_2"))

    def _aplicar_icone(self):
        if self.nome_icone:
            self.setIcon(icone(self.nome_icone, self._cor_icone(), 16))
            self.setIconSize(QSize(16, 16))

    def carregando(self, sim=True):
        """Estado carregando: desabilita e troca o texto, evitando clique duplo."""
        self.setEnabled(not sim)
        self.setText("Aguarde..." if sim else self._texto)
        QApplication.processEvents()


def botao_icone(nome, dica, ao_clicar=None):
    b = Botao("", "icone", nome, dica, ao_clicar)
    b.setFixedSize(34, 34)
    return b


# ------------------------------------------------------------------ campos
class Campo(QWidget):
    """Rótulo, controle, texto de ajuda e mensagem de erro, com validação enquanto o usuário digita."""
    alterado = Signal()

    def __init__(self, rotulo_texto, controle, ajuda="", obrigatorio=False, validar=None, unidade=None):
        super().__init__()
        self.controle, self.obrigatorio, self.validador = controle, obrigatorio, validar
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.rotulo = rotulo(rotulo_texto + (" *" if obrigatorio else ""), "rotulo")
        self.rotulo.setBuddy(controle)
        lay.addWidget(self.rotulo)
        if unidade:
            h = QHBoxLayout()
            h.setSpacing(8)
            h.addWidget(controle, 1)
            h.addWidget(rotulo(unidade, "unidade"))
            lay.addLayout(h)
        else:
            lay.addWidget(controle)
        self.ajuda = rotulo(ajuda, "ajuda", True)
        self.ajuda.setVisible(bool(ajuda))
        lay.addWidget(self.ajuda)
        self.msg_erro = rotulo("", "erro", True)
        self.msg_erro.hide()
        lay.addWidget(self.msg_erro)
        controle.setAccessibleName(rotulo_texto)
        for nome in ("textChanged", "currentIndexChanged", "valueChanged"):
            sinal = getattr(controle, nome, None)
            if sinal is not None:
                sinal.connect(self._mudou)
                break

    def _mudou(self, *_):
        if self.msg_erro.isVisible():
            self.validar()
        self.alterado.emit()

    def valor(self):
        c = self.controle
        if isinstance(c, QComboBox):
            if c.currentIndex() < 0:
                return ""
            dado = c.currentData()
            return dado if dado is not None else c.currentText()
        if isinstance(c, QPlainTextEdit):
            return c.toPlainText().strip()
        if isinstance(c, QSpinBox):
            return str(c.value())
        if hasattr(c, "get"):
            return c.get()
        return c.text().strip()

    def definir(self, valor):
        c = self.controle
        valor = "" if valor is None else valor
        if isinstance(c, QComboBox):
            i = c.findData(valor)
            c.setCurrentIndex(i if i >= 0 else c.findText(str(valor)))
        elif isinstance(c, QPlainTextEdit):
            c.setPlainText(str(valor))
        elif isinstance(c, QSpinBox):
            c.setValue(int(valor or c.minimum()))
        elif hasattr(c, "definir"):
            c.definir(valor)
        else:
            c.setText(str(valor))
        self.erro("")

    def erro(self, msg=""):
        self.msg_erro.setText(msg)
        self.msg_erro.setVisible(bool(msg))
        self.ajuda.setVisible(bool(self.ajuda.text()) and not msg)
        estilo(self.controle, erro="true" if msg else "false")

    def validar(self):
        v = self.valor()
        if self.obrigatorio and (v is None or str(v).strip() == ""):
            self.erro("Preencha este campo.")
            return False
        if self.validador and str(v).strip():
            msg = self.validador(v)
            if msg:
                self.erro(msg)
                return False
        self.erro("")
        return True


def entrada(placeholder="", senha=False):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    if senha:
        e.setEchoMode(QLineEdit.Password)
    return e


def selecao(opcoes=(), placeholder="Selecione..."):
    """opcoes: textos ou pares (id, texto); o valor devolvido é o id (ou o texto)."""
    cb = QComboBox()
    cb.setPlaceholderText(placeholder)
    definir_opcoes(cb, opcoes)
    return cb


def definir_opcoes(cb, opcoes):
    cb.blockSignals(True)
    cb.clear()
    for o in opcoes:
        if isinstance(o, tuple):
            cb.addItem(str(o[1]), o[0])
        else:
            cb.addItem(str(o), o)
    cb.setCurrentIndex(-1)
    cb.blockSignals(False)


def area_texto(placeholder="", altura=84):
    t = QPlainTextEdit()
    t.setPlaceholderText(placeholder)
    t.setFixedHeight(altura)
    t.setTabChangesFocus(True)
    return t


def quantidade(minimo=1, maximo=999):
    s = QSpinBox()
    s.setRange(minimo, maximo)
    s.setValue(minimo)
    s.setFixedWidth(84)
    return s


def numero_valido(v):
    texto = str(v).strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        float(texto)
    except ValueError:
        return "Informe um número (ex.: 150 ou 150,50)."
    return None


def inteiro_valido(v):
    return None if str(v).strip().isdigit() else "Informe um número inteiro."


class Busca(QLineEdit):
    """Campo de busca com lupa; pesquisa enquanto o usuário digita e limpa com Esc."""
    pesquisar = Signal(str)

    def __init__(self, placeholder="Pesquisar..."):
        super().__init__()
        self.setPlaceholderText(placeholder)
        estilo(self, busca="true")
        self.lupa = QLabel(self)
        self.lupa.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._icone()
        Tema.ouvintes.append(self._icone)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(lambda: self.pesquisar.emit(self.text().strip()))
        self.textChanged.connect(lambda _: self.timer.start())
        self.setClearButtonEnabled(True)
        self.setAccessibleName(placeholder)

    def _icone(self):
        self.lupa.setPixmap(icone("search", Tema.cor("texto_2"), 16).pixmap(16, 16))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.lupa.move(12, (self.height() - 16) // 2)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.text():
            self.clear()
            return
        super().keyPressEvent(e)


class CampoData(QWidget):
    """Data dd/mm/aaaa digitada ou escolhida no calendário; pode ficar vazia."""
    mudou = Signal()

    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.texto = QLineEdit()
        self.texto.setPlaceholderText("dd/mm/aaaa")
        self.texto.setFixedWidth(116)
        self.texto.editingFinished.connect(self._digitou)
        self.texto.setAccessibleName("Data no formato dia, mês e ano")
        lay.addWidget(self.texto)
        self.botao = botao_icone("calendar", "Escolher no calendário", self.abrir)
        lay.addWidget(self.botao)

    def _digitou(self):
        t = self.texto.text().strip()
        estilo(self.texto, erro="true" if t and not self.data() else "false")
        self.mudou.emit()

    def abrir(self):
        menu = QMenu(self)
        cal = QCalendarWidget()
        cal.setGridVisible(False)
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        d = self.data()
        if d:
            cal.setSelectedDate(QDate(d.year, d.month, d.day))
        cal.clicked.connect(lambda q: (self.definir(date(q.year(), q.month(), q.day())), menu.close(), self.mudou.emit()))
        acao = QWidgetAction(menu)
        acao.setDefaultWidget(cal)
        menu.addAction(acao)
        menu.addAction("Limpar data", lambda: (self.definir(None), self.mudou.emit()))
        menu.exec(self.botao.mapToGlobal(QPoint(0, self.botao.height() + 4)))

    def data(self):
        try:
            d, m, a = (int(x) for x in self.texto.text().strip().split("/"))
            return date(a, m, d)
        except ValueError:
            return None

    def definir(self, d):
        if isinstance(d, str):
            self.texto.setText(d)
            return
        self.texto.setText(d.strftime("%d/%m/%Y") if d else "")
        estilo(self.texto, erro="false")

    def get(self):
        d = self.data()
        return d.isoformat() if d else ""


def periodos_rapidos():
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    fim_anterior = inicio_mes - timedelta(days=1)
    return [("Hoje", hoje, hoje), ("Últimos 7 dias", hoje - timedelta(days=6), hoje), ("Este mês", inicio_mes, hoje),
            ("Mês anterior", fim_anterior.replace(day=1), fim_anterior), ("Este ano", hoje.replace(month=1, day=1), hoje),
            ("Todo o período", None, None)]


class SeletorPeriodo(QWidget):
    mudou = Signal()

    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.de, self.ate = CampoData(), CampoData()
        self.atalhos = periodos_rapidos()
        self.rapido = selecao([n for n, _, _ in self.atalhos], "Período rápido")
        self.rapido.setFixedWidth(160)
        self.rapido.setAccessibleName("Período rápido")
        self.rapido.activated.connect(self._atalho)
        lay.addWidget(rotulo("De", "legenda"))
        lay.addWidget(self.de)
        lay.addWidget(rotulo("até", "legenda"))
        lay.addWidget(self.ate)
        lay.addWidget(self.rapido)
        self.de.mudou.connect(self.mudou.emit)
        self.ate.mudou.connect(self.mudou.emit)

    def _atalho(self, i):
        _, de, ate = self.atalhos[i]
        self.de.definir(de)
        self.ate.definir(ate)
        self.mudou.emit()

    def get(self):
        return self.de.get(), self.ate.get()


class Interruptor(QCheckBox):
    """Interruptor (switch) liga/desliga, desenhado com as cores do tema e animado."""

    def __init__(self, texto=""):
        super().__init__(texto)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 0.0
        self.toggled.connect(self._animar)
        self.setMinimumHeight(26)

    def _animar(self, ligado):
        self.anim = QPropertyAnimation(self, b"pos_bolinha", self)
        self.anim.setDuration(duracao("rapida"))
        self.anim.setEndValue(1.0 if ligado else 0.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def _get_pos(self):
        return self._pos

    def _set_pos(self, v):
        self._pos = v
        self.update()

    pos_bolinha = Property(float, _get_pos, _set_pos)

    def definir_sem_animar(self, ligado):
        self.blockSignals(True)
        self.setChecked(ligado)
        self._pos = 1.0 if ligado else 0.0
        self.blockSignals(False)
        self.update()

    def sizeHint(self):
        largura = 44 + (10 + self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0)
        return QSize(largura, 26)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        trilho = QRectF(2, 4, 40, 20)
        on, off = QColor(Tema.cor("destaque")), QColor("#5B6B7A")
        cor = QColor(int(off.red() + (on.red() - off.red()) * self._pos),
                     int(off.green() + (on.green() - off.green()) * self._pos),
                     int(off.blue() + (on.blue() - off.blue()) * self._pos))
        p.setPen(Qt.NoPen)
        p.setBrush(cor)
        p.drawRoundedRect(trilho, 10, 10)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(4 + 20 * self._pos, 6, 16, 16))
        if self.hasFocus():
            p.setPen(QPen(QColor(Tema.cor("destaque")), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(trilho.adjusted(-2, -2, 2, 2), 12, 12)
        if self.text():
            p.setPen(self.palette().windowText().color() if not self.property("cor_texto")
                     else QColor(self.property("cor_texto")))
            p.drawText(QRect(52, 0, self.width() - 52, self.height()), Qt.AlignVCenter, self.text())
        p.end()


# ------------------------------------------------------------------ cartões, selos e avatar
class Cartao(QFrame):
    def __init__(self, titulo=None, subtitulo=None, nivel=1, margem=ESPACO["l"]):
        super().__init__()
        estilo(self, papel="cartao")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(margem, margem - 4, margem, margem)
        self.lay.setSpacing(ESPACO["s"])
        self.cabeca = QHBoxLayout()
        self.cabeca.setSpacing(ESPACO["xs"])
        if titulo:
            textos = QVBoxLayout()
            textos.setSpacing(2)
            textos.addWidget(rotulo(titulo, "titulo_secao"))
            if subtitulo:
                textos.addWidget(rotulo(subtitulo, "legenda", True))
            self.cabeca.addLayout(textos, 1)
            self.lay.addLayout(self.cabeca)
        if nivel:
            sombra(self, nivel)


class Selo(QLabel):
    """Etiqueta arredondada (badge). Para as etapas da OS, use selo_status()."""

    def __init__(self, texto, cor_texto, cor_fundo):
        super().__init__(texto)
        self.pintar(cor_texto, cor_fundo)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def pintar(self, cor_texto, cor_fundo):
        self.setStyleSheet(f"QLabel {{ color: {cor_texto}; background: {cor_fundo}; border-radius: 11px;"
                           f" padding: 3px 11px; font-size: 12px; font-weight: 600; }}")


def selo_status(codigo):
    fg, bg = Tema.status(codigo)
    return Selo(StatusOS.NOMES.get(codigo, codigo), fg, bg)


class Avatar(QLabel):
    def __init__(self, nome, tamanho=34):
        super().__init__("".join(p[0] for p in nome.split()[:2]).upper())
        self.setFixedSize(tamanho, tamanho)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"QLabel {{ background: {Tema.cor('destaque')}; color: #1A1206; border-radius: {tamanho // 2}px;"
                           f" font-weight: 700; font-size: 13px; }}")
        self.setAccessibleName(f"Usuário {nome}")


# ------------------------------------------------------------------ estados vazio, carregando e erro
class EstadoVazio(QWidget):
    def __init__(self, ic="inbox", titulo="Nada por aqui", texto="", acao_texto=None, acao=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(ESPACO["xs"])
        self.circulo = QLabel()
        self.circulo.setFixedSize(64, 64)
        self.circulo.setAlignment(Qt.AlignCenter)
        self.nome_icone = ic
        lay.addWidget(self.circulo, 0, Qt.AlignHCenter)
        lay.addSpacing(4)
        self.titulo = rotulo(titulo, "vazio_titulo")
        self.titulo.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.titulo)
        self.texto = rotulo(texto, "subtitulo", True)
        self.texto.setAlignment(Qt.AlignCenter)
        self.texto.setMaximumWidth(400)
        lay.addWidget(self.texto, 0, Qt.AlignHCenter)
        self.botao = None
        if acao_texto and acao:
            self.botao = Botao(acao_texto, "primario", None, None, acao)
            lay.addSpacing(6)
            lay.addWidget(self.botao, 0, Qt.AlignHCenter)
        self._pintar()
        Tema.ouvintes.append(self._pintar)

    def _pintar(self):
        self.circulo.setStyleSheet(f"QLabel {{ background: {Tema.cor('realce')}; border-radius: 32px; }}")
        self.circulo.setPixmap(icone(self.nome_icone, Tema.cor("texto_2"), 28).pixmap(28, 28))

    def definir(self, ic=None, titulo=None, texto=None):
        if ic:
            self.nome_icone = ic
            self._pintar()
        if titulo is not None:
            self.titulo.setText(titulo)
        if texto is not None:
            self.texto.setText(texto)


class Esqueleto(QWidget):
    """Esqueleto de carregamento: barras com um brilho que percorre (parado com movimento reduzido)."""

    def __init__(self, linhas=7):
        super().__init__()
        self.linhas, self.fase = linhas, 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._passo)

    def showEvent(self, e):
        if duracao() > 0:
            self.timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def _passo(self):
        self.fase = (self.fase + 0.025) % 1.3
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        base, brilho = QColor(Tema.cor("realce")), QColor(Tema.cor("borda"))
        w = max(self.width(), 1)
        for i in range(self.linhas):
            y = 20 + i * 40
            for x, larg in ((0.02, 0.07), (0.12, 0.22), (0.38, 0.30), (0.72, 0.18)):
                perto = abs(x - (self.fase - 0.15)) < 0.12
                p.setBrush(brilho if perto else base)
                p.drawRoundedRect(QRectF(x * w, y, larg * w, 14), 7, 7)
        p.end()


# ------------------------------------------------------------------ tabela
# colunas de texto livre: podem encolher quando a tabela não cabe (o texto inteiro aparece na dica)
ENCOLHEM = {"nome", "descricao", "cliente_nome", "mecanico_nome", "modelo", "marca", "email", "peca_descricao",
            "fornecedor_nome", "destinacao_residuo", "problema", "diagnostico", "usuario_nome", "situacao"}


class _Modelo(QAbstractTableModel):
    def __init__(self, colunas):
        super().__init__()
        self.colunas, self.todos, self.visiveis = colunas, [], []
        self.pagina, self.por_pagina, self.cor_linha = 0, 50, None

    def definir(self, objetos):
        self.beginResetModel()
        self.todos = list(objetos)
        self.pagina = min(self.pagina, max((len(self.todos) - 1) // self.por_pagina, 0))
        self._fatiar()
        self.endResetModel()

    def _fatiar(self):
        i = self.pagina * self.por_pagina
        self.visiveis = self.todos[i:i + self.por_pagina]

    def mudar_pagina(self, delta):
        ultima = max((len(self.todos) - 1) // self.por_pagina, 0)
        self.beginResetModel()
        self.pagina = max(0, min(ultima, self.pagina + delta))
        self._fatiar()
        self.endResetModel()

    def rowCount(self, _=QModelIndex()):
        return len(self.visiveis)

    def columnCount(self, _=QModelIndex()):
        return len(self.colunas)

    @staticmethod
    def _bruto(obj, col):
        return getattr(obj, col["chave"], "")

    def data(self, idx, papel=Qt.DisplayRole):
        if not idx.isValid():
            return None
        obj, col = self.visiveis[idx.row()], self.colunas[idx.column()]
        v = self._bruto(obj, col)
        if papel == Qt.DisplayRole:
            if col.get("formato"):
                v = col["formato"](v)
            return "" if v is None else str(v)
        if papel == Qt.UserRole:
            return v
        if papel == Qt.TextAlignmentRole:
            return int((Qt.AlignRight if col.get("numero") else Qt.AlignLeft) | Qt.AlignVCenter)
        if papel == Qt.FontRole and col.get("numero"):
            return fonte("corpo", "normal", tabular=True)
        if papel == Qt.ForegroundRole and self.cor_linha:
            cor = self.cor_linha(obj)
            return QColor(cor) if cor else None
        if papel == Qt.ToolTipRole and (col.get("dica") or col["chave"] in ENCOLHEM):
            return "" if v is None else str(v)
        return None

    def headerData(self, secao, orientacao, papel=Qt.DisplayRole):
        if orientacao != Qt.Horizontal:
            return None
        if papel == Qt.DisplayRole:
            return self.colunas[secao]["titulo"]
        if papel == Qt.TextAlignmentRole:
            return int((Qt.AlignRight if self.colunas[secao].get("numero") else Qt.AlignLeft) | Qt.AlignVCenter)
        return None

    def sort(self, coluna, ordem=Qt.AscendingOrder):
        col = self.colunas[coluna]

        def chave(o):
            v = self._bruto(o, col)
            return (v is None or v == "", v if isinstance(v, (int, float)) else str(v).lower())
        self.beginResetModel()
        try:
            self.todos.sort(key=chave, reverse=ordem == Qt.DescendingOrder)
        except TypeError:
            self.todos.sort(key=lambda o: str(self._bruto(o, col)), reverse=ordem == Qt.DescendingOrder)
        self.pagina = 0
        self._fatiar()
        self.endResetModel()


class _DelegadoSelo(QStyledItemDelegate):
    """Desenha a coluna de status como selo colorido."""

    def sizeHint(self, opt, idx):
        s = super().sizeHint(opt, idx)
        return QSize(s.width() + 30, s.height())

    def paint(self, p, opt, idx):
        if opt.state & QStyle.State_Selected:
            p.fillRect(opt.rect, QColor(Tema.cor("primaria_suave")))
        elif opt.state & QStyle.State_MouseOver:
            p.fillRect(opt.rect, QColor(Tema.cor("realce")))
        elif idx.row() % 2:
            p.fillRect(opt.rect, QColor(Tema.cor("superficie_2")))
        codigo, texto = idx.data(Qt.UserRole), idx.data(Qt.DisplayRole)
        fg, bg = Tema.status(codigo)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(fonte("legenda", "seminegrito"))
        largura = p.fontMetrics().horizontalAdvance(texto) + 22
        r = QRectF(opt.rect.x() + 10, opt.rect.center().y() - 11, min(largura, opt.rect.width() - 16), 22)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(bg))
        p.drawRoundedRect(r, 11, 11)
        p.setPen(QColor(fg))
        p.drawText(r, Qt.AlignCenter, texto)
        p.setPen(QColor(Tema.cor("borda")))
        p.drawLine(opt.rect.bottomLeft(), opt.rect.bottomRight())
        p.restore()


class Tabela(QWidget):
    """Tabela com cabeçalho fixo, ordenação por coluna, linhas zebradas, ações por linha (duplo clique, Enter ou
    menu do botão direito), paginação e estados vazio, carregando e erro.

    colunas: dicts {chave, titulo, largura, formato, numero, status, dica} ou tuplas (chave, titulo, largura).
    acoes: [(texto, ícone, função(id))] para o menu do botão direito."""
    ativado = Signal(int)
    selecionou = Signal(object)

    def __init__(self, colunas, vazio=("inbox", "Nada por aqui", ""), acoes=None, por_pagina=50, altura_linha=42):
        super().__init__()
        cols = [c if isinstance(c, dict) else {"chave": c[0], "titulo": c[1], "largura": c[2]} for c in colunas]
        self.modelo = _Modelo(cols)
        self.modelo.por_pagina = por_pagina
        self.acoes = acoes or []
        self.pilha = QStackedLayout(self)
        caixa = QWidget()
        v = QVBoxLayout(caixa)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.view = QTableView()
        self.view.setModel(self.modelo)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setShowGrid(False)
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.view.setWordWrap(False)
        self.view.setMouseTracking(True)
        self.view.setFocusPolicy(Qt.StrongFocus)
        self.view.verticalHeader().hide()
        self.view.verticalHeader().setDefaultSectionSize(altura_linha)
        cab = self.view.horizontalHeader()
        cab.setHighlightSections(False)
        cab.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cab.setStretchLastSection(True)
        for i, c in enumerate(cols):
            if c.get("largura"):
                self.view.setColumnWidth(i, c["largura"])
            if c.get("status"):
                self.view.setItemDelegateForColumn(i, _DelegadoSelo(self.view))
        self.view.doubleClicked.connect(self._ativar)
        self.view.activated.connect(self._ativar)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._menu)
        self.view.selectionModel().selectionChanged.connect(lambda *_: self.selecionou.emit(self.id_selecionado()))
        v.addWidget(self.view, 1)
        self.rodape = QWidget()
        r = QHBoxLayout(self.rodape)
        r.setContentsMargins(12, 6, 6, 6)
        self.info = rotulo("", "legenda")
        r.addWidget(self.info)
        r.addStretch(1)
        self.ant = botao_icone("chevron-left", "Página anterior", lambda: self._pagina(-1))
        self.prox = botao_icone("chevron-right", "Próxima página", lambda: self._pagina(1))
        r.addWidget(self.ant)
        r.addWidget(self.prox)
        v.addWidget(self.rodape)
        self.pilha.addWidget(caixa)
        self.vazio = EstadoVazio(*vazio)
        self.pilha.addWidget(self.vazio)
        self.esqueleto = Esqueleto()
        self.pilha.addWidget(self.esqueleto)
        self.erro = EstadoVazio("triangle-alert", "Não foi possível carregar", "", "Tentar de novo", self._repetir)
        self.pilha.addWidget(self.erro)
        self._fonte = None

    def preencher(self, objetos):
        objetos = list(objetos or [])
        self.modelo.definir(objetos)
        self.pilha.setCurrentIndex(0 if objetos else 1)
        self._atualizar_rodape()
        self._ajustar_colunas()

    def _ajustar_colunas(self):
        """Largura de cada coluna pelo conteúdo, sem cortar datas, placas e valores; se a tabela não couber,
        as colunas de texto mais largas encolhem (o texto completo aparece na dica)."""
        cols = self.modelo.colunas
        if not cols:
            return
        self.view.resizeColumnsToContents()
        larg = [min(self.view.columnWidth(i) + 20, 360) for i in range(len(cols))]
        for i, c in enumerate(cols):
            if c.get("status"):
                larg[i] = max(larg[i], 150)
            elif c["chave"] == "id":             # códigos curtos: não precisam da largura do cabeçalho com a seta
                larg[i] = min(larg[i], max(self.view.sizeHintForColumn(i) + 28, 64))
        disponivel = self.view.viewport().width()
        excesso = sum(larg) - disponivel if disponivel > 50 else 0
        textos = sorted([i for i, c in enumerate(cols) if c.get("dica") or c["chave"] in ENCOLHEM],
                        key=lambda i: -larg[i])
        while excesso > 0 and textos:
            i = textos[0]
            corte = min(excesso, max(larg[i] - 110, 0))
            if corte <= 0:
                textos.pop(0)
                continue
            larg[i] -= corte
            excesso -= corte
            textos.sort(key=lambda k: -larg[k])
        for i in range(len(cols) - 1):           # a última coluna estica até a borda
            self.view.setColumnWidth(i, larg[i])
        ultima = cols[-1]
        resto = disponivel - sum(larg[:-1])
        if disponivel > 50 and resto > 0 and (ultima.get("dica") or ultima["chave"] in ENCOLHEM):
            # se for texto livre, também não fica mais larga que o espaço que sobrou (o texto todo vai na dica)
            self.view.setColumnWidth(len(cols) - 1, min(larg[-1], resto))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ajustar_colunas()

    def carregar(self, fonte_dados):
        """Mostra o esqueleto, busca os dados e exibe a lista (ou o estado de erro, com a opção de tentar de novo)."""
        self._fonte = fonte_dados
        self.pilha.setCurrentIndex(2)
        QTimer.singleShot(0, self._buscar)

    def _buscar(self):
        try:
            self.preencher(self._fonte())
        except RegraNegocioError as e:
            self.erro.definir(texto=str(e))
            self.pilha.setCurrentIndex(3)

    def _repetir(self):
        if self._fonte:
            self.carregar(self._fonte)

    def _pagina(self, delta):
        self.modelo.mudar_pagina(delta)
        self._atualizar_rodape()

    def _atualizar_rodape(self):
        total, pp, pg = len(self.modelo.todos), self.modelo.por_pagina, self.modelo.pagina
        inicio, fim = (pg * pp + 1 if total else 0), min((pg + 1) * pp, total)
        self.info.setText(f"{total} registro(s)" if total <= pp else f"Mostrando {inicio}–{fim} de {total}")
        varias = total > pp
        self.ant.setVisible(varias)
        self.prox.setVisible(varias)
        self.ant.setEnabled(pg > 0)
        self.prox.setEnabled(fim < total)

    def objeto_selecionado(self):
        idx = self.view.selectionModel().selectedRows()
        return self.modelo.visiveis[idx[0].row()] if idx else None

    def id_selecionado(self):
        o = self.objeto_selecionado()
        return getattr(o, "id", None) if o else None

    def selecionado(self, aviso="Selecione um item na lista."):
        i = self.id_selecionado()
        if i is None and aviso:
            notificar(self, aviso, "info")
        return i

    def limpar_selecao(self):
        self.view.clearSelection()

    def _ativar(self, idx):
        o = self.modelo.visiveis[idx.row()]
        if getattr(o, "id", None) is not None:
            self.ativado.emit(o.id)

    def _menu(self, pos):
        idx = self.view.indexAt(pos)
        if not idx.isValid() or not self.acoes:
            return
        self.view.selectRow(idx.row())
        menu = QMenu(self)
        for texto, ic, func in self.acoes:
            a = menu.addAction(icone(ic, Tema.cor("texto_2"), 16), texto)
            a.triggered.connect(lambda _=False, f=func: f(self.id_selecionado()))
        menu.exec(self.view.viewport().mapToGlobal(pos))

    def cor_por_linha(self, func):
        self.modelo.cor_linha = func


# ------------------------------------------------------------------ indicadores e gráfico
class Kpi(QFrame):
    """Indicador do painel: rótulo, número grande (tabular) e faixa lateral na cor da etapa."""

    def __init__(self, rotulo_texto, valor="0", cor=None, ic=None, ajuda=""):
        super().__init__()
        estilo(self, papel="cartao")
        self.cor, self.nome_icone = cor, ic
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 16, 14)
        lay.setSpacing(2)
        topo = QHBoxLayout()
        self.lb = rotulo(rotulo_texto.upper(), "kpi_rotulo")
        topo.addWidget(self.lb, 1)
        self.ico = QLabel()
        topo.addWidget(self.ico)
        lay.addLayout(topo)
        self.valor = rotulo(str(valor), "kpi_valor")
        self.valor.setFont(fonte("numero", "seminegrito", tabular=True))
        lay.addWidget(self.valor)
        self.ajuda = rotulo(ajuda, "legenda", True)
        self.ajuda.setVisible(bool(ajuda))
        lay.addWidget(self.ajuda)
        self.barra = QFrame(self)
        self._pintar()
        Tema.ouvintes.append(self._pintar)
        sombra(self, 1)
        self.setMinimumWidth(120)

    def _pintar(self):
        cor = self.cor() if callable(self.cor) else (self.cor or Tema.cor("primaria"))
        self.barra.setStyleSheet(f"background: {cor}; border: none; border-top-left-radius: {RAIO['m']}px;"
                                 f" border-bottom-left-radius: {RAIO['m']}px;")
        if self.nome_icone:
            self.ico.setPixmap(icone(self.nome_icone, cor, 18).pixmap(18, 18))

    def resizeEvent(self, e):
        self.barra.setGeometry(0, 0, 4, self.height())
        super().resizeEvent(e)

    def definir(self, valor, ajuda=None):
        self.valor.setText(str(valor))
        if ajuda is not None:
            self.ajuda.setText(ajuda)
            self.ajuda.setVisible(bool(ajuda))


class GraficoBarras(QWidget):
    """Barras horizontais nas cores do tema; dados: [(rótulo, valor, cor ou None)]. Cresce com animação."""

    def __init__(self, formato=str, vazio="Sem dados no período."):
        super().__init__()
        self.dados, self.formato, self.texto_vazio, self._prog = [], formato, vazio, 1.0
        self.setMinimumHeight(70)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._animar)
        Tema.ouvintes.append(self.update)

    def definir(self, dados):
        self.dados = list(dados)
        self.setMinimumHeight(max(70, 34 * len(self.dados) + 8))
        self._prog = 0.0 if duracao() else 1.0
        if duracao():
            self.timer.start()
        self.update()

    def _animar(self):
        self._prog = min(1.0, self._prog + 16 / duracao("lenta"))
        if self._prog >= 1.0:
            self.timer.stop()
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(fonte("corpo"))
        if not self.dados:
            p.setPen(QColor(Tema.cor("texto_2")))
            p.drawText(self.rect(), Qt.AlignCenter, self.texto_vazio)
            return
        maximo = max(v for _, v, _ in self.dados) or 1
        larg_rot = min(max(p.fontMetrics().horizontalAdvance(r) for r, _, _ in self.dados) + 16, self.width() * 0.42)
        larg_val = 96
        area = max(self.width() - larg_rot - larg_val, 20)
        for i, (rot, val, cor) in enumerate(self.dados):
            y = 4 + i * 34
            p.setFont(fonte("corpo"))
            p.setPen(QColor(Tema.cor("texto")))
            p.drawText(QRectF(0, y, larg_rot - 10, 26), Qt.AlignVCenter | Qt.AlignLeft,
                       p.fontMetrics().elidedText(rot, Qt.ElideRight, int(larg_rot - 12)))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(Tema.cor("realce")))
            p.drawRoundedRect(QRectF(larg_rot, y + 6, area, 14), 7, 7)
            p.setBrush(QColor(cor or Tema.cor("primaria")))
            p.drawRoundedRect(QRectF(larg_rot, y + 6, max(area * val / maximo * self._prog, 6), 14), 7, 7)
            p.setFont(fonte("corpo", "medio", tabular=True))
            p.setPen(QColor(Tema.cor("texto_2")))
            p.drawText(QRectF(larg_rot + area + 8, y, larg_val - 8, 26), Qt.AlignVCenter | Qt.AlignRight,
                       self.formato(val))
        p.end()


def barra_progresso(valor=0, maximo=100):
    b = QProgressBar()
    b.setRange(0, maximo)
    b.setValue(valor)
    b.setTextVisible(False)
    return b


# ------------------------------------------------------------------ diálogos
class Dialogo(QDialog):
    """Janela modal com título, subtítulo, corpo e botões (Cancelar e a ação principal); validar() decide o OK."""

    def __init__(self, pai, titulo, subtitulo="", texto_ok="Salvar", largura=520, perigo=False):
        super().__init__(pai)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(largura)
        self.resultado = None
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(ESPACO["l"], ESPACO["l"], ESPACO["l"], ESPACO["l"])
        raiz.setSpacing(ESPACO["m"])
        cab = QVBoxLayout()
        cab.setSpacing(4)
        cab.addWidget(rotulo(titulo, "titulo_secao"))
        if subtitulo:
            cab.addWidget(rotulo(subtitulo, "subtitulo", True))
        raiz.addLayout(cab)
        self.corpo = QVBoxLayout()
        self.corpo.setSpacing(ESPACO["s"])
        raiz.addLayout(self.corpo, 1)
        botoes = QHBoxLayout()
        botoes.addStretch(1)
        self.cancelar = Botao("Cancelar", "fantasma", None, None, self.reject)
        self.ok = Botao(texto_ok, "perigo_cheio" if perigo else "primario", None, None, self._ok)
        self.ok.setDefault(True)
        botoes.addWidget(self.cancelar)
        botoes.addWidget(self.ok)
        raiz.addLayout(botoes)

    def showEvent(self, e):
        super().showEvent(e)
        if duracao():
            self.setWindowOpacity(0.0)
            self.anim = QPropertyAnimation(self, b"windowOpacity", self)
            self.anim.setDuration(duracao("rapida"))
            self.anim.setStartValue(0.0)
            self.anim.setEndValue(1.0)
            self.anim.setEasingCurve(QEasingCurve.OutCubic)
            self.anim.start()
        for w in self.findChildren(QWidget):          # foco automático no primeiro campo
            if isinstance(w, (QLineEdit, QComboBox, QPlainTextEdit, QSpinBox)) and w.isEnabled() and w.isVisibleTo(self):
                w.setFocus()
                break

    def _ok(self):
        r = self.validar()
        if r is not None and r is not False:
            self.resultado = r
            self.accept()

    def validar(self):
        return True

    def mostrar(self):
        return self.resultado if self.exec() == QDialog.Accepted else None


def confirmar(pai, titulo, texto, botao="Confirmar", perigo=False):
    return Dialogo(pai, titulo, texto, botao, largura=440, perigo=perigo).mostrar() is not None


def informar(pai, titulo, texto, botao="Entendi"):
    d = Dialogo(pai, titulo, "", botao, largura=480)
    lb = rotulo(texto, None, True)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    d.corpo.addWidget(lb)
    d.cancelar.hide()
    d.mostrar()


class DialogoCampos(Dialogo):
    """campos: (chave, rótulo), (chave, rótulo, opções) ou dicts {chave, rotulo, opcoes, unidade, obrigatorio,
    validar, ajuda, placeholder}."""

    def __init__(self, pai, titulo, campos, valores=None, subtitulo="", texto_ok="Salvar"):
        super().__init__(pai, titulo, subtitulo, texto_ok)
        self.campos = {}
        for c in campos:
            if not isinstance(c, dict):
                c = {"chave": c[0], "rotulo": c[1], "opcoes": c[2] if len(c) > 2 else None}
            controle = selecao(c["opcoes"]) if c.get("opcoes") is not None else entrada(c.get("placeholder", ""))
            campo = Campo(c["rotulo"], controle, c.get("ajuda", ""), c.get("obrigatorio", True), c.get("validar"),
                          c.get("unidade"))
            self.corpo.addWidget(campo)
            self.campos[c["chave"]] = campo
        for k, v in (valores or {}).items():
            if k in self.campos:
                self.campos[k].definir(v)

    def validar(self):
        ok = all([c.validar() for c in self.campos.values()])
        return {k: c.valor() for k, c in self.campos.items()} if ok else None


def pedir(pai, titulo, campos, valores=None, subtitulo="", texto_ok="Salvar"):
    return DialogoCampos(pai, titulo, campos, valores, subtitulo, texto_ok).mostrar()


# ------------------------------------------------------------------ histórico e PDF
COLUNAS_HISTORICO = [
    {"chave": "id", "titulo": "OS", "largura": 64, "numero": True},
    {"chave": "data_abertura", "titulo": "Data", "largura": 150, "formato": lambda d: data_br(d, True)},
    {"chave": "placa", "titulo": "Placa", "largura": 90},
    {"chave": "status", "titulo": "Status", "largura": 180, "status": True, "formato": lambda s: StatusOS.NOMES.get(s, s)},
    {"chave": "problema", "titulo": "Problema", "largura": 200, "dica": True},
    {"chave": "diagnostico", "titulo": "Diagnóstico", "largura": 190, "dica": True},
    {"chave": "total", "titulo": "Valor", "largura": 110, "numero": True, "formato": moeda},
]


def janela_historico(pai, titulo, lista, abrir_os):
    """RF33: OS anteriores de um cliente ou veículo; duplo clique (ou Enter) abre a OS."""
    d = Dialogo(pai, titulo, "Dê um duplo clique numa linha (ou tecle Enter) para abrir a OS.", "Fechar", largura=1000)
    d.cancelar.hide()
    t = Tabela(COLUNAS_HISTORICO, ("history", "Sem histórico", "Este cadastro ainda não tem ordens de serviço."))
    t.setMinimumHeight(380)
    t.preencher(lista)
    t.ativado.connect(lambda i: (d.accept(), abrir_os(i)))
    d.corpo.addWidget(t)
    d.mostrar()


def salvar_e_abrir_pdf(pai, nome_inicial, gravar):
    """Pergunta onde salvar, grava o PDF e oferece abrir o arquivo."""
    caminho, _ = QFileDialog.getSaveFileName(pai, "Salvar PDF", nome_inicial, "PDF (*.pdf)")
    if caminho and executar(gravar, caminho, pai=pai):
        if confirmar(pai, "PDF salvo", f"O arquivo foi salvo em:\n{caminho}\n\nDeseja abrir agora?", "Abrir PDF"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(caminho)))

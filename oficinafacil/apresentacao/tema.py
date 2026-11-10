"""Design system do OficinaFácil: tokens (cores dos temas claro e escuro, tipografia, espaçamento, raios, sombras e
movimento), folha de estilos QSS gerada a partir deles, fonte Inter embarcada e ícones Lucide recoloridos.

Documentação e exemplos: docs/DESIGN.md.
"""
import math
import os
import sys

from PySide6.QtCore import QByteArray, QPointF, QRectF, QSettings, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer

RECURSOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recursos")

# ------------------------------------------------------------------ cores
# As combinações de texto e fundo usadas atendem ao contraste mínimo WCAG AA (4,5:1 para texto normal).
CLARO = {
    "fundo": "#F4F6F9", "superficie": "#FFFFFF", "superficie_2": "#F8FAFC", "realce": "#EEF2F7",
    "borda": "#E2E8F0", "borda_forte": "#CBD5E1",
    "texto": "#0F172A", "texto_2": "#475569", "texto_desab": "#94A3B8",
    "primaria": "#1E3A5F", "primaria_hover": "#2A4D7A", "primaria_suave": "#E6EEF7", "sobre_primaria": "#FFFFFF",
    "destaque": "#F28C28", "destaque_suave": "#FDEBD8",
    "sucesso": "#15803D", "sucesso_suave": "#DCFCE7",
    "alerta": "#B45309", "alerta_suave": "#FEF3C7",
    "erro": "#B91C1C", "erro_suave": "#FEE2E2",
    "info": "#1D4ED8", "info_suave": "#DBEAFE",
    "lateral": "#13283F", "lateral_texto": "#C8D3E0", "lateral_hover": "#1D3753", "lateral_ativo": "#24456A",
    "sombra": "#0F172A",
}
ESCURO = {
    "fundo": "#0E151D", "superficie": "#16202B", "superficie_2": "#1B2733", "realce": "#223040",
    "borda": "#263544", "borda_forte": "#344759",
    "texto": "#E6EDF3", "texto_2": "#9FB0C0", "texto_desab": "#5B6B7A",
    "primaria": "#6AA6DE", "primaria_hover": "#86B9E8", "primaria_suave": "#1B3047", "sobre_primaria": "#0A1520",
    "destaque": "#F5A04A", "destaque_suave": "#3A2712",
    "sucesso": "#4ADE80", "sucesso_suave": "#12351F",
    "alerta": "#FBBF24", "alerta_suave": "#3A2C0B",
    "erro": "#F87171", "erro_suave": "#3B1515",
    "info": "#7DB4FA", "info_suave": "#132A47",
    "lateral": "#0A1118", "lateral_texto": "#9FB0C0", "lateral_hover": "#152230", "lateral_ativo": "#1D3047",
    "sombra": "#000000",
}
# etapa da OS -> (cor do texto, cor do fundo) do selo, em cada tema
STATUS = {
    "claro": {"ABERTA": ("#1D4ED8", "#DBEAFE"), "EM_DIAGNOSTICO": ("#6D28D9", "#EDE9FE"),
              "AGUARDANDO_GERENTE": ("#B45309", "#FEF3C7"), "AGUARDANDO_CLIENTE": ("#C2410C", "#FFEDD5"),
              "AGUARDANDO_PECAS": ("#B42318", "#FEE4E2"), "EM_EXECUCAO": ("#0F766E", "#CCFBF1"),
              "CONCLUIDA": ("#15803D", "#DCFCE7"), "ENCERRADA": ("#475569", "#E2E8F0"),
              "CANCELADA": ("#526071", "#F1F5F9"),
              "PENDENTE": ("#B45309", "#FEF3C7"), "COMPRADA": ("#1D4ED8", "#DBEAFE"), "RECEBIDA": ("#15803D", "#DCFCE7")},
    "escuro": {"ABERTA": ("#93C5FD", "#132A47"), "EM_DIAGNOSTICO": ("#C4B5FD", "#2A1F47"),
               "AGUARDANDO_GERENTE": ("#FCD34D", "#3A2C0B"), "AGUARDANDO_CLIENTE": ("#FDBA74", "#3B2210"),
               "AGUARDANDO_PECAS": ("#FCA5A5", "#3B1515"), "EM_EXECUCAO": ("#5EEAD4", "#0E3330"),
               "CONCLUIDA": ("#86EFAC", "#12351F"), "ENCERRADA": ("#CBD5E1", "#263544"),
               "CANCELADA": ("#94A3B8", "#1E2A36"),
               "PENDENTE": ("#FCD34D", "#3A2C0B"), "COMPRADA": ("#93C5FD", "#132A47"), "RECEBIDA": ("#86EFAC", "#12351F")},
}

# ------------------------------------------------------------------ tipografia, espaçamento, forma e movimento
FONTE = "Inter"
TAMANHOS = {"legenda": 12, "corpo": 14, "destaque": 16, "titulo_secao": 20, "titulo": 24, "numero": 32}
PESOS = {"normal": 400, "medio": 500, "seminegrito": 600, "negrito": 700}
ALTURA_LINHA = 1.45
ESPACO = {"xxs": 4, "xs": 8, "s": 12, "m": 16, "l": 24, "xl": 32, "xxl": 48}
RAIO = {"p": 6, "m": 10, "g": 16}
SOMBRAS = {1: (10, 2, 0.06), 2: (20, 4, 0.10), 3: (36, 10, 0.18)}  # nível: (desfoque, deslocamento y, opacidade)
DURACAO = {"rapida": 150, "media": 200, "lenta": 250}               # ms, sempre com a curva OutCubic


class Tema:
    """Tema atual (claro ou escuro). A escolha fica salva entre uma execução e outra."""
    nome = "claro"
    cores = CLARO
    ouvintes = []

    @classmethod
    def carregar(cls):
        cls.definir(QSettings("OficinaFacil", "OficinaFacil").value("tema", "claro"), salvar=False)

    @classmethod
    def definir(cls, nome, salvar=True):
        cls.nome = "escuro" if nome == "escuro" else "claro"
        cls.cores = ESCURO if cls.nome == "escuro" else CLARO
        if salvar:
            QSettings("OficinaFacil", "OficinaFacil").setValue("tema", cls.nome)
        for f in list(cls.ouvintes):
            try:
                f()
            except RuntimeError:          # widget já destruído
                cls.ouvintes.remove(f)

    @classmethod
    def cor(cls, chave):
        return cls.cores[chave]

    @classmethod
    def status(cls, codigo):
        return STATUS[cls.nome].get(codigo, (cls.cores["texto_2"], cls.cores["realce"]))


def movimento_reduzido():
    """Respeita a preferência do sistema por menos animação (no Windows, 'Mostrar animações' desligado)."""
    if os.environ.get("OFICINAFACIL_SEM_ANIMACAO"):
        return True
    if sys.platform == "win32":
        try:
            import ctypes
            valor = ctypes.c_bool(True)
            ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(valor), 0)  # SPI_GETCLIENTAREAANIMATION
            return not valor.value
        except Exception:
            return False
    return False


def duracao(chave="media"):
    return 0 if movimento_reduzido() else DURACAO[chave]


# ------------------------------------------------------------------ fontes
def carregar_fontes():
    pasta = os.path.join(RECURSOS, "fontes")
    for nome in sorted(os.listdir(pasta)):
        if nome.endswith(".ttf"):
            QFontDatabase.addApplicationFont(os.path.join(pasta, nome))


def fonte(tamanho="corpo", peso="normal", tabular=False):
    f = QFont(FONTE)
    f.setPixelSize(TAMANHOS[tamanho] if isinstance(tamanho, str) else tamanho)
    f.setWeight(QFont.Weight(PESOS[peso]))
    if tabular:
        f.setFeature(QFont.Tag("tnum"), 1)     # números tabulares: valores alinhados nas colunas
    return f


# ------------------------------------------------------------------ ícones
_svg = {}


def icone(nome, cor=None, tamanho=18):
    """Ícone Lucide recolorido (o SVG usa currentColor), nítido em telas de alta resolução."""
    cor = cor or Tema.cor("texto_2")
    if nome not in _svg:
        with open(os.path.join(RECURSOS, "icones", nome + ".svg"), encoding="utf-8") as f:
            _svg[nome] = f.read()
    renderer = QSvgRenderer(QByteArray(_svg[nome].replace("currentColor", cor).encode("utf-8")))
    ic = QIcon()
    for escala in (1, 2, 3):
        pm = QPixmap(tamanho * escala, tamanho * escala)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        pm.setDevicePixelRatio(escala)
        ic.addPixmap(pm)
    return ic


def logotipo(tamanho=64):
    """Marca do sistema: engrenagem branca com miolo laranja num quadrado arredondado azul, desenhada em vetor."""
    pm = QPixmap(tamanho * 3, tamanho * 3)
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(3)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    t = float(tamanho)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(CLARO["primaria"]))
    p.drawRoundedRect(QRectF(0, 0, t, t), t * 0.24, t * 0.24)
    c = QPointF(t / 2, t / 2)
    caminho, dentes = QPainterPath(), 8
    for i in range(dentes * 4):
        ang = math.pi * 2 * (i - 0.5) / (dentes * 4)
        r = t * (0.34 if (i % 4) in (1, 2) else 0.26)
        ponto = QPointF(c.x() + r * math.cos(ang), c.y() + r * math.sin(ang))
        if i:
            caminho.lineTo(ponto)
        else:
            caminho.moveTo(ponto)
    caminho.closeSubpath()
    p.setBrush(QColor("#FFFFFF"))
    p.drawPath(caminho)
    p.setBrush(QColor(CLARO["primaria"]))
    p.drawEllipse(c, t * 0.13, t * 0.13)
    p.setBrush(QColor(CLARO["destaque"]))
    p.drawEllipse(c, t * 0.085, t * 0.085)
    p.end()
    return pm


def svg_colorido(nome, cor):
    """Grava uma cópia do ícone na cor pedida (o QSS só aceita arquivos de imagem) e devolve o caminho."""
    import tempfile
    pasta = os.path.join(tempfile.gettempdir(), "oficinafacil_icones")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{nome}_{cor.lstrip('#')}.svg")
    if not os.path.exists(caminho):
        with open(os.path.join(RECURSOS, "icones", nome + ".svg"), encoding="utf-8") as f:
            svg = f.read().replace("currentColor", cor)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(svg)
    return caminho.replace(os.sep, "/")


# ------------------------------------------------------------------ folha de estilos
def qss():
    c, r, t = Tema.cores, RAIO, TAMANHOS
    baixo, cima = svg_colorido("chevron-down", c["texto_2"]), svg_colorido("chevron-up", c["texto_2"])
    return f"""
* {{ font-family: "{FONTE}"; font-size: {t['corpo']}px; color: {c['texto']}; outline: none; }}
QMainWindow, QDialog, QWidget#Janela, QWidget#Pagina, QStackedWidget, QScrollArea > QWidget > QWidget {{ background: {c['fundo']}; }}
QToolTip {{ background: {c['texto']}; color: {c['superficie']}; border: none; padding: 6px 8px; }}

QLabel {{ background: transparent; }}
QLabel[papel="titulo"] {{ font-size: {t['titulo']}px; font-weight: 600; }}
QLabel[papel="titulo_secao"] {{ font-size: {t['destaque']}px; font-weight: 600; }}
QLabel[papel="subtitulo"] {{ color: {c['texto_2']}; }}
QLabel[papel="ajuda"], QLabel[papel="legenda"], QLabel[papel="breadcrumb"] {{ color: {c['texto_2']}; font-size: {t['legenda']}px; }}
QLabel[papel="erro"] {{ color: {c['erro']}; font-size: {t['legenda']}px; }}
QLabel[papel="rotulo"] {{ font-weight: 500; }}
QLabel[papel="valor"] {{ font-weight: 500; }}
QLabel[papel="kpi_valor"] {{ font-size: {t['numero']}px; font-weight: 600; }}
QLabel[papel="kpi_rotulo"] {{ color: {c['texto_2']}; font-size: {t['legenda']}px; font-weight: 500; }}
QLabel[papel="vazio_titulo"] {{ font-size: {t['destaque']}px; font-weight: 600; }}
QLabel[papel="alerta"] {{ color: {c['alerta']}; background: {c['alerta_suave']}; border-radius: {r['p']}px;
    padding: 8px 12px; font-weight: 500; }}

QFrame[papel="cartao"] {{ background: {c['superficie']}; border: 1px solid {c['borda']}; border-radius: {r['m']}px; }}
QFrame[papel="divisor"] {{ background: {c['borda']}; max-height: 1px; min-height: 1px; border: none; }}

QPushButton {{ border-radius: {r['p']}px; padding: 8px 14px; font-weight: 500;
    border: 1px solid {c['borda_forte']}; background: {c['superficie']}; color: {c['texto']}; }}
QPushButton:hover {{ background: {c['realce']}; }}
QPushButton:pressed {{ background: {c['borda']}; }}
QPushButton:focus {{ border: 2px solid {c['primaria']}; padding: 7px 13px; }}
QPushButton:disabled {{ color: {c['texto_desab']}; background: {c['superficie_2']}; border-color: {c['borda']}; }}
QPushButton[variante="primario"] {{ background: {c['primaria']}; color: {c['sobre_primaria']}; border: 1px solid {c['primaria']}; }}
QPushButton[variante="primario"]:hover {{ background: {c['primaria_hover']}; border-color: {c['primaria_hover']}; }}
QPushButton[variante="primario"]:focus {{ border: 2px solid {c['destaque']}; padding: 7px 13px; }}
QPushButton[variante="primario"]:disabled {{ background: {c['borda_forte']}; border-color: {c['borda_forte']}; color: {c['superficie']}; }}
QPushButton[variante="fantasma"] {{ background: transparent; border: 1px solid transparent; color: {c['texto_2']}; }}
QPushButton[variante="fantasma"]:hover {{ background: {c['realce']}; color: {c['texto']}; }}
QPushButton[variante="fantasma"]:focus {{ border: 2px solid {c['primaria']}; }}
QPushButton[variante="perigo"] {{ background: {c['superficie']}; color: {c['erro']}; border: 1px solid {c['erro']}; }}
QPushButton[variante="perigo"]:hover {{ background: {c['erro_suave']}; }}
QPushButton[variante="perigo_cheio"] {{ background: {c['erro']}; color: {c['superficie']}; border: 1px solid {c['erro']}; }}
QPushButton[variante="perigo_cheio"]:hover {{ background: {c['erro']}; border-color: {c['texto']}; }}
QPushButton[variante="icone"] {{ background: transparent; border: 1px solid transparent; padding: 6px; }}
QPushButton[variante="icone"]:hover {{ background: {c['realce']}; }}
QPushButton[variante="icone"]:focus {{ border: 2px solid {c['primaria']}; padding: 5px; }}

QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {{ background: {c['superficie']}; border: 1px solid {c['borda_forte']};
    border-radius: {r['p']}px; padding: 7px 10px; min-height: 20px; selection-background-color: {c['primaria_suave']};
    selection-color: {c['texto']}; }}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover {{ border-color: {c['texto_desab']}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {c['primaria']}; padding: 6px 9px; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: {c['texto_desab']}; background: {c['superficie_2']}; }}
QLineEdit[erro="true"], QPlainTextEdit[erro="true"], QComboBox[erro="true"] {{ border: 2px solid {c['erro']}; padding: 6px 9px; }}
QLineEdit[busca="true"] {{ padding-left: 34px; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: url("{baixo}"); width: 16px; height: 16px; margin-right: 8px; }}
QComboBox QAbstractItemView {{ background: {c['superficie']}; border: 1px solid {c['borda']}; padding: 4px;
    selection-background-color: {c['primaria_suave']}; selection-color: {c['texto']}; outline: none; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; border: none; background: transparent; }}
QSpinBox::up-arrow {{ image: url("{cima}"); width: 12px; height: 12px; }}
QSpinBox::down-arrow {{ image: url("{baixo}"); width: 12px; height: 12px; }}
QLabel[papel="unidade"] {{ color: {c['texto_2']}; font-size: {t['legenda']}px; font-weight: 500; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid {c['borda_forte']}; background: {c['superficie']}; }}
QCheckBox::indicator:checked {{ background: {c['primaria']}; border-color: {c['primaria']}; }}
QCheckBox:focus {{ color: {c['primaria']}; }}

QTableView {{ background: {c['superficie']}; alternate-background-color: {c['superficie_2']}; border: none;
    gridline-color: transparent; selection-background-color: {c['primaria_suave']}; selection-color: {c['texto']}; }}
QTableView::item {{ padding: 0 8px; border-bottom: 1px solid {c['borda']}; }}
QTableView::item:hover {{ background: {c['realce']}; }}
QTableView::item:selected {{ background: {c['primaria_suave']}; color: {c['texto']}; }}
QTableView:focus {{ border: 1px solid {c['primaria']}; }}
QHeaderView {{ background: {c['superficie_2']}; border: none; }}
QHeaderView::section {{ background: {c['superficie_2']}; color: {c['texto_2']}; font-size: {t['legenda']}px; font-weight: 600;
    border: none; border-bottom: 1px solid {c['borda']}; padding: 10px 12px; }}
QHeaderView::section:hover {{ color: {c['texto']}; }}
QListWidget {{ background: {c['superficie']}; border: 1px solid {c['borda']}; border-radius: {r['p']}px; padding: 4px; }}
QListWidget::item {{ padding: 7px 8px; border-radius: 4px; }}
QListWidget::item:selected {{ background: {c['primaria_suave']}; color: {c['texto']}; }}

QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{ background: transparent; color: {c['texto_2']}; padding: 10px 16px; margin-right: 4px;
    border: none; border-bottom: 2px solid transparent; font-weight: 500; }}
QTabBar::tab:hover {{ color: {c['texto']}; }}
QTabBar::tab:selected {{ color: {c['primaria']}; border-bottom: 2px solid {c['destaque']}; font-weight: 600; }}
QTabBar::tab:focus {{ color: {c['primaria']}; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['borda_forte']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['texto_desab']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['borda_forte']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QProgressBar {{ background: {c['realce']}; border: none; border-radius: 4px; max-height: 8px; min-height: 8px; color: transparent; }}
QProgressBar::chunk {{ background: {c['sucesso']}; border-radius: 4px; }}

QFrame#Lateral {{ background: {c['lateral']}; }}
QFrame#Lateral QLabel {{ color: {c['lateral_texto']}; }}
QFrame#Lateral QLabel#Marca, QLabel#Marca {{ color: #FFFFFF; font-size: 17px; font-weight: 700; }}
QPushButton[papel="nav"] {{ background: transparent; border: 2px solid transparent; border-radius: {r['p']}px;
    color: {c['lateral_texto']}; text-align: left; padding: 9px 10px; font-weight: 500; }}
QPushButton[papel="nav"]:hover {{ background: {c['lateral_hover']}; color: #FFFFFF; }}
QPushButton[papel="nav"]:focus {{ border: 2px solid {c['destaque']}; }}
QPushButton[papel="nav"][ativo="true"] {{ background: {c['lateral_ativo']}; color: #FFFFFF; font-weight: 600; }}
QPushButton[papel="lateral_acao"] {{ background: transparent; border: 2px solid transparent; border-radius: {r['p']}px;
    color: {c['lateral_texto']}; text-align: left; padding: 8px 10px; }}
QPushButton[papel="lateral_acao"]:hover {{ background: {c['lateral_hover']}; color: #FFFFFF; }}
QPushButton[papel="lateral_acao"]:focus {{ border: 2px solid {c['destaque']}; }}
QFrame#Cabecalho {{ background: {c['superficie']}; border: none; border-bottom: 1px solid {c['borda']}; }}

QCalendarWidget QWidget {{ alternate-background-color: {c['superficie_2']}; background: {c['superficie']}; }}
QCalendarWidget QAbstractItemView {{ background: {c['superficie']}; selection-background-color: {c['primaria']};
    selection-color: {c['sobre_primaria']}; }}
QCalendarWidget QToolButton {{ color: {c['texto']}; background: transparent; padding: 4px 8px; font-weight: 600; border: none; }}
QCalendarWidget QToolButton:hover {{ background: {c['realce']}; }}
QCalendarWidget QSpinBox {{ padding: 2px 4px; }}
QMenu {{ background: {c['superficie']}; border: 1px solid {c['borda']}; padding: 4px; }}
QMenu::item {{ padding: 8px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background: {c['primaria_suave']}; }}
"""

"""Aplicação da estação de trabalho: janela principal, tema e troca entre o login e a área de trabalho.

Na rede, os dados ficam no servidor central e as chamadas vão por ControladoresRemotos (pacote comunicacao).

A camada de apresentação não acessa os controladores nem o banco: tudo passa pelo pacote comunicacao.
"""
import sys

class App:

    def __init__(self, servidor=""):
        """servidor: endereço do servidor central (ex.: 192.168.0.10:8765); sem ele, usa o último que deu certo."""
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication, QMainWindow
        from . import tema
        from .componentes import TITULO
        self.qapp = QApplication.instance() or QApplication(sys.argv)
        self.qapp.setApplicationName(TITULO)
        tema.carregar_fontes()
        self.qapp.setFont(tema.fonte("corpo"))
        tema.Tema.carregar()
        self.qapp.setWindowIcon(QIcon(tema.logotipo(64)))
        self.ctrl = None                     # ControladoresRemotos, criado no login
        from PySide6.QtCore import QSettings
        self.servidor = servidor or QSettings("OficinaFacil", "OficinaFacil").value("servidor", "192.168.0.10:8765")
        self.janela = QMainWindow()
        self.janela.setObjectName("Janela")
        self.janela.setWindowTitle(TITULO)
        self.janela.setMinimumSize(1000, 640)
        tela = self.qapp.primaryScreen().availableGeometry()
        larg, alt = min(1280, tela.width() - 40), min(800, tela.height() - 60)
        self.janela.resize(larg, alt)
        self.janela.move(tela.x() + (tela.width() - larg) // 2, tela.y() + (tela.height() - alt) // 2)
        self.tela, self.usuario = None, None
        self.aplicar_estilo()
        self.sair()

    def aplicar_estilo(self):
        from .tema import qss
        self.qapp.setStyleSheet(qss())

    def alternar_tema(self):
        """Troca claro/escuro, salva a escolha e redesenha as telas abertas, na mesma página."""
        from .tema import Tema
        Tema.ouvintes.clear()
        Tema.definir("escuro" if Tema.nome == "claro" else "claro")
        self.aplicar_estilo()
        if self.usuario:
            pagina = self.tela.pagina_atual()
            abertas = [j.os_id for j in self.tela.janelas_os()]
            for j in self.tela.janelas_os():
                j.close()
            self.abrir_principal(self.usuario, pagina)
            for os_id in abertas:
                self.tela.abrir_os(os_id)
        else:
            self.sair()

    def _trocar(self, tela):
        antiga = self.tela
        self.tela = tela
        self.janela.setCentralWidget(tela)
        if antiga is not None:
            antiga.deleteLater()

    def abrir_principal(self, usuario, pagina=0):
        from .tela_principal import TelaPrincipal
        self.usuario = usuario
        self._trocar(TelaPrincipal(self, usuario, pagina))

    def conectar(self, endereco):
        """Prepara as chamadas ao servidor central e guarda o endereço para a próxima vez."""
        from PySide6.QtCore import QSettings
        from ..comunicacao.cliente import ControladoresRemotos
        self.ctrl = ControladoresRemotos(endereco)
        self.ctrl.api.status()                 # confere se o servidor responde
        self.servidor = self.ctrl.endereco
        QSettings("OficinaFacil", "OficinaFacil").setValue("servidor", self.servidor)

    def sair(self):
        from .tela_login import TelaLogin
        if self.usuario and self.tela is not None:
            for j in self.tela.janelas_os():
                j.close()
        if self.usuario and self.ctrl is not None:
            self.ctrl.sair()                      # encerra a sessão no servidor
        self.usuario = None
        self._trocar(TelaLogin(self))

    def executar(self):
        self.janela.show()
        return self.qapp.exec()

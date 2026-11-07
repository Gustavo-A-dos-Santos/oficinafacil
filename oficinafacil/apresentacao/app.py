"""Aplicação: janela raiz, estilos e troca entre a tela de login e a tela principal."""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from ..controle.auth_controller import AuthController
from ..controle.cadastro_controller import CadastroController
from ..controle.orcamento_controller import OrcamentoController
from ..controle.os_controller import OSController
from ..controle.pagamento_controller import PagamentoController
from ..controle.pecas_compras_controller import PecasComprasController
from ..controle.relatorio_controller import RelatorioController
from .componentes import TITULO
from .tela_login import TelaLogin
from .tela_principal import TelaPrincipal


class Controladores:
    """Os sete controladores usados pelas telas (como os BO de cada formulário)."""

    def __init__(self, conn):
        self.auth = AuthController(conn)
        self.cadastro = CadastroController(conn)
        self.os = OSController(conn)
        self.orcamento = OrcamentoController(conn)
        self.compras = PecasComprasController(conn)
        self.pagamento = PagamentoController(conn)
        self.relatorio = RelatorioController(conn)


class App:

    def __init__(self, conn):
        self.ctrl = Controladores(conn)
        self.root = tk.Tk()
        self.root.title(TITULO)
        # janela no centro da tela, sem passar do tamanho da tela em monitores pequenos
        larg, alt = min(1150, self.root.winfo_screenwidth() - 40), min(680, self.root.winfo_screenheight() - 80)
        x, y = (self.root.winfo_screenwidth() - larg) // 2, max((self.root.winfo_screenheight() - alt) // 2 - 20, 0)
        self.root.geometry(f"{larg}x{alt}+{x}+{y}")
        self.root.minsize(900, 560)
        for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(nome).configure(size=11)
        estilo = ttk.Style()
        if "vista" in estilo.theme_names():
            estilo.theme_use("vista")
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1f4e79")
        estilo.configure("Sub.TLabel", font=("Segoe UI", 12, "bold"))
        estilo.configure("Numero.TLabel", font=("Segoe UI", 20, "bold"), foreground="#1f4e79")
        estilo.configure("Treeview", rowheight=24)
        self.tela = None
        self.sair()

    def _trocar(self, tela):
        if self.tela:
            self.tela.destroy()
        self.tela = tela
        if isinstance(tela, TelaLogin):
            tela.place(relx=0.5, rely=0.5, anchor="center")  # formulário de login no centro da janela
        else:
            tela.pack(fill="both", expand=True)

    def abrir_principal(self, usuario):
        self._trocar(TelaPrincipal(self, usuario))

    def sair(self):
        for janela in self.root.winfo_children():
            if isinstance(janela, tk.Toplevel):
                janela.destroy()
        self._trocar(TelaLogin(self))

    def executar(self):
        self.root.mainloop()

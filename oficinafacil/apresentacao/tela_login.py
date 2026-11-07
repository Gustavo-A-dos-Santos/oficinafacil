"""Tela de login (RF01)."""
from tkinter import messagebox, ttk

from .componentes import TITULO


class TelaLogin(ttk.Frame):

    def __init__(self, app):
        super().__init__(app.root, padding=40)
        self.app = app
        ttk.Label(self, text=TITULO, style="Titulo.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 4))
        ttk.Label(self, text="Gestão de ordens de serviço da oficina").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        ttk.Label(self, text="Login:").grid(row=2, column=0, sticky="e", pady=4)
        ttk.Label(self, text="Senha:").grid(row=3, column=0, sticky="e", pady=4)
        self.login, self.senha = ttk.Entry(self, width=25), ttk.Entry(self, width=25, show="*")
        self.login.grid(row=2, column=1, pady=4)
        self.senha.grid(row=3, column=1, pady=4)
        ttk.Button(self, text="Entrar", command=self.entrar).grid(row=4, column=0, columnspan=2, pady=16)
        ttk.Label(self, text="Usuários de teste: gerente, atendente, mecanico (senha 123)",
                  foreground="gray").grid(row=5, column=0, columnspan=2)
        self.senha.bind("<Return>", lambda e: self.entrar())
        self.login.bind("<Return>", lambda e: self.senha.focus())
        self.login.focus()

    def entrar(self):
        usuario = self.app.ctrl.auth.autenticar(self.login.get().strip(), self.senha.get())
        if not usuario:
            messagebox.showerror(TITULO, "Login ou senha inválidos, ou usuário inativo.")
            return
        self.app.abrir_principal(usuario)

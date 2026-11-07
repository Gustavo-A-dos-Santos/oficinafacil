"""Componentes comuns das telas: tabela, formulário, diálogos e o tratamento de erros de regra de negócio."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..modelo import RegraNegocioError

TITULO = "OficinaFácil"


def executar(func, *args, sucesso=None, parent=None, **kwargs):
    """Chama um método de controlador e mostra o erro de regra de negócio numa caixa de aviso."""
    try:
        resultado = func(*args, **kwargs)
    except RegraNegocioError as e:
        messagebox.showwarning(TITULO, str(e), parent=parent)
        return None
    if sucesso:
        messagebox.showinfo(TITULO, sucesso, parent=parent)
    return resultado if resultado is not None else True


def criar_tabela(pai, colunas, altura=10):
    """colunas: lista de (atributo, título, largura). Devolve o Treeview, já com barra de rolagem."""
    quadro = ttk.Frame(pai)
    tree = ttk.Treeview(quadro, columns=[c[0] for c in colunas], show="headings", height=altura, selectmode="browse")
    for chave, titulo, largura in colunas:
        tree.heading(chave, text=titulo)
        tree.column(chave, width=largura, anchor="w")
    barra = ttk.Scrollbar(quadro, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=barra.set)
    tree.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    tree.quadro = quadro
    tree.chaves = [c[0] for c in colunas]
    return tree


def preencher(tree, objetos, formatos=None):
    """Mostra uma lista de objetos do modelo; cada coluna é um atributo (formatos: atributo -> função)."""
    formatos = formatos or {}
    tree.delete(*tree.get_children())
    for obj in objetos:
        valores = []
        for chave in tree.chaves:
            v = getattr(obj, chave, "")
            if chave in formatos:
                v = formatos[chave](v)
            valores.append("" if v is None else v)
        tree.insert("", "end", iid=str(obj.id), values=valores)


def selecionado(tree, aviso="Selecione um item na lista."):
    sel = tree.selection()
    if not sel:
        messagebox.showinfo(TITULO, aviso, parent=tree.winfo_toplevel())
        return None
    return int(sel[0])


def sim_nao(v):
    return "Sim" if v else "Não"


def opcao(id, texto):
    return f"{id} - {texto}"


def id_da_opcao(texto):
    try:
        return int(str(texto).split(" - ")[0])
    except ValueError:
        return None


class Formulario(ttk.Frame):
    """Rótulos e campos em grade. campos: (atributo, rótulo) ou (atributo, rótulo, opções) para lista."""

    def __init__(self, pai, campos, colunas=1):
        super().__init__(pai)
        self.vars = {}
        for i, campo in enumerate(campos):
            chave, rotulo = campo[0], campo[1]
            lin, col = divmod(i, colunas)
            ttk.Label(self, text=rotulo + ":").grid(row=lin, column=col * 2, sticky="e", padx=4, pady=3)
            var = tk.StringVar()
            if len(campo) > 2:
                w = ttk.Combobox(self, textvariable=var, values=campo[2], state="readonly", width=28)
            else:
                w = ttk.Entry(self, textvariable=var, width=30)
            w.grid(row=lin, column=col * 2 + 1, sticky="w", padx=4, pady=3)
            self.vars[chave] = var

    def obter(self):
        return {k: v.get().strip() for k, v in self.vars.items()}

    def definir(self, obj):
        for chave, var in self.vars.items():
            v = getattr(obj, chave, "")
            var.set("" if v is None else str(v))

    def limpar(self):
        for var in self.vars.values():
            var.set("")


class Dialogo(tk.Toplevel):
    """Janela modal com OK e Cancelar; as subclasses montam o corpo e implementam validar()."""

    def __init__(self, pai, titulo):
        super().__init__(pai)
        self.title(titulo)
        self.resultado = None
        self.corpo = ttk.Frame(self, padding=12)
        self.corpo.pack(fill="both", expand=True)
        botoes = ttk.Frame(self, padding=(12, 0, 12, 12))
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Cancelar", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(botoes, text="OK", command=self._ok).pack(side="right", padx=4)
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(pai)

    def mostrar(self):
        self.grab_set()
        self.wait_window()
        return self.resultado

    def _ok(self):
        r = self.validar()
        if r is not None:
            self.resultado = r
            self.destroy()

    def validar(self):
        return True


class DialogoCampos(Dialogo):
    def __init__(self, pai, titulo, campos, valores=None):
        super().__init__(pai, titulo)
        self.form = Formulario(self.corpo, campos)
        self.form.pack()
        for k, v in (valores or {}).items():
            self.form.vars[k].set(v)

    def validar(self):
        return self.form.obter()


def pedir(pai, titulo, campos, valores=None):
    return DialogoCampos(pai, titulo, campos, valores).mostrar()


class DialogoItens(Dialogo):
    """Escolha de serviços e peças do catálogo (diagnóstico RF11 e execução RF26)."""

    def __init__(self, pai, cadastro, titulo, com_descricao, aviso=""):
        super().__init__(pai, titulo)
        self.com_descricao = com_descricao
        self.servicos, self.pecas = [], []
        c, linha = self.corpo, 0
        if aviso:
            ttk.Label(c, text=aviso, foreground="gray", wraplength=560).grid(row=0, column=0, columnspan=4, sticky="w")
            linha = 1
        if com_descricao:
            ttk.Label(c, text="Diagnóstico e observações:").grid(row=linha, column=0, columnspan=4, sticky="w")
            self.texto = tk.Text(c, width=60, height=4)
            self.texto.grid(row=linha + 1, column=0, columnspan=4, pady=(0, 8))
            linha += 2
        from ..modelo import moeda
        servicos = [opcao(s.id, f"{s.descricao} ({moeda(s.valor_base)})") for s in cadastro.get_servicos(True)]
        pecas = [opcao(p.id, f"{p.descricao} ({moeda(p.valor)}, estoque {p.qtd_estoque})") for p in cadastro.get_pecas()]
        self.cb_serv, self.qt_serv = self._linha(linha, "Serviço:", servicos, self._add_servico)
        self.cb_peca, self.qt_peca = self._linha(linha + 1, "Peça:", pecas, self._add_peca)
        self.lista = tk.Listbox(c, width=70, height=7)
        self.lista.grid(row=linha + 2, column=0, columnspan=4, pady=6)

    def _linha(self, linha, rotulo, valores, comando):
        ttk.Label(self.corpo, text=rotulo).grid(row=linha, column=0, sticky="e")
        cb = ttk.Combobox(self.corpo, values=valores, state="readonly", width=45)
        cb.grid(row=linha, column=1, padx=4, pady=2)
        qt = ttk.Spinbox(self.corpo, from_=1, to=99, width=4)
        qt.set(1)
        qt.grid(row=linha, column=2)
        ttk.Button(self.corpo, text="Adicionar", command=comando).grid(row=linha, column=3, padx=4)
        return cb, qt

    def _add(self, cb, qt, destino, tipo):
        item_id = id_da_opcao(cb.get())
        if item_id:
            destino.append((item_id, qt.get()))
            self.lista.insert("end", f"{tipo}: {qt.get()} x {cb.get().split(' - ', 1)[1]}")

    def _add_servico(self):
        self._add(self.cb_serv, self.qt_serv, self.servicos, "Serviço")

    def _add_peca(self):
        self._add(self.cb_peca, self.qt_peca, self.pecas, "Peça")

    def validar(self):
        descricao = self.texto.get("1.0", "end").strip() if self.com_descricao else ""
        return descricao, self.servicos, self.pecas

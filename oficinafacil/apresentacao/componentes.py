"""Componentes comuns das telas: tabela, formulário, diálogos, campo de data com calendário e o tratamento
de erros de regra de negócio."""
import calendar
import os
import tkinter as tk
import webbrowser
from datetime import date, timedelta
from tkinter import messagebox, ttk

from ..modelo import RegraNegocioError, moeda

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
    """Escolha de serviços e peças do catálogo, com pesquisa (diagnóstico RF11 e execução RF26)."""

    def __init__(self, pai, cadastro, titulo, com_descricao, aviso=""):
        super().__init__(pai, titulo)
        self.cadastro, self.com_descricao = cadastro, com_descricao
        self.servicos, self.pecas = [], []
        c, linha = self.corpo, 0
        if aviso:
            ttk.Label(c, text=aviso, foreground="gray", wraplength=640).grid(row=0, column=0, columnspan=5, sticky="w")
            linha = 1
        if com_descricao:
            ttk.Label(c, text="Diagnóstico e observações:").grid(row=linha, column=0, columnspan=5, sticky="w")
            self.texto = tk.Text(c, width=72, height=4)
            self.texto.grid(row=linha + 1, column=0, columnspan=5, pady=(0, 8))
            linha += 2
        ttk.Label(c, text="Pesquisar", foreground="gray").grid(row=linha, column=1, sticky="w", padx=4)
        ttk.Label(c, text="Resultado (escolha um)", foreground="gray").grid(row=linha, column=2, sticky="w", padx=4)
        self.cb_serv, self.qt_serv = self._linha(linha + 1, "Serviço:", self._opcoes_servico, self._add_servico)
        self.cb_peca, self.qt_peca = self._linha(linha + 2, "Peça:", self._opcoes_peca, self._add_peca)
        self.lista = tk.Listbox(c, width=86, height=7)
        self.lista.grid(row=linha + 3, column=0, columnspan=5, pady=(8, 2))
        ttk.Button(c, text="Retirar da lista", command=self._retirar).grid(row=linha + 4, column=4, sticky="e")

    def _opcoes_servico(self, busca=""):
        return [opcao(s.id, f"{s.descricao} ({moeda(s.valor_base)})") for s in self.cadastro.get_servicos(True, busca)]

    def _opcoes_peca(self, busca=""):
        return [opcao(p.id, f"{p.descricao} ({moeda(p.valor)}, estoque {p.qtd_estoque})")
                for p in self.cadastro.get_pecas(busca)]

    def _linha(self, linha, rotulo, opcoes, comando):
        ttk.Label(self.corpo, text=rotulo).grid(row=linha, column=0, sticky="e")
        busca = ttk.Entry(self.corpo, width=16)
        busca.grid(row=linha, column=1, padx=4, pady=2)
        cb = ttk.Combobox(self.corpo, values=opcoes(), state="readonly", width=44)
        cb.grid(row=linha, column=2, padx=4, pady=2)

        def filtrar(_evento=None):  # a cada tecla, mostra só o que contém o texto (sem diferenciar acentos)
            valores = opcoes(busca.get())
            cb["values"] = valores
            cb.set(valores[0] if valores and busca.get().strip() else "")
        busca.bind("<KeyRelease>", filtrar)
        busca.bind("<Return>", lambda e: comando())
        qt = ttk.Spinbox(self.corpo, from_=1, to=99, width=4)
        qt.set(1)
        qt.grid(row=linha, column=3)
        ttk.Button(self.corpo, text="Adicionar", command=comando).grid(row=linha, column=4, padx=4)
        return cb, qt

    def _add(self, cb, qt, destino, tipo):
        item_id = id_da_opcao(cb.get())
        if not item_id:
            messagebox.showinfo(TITULO, f"Pesquise e escolha o item ({tipo.lower()}) na lista.", parent=self)
            return
        destino.append((item_id, qt.get()))
        self.lista.insert("end", f"{tipo}: {qt.get()} x {cb.get().split(' - ', 1)[1]}")

    def _add_servico(self):
        self._add(self.cb_serv, self.qt_serv, self.servicos, "Serviço")

    def _add_peca(self):
        self._add(self.cb_peca, self.qt_peca, self.pecas, "Peça")

    def _retirar(self):
        sel = self.lista.curselection()
        if not sel:
            return
        n = sel[0]
        tipo = self.lista.get(n).split(":")[0]
        destino = self.servicos if tipo == "Serviço" else self.pecas
        posicao = sum(1 for i in range(n) if self.lista.get(i).split(":")[0] == tipo)  # posição entre os do mesmo tipo
        del destino[posicao]
        self.lista.delete(n)

    def validar(self):
        descricao = self.texto.get("1.0", "end").strip() if self.com_descricao else ""
        return descricao, self.servicos, self.pecas


# ---------------------------------------------------------------- datas com calendário
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro",
         "Novembro", "Dezembro"]
AZUL, AZUL_CLARO = "#1f4e79", "#e3edf7"


def data_de_texto(texto):
    """'07/11/2026' -> date; devolve None se o texto não for uma data."""
    try:
        d, m, a = (int(x) for x in str(texto).strip().split("/"))
        return date(a, m, d)
    except (ValueError, TypeError):
        return None


class Calendario(tk.Toplevel):
    """Calendário do mês, aberto embaixo do campo de data; um clique no dia escolhe a data."""

    def __init__(self, campo):
        super().__init__(campo)
        self.campo = campo
        self.title("Escolha a data")
        self.resizable(False, False)
        self.transient(campo.winfo_toplevel())
        self.mes = (campo.data() or date.today()).replace(day=1)
        self.quadro = tk.Frame(self, background="white", padx=8, pady=8)
        self.quadro.pack()
        self._desenhar()
        self.geometry(f"+{campo.winfo_rootx()}+{campo.winfo_rooty() + campo.winfo_height()}")
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()  # enquanto aberto, o clique vai para o calendário
        self.focus_force()

    def _desenhar(self):
        for w in self.quadro.winfo_children():
            w.destroy()
        q = self.quadro
        topo = tk.Frame(q, background="white")
        topo.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 4))
        estilo = dict(relief="flat", background="white", activebackground=AZUL_CLARO, cursor="hand2",
                      font=("Segoe UI", 11, "bold"), foreground=AZUL)
        for texto, meses, lado in (("«", -12, "left"), ("‹", -1, "left"), ("»", 12, "right"), ("›", 1, "right")):
            tk.Button(topo, text=texto, command=lambda m=meses: self._mudar(m), **estilo).pack(side=lado)
        tk.Label(topo, text=f"{MESES[self.mes.month - 1]} de {self.mes.year}", background="white",
                 font=("Segoe UI", 10, "bold"), foreground=AZUL).pack(side="left", expand=True)
        for i, nome in enumerate(["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]):
            tk.Label(q, text=nome, background="white", foreground="gray", width=4).grid(row=1, column=i)
        hoje, escolhida = date.today(), self.campo.data()
        semanas = calendar.Calendar(firstweekday=6).monthdayscalendar(self.mes.year, self.mes.month)
        for lin, semana in enumerate(semanas, start=2):
            for col, dia in enumerate(semana):
                if not dia:
                    continue
                d = self.mes.replace(day=dia)
                if d == escolhida:
                    fundo, letra = AZUL, "white"
                elif d == hoje:
                    fundo, letra = AZUL_CLARO, AZUL
                else:
                    fundo, letra = "white", "black"
                tk.Button(q, text=str(dia), width=3, relief="flat", background=fundo, foreground=letra,
                          activebackground="#c9daea", cursor="hand2",
                          command=lambda d=d: self._escolher(d)).grid(row=lin, column=col, padx=1, pady=1)
        rodape = tk.Frame(q, background="white")
        rodape.grid(row=9, column=0, columnspan=7, sticky="ew", pady=(6, 0))
        estilo["font"] = ("Segoe UI", 9)
        tk.Button(rodape, text="Hoje", command=lambda: self._escolher(hoje), **estilo).pack(side="left")
        tk.Button(rodape, text="Limpar", command=lambda: self._escolher(None), **estilo).pack(side="right")

    def _mudar(self, meses):
        total = self.mes.year * 12 + self.mes.month - 1 + meses
        self.mes = date(total // 12, total % 12 + 1, 1)
        self._desenhar()

    def _escolher(self, d):
        self.campo.definir(d)
        self.destroy()


class CampoData(ttk.Frame):
    """Campo de data DD/MM/AAAA com botão que abre o calendário (também aceita a data digitada).
    get() devolve AAAA-MM-DD (o formato do banco), vazio, ou o texto digitado se não for uma data,
    para o controlador recusar com a mensagem certa."""

    def __init__(self, pai, ao_mudar=None):
        super().__init__(pai)
        self.ao_mudar = ao_mudar
        self.var = tk.StringVar()
        entrada = ttk.Entry(self, textvariable=self.var, width=11)
        entrada.pack(side="left")
        entrada.bind("<Return>", lambda e: self._mudou())
        ttk.Button(self, text="▼", width=3, command=self.abrir).pack(side="left", padx=(1, 0))

    def abrir(self):
        Calendario(self)

    def data(self):
        return data_de_texto(self.var.get())

    def definir(self, d):
        self.var.set(d.strftime("%d/%m/%Y") if d else "")
        self._mudou()

    def _mudou(self):
        if self.ao_mudar:
            self.ao_mudar()

    def get(self):
        texto = self.var.get().strip()
        d = data_de_texto(texto)
        return d.isoformat() if d else texto


def periodos_rapidos():
    """Atalhos de período: (nome, data inicial, data final)."""
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    fim_mes_anterior = inicio_mes - timedelta(days=1)
    return [("Hoje", hoje, hoje), ("Últimos 7 dias", hoje - timedelta(days=6), hoje),
            ("Este mês", inicio_mes, hoje), ("Mês anterior", fim_mes_anterior.replace(day=1), fim_mes_anterior),
            ("Este ano", hoje.replace(month=1, day=1), hoje), ("Tudo", None, None)]


class SeletorPeriodo(ttk.Frame):
    """Dois campos de data (de / até) e os atalhos de período numa lista."""

    def __init__(self, pai, ao_mudar=None):
        super().__init__(pai)
        self.ao_mudar = ao_mudar
        ttk.Label(self, text="De:").pack(side="left", padx=(0, 2))
        self.de = CampoData(self)
        self.de.pack(side="left")
        ttk.Label(self, text="até:").pack(side="left", padx=(6, 2))
        self.ate = CampoData(self)
        self.ate.pack(side="left")
        self.atalhos = periodos_rapidos()
        self.rapido = ttk.Combobox(self, state="readonly", width=14, values=[n for n, _, _ in self.atalhos])
        self.rapido.set("Período...")
        self.rapido.pack(side="left", padx=6)
        self.rapido.bind("<<ComboboxSelected>>", self._atalho)

    def _atalho(self, _evento):
        _, de, ate = self.atalhos[self.rapido.current()]
        self.de.var.set(de.strftime("%d/%m/%Y") if de else "")
        self.ate.var.set(ate.strftime("%d/%m/%Y") if ate else "")
        if self.ao_mudar:
            self.ao_mudar()

    def get(self):
        return self.de.get(), self.ate.get()


def abrir_arquivo(caminho):
    """Abre o arquivo no programa padrão (o leitor de PDF, por exemplo)."""
    try:
        os.startfile(caminho)  # Windows
    except AttributeError:
        webbrowser.open("file://" + os.path.abspath(caminho))


def salvar_e_abrir_pdf(pai, nome_inicial, gravar):
    """Pergunta onde salvar, chama gravar(caminho) e oferece abrir o PDF gerado."""
    from tkinter import filedialog
    caminho = filedialog.asksaveasfilename(parent=pai, defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                           initialfile=nome_inicial)
    if caminho and executar(gravar, caminho, parent=pai):
        if messagebox.askyesno(TITULO, f"PDF salvo em:\n{caminho}\n\nAbrir agora?", parent=pai):
            abrir_arquivo(caminho)

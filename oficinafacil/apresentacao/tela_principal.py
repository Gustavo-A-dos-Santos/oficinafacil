"""Tela principal: cabeçalho com o usuário e as abas permitidas ao perfil."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..modelo import moeda
from ..modelo.atendimento import StatusOS
from ..modelo.cadastro import Perfil
from .componentes import (TITULO, Dialogo, Formulario, criar_tabela, executar, id_da_opcao, opcao, pedir, preencher,
                          selecionado, sim_nao)
from .janela_os import JanelaOS

COLUNAS_OS = [("id", "OS", 45), ("status", "Status", 165), ("data_abertura", "Abertura", 160),
              ("cliente_nome", "Cliente", 150), ("placa", "Placa", 90), ("modelo", "Modelo", 90),
              ("mecanico_nome", "Mecânico", 120), ("problema", "Problema", 250)]
FORMATO_OS = {"status": lambda s: StatusOS.NOMES.get(s, s)}


class TelaPrincipal(ttk.Frame):

    def __init__(self, app, usuario):
        super().__init__(app.root, padding=8)
        self.app, self.ctrl, self.usuario = app, app.ctrl, usuario
        topo = ttk.Frame(self)
        topo.pack(fill="x")
        ttk.Label(topo, text=TITULO, style="Titulo.TLabel").pack(side="left")
        ttk.Button(topo, text="Sair", command=app.sair).pack(side="right")
        ttk.Label(topo, text=f"{usuario.nome} ({Perfil.NOMES[usuario.perfil]})").pack(side="right", padx=10)
        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, pady=6)
        p = usuario.perfil
        self._aba(AbaPainel, "Painel")
        self._aba(AbaOS, "Ordens de serviço")
        if p in (Perfil.ATENDENTE, Perfil.GERENTE):
            self._aba(AbaClientes, "Clientes e veículos")
        if p == Perfil.GERENTE:
            self._aba(AbaCompras, "Compras")
            self._aba(AbaCatalogo, "Catálogo")
            self._aba(AbaUsuarios, "Usuários")
            self._aba(AbaRelatorios, "Relatórios")
        self.abas.bind("<<NotebookTabChanged>>", lambda e: self.atualizar_aba_atual())

    def _aba(self, classe, titulo):
        self.abas.add(classe(self.abas, self), text=titulo)

    def atualizar_aba_atual(self):
        self.abas.nametowidget(self.abas.select()).atualizar()

    def abrir_os(self, os_id):
        JanelaOS(self, os_id)


class Aba(ttk.Frame):
    def __init__(self, pai, principal):
        super().__init__(pai, padding=8)
        self.principal, self.ctrl, self.usuario = principal, principal.ctrl, principal.usuario
        self.perfil = self.usuario.perfil

    def atualizar(self):
        pass


class AbaPainel(Aba):
    """RF35 (painel) e pendências do perfil (RF10, RF15, RF28)."""

    def __init__(self, pai, principal):
        super().__init__(pai, principal)
        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x")
        ttk.Label(self, text="Minhas pendências (dê dois cliques para abrir a OS)", style="Sub.TLabel").pack(anchor="w", pady=(14, 4))
        self.tree = criar_tabela(self, COLUNAS_OS, 12)
        self.tree.quadro.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self._abrir())
        self.aviso = ttk.Label(self, foreground="#a33")
        self.aviso.pack(anchor="w", pady=4)
        ttk.Button(self, text="Atualizar", command=self.atualizar).pack(anchor="e")
        self.atualizar()

    def _abrir(self):
        os_id = selecionado(self.tree)
        if os_id:
            self.principal.abrir_os(os_id)

    def atualizar(self):
        for w in self.cards.winfo_children():
            w.destroy()
        contagem = self.ctrl.relatorio.painel()
        for i, (nome, qtd) in enumerate(contagem):
            card = ttk.Frame(self.cards, padding=8, relief="groove")
            card.grid(row=0, column=i, padx=3, sticky="nsew")
            ttk.Label(card, text=str(qtd), style="Numero.TLabel").pack()
            ttk.Label(card, text=nome).pack()
        preencher(self.tree, self.ctrl.os.pendencias(self.usuario), FORMATO_OS)
        avisos = []
        if not any(q for _, q in contagem):
            avisos.append("Não há OS em andamento.")
        baixos = self.ctrl.compras.pecas_abaixo_do_minimo()
        if self.perfil == Perfil.GERENTE and baixos:
            avisos.append("Peças abaixo do estoque mínimo: " + ", ".join(p.descricao for p in baixos))
        self.aviso.config(text="   ".join(avisos))


class AbaOS(Aba):
    """RF13 (consulta e filtro) e RF08 (nova OS)."""

    def __init__(self, pai, principal):
        super().__init__(pai, principal)
        filtros = ttk.Frame(self)
        filtros.pack(fill="x")
        self.status = ttk.Combobox(filtros, state="readonly", width=18, values=["Todos"] + list(StatusOS.NOMES.values()))
        self.status.set("Todos")
        self.cliente, self.placa = ttk.Entry(filtros, width=16), ttk.Entry(filtros, width=10)
        self.de, self.ate = ttk.Entry(filtros, width=11), ttk.Entry(filtros, width=11)
        for rotulo, w in [("Status", self.status), ("Cliente", self.cliente), ("Placa", self.placa),
                          ("De (AAAA-MM-DD)", self.de), ("Até", self.ate)]:
            ttk.Label(filtros, text=rotulo + ":").pack(side="left", padx=(8, 2))
            w.pack(side="left")
        ttk.Button(filtros, text="Buscar", command=self.atualizar).pack(side="left", padx=8)
        self.tree = criar_tabela(self, COLUNAS_OS, 16)
        self.tree.quadro.pack(fill="both", expand=True, pady=8)
        self.tree.bind("<Double-1>", lambda e: self._abrir())
        botoes = ttk.Frame(self)
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Abrir detalhes da OS", command=self._abrir).pack(side="right")
        if self.perfil in (Perfil.ATENDENTE, Perfil.GERENTE):
            ttk.Button(botoes, text="Nova OS", command=self.nova_os).pack(side="left")
        self.atualizar()

    def atualizar(self):
        codigo = next((k for k, v in StatusOS.NOMES.items() if v == self.status.get()), None)
        lista = self.ctrl.os.get_lista(self.usuario, codigo, self.cliente.get().strip(), self.placa.get().strip(),
                                       self.de.get().strip(), self.ate.get().strip())
        preencher(self.tree, lista, FORMATO_OS)

    def _abrir(self):
        os_id = selecionado(self.tree)
        if os_id:
            self.principal.abrir_os(os_id)

    def nova_os(self):
        r = DialogoNovaOS(self, self.ctrl.cadastro).mostrar()
        if r:
            os_id = executar(self.ctrl.os.abrir_os, self.usuario, r["cliente_id"], r["veiculo_id"], r["problema"], r["km"])
            if os_id:
                messagebox.showinfo(TITULO, f"OS nº {os_id} aberta. O mecânico foi avisado no painel.")
                self.atualizar()
                self.principal.abrir_os(os_id)


class DialogoNovaOS(Dialogo):
    def __init__(self, pai, cadastro):
        super().__init__(pai, "Nova ordem de serviço")
        self.cadastro = cadastro
        c = self.corpo
        clientes = [opcao(x.id, x.nome) for x in cadastro.get_clientes(so_ativos=True)]
        ttk.Label(c, text="Cliente:").grid(row=0, column=0, sticky="e", pady=3)
        self.cliente = ttk.Combobox(c, values=clientes, state="readonly", width=40)
        self.cliente.grid(row=0, column=1, pady=3)
        self.cliente.bind("<<ComboboxSelected>>", self._carregar_veiculos)
        ttk.Label(c, text="Veículo:").grid(row=1, column=0, sticky="e", pady=3)
        self.veiculo = ttk.Combobox(c, state="readonly", width=40)
        self.veiculo.grid(row=1, column=1, pady=3)
        ttk.Label(c, text="Km de entrada:").grid(row=2, column=0, sticky="e", pady=3)
        self.km = ttk.Entry(c, width=12)
        self.km.grid(row=2, column=1, sticky="w", pady=3)
        ttk.Label(c, text="Problema relatado:").grid(row=3, column=0, sticky="ne", pady=3)
        self.problema = tk.Text(c, width=40, height=4)
        self.problema.grid(row=3, column=1, pady=3)
        ttk.Label(c, text="Cliente ou veículo novo? Cadastre antes na aba Clientes e veículos.",
                  foreground="gray").grid(row=4, column=0, columnspan=2)

    def _carregar_veiculos(self, _evento=None):
        veiculos = self.cadastro.get_veiculos(id_da_opcao(self.cliente.get()))
        self.veiculo["values"] = [opcao(v.id, f"{v.placa} - {v.marca} {v.modelo}") for v in veiculos]
        self.veiculo.set("")
        if veiculos:
            self.veiculo.current(0)
            self.km.delete(0, "end")
            self.km.insert(0, veiculos[0].km or "")

    def validar(self):
        cliente_id, veiculo_id = id_da_opcao(self.cliente.get()), id_da_opcao(self.veiculo.get())
        if not cliente_id or not veiculo_id:
            messagebox.showwarning(TITULO, "Selecione o cliente e o veículo.", parent=self)
            return None
        return {"cliente_id": cliente_id, "veiculo_id": veiculo_id, "km": self.km.get(),
                "problema": self.problema.get("1.0", "end").strip()}


class AbaClientes(Aba):
    """RF03, RF04 e RF33 (histórico)."""

    def __init__(self, pai, principal):
        super().__init__(pai, principal)
        self.cliente_id = self.veiculo_id = None
        esq = ttk.LabelFrame(self, text="Clientes", padding=6)
        dir_ = ttk.LabelFrame(self, text="Veículos do cliente", padding=6)
        esq.pack(side="left", fill="both", expand=True, padx=(0, 4))
        dir_.pack(side="left", fill="both", expand=True, padx=(4, 0))
        busca = ttk.Frame(esq)
        busca.pack(fill="x")
        ttk.Label(busca, text="Buscar (nome, telefone ou CPF):").pack(side="left")
        self.busca = ttk.Entry(busca, width=20)
        self.busca.pack(side="left", padx=4)
        self.busca.bind("<KeyRelease>", lambda e: self.atualizar())
        self.tc = criar_tabela(esq, [("id", "Cód.", 45), ("nome", "Nome", 170), ("telefone", "Telefone", 120),
                                     ("ativo", "Ativo", 50)], 8)
        self.tc.quadro.pack(fill="both", expand=True, pady=4)
        self.tc.bind("<<TreeviewSelect>>", self._selecionar_cliente)
        self.fc = Formulario(esq, [("nome", "Nome"), ("telefone", "Telefone"), ("cpf", "CPF (opcional)"), ("email", "E-mail")])
        self.fc.pack(anchor="w")
        bc = ttk.Frame(esq)
        bc.pack(fill="x", pady=4)
        ttk.Button(bc, text="Novo", command=self._novo_cliente).pack(side="left")
        ttk.Button(bc, text="Salvar", command=self._salvar_cliente).pack(side="left", padx=4)
        ttk.Button(bc, text="Ativar/Inativar", command=self._inativar_cliente).pack(side="left")
        ttk.Button(bc, text="Histórico do cliente", command=self._historico_cliente).pack(side="left", padx=4)

        self.tv = criar_tabela(dir_, [("id", "Cód.", 45), ("placa", "Placa", 80), ("marca", "Marca", 90),
                                      ("modelo", "Modelo", 100), ("ano", "Ano", 50), ("km", "Km", 70)], 8)
        self.tv.quadro.pack(fill="both", expand=True, pady=(26, 4))
        self.tv.bind("<<TreeviewSelect>>", self._selecionar_veiculo)
        self.fv = Formulario(dir_, [("placa", "Placa"), ("marca", "Marca"), ("modelo", "Modelo"), ("ano", "Ano"),
                                    ("km", "Quilometragem")])
        self.fv.pack(anchor="w")
        bv = ttk.Frame(dir_)
        bv.pack(fill="x", pady=4)
        ttk.Button(bv, text="Novo", command=self._novo_veiculo).pack(side="left")
        ttk.Button(bv, text="Salvar", command=self._salvar_veiculo).pack(side="left", padx=4)
        ttk.Button(bv, text="Histórico do veículo", command=self._historico_veiculo).pack(side="left")
        self.atualizar()

    def atualizar(self):
        preencher(self.tc, self.ctrl.cadastro.get_clientes(self.busca.get().strip()), {"ativo": sim_nao})
        self._listar_veiculos()

    def _listar_veiculos(self):
        preencher(self.tv, self.ctrl.cadastro.get_veiculos(self.cliente_id) if self.cliente_id else [])

    def _selecionar_cliente(self, _evento):
        sel = self.tc.selection()
        if sel:
            self.cliente_id = int(sel[0])
            self.fc.definir(self.ctrl.cadastro.get_cliente(self.cliente_id))
            self._novo_veiculo()
            self._listar_veiculos()

    def _selecionar_veiculo(self, _evento):
        sel = self.tv.selection()
        if sel:
            self.veiculo_id = int(sel[0])
            self.fv.definir(self.ctrl.cadastro.get_veiculo(self.veiculo_id))

    def _novo_cliente(self):
        self.cliente_id = None
        self.tc.selection_set(())
        self.fc.limpar()
        self._novo_veiculo()
        self._listar_veiculos()

    def _salvar_cliente(self):
        d = self.fc.obter()
        c = executar(self.ctrl.cadastro.salvar_cliente, self.usuario, d["nome"], d["telefone"], d["cpf"], d["email"],
                     id=self.cliente_id, sucesso="Cliente salvo.")
        if c:
            self.cliente_id = c.id
            self.atualizar()

    def _inativar_cliente(self):
        if self.cliente_id and executar(self.ctrl.cadastro.alternar_ativo_cliente, self.usuario, self.cliente_id):
            self.atualizar()

    def _novo_veiculo(self):
        self.veiculo_id = None
        self.fv.limpar()

    def _salvar_veiculo(self):
        if not self.cliente_id:
            messagebox.showinfo(TITULO, "Selecione (ou salve) o cliente primeiro.")
            return
        d = self.fv.obter()
        if executar(self.ctrl.cadastro.salvar_veiculo, self.usuario, self.cliente_id, d["placa"], d["marca"],
                    d["modelo"], d["ano"], d["km"], id=self.veiculo_id, sucesso="Veículo salvo."):
            self._listar_veiculos()

    def _historico(self, titulo, lista):
        j = tk.Toplevel(self)
        j.title(titulo)
        t = criar_tabela(j, [("id", "OS", 50), ("data_abertura", "Data", 140), ("placa", "Placa", 80),
                             ("status", "Status", 130), ("problema", "Problema", 200), ("diagnostico", "Diagnóstico", 200),
                             ("total", "Valor", 100)], 12)
        t.quadro.pack(fill="both", expand=True, padx=8, pady=8)
        preencher(t, lista, {**FORMATO_OS, "total": moeda})
        if not lista:
            ttk.Label(j, text="Não há histórico.", foreground="gray").pack()
        t.bind("<Double-1>", lambda e: t.selection() and self.principal.abrir_os(int(t.selection()[0])))

    def _historico_cliente(self):
        if self.cliente_id:
            self._historico("Histórico do cliente", self.ctrl.relatorio.historico_manutencao(cliente_id=self.cliente_id))

    def _historico_veiculo(self):
        if self.veiculo_id:
            self._historico("Histórico do veículo", self.ctrl.relatorio.historico_manutencao(veiculo_id=self.veiculo_id))


class CadastroSimples(ttk.LabelFrame):
    """Lista mais formulário, usada no catálogo e nos usuários."""

    def __init__(self, pai, titulo, colunas, campos, listar, salvar, alternar=None, formatos=None):
        super().__init__(pai, text=titulo, padding=6)
        self.listar, self.salvar, self.alternar, self.formatos = listar, salvar, alternar, formatos or {}
        self.id = None
        self.tree = criar_tabela(self, colunas, 8)
        self.tree.quadro.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._selecionar)
        self.form = Formulario(self, campos)
        self.form.pack(anchor="w", pady=4)
        b = ttk.Frame(self)
        b.pack(fill="x")
        ttk.Button(b, text="Novo", command=self._novo).pack(side="left")
        ttk.Button(b, text="Salvar", command=self._salvar).pack(side="left", padx=4)
        if alternar:
            ttk.Button(b, text="Ativar/Inativar", command=self._alternar).pack(side="left")
        self.atualizar()

    def atualizar(self):
        self.objetos = {o.id: o for o in self.listar()}
        preencher(self.tree, self.objetos.values(), self.formatos)

    def _selecionar(self, _evento):
        sel = self.tree.selection()
        if sel:
            self.id = int(sel[0])
            self.form.definir(self.objetos[self.id])

    def _novo(self):
        self.id = None
        self.form.limpar()

    def _salvar(self):
        if executar(self.salvar, self.form.obter(), self.id, sucesso="Registro salvo."):
            self._novo()
            self.atualizar()

    def _alternar(self):
        if self.id and executar(self.alternar, self.id):
            self.atualizar()


class AbaCatalogo(Aba):
    """RF05, RF06 e RF07."""

    def __init__(self, pai, principal):
        super().__init__(pai, principal)
        cad, u = self.ctrl.cadastro, self.usuario
        formato = {"valor_base": moeda, "valor": moeda, "ativo": sim_nao}
        self.partes = [
            CadastroSimples(self, "Serviços", [("id", "Cód.", 40), ("descricao", "Descrição", 170),
                                               ("valor_base", "Valor base", 90), ("ativo", "Ativo", 45)],
                            [("descricao", "Descrição"), ("valor_base", "Valor base")], lambda: cad.get_servicos(),
                            lambda d, id: cad.salvar_servico(u, d["descricao"], d["valor_base"], id),
                            lambda id: cad.alternar_ativo_servico(u, id), formato),
            CadastroSimples(self, "Peças e estoque", [("id", "Cód.", 40), ("descricao", "Descrição", 150),
                                                      ("valor", "Valor", 80), ("qtd_estoque", "Estoque", 60),
                                                      ("estoque_minimo", "Mínimo", 55)],
                            [("descricao", "Descrição"), ("valor", "Valor"), ("qtd_estoque", "Qtd. em estoque"),
                             ("estoque_minimo", "Estoque mínimo")], cad.get_pecas,
                            lambda d, id: cad.salvar_peca(u, d["descricao"], d["valor"], d["qtd_estoque"],
                                                          d["estoque_minimo"], id), formatos=formato),
            CadastroSimples(self, "Fornecedores", [("id", "Cód.", 40), ("nome", "Nome", 150), ("telefone", "Telefone", 110)],
                            [("nome", "Nome"), ("telefone", "Telefone"), ("email", "E-mail")], cad.get_fornecedores,
                            lambda d, id: cad.salvar_fornecedor(u, d["nome"], d["telefone"], d["email"], id)),
        ]
        for parte in self.partes:
            parte.pack(side="left", fill="both", expand=True, padx=3)

    def atualizar(self):
        for parte in self.partes:
            parte.atualizar()


class AbaUsuarios(Aba):
    """RF02."""

    def __init__(self, pai, principal):
        super().__init__(pai, principal)
        auth, u = self.ctrl.auth, self.usuario
        ttk.Label(self, text="Na alteração, deixe a senha em branco para manter a atual.", foreground="gray").pack(anchor="w")
        self.cadastro = CadastroSimples(
            self, "Funcionários", [("id", "Cód.", 40), ("nome", "Nome", 200), ("login", "Login", 120),
                                   ("perfil", "Perfil", 100), ("ativo", "Ativo", 50)],
            [("nome", "Nome"), ("login", "Login"), ("perfil", "Perfil", Perfil.TODOS), ("senha", "Senha")],
            auth.get_usuarios, lambda d, id: auth.salvar_usuario(u, d["nome"], d["login"], d["perfil"], d.get("senha"), id),
            lambda id: auth.alternar_ativo(u, id), {"ativo": sim_nao})
        self.cadastro.pack(fill="both", expand=True)

    def atualizar(self):
        self.cadastro.atualizar()


class AbaCompras(Aba):
    """RF23: solicitações de compra."""

    def __init__(self, pai, principal):
        super().__init__(pai, principal)
        self.tree = criar_tabela(self, [("id", "Nº", 50), ("os_id", "OS", 50), ("peca_descricao", "Peça", 200),
                                        ("quantidade", "Qtd.", 50), ("situacao", "Situação", 100),
                                        ("fornecedor_nome", "Fornecedor", 200)], 15)
        self.tree.quadro.pack(fill="both", expand=True)
        b = ttk.Frame(self)
        b.pack(fill="x", pady=6)
        ttk.Button(b, text="Registrar compra", command=self.comprar).pack(side="left")
        ttk.Button(b, text="Registrar recebimento", command=self.receber).pack(side="left", padx=6)
        ttk.Button(b, text="Cancelar solicitação", command=self.cancelar).pack(side="left")
        ttk.Button(b, text="Atualizar", command=self.atualizar).pack(side="right")
        self.atualizar()

    def atualizar(self):
        preencher(self.tree, self.ctrl.compras.get_solicitacoes(), {"situacao": lambda s: s.capitalize()})

    def comprar(self):
        sol = selecionado(self.tree)
        if not sol:
            return
        fornecedores = [opcao(f.id, f.nome) for f in self.ctrl.cadastro.get_fornecedores()]
        r = pedir(self, "Registrar compra", [("f", "Fornecedor", fornecedores)])
        if r and executar(self.ctrl.compras.registrar_compra, self.usuario, sol, id_da_opcao(r["f"]),
                          sucesso="Compra registrada."):
            self.atualizar()

    def receber(self):
        sol = selecionado(self.tree)
        if sol and executar(self.ctrl.compras.registrar_recebimento, self.usuario, sol,
                            sucesso="Recebimento registrado; estoque atualizado."):
            self.atualizar()

    def cancelar(self):
        sol = selecionado(self.tree)
        if sol and messagebox.askyesno(TITULO, "Cancelar esta solicitação de compra?") and \
                executar(self.ctrl.compras.cancelar_solicitacao, self.usuario, sol, sucesso="Solicitação cancelada."):
            self.atualizar()


class AbaRelatorios(Aba):
    """RF34."""

    def __init__(self, pai, principal):
        super().__init__(pai, principal)
        f = ttk.Frame(self)
        f.pack(fill="x")
        ttk.Label(f, text="Período de (AAAA-MM-DD):").pack(side="left")
        self.de, self.ate = ttk.Entry(f, width=11), ttk.Entry(f, width=11)
        self.de.pack(side="left", padx=4)
        ttk.Label(f, text="até:").pack(side="left")
        self.ate.pack(side="left", padx=4)
        ttk.Button(f, text="Gerar relatório", command=self.atualizar).pack(side="left", padx=8)
        ttk.Button(f, text="Exportar PDF", command=self.exportar).pack(side="left")
        self.texto = tk.Text(self, width=90, height=24, font=("Consolas", 11))
        self.texto.pack(fill="both", expand=True, pady=8)
        self.relatorio = None
        self.atualizar()

    def atualizar(self):
        r = executar(self.ctrl.relatorio.gerar, self.usuario, self.de.get().strip(), self.ate.get().strip())
        if r:
            self.relatorio = r
            self.texto.delete("1.0", "end")
            self.texto.insert("1.0", "\n".join(self.ctrl.relatorio.linhas(r)))

    def exportar(self):
        if not self.relatorio:
            return
        caminho = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                               initialfile="relatorio_gerencial.pdf")
        if caminho and executar(self.ctrl.relatorio.exportar_pdf, self.usuario, self.relatorio, caminho):
            messagebox.showinfo(TITULO, f"Relatório salvo em:\n{caminho}")

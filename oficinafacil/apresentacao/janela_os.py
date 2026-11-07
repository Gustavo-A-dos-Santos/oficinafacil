"""Janela da OS: detalhes e as ações permitidas para o perfil e o status atuais."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..controle.pagamento_controller import PagamentoController
from ..modelo import data_br, moeda
from ..modelo.atendimento import StatusOS
from ..modelo.cadastro import Perfil
from .componentes import (TITULO, DialogoItens, criar_tabela, executar, id_da_opcao, opcao, pedir, preencher,
                          salvar_e_abrir_pdf, selecionado)

S = StatusOS
DESTINACOES = ["Devolvido ao cliente", "Reciclagem (sucata metálica)", "Coleta de óleo usado (rerrefino)",
               "Logística reversa (bateria/pneu)", "Descarte em empresa licenciada"]


class JanelaOS(tk.Toplevel):

    def __init__(self, principal, os_id):
        super().__init__(principal)
        self.principal, self.ctrl, self.usuario, self.os_id = principal, principal.ctrl, principal.usuario, os_id
        self.title(f"OS nº {os_id}")
        self.geometry("980x640")
        self.cabecalho = ttk.Label(self, padding=10, justify="left")
        self.cabecalho.pack(fill="x")
        self.botoes = ttk.Frame(self, padding=(10, 0))
        self.botoes.pack(fill="x")
        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True, padx=10, pady=10)
        f1, f2, f3 = (ttk.Frame(abas, padding=6) for _ in range(3))
        abas.add(f1, text="Serviços e peças")
        abas.add(f2, text="Orçamentos e pagamentos")
        abas.add(f3, text="Histórico de status")
        self.t_serv = criar_tabela(f1, [("id", "Item", 50), ("descricao", "Serviço", 300), ("quantidade", "Qtd.", 50),
                                        ("valor", "Valor unit.", 100)], 5)
        self.t_serv.quadro.pack(fill="both", expand=True)
        self.t_peca = criar_tabela(f1, [("id", "Item", 50), ("descricao", "Peça", 250), ("quantidade", "Qtd.", 50),
                                        ("valor", "Valor unit.", 100), ("destinacao_residuo", "Destinação do resíduo", 250)], 5)
        self.t_peca.quadro.pack(fill="both", expand=True, pady=(8, 0))
        self.t_orc = criar_tabela(f2, [("id", "Nº", 40), ("versao", "Versão", 60), ("valor_total", "Total", 100),
                                       ("situacao", "Situação", 160), ("gerente_nome", "Aprovado por", 140),
                                       ("data", "Data", 140), ("data_hora_decisao_cliente", "Decisão do cliente", 150)], 5)
        self.t_orc.quadro.pack(fill="both", expand=True)
        self.t_pag = criar_tabela(f2, [("id", "Nº", 40), ("valor", "Valor", 100), ("forma_pagamento", "Forma", 140),
                                       ("data", "Data", 150)], 4)
        self.t_pag.quadro.pack(fill="both", expand=True, pady=(8, 0))
        self.t_hist = criar_tabela(f3, [("id", "Nº", 40), ("status", "Status", 160), ("usuario_nome", "Alterado por", 180),
                                        ("data_hora", "Data e hora", 160)], 12)
        self.t_hist.quadro.pack(fill="both", expand=True)
        self.atualizar()

    def atualizar(self):
        self.os = o = self.ctrl.os.get_os(self.os_id)
        servicos, pecas = self.ctrl.os.get_itens(self.os_id)
        self.diag = diag = self.ctrl.os.get_diagnostico(self.os_id)
        texto = (f"Status: {o.nome_status()}        Aberta em {data_br(o.data_abertura, True)} por {o.aberta_por}\n"
                 f"Cliente: {o.cliente_nome} ({o.cliente_telefone})        Veículo: {o.marca} {o.modelo} - "
                 f"placa {o.placa} - km {o.km_entrada}\n"
                 f"Problema relatado: {o.problema}\n"
                 f"Mecânico responsável: {o.mecanico_nome or '-'}        Diagnóstico: {diag.descricao if diag else '-'}\n"
                 f"Total da OS: {moeda(self.ctrl.os.calcular_total(self.os_id))}        "
                 f"Pago: {moeda(self.ctrl.pagamento.get_total_pago(self.os_id))}")
        for rotulo, valor in (("Execução registrada em", data_br(o.data_execucao, True)),
                              ("Concluída em", data_br(o.data_conclusao, True)),
                              ("Cliente avisado em", data_br(o.data_aviso_cliente, True)),
                              ("Motivo do cancelamento", o.motivo_cancelamento)):
            if valor:
                texto += f"\n{rotulo}: {valor}"
        if o.status == S.EM_DIAGNOSTICO and diag:
            texto += "\nOrçamento em preparação: revise os itens e use Enviar orçamento ao gerente."
        self.cabecalho.config(text=texto)
        formato = {"valor": moeda, "valor_total": moeda}
        preencher(self.t_serv, servicos, formato)
        preencher(self.t_peca, pecas, formato)
        preencher(self.t_orc, self.ctrl.orcamento.get_versoes(self.os_id),
                  {"valor_total": moeda, "situacao": lambda s: s.replace("_", " ").capitalize()})
        preencher(self.t_pag, self.ctrl.pagamento.get_pagamentos(self.os_id), formato)
        preencher(self.t_hist, self.ctrl.os.get_historico_status(self.os_id), {"status": lambda s: S.NOMES[s]})
        self._montar_botoes()

    def _botao(self, texto, comando):
        ttk.Button(self.botoes, text=texto, command=comando).pack(side="left", padx=3, pady=2)

    def _montar_botoes(self):
        for w in self.botoes.winfo_children():
            w.destroy()
        s, p = self.os.status, self.usuario.perfil
        if s == S.ABERTA and p in (Perfil.ATENDENTE, Perfil.MECANICO):
            self._botao("Classificar atendimento", self.classificar)
        if p == Perfil.MECANICO:
            if s == S.EM_DIAGNOSTICO and not self.diag:
                self._botao("Registrar diagnóstico", self.diagnosticar)
            if s == S.EM_DIAGNOSTICO and self.diag:  # orçamento em preparação: revisar e enviar
                self._botao("Adicionar itens", self.adicionar_itens)
                self._botao("Remover item", self.remover_item)
                self._botao("Enviar orçamento ao gerente", self.enviar_orcamento)
            if s == S.EM_EXECUCAO:
                if not self.os.data_execucao:
                    self._botao("Registrar execução", self.registrar_execucao)
                self._botao("Destinação de resíduo", self.destinacao)
                self._botao("Concluir serviço", self.concluir)
            if s in (S.EM_DIAGNOSTICO, S.EM_EXECUCAO, S.AGUARDANDO_PECAS):
                self._botao("Solicitar compra de peça", self.solicitar)
        if p == Perfil.GERENTE and s == S.AGUARDANDO_GERENTE:
            self._botao("Alterar valor de item", self.alterar_valor)
            self._botao("Aprovar orçamento", self.aprovar)
        if p == Perfil.ATENDENTE:
            if s != S.CANCELADA and self.ctrl.orcamento.get_atual(self.os_id) and s not in (S.AGUARDANDO_GERENTE,):
                self._botao("Exportar orçamento (PDF)", self.exportar)
            if s == S.AGUARDANDO_CLIENTE:
                self._botao("Registrar decisão do cliente", self.decisao)
            if s == S.CONCLUIDA:
                self._botao("Avisar cliente", self.avisar)
                self._botao("Registrar pagamento", self.pagamento)
                self._botao("Entregar veículo e encerrar", self.entregar)
        ttk.Button(self.botoes, text="Fechar", command=self.destroy).pack(side="right")

    def _feito(self, mensagem=None):
        if mensagem:
            messagebox.showinfo(TITULO, mensagem, parent=self)
        self.atualizar()
        self.principal.atualizar_aba_atual()

    def _executar(self, func, *args, **kwargs):
        return executar(func, *args, parent=self, **kwargs)

    # ---------------------------------------------------------------- ações
    def classificar(self):
        mecanicos = [opcao(m.id, m.nome) for m in self.ctrl.auth.get_usuarios(Perfil.MECANICO, True)]
        valores = {"m": opcao(self.usuario.id, self.usuario.nome)} if self.usuario.perfil == Perfil.MECANICO else {}
        r = pedir(self, "Classificar atendimento",
                  [("tipo", "Tipo de atendimento", ["Avaliação completa (com orçamento)", "Serviço simples (sem orçamento)"]),
                   ("m", "Mecânico responsável", mecanicos)], valores)
        if not r:
            return
        if not r["tipo"]:
            messagebox.showwarning(TITULO, "Escolha o tipo de atendimento.", parent=self)
            return
        if self._executar(self.ctrl.os.classificar, self.usuario, self.os_id, r["tipo"].startswith("Serviço simples"),
                          id_da_opcao(r["m"])):
            self._feito()

    def diagnosticar(self):
        r = DialogoItens(self, self.ctrl.cadastro, "Registrar diagnóstico", True).mostrar()
        if r and self._executar(self.ctrl.os.registrar_diagnostico, self.usuario, self.os_id, *r):
            self._feito("Diagnóstico registrado. Revise os itens e, quando estiver pronto, clique em "
                        "Enviar orçamento ao gerente.")

    def adicionar_itens(self):
        r = DialogoItens(self, self.ctrl.cadastro, "Adicionar itens ao orçamento", False).mostrar()
        if r and self._executar(self.ctrl.os.adicionar_itens, self.usuario, self.os_id, r[1], r[2]):
            self._feito()

    def remover_item(self):
        tipo, tree = ("servico", self.t_serv) if self.t_serv.selection() else ("peca", self.t_peca)
        item = selecionado(tree, "Selecione o serviço ou a peça na aba Serviços e peças.")
        if item and messagebox.askyesno(TITULO, "Remover o item selecionado do orçamento?", parent=self) and \
                self._executar(self.ctrl.os.remover_item, self.usuario, self.os_id, tipo, item):
            self._feito()

    def enviar_orcamento(self):
        total = moeda(self.ctrl.os.calcular_total(self.os_id))
        if messagebox.askyesno(TITULO, f"Enviar o orçamento de {total} ao gerente?\n\nDepois do envio, os itens só "
                                       "mudam pelo gerente.", parent=self) and \
                self._executar(self.ctrl.os.enviar_orcamento, self.usuario, self.os_id):
            self._feito("Orçamento enviado. O gerente foi avisado no painel.")

    def registrar_execucao(self):
        tem_orcamento = self.ctrl.orcamento.get_atual(self.os_id) is not None
        aviso = ("Confirme os serviços e peças do orçamento aprovado (não adicione itens: eles exigiriam nova aprovação)."
                 if tem_orcamento else "Informe os serviços realizados e as peças usadas.")
        r = DialogoItens(self, self.ctrl.cadastro, "Registrar execução", False, aviso).mostrar()
        if r and self._executar(self.ctrl.os.registrar_execucao, self.usuario, self.os_id, r[1], r[2]):
            self._feito("Execução registrada; o estoque das peças foi baixado.")

    def destinacao(self):
        item = selecionado(self.t_peca, "Selecione a peça na aba Serviços e peças.")
        if not item:
            return
        r = pedir(self, "Destinação do resíduo", [("d", "Destinação", DESTINACOES)])
        if r and self._executar(self.ctrl.compras.registrar_destinacao, self.usuario, item, r["d"]):
            self._feito()

    def concluir(self):
        if messagebox.askyesno(TITULO, "Confirmar a conclusão do serviço?", parent=self) and \
                self._executar(self.ctrl.os.concluir_servico, self.usuario, self.os_id):
            self._feito("Serviço concluído. O atendente foi avisado no painel.")

    def solicitar(self):
        pecas = [opcao(p.id, p.descricao) for p in self.ctrl.cadastro.get_pecas()]
        r = pedir(self, "Solicitar compra de peça", [("p", "Peça", pecas), ("q", "Quantidade")], {"q": "1"})
        if r and self._executar(self.ctrl.compras.solicitar_compra, self.usuario, self.os_id, id_da_opcao(r["p"]), r["q"]):
            self._feito("Solicitação de compra registrada.")

    def alterar_valor(self):
        tipo, tree = ("servico", self.t_serv) if self.t_serv.selection() else ("peca", self.t_peca)
        item = selecionado(tree, "Selecione o item (serviço ou peça) na aba Serviços e peças.")
        if not item:
            return
        r = pedir(self, "Alterar valor", [("v", "Novo valor unitário")])
        if r and self._executar(self.ctrl.orcamento.alterar_valor_item, self.usuario, self.os_id, tipo, item, r["v"]):
            self._feito("Nova versão do orçamento criada. Ela precisa ser aprovada.")

    def aprovar(self):
        if self._executar(self.ctrl.orcamento.aprovar, self.usuario, self.os_id):
            self._feito("Orçamento aprovado e disponível ao atendente.")

    def exportar(self):
        salvar_e_abrir_pdf(self, f"orcamento_OS{self.os_id}.pdf",
                           lambda caminho: self.ctrl.orcamento.exportar_pdf(self.os_id, caminho))

    def decisao(self):
        r = pedir(self, "Decisão do cliente", [("d", "O cliente", ["Aprovou o orçamento", "Rejeitou o orçamento"]),
                                               ("motivo", "Motivo (se rejeitou)")])
        if not r or not r["d"]:
            return
        novo = self._executar(self.ctrl.orcamento.registrar_decisao_cliente, self.usuario, self.os_id,
                              r["d"].startswith("Aprovou"), r["motivo"])
        if novo:
            self._feito({S.CANCELADA: "OS cancelada por rejeição do orçamento.",
                         S.AGUARDANDO_PECAS: "Execução autorizada, mas faltam peças: a solicitação de compra foi "
                                             "enviada ao gerente.",
                         S.EM_EXECUCAO: "Execução autorizada. O mecânico foi avisado no painel."}[novo])

    def avisar(self):
        texto = self._executar(self.ctrl.os.gerar_mensagem, self.os_id)
        if not texto:
            return
        self.clipboard_clear()
        self.clipboard_append(texto)
        if messagebox.askyesno(TITULO, texto + "\n\nA mensagem foi copiada; cole no WhatsApp ou SMS.\n"
                                               "Confirmar que o cliente foi avisado?", parent=self) and \
                self._executar(self.ctrl.os.registrar_aviso_cliente, self.usuario, self.os_id):
            self._feito()

    def pagamento(self):
        falta = self.ctrl.os.calcular_total(self.os_id) - self.ctrl.pagamento.get_total_pago(self.os_id)
        r = pedir(self, "Registrar pagamento", [("v", "Valor"), ("f", "Forma de pagamento", PagamentoController.FORMAS)],
                  {"v": f"{max(falta, 0):.2f}".replace(".", ",")})
        if r and self._executar(self.ctrl.pagamento.registrar_pagamento, self.usuario, self.os_id, r["v"], r["f"]):
            self._feito("Pagamento registrado.")

    def entregar(self):
        if self._executar(self.ctrl.pagamento.entregar_veiculo, self.usuario, self.os_id):
            self._feito("Veículo entregue. OS encerrada.")

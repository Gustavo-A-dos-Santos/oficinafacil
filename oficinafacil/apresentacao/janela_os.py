"""Janela da OS: detalhes, valores e as ações permitidas para o perfil e a etapa atuais."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QListWidget, QScrollArea, QTabWidget,
                               QVBoxLayout, QWidget)

from ..modelo import data_br, moeda
from ..modelo.atendimento import FORMAS_PAGAMENTO, StatusOS as S
from ..modelo.cadastro import Perfil
from .componentes import (Botao, Busca, Campo, Cartao, Dialogo, Selo, Tabela, area_texto, barra_progresso,
                          confirmar, definir_opcoes, executar, janela_historico, notificar, numero_valido, pedir,
                          quantidade, rotulo, salvar_e_abrir_pdf, selecao)
from .tema import ESPACO, Tema, icone

DESTINACOES = ["Devolvido ao cliente", "Reciclagem (sucata metálica)", "Coleta de óleo usado (rerrefino)",
               "Logística reversa (bateria/pneu)", "Descarte em empresa licenciada"]


class JanelaOS(QWidget):

    def __init__(self, principal, os_id):
        super().__init__(principal, Qt.Window)
        self.principal, self.ctrl, self.usuario, self.os_id = principal, principal.ctrl, principal.usuario, os_id
        self.setObjectName("Pagina")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(f"OS nº {os_id} · OficinaFácil")
        self.setMinimumSize(920, 640)
        self.resize(1080, 760)
        externo = QVBoxLayout(self)
        externo.setContentsMargins(0, 0, 0, 0)
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setFrameShape(QFrame.NoFrame)
        conteudo = QWidget()
        conteudo.setObjectName("Pagina")
        rolagem.setWidget(conteudo)
        externo.addWidget(rolagem)
        raiz = QVBoxLayout(conteudo)
        raiz.setContentsMargins(ESPACO["l"], ESPACO["m"], ESPACO["l"], ESPACO["l"])
        raiz.setSpacing(ESPACO["m"])
        # cabeçalho: trilha, título, selo e histórico
        raiz.addWidget(rotulo("Ordens de serviço  ›  Detalhes da OS", "breadcrumb"))
        topo = QHBoxLayout()
        topo.setSpacing(ESPACO["s"])
        topo.addWidget(rotulo(f"OS nº {os_id}", "titulo"))
        self.selo = Selo("", "#000", "#fff")
        topo.addWidget(self.selo)
        topo.addStretch(1)
        topo.addWidget(Botao("Histórico do veículo", "fantasma", "history", "Ver as OS anteriores deste veículo",
                             self.historico_veiculo))
        topo.addWidget(Botao("Fechar", "secundario", "x", "Fechar a janela (Esc)", self.close))
        raiz.addLayout(topo)
        # informações e valores
        meio = QHBoxLayout()
        meio.setSpacing(ESPACO["m"])
        info = Cartao("Atendimento", nivel=1)
        self.grade = QGridLayout()
        self.grade.setHorizontalSpacing(ESPACO["l"])
        self.grade.setVerticalSpacing(ESPACO["xs"])
        info.lay.addLayout(self.grade)
        meio.addWidget(info, 3)
        valores = Cartao("Valores", nivel=1)
        self.total = rotulo("", "kpi_valor")
        from .tema import fonte
        self.total.setFont(fonte("titulo", "seminegrito", tabular=True))
        valores.lay.addWidget(rotulo("Total da OS", "legenda"))
        valores.lay.addWidget(self.total)
        self.progresso = barra_progresso()
        valores.lay.addWidget(self.progresso)
        self.pago = rotulo("", "legenda")
        valores.lay.addWidget(self.pago)
        valores.lay.addStretch(1)
        meio.addWidget(valores, 1)
        raiz.addLayout(meio)
        # ações
        self.barra = Cartao(nivel=1, margem=ESPACO["s"])
        self.botoes = QHBoxLayout()
        self.botoes.setSpacing(ESPACO["xs"])
        self.barra.lay.addLayout(self.botoes)
        raiz.addWidget(self.barra)
        # abas
        abas = QTabWidget()
        f1, f2, f3 = QWidget(), QWidget(), QWidget()
        for f in (f1, f2, f3):
            f.setObjectName("Pagina")
        abas.addTab(f1, icone("wrench", Tema.cor("texto_2"), 16), "Serviços e peças")
        abas.addTab(f2, icone("banknote", Tema.cor("texto_2"), 16), "Orçamentos e pagamentos")
        abas.addTab(f3, icone("history", Tema.cor("texto_2"), 16), "Histórico de status")
        l1, l2, l3 = (QVBoxLayout(f) for f in (f1, f2, f3))
        for l in (l1, l2, l3):
            l.setContentsMargins(0, ESPACO["s"], 0, 0)
            l.setSpacing(ESPACO["s"])
        cs, cp = Cartao("Serviços", nivel=0, margem=ESPACO["s"]), Cartao("Peças", nivel=0, margem=ESPACO["s"])
        self.t_serv = Tabela([{"chave": "id", "titulo": "Item", "largura": 64, "numero": True},
                              {"chave": "descricao", "titulo": "Serviço", "largura": 360},
                              {"chave": "quantidade", "titulo": "Qtd.", "largura": 64, "numero": True},
                              {"chave": "valor", "titulo": "Valor unit.", "largura": 120, "numero": True, "formato": moeda}],
                             ("wrench", "Nenhum serviço", "Os serviços entram no diagnóstico ou na execução."))
        self.t_peca = Tabela([{"chave": "id", "titulo": "Item", "largura": 64, "numero": True},
                              {"chave": "descricao", "titulo": "Peça", "largura": 260},
                              {"chave": "quantidade", "titulo": "Qtd.", "largura": 64, "numero": True},
                              {"chave": "valor", "titulo": "Valor unit.", "largura": 120, "numero": True, "formato": moeda},
                              {"chave": "destinacao_residuo", "titulo": "Destinação do resíduo", "largura": 230}],
                             ("package", "Nenhuma peça", "As peças entram no diagnóstico ou na execução."))
        for t in (self.t_serv, self.t_peca):
            t.setMinimumHeight(190)
        self.t_serv.selecionou.connect(lambda i: i and self.t_peca.limpar_selecao())
        self.t_peca.selecionou.connect(lambda i: i and self.t_serv.limpar_selecao())
        cs.lay.addWidget(self.t_serv)
        cp.lay.addWidget(self.t_peca)
        l1.addWidget(cs)
        l1.addWidget(cp)
        co, cg = Cartao("Versões do orçamento", nivel=0, margem=ESPACO["s"]), Cartao("Pagamentos", nivel=0,
                                                                                   margem=ESPACO["s"])
        self.t_orc = Tabela([{"chave": "versao", "titulo": "Versão", "largura": 80, "numero": True},
                             {"chave": "valor_total", "titulo": "Total", "largura": 130, "numero": True, "formato": moeda},
                             {"chave": "situacao", "titulo": "Situação", "largura": 200,
                              "formato": lambda s: s.replace("_", " ").capitalize()},
                             {"chave": "data", "titulo": "Data", "largura": 150, "formato": lambda d: data_br(d, True)}],
                            ("file-text", "Sem orçamento", "Serviços simples não têm orçamento; nos demais, ele é "
                                                           "gerado quando o mecânico o envia ao gerente."))
        self.t_pag = Tabela([{"chave": "id", "titulo": "Nº", "largura": 64, "numero": True},
                             {"chave": "valor", "titulo": "Valor", "largura": 130, "numero": True, "formato": moeda},
                             {"chave": "forma_pagamento", "titulo": "Forma", "largura": 180},
                             {"chave": "data", "titulo": "Data", "largura": 150, "formato": lambda d: data_br(d, True)}],
                            ("banknote", "Nenhum pagamento", "O pagamento é registrado pelo atendente na entrega."))
        for t in (self.t_orc, self.t_pag):
            t.setMinimumHeight(190)
        co.lay.addWidget(self.t_orc)
        cg.lay.addWidget(self.t_pag)
        l2.addWidget(co)
        l2.addWidget(cg)
        ch = Cartao("Quem mudou cada etapa e quando", nivel=0, margem=ESPACO["s"])
        self.t_hist = Tabela([{"chave": "status", "titulo": "Etapa", "largura": 210, "status": True,
                               "formato": lambda s: S.NOMES.get(s, s)},
                              {"chave": "usuario_nome", "titulo": "Alterado por", "largura": 200},
                              {"chave": "data_hora", "titulo": "Data e hora", "largura": 180,
                               "formato": lambda d: data_br(d, True)}],
                             ("history", "Sem histórico", ""))
        self.t_hist.setMinimumHeight(320)
        ch.lay.addWidget(self.t_hist)
        l3.addWidget(ch)
        raiz.addWidget(abas, 1)
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        self.atualizar()

    # ---------------------------------------------------------------- dados
    def _info(self, linha, col, titulo, valor):
        self.grade.addWidget(rotulo(titulo, "legenda"), linha * 2, col)
        v = rotulo(valor or "—", "valor", True)
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.grade.addWidget(v, linha * 2 + 1, col)

    def atualizar(self):
        self.os = o = self.ctrl.os.get_os(self.os_id)
        servicos, pecas = self.ctrl.os.get_itens(self.os_id)
        self.diag = diag = self.ctrl.os.get_diagnostico(self.os_id)
        fg, bg = Tema.status(o.status)
        self.selo.setText(o.nome_status())
        self.selo.pintar(fg, bg)
        while self.grade.count():
            w = self.grade.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._info(0, 0, "Cliente", f"{o.cliente_nome} · {o.cliente_telefone}")
        self._info(0, 1, "Veículo", f"{o.marca} {o.modelo} · placa {o.placa} · {o.km_entrada} km")
        self._info(1, 0, "Problema relatado", o.problema)
        self._info(1, 1, "Diagnóstico", diag.descricao if diag else None)
        self._info(2, 0, "Mecânico responsável", o.mecanico_nome)
        self._info(2, 1, "Aberta em", f"{data_br(o.data_abertura, True)} por {o.aberta_por}")
        extras = [(t, data_br(v, True) if t != "Motivo do cancelamento" else v)
                  for t, v in (("Execução registrada em", o.data_execucao), ("Concluída em", o.data_conclusao),
                               ("Cliente avisado em", o.data_aviso_cliente), ("Motivo do cancelamento",
                                                                              o.motivo_cancelamento)) if v]
        for i, (t, v) in enumerate(extras):
            self._info(3 + i // 2, i % 2, t, v)
        if o.status == S.EM_DIAGNOSTICO and diag:
            aviso = rotulo("Orçamento em preparação: revise os itens e use Enviar orçamento ao gerente.", "alerta", True)
            self.grade.addWidget(aviso, 20, 0, 1, 2)
        total, pago = self.ctrl.os.calcular_total(self.os_id), self.ctrl.pagamento.get_total_pago(self.os_id)
        self.total.setText(moeda(total))
        self.progresso.setValue(int(min(pago / total, 1) * 100) if total else 0)
        self.pago.setText(f"Pago: {moeda(pago)}" + (f"  ·  Falta: {moeda(total - pago)}" if total - pago > 0.004 else ""))
        self.t_serv.preencher(servicos)
        self.t_peca.preencher(pecas)
        self.t_orc.preencher(self.ctrl.orcamento.get_versoes(self.os_id))
        self.t_pag.preencher(self.ctrl.pagamento.get_pagamentos(self.os_id))
        self.t_hist.preencher(self.ctrl.os.get_historico_status(self.os_id))
        self._montar_botoes()

    def _botao(self, texto, comando, variante="secundario", ic=None, dica=None):
        self.botoes.addWidget(Botao(texto, variante, ic, dica or texto, comando))

    def _montar_botoes(self):
        while self.botoes.count():
            item = self.botoes.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        s, p = self.os.status, self.usuario.perfil
        if s == S.ABERTA and p in (Perfil.ATENDENTE, Perfil.MECANICO):
            self._botao("Classificar atendimento", self.classificar, "primario", "clipboard-check")
        if p == Perfil.MECANICO:
            if s == S.EM_DIAGNOSTICO and not self.diag:
                self._botao("Registrar diagnóstico", self.diagnosticar, "primario", "pencil")
            if s == S.EM_DIAGNOSTICO and self.diag:
                self._botao("Enviar orçamento ao gerente", self.enviar_orcamento, "primario", "send")
                self._botao("Adicionar itens", self.adicionar_itens, ic="plus")
                self._botao("Remover item", self.remover_item, "perigo", "trash-2")
            if s == S.EM_EXECUCAO:
                if not self.os.data_execucao:
                    self._botao("Registrar execução", self.registrar_execucao, "primario", "hammer")
                self._botao("Concluir serviço", self.concluir, "primario" if self.os.data_execucao else "secundario",
                            "circle-check")
                self._botao("Destinação de resíduo", self.destinacao, ic="recycle")
            if s in (S.EM_DIAGNOSTICO, S.EM_EXECUCAO, S.AGUARDANDO_PECAS):
                self._botao("Solicitar compra de peça", self.solicitar, ic="shopping-cart")
        if p == Perfil.GERENTE and s == S.AGUARDANDO_GERENTE:
            self._botao("Aprovar orçamento", self.aprovar, "primario", "check")
            self._botao("Alterar valor de item", self.alterar_valor, ic="pencil")
        if p == Perfil.ATENDENTE:
            if s == S.AGUARDANDO_CLIENTE:
                self._botao("Registrar decisão do cliente", self.decisao, "primario", "message-square")
            if s == S.CONCLUIDA:
                self._botao("Avisar cliente", self.avisar, "primario" if not self.os.data_aviso_cliente else "secundario",
                            "message-square")
                self._botao("Registrar pagamento", self.pagamento, ic="banknote")
                self._botao("Entregar veículo e encerrar", self.entregar, "primario" if self.os.data_aviso_cliente
                            else "secundario", "car")
            if s != S.CANCELADA and s != S.AGUARDANDO_GERENTE and self.ctrl.orcamento.get_atual(self.os_id):
                self._botao("Exportar orçamento (PDF)", self.exportar, "fantasma", "file-down")
        if not self.botoes.count():
            self.botoes.addWidget(rotulo("Nenhuma ação disponível para o seu perfil nesta etapa.", "subtitulo"))
        self.botoes.addStretch(1)

    def historico_veiculo(self):
        janela_historico(self, f"Histórico do veículo {self.os.placa or ''}",
                         self.ctrl.relatorio.historico_manutencao(veiculo_id=self.os.veiculo_id), self.principal.abrir_os)

    def _feito(self, mensagem=None):
        if mensagem:
            notificar(self, mensagem)
        self.atualizar()
        self.principal.atualizar_aba_atual()

    def _executar(self, func, *args, **kwargs):
        return executar(func, *args, pai=self, **kwargs)

    def _item_selecionado(self, aviso):
        if self.t_serv.id_selecionado():
            return "servico", self.t_serv.id_selecionado()
        if self.t_peca.id_selecionado():
            return "peca", self.t_peca.id_selecionado()
        notificar(self, aviso, "info")
        return None, None

    # ---------------------------------------------------------------- ações
    def classificar(self):
        mecanicos = [(m.id, m.nome) for m in self.ctrl.auth.get_usuarios(Perfil.MECANICO, True)]
        valores = {"m": self.usuario.id} if self.usuario.perfil == Perfil.MECANICO else {}
        r = pedir(self, "Classificar atendimento",
                  [("tipo", "Tipo de atendimento", [("completa", "Avaliação completa (com orçamento)"),
                                                    ("simples", "Serviço simples (sem orçamento)")]),
                   ("m", "Mecânico responsável", mecanicos)], valores,
                  "Serviço simples, como troca de óleo, vai direto para a execução.", "Classificar")
        if r and self._executar(self.ctrl.os.classificar, self.usuario, self.os_id, r["tipo"] == "simples", r["m"]):
            self._feito("Atendimento classificado.")

    def diagnosticar(self):
        r = DialogoItens(self, self.ctrl.cadastro, "Registrar diagnóstico", True).mostrar()
        if r and self._executar(self.ctrl.os.registrar_diagnostico, self.usuario, self.os_id, *r):
            self._feito("Diagnóstico registrado. Revise os itens e envie o orçamento ao gerente.")

    def adicionar_itens(self):
        r = DialogoItens(self, self.ctrl.cadastro, "Adicionar itens ao orçamento", False).mostrar()
        if r and self._executar(self.ctrl.os.adicionar_itens, self.usuario, self.os_id, r[1], r[2]):
            self._feito("Itens adicionados.")

    def remover_item(self):
        tipo, item = self._item_selecionado("Selecione o serviço ou a peça na aba Serviços e peças.")
        if item and confirmar(self, "Remover item", "O item selecionado sai do orçamento em preparação. Continuar?",
                              "Remover", perigo=True) and \
                self._executar(self.ctrl.os.remover_item, self.usuario, self.os_id, tipo, item):
            self._feito("Item removido.")

    def enviar_orcamento(self):
        total = moeda(self.ctrl.os.calcular_total(self.os_id))
        if confirmar(self, "Enviar orçamento ao gerente", f"O orçamento de {total} vai para a aprovação do gerente. "
                                                         "Depois do envio, os itens só mudam pelo gerente.",
                     "Enviar orçamento") and self._executar(self.ctrl.os.enviar_orcamento, self.usuario, self.os_id):
            self._feito("Orçamento enviado. O gerente foi avisado no painel.")

    def registrar_execucao(self):
        tem_orcamento = self.ctrl.orcamento.get_atual(self.os_id) is not None
        aviso = ("Confirme os serviços e peças do orçamento aprovado. Não adicione itens: eles exigiriam nova "
                 "aprovação." if tem_orcamento else "Informe os serviços realizados e as peças usadas.")
        r = DialogoItens(self, self.ctrl.cadastro, "Registrar execução", False, aviso).mostrar()
        if r and self._executar(self.ctrl.os.registrar_execucao, self.usuario, self.os_id, r[1], r[2]):
            self._feito("Execução registrada; o estoque das peças foi baixado.")

    def destinacao(self):
        item = self.t_peca.selecionado("Selecione a peça na aba Serviços e peças.")
        if not item:
            return
        r = pedir(self, "Destinação do resíduo", [("d", "Destinação", DESTINACOES)],
                  subtitulo="Para onde vai a peça trocada (apoio ao ODS 12).", texto_ok="Registrar")
        if r and self._executar(self.ctrl.compras.registrar_destinacao, self.usuario, item, r["d"]):
            self._feito("Destinação registrada.")

    def concluir(self):
        if confirmar(self, "Concluir serviço", "Confirmar a conclusão? O atendente será avisado no painel.",
                     "Concluir serviço") and self._executar(self.ctrl.os.concluir_servico, self.usuario, self.os_id):
            self._feito("Serviço concluído. O atendente foi avisado no painel.")

    def solicitar(self):
        from .dialogo_compra import DialogoSolicitacao
        r = DialogoSolicitacao(self, self.ctrl, self.usuario, os_id=self.os_id, os_fixa=True).mostrar()
        if r and self._executar(self.ctrl.compras.solicitar_compra, self.usuario, self.os_id, r["peca"], r["qtd"],
                                r["obs"]):
            self._feito("Solicitação de compra registrada. O gerente vê o pedido na página Compras.")

    def alterar_valor(self):
        tipo, item = self._item_selecionado("Selecione o item (serviço ou peça) na aba Serviços e peças.")
        if not item:
            return
        r = pedir(self, "Alterar valor do item", [{"chave": "v", "rotulo": "Novo valor unitário", "validar": numero_valido,
                                                   "unidade": "R$"}],
                  subtitulo="Uma nova versão do orçamento é criada e precisa ser aprovada.", texto_ok="Alterar valor")
        if r and self._executar(self.ctrl.orcamento.alterar_valor_item, self.usuario, self.os_id, tipo, item, r["v"]):
            self._feito("Nova versão do orçamento criada. Ela precisa ser aprovada.")

    def aprovar(self):
        if confirmar(self, "Aprovar orçamento", f"Aprovar o orçamento de {moeda(self.ctrl.os.calcular_total(self.os_id))}"
                                                "? Ele fica disponível para o atendente apresentar ao cliente.",
                     "Aprovar") and self._executar(self.ctrl.orcamento.aprovar, self.usuario, self.os_id):
            self._feito("Orçamento aprovado e disponível ao atendente.")

    def exportar(self):
        salvar_e_abrir_pdf(self, f"orcamento_OS{self.os_id}.pdf",
                           lambda caminho: self.ctrl.orcamento.exportar_pdf(self.os_id, caminho))

    def decisao(self):
        d = DialogoDecisao(self)
        r = d.mostrar()
        if not r:
            return
        novo = self._executar(self.ctrl.orcamento.registrar_decisao_cliente, self.usuario, self.os_id,
                              r["aprovou"], r["motivo"])
        if novo:
            self._feito({S.CANCELADA: "OS cancelada por rejeição do orçamento.",
                         S.AGUARDANDO_PECAS: "Execução autorizada, mas faltam peças: a solicitação de compra foi "
                                             "enviada ao gerente.",
                         S.EM_EXECUCAO: "Execução autorizada. O mecânico foi avisado no painel."}[novo])

    def avisar(self):
        texto = self._executar(self.ctrl.os.gerar_mensagem, self.os_id)
        if not texto:
            return
        QGuiApplication.clipboard().setText(texto)
        if confirmar(self, "Avisar cliente", texto + "\n\nA mensagem já foi copiada: cole no WhatsApp ou no SMS. "
                                                     "Confirmar que o cliente foi avisado?", "Confirmar aviso") and \
                self._executar(self.ctrl.os.registrar_aviso_cliente, self.usuario, self.os_id):
            self._feito("Aviso ao cliente registrado na OS.")

    def pagamento(self):
        falta = self.ctrl.os.calcular_total(self.os_id) - self.ctrl.pagamento.get_total_pago(self.os_id)
        r = pedir(self, "Registrar pagamento",
                  [{"chave": "v", "rotulo": "Valor", "validar": numero_valido, "unidade": "R$"},
                   ("f", "Forma de pagamento", FORMAS_PAGAMENTO)],
                  {"v": f"{max(falta, 0):.2f}".replace(".", ",")}, f"Falta receber {moeda(max(falta, 0))}.",
                  "Registrar pagamento")
        if r and self._executar(self.ctrl.pagamento.registrar_pagamento, self.usuario, self.os_id, r["v"], r["f"]):
            self._feito("Pagamento registrado.")

    def entregar(self):
        if confirmar(self, "Entregar veículo", "Registrar a entrega e encerrar a OS? Só é possível com o valor total "
                                               "pago.", "Entregar e encerrar") and \
                self._executar(self.ctrl.pagamento.entregar_veiculo, self.usuario, self.os_id):
            self._feito("Veículo entregue. OS encerrada.")


class DialogoDecisao(Dialogo):
    def __init__(self, pai):
        super().__init__(pai, "Decisão do cliente", "Registre se o cliente aprovou ou rejeitou o orçamento.",
                         "Registrar decisão")
        self.escolha = selecao([(True, "Aprovou o orçamento"), (False, "Rejeitou o orçamento")])
        self.motivo = area_texto("Por que o cliente rejeitou?", 70)
        self.c_escolha = Campo("O cliente", self.escolha, obrigatorio=True)
        self.c_motivo = Campo("Motivo da rejeição", self.motivo, "Obrigatório quando o cliente rejeita (RN09).")
        self.corpo.addWidget(self.c_escolha)
        self.corpo.addWidget(self.c_motivo)
        self.c_motivo.setEnabled(False)
        self.escolha.currentIndexChanged.connect(lambda _: self.c_motivo.setEnabled(self.escolha.currentData() is False))

    def validar(self):
        if not self.c_escolha.validar():
            return None
        aprovou = self.escolha.currentData()
        if not aprovou and not self.motivo.toPlainText().strip():
            self.c_motivo.erro("Informe o motivo da rejeição.")
            return None
        return {"aprovou": aprovou, "motivo": self.motivo.toPlainText().strip()}


class DialogoItens(Dialogo):
    """Escolha de serviços e peças do catálogo, com pesquisa (diagnóstico RF11, itens e execução RF26)."""

    def __init__(self, pai, cadastro, titulo, com_descricao, aviso=""):
        super().__init__(pai, titulo, aviso or "Pesquise no catálogo, escolha o item e a quantidade e clique em "
                                               "Adicionar.", "Confirmar", largura=760)
        self.cadastro, self.com_descricao = cadastro, com_descricao
        self.servicos, self.pecas = [], []
        if com_descricao:
            self.texto = area_texto("Descreva o que foi encontrado na avaliação do veículo.")
            self.c_texto = Campo("Diagnóstico e observações", self.texto, obrigatorio=True)
            self.corpo.addWidget(self.c_texto)
        self.cb_serv, self.qt_serv = self._linha("Serviço", self._opcoes_servico, self._add_servico)
        self.cb_peca, self.qt_peca = self._linha("Peça", self._opcoes_peca, self._add_peca)
        self.corpo.addWidget(rotulo("Itens escolhidos", "rotulo"))
        self.lista = QListWidget()
        self.lista.setMinimumHeight(150)
        self.lista.setAccessibleName("Itens escolhidos")
        self.corpo.addWidget(self.lista)
        self.vazio = rotulo("Nenhum item adicionado ainda.", "ajuda")
        self.corpo.addWidget(self.vazio)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(Botao("Retirar da lista", "perigo", "trash-2", "Retirar o item selecionado", self._retirar))
        self.corpo.addLayout(h)

    def _opcoes_servico(self, busca=""):
        return [(s.id, f"{s.descricao} · {moeda(s.valor_base)}") for s in self.cadastro.get_servicos(True, busca)]

    def _opcoes_peca(self, busca=""):
        return [(p.id, f"{p.descricao} · {moeda(p.valor)} · estoque {p.qtd_estoque}")
                for p in self.cadastro.get_pecas(busca)]

    def _linha(self, titulo, opcoes, comando):
        caixa = QFrame()
        caixa.setProperty("papel", "cartao")
        g = QGridLayout(caixa)
        g.setContentsMargins(ESPACO["s"], ESPACO["s"], ESPACO["s"], ESPACO["s"])
        g.setHorizontalSpacing(ESPACO["xs"])
        g.addWidget(rotulo(titulo, "titulo_secao"), 0, 0, 1, 4)
        busca = Busca(f"Pesquisar {titulo.lower()}")
        cb = selecao(opcoes(), f"Escolha o {titulo.lower()}" if titulo == "Serviço" else "Escolha a peça")
        cb.setAccessibleName(titulo)
        qt = quantidade()
        qt.setAccessibleName(f"Quantidade de {titulo.lower()}")

        def filtrar(texto):
            valores = opcoes(texto)
            definir_opcoes(cb, valores)
            if valores and texto:
                cb.setCurrentIndex(0)
        busca.pesquisar.connect(filtrar)
        busca.returnPressed.connect(comando)
        g.addWidget(busca, 1, 0)
        g.addWidget(cb, 1, 1)
        g.addWidget(qt, 1, 2)
        g.addWidget(Botao("Adicionar", "secundario", "plus", f"Adicionar {titulo.lower()} à lista", comando), 1, 3)
        g.setColumnStretch(0, 2)
        g.setColumnStretch(1, 3)
        self.corpo.addWidget(caixa)
        return cb, qt

    def _add(self, cb, qt, destino, tipo):
        if cb.currentIndex() < 0:
            notificar(self, f"Pesquise e escolha o item ({tipo.lower()}) na lista.", "info")
            return
        destino.append((cb.currentData(), str(qt.value())))
        self.lista.addItem(f"{tipo}: {qt.value()} × {cb.currentText()}")
        self.vazio.hide()

    def _add_servico(self):
        self._add(self.cb_serv, self.qt_serv, self.servicos, "Serviço")

    def _add_peca(self):
        self._add(self.cb_peca, self.qt_peca, self.pecas, "Peça")

    def _retirar(self):
        n = self.lista.currentRow()
        if n < 0:
            notificar(self, "Selecione o item na lista de itens escolhidos.", "info")
            return
        tipo = self.lista.item(n).text().split(":")[0]
        destino = self.servicos if tipo == "Serviço" else self.pecas
        posicao = sum(1 for i in range(n) if self.lista.item(i).text().split(":")[0] == tipo)
        del destino[posicao]
        self.lista.takeItem(n)
        self.vazio.setVisible(self.lista.count() == 0)

    def validar(self):
        if self.com_descricao and not self.c_texto.validar():
            return None
        descricao = self.texto.toPlainText().strip() if self.com_descricao else ""
        return descricao, self.servicos, self.pecas

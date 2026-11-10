"""Diálogo de solicitação de compra de peça (RF22): para uma OS ou, sem OS, para repor o estoque.

Usado pela página Compras, pela página Peças e serviços e pela janela da OS.
"""
from ..modelo.atendimento import StatusOS
from .componentes import Campo, Dialogo, area_texto, executar, notificar, quantidade, rotulo, selecao

SEM_OS = 0           # valor do item "Repor o estoque" na lista de destinos


class DialogoSolicitacao(Dialogo):

    def __init__(self, pai, ctrl, usuario, peca_id=None, os_id=None, os_fixa=False):
        super().__init__(pai, "Nova solicitação de compra",
                         "Peça a compra para uma OS ou para repor o estoque. O gerente vê o pedido na página Compras "
                         "e registra a compra e o recebimento.", "Solicitar compra", largura=580)
        self.pecas = {p.id: p for p in ctrl.cadastro.get_pecas()}
        ordem = sorted(self.pecas.values(), key=lambda p: p.descricao.lower())
        self.c_peca = Campo("Peça", selecao([(p.id, f"{p.descricao} (cód. {p.id})") for p in ordem], "Escolha a peça"),
                            obrigatorio=True)
        self.info = rotulo("", "legenda", True)
        self.c_qtd = Campo("Quantidade", quantidade(1, 999), "Sugestão: o que falta para chegar ao estoque mínimo.",
                           unidade="un.")
        if os_fixa:
            destinos = [(os_id, f"OS {os_id}")]
        else:
            ativos = [s for s in StatusOS.NOMES if s not in (StatusOS.ENCERRADA, StatusOS.CANCELADA)]
            destinos = [(SEM_OS, "Repor o estoque (sem OS)")] + [
                (o.id, f"OS {o.id} · {o.placa} · {o.cliente_nome} ({StatusOS.NOMES.get(o.status, o.status)})")
                for o in ctrl.os.get_lista(usuario, ativos)]
        self.c_dest = Campo("Para", selecao(destinos), "Sem OS, a peça entra no estoque quando chegar; com OS, a OS "
                                                      "volta para execução quando todas as peças chegarem.",
                            obrigatorio=True)
        self.c_dest.controle.setEnabled(not os_fixa)
        self.c_obs = Campo("Observação", area_texto("Ex.: marca preferida, urgência ou aplicação da peça", 72))
        for w in (self.c_peca, self.info, self.c_qtd, self.c_dest, self.c_obs):
            self.corpo.addWidget(w)
        self.c_obs.controle.ensurePolished()           # o estilo aplica a altura mínima dos campos; a da área
        self.c_obs.controle.setMinimumHeight(72)       # de texto vem depois, para não ficar com uma linha só
        self.c_peca.controle.currentIndexChanged.connect(self._peca_mudou)
        self.c_dest.definir(os_id if os_id else SEM_OS)
        if peca_id in self.pecas:
            self.c_peca.definir(peca_id)
        self._peca_mudou()
        self.setMinimumHeight(self.sizeHint().height())

    def _peca_mudou(self, *_):
        p = self.pecas.get(self.c_peca.controle.currentData())
        if not p:
            self.info.setText("")
            return
        situacao = ("sem estoque" if p.qtd_estoque <= 0 else
                    "abaixo do mínimo" if p.qtd_estoque < p.estoque_minimo else "estoque normal")
        self.info.setText(f"Em estoque: {p.qtd_estoque} un. · mínimo: {p.estoque_minimo} un. · {situacao}")
        self.c_qtd.definir(max(1, p.estoque_minimo - p.qtd_estoque))

    def validar(self):
        if not all([self.c_peca.validar(), self.c_qtd.validar(), self.c_dest.validar()]):
            return None
        return {"peca": self.c_peca.valor(), "qtd": self.c_qtd.valor(), "os": self.c_dest.valor() or None,
                "obs": self.c_obs.valor()}


def solicitar_compra(pai, ctrl, usuario, peca_id=None, os_id=None, os_fixa=False):
    """Mostra o diálogo e registra a solicitação; devolve a solicitação criada (ou None)."""
    r = DialogoSolicitacao(pai, ctrl, usuario, peca_id, os_id, os_fixa).mostrar()
    if not r:
        return None
    sol = executar(ctrl.compras.solicitar_compra, usuario, r["os"], r["peca"], r["qtd"], r["obs"], pai=pai)
    if sol:
        destino = f"para a OS {sol.os_id}" if sol.os_id else "para o estoque"
        notificar(pai, f"Solicitação nº {sol.id} registrada {destino}. Acompanhe na página Compras.", "sucesso")
    return sol


def alterar_solicitacao(pai, ctrl, usuario, sol):
    """Quantidade e observação de uma solicitação pendente."""
    d = Dialogo(pai, f"Alterar solicitação nº {sol.id}", f"{sol.peca_descricao} · {sol.origem}", "Salvar", largura=480)
    c_qtd = Campo("Quantidade", quantidade(1, 999), unidade="un.")
    c_qtd.definir(sol.quantidade)
    c_obs = Campo("Observação", area_texto("", 72))
    c_obs.definir(sol.observacao)
    d.corpo.addWidget(c_qtd)
    d.corpo.addWidget(c_obs)
    c_obs.controle.ensurePolished()
    c_obs.controle.setMinimumHeight(72)
    d.validar = lambda: {"q": c_qtd.valor(), "o": c_obs.valor()}
    r = d.mostrar()
    return bool(r) and bool(executar(ctrl.compras.alterar_solicitacao, usuario, sol.id, r["q"], r["o"],
                                     sucesso="Solicitação alterada.", pai=pai))

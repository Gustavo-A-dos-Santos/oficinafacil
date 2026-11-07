"""ServicoOrcamento: cálculo dos totais e criação das versões do orçamento (RF14, RF16, RN10)."""
from ..modelo.atendimento import Orcamento, SituacaoOrcamento
from ..persistencia import agora
from ..persistencia.orcamento_dao import OrcamentoDAO
from ..persistencia.ordem_servico_dao import OrdemServicoDAO


class ServicoOrcamento:

    def __init__(self, conn):
        self.os_dao = OrdemServicoDAO(conn)
        self.orcamento_dao = OrcamentoDAO(conn)

    def calcular_total(self, os_id):
        """Soma dos serviços e das peças da OS."""
        total = sum(i.subtotal() for i in self.os_dao.get_itens_servico(os_id))
        total += sum(i.subtotal() for i in self.os_dao.get_itens_peca(os_id))
        return round(total, 2)

    def nova_versao(self, os_id):
        """Grava uma nova versão pendente de aprovação; a anterior, se houver, fica como Alterado."""
        atual = self.orcamento_dao.get_atual(os_id)
        if atual:
            atual.situacao = SituacaoOrcamento.ALTERADO
            self.orcamento_dao.editar(atual)
        versao = atual.versao + 1 if atual else 1
        return self.orcamento_dao.salvar(Orcamento(os_id=os_id, versao=versao, valor_total=self.calcular_total(os_id),
                                                   data=agora()))

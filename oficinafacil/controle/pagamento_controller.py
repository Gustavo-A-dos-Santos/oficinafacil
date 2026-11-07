"""PagamentoController: pagamento (RF30), bloqueio da entrega sem pagamento (RF31) e entrega (RF32)."""
from ..modelo import RegraNegocioError, moeda
from ..modelo.atendimento import Pagamento, StatusOS
from ..modelo.cadastro import Perfil
from ..persistencia import agora
from ..persistencia.ordem_servico_dao import OrdemServicoDAO
from ..persistencia.pagamento_dao import PagamentoDAO
from ..servico.orcamento import ServicoOrcamento
from ..servico.seguranca import ServicoSeguranca
from . import exigir_status, mudar_status, transacao, valor_monetario


class PagamentoController:

    FORMAS = ["Dinheiro", "PIX", "Cartão de débito", "Cartão de crédito"]

    def __init__(self, conn):
        self.conn = conn
        self.os_dao = OrdemServicoDAO(conn)
        self.pagamento_dao = PagamentoDAO(conn)
        self.servico_orcamento = ServicoOrcamento(conn)
        self.seguranca = ServicoSeguranca()

    @transacao
    def registrar_pagamento(self, usuario, os_id, valor, forma):
        """RF30: valor, forma e data, vinculados à OS concluída. Aceita mais de um pagamento."""
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE)
        exigir_status(self._os(os_id), StatusOS.CONCLUIDA)
        if forma not in self.FORMAS:
            raise RegraNegocioError("Selecione a forma de pagamento.")
        return self.pagamento_dao.salvar(Pagamento(os_id=os_id, valor=valor_monetario(valor, "valor", positivo=True),
                                                   forma_pagamento=forma, data=agora()))

    @transacao
    def entregar_veiculo(self, usuario, os_id):
        """RF32 (inclui RF31; RN07): só encerra a OS se os pagamentos cobrirem o total."""
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE)
        os_ = self._os(os_id)
        exigir_status(os_, StatusOS.CONCLUIDA)
        total, pago = self.servico_orcamento.calcular_total(os_id), self.pagamento_dao.get_total_pago(os_id)
        if pago == 0 or pago < total:
            raise RegraNegocioError(f"Entrega bloqueada: pagamento não registrado (RN07). "
                                    f"Total {moeda(total)}, pago {moeda(pago)}.")
        mudar_status(self.os_dao, os_, StatusOS.ENCERRADA, usuario)

    def get_pagamentos(self, os_id):
        return self.pagamento_dao.get_pagamentos(os_id)

    def get_total_pago(self, os_id):
        return self.pagamento_dao.get_total_pago(os_id)

    def _os(self, os_id):
        os_ = self.os_dao.get_os(os_id)
        if not os_:
            raise RegraNegocioError(f"OS {os_id} não encontrada.")
        return os_

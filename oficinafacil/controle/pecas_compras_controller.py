"""PecasComprasController: disponibilidade (RF21), solicitações (RF22), compras (RF23), baixa (RF24) e resíduos (RF25)."""
from ..modelo import RegraNegocioError
from ..modelo.atendimento import SituacaoCompra, SolicitacaoCompra, StatusOS
from ..modelo.cadastro import Perfil
from ..persistencia.estoque_dao import EstoqueDAO
from ..persistencia.ordem_servico_dao import OrdemServicoDAO
from ..servico.estoque import ServicoEstoque
from ..servico.seguranca import ServicoSeguranca
from . import inteiro, mudar_status, obrigatorio, transacao


class PecasComprasController:

    def __init__(self, conn):
        self.conn = conn
        self.os_dao = OrdemServicoDAO(conn)
        self.estoque_dao = EstoqueDAO(conn)
        self.servico_estoque = ServicoEstoque(conn)
        self.seguranca = ServicoSeguranca()

    def verificar_pecas(self, os_id):
        """RF21: [(peca_id, quantidade que falta)] das peças da OS sem estoque."""
        return self.servico_estoque.verificar_pecas(os_id)

    @transacao
    def solicitar_faltantes(self, os_id):
        """RF22 (extensão de RF21): uma solicitação pendente para cada peça que falta. Devolve as solicitações."""
        return [self.estoque_dao.salvar_solicitacao(SolicitacaoCompra(os_id=os_id, peca_id=peca_id, quantidade=falta))
                for peca_id, falta in self.verificar_pecas(os_id)]

    @transacao
    def solicitar_compra(self, usuario, os_id, peca_id, quantidade):
        """RF22: pedido manual do mecânico."""
        self.seguranca.exigir_perfil(usuario, Perfil.MECANICO)
        if not self.os_dao.get_os(os_id):
            raise RegraNegocioError(f"OS {os_id} não encontrada.")
        if not self.estoque_dao.get_peca(peca_id):
            raise RegraNegocioError("Selecione a peça.")
        return self.estoque_dao.salvar_solicitacao(
            SolicitacaoCompra(os_id=os_id, peca_id=peca_id, quantidade=inteiro(quantidade, "quantidade", 1)))

    @transacao
    def registrar_compra(self, usuario, solicitacao_id, fornecedor_id):
        """RF23: o gerente registra a compra com o fornecedor."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        s = self._solicitacao(solicitacao_id, SituacaoCompra.PENDENTE)
        if not self.estoque_dao.get_fornecedor(fornecedor_id):
            raise RegraNegocioError("Selecione o fornecedor.")
        s.fornecedor_id, s.situacao = fornecedor_id, SituacaoCompra.COMPRADA
        self.estoque_dao.editar_solicitacao(s)

    @transacao
    def registrar_recebimento(self, usuario, solicitacao_id):
        """RF23: soma as peças ao estoque e libera a OS para execução quando não há mais compras em aberto."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        s = self._solicitacao(solicitacao_id, SituacaoCompra.COMPRADA)
        s.situacao = SituacaoCompra.RECEBIDA
        self.estoque_dao.editar_solicitacao(s)
        self.estoque_dao.somar_estoque(s.peca_id, s.quantidade)
        self._liberar_os_se_completa(s.os_id, usuario)

    @transacao
    def cancelar_solicitacao(self, usuario, solicitacao_id):
        """RF23 (A2): compra desistida; a solicitação fica Cancelada."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        s = self._solicitacao(solicitacao_id, SituacaoCompra.PENDENTE, SituacaoCompra.COMPRADA)
        s.situacao = SituacaoCompra.CANCELADA
        self.estoque_dao.editar_solicitacao(s)

    def _liberar_os_se_completa(self, os_id, usuario):
        os_ = self.os_dao.get_os(os_id)
        abertas = self.estoque_dao.get_solicitacoes([SituacaoCompra.PENDENTE, SituacaoCompra.COMPRADA], os_id)
        if os_.status == StatusOS.AGUARDANDO_PECAS and not abertas and not self.verificar_pecas(os_id):
            mudar_status(self.os_dao, os_, StatusOS.EM_EXECUCAO, usuario)  # o mecânico vê no painel

    def _solicitacao(self, id, *situacoes):
        s = self.estoque_dao.get_solicitacao(id)
        if not s or s.situacao not in situacoes:
            raise RegraNegocioError("Situação da solicitação não permite a operação.")
        return s

    def get_solicitacoes(self, situacao=None):
        return self.estoque_dao.get_solicitacoes(situacao)

    @transacao
    def registrar_destinacao(self, usuario, item_peca_id, destino):
        """RF25: destinação da peça ou resíduo substituído (óleo, filtro, bateria, pneu)."""
        self.seguranca.exigir_perfil(usuario, Perfil.MECANICO)
        if self.os_dao.editar_destinacao(item_peca_id, obrigatorio(destino, "destinação")) == 0:
            raise RegraNegocioError("Item de peça não encontrado.")

    def pecas_abaixo_do_minimo(self):
        return self.servico_estoque.pecas_abaixo_do_minimo()

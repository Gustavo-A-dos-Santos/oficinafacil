"""OrcamentoController: gera (RF14), notifica (RF15), aprova ou altera (RF16), exporta (RF17) o orçamento
e registra a decisão do cliente (RF18), que autoriza a execução (RF19) ou encerra por rejeição (RF20)."""
from ..modelo import RegraNegocioError
from ..modelo.atendimento import SituacaoOrcamento, StatusOS
from ..modelo.cadastro import Perfil
from ..persistencia import agora
from ..persistencia.orcamento_dao import OrcamentoDAO
from ..persistencia.ordem_servico_dao import OrdemServicoDAO
from ..servico.orcamento import ServicoOrcamento
from ..servico.relatorio import ServicoRelatorio
from ..servico.seguranca import ServicoSeguranca
from . import exigir_status, mudar_status, obrigatorio, transacao, valor_monetario


class OrcamentoController:

    def __init__(self, conn):
        self.conn = conn
        self.os_dao = OrdemServicoDAO(conn)
        self.orcamento_dao = OrcamentoDAO(conn)
        self.servico_orcamento = ServicoOrcamento(conn)
        self.servico_relatorio = ServicoRelatorio(conn)
        self.seguranca = ServicoSeguranca()

    @transacao
    def gerar_orcamento(self, usuario, os_id):
        """RF14 (inclui RF15): versão 1 pendente de aprovação; a OS passa a Aguardando gerente (painel do gerente)."""
        orcamento = self.servico_orcamento.nova_versao(os_id)
        mudar_status(self.os_dao, self.os_dao.get_os(os_id), StatusOS.AGUARDANDO_GERENTE, usuario)
        return orcamento

    @transacao
    def alterar_valor_item(self, usuario, os_id, tipo, item_id, novo_valor):
        """RF16 (RN10): muda o valor unitário de um item e cria nova versão, que precisa ser aprovada."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        exigir_status(self._os(os_id), StatusOS.AGUARDANDO_GERENTE)
        if tipo not in ("servico", "peca"):
            raise RegraNegocioError("Tipo de item inválido.")
        if self.os_dao.editar_valor_item(tipo, item_id, os_id, valor_monetario(novo_valor, "novo valor")) == 0:
            raise RegraNegocioError("Item não encontrado nesta OS.")
        return self.servico_orcamento.nova_versao(os_id)

    @transacao
    def aprovar(self, usuario, os_id):
        """RF16 e RF17 (RN02): o gerente aprova e o orçamento fica disponível ao atendente."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        os_ = self._os(os_id)
        exigir_status(os_, StatusOS.AGUARDANDO_GERENTE)
        orcamento = self.orcamento_dao.get_atual(os_id)
        orcamento.gerente_id, orcamento.situacao = usuario.id, SituacaoOrcamento.APROVADO_GERENTE
        self.orcamento_dao.editar(orcamento)
        mudar_status(self.os_dao, os_, StatusOS.AGUARDANDO_CLIENTE, usuario)

    @transacao
    def registrar_decisao_cliente(self, usuario, os_id, aprovado, motivo=""):
        """RF18 (estendido por RF19 e RF20). Devolve o novo status da OS."""
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE)
        os_ = self._os(os_id)
        exigir_status(os_, StatusOS.AGUARDANDO_CLIENTE)
        orcamento = self.orcamento_dao.get_atual(os_id)
        orcamento.data_hora_decisao_cliente = agora()  # o responsável fica no histórico de status
        if not aprovado:
            # RF20 (RN09): rejeição cancela a OS com o motivo
            os_.motivo_cancelamento = obrigatorio(motivo, "motivo da rejeição")
            orcamento.situacao = SituacaoOrcamento.REJEITADO
            self.orcamento_dao.editar(orcamento)
            mudar_status(self.os_dao, os_, StatusOS.CANCELADA, usuario)
            return StatusOS.CANCELADA
        orcamento.situacao = SituacaoOrcamento.APROVADO_CLIENTE
        self.orcamento_dao.editar(orcamento)
        from .os_controller import OSController  # import aqui para evitar import circular
        return OSController(self.conn).autorizar_execucao(usuario, os_id)  # RF19

    def exportar_pdf(self, os_id, caminho):
        """RF17: só depois de aprovado pelo gerente (RN02)."""
        orcamento = self.orcamento_dao.get_atual(os_id)
        if not orcamento or orcamento.situacao not in (SituacaoOrcamento.APROVADO_GERENTE,
                                                       SituacaoOrcamento.APROVADO_CLIENTE):
            raise RegraNegocioError("O orçamento só pode ser exportado depois de aprovado pelo gerente (RN02).")
        linhas = self.servico_relatorio.linhas_orcamento(self._os(os_id), orcamento, self.os_dao.get_itens_servico(os_id),
                                                         self.os_dao.get_itens_peca(os_id))
        self.servico_relatorio.escrever_pdf(caminho, linhas)

    def get_atual(self, os_id):
        return self.orcamento_dao.get_atual(os_id)

    def get_versoes(self, os_id):
        return self.orcamento_dao.get_versoes(os_id)

    def _os(self, os_id):
        os_ = self.os_dao.get_os(os_id)
        if not os_:
            raise RegraNegocioError(f"OS {os_id} não encontrada.")
        return os_

"""PecasComprasController: disponibilidade (RF21), solicitações (RF22, para uma OS ou para repor o estoque), compras
(RF23), baixa (RF24) e resíduos (RF25)."""
from ..modelo import RegraNegocioError
from ..modelo.atendimento import SituacaoCompra, SolicitacaoCompra, StatusOS
from ..modelo.cadastro import Perfil
from ..persistencia.estoque_dao import EstoqueDAO
from ..persistencia.ordem_servico_dao import OrdemServicoDAO
from ..servico.estoque import ServicoEstoque
from ..servico.seguranca import ServicoSeguranca
from . import inteiro, mudar_status, obrigatorio, periodo, transacao


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
        return [self.estoque_dao.salvar_solicitacao(SolicitacaoCompra(os_id=os_id, peca_id=peca_id, quantidade=falta,
                                                                      observacao="Peça em falta na OS."))
                for peca_id, falta in self.verificar_pecas(os_id)]

    @transacao
    def solicitar_compra(self, usuario, os_id, peca_id, quantidade, observacao=""):
        """RF22: pedido manual de peça, ligado a uma OS ou, sem OS, para repor o estoque. Mecânico, atendente e
        gerente podem pedir; quem pediu fica registrado."""
        self.seguranca.exigir_perfil(usuario, Perfil.MECANICO, Perfil.ATENDENTE, Perfil.GERENTE)
        os_id = inteiro(os_id, "número da OS", 1) if os_id not in (None, "", 0, "0") else None
        if os_id:
            os_ = self.os_dao.get_os(os_id)
            if not os_:
                raise RegraNegocioError(f"OS {os_id} não encontrada.")
            if os_.status in (StatusOS.ENCERRADA, StatusOS.CANCELADA):
                raise RegraNegocioError(f"A OS {os_id} já foi encerrada ou cancelada; peça a compra sem OS, para o estoque.")
        if not peca_id or not self.estoque_dao.get_peca(peca_id):
            raise RegraNegocioError("Selecione a peça.")
        aberta = [s for s in self.estoque_dao.get_solicitacoes(SituacaoCompra.PENDENTE, peca_id=peca_id)
                  if s.os_id == os_id]
        if aberta:
            destino = f"para a OS {os_id}" if os_id else "para o estoque"
            raise RegraNegocioError(f"Já existe a solicitação nº {aberta[0].id}, pendente, desta peça {destino}. "
                                    "Altere a quantidade dela.")
        return self.estoque_dao.salvar_solicitacao(
            SolicitacaoCompra(os_id=os_id, peca_id=peca_id, quantidade=inteiro(quantidade, "quantidade", 1),
                              solicitante_id=usuario.id, observacao=(observacao or "").strip()[:300]))

    @transacao
    def alterar_solicitacao(self, usuario, solicitacao_id, quantidade, observacao=""):
        """Muda a quantidade e a observação enquanto a solicitação está pendente (o gerente ou quem pediu)."""
        s = self._solicitacao(solicitacao_id, SituacaoCompra.PENDENTE)
        self._exigir_dono_ou_gerente(usuario, s)
        s.quantidade = inteiro(quantidade, "quantidade", 1)
        s.observacao = (observacao or "").strip()[:300]
        self.estoque_dao.editar_solicitacao(s)

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
        if s.os_id:                                     # compra para o estoque não mexe em OS
            self._liberar_os_se_completa(s.os_id, usuario)

    @transacao
    def cancelar_solicitacao(self, usuario, solicitacao_id):
        """RF23 (A2): compra desistida; a solicitação fica Cancelada. O gerente cancela pendentes e compradas; quem
        pediu pode cancelar a sua enquanto está pendente."""
        if usuario.tem_perfil(Perfil.GERENTE):
            s = self._solicitacao(solicitacao_id, SituacaoCompra.PENDENTE, SituacaoCompra.COMPRADA)
        else:
            s = self._solicitacao(solicitacao_id, SituacaoCompra.PENDENTE)
            self._exigir_dono_ou_gerente(usuario, s)
        s.situacao = SituacaoCompra.CANCELADA
        self.estoque_dao.editar_solicitacao(s)

    def _liberar_os_se_completa(self, os_id, usuario):
        os_ = self.os_dao.get_os(os_id)
        abertas = self.estoque_dao.get_solicitacoes([SituacaoCompra.PENDENTE, SituacaoCompra.COMPRADA], os_id)
        if os_.status == StatusOS.AGUARDANDO_PECAS and not abertas and not self.verificar_pecas(os_id):
            mudar_status(self.os_dao, os_, StatusOS.EM_EXECUCAO, usuario)  # o mecânico vê no painel

    @staticmethod
    def _exigir_dono_ou_gerente(usuario, s):
        if not usuario.tem_perfil(Perfil.GERENTE) and s.solicitante_id != usuario.id:
            raise RegraNegocioError("Só o gerente ou quem fez a solicitação pode alterá-la ou cancelá-la.")

    def _solicitacao(self, id, *situacoes):
        s = self.estoque_dao.get_solicitacao(id)
        if not s or s.situacao not in situacoes:
            raise RegraNegocioError("Situação da solicitação não permite a operação.")
        return s

    def get_solicitacoes(self, situacao=None, os_id=None, peca="", fornecedor_id=None, origem=None, data_inicio="",
                         data_fim="", solicitante_id=None):
        """Lista com filtros (ver EstoqueDAO.get_solicitacoes); o período e o número da OS são validados."""
        data_inicio, data_fim = periodo(data_inicio, data_fim)
        if os_id not in (None, ""):
            os_id = inteiro(os_id, "número da OS", 1)
        return self.estoque_dao.get_solicitacoes(situacao, os_id, (peca or "").strip(), fornecedor_id, origem,
                                                 data_inicio, data_fim, solicitante_id)

    def resumo_solicitacoes(self):
        """{situação: quantidade} de todas as solicitações, para os indicadores da página Compras."""
        contagem = self.estoque_dao.contar_solicitacoes()
        return {s: contagem.get(s, 0) for s in SituacaoCompra.TODAS}

    @transacao
    def registrar_destinacao(self, usuario, item_peca_id, destino):
        """RF25: destinação da peça ou resíduo substituído (óleo, filtro, bateria, pneu)."""
        self.seguranca.exigir_perfil(usuario, Perfil.MECANICO)
        if self.os_dao.editar_destinacao(item_peca_id, obrigatorio(destino, "destinação")) == 0:
            raise RegraNegocioError("Item de peça não encontrado.")

    def pecas_abaixo_do_minimo(self):
        return self.servico_estoque.pecas_abaixo_do_minimo()

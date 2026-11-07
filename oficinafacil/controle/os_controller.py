"""OSController: abertura (RF08, RF10), classificação (RF09), diagnóstico (RF11), status (RF12), consulta (RF13),
autorização (RF19), execução (RF26), conclusão (RF27, RF28) e aviso ao cliente (RF29)."""
from ..modelo import RegraNegocioError
from ..modelo.atendimento import Diagnostico, ItemPecaOS, ItemServicoOS, OrdemServico, StatusOS
from ..modelo.cadastro import Perfil
from ..persistencia import agora
from ..persistencia.cliente_veiculo_dao import ClienteVeiculoDAO
from ..persistencia.estoque_dao import EstoqueDAO
from ..persistencia.ordem_servico_dao import OrdemServicoDAO
from ..persistencia.usuario_dao import UsuarioDAO
from ..servico.estoque import ServicoEstoque
from ..servico.notificacao import ServicoNotificacao
from ..servico.orcamento import ServicoOrcamento
from ..servico.seguranca import ServicoSeguranca
from . import exigir_status, inteiro, mudar_status, obrigatorio, transacao
from .orcamento_controller import OrcamentoController
from .pecas_compras_controller import PecasComprasController


class OSController:

    def __init__(self, conn):
        self.conn = conn
        self.os_dao = OrdemServicoDAO(conn)
        self.cv_dao = ClienteVeiculoDAO(conn)
        self.estoque_dao = EstoqueDAO(conn)
        self.usuario_dao = UsuarioDAO(conn)
        self.servico_estoque = ServicoEstoque(conn)
        self.servico_orcamento = ServicoOrcamento(conn)
        self.notificacao = ServicoNotificacao(conn)
        self.seguranca = ServicoSeguranca()

    @transacao
    def abrir_os(self, usuario, cliente_id, veiculo_id, problema, km_entrada):
        """RF08 (inclui RF10 e RF12): a OS nasce Aberta e aparece no painel do mecânico."""
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE, Perfil.GERENTE)
        veiculo = self.cv_dao.get_veiculo(veiculo_id)
        if not veiculo or veiculo.cliente_id != cliente_id:
            raise RegraNegocioError("O veículo deve pertencer ao cliente da OS (RN08).")
        os_ = self.os_dao.salvar(OrdemServico(cliente_id=cliente_id, veiculo_id=veiculo_id, usuario_abertura_id=usuario.id,
                                              problema=obrigatorio(problema, "problema relatado"),
                                              km_entrada=inteiro(km_entrada, "quilometragem de entrada"),
                                              data_abertura=agora()))
        self.cv_dao.atualizar_km(veiculo_id, os_.km_entrada)
        mudar_status(self.os_dao, os_, StatusOS.ABERTA, usuario)
        return os_.id

    @transacao
    def classificar(self, usuario, os_id, simples, mecanico_id):
        """RF09 (RN01): serviço simples vai direto para execução; avaliação completa vai para diagnóstico."""
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE, Perfil.MECANICO)
        os_ = self.get_os(os_id)
        exigir_status(os_, StatusOS.ABERTA)
        mecanico = self.usuario_dao.get_usuario(mecanico_id)
        if not mecanico or mecanico.perfil != Perfil.MECANICO or not mecanico.ativo:
            raise RegraNegocioError("Selecione o mecânico responsável.")
        os_.mecanico_id = mecanico_id
        mudar_status(self.os_dao, os_, StatusOS.EM_EXECUCAO if simples else StatusOS.EM_DIAGNOSTICO, usuario)

    @transacao
    def registrar_diagnostico(self, usuario, os_id, descricao, servicos, pecas):
        """RF11 (inclui RF14 e RF12). servicos e pecas: listas de (id, quantidade)."""
        self.seguranca.exigir_perfil(usuario, Perfil.MECANICO)
        exigir_status(self.get_os(os_id), StatusOS.EM_DIAGNOSTICO)
        if not servicos:
            raise RegraNegocioError("Informe ao menos um serviço necessário.")
        self.os_dao.salvar_diagnostico(Diagnostico(os_id=os_id, mecanico_id=usuario.id,
                                                   descricao=obrigatorio(descricao, "diagnóstico"), data=agora()))
        self._inserir_itens(os_id, servicos, pecas)
        OrcamentoController(self.conn).gerar_orcamento(usuario, os_id)

    @transacao
    def autorizar_execucao(self, usuario, os_id):
        """RF19 (inclui RF21; estendido por RF22): com todas as peças, a OS vai para execução;
        se faltar peça, as solicitações de compra são criadas e a OS aguarda peças. Devolve o novo status."""
        os_ = self.get_os(os_id)
        compras = PecasComprasController(self.conn)
        if compras.verificar_pecas(os_id):
            compras.solicitar_faltantes(os_id)
            novo = StatusOS.AGUARDANDO_PECAS
        else:
            novo = StatusOS.EM_EXECUCAO  # o mecânico vê no painel
        mudar_status(self.os_dao, os_, novo, usuario)
        return novo

    @transacao
    def registrar_execucao(self, usuario, os_id, servicos=(), pecas=()):
        """RF26 (inclui RF24): confirma os serviços e as peças usados (os do orçamento mais os extras informados)
        e dá baixa no estoque. É feito uma vez, antes de concluir."""
        self.seguranca.exigir_perfil(usuario, Perfil.MECANICO)
        os_ = self.get_os(os_id)
        exigir_status(os_, StatusOS.EM_EXECUCAO)
        if os_.data_execucao:
            raise RegraNegocioError("A execução desta OS já foi registrada.")
        if (servicos or pecas) and OrcamentoController(self.conn).get_atual(os_id):
            # com orçamento aprovado, item a mais mudaria o valor sem nova aprovação (RN10)
            raise RegraNegocioError("Esta OS tem orçamento aprovado: itens fora dele exigem nova aprovação (RN10).")
        self._inserir_itens(os_id, servicos, pecas)
        if not self.os_dao.get_itens_servico(os_id):
            raise RegraNegocioError("Informe ao menos um serviço realizado.")
        self.servico_estoque.baixar(os_id)
        os_.data_execucao = agora()
        self.os_dao.editar(os_)

    @transacao
    def concluir_servico(self, usuario, os_id):
        """RF27 (inclui RF28 e RF12; RN05): exige a execução registrada; o atendente vê no painel."""
        self.seguranca.exigir_perfil(usuario, Perfil.MECANICO)
        os_ = self.get_os(os_id)
        exigir_status(os_, StatusOS.EM_EXECUCAO)
        if not os_.data_execucao:
            raise RegraNegocioError("Registre a execução (serviços e peças usados) antes de concluir.")
        os_.data_conclusao = agora()
        mudar_status(self.os_dao, os_, StatusOS.CONCLUIDA, usuario)

    def gerar_mensagem(self, os_id):
        """RF29 (RN06): mensagem pronta avisando que o veículo está disponível."""
        os_ = self.get_os(os_id)
        exigir_status(os_, StatusOS.CONCLUIDA, StatusOS.ENCERRADA)
        return self.notificacao.mensagem_cliente(os_, self.servico_orcamento.calcular_total(os_id))

    @transacao
    def registrar_aviso_cliente(self, usuario, os_id):
        """RF29: o atendente confirma que avisou o cliente; a data do aviso fica na OS."""
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE)
        os_ = self.get_os(os_id)
        exigir_status(os_, StatusOS.CONCLUIDA)
        os_.data_aviso_cliente = agora()
        self.os_dao.editar(os_)

    # ---------------------------------------------------------------- consultas (RF12, RF13)
    def get_os(self, os_id):
        os_ = self.os_dao.get_os(os_id)
        if not os_:
            raise RegraNegocioError(f"OS {os_id} não encontrada.")
        return os_

    def get_lista(self, usuario, status=None, cliente="", placa="", data_inicio="", data_fim=""):
        """RF13: o mecânico vê as OS sob sua responsabilidade e as ainda sem responsável."""
        lista = self.os_dao.get_lista(status, cliente, placa, data_inicio, data_fim)
        if usuario.perfil == Perfil.MECANICO:
            lista = [o for o in lista if o.mecanico_id in (None, usuario.id)]
        return lista

    def get_historico_status(self, os_id):
        return self.os_dao.get_historico(os_id)

    def get_diagnostico(self, os_id):
        return self.os_dao.get_diagnostico(os_id)

    def get_itens(self, os_id):
        return self.os_dao.get_itens_servico(os_id), self.os_dao.get_itens_peca(os_id)

    def calcular_total(self, os_id):
        return self.servico_orcamento.calcular_total(os_id)

    def pendencias(self, usuario):
        """RF10, RF15, RF28: o que espera pelo perfil do usuário."""
        return self.notificacao.pendencias(usuario)

    def _inserir_itens(self, os_id, servicos, pecas):
        """Itens com o valor atual do catálogo."""
        for servico_id, qtd in servicos:
            s = self.estoque_dao.get_servico(servico_id)
            if not s or not s.ativo:
                raise RegraNegocioError("Serviço inválido ou inativo.")
            self.os_dao.salvar_item_servico(ItemServicoOS(os_id=os_id, servico_id=servico_id, valor=s.valor_base,
                                                          quantidade=inteiro(qtd, "quantidade", 1)))
        for peca_id, qtd in pecas:
            p = self.estoque_dao.get_peca(peca_id)
            if not p:
                raise RegraNegocioError("Peça inválida.")
            self.os_dao.salvar_item_peca(ItemPecaOS(os_id=os_id, peca_id=peca_id, valor=p.valor,
                                                    quantidade=inteiro(qtd, "quantidade", 1)))

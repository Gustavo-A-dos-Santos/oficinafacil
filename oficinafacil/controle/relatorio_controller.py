"""RelatorioController: histórico de manutenção (RF33), relatórios gerenciais (RF34) e painel (RF35)."""
from ..modelo.atendimento import StatusOS
from ..modelo.cadastro import Perfil
from ..persistencia.ordem_servico_dao import OrdemServicoDAO
from ..servico.orcamento import ServicoOrcamento
from ..servico.relatorio import ServicoRelatorio
from ..servico.seguranca import ServicoSeguranca
from . import periodo


class RelatorioController:

    def __init__(self, conn):
        self.conn = conn
        self.os_dao = OrdemServicoDAO(conn)
        self.servico_orcamento = ServicoOrcamento(conn)
        self.servico_relatorio = ServicoRelatorio(conn)
        self.seguranca = ServicoSeguranca()

    def historico_manutencao(self, veiculo_id=None, cliente_id=None):
        """RF33: OS de um veículo ou de um cliente, com diagnóstico e valor total."""
        lista = self.os_dao.get_lista(veiculo_id=veiculo_id, cliente_id=cliente_id)
        for os_ in lista:
            diag = self.os_dao.get_diagnostico(os_.id)
            os_.diagnostico = diag.descricao if diag else ""
            os_.total = self.servico_orcamento.calcular_total(os_.id)
        return lista

    def gerar(self, usuario, data_inicio="", data_fim=""):
        """RF34: relatório gerencial do período."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        return self.servico_relatorio.gerar(*periodo(data_inicio, data_fim))

    def linhas(self, relatorio):
        return self.servico_relatorio.linhas_relatorio(relatorio)

    def exportar_pdf(self, usuario, relatorio, caminho):
        """RF34 (A2): exporta o relatório em PDF."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        self.servico_relatorio.pdf_relatorio(caminho, relatorio)

    def painel(self):
        """RF35: quantidade de OS em andamento por etapa."""
        contagem = self.os_dao.contar_por_status()
        return [(StatusOS.NOMES[s], contagem.get(s, 0)) for s in StatusOS.EM_ANDAMENTO]

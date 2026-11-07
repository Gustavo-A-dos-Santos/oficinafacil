"""ServicoEstoque: verificação de disponibilidade (RF21) e baixa de estoque (RF24)."""
from ..modelo import RegraNegocioError
from ..persistencia.estoque_dao import EstoqueDAO
from ..persistencia.ordem_servico_dao import OrdemServicoDAO


class ServicoEstoque:

    def __init__(self, conn):
        self.os_dao = OrdemServicoDAO(conn)
        self.estoque_dao = EstoqueDAO(conn)

    def verificar_pecas(self, os_id):
        """Devolve [(peca_id, quantidade que falta)] das peças da OS sem estoque suficiente."""
        necessario = {}
        for item in self.os_dao.get_itens_peca(os_id):
            necessario[item.peca_id] = necessario.get(item.peca_id, 0) + item.quantidade
        faltas = []
        for peca_id, qtd in necessario.items():
            peca = self.estoque_dao.get_peca(peca_id)
            if not peca.verificar_disponibilidade(qtd):
                faltas.append((peca_id, qtd - peca.qtd_estoque))
        return faltas

    def baixar(self, os_id):
        """Tira do estoque todas as peças da OS (feito uma vez, ao registrar a execução)."""
        if self.verificar_pecas(os_id):
            raise RegraNegocioError("Não há estoque suficiente para as peças da OS. Registre uma solicitação de compra.")
        for item in self.os_dao.get_itens_peca(os_id):
            self.estoque_dao.somar_estoque(item.peca_id, -item.quantidade)

    def pecas_abaixo_do_minimo(self):
        return [p for p in self.estoque_dao.get_pecas() if p.abaixo_do_minimo()]

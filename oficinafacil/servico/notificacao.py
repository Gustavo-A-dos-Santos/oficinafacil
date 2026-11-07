"""ServicoNotificacao: avisos internos por perfil (RF10, RF15, RF28) e mensagem pronta ao cliente (RF29).

Os avisos são a lista "Minhas pendências" do painel: cada perfil vê as OS que esperam por ele.
"""
from ..modelo import moeda
from ..modelo.atendimento import StatusOS
from ..modelo.cadastro import Perfil
from ..persistencia.ordem_servico_dao import OrdemServicoDAO


class ServicoNotificacao:

    def __init__(self, conn):
        self.os_dao = OrdemServicoDAO(conn)

    def pendencias(self, usuario):
        if usuario.perfil == Perfil.MECANICO:
            # OS novas (ainda sem responsável) e as OS sob responsabilidade do mecânico
            return (self.os_dao.get_lista(StatusOS.ABERTA)
                    + self.os_dao.get_lista([StatusOS.EM_DIAGNOSTICO, StatusOS.EM_EXECUCAO], mecanico_id=usuario.id))
        if usuario.perfil == Perfil.GERENTE:
            return self.os_dao.get_lista([StatusOS.AGUARDANDO_GERENTE, StatusOS.AGUARDANDO_PECAS])
        return self.os_dao.get_lista([StatusOS.AGUARDANDO_CLIENTE, StatusOS.CONCLUIDA])

    def mensagem_cliente(self, os_, total):
        primeiro_nome = os_.cliente_nome.split()[0]
        return (f"Olá, {primeiro_nome}! O serviço no seu {os_.marca} {os_.modelo} (placa {os_.placa}) foi concluído "
                f"e o veículo já está disponível para retirada na OficinaFácil. Valor total: {moeda(total)}. "
                f"OS nº {os_.id}.")

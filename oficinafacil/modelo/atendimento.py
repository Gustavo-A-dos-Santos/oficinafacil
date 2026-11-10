"""Pacote modelo.atendimento: OrdemServico e suas partes, e as enumerações do atendimento."""


FORMAS_PAGAMENTO = ["Dinheiro", "PIX", "Cartão de débito", "Cartão de crédito"]


class StatusOS:
    ABERTA = "ABERTA"
    EM_DIAGNOSTICO = "EM_DIAGNOSTICO"
    AGUARDANDO_GERENTE = "AGUARDANDO_GERENTE"
    AGUARDANDO_CLIENTE = "AGUARDANDO_CLIENTE"
    AGUARDANDO_PECAS = "AGUARDANDO_PECAS"
    EM_EXECUCAO = "EM_EXECUCAO"
    CONCLUIDA = "CONCLUIDA"
    ENCERRADA = "ENCERRADA"
    CANCELADA = "CANCELADA"
    NOMES = {ABERTA: "Aberta", EM_DIAGNOSTICO: "Em diagnóstico", AGUARDANDO_GERENTE: "Aguardando gerente",
             AGUARDANDO_CLIENTE: "Aguardando cliente", AGUARDANDO_PECAS: "Aguardando peças",
             EM_EXECUCAO: "Em execução", CONCLUIDA: "Concluída", ENCERRADA: "Encerrada", CANCELADA: "Cancelada"}
    EM_ANDAMENTO = [ABERTA, EM_DIAGNOSTICO, AGUARDANDO_GERENTE, AGUARDANDO_CLIENTE, AGUARDANDO_PECAS,
                    EM_EXECUCAO, CONCLUIDA]


class SituacaoOrcamento:
    PENDENTE_APROVACAO = "PENDENTE_APROVACAO"
    ALTERADO = "ALTERADO"
    APROVADO_GERENTE = "APROVADO_GERENTE"
    APROVADO_CLIENTE = "APROVADO_CLIENTE"
    REJEITADO = "REJEITADO"


class SituacaoCompra:
    PENDENTE = "PENDENTE"
    COMPRADA = "COMPRADA"
    RECEBIDA = "RECEBIDA"
    CANCELADA = "CANCELADA"
    TODAS = [PENDENTE, COMPRADA, RECEBIDA, CANCELADA]
    NOMES = {PENDENTE: "Pendente", COMPRADA: "Comprada", RECEBIDA: "Recebida", CANCELADA: "Cancelada"}


class OrdemServico:
    def __init__(self, id=None, cliente_id=None, veiculo_id=None, usuario_abertura_id=None, mecanico_id=None,
                 problema="", km_entrada=None, status=StatusOS.ABERTA, data_abertura=None, data_execucao=None,
                 data_conclusao=None, data_aviso_cliente=None, motivo_cancelamento=None):
        self.id = id
        self.cliente_id = cliente_id
        self.veiculo_id = veiculo_id
        self.usuario_abertura_id = usuario_abertura_id  # atendente ou gerente que abriu
        self.mecanico_id = mecanico_id                  # mecânico responsável
        self.problema = problema
        self.km_entrada = km_entrada
        self.status = status
        self.data_abertura = data_abertura
        self.data_execucao = data_execucao              # execução registrada (RF26)
        self.data_conclusao = data_conclusao
        self.data_aviso_cliente = data_aviso_cliente    # aviso ao cliente (RF29)
        self.motivo_cancelamento = motivo_cancelamento  # rejeição do orçamento (RN09)
        # preenchidos nas consultas, para exibir nas telas
        self.cliente_nome = ""
        self.cliente_telefone = ""
        self.placa = ""
        self.marca = ""
        self.modelo = ""
        self.aberta_por = ""
        self.mecanico_nome = ""

    def nome_status(self):
        return StatusOS.NOMES[self.status]


class Diagnostico:
    def __init__(self, id=None, os_id=None, mecanico_id=None, descricao="", data=None):
        self.id = id
        self.os_id = os_id
        self.mecanico_id = mecanico_id
        self.descricao = descricao
        self.data = data


class ItemServicoOS:
    def __init__(self, id=None, os_id=None, servico_id=None, valor=0.0, quantidade=1, descricao=""):
        self.id = id
        self.os_id = os_id
        self.servico_id = servico_id
        self.valor = valor
        self.quantidade = quantidade
        self.descricao = descricao  # descrição do serviço do catálogo

    def subtotal(self):
        return self.valor * self.quantidade


class ItemPecaOS:
    def __init__(self, id=None, os_id=None, peca_id=None, quantidade=1, valor=0.0, destinacao_residuo=None,
                 descricao=""):
        self.id = id
        self.os_id = os_id
        self.peca_id = peca_id
        self.quantidade = quantidade
        self.valor = valor
        self.destinacao_residuo = destinacao_residuo  # RF25
        self.descricao = descricao

    def subtotal(self):
        return self.valor * self.quantidade


class Orcamento:
    def __init__(self, id=None, os_id=None, gerente_id=None, versao=1, valor_total=0.0,
                 situacao=SituacaoOrcamento.PENDENTE_APROVACAO, data=None, data_hora_decisao_cliente=None):
        self.id = id
        self.os_id = os_id
        self.gerente_id = gerente_id  # vazio enquanto pendente
        self.versao = versao
        self.valor_total = valor_total
        self.situacao = situacao
        self.data = data
        self.data_hora_decisao_cliente = data_hora_decisao_cliente
        self.gerente_nome = ""


class SolicitacaoCompra:
    def __init__(self, id=None, os_id=None, peca_id=None, fornecedor_id=None, quantidade=1,
                 situacao=SituacaoCompra.PENDENTE, solicitante_id=None, data_solicitacao=None, observacao=""):
        self.id = id
        self.os_id = os_id                  # vazio: compra para repor o estoque, sem OS
        self.peca_id = peca_id
        self.fornecedor_id = fornecedor_id  # vazio enquanto pendente
        self.quantidade = quantidade
        self.situacao = situacao
        self.solicitante_id = solicitante_id  # vazio quando a solicitação nasce da falta de peça na OS (RF21)
        self.data_solicitacao = data_solicitacao
        self.observacao = observacao or ""
        self.peca_descricao = ""
        self.fornecedor_nome = ""
        self.solicitante_nome = ""

    @property
    def origem(self):
        return f"OS {self.os_id}" if self.os_id else "Estoque"


class Pagamento:
    def __init__(self, id=None, os_id=None, valor=0.0, forma_pagamento="", data=None):
        self.id = id
        self.os_id = os_id
        self.valor = valor
        self.forma_pagamento = forma_pagamento
        self.data = data


class HistoricoStatus:
    def __init__(self, id=None, os_id=None, status="", usuario_id=None, data_hora=None):
        self.id = id
        self.os_id = os_id
        self.status = status
        self.usuario_id = usuario_id
        self.data_hora = data_hora
        self.usuario_nome = ""

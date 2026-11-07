"""Pacote modelo.catalogo: Servico, Peca e Fornecedor."""


class Servico:
    def __init__(self, id=None, descricao="", valor_base=0.0, ativo=True):
        self.id = id
        self.descricao = descricao
        self.valor_base = valor_base
        self.ativo = ativo


class Peca:
    def __init__(self, id=None, descricao="", valor=0.0, qtd_estoque=0, estoque_minimo=0):
        self.id = id
        self.descricao = descricao
        self.valor = valor
        self.qtd_estoque = qtd_estoque
        self.estoque_minimo = estoque_minimo

    def verificar_disponibilidade(self, qtd):
        return self.qtd_estoque >= qtd

    def abaixo_do_minimo(self):
        return self.qtd_estoque < self.estoque_minimo


class Fornecedor:
    def __init__(self, id=None, nome="", telefone="", email=""):
        self.id = id
        self.nome = nome
        self.telefone = telefone
        self.email = email

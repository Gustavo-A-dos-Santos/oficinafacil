"""Camada modelo: classes de domínio do diagrama de classes (item 7a).

Os objetos só guardam dados; quem grava e lê do banco são os DAOs (pacote persistencia).
"""


class RegraNegocioError(Exception):
    """Operação recusada por uma regra de negócio ou por um dado inválido."""


def moeda(valor):
    """1234.5 -> 'R$ 1.234,50'"""
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

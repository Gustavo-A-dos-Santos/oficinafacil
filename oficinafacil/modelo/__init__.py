"""Camada modelo: classes de domínio do diagrama de classes (item 7a).

Os objetos só guardam dados; quem grava e lê do banco são os DAOs (pacote persistencia).
"""


class RegraNegocioError(Exception):
    """Operação recusada por uma regra de negócio ou por um dado inválido."""


def moeda(valor):
    """1234.5 -> 'R$ 1.234,50'"""
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(valor, com_hora=False):
    """'2026-11-07 14:30:00' -> '07/11/2026' (ou '07/11/2026 14:30'); vazio continua vazio."""
    if not valor:
        return ""
    data, _, hora = str(valor).partition(" ")
    partes = data.split("-")
    if len(partes) != 3:
        return str(valor)
    texto = f"{partes[2]}/{partes[1]}/{partes[0]}"
    return f"{texto} {hora[:5]}" if com_hora and hora else texto

"""Camada persistencia: Conexao e os seis DAOs do diagrama de componentes (item 7b).

Os DAOs só executam SQL parametrizado (RNF03) e montam os objetos do modelo; não fazem commit.
Quem confirma ou desfaz a transação é o controlador que chamou (RNF06).
"""
from datetime import datetime


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

"""Camada persistencia: Conexao e os seis DAOs do diagrama de componentes (item 7b).

Os DAOs só executam SQL parametrizado (RNF03) e montam os objetos do modelo; não fazem commit.
Quem confirma ou desfaz a transação é o controlador que chamou (RNF06).
"""
import unicodedata
from datetime import datetime


def sem_acento(texto):
    """Texto em minúsculas e sem acentos, para pesquisar "oleo" e achar "Óleo"."""
    texto = unicodedata.normalize("NFD", str(texto or "")).lower()
    return "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

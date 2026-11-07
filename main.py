"""Ponto de entrada do OficinaFácil: python main.py"""
import os
import sys

from oficinafacil.apresentacao.app import App
from oficinafacil.persistencia.conexao import Conexao

if __name__ == "__main__":
    pasta = os.path.dirname(os.path.abspath(sys.argv[0]))
    conexao = Conexao(os.path.join(pasta, "oficinafacil.db"))
    conn = conexao.conectar()
    conexao.backup_diario(conn, os.path.join(pasta, "backups"))  # RNF05
    try:
        App(conn).executar()
    finally:
        conn.close()

"""Servidor central do OficinaFácil: python servidor.py [--host 192.168.0.10] [--porta 8765]

Roda num computador da oficina, guarda o banco (oficinafacil.db) e os backups e atende as estações da rede local.
Só aceita endereços privados (10.x, 172.16 a 172.31.x, 192.168.x) e o próprio computador.
"""
import argparse
import os
import sys
from datetime import datetime

from oficinafacil.controle.controladores import Controladores
from oficinafacil.comunicacao.protocolo import PORTA_PADRAO, ip_local
from oficinafacil.comunicacao.servidor import ServidorAplicacao
from oficinafacil.modelo import RegraNegocioError
from oficinafacil.persistencia.conexao import Conexao


def registrar(texto):
    print(f"[{datetime.now():%d/%m/%Y %H:%M:%S}] {texto}", flush=True)


if __name__ == "__main__":
    pasta = os.path.dirname(os.path.abspath(sys.argv[0]))
    args = argparse.ArgumentParser(description="Servidor central do OficinaFácil")
    args.add_argument("--host", default=ip_local(), help="endereço privado deste computador na rede da oficina")
    args.add_argument("--porta", type=int, default=PORTA_PADRAO)
    args.add_argument("--banco", default=os.path.join(pasta, "oficinafacil.db"))
    op = args.parse_args()
    conexao = Conexao(op.banco)
    conn = conexao.conectar(varias_linhas=True)
    registrar(f"Backup do dia: {conexao.backup_diario(conn, os.path.join(pasta, 'backups'))}")  # RNF05
    try:
        servidor = ServidorAplicacao(op.host, op.porta, Controladores(conn), registrar)
    except (RegraNegocioError, OSError) as e:
        registrar(f"Não foi possível iniciar: {e}")
        sys.exit(1)
    registrar(f"OficinaFácil no ar em {op.host}:{op.porta}. Nas estações, use este endereço no login.")
    registrar("Para desligar, feche esta janela ou tecle Ctrl+C.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        registrar("Servidor desligado.")
    finally:
        servidor.server_close()
        conn.close()

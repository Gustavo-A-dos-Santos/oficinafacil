"""Estação de trabalho do OficinaFácil: python main.py [--servidor 192.168.0.10:8765]

Abre a interface gráfica; os dados ficam no servidor central (servidor.py), na rede local da oficina.
O endereço do servidor é informado na tela de login (ou aqui) e fica salvo para as próximas vezes.
"""
import argparse

from oficinafacil.apresentacao.app import App

if __name__ == "__main__":
    args = argparse.ArgumentParser(description="Estação de trabalho do OficinaFácil")
    args.add_argument("--servidor", default="", help="endereço do servidor central, ex.: 192.168.0.10:8765")
    App(servidor=args.parse_args().servidor).executar()

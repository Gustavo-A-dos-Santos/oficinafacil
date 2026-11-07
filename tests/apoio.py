"""Pré-condições comuns dos testes: banco novo em memória, com os dados iniciais, e os sete controladores."""
import unittest

from oficinafacil.apresentacao.app import Controladores
from oficinafacil.persistencia.conexao import Conexao


class BaseTeste(unittest.TestCase):

    def setUp(self):
        self.conn = Conexao(":memory:").conectar()
        self.c = Controladores(self.conn)
        self.gerente = self.c.auth.autenticar("gerente", "123")
        self.atendente = self.c.auth.autenticar("atendente", "123")
        self.mecanico = self.c.auth.autenticar("mecanico", "123")

    def tearDown(self):
        self.conn.close()

    # atalhos para montar os cenários
    def status(self, os_id):
        return self.c.os.get_os(os_id).status

    def estoque(self, peca_id):
        return self.conn.execute("SELECT qtd_estoque FROM peca WHERE id = ?", (peca_id,)).fetchone()[0]

    def nova_os(self, problema="Barulho na suspensão", km=148600):
        return self.c.os.abrir_os(self.atendente, 1, 1, problema, km)

    def os_aguardando_gerente(self, servicos=((1, 1),), pecas=((1, 2),)):
        os_id = self.nova_os()
        self.c.os.classificar(self.atendente, os_id, False, self.mecanico.id)
        self.c.os.registrar_diagnostico(self.mecanico, os_id, "Amortecedores gastos", list(servicos), list(pecas))
        return os_id

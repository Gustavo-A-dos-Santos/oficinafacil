"""Testes das solicitações de compra com e sem OS, dos filtros e das permissões de quem pediu."""
import os
import sqlite3
import tempfile
import unittest

from apoio import BaseTeste
from oficinafacil.controle.controladores import Controladores
from oficinafacil.modelo import RegraNegocioError
from oficinafacil.modelo.atendimento import SituacaoCompra as SC
from oficinafacil.persistencia.conexao import Conexao


class TestesCompras(BaseTeste):

    def test_CT_U26_compra_para_estoque_sem_os(self):
        """RF22, RF23: atendente e mecânico pedem peça sem OS; ao receber, o estoque sobe e nenhuma OS muda."""
        antes = self.estoque(3)
        s1 = self.c.compras.solicitar_compra(self.atendente, None, 3, 5, "Repor para a semana")
        s2 = self.c.compras.solicitar_compra(self.mecanico, "", 4, 2)
        self.assertIsNone(s1.os_id)
        self.assertEqual(s1.solicitante_id, self.atendente.id)
        self.assertEqual(self.c.compras.get_solicitacoes(origem="ESTOQUE")[0].id, s2.id)   # mais recente primeiro
        self.c.compras.registrar_compra(self.gerente, s1.id, 1)
        self.c.compras.registrar_recebimento(self.gerente, s1.id)
        self.assertEqual(self.estoque(3), antes + 5)
        lida = self.c.compras.get_solicitacoes(SC.RECEBIDA)[0]
        self.assertEqual((lida.origem, lida.solicitante_nome, lida.observacao),
                         ("Estoque", "Ana Souza", "Repor para a semana"))

    def test_CT_U27_filtros_das_solicitacoes(self):
        """Filtros por situação, destino, peça, OS, fornecedor, solicitante e período."""
        os_id = self.nova_os()
        com_os = self.c.compras.solicitar_compra(self.mecanico, os_id, 1, 2)
        sem_os = self.c.compras.solicitar_compra(self.atendente, None, 2, 10)
        self.c.compras.registrar_compra(self.gerente, sem_os.id, 1)
        ids = lambda **f: [s.id for s in self.c.compras.get_solicitacoes(**f)]
        self.assertEqual(ids(origem="OS"), [com_os.id])
        self.assertEqual(ids(situacao=[SC.PENDENTE, SC.COMPRADA]), [sem_os.id, com_os.id])
        self.assertEqual(ids(situacao=SC.COMPRADA), [sem_os.id])
        self.assertEqual(ids(peca="amortecedor"), [com_os.id])
        self.assertEqual(ids(os_id=str(os_id)), [com_os.id])
        self.assertEqual(ids(fornecedor_id=1), [sem_os.id])
        self.assertEqual(ids(solicitante_id=self.atendente.id), [sem_os.id])
        self.assertEqual(ids(data_inicio="2000-01-01", data_fim="2000-01-31"), [])
        self.assertEqual(self.c.compras.resumo_solicitacoes(), {SC.PENDENTE: 1, SC.COMPRADA: 1, SC.RECEBIDA: 0,
                                                                 SC.CANCELADA: 0})
        with self.assertRaises(RegraNegocioError):
            self.c.compras.get_solicitacoes(os_id="abc")

    def test_CT_U28_quem_pediu_altera_e_cancela(self):
        """Quem pediu (ou o gerente) altera e cancela a solicitação pendente; os outros não."""
        s = self.c.compras.solicitar_compra(self.atendente, None, 2, 3)
        with self.assertRaises(RegraNegocioError):
            self.c.compras.alterar_solicitacao(self.mecanico, s.id, 9)
        self.c.compras.alterar_solicitacao(self.atendente, s.id, 6, "Urgente")
        self.assertEqual(self.c.compras.get_solicitacoes()[0].quantidade, 6)
        with self.assertRaises(RegraNegocioError):
            self.c.compras.cancelar_solicitacao(self.mecanico, s.id)
        self.c.compras.cancelar_solicitacao(self.atendente, s.id)
        self.assertEqual(self.c.compras.get_solicitacoes()[0].situacao, SC.CANCELADA)

    def test_CT_U29_pedido_repetido_e_os_encerrada(self):
        """Não aceita duas solicitações pendentes da mesma peça para o mesmo destino nem OS cancelada."""
        self.c.compras.solicitar_compra(self.atendente, None, 2, 3)
        with self.assertRaises(RegraNegocioError):
            self.c.compras.solicitar_compra(self.mecanico, None, 2, 1)
        os_id = self.nova_os()
        self.c.compras.solicitar_compra(self.mecanico, os_id, 2, 1)        # mesma peça, outro destino: aceita
        self.conn.execute("UPDATE ordem_servico SET status = ? WHERE id = ?", ("CANCELADA", os_id))
        with self.assertRaises(RegraNegocioError):
            self.c.compras.solicitar_compra(self.mecanico, os_id, 3, 1)

    def test_CT_U30_banco_antigo_atualizado(self):
        """Um banco criado antes (OS obrigatória na solicitação) é atualizado sem perder as solicitações."""
        caminho = os.path.join(tempfile.mkdtemp(), "antigo.db")
        conn = Conexao(caminho).conectar()
        c = Controladores(conn)
        os_id = c.os.abrir_os(c.auth.autenticar("atendente", "123"), 1, 1, "Teste", 150000)
        conn.close()
        bruto = sqlite3.connect(caminho)
        bruto.executescript(f"""
            DROP TABLE solicitacao_compra;
            CREATE TABLE solicitacao_compra (id INTEGER PRIMARY KEY, os_id INTEGER NOT NULL REFERENCES ordem_servico(id),
                peca_id INTEGER NOT NULL REFERENCES peca(id), fornecedor_id INTEGER REFERENCES fornecedor(id),
                quantidade INTEGER NOT NULL CHECK (quantidade > 0), situacao TEXT NOT NULL);
            INSERT INTO solicitacao_compra (os_id, peca_id, quantidade, situacao) VALUES ({os_id}, 1, 2, 'PENDENTE');""")
        bruto.commit()
        bruto.close()
        conn = Conexao(caminho).conectar()
        cols = {c["name"]: c["notnull"] for c in conn.execute("PRAGMA table_info(solicitacao_compra)")}
        self.assertEqual((cols["os_id"], "solicitante_id" in cols), (0, True))
        self.assertEqual(conn.execute("SELECT os_id, quantidade FROM solicitacao_compra").fetchone()[:], (os_id, 2))
        conn.close()


if __name__ == "__main__":
    unittest.main()

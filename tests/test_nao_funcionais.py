"""Testes de requisitos não funcionais (CT-N01 a CT-N05 do plano de testes)."""
import os
import tempfile
import time
import unittest

from apoio import BaseTeste
from oficinafacil.modelo import RegraNegocioError
from oficinafacil.modelo.atendimento import StatusOS
from oficinafacil.persistencia import agora
from oficinafacil.persistencia.conexao import Conexao


class TestNaoFuncionais(BaseTeste):

    def test_CT_N01_transacao_desfeita_em_erro(self):
        """RNF06: se o diagnóstico falha no meio, nada fica gravado."""
        os_id = self.nova_os()
        self.c.os.classificar(self.atendente, os_id, False, self.mecanico.id)
        with self.assertRaises(RegraNegocioError):
            self.c.os.registrar_diagnostico(self.mecanico, os_id, "Diag", [(1, 1)], [(999, 1)])  # peça inexistente
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM diagnostico").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM item_servico_os").fetchone()[0], 0)
        self.assertEqual(self.status(os_id), StatusOS.EM_DIAGNOSTICO)

    def test_CT_N02_sql_injection(self):
        """RNF03: entradas maliciosas são tratadas como texto (consultas parametrizadas)."""
        self.assertIsNone(self.c.auth.autenticar("' OR '1'='1", "' OR '1'='1"))
        self.assertEqual(self.c.cadastro.get_clientes("'; DROP TABLE cliente; --"), [])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cliente").fetchone()[0], 1)

    def test_CT_N03_rastreabilidade(self):
        """RNF09: toda mudança de status registra usuário, data e hora."""
        os_id = self.nova_os()
        self.c.os.classificar(self.mecanico, os_id, True, self.mecanico.id)
        hist = self.c.os.get_historico_status(os_id)
        self.assertEqual([(h.status, h.usuario_nome) for h in hist],
                         [(StatusOS.ABERTA, "Ana Souza"), (StatusOS.EM_EXECUCAO, "João Pereira")])
        self.assertTrue(all(h.data_hora for h in hist))

    def test_CT_N04_backup_diario(self):
        """RNF05: gera a cópia do dia, que abre e contém os dados."""
        arquivo = Conexao().backup_diario(self.conn, tempfile.mkdtemp())
        self.assertTrue(os.path.exists(arquivo))
        copia = Conexao(arquivo).conectar()
        self.assertEqual(copia.execute("SELECT COUNT(*) FROM usuario").fetchone()[0], 3)
        copia.close()

    def test_CT_N05_desempenho_com_10000_os(self):
        """RNF02, RNF10: com 10.000 OS, as consultas principais respondem em menos de 3 segundos."""
        data = agora()
        self.conn.executemany(
            "INSERT INTO ordem_servico (cliente_id, veiculo_id, usuario_abertura_id, problema, km_entrada, status, "
            "data_abertura) VALUES (1, 1, 2, ?, 1000, ?, ?)",
            [(f"Problema {i}", StatusOS.EM_ANDAMENTO[i % 7], data) for i in range(10_000)])
        self.conn.commit()
        consultas = [lambda: self.c.os.get_lista(self.gerente),
                     lambda: self.c.os.get_lista(self.gerente, status=StatusOS.ABERTA, placa="ABC"),
                     lambda: self.c.relatorio.painel(),
                     lambda: self.c.os.pendencias(self.atendente),
                     lambda: self.c.os.get_lista(self.mecanico)]
        for consulta in consultas:
            inicio = time.perf_counter()
            consulta()
            self.assertLess(time.perf_counter() - inicio, 3.0)


if __name__ == "__main__":
    unittest.main()

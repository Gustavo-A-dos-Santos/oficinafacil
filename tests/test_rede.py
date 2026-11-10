"""Testes da comunicação entre as estações e o servidor central (HTTP/JSON na rede local).

Cada teste sobe um servidor de verdade em 127.0.0.1 (porta livre), com banco novo em memória, e usa
ControladoresRemotos como as estações usam.
"""
import os
import tempfile
import unittest

from oficinafacil.controle.controladores import Controladores
from oficinafacil.comunicacao.cliente import ControladoresRemotos
from oficinafacil.comunicacao.protocolo import ErroConexao, endereco_privado
from oficinafacil.comunicacao.servidor import ServidorAplicacao, iniciar_em_segundo_plano
from oficinafacil.modelo import RegraNegocioError
from oficinafacil.modelo.atendimento import SituacaoCompra as SC, StatusOS as S
from oficinafacil.persistencia.conexao import Conexao


class BaseRede(unittest.TestCase):

    def setUp(self):
        self.conn = Conexao(":memory:").conectar(varias_linhas=True)
        self.servidor = iniciar_em_segundo_plano("127.0.0.1", 0, Controladores(self.conn))
        self.endereco = f"127.0.0.1:{self.servidor.server_address[1]}"

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.conn.close()

    def estacao(self, login):
        """Uma estação de trabalho com o usuário já autenticado."""
        ctrl = ControladoresRemotos(self.endereco)
        usuario = ctrl.auth.autenticar(login, "123")
        self.assertIsNotNone(usuario)
        return ctrl, usuario


class TestesIntegracaoRede(BaseRede):

    def test_CT_I05_duas_estacoes_na_mesma_os(self):
        """RF01, RF08, RF10: a OS aberta numa estação aparece nas pendências do mecânico em outra estação."""
        balcao, atendente = self.estacao("atendente")
        oficina, mecanico = self.estacao("mecanico")
        os_id = balcao.os.abrir_os(atendente, 1, 1, "Barulho no motor", 150000)
        self.assertIn(os_id, [o.id for o in oficina.os.pendencias(mecanico)])
        self.assertEqual(oficina.os.get_os(os_id).status, S.ABERTA)

    def test_CT_I06_ciclo_remoto_e_regra_de_negocio(self):
        """RF09 a RF32, RN07: o ciclo completo passa pelo servidor; a entrega sem pagamento volta como erro."""
        balcao, atendente = self.estacao("atendente")
        oficina, mecanico = self.estacao("mecanico")
        os_id = balcao.os.abrir_os(atendente, 1, 1, "Óleo vencido", 150000)
        oficina.os.classificar(mecanico, os_id, True, mecanico.id)          # serviço simples
        oficina.os.registrar_execucao(mecanico, os_id, [(2, 1)], [(2, 4)])
        oficina.os.concluir_servico(mecanico, os_id)
        with self.assertRaises(RegraNegocioError) as erro:
            balcao.pagamento.entregar_veiculo(atendente, os_id)
        self.assertIn("RN07", str(erro.exception))
        total = balcao.os.calcular_total(os_id)
        balcao.pagamento.registrar_pagamento(atendente, os_id, f"{total:.2f}".replace(".", ","), "PIX")
        balcao.pagamento.entregar_veiculo(atendente, os_id)
        self.assertEqual(balcao.os.get_os(os_id).status, S.ENCERRADA)

    def test_CT_I07_pdf_gerado_no_servidor(self):
        """RF17: o PDF do orçamento é gerado no servidor e gravado na estação."""
        balcao, atendente = self.estacao("atendente")
        oficina, mecanico = self.estacao("mecanico")
        gerencia, gerente = self.estacao("gerente")
        os_id = balcao.os.abrir_os(atendente, 1, 1, "Freio", 150000)
        oficina.os.classificar(mecanico, os_id, False, mecanico.id)
        oficina.os.registrar_diagnostico(mecanico, os_id, "Pastilhas", [(3, 1)], [(4, 1)])
        oficina.os.enviar_orcamento(mecanico, os_id)
        gerencia.orcamento.aprovar(gerente, os_id)
        caminho = os.path.join(tempfile.mkdtemp(), "orcamento.pdf")
        balcao.orcamento.exportar_pdf(os_id, caminho)
        with open(caminho, "rb") as f:
            self.assertEqual(f.read(5), b"%PDF-")

    def test_CT_I08_compra_sem_os_pela_rede(self):
        """RF22, RF23: o atendente pede peça para o estoque numa estação e o gerente filtra e recebe em outra."""
        balcao, atendente = self.estacao("atendente")
        gerencia, gerente = self.estacao("gerente")
        sol = balcao.compras.solicitar_compra(atendente, None, 3, 4, "Repor")
        lista = gerencia.compras.get_solicitacoes([SC.PENDENTE], None, "filtro", None, "ESTOQUE")
        self.assertEqual([(s.id, s.origem, s.solicitante_nome) for s in lista], [(sol.id, "Estoque", "Ana Souza")])
        gerencia.compras.registrar_compra(gerente, sol.id, 1)
        gerencia.compras.registrar_recebimento(gerente, sol.id)
        self.assertEqual(gerencia.compras.resumo_solicitacoes()[SC.RECEBIDA], 1)


class TestesNaoFuncionaisRede(BaseRede):

    def test_CT_N06_sessao_obrigatoria(self):
        """RNF03: sem login válido o servidor não executa nada."""
        estacao = ControladoresRemotos(self.endereco)
        self.assertIsNone(estacao.auth.autenticar("atendente", "errada"))
        with self.assertRaises(RegraNegocioError):
            estacao.cadastro.get_clientes()

    def test_CT_N07_somente_rede_local(self):
        """RNF15: servidor e estação só aceitam endereços privados da rede local."""
        self.assertTrue(endereco_privado("192.168.0.10"))
        self.assertTrue(endereco_privado("10.1.2.3"))
        self.assertTrue(endereco_privado("172.20.0.5"))
        self.assertFalse(endereco_privado("8.8.8.8"))
        with self.assertRaises(RegraNegocioError):
            ServidorAplicacao("8.8.8.8", 0, Controladores(self.conn))
        with self.assertRaises(RegraNegocioError):
            ControladoresRemotos("8.8.8.8:8765")

    def test_CT_N08_perfil_vem_da_sessao(self):
        """RNF03: o servidor usa o usuário da sessão; um usuário forjado pela estação não muda o perfil."""
        balcao, atendente = self.estacao("atendente")
        atendente.perfil = "GERENTE"                    # tentativa de se passar por gerente
        with self.assertRaises(RegraNegocioError):
            balcao.cadastro.salvar_servico(atendente, "Serviço forjado", "10", None)
        self.assertFalse(hasattr(atendente, "senha_hash"))   # o hash da senha não sai do servidor

    def test_CT_N09_servidor_fora_do_ar(self):
        """RNF05: com o servidor desligado, a estação mostra um aviso claro em vez de travar."""
        self.servidor.shutdown()
        self.servidor.server_close()
        estacao = ControladoresRemotos(self.endereco)
        with self.assertRaises(ErroConexao) as erro:
            estacao.auth.autenticar("atendente", "123")
        self.assertIn("Sem conexão com o servidor", str(erro.exception))
        self.servidor = iniciar_em_segundo_plano("127.0.0.1", 0, Controladores(self.conn))   # para o tearDown


if __name__ == "__main__":
    unittest.main()

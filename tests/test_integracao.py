"""Testes de integração: fluxos completos da OS passando por controladores, serviços, DAOs e banco
(CT-I01 a CT-I04). Seguem o diagrama de estados (item 5c) e o diagrama de tempo (item 6d, marcos t0 a t9)."""
import unittest

from apoio import BaseTeste
from oficinafacil.modelo import RegraNegocioError
from oficinafacil.modelo.atendimento import SituacaoCompra, SituacaoOrcamento, StatusOS as S


class TestFluxos(BaseTeste):

    def test_CT_I01_fluxo_completo_com_falta_de_peca(self):
        """RF08 a RF32: atendimento em que falta uma peça."""
        c = self.c
        os_id = c.os.abrir_os(self.atendente, 1, 1, "Barulho na suspensão dianteira", 148500)            # t0
        self.assertIn(os_id, [o.id for o in c.os.pendencias(self.mecanico)])                            # RF10
        c.os.classificar(self.atendente, os_id, False, self.mecanico.id)                                 # t1
        c.os.registrar_diagnostico(self.mecanico, os_id, "Amortecedores dianteiros desgastados",
                                   [(1, 1)], [(1, 2)])                                                    # t2
        self.assertEqual(self.status(os_id), S.AGUARDANDO_GERENTE)
        self.assertIn(os_id, [o.id for o in c.os.pendencias(self.gerente)])                             # RF15
        item_peca = c.os.get_itens(os_id)[1][0]
        c.orcamento.alterar_valor_item(self.gerente, os_id, "peca", item_peca.id, 265)
        c.orcamento.aprovar(self.gerente, os_id)                                                         # t3
        self.assertEqual(c.orcamento.registrar_decisao_cliente(self.atendente, os_id, True), S.AGUARDANDO_PECAS)  # t4
        sol = c.compras.get_solicitacoes(SituacaoCompra.PENDENTE)[0]
        self.assertEqual((sol.peca_id, sol.quantidade), (1, 2))
        c.compras.registrar_compra(self.gerente, sol.id, 1)                                              # t5
        c.compras.registrar_recebimento(self.gerente, sol.id)                                            # t6
        self.assertEqual((self.status(os_id), self.estoque(1)), (S.EM_EXECUCAO, 2))
        c.os.registrar_execucao(self.mecanico, os_id)                                                    # RF26
        self.assertEqual(self.estoque(1), 0)                                                             # RF24
        c.compras.registrar_destinacao(self.mecanico, item_peca.id, "Sucata metálica para reciclagem")   # RF25
        c.os.concluir_servico(self.mecanico, os_id)                                                      # t7
        self.assertIn(os_id, [o.id for o in c.os.pendencias(self.atendente)])                           # RF28
        self.assertIn("Carlos", c.os.gerar_mensagem(os_id))                                              # RF29
        c.os.registrar_aviso_cliente(self.atendente, os_id)
        with self.assertRaises(RegraNegocioError):                                                       # RF31
            c.pagamento.entregar_veiculo(self.atendente, os_id)
        c.pagamento.registrar_pagamento(self.atendente, os_id, "780,00", "PIX")                          # t8
        c.pagamento.entregar_veiculo(self.atendente, os_id)                                              # t9
        os_ = c.os.get_os(os_id)
        self.assertEqual(os_.status, S.ENCERRADA)
        self.assertTrue(os_.data_execucao and os_.data_conclusao and os_.data_aviso_cliente)
        esperado = [S.ABERTA, S.EM_DIAGNOSTICO, S.AGUARDANDO_GERENTE, S.AGUARDANDO_CLIENTE, S.AGUARDANDO_PECAS,
                    S.EM_EXECUCAO, S.CONCLUIDA, S.ENCERRADA]
        self.assertEqual([h.status for h in c.os.get_historico_status(os_id)], esperado)
        orc = c.orcamento.get_atual(os_id)
        self.assertEqual((orc.versao, orc.situacao, orc.gerente_id), (2, SituacaoOrcamento.APROVADO_CLIENTE, self.gerente.id))
        self.assertIsNotNone(orc.data_hora_decisao_cliente)

    def test_CT_I02_servico_simples_sem_orcamento(self):
        """RF09, RF26, RF30 a RF32, RN01, RN07: sem orçamento; pagamento parcial não libera a entrega."""
        c = self.c
        os_id = c.os.abrir_os(self.atendente, 1, 1, "Troca de óleo", 150000)
        c.os.classificar(self.mecanico, os_id, True, self.mecanico.id)
        self.assertEqual(self.status(os_id), S.EM_EXECUCAO)
        self.assertIsNone(c.orcamento.get_atual(os_id))
        c.os.registrar_execucao(self.mecanico, os_id, [(2, 1)], [(2, 4), (3, 1)])
        c.os.concluir_servico(self.mecanico, os_id)
        self.assertEqual((self.estoque(2), self.estoque(3)), (16, 5))
        self.assertEqual(c.os.calcular_total(os_id), 275.0)            # 60 + 4 x 45 + 35
        c.pagamento.registrar_pagamento(self.atendente, os_id, 200, "Dinheiro")
        with self.assertRaises(RegraNegocioError):
            c.pagamento.entregar_veiculo(self.atendente, os_id)
        c.pagamento.registrar_pagamento(self.atendente, os_id, 75, "PIX")
        c.pagamento.entregar_veiculo(self.atendente, os_id)
        self.assertEqual(self.status(os_id), S.ENCERRADA)

    def test_CT_I03_rejeicao_cancela_a_os(self):
        """RF18, RF20, RN09: cancelada com motivo, sem mexer no estoque."""
        c = self.c
        os_id = c.os.abrir_os(self.atendente, 1, 1, "Freio rangendo", 150000)
        c.os.classificar(self.atendente, os_id, False, self.mecanico.id)
        c.os.registrar_diagnostico(self.mecanico, os_id, "Pastilhas gastas", [(3, 1)], [(4, 1)])
        c.orcamento.aprovar(self.gerente, os_id)
        c.orcamento.registrar_decisao_cliente(self.atendente, os_id, False, "Achou caro")
        os_ = c.os.get_os(os_id)
        self.assertEqual((os_.status, os_.motivo_cancelamento), (S.CANCELADA, "Achou caro"))
        self.assertEqual(c.orcamento.get_atual(os_id).situacao, SituacaoOrcamento.REJEITADO)
        self.assertEqual(self.estoque(4), 4)

    def test_CT_I04_consultas_relatorio_e_painel(self):
        """RF13, RF33 a RF35."""
        self.test_CT_I02_servico_simples_sem_orcamento()
        c = self.c
        c.os.abrir_os(self.atendente, 1, 1, "Revisão", 151000)
        self.assertEqual(len(c.os.get_lista(self.atendente, placa="abc1")), 2)
        self.assertEqual(len(c.os.get_lista(self.atendente, status=S.ABERTA)), 1)
        historico = c.relatorio.historico_manutencao(veiculo_id=1)
        self.assertEqual((len(historico), historico[1].total), (2, 275.0))
        self.assertIn(("Aberta", 1), c.relatorio.painel())
        rel = c.relatorio.gerar(self.gerente)
        self.assertEqual((rel["faturamento"], rel["servicos"][0][0]), (275.0, "Troca de óleo"))


if __name__ == "__main__":
    unittest.main()

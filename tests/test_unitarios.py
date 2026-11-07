"""Testes unitários: cada regra de negócio isolada (CT-U01 a CT-U25 do plano de testes)."""
import os
import tempfile
import unittest

from apoio import BaseTeste
from oficinafacil.modelo import RegraNegocioError
from oficinafacil.modelo.atendimento import SituacaoCompra, SituacaoOrcamento, StatusOS
from oficinafacil.servico.seguranca import ServicoSeguranca


class TestSeguranca(BaseTeste):

    def test_CT_U01_hash_nao_guarda_senha_em_texto(self):
        """RNF03: a senha não aparece no hash, e a conferência acerta a certa e recusa a errada."""
        seg = ServicoSeguranca()
        h = seg.gerar_hash("segredo")
        self.assertNotIn("segredo", h)
        self.assertTrue(seg.conferir("segredo", h))
        self.assertFalse(seg.conferir("errada", h))

    def test_CT_U02_login_valido_e_invalido(self):
        """RF01."""
        self.assertEqual(self.gerente.perfil, "GERENTE")
        self.assertIsNone(self.c.auth.autenticar("gerente", "errada"))
        self.assertIsNone(self.c.auth.autenticar("naoexiste", "123"))

    def test_CT_U03_usuario_inativo_nao_entra(self):
        """RF02."""
        self.c.auth.alternar_ativo(self.gerente, self.atendente.id)
        self.assertIsNone(self.c.auth.autenticar("atendente", "123"))

    def test_CT_U04_perfil_sem_permissao(self):
        """RNF03: cada operação só para o perfil autorizado."""
        with self.assertRaises(RegraNegocioError):
            self.c.cadastro.salvar_servico(self.atendente, "Lavagem", 30)
        with self.assertRaises(RegraNegocioError):
            self.c.os.abrir_os(self.mecanico, 1, 1, "x", 1)


class TestCadastros(BaseTeste):

    def test_CT_U05_placa_unica(self):
        """RN08: a placa é única, mesmo digitada com hífen ou minúscula; a mensagem diz de quem é."""
        with self.assertRaises(RegraNegocioError) as erro:
            self.c.cadastro.salvar_veiculo(self.atendente, 1, "abc-1d23", "VW", "Gol")
        self.assertIn("Carlos Mendes", str(erro.exception))

    def test_CT_U06_campos_obrigatorios_e_cpf_opcional(self):
        """RF03, RNF04."""
        with self.assertRaises(RegraNegocioError):
            self.c.cadastro.salvar_cliente(self.atendente, "", "3499")
        cliente = self.c.cadastro.salvar_cliente(self.atendente, "Maria", "(34) 98888-0000")
        self.assertIsNone(self.c.cadastro.get_cliente(cliente.id).cpf)

    def test_CT_U07_valor_negativo_recusado(self):
        """RNF06."""
        with self.assertRaises(RegraNegocioError):
            self.c.cadastro.salvar_peca(self.gerente, "Vela", -5, 1, 1)

    def test_CT_U08_veiculo_de_outro_cliente(self):
        """RN08: o veículo da OS tem de ser do cliente da OS."""
        outro = self.c.cadastro.salvar_cliente(self.atendente, "Maria", "3499")
        with self.assertRaises(RegraNegocioError):
            self.c.os.abrir_os(self.atendente, outro.id, 1, "Freio", 1000)

    def test_CT_U17_cpf_repetido(self):
        """RF03 (A2): CPF já cadastrado mostra o cliente existente."""
        self.c.cadastro.salvar_cliente(self.atendente, "Maria", "3499", "111.222.333-44")
        with self.assertRaises(RegraNegocioError) as erro:
            self.c.cadastro.salvar_cliente(self.atendente, "Outra", "3498", "111.222.333-44")
        self.assertIn("Maria", str(erro.exception))

    def test_CT_U18_servico_com_valor_zero(self):
        """RF05 (A1): valor base tem de ser maior que zero."""
        with self.assertRaises(RegraNegocioError):
            self.c.cadastro.salvar_servico(self.gerente, "Cortesia", 0)


class TestOrdemServico(BaseTeste):

    def test_CT_U09_os_nasce_aberta_com_historico(self):
        """RF08, RF12."""
        os_id = self.nova_os()
        self.assertEqual(self.status(os_id), StatusOS.ABERTA)
        hist = self.c.os.get_historico_status(os_id)
        self.assertEqual((hist[0].status, hist[0].usuario_id), (StatusOS.ABERTA, self.atendente.id))

    def test_CT_U10_calculo_do_orcamento(self):
        """RF14: 1 x R$ 250,00 (serviço) + 2 x R$ 265,00 (peça) = R$ 780,00."""
        os_id = self.os_aguardando_gerente()
        self.assertEqual(self.c.os.calcular_total(os_id), 780.0)
        self.assertEqual(self.c.orcamento.get_atual(os_id).valor_total, 780.0)

    def test_CT_U11_alteracao_gera_nova_versao(self):
        """RF16, RN10."""
        os_id = self.os_aguardando_gerente()
        item = self.c.os.get_itens(os_id)[0][0]
        self.c.orcamento.alterar_valor_item(self.gerente, os_id, "servico", item.id, 200)
        versoes = self.c.orcamento.get_versoes(os_id)
        self.assertEqual([v.situacao for v in versoes], [SituacaoOrcamento.ALTERADO, SituacaoOrcamento.PENDENTE_APROVACAO])
        self.assertEqual(versoes[1].valor_total, 730.0)
        self.assertEqual(self.status(os_id), StatusOS.AGUARDANDO_GERENTE)

    def test_CT_U12_transicao_invalida(self):
        """RN02, RN03: não se aprova nem se conclui uma OS que acabou de abrir."""
        os_id = self.nova_os()
        with self.assertRaises(RegraNegocioError):
            self.c.orcamento.aprovar(self.gerente, os_id)
        with self.assertRaises(RegraNegocioError):
            self.c.os.concluir_servico(self.mecanico, os_id)
        self.assertEqual(self.status(os_id), StatusOS.ABERTA)

    def test_CT_U13_rejeicao_exige_motivo(self):
        """RF20, RN09."""
        os_id = self.os_aguardando_gerente()
        self.c.orcamento.aprovar(self.gerente, os_id)
        with self.assertRaises(RegraNegocioError):
            self.c.orcamento.registrar_decisao_cliente(self.atendente, os_id, False, "")

    def test_CT_U14_verificar_pecas(self):
        """RF21: amortecedor (id 1) tem 0 em estoque; óleo (id 2) tem 20."""
        os_id = self.os_aguardando_gerente(pecas=[(1, 2), (2, 4)])
        self.assertEqual(self.c.compras.verificar_pecas(os_id), [(1, 2)])

    def test_CT_U15_pdf_do_orcamento(self):
        """RF17, RN02: só depois de aprovado pelo gerente."""
        os_id = self.os_aguardando_gerente()
        caminho = os.path.join(tempfile.mkdtemp(), "orc.pdf")
        with self.assertRaises(RegraNegocioError):
            self.c.orcamento.exportar_pdf(os_id, caminho)
        self.c.orcamento.aprovar(self.gerente, os_id)
        self.c.orcamento.exportar_pdf(os_id, caminho)
        with open(caminho, "rb") as f:
            conteudo = f.read()
        self.assertTrue(conteudo.startswith(b"%PDF-1.4"))
        self.assertIn("780,00".encode(), conteudo)

    def test_CT_U16_gerente_tambem_abre_os(self):
        """RF08 (A19): o gerente também abre OS; o mecânico não."""
        os_id = self.c.os.abrir_os(self.gerente, 1, 1, "Revisão", 150000)
        self.assertEqual(self.c.os.get_os(os_id).usuario_abertura_id, self.gerente.id)
        with self.assertRaises(RegraNegocioError):
            self.c.os.abrir_os(self.mecanico, 1, 1, "Revisão", 150000)

    def test_CT_U19_concluir_exige_execucao_registrada(self):
        """RF27 (A1): sem registrar a execução (RF26), o serviço não pode ser concluído."""
        os_id = self.nova_os()
        self.c.os.classificar(self.mecanico, os_id, True, self.mecanico.id)
        with self.assertRaises(RegraNegocioError):
            self.c.os.concluir_servico(self.mecanico, os_id)

    def test_CT_U20_item_fora_do_orcamento(self):
        """RN10: com orçamento aprovado, a execução não aceita item a mais."""
        os_id = self.os_aguardando_gerente(pecas=[])
        self.c.orcamento.aprovar(self.gerente, os_id)
        self.c.orcamento.registrar_decisao_cliente(self.atendente, os_id, True)
        with self.assertRaises(RegraNegocioError):
            self.c.os.registrar_execucao(self.mecanico, os_id, [(2, 1)], [])

    def test_CT_U21_cancelar_solicitacao(self):
        """RF23 (A2): compra desistida fica Cancelada."""
        os_id = self.nova_os()
        sol = self.c.compras.solicitar_compra(self.mecanico, os_id, 1, 2)
        self.c.compras.cancelar_solicitacao(self.gerente, sol.id)
        self.assertEqual(self.c.compras.get_solicitacoes(SituacaoCompra.CANCELADA)[0].id, sol.id)

    def test_CT_U22_orcamento_so_vai_ao_gerente_ao_enviar(self):
        """RF11, RF14: o diagnóstico fica em preparação; só o envio do mecânico gera o orçamento."""
        os_id = self.nova_os()
        self.c.os.classificar(self.atendente, os_id, False, self.mecanico.id)
        self.c.os.registrar_diagnostico(self.mecanico, os_id, "Amortecedores gastos", [(1, 1)], [])
        self.assertEqual(self.status(os_id), StatusOS.EM_DIAGNOSTICO)
        self.assertIsNone(self.c.orcamento.get_atual(os_id))
        self.assertNotIn(os_id, [o.id for o in self.c.os.pendencias(self.gerente)])
        self.c.os.adicionar_itens(self.mecanico, os_id, [], [(1, 2)])
        self.c.os.enviar_orcamento(self.mecanico, os_id)
        self.assertEqual(self.status(os_id), StatusOS.AGUARDANDO_GERENTE)
        self.assertEqual(self.c.orcamento.get_atual(os_id).valor_total, 780.0)
        with self.assertRaises(RegraNegocioError):  # depois do envio, só o gerente muda os itens
            self.c.os.adicionar_itens(self.mecanico, os_id, [(2, 1)], [])

    def test_CT_U23_remover_item_e_envio_sem_servico(self):
        """RF11, RF14: item retirado antes do envio; orçamento sem serviço não é enviado."""
        os_id = self.nova_os()
        self.c.os.classificar(self.atendente, os_id, False, self.mecanico.id)
        with self.assertRaises(RegraNegocioError):  # sem diagnóstico não há o que enviar
            self.c.os.enviar_orcamento(self.mecanico, os_id)
        self.c.os.registrar_diagnostico(self.mecanico, os_id, "Amortecedores gastos", [(1, 1)], [(1, 2)])
        item = self.c.os.get_itens(os_id)[0][0]
        self.c.os.remover_item(self.mecanico, os_id, "servico", item.id)
        with self.assertRaises(RegraNegocioError):
            self.c.os.enviar_orcamento(self.mecanico, os_id)
        self.assertEqual(self.status(os_id), StatusOS.EM_DIAGNOSTICO)

    def test_CT_U24_pesquisar_pecas_e_servicos(self):
        """RF05, RF06: pesquisa por parte da descrição, sem diferenciar maiúsculas e acentos, ou pelo código."""
        pecas = self.c.cadastro.get_pecas("OLEO")
        self.assertTrue(pecas and all("óleo" in p.descricao.lower() for p in pecas))
        self.assertEqual([p.id for p in self.c.cadastro.get_pecas("1")][:1], [1])
        self.assertEqual([s.descricao for s in self.c.cadastro.get_servicos(busca="revisao")], ["Revisão de freios"])
        self.assertEqual(self.c.cadastro.get_servicos(busca="não existe"), [])

    def test_CT_U25_periodo_do_relatorio(self):
        """RF34: datas inválidas ou período invertido são recusados; o PDF sai com o período."""
        with self.assertRaises(RegraNegocioError):
            self.c.relatorio.gerar(self.gerente, "2026-13-01", "")
        with self.assertRaises(RegraNegocioError):
            self.c.relatorio.gerar(self.gerente, "2026-11-30", "2026-11-01")
        r = self.c.relatorio.gerar(self.gerente, "2026-11-01", "2026-11-30")
        caminho = os.path.join(tempfile.mkdtemp(), "rel.pdf")
        self.c.relatorio.exportar_pdf(self.gerente, r, caminho)
        with open(caminho, "rb") as f:
            conteudo = f.read()
        self.assertTrue(conteudo.startswith(b"%PDF-1.4"))
        self.assertIn(b"01/11/2026 a 30/11/2026", conteudo)


if __name__ == "__main__":
    unittest.main()

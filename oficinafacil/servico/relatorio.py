"""ServicoRelatorio: relatório gerencial (RF34) e exportação em PDF do orçamento (RF17) e do relatório."""
from ..modelo import data_br, moeda
from ..modelo.atendimento import StatusOS
from .pdf import DocumentoPDF


class ServicoRelatorio:

    def __init__(self, conn):
        self.conn = conn

    def gerar(self, data_inicio="", data_fim=""):
        """OS por status, serviços e peças mais usados, faturamento e tempo médio de atendimento."""
        filtro, args = "", []
        if data_inicio:
            filtro += " AND date(o.data_abertura) >= date(?)"
            args.append(data_inicio)
        if data_fim:
            filtro += " AND date(o.data_abertura) <= date(?)"
            args.append(data_fim)
        c = self.conn
        por_status = c.execute(f"SELECT o.status, COUNT(*) FROM ordem_servico o WHERE 1=1{filtro} GROUP BY o.status",
                               args).fetchall()
        servicos = c.execute("SELECT s.descricao, SUM(i.quantidade) AS qtd FROM item_servico_os i "
                             "JOIN servico s ON s.id = i.servico_id JOIN ordem_servico o ON o.id = i.os_id "
                             f"WHERE o.status = 'ENCERRADA'{filtro} GROUP BY s.id ORDER BY qtd DESC LIMIT 5", args).fetchall()
        pecas = c.execute("SELECT p.descricao, SUM(i.quantidade) AS qtd FROM item_peca_os i "
                          "JOIN peca p ON p.id = i.peca_id JOIN ordem_servico o ON o.id = i.os_id "
                          f"WHERE o.status = 'ENCERRADA'{filtro} GROUP BY p.id ORDER BY qtd DESC LIMIT 5", args).fetchall()
        faturamento = c.execute("SELECT IFNULL(SUM(p.valor), 0) FROM pagamento p JOIN ordem_servico o ON o.id = p.os_id "
                                f"WHERE 1=1{filtro}", args).fetchone()[0]
        horas = c.execute("SELECT AVG((julianday(o.data_conclusao) - julianday(o.data_abertura)) * 24) "
                          f"FROM ordem_servico o WHERE o.data_conclusao IS NOT NULL{filtro}", args).fetchone()[0]
        return {"data_inicio": data_inicio, "data_fim": data_fim, "por_status": [(StatusOS.NOMES[s], n) for s, n in por_status],
                "servicos": [tuple(l) for l in servicos], "pecas": [tuple(l) for l in pecas],
                "faturamento": round(faturamento, 2),
                "tempo_medio_horas": round(horas, 1) if horas is not None else None}

    def linhas_relatorio(self, r):
        """Texto do relatório, usado na tela e no PDF."""
        de, ate = data_br(r.get("data_inicio")) or "início", data_br(r.get("data_fim")) or "hoje"
        linhas = ["RELATÓRIO GERENCIAL", f"Período: {de} a {ate}", "", "OS por status:"]
        linhas += [f"   {nome:<22}{n:>5}" for nome, n in r["por_status"]] or ["   (nenhuma)"]
        tm = r["tempo_medio_horas"]
        linhas += ["", f"Faturamento (pagamentos recebidos): {moeda(r['faturamento'])}",
                   f"Tempo médio de atendimento (abertura até conclusão): {'-' if tm is None else f'{tm} horas'}",
                   "", "Serviços mais realizados (OS encerradas):"]
        linhas += [f"   {d:<35}{q:>5}" for d, q in r["servicos"]] or ["   (nenhum)"]
        linhas += ["", "Peças mais utilizadas (OS encerradas):"]
        linhas += [f"   {d:<35}{q:>5}" for d, q in r["pecas"]] or ["   (nenhuma)"]
        return linhas

    def pdf_orcamento(self, caminho, os_, orcamento, itens_servico, itens_peca, diagnostico=None):
        """RF17: orçamento para o cliente, com os dados da OS, os itens, os totais e as assinaturas."""
        doc = DocumentoPDF("Orçamento", f"OS nº {os_.id}  ·  versão {orcamento.versao}")
        doc.secao("Dados do atendimento")
        doc.campos([("Cliente", os_.cliente_nome), ("Telefone", os_.cliente_telefone),
                    ("Veículo", f"{os_.marca} {os_.modelo}"), ("Placa e quilometragem", f"{os_.placa}  ·  {os_.km_entrada or 0:,} km".replace(",", ".")),
                    ("Data do orçamento", data_br(orcamento.data, True)), ("Mecânico responsável", os_.mecanico_nome)])
        doc.secao("Problema relatado")
        doc.paragrafo(os_.problema)
        if diagnostico:
            doc.secao("Diagnóstico")
            doc.paragrafo(diagnostico.descricao)
        colunas = [("Descrição", 6, "esquerda"), ("Qtd.", 1, "direita"), ("Valor unitário", 2, "direita"),
                   ("Subtotal", 2, "direita")]
        total_servicos = sum(i.subtotal() for i in itens_servico)
        total_pecas = sum(i.subtotal() for i in itens_peca)
        doc.secao("Serviços")
        doc.tabela(colunas, [(i.descricao, i.quantidade, moeda(i.valor), moeda(i.subtotal())) for i in itens_servico],
                   "Nenhum serviço.")
        doc.secao("Peças")
        doc.tabela(colunas, [(i.descricao, i.quantidade, moeda(i.valor), moeda(i.subtotal())) for i in itens_peca],
                   "Nenhuma peça.")
        doc.totais([("Serviços", moeda(total_servicos)), ("Peças", moeda(total_pecas))],
                   ("TOTAL", moeda(orcamento.valor_total)))
        doc.paragrafo("Os valores consideram as peças e os serviços listados acima. Qualquer item a mais será "
                      "informado em um novo orçamento, para nova aprovação.", 8.5, (0.45, 0.45, 0.45))
        doc.assinaturas(["Assinatura do cliente", "OficinaFácil"])
        doc.salvar(caminho)

    def pdf_relatorio(self, caminho, r):
        """RF34: relatório gerencial do período, com indicadores e gráficos de barras."""
        de, ate = data_br(r.get("data_inicio")), data_br(r.get("data_fim"))
        periodo = (f"{de} a {ate}" if de and ate else f"a partir de {de}" if de else f"até {ate}" if ate
                   else "todo o período")
        doc = DocumentoPDF("Relatório gerencial", f"Período: {periodo}")
        tm = r["tempo_medio_horas"]
        doc.cartoes([("OS abertas no período", str(sum(n for _, n in r["por_status"]))),
                     ("Faturamento recebido", moeda(r["faturamento"])),
                     ("Tempo médio de atendimento", "-" if tm is None else f"{tm} h")])
        doc.secao("Ordens de serviço por status")
        doc.barras(r["por_status"], "Nenhuma OS no período.")
        doc.secao("Serviços mais realizados (OS encerradas)")
        doc.tabela([("Serviço", 8, "esquerda"), ("Quantidade", 2, "direita")], r["servicos"], "Nenhum serviço.")
        doc.secao("Peças mais utilizadas (OS encerradas)")
        doc.tabela([("Peça", 8, "esquerda"), ("Quantidade", 2, "direita")], r["pecas"], "Nenhuma peça.")
        doc.paragrafo("Faturamento: soma dos pagamentos das OS abertas no período. Tempo médio: da abertura até a "
                      "conclusão do serviço.", 8.5, (0.45, 0.45, 0.45))
        doc.salvar(caminho)

"""ServicoRelatorio: relatório gerencial (RF34) e exportação em PDF do orçamento (RF17) e do relatório."""
from ..modelo import moeda
from ..modelo.atendimento import StatusOS


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
        return {"por_status": [(StatusOS.NOMES[s], n) for s, n in por_status],
                "servicos": [tuple(l) for l in servicos], "pecas": [tuple(l) for l in pecas],
                "faturamento": round(faturamento, 2),
                "tempo_medio_horas": round(horas, 1) if horas is not None else None}

    def linhas_relatorio(self, r):
        """Texto do relatório, usado na tela e no PDF."""
        linhas = ["RELATÓRIO GERENCIAL", "", "OS por status:"]
        linhas += [f"   {nome:<22}{n:>5}" for nome, n in r["por_status"]] or ["   (nenhuma)"]
        tm = r["tempo_medio_horas"]
        linhas += ["", f"Faturamento (pagamentos recebidos): {moeda(r['faturamento'])}",
                   f"Tempo médio de atendimento (abertura até conclusão): {'-' if tm is None else f'{tm} horas'}",
                   "", "Serviços mais realizados (OS encerradas):"]
        linhas += [f"   {d:<35}{q:>5}" for d, q in r["servicos"]] or ["   (nenhum)"]
        linhas += ["", "Peças mais utilizadas (OS encerradas):"]
        linhas += [f"   {d:<35}{q:>5}" for d, q in r["pecas"]] or ["   (nenhuma)"]
        return linhas

    def linhas_orcamento(self, os_, orcamento, itens_servico, itens_peca):
        linhas = ["OficinaFácil - Orçamento", "",
                  f"OS nº {os_.id}    Versão do orçamento: {orcamento.versao}    Data: {orcamento.data}",
                  f"Cliente: {os_.cliente_nome}    Telefone: {os_.cliente_telefone}",
                  f"Veículo: {os_.marca} {os_.modelo}    Placa: {os_.placa}    Km: {os_.km_entrada}",
                  f"Problema relatado: {os_.problema}", "", "Serviços:"]
        for i in itens_servico:
            linhas.append(f"   {i.quantidade} x {i.descricao}  ({moeda(i.valor)})  = {moeda(i.subtotal())}")
        linhas.append("Peças:")
        for i in itens_peca:
            linhas.append(f"   {i.quantidade} x {i.descricao}  ({moeda(i.valor)})  = {moeda(i.subtotal())}")
        linhas += ["", f"TOTAL: {moeda(orcamento.valor_total)}", "",
                   "Assinatura do cliente: ______________________________________"]
        return linhas

    def escrever_pdf(self, caminho, linhas):
        """PDF A4 só com texto (Helvetica 11, até 60 linhas por página), sem bibliotecas externas."""
        paginas = [linhas[i:i + 60] for i in range(0, max(len(linhas), 1), 60)] or [[]]
        kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(paginas)))
        objetos = [b"<< /Type /Catalog /Pages 2 0 R >>",
                   f"<< /Type /Pages /Kids [{kids}] /Count {len(paginas)} >>".encode(),
                   b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
        for i, pagina in enumerate(paginas):
            fluxo = ["BT", "/F1 11 Tf", "14 TL", "50 800 Td"]
            for linha in pagina:
                texto = linha.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                fluxo.append(f"({texto}) Tj T*")
            fluxo.append("ET")
            dados = "\n".join(fluxo).encode("cp1252", errors="replace")
            objetos.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                           f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>".encode())
            objetos.append(f"<< /Length {len(dados)} >>\nstream\n".encode() + dados + b"\nendstream")
        saida = bytearray(b"%PDF-1.4\n")
        posicoes = []
        for n, obj in enumerate(objetos, start=1):
            posicoes.append(len(saida))
            saida += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
        inicio_xref = len(saida)
        saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
        for p in posicoes:
            saida += f"{p:010d} 00000 n \n".encode()
        saida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
        with open(caminho, "wb") as f:
            f.write(saida)

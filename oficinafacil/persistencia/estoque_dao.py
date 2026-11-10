"""EstoqueDAO: CRUD do catálogo (servico, peca), dos fornecedores e das solicitações de compra."""
from ..modelo.atendimento import SolicitacaoCompra
from ..modelo.catalogo import Fornecedor, Peca, Servico
from . import agora, sem_acento


class EstoqueDAO:

    def __init__(self, conn):
        self.conn = conn

    # ---------------------------------------------------------------- serviço
    def salvar_servico(self, s):
        s.id = self.conn.execute("INSERT INTO servico (descricao, valor_base) VALUES (?,?)",
                                 (s.descricao, s.valor_base)).lastrowid
        return s

    def editar_servico(self, s):
        self.conn.execute("UPDATE servico SET descricao = ?, valor_base = ? WHERE id = ?", (s.descricao, s.valor_base, s.id))

    def alternar_ativo_servico(self, id):
        self.conn.execute("UPDATE servico SET ativo = 1 - ativo WHERE id = ?", (id,))

    def get_servico(self, id):
        rs = self.conn.execute("SELECT * FROM servico WHERE id = ?", (id,)).fetchone()
        return Servico(rs["id"], rs["descricao"], rs["valor_base"], bool(rs["ativo"])) if rs else None

    def get_servicos(self, so_ativos=False, busca=""):
        """busca: parte da descrição (sem diferenciar maiúsculas nem acentos) ou o código."""
        sql, args = "SELECT * FROM servico WHERE 1=1", []
        if so_ativos:
            sql += " AND ativo = 1"
        if busca:
            sql += " AND (sem_acento(descricao) LIKE ? OR CAST(id AS TEXT) = ?)"
            args += [f"%{sem_acento(busca)}%", busca]
        return [Servico(rs["id"], rs["descricao"], rs["valor_base"], bool(rs["ativo"]))
                for rs in self.conn.execute(sql + " ORDER BY descricao", args)]

    # ---------------------------------------------------------------- peça e estoque
    def salvar_peca(self, p):
        p.id = self.conn.execute("INSERT INTO peca (descricao, valor, qtd_estoque, estoque_minimo) VALUES (?,?,?,?)",
                                 (p.descricao, p.valor, p.qtd_estoque, p.estoque_minimo)).lastrowid
        return p

    def editar_peca(self, p):
        self.conn.execute("UPDATE peca SET descricao = ?, valor = ?, qtd_estoque = ?, estoque_minimo = ? WHERE id = ?",
                          (p.descricao, p.valor, p.qtd_estoque, p.estoque_minimo, p.id))

    def somar_estoque(self, peca_id, quantidade):
        """Entrada (quantidade positiva) ou baixa (negativa) no estoque da peça."""
        self.conn.execute("UPDATE peca SET qtd_estoque = qtd_estoque + ? WHERE id = ?", (quantidade, peca_id))

    def get_peca(self, id):
        rs = self.conn.execute("SELECT * FROM peca WHERE id = ?", (id,)).fetchone()
        return self._montar_peca(rs) if rs else None

    def get_pecas(self, busca=""):
        """busca: parte da descrição (sem diferenciar maiúsculas nem acentos) ou o código."""
        sql, args = "SELECT * FROM peca", []
        if busca:
            sql += " WHERE sem_acento(descricao) LIKE ? OR CAST(id AS TEXT) = ?"
            args = [f"%{sem_acento(busca)}%", busca]
        return [self._montar_peca(rs) for rs in self.conn.execute(sql + " ORDER BY descricao", args)]

    def _montar_peca(self, rs):
        return Peca(rs["id"], rs["descricao"], rs["valor"], rs["qtd_estoque"], rs["estoque_minimo"])

    # ---------------------------------------------------------------- fornecedor
    def salvar_fornecedor(self, f):
        f.id = self.conn.execute("INSERT INTO fornecedor (nome, telefone, email) VALUES (?,?,?)",
                                 (f.nome, f.telefone, f.email)).lastrowid
        return f

    def editar_fornecedor(self, f):
        self.conn.execute("UPDATE fornecedor SET nome = ?, telefone = ?, email = ? WHERE id = ?",
                          (f.nome, f.telefone, f.email, f.id))

    def get_fornecedor(self, id):
        rs = self.conn.execute("SELECT * FROM fornecedor WHERE id = ?", (id,)).fetchone()
        return Fornecedor(rs["id"], rs["nome"], rs["telefone"], rs["email"]) if rs else None

    def get_fornecedores(self):
        return [Fornecedor(rs["id"], rs["nome"], rs["telefone"], rs["email"])
                for rs in self.conn.execute("SELECT * FROM fornecedor ORDER BY nome")]

    # ---------------------------------------------------------------- solicitação de compra
    def salvar_solicitacao(self, s):
        s.data_solicitacao = s.data_solicitacao or agora()
        s.id = self.conn.execute("INSERT INTO solicitacao_compra (os_id, peca_id, quantidade, situacao, solicitante_id, "
                                 "data_solicitacao, observacao) VALUES (?,?,?,?,?,?,?)",
                                 (s.os_id, s.peca_id, s.quantidade, s.situacao, s.solicitante_id, s.data_solicitacao,
                                  s.observacao)).lastrowid
        return s

    def editar_solicitacao(self, s):
        self.conn.execute("UPDATE solicitacao_compra SET fornecedor_id = ?, situacao = ?, quantidade = ?, observacao = ? "
                          "WHERE id = ?", (s.fornecedor_id, s.situacao, s.quantidade, s.observacao, s.id))

    def get_solicitacao(self, id):
        rs = self.conn.execute(self.SQL_SOLICITACAO + " WHERE s.id = ?", (id,)).fetchone()
        return self._montar_solicitacao(rs) if rs else None

    def get_solicitacoes(self, situacao=None, os_id=None, peca="", fornecedor_id=None, origem=None, data_inicio="",
                         data_fim="", solicitante_id=None, peca_id=None):
        """Filtros combináveis: situação (uma ou várias), OS, peça (descrição ou código), fornecedor, origem
        ("OS" ou "ESTOQUE"), período da solicitação e solicitante. As mais recentes vêm primeiro."""
        sql, args = self.SQL_SOLICITACAO + " WHERE 1=1", []
        if situacao:
            lista = situacao if isinstance(situacao, (list, tuple)) else [situacao]
            sql += f" AND s.situacao IN ({','.join('?' * len(lista))})"
            args += list(lista)
        if peca:
            sql += " AND (sem_acento(p.descricao) LIKE ? OR CAST(p.id AS TEXT) = ?)"
            args += [f"%{sem_acento(peca)}%", str(peca).strip()]
        if origem == "OS":
            sql += " AND s.os_id IS NOT NULL"
        elif origem == "ESTOQUE":
            sql += " AND s.os_id IS NULL"
        if data_inicio:
            sql += " AND date(s.data_solicitacao) >= date(?)"
            args.append(data_inicio)
        if data_fim:
            sql += " AND date(s.data_solicitacao) <= date(?)"
            args.append(data_fim)
        for campo, valor in (("s.os_id", os_id), ("s.fornecedor_id", fornecedor_id),
                             ("s.solicitante_id", solicitante_id), ("s.peca_id", peca_id)):
            if valor:
                sql += f" AND {campo} = ?"
                args.append(valor)
        return [self._montar_solicitacao(rs) for rs in self.conn.execute(sql + " ORDER BY s.id DESC", args)]

    def contar_solicitacoes(self):
        """Quantidade de solicitações por situação."""
        return {rs[0]: rs[1] for rs in
                self.conn.execute("SELECT situacao, COUNT(*) FROM solicitacao_compra GROUP BY situacao")}

    SQL_SOLICITACAO = ("SELECT s.*, p.descricao AS peca_descricao, f.nome AS fornecedor_nome, u.nome AS solicitante_nome "
                       "FROM solicitacao_compra s JOIN peca p ON p.id = s.peca_id "
                       "LEFT JOIN fornecedor f ON f.id = s.fornecedor_id LEFT JOIN usuario u ON u.id = s.solicitante_id")

    def _montar_solicitacao(self, rs):
        s = SolicitacaoCompra(rs["id"], rs["os_id"], rs["peca_id"], rs["fornecedor_id"], rs["quantidade"], rs["situacao"],
                              rs["solicitante_id"], rs["data_solicitacao"], rs["observacao"])
        s.peca_descricao, s.fornecedor_nome = rs["peca_descricao"], rs["fornecedor_nome"] or ""
        s.solicitante_nome = rs["solicitante_nome"] or ("Sistema (falta de peça)" if s.os_id else "")
        return s

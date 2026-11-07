"""OrcamentoDAO: CRUD da tabela orcamento (versões do orçamento de cada OS)."""
from ..modelo.atendimento import Orcamento


class OrcamentoDAO:

    def __init__(self, conn):
        self.conn = conn

    def salvar(self, o):
        cur = self.conn.execute("INSERT INTO orcamento (os_id, versao, valor_total, situacao, data) VALUES (?,?,?,?,?)",
                                (o.os_id, o.versao, o.valor_total, o.situacao, o.data))
        o.id = cur.lastrowid
        return o

    def editar(self, o):
        self.conn.execute("UPDATE orcamento SET gerente_id = ?, situacao = ?, data_hora_decisao_cliente = ? WHERE id = ?",
                          (o.gerente_id, o.situacao, o.data_hora_decisao_cliente, o.id))

    def get_atual(self, os_id):
        """A versão mais recente do orçamento da OS (ou None, se a OS não tem orçamento)."""
        lista = self.get_versoes(os_id)
        return lista[-1] if lista else None

    def get_versoes(self, os_id):
        lista = []
        for rs in self.conn.execute("SELECT o.*, u.nome AS gerente_nome FROM orcamento o "
                                    "LEFT JOIN usuario u ON u.id = o.gerente_id WHERE os_id = ? ORDER BY versao",
                                    (os_id,)):
            o = Orcamento(rs["id"], rs["os_id"], rs["gerente_id"], rs["versao"], rs["valor_total"], rs["situacao"],
                          rs["data"], rs["data_hora_decisao_cliente"])
            o.gerente_nome = rs["gerente_nome"] or ""
            lista.append(o)
        return lista

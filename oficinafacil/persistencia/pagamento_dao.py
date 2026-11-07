"""PagamentoDAO: CRUD da tabela pagamento."""
from ..modelo.atendimento import Pagamento


class PagamentoDAO:

    def __init__(self, conn):
        self.conn = conn

    def salvar(self, p):
        p.id = self.conn.execute("INSERT INTO pagamento (os_id, valor, forma_pagamento, data) VALUES (?,?,?,?)",
                                 (p.os_id, p.valor, p.forma_pagamento, p.data)).lastrowid
        return p

    def get_pagamentos(self, os_id):
        return [Pagamento(rs["id"], rs["os_id"], rs["valor"], rs["forma_pagamento"], rs["data"])
                for rs in self.conn.execute("SELECT * FROM pagamento WHERE os_id = ? ORDER BY id", (os_id,))]

    def get_total_pago(self, os_id):
        return round(self.conn.execute("SELECT IFNULL(SUM(valor), 0) FROM pagamento WHERE os_id = ?",
                                       (os_id,)).fetchone()[0], 2)

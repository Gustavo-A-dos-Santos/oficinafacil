"""OrdemServicoDAO: CRUD de ordem_servico e das suas partes (diagnostico, itens e historico_status)."""
from ..modelo.atendimento import Diagnostico, HistoricoStatus, ItemPecaOS, ItemServicoOS, OrdemServico


class OrdemServicoDAO:

    SQL_OS = ("SELECT o.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone, v.placa, v.marca, v.modelo, "
              "a.nome AS aberta_por, m.nome AS mecanico_nome "
              "FROM ordem_servico o JOIN cliente c ON c.id = o.cliente_id JOIN veiculo v ON v.id = o.veiculo_id "
              "JOIN usuario a ON a.id = o.usuario_abertura_id LEFT JOIN usuario m ON m.id = o.mecanico_id")

    def __init__(self, conn):
        self.conn = conn

    # ---------------------------------------------------------------- ordem de serviço
    def salvar(self, os_):
        cur = self.conn.execute(
            "INSERT INTO ordem_servico (cliente_id, veiculo_id, usuario_abertura_id, problema, km_entrada, status, "
            "data_abertura) VALUES (?,?,?,?,?,?,?)",
            (os_.cliente_id, os_.veiculo_id, os_.usuario_abertura_id, os_.problema, os_.km_entrada, os_.status,
             os_.data_abertura))
        os_.id = cur.lastrowid
        return os_

    def editar(self, os_):
        self.conn.execute(
            "UPDATE ordem_servico SET mecanico_id = ?, status = ?, data_execucao = ?, data_conclusao = ?, "
            "data_aviso_cliente = ?, motivo_cancelamento = ? WHERE id = ?",
            (os_.mecanico_id, os_.status, os_.data_execucao, os_.data_conclusao, os_.data_aviso_cliente,
             os_.motivo_cancelamento, os_.id))

    def get_os(self, id):
        rs = self.conn.execute(self.SQL_OS + " WHERE o.id = ?", (id,)).fetchone()
        return self._montar(rs) if rs else None

    def get_lista(self, status=None, cliente="", placa="", data_inicio="", data_fim="", mecanico_id=None,
                  veiculo_id=None, cliente_id=None):
        """RF13 e RF33: filtra por status (um ou vários), cliente, placa, período, mecânico, veículo ou cliente."""
        sql, args = self.SQL_OS + " WHERE 1=1", []
        if status:
            lista = status if isinstance(status, (list, tuple)) else [status]
            sql += f" AND o.status IN ({','.join('?' * len(lista))})"
            args += list(lista)
        if cliente:
            sql += " AND c.nome LIKE ?"
            args.append(f"%{cliente}%")
        if placa:
            sql += " AND v.placa LIKE ?"
            args.append(f"%{placa.upper()}%")
        if data_inicio:
            sql += " AND date(o.data_abertura) >= date(?)"
            args.append(data_inicio)
        if data_fim:
            sql += " AND date(o.data_abertura) <= date(?)"
            args.append(data_fim)
        for campo, valor in (("o.mecanico_id", mecanico_id), ("o.veiculo_id", veiculo_id), ("o.cliente_id", cliente_id)):
            if valor:
                sql += f" AND {campo} = ?"
                args.append(valor)
        return [self._montar(rs) for rs in self.conn.execute(sql + " ORDER BY o.id DESC", args)]

    def contar_por_status(self):
        return dict(self.conn.execute("SELECT status, COUNT(*) FROM ordem_servico GROUP BY status").fetchall())

    def _montar(self, rs):
        os_ = OrdemServico(rs["id"], rs["cliente_id"], rs["veiculo_id"], rs["usuario_abertura_id"], rs["mecanico_id"],
                           rs["problema"], rs["km_entrada"], rs["status"], rs["data_abertura"], rs["data_execucao"],
                           rs["data_conclusao"], rs["data_aviso_cliente"], rs["motivo_cancelamento"])
        os_.cliente_nome, os_.cliente_telefone = rs["cliente_nome"], rs["cliente_telefone"]
        os_.placa, os_.marca, os_.modelo = rs["placa"], rs["marca"], rs["modelo"]
        os_.aberta_por, os_.mecanico_nome = rs["aberta_por"], rs["mecanico_nome"] or ""
        return os_

    # ---------------------------------------------------------------- histórico de status (RF12, RNF09)
    def salvar_historico(self, h):
        cur = self.conn.execute("INSERT INTO historico_status (os_id, status, usuario_id, data_hora) VALUES (?,?,?,?)",
                                (h.os_id, h.status, h.usuario_id, h.data_hora))
        h.id = cur.lastrowid
        return h

    def get_historico(self, os_id):
        lista = []
        for rs in self.conn.execute("SELECT h.*, u.nome AS usuario_nome FROM historico_status h "
                                    "JOIN usuario u ON u.id = h.usuario_id WHERE os_id = ? ORDER BY h.id", (os_id,)):
            h = HistoricoStatus(rs["id"], rs["os_id"], rs["status"], rs["usuario_id"], rs["data_hora"])
            h.usuario_nome = rs["usuario_nome"]
            lista.append(h)
        return lista

    # ---------------------------------------------------------------- diagnóstico
    def salvar_diagnostico(self, d):
        cur = self.conn.execute("INSERT INTO diagnostico (os_id, mecanico_id, descricao, data) VALUES (?,?,?,?)",
                                (d.os_id, d.mecanico_id, d.descricao, d.data))
        d.id = cur.lastrowid
        return d

    def get_diagnostico(self, os_id):
        rs = self.conn.execute("SELECT * FROM diagnostico WHERE os_id = ?", (os_id,)).fetchone()
        return Diagnostico(rs["id"], rs["os_id"], rs["mecanico_id"], rs["descricao"], rs["data"]) if rs else None

    # ---------------------------------------------------------------- itens de serviço e de peça
    def salvar_item_servico(self, i):
        cur = self.conn.execute("INSERT INTO item_servico_os (os_id, servico_id, valor, quantidade) VALUES (?,?,?,?)",
                                (i.os_id, i.servico_id, i.valor, i.quantidade))
        i.id = cur.lastrowid
        return i

    def salvar_item_peca(self, i):
        cur = self.conn.execute("INSERT INTO item_peca_os (os_id, peca_id, quantidade, valor) VALUES (?,?,?,?)",
                                (i.os_id, i.peca_id, i.quantidade, i.valor))
        i.id = cur.lastrowid
        return i

    def editar_valor_item(self, tabela, item_id, os_id, valor):
        """Muda o valor unitário de um item da OS; devolve quantas linhas mudaram (0 se o item não é da OS)."""
        tabela = {"servico": "item_servico_os", "peca": "item_peca_os"}[tabela]
        return self.conn.execute(f"UPDATE {tabela} SET valor = ? WHERE id = ? AND os_id = ?",
                                 (valor, item_id, os_id)).rowcount

    def editar_destinacao(self, item_peca_id, destino):
        return self.conn.execute("UPDATE item_peca_os SET destinacao_residuo = ? WHERE id = ?",
                                 (destino, item_peca_id)).rowcount

    def get_itens_servico(self, os_id):
        return [ItemServicoOS(rs["id"], rs["os_id"], rs["servico_id"], rs["valor"], rs["quantidade"], rs["descricao"])
                for rs in self.conn.execute("SELECT i.*, s.descricao FROM item_servico_os i "
                                            "JOIN servico s ON s.id = i.servico_id WHERE os_id = ?", (os_id,))]

    def get_itens_peca(self, os_id):
        return [ItemPecaOS(rs["id"], rs["os_id"], rs["peca_id"], rs["quantidade"], rs["valor"],
                           rs["destinacao_residuo"], rs["descricao"])
                for rs in self.conn.execute("SELECT i.*, p.descricao FROM item_peca_os i "
                                            "JOIN peca p ON p.id = i.peca_id WHERE os_id = ?", (os_id,))]

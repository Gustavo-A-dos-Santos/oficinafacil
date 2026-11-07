"""ClienteVeiculoDAO: CRUD das tabelas cliente e veiculo."""
from ..modelo.cadastro import Cliente, Veiculo


class ClienteVeiculoDAO:

    def __init__(self, conn):
        self.conn = conn

    # ---------------------------------------------------------------- cliente
    def salvar_cliente(self, c):
        cur = self.conn.execute("INSERT INTO cliente (nome, telefone, cpf, email) VALUES (?,?,?,?)",
                                (c.nome, c.telefone, c.cpf, c.email))
        c.id = cur.lastrowid
        return c

    def editar_cliente(self, c):
        self.conn.execute("UPDATE cliente SET nome = ?, telefone = ?, cpf = ?, email = ? WHERE id = ?",
                          (c.nome, c.telefone, c.cpf, c.email, c.id))

    def alternar_ativo_cliente(self, id):
        self.conn.execute("UPDATE cliente SET ativo = 1 - ativo WHERE id = ?", (id,))

    def get_cliente(self, id):
        rs = self.conn.execute("SELECT * FROM cliente WHERE id = ?", (id,)).fetchone()
        return self._montar_cliente(rs) if rs else None

    def get_cliente_por_cpf(self, cpf):
        rs = self.conn.execute("SELECT * FROM cliente WHERE cpf = ?", (cpf,)).fetchone()
        return self._montar_cliente(rs) if rs else None

    def get_clientes(self, busca="", so_ativos=False):
        sql = "SELECT * FROM cliente WHERE (nome LIKE ? OR telefone LIKE ? OR IFNULL(cpf, '') LIKE ?)"
        if so_ativos:
            sql += " AND ativo = 1"
        b = f"%{busca}%"
        return [self._montar_cliente(rs) for rs in self.conn.execute(sql + " ORDER BY nome", (b, b, b))]

    def _montar_cliente(self, rs):
        return Cliente(rs["id"], rs["nome"], rs["telefone"], rs["cpf"], rs["email"], bool(rs["ativo"]))

    # ---------------------------------------------------------------- veiculo
    def salvar_veiculo(self, v):
        cur = self.conn.execute("INSERT INTO veiculo (cliente_id, placa, marca, modelo, ano, km) VALUES (?,?,?,?,?,?)",
                                (v.cliente_id, v.placa, v.marca, v.modelo, v.ano, v.km))
        v.id = cur.lastrowid
        return v

    def editar_veiculo(self, v):
        self.conn.execute("UPDATE veiculo SET cliente_id = ?, placa = ?, marca = ?, modelo = ?, ano = ?, km = ? "
                          "WHERE id = ?", (v.cliente_id, v.placa, v.marca, v.modelo, v.ano, v.km, v.id))

    def atualizar_km(self, id, km):
        # só aumenta: a quilometragem de entrada de uma OS nova não pode diminuir o km do veículo
        self.conn.execute("UPDATE veiculo SET km = ? WHERE id = ? AND (km IS NULL OR km < ?)", (km, id, km))

    def get_veiculo(self, id):
        rs = self.conn.execute(self.SQL_VEICULO + " WHERE v.id = ?", (id,)).fetchone()
        return self._montar_veiculo(rs) if rs else None

    def get_veiculo_por_placa(self, placa):
        rs = self.conn.execute(self.SQL_VEICULO + " WHERE v.placa = ?", (placa,)).fetchone()
        return self._montar_veiculo(rs) if rs else None

    def get_veiculos(self, cliente_id=None, busca=""):
        sql = self.SQL_VEICULO + " WHERE (v.placa LIKE ? OR v.modelo LIKE ? OR c.nome LIKE ?)"
        b = f"%{busca}%"
        args = [b, b, b]
        if cliente_id:
            sql += " AND v.cliente_id = ?"
            args.append(cliente_id)
        return [self._montar_veiculo(rs) for rs in self.conn.execute(sql + " ORDER BY v.placa", args)]

    SQL_VEICULO = "SELECT v.*, c.nome AS cliente_nome FROM veiculo v JOIN cliente c ON c.id = v.cliente_id"

    def _montar_veiculo(self, rs):
        v = Veiculo(rs["id"], rs["cliente_id"], rs["placa"], rs["marca"], rs["modelo"], rs["ano"], rs["km"])
        v.cliente_nome = rs["cliente_nome"]
        return v

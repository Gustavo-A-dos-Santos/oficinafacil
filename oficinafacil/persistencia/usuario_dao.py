"""UsuarioDAO: CRUD da tabela usuario."""
from ..modelo.cadastro import Usuario


class UsuarioDAO:

    def __init__(self, conn):
        self.conn = conn

    def salvar(self, u):
        cur = self.conn.execute("INSERT INTO usuario (nome, login, senha_hash, perfil) VALUES (?,?,?,?)",
                                (u.nome, u.login, u.senha_hash, u.perfil))
        u.id = cur.lastrowid
        return u

    def editar(self, u):
        self.conn.execute("UPDATE usuario SET nome = ?, login = ?, perfil = ? WHERE id = ?",
                          (u.nome, u.login, u.perfil, u.id))

    def alterar_senha(self, id, senha_hash):
        self.conn.execute("UPDATE usuario SET senha_hash = ? WHERE id = ?", (senha_hash, id))

    def alternar_ativo(self, id):
        self.conn.execute("UPDATE usuario SET ativo = 1 - ativo WHERE id = ?", (id,))

    def get_usuario(self, id):
        rs = self.conn.execute("SELECT * FROM usuario WHERE id = ?", (id,)).fetchone()
        return self._montar(rs) if rs else None

    def get_usuario_por_login(self, login):
        rs = self.conn.execute("SELECT * FROM usuario WHERE login = ?", (login,)).fetchone()
        return self._montar(rs) if rs else None

    def get_usuarios(self, perfil=None, so_ativos=False):
        sql, args = "SELECT * FROM usuario WHERE 1=1", []
        if perfil:
            sql += " AND perfil = ?"
            args.append(perfil)
        if so_ativos:
            sql += " AND ativo = 1"
        return [self._montar(rs) for rs in self.conn.execute(sql + " ORDER BY nome", args)]

    def _montar(self, rs):
        return Usuario(rs["id"], rs["nome"], rs["login"], rs["perfil"], bool(rs["ativo"]), rs["senha_hash"])

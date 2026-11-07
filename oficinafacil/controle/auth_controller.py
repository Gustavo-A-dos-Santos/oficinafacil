"""AuthController: login (RF01) e manutenção de usuários e perfis (RF02)."""
from ..modelo import RegraNegocioError
from ..modelo.cadastro import Perfil, Usuario
from ..persistencia.usuario_dao import UsuarioDAO
from ..servico.seguranca import ServicoSeguranca
from . import obrigatorio, transacao


class AuthController:

    def __init__(self, conn):
        self.conn = conn
        self.usuario_dao = UsuarioDAO(conn)
        self.seguranca = ServicoSeguranca()

    def autenticar(self, login, senha):
        """RF01: devolve o usuário ou None se o login/senha estiverem errados ou o usuário estiver inativo."""
        u = self.usuario_dao.get_usuario_por_login(login)
        if u and u.ativo and self.seguranca.conferir(senha, u.senha_hash):
            return u
        return None

    @transacao
    def salvar_usuario(self, usuario, nome, login, perfil, senha=None, id=None):
        """RF02: cadastra (id vazio) ou altera um funcionário. Na alteração, senha vazia mantém a atual."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        u = Usuario(id, obrigatorio(nome, "nome"), obrigatorio(login, "login"), perfil)
        if perfil not in Perfil.TODOS:
            raise RegraNegocioError("Selecione o perfil.")
        outro = self.usuario_dao.get_usuario_por_login(u.login)
        if outro and outro.id != id:
            raise RegraNegocioError("Já existe um usuário com esse login.")
        if id is None:
            u.senha_hash = self.seguranca.gerar_hash(obrigatorio(senha, "senha"))
            return self.usuario_dao.salvar(u)
        self.usuario_dao.editar(u)
        if senha:
            self.usuario_dao.alterar_senha(id, self.seguranca.gerar_hash(senha))
        return u

    @transacao
    def alternar_ativo(self, usuario, id):
        """RF02: inativa ou reativa um funcionário (o inativo não entra, mas o histórico é mantido)."""
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        if id == usuario.id:
            raise RegraNegocioError("Você não pode inativar o próprio usuário.")
        self.usuario_dao.alternar_ativo(id)

    def get_usuarios(self, perfil=None, so_ativos=False):
        return self.usuario_dao.get_usuarios(perfil, so_ativos)

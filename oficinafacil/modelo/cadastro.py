"""Pacote modelo.cadastro: Usuario (e perfis), Cliente e Veiculo."""


class Perfil:
    ATENDENTE = "ATENDENTE"
    MECANICO = "MECANICO"
    GERENTE = "GERENTE"
    TODOS = [ATENDENTE, MECANICO, GERENTE]
    NOMES = {ATENDENTE: "Atendente", MECANICO: "Mecânico", GERENTE: "Gerente"}


class Usuario:
    """Funcionário. Atendente, Mecânico e Gerente são o mesmo objeto, diferenciados pelo perfil."""

    def __init__(self, id=None, nome="", login="", perfil="", ativo=True, senha_hash=""):
        self.id = id
        self.nome = nome
        self.login = login
        self.perfil = perfil
        self.ativo = ativo
        self.senha_hash = senha_hash

    def tem_perfil(self, *perfis):
        return self.perfil in perfis


class Cliente:
    def __init__(self, id=None, nome="", telefone="", cpf=None, email=None, ativo=True):
        self.id = id
        self.nome = nome
        self.telefone = telefone
        self.cpf = cpf  # opcional (LGPD)
        self.email = email
        self.ativo = ativo


class Veiculo:
    def __init__(self, id=None, cliente_id=None, placa="", marca="", modelo="", ano=None, km=None):
        self.id = id
        self.cliente_id = cliente_id
        self.placa = placa  # única (RN08)
        self.marca = marca
        self.modelo = modelo
        self.ano = ano
        self.km = km
        self.cliente_nome = ""  # preenchido nas consultas com o nome do dono

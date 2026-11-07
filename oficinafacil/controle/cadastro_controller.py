"""CadastroController: clientes (RF03), veículos (RF04), serviços (RF05), peças (RF06) e fornecedores (RF07)."""
from ..modelo import RegraNegocioError
from ..modelo.cadastro import Cliente, Perfil, Veiculo
from ..modelo.catalogo import Fornecedor, Peca, Servico
from ..persistencia.cliente_veiculo_dao import ClienteVeiculoDAO
from ..persistencia.estoque_dao import EstoqueDAO
from ..servico.seguranca import ServicoSeguranca
from . import inteiro, obrigatorio, transacao, valor_monetario


class CadastroController:

    def __init__(self, conn):
        self.conn = conn
        self.cv_dao = ClienteVeiculoDAO(conn)
        self.estoque_dao = EstoqueDAO(conn)
        self.seguranca = ServicoSeguranca()

    # ---------------------------------------------------------------- RF03 clientes
    @transacao
    def salvar_cliente(self, usuario, nome, telefone, cpf="", email="", id=None):
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE, Perfil.GERENTE)
        c = Cliente(id, obrigatorio(nome, "nome"), obrigatorio(telefone, "telefone"),
                    (cpf or "").strip() or None, (email or "").strip() or None)  # CPF opcional (RNF04)
        if c.cpf:
            outro = self.cv_dao.get_cliente_por_cpf(c.cpf)
            if outro and outro.id != id:
                raise RegraNegocioError(f"O CPF {c.cpf} já está cadastrado para o cliente {outro.nome} "
                                        f"(código {outro.id}).")
        if id is None:
            return self.cv_dao.salvar_cliente(c)
        self.cv_dao.editar_cliente(c)
        return c

    @transacao
    def alternar_ativo_cliente(self, usuario, id):
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE, Perfil.GERENTE)
        self.cv_dao.alternar_ativo_cliente(id)

    def get_clientes(self, busca="", so_ativos=False):
        return self.cv_dao.get_clientes(busca, so_ativos)

    def get_cliente(self, id):
        return self.cv_dao.get_cliente(id)

    # ---------------------------------------------------------------- RF04 veículos
    @transacao
    def salvar_veiculo(self, usuario, cliente_id, placa, marca, modelo, ano="", km="", id=None):
        self.seguranca.exigir_perfil(usuario, Perfil.ATENDENTE, Perfil.GERENTE)
        if not self.cv_dao.get_cliente(cliente_id):
            raise RegraNegocioError("Selecione o cliente dono do veículo (RN08).")
        placa = obrigatorio(placa, "placa").upper().replace("-", "").replace(" ", "")
        outro = self.cv_dao.get_veiculo_por_placa(placa)
        if outro and outro.id != id:
            raise RegraNegocioError(f"A placa {placa} já está cadastrada para o cliente {outro.cliente_nome} (RN08).")
        v = Veiculo(id, cliente_id, placa, obrigatorio(marca, "marca"), obrigatorio(modelo, "modelo"),
                    inteiro(ano, "ano", 1900) if str(ano).strip() else None,
                    inteiro(km, "quilometragem") if str(km).strip() else None)
        if id is None:
            return self.cv_dao.salvar_veiculo(v)
        self.cv_dao.editar_veiculo(v)
        return v

    def get_veiculos(self, cliente_id=None, busca=""):
        return self.cv_dao.get_veiculos(cliente_id, busca)

    def get_veiculo(self, id):
        return self.cv_dao.get_veiculo(id)

    # ---------------------------------------------------------------- RF05 serviços
    @transacao
    def salvar_servico(self, usuario, descricao, valor_base, id=None):
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        s = Servico(id, obrigatorio(descricao, "descrição"), valor_monetario(valor_base, "valor base", positivo=True))
        if id is None:
            return self.estoque_dao.salvar_servico(s)
        self.estoque_dao.editar_servico(s)
        return s

    @transacao
    def alternar_ativo_servico(self, usuario, id):
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        self.estoque_dao.alternar_ativo_servico(id)

    def get_servicos(self, so_ativos=False):
        return self.estoque_dao.get_servicos(so_ativos)

    # ---------------------------------------------------------------- RF06 peças
    @transacao
    def salvar_peca(self, usuario, descricao, valor, qtd_estoque, estoque_minimo, id=None):
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        p = Peca(id, obrigatorio(descricao, "descrição"), valor_monetario(valor, "valor"),
                 inteiro(qtd_estoque, "quantidade em estoque"), inteiro(estoque_minimo, "estoque mínimo"))
        if id is None:
            return self.estoque_dao.salvar_peca(p)
        self.estoque_dao.editar_peca(p)
        return p

    def get_pecas(self):
        return self.estoque_dao.get_pecas()

    # ---------------------------------------------------------------- RF07 fornecedores
    @transacao
    def salvar_fornecedor(self, usuario, nome, telefone="", email="", id=None):
        self.seguranca.exigir_perfil(usuario, Perfil.GERENTE)
        f = Fornecedor(id, obrigatorio(nome, "nome"), (telefone or "").strip(), (email or "").strip())
        if id is None:
            return self.estoque_dao.salvar_fornecedor(f)
        self.estoque_dao.editar_fornecedor(f)
        return f

    def get_fornecedores(self):
        return self.estoque_dao.get_fornecedores()

"""Os sete controladores reunidos, como o servidor central (e os testes) os usam."""
from .auth_controller import AuthController
from .cadastro_controller import CadastroController
from .orcamento_controller import OrcamentoController
from .os_controller import OSController
from .pagamento_controller import PagamentoController
from .pecas_compras_controller import PecasComprasController
from .relatorio_controller import RelatorioController


class Controladores:
    """Os sete controladores do diagrama de componentes (como os BO de cada formulário), sobre uma conexão."""

    def __init__(self, conn):
        self.auth = AuthController(conn)
        self.cadastro = CadastroController(conn)
        self.os = OSController(conn)
        self.orcamento = OrcamentoController(conn)
        self.compras = PecasComprasController(conn)
        self.pagamento = PagamentoController(conn)
        self.relatorio = RelatorioController(conn)

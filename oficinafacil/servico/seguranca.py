"""ServicoSeguranca: hash de senha (PBKDF2-SHA256 com sal) e controle de acesso por perfil (RNF03)."""
import hashlib
import hmac
import os

from ..modelo import RegraNegocioError
from ..modelo.cadastro import Perfil


class ServicoSeguranca:

    ITERACOES = 100_000

    def gerar_hash(self, senha):
        sal = os.urandom(16)
        h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, self.ITERACOES)
        return sal.hex() + "$" + h.hex()

    def conferir(self, senha, senha_hash):
        sal_hex, h_hex = senha_hash.split("$")
        h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal_hex), self.ITERACOES)
        return hmac.compare_digest(h.hex(), h_hex)

    def exigir_perfil(self, usuario, *perfis):
        if not usuario.tem_perfil(*perfis):
            nomes = ", ".join(Perfil.NOMES[p] for p in perfis)
            raise RegraNegocioError(f"Operação permitida apenas para: {nomes}.")

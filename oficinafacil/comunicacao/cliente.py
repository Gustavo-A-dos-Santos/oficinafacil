"""Lado da estação: imita os sete controladores e envia cada chamada ao servidor central.

As telas usam ControladoresRemotos do mesmo jeito que usariam os controladores locais (ctrl.os.abrir_os(...)),
e uma regra de negócio violada no servidor volta aqui como RegraNegocioError.
"""
import base64
import json
import urllib.error
import urllib.request

from ..modelo import RegraNegocioError
from .protocolo import ErroConexao, codificar, decodificar, separar_endereco

TEMPO_LIMITE = 20   # segundos


class ClienteAPI:
    def __init__(self, endereco):
        self.host, self.porta = separar_endereco(endereco)
        self.base = f"http://{self.host}:{self.porta}/api"
        self.chave = None

    def _pedido(self, caminho, dados=None, metodo="POST"):
        corpo = codificar(dados) if dados is not None else None
        req = urllib.request.Request(self.base + caminho, data=corpo, method=metodo,
                                     headers={"Content-Type": "application/json"})
        if self.chave:
            req.add_header("Authorization", "Bearer " + self.chave)
        try:
            with urllib.request.urlopen(req, timeout=TEMPO_LIMITE) as resp:
                return decodificar(resp.read())
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode("utf-8")).get("erro", "")
            except ValueError:
                msg = ""
            finally:
                e.close()
            if e.code == 401 and caminho == "/entrar":
                return None
            raise RegraNegocioError(msg or f"O servidor recusou o pedido (código {e.code}).")
        except (urllib.error.URLError, OSError):
            raise ErroConexao(f"Sem conexão com o servidor {self.host}:{self.porta}. Confira se ele está ligado e "
                              "se este computador está na rede da oficina.")

    def status(self):
        return self._pedido("/status", metodo="GET")

    def entrar(self, login, senha):
        r = self._pedido("/entrar", {"login": login, "senha": senha})
        if not r:
            return None
        self.chave = r["chave"]
        return r["usuario"]

    def sair(self):
        if self.chave:
            try:
                self._pedido("/sair", {})
            except RegraNegocioError:
                pass
            self.chave = None

    def chamar(self, controlador, metodo, args, kwargs):
        return self._pedido("/chamar", {"controlador": controlador, "metodo": metodo, "args": list(args),
                                        "kwargs": kwargs})["resultado"]


class _Proxy:
    def __init__(self, api, nome):
        self._api, self._nome = api, nome

    def __getattr__(self, metodo):
        if metodo.startswith("_"):
            raise AttributeError(metodo)

        def chamada(*args, **kwargs):
            if metodo == "exportar_pdf":
                caminho = args[-1]
                r = self._api.chamar(self._nome, metodo, list(args[:-1]) + [""], kwargs)
                with open(caminho, "wb") as f:
                    f.write(base64.b64decode(r["__arquivo__"]))
                return None
            return self._api.chamar(self._nome, metodo, args, kwargs)
        return chamada


class _AuthRemoto(_Proxy):
    def autenticar(self, login, senha):
        return self._api.entrar(login, senha)


class ControladoresRemotos:
    """Mesma interface da classe Controladores, mas cada chamada vai ao servidor central."""

    def __init__(self, endereco):
        self.api = ClienteAPI(endereco)
        self.auth = _AuthRemoto(self.api, "auth")
        for nome in ("cadastro", "os", "orcamento", "compras", "pagamento", "relatorio"):
            setattr(self, nome, _Proxy(self.api, nome))

    @property
    def endereco(self):
        return f"{self.api.host}:{self.api.porta}"

    def sair(self):
        self.api.sair()

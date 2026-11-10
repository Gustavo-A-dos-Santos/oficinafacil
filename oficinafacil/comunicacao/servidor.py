"""Servidor de aplicação central: recebe as chamadas das estações (HTTP/JSON) e executa os controladores.

O servidor é o único que abre o banco SQLite. Cada pedido roda numa linha de execução própria, e as operações
passam uma de cada vez pelo banco (trava), o que mantém as transações íntegras com várias estações ao mesmo tempo.
"""
import base64
import os
import secrets
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..modelo import RegraNegocioError
from .protocolo import VERSAO, codificar, decodificar, endereco_privado

CONTROLADORES = ("auth", "cadastro", "os", "orcamento", "compras", "pagamento", "relatorio")
LIMITE_CORPO = 1_000_000                 # bytes por pedido
DURACAO_SESSAO = 12 * 3600               # segundos sem uso até a sessão expirar


class Sessoes:
    """Sessões abertas: chave -> (usuário, último uso)."""

    def __init__(self):
        self.abertas, self.trava = {}, threading.Lock()

    def abrir(self, usuario):
        chave = secrets.token_urlsafe(32)
        with self.trava:
            self.abertas[chave] = [usuario, time.time()]
        return chave

    def usuario(self, chave):
        with self.trava:
            item = self.abertas.get(chave)
            if not item or time.time() - item[1] > DURACAO_SESSAO:
                self.abertas.pop(chave, None)
                return None
            item[1] = time.time()
            return item[0]

    def fechar(self, chave):
        with self.trava:
            self.abertas.pop(chave, None)


class ServidorAplicacao(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, host, porta, controladores, registrar=print):
        if not endereco_privado(host):
            raise RegraNegocioError(f"O servidor só pode usar um endereço privado da rede local (recebido: {host}).")
        self.ctrl, self.registrar = controladores, registrar
        self.sessoes, self.trava_banco = Sessoes(), threading.Lock()
        super().__init__((host, porta), Manipulador)


class Manipulador(BaseHTTPRequestHandler):
    server_version = "OficinaFacil/" + VERSAO

    def log_message(self, formato, *args):
        self.server.registrar(f"{self.client_address[0]} - {formato % args}")

    def _responder(self, codigo, dados):
        corpo = codificar(dados)
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _origem_permitida(self):
        if endereco_privado(self.client_address[0]):
            return True
        self._responder(403, {"erro": "Acesso permitido só a partir da rede local da oficina."})
        return False

    def _chave(self):
        cab = self.headers.get("Authorization", "")
        return cab[7:] if cab.startswith("Bearer ") else ""

    def do_GET(self):
        if not self._origem_permitida():
            return
        if self.path == "/api/status":
            self._responder(200, {"sistema": "OficinaFácil", "versao": VERSAO})
        else:
            self._responder(404, {"erro": "Endereço não encontrado."})

    def do_POST(self):
        if not self._origem_permitida():
            return
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > LIMITE_CORPO:
            self._responder(413, {"erro": "Pedido grande demais."})
            return
        corpo = self.rfile.read(tamanho)
        try:
            if self.path == "/api/entrar":
                self._entrar(decodificar(corpo))
            elif self.path == "/api/sair":
                self.server.sessoes.fechar(self._chave())
                self._responder(200, {"ok": True})
            elif self.path == "/api/chamar":
                self._chamar(corpo)
            else:
                self._responder(404, {"erro": "Endereço não encontrado."})
        except RegraNegocioError as e:
            self._responder(422, {"erro": str(e)})
        except Exception as e:                       # erro inesperado: registrado no servidor, mensagem curta
            self.server.registrar(f"ERRO {type(e).__name__}: {e}")
            self._responder(500, {"erro": "Erro interno no servidor. Tente de novo."})

    def _entrar(self, dados):
        with self.server.trava_banco:
            usuario = self.server.ctrl.auth.autenticar(dados.get("login", ""), dados.get("senha", ""))
        if not usuario:
            self._responder(401, {"erro": "Login ou senha inválidos, ou usuário inativo."})
            return
        self._responder(200, {"chave": self.server.sessoes.abrir(usuario), "usuario": usuario})

    def _chamar(self, corpo):
        usuario = self.server.sessoes.usuario(self._chave())
        if usuario is None:
            self._responder(401, {"erro": "Sessão expirada ou inexistente. Entre de novo."})
            return
        pedido = decodificar(corpo, trocar_usuario=usuario)
        nome_ctrl, metodo = pedido.get("controlador", ""), pedido.get("metodo", "")
        if nome_ctrl not in CONTROLADORES or metodo.startswith("_") or (nome_ctrl, metodo) == ("auth", "autenticar"):
            self._responder(403, {"erro": "Operação não permitida."})
            return
        funcao = getattr(getattr(self.server.ctrl, nome_ctrl), metodo, None)
        if not callable(funcao):
            self._responder(404, {"erro": "Operação inexistente."})
            return
        args, kwargs = pedido.get("args", []), pedido.get("kwargs", {})
        arquivo = None
        if metodo == "exportar_pdf":           # o PDF é gerado no servidor e devolvido à estação
            arquivo = os.path.join(tempfile.mkdtemp(), "documento.pdf")
            args = list(args[:-1]) + [arquivo]
        with self.server.trava_banco:
            resultado = funcao(*args, **kwargs)
        if arquivo:
            with open(arquivo, "rb") as f:
                resultado = {"__arquivo__": base64.b64encode(f.read()).decode("ascii")}
            os.remove(arquivo)
        self._responder(200, {"resultado": resultado})


def iniciar_em_segundo_plano(host, porta, controladores, registrar=lambda _: None):
    """Usado pelos testes e pelas capturas de tela: sobe o servidor numa linha de execução e o devolve."""
    srv = ServidorAplicacao(host, porta, controladores, registrar)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

"""Protocolo entre as estações e o servidor central: JSON sobre HTTP, na rede local da oficina.

Os objetos do modelo viajam como {"__classe__": nome, "dados": atributos} e são recriados do outro lado.
Só endereços privados (IPv4 10.x, 172.16.x a 172.31.x e 192.168.x) e o próprio computador são aceitos.
"""
import ipaddress
import json
import socket

from ..modelo import RegraNegocioError, atendimento, cadastro, catalogo

PORTA_PADRAO = 8765
VERSAO = "1.0"

CLASSES = {}
for _modulo in (cadastro, catalogo, atendimento):
    for _nome in dir(_modulo):
        _obj = getattr(_modulo, _nome)
        if isinstance(_obj, type) and _obj.__module__ == _modulo.__name__:
            CLASSES[_nome] = _obj


class ErroConexao(RegraNegocioError):
    """O servidor não respondeu (desligado, endereço errado ou rede fora do ar)."""


# ------------------------------------------------------------------ serialização
def _para_json(valor):
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    if isinstance(valor, dict):
        return {str(k): _para_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [_para_json(v) for v in valor]
    nome = type(valor).__name__
    if nome in CLASSES:
        dados = {k: _para_json(v) for k, v in vars(valor).items() if k != "senha_hash"}   # o hash não sai do servidor
        return {"__classe__": nome, "dados": dados}
    raise TypeError(f"Tipo não suportado no protocolo: {nome}")


def _de_json(valor, trocar_usuario=None):
    if isinstance(valor, list):
        return [_de_json(v, trocar_usuario) for v in valor]
    if isinstance(valor, dict):
        if "__classe__" in valor:
            if valor["__classe__"] == "Usuario" and trocar_usuario is not None:
                return trocar_usuario          # no servidor, o usuário vem sempre da sessão
            cls = CLASSES[valor["__classe__"]]
            obj = cls.__new__(cls)
            obj.__dict__.update({k: _de_json(v, trocar_usuario) for k, v in valor["dados"].items()})
            return obj
        return {k: _de_json(v, trocar_usuario) for k, v in valor.items()}
    return valor


def codificar(dados):
    return json.dumps(_para_json(dados), ensure_ascii=False).encode("utf-8")


def decodificar(corpo, trocar_usuario=None):
    return _de_json(json.loads(corpo.decode("utf-8")) if corpo else {}, trocar_usuario)


# ------------------------------------------------------------------ endereços
def endereco_privado(host):
    """True para IPv4 privado (RFC 1918) ou o próprio computador (127.x); nomes são resolvidos antes."""
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
    except (OSError, ValueError):
        return False
    if ip.is_loopback:
        return True
    redes = [ipaddress.ip_network(r) for r in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    return any(ip in r for r in redes)


def separar_endereco(texto):
    """'192.168.0.10:8765' -> ('192.168.0.10', 8765); sem porta, usa a padrão."""
    texto = (texto or "").strip()
    host, _, porta = texto.partition(":")
    if not host:
        raise RegraNegocioError("Informe o endereço do servidor (ex.: 192.168.0.10:8765).")
    try:
        porta = int(porta) if porta else PORTA_PADRAO
    except ValueError:
        raise RegraNegocioError("Porta inválida no endereço do servidor.")
    if not endereco_privado(host):
        raise RegraNegocioError("Use um endereço da rede local (10.x, 172.16 a 172.31.x ou 192.168.x).")
    return host, porta


def ip_local():
    """Primeiro IPv4 privado deste computador (o endereço que as estações devem usar)."""
    candidatos = []
    try:
        candidatos = socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    for ip in candidatos:
        if not ip.startswith("127.") and endereco_privado(ip):
            return ip
    return "127.0.0.1"

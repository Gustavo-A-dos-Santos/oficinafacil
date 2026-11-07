"""Camada controle: os sete controladores do diagrama de componentes (item 7b).

Cada controlador recebe a conexão, cria os DAOs e serviços de que precisa e aplica as regras de negócio.
Este módulo traz o que é comum a todos: a transação (RNF06), a mudança de status (RF12) e as validações.
"""
import functools

from ..modelo import RegraNegocioError
from ..modelo.atendimento import HistoricoStatus
from ..persistencia import agora

_profundidade = {}  # chamadas de controlador em andamento por conexão


def transacao(metodo):
    """Executa o método como uma transação: grava tudo no fim ou desfaz tudo se der erro.

    Quando um controlador chama outro (ex.: o diagnóstico gera o orçamento), só a chamada mais
    externa confirma, para que a operação inteira continue sendo uma transação só.
    """
    @functools.wraps(metodo)
    def envolvido(self, *args, **kwargs):
        chave = id(self.conn)
        _profundidade[chave] = _profundidade.get(chave, 0) + 1
        try:
            resultado = metodo(self, *args, **kwargs)
            if _profundidade[chave] == 1:
                self.conn.commit()
            return resultado
        except Exception:
            if _profundidade[chave] == 1:
                self.conn.rollback()
            raise
        finally:
            _profundidade[chave] -= 1
    return envolvido


def mudar_status(os_dao, os_, status, usuario):
    """RF12: muda o status da OS e registra quem alterou e quando (RNF09)."""
    os_.status = status
    os_dao.editar(os_)
    os_dao.salvar_historico(HistoricoStatus(os_id=os_.id, status=status, usuario_id=usuario.id, data_hora=agora()))


def exigir_status(os_, *status):
    if os_.status not in status:
        from ..modelo.atendimento import StatusOS
        esperados = " ou ".join(StatusOS.NOMES[s] for s in status)
        raise RegraNegocioError(f"A OS {os_.id} está {os_.nome_status()}; a operação exige {esperados}.")


def obrigatorio(valor, campo):
    if valor is None or str(valor).strip() == "":
        raise RegraNegocioError(f"Informe o campo {campo}.")
    return str(valor).strip()


def inteiro(valor, campo, minimo=0):
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise RegraNegocioError(f"O campo {campo} deve ser um número inteiro.")
    if n < minimo:
        raise RegraNegocioError(f"O campo {campo} deve ser no mínimo {minimo}.")
    return n


def valor_monetario(valor, campo, positivo=False):
    try:
        v = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        raise RegraNegocioError(f"O campo {campo} deve ser um valor numérico.")
    if v < 0 or (positivo and v == 0):
        raise RegraNegocioError(f"O campo {campo} deve ser {'maior que zero' if positivo else 'positivo'}.")
    return round(v, 2)


def periodo(data_inicio, data_fim):
    """Valida o período de uma consulta: datas AAAA-MM-DD (ou vazias) e início não depois do fim."""
    from datetime import date
    datas = []
    for valor, campo in ((data_inicio, "data inicial"), (data_fim, "data final")):
        valor = (valor or "").strip()
        if valor:
            try:
                date.fromisoformat(valor)
            except ValueError:
                raise RegraNegocioError(f"A {campo} é inválida; escolha a data no calendário.")
        datas.append(valor)
    if datas[0] and datas[1] and datas[0] > datas[1]:
        raise RegraNegocioError("A data inicial não pode ser depois da data final.")
    return datas

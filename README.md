# OficinaFácil

Sistema de gestão de ordens de serviço (OS) de oficina mecânica, desenvolvido como TCD de
Engenharia de Software 3 (IFTM Patrocínio). Implementa os requisitos RF01 a RF35 e as regras
RN01 a RN10 modelados na Parte 1 do trabalho.

Sistema **cliente-servidor para a rede local da oficina**: um computador faz o papel de
**servidor central** (guarda o banco SQLite, os backups e executa as regras de negócio) e os demais
são **estações de trabalho** (balcão, oficina, gerência), com a interface gráfica em **PySide6 (Qt)**.
As estações falam com o servidor por HTTP/JSON, só com endereços privados da rede (10.x, 172.16 a
172.31.x e 192.168.x). O servidor usa só a biblioteca padrão do Python. O design system da interface
está em [`docs/DESIGN.md`](docs/DESIGN.md).

```
  Estação do balcão        Estação da oficina       Estação da gerência
  192.168.0.11             192.168.0.12             192.168.0.13
  python main.py           python main.py           python main.py
        \                        |                        /
         \---------- rede local da oficina (HTTP/JSON) --/
                                  |
                       Servidor central 192.168.0.10:8765
                       python servidor.py  (oficinafacil.db + backups)
```

## Como instalar e executar

1. Em **todos** os computadores, instale o Python 3.10 ou mais novo
   (https://www.python.org/downloads/). No Windows, marque **"Add python.exe to PATH"**.
2. Copie a pasta `sistema` para cada computador (ou use `git clone`).
3. **No servidor** (um computador que fica ligado durante o expediente), na pasta `sistema`:

   ```
   python servidor.py
   ```

   Ele mostra o endereço a usar nas estações, por exemplo `192.168.0.10:8765`. Na primeira vez, o
   Windows pergunta se o Python pode usar a rede: permita **só em redes privadas**. Para escolher o
   endereço ou a porta: `python servidor.py --host 192.168.0.10 --porta 8765`. O ideal é reservar
   esse endereço no roteador, para ele não mudar.
4. **Em cada estação**, na pasta `sistema`, instale a biblioteca da interface (uma vez só) e abra o
   sistema:

   ```
   python -m pip install -r requirements.txt
   python main.py
   ```

5. Na tela de login, informe o endereço do servidor (fica salvo) e entre com um dos usuários de
   teste (senha `123`): `gerente`, `atendente` ou `mecanico`. O mesmo computador pode ser servidor e
   estação ao mesmo tempo.

O banco `oficinafacil.db` é criado no servidor na primeira execução, e uma cópia diária vai para
`backups/` no servidor. A escolha entre tema claro e escuro fica salva em cada estação.

## Compras de peças

Atendente, mecânico e gerente pedem peças pela página **Compras** (botão Nova solicitação) ou pela
página **Peças e serviços** (botão Solicitar compra ou duplo clique na peça). O pedido pode ser para
uma OS ou, sem OS, para repor o estoque; quem pediu fica registrado e pode alterar a quantidade ou
cancelar enquanto o pedido está pendente. O gerente registra a compra (com o fornecedor), o recebimento
(o estoque sobe e, se for de uma OS, ela volta para execução) e o cancelamento. A lista tem
indicadores por situação e filtros por situação, destino (OS ou estoque), fornecedor, peça, número da
OS, período e "só as minhas". Um banco criado antes dessa mudança é atualizado sozinho na primeira
execução do servidor, sem perder as solicitações.

## Como testar

```
python -m unittest discover -s tests -v
```

Os testes cobrem as regras de negócio, os controladores, o banco e a comunicação entre estação e
servidor (o servidor de teste sobe sozinho em 127.0.0.1); não abrem janelas e não dependem do PySide6.

## Estrutura

Orientado a objetos, em camadas, com um pacote para cada pacote do diagrama de pacotes (item 7c):
as telas, na estação, chamam os controladores do servidor pelo pacote comunicacao; no servidor, cada
controlador cria os DAOs e serviços de que precisa, e os DAOs fazem o CRUD
com SQL parametrizado e devolvem objetos do modelo.

| Pacote | Camada | Conteúdo |
|---|---|---|
| `servidor.py` | — | Ponto de entrada do servidor central |
| `main.py` | — | Ponto de entrada da estação de trabalho |
| `oficinafacil/apresentacao/` | Apresentação | `App`, `TelaLogin`, `TelaPrincipal` (barra lateral e páginas), `JanelaOS`, o design system (`tema.py`), a biblioteca de componentes (`componentes.py`) e os recursos (fonte Inter e ícones Lucide), em PySide6 |
| `oficinafacil/comunicacao/` | Comunicação | `ServidorAplicacao` (servidor HTTP/JSON, sessões, só rede local), `ControladoresRemotos` (lado da estação) e o protocolo |
| `oficinafacil/controle/` | Controle | Os 7 controladores (`AuthController`, `CadastroController`, `OSController`, `OrcamentoController`, `PecasComprasController`, `PagamentoController`, `RelatorioController`), transação e mudança de status |
| `oficinafacil/servico/` | Serviços | `ServicoSeguranca`, `ServicoOrcamento`, `ServicoEstoque`, `ServicoNotificacao`, `ServicoRelatorio` (PDF) |
| `oficinafacil/persistencia/` | Persistência | `Conexao` (14 tabelas, dados iniciais, backup) e os 6 DAOs |
| `oficinafacil/modelo/` | Modelo | Classes de domínio: `cadastro`, `catalogo`, `atendimento` e as enumerações |
| `tests/` | Testes | `apoio.py` (pré-condições), unitários, compras, integração, rede e não funcionais (unittest, 47 testes) |
| `docs/` | Documentação | Itens 8 a 10 do TCD, design system, licenças de terceiros e capturas de tela (temas claro e escuro) |

## Bibliotecas e licenças de terceiros

| Item | Uso | Licença |
|---|---|---|
| PySide6 (Qt for Python), pacote `PySide6-Essentials` | Interface gráfica | LGPL v3 (uso como biblioteca, sem modificação) |
| Fonte Inter 4.1 | Tipografia da interface | SIL Open Font License 1.1 |
| Ícones Lucide 0.460 | Ícones da interface | ISC |

Detalhes em [`docs/LICENCAS.md`](docs/LICENCAS.md). Os textos das licenças da fonte e dos ícones
acompanham os arquivos em `oficinafacil/apresentacao/recursos/`.

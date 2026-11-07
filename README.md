# OficinaFácil

Sistema de gestão de ordens de serviço (OS) de oficina mecânica, desenvolvido como TCD de
Engenharia de Software 3 (IFTM Patrocínio). Implementa os requisitos RF01 a RF35 e as regras
RN01 a RN10 modelados na Parte 1 do trabalho.

Feito só com Python e a biblioteca padrão: **não precisa instalar nada além do Python**.

## Como executar

1. Instale o Python 3.10 ou mais novo (https://www.python.org/downloads/). No Windows, marque
   a opção **"Add python.exe to PATH"** na instalação. O tkinter já vem junto.
2. Na pasta `sistema`, execute:

   ```
   python main.py
   ```

3. Entre com um dos usuários de teste (senha `123`): `gerente`, `atendente` ou `mecanico`.

O banco `oficinafacil.db` é criado automaticamente na primeira execução, e uma cópia diária vai
para `backups/`.

## Como testar

```
python -m unittest discover -s tests -v
```

## Estrutura

Orientado a objetos, em camadas, com um pacote para cada pacote do diagrama de pacotes (item 7c):
as telas chamam os controladores, que criam os DAOs e serviços de que precisam; os DAOs fazem o CRUD
com SQL parametrizado e devolvem objetos do modelo.

| Pacote | Camada | Conteúdo |
|---|---|---|
| `main.py` | — | Ponto de entrada |
| `oficinafacil/apresentacao/` | Apresentação | `App`, `TelaLogin`, `TelaPrincipal` (abas), `JanelaOS` e componentes comuns (tkinter) |
| `oficinafacil/controle/` | Controle | Os 7 controladores (`AuthController`, `CadastroController`, `OSController`, `OrcamentoController`, `PecasComprasController`, `PagamentoController`, `RelatorioController`), transação e mudança de status |
| `oficinafacil/servico/` | Serviços | `ServicoSeguranca`, `ServicoOrcamento`, `ServicoEstoque`, `ServicoNotificacao`, `ServicoRelatorio` (PDF) |
| `oficinafacil/persistencia/` | Persistência | `Conexao` (14 tabelas, dados iniciais, backup) e os 6 DAOs |
| `oficinafacil/modelo/` | Modelo | Classes de domínio: `cadastro`, `catalogo`, `atendimento` e as enumerações |
| `tests/` | Testes | `apoio.py` (pré-condições), unitários, integração e não funcionais (unittest, 30 testes) |
| `docs/` | Documentação | Itens 8 a 10 do TCD e capturas de tela |

# Bibliotecas e recursos de terceiros

Todos são gratuitos e de licença permissiva (ou LGPL usada como biblioteca), compatíveis com o uso
no OficinaFácil.

| Item | Versão | Onde está | Uso | Licença |
|---|---|---|---|---|
| PySide6 (Qt for Python), pacote `PySide6-Essentials` | 6.11.3 | instalado pelo `pip` (`requirements.txt`) | Janelas, componentes, estilos (QSS), SVG | LGPL v3 |
| Fonte Inter | 4.1 | `oficinafacil/apresentacao/recursos/fontes/` (Regular, Medium, SemiBold, Bold) | Tipografia, com números tabulares | SIL Open Font License 1.1 (`LICENSE-Inter-OFL.txt`) |
| Ícones Lucide (`lucide-static`) | 0.460.0 | `oficinafacil/apresentacao/recursos/icones/` (45 SVG) | Ícones da interface | ISC (`LICENSE-Lucide-ISC.txt`) |

## Observações sobre a LGPL (PySide6)

O PySide6 é usado sem modificação, como biblioteca carregada dinamicamente e instalada separadamente
pelo `pip`. O código do OficinaFácil não incorpora nem altera o código do Qt, e quem usa o sistema
pode trocar a versão do PySide6 por outra compatível, o que atende às condições da LGPL v3.

## Biblioteca padrão do Python

O restante do sistema usa só a biblioteca padrão: `sqlite3` (banco), `hashlib` e `hmac` (senhas),
`datetime`, `functools` e `unittest` (testes). A licença do Python (PSF License) é permissiva.

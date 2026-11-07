"""DocumentoPDF: monta PDF A4 com faixa de título, caixas, tabelas e rodapé paginado, sem bibliotecas externas.

Usa as fontes padrão Helvetica e Helvetica-Bold (todo leitor de PDF as tem) com a codificação WinAnsi,
que cobre os acentos do português. As larguras das letras vêm da tabela de métricas da Helvetica,
para alinhar valores à direita e quebrar textos longos.
"""
import unicodedata
from datetime import datetime

LARGURA, ALTURA = 595, 842   # A4 em pontos
MARGEM = 42
AZUL = (0.12, 0.31, 0.47)    # mesma cor do título das telas (#1f4e79)
AZUL_CLARO = (0.89, 0.93, 0.97)
CINZA = (0.45, 0.45, 0.45)
CINZA_CLARO = (0.96, 0.96, 0.96)
BORDA = (0.80, 0.80, 0.80)
PRETO, BRANCO = (0, 0, 0), (1, 1, 1)

# larguras (em milésimos do corpo) dos caracteres 32 a 126 da Helvetica e da Helvetica-Bold
_REGULAR = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556,
            556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278,
            500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469,
            556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500,
            278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_NEGRITO = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556,
            556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278,
            556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584,
            556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556,
            333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]


def largura_texto(texto, tamanho, negrito=False):
    tabela = _NEGRITO if negrito else _REGULAR
    total = 0
    for ch in str(texto):
        base = unicodedata.normalize("NFD", ch)[0]  # letra acentuada tem a largura da letra sem acento
        codigo = ord(base)
        total += tabela[codigo - 32] if 32 <= codigo <= 126 else 556
    return total * tamanho / 1000


def quebrar(texto, largura, tamanho, negrito=False):
    """Divide o texto em linhas que cabem na largura (em pontos)."""
    linhas = []
    for paragrafo in str(texto or "").splitlines() or [""]:
        atual = ""
        for palavra in paragrafo.split():
            teste = f"{atual} {palavra}".strip()
            if largura_texto(teste, tamanho, negrito) <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


def cortar(texto, largura, tamanho, negrito=False):
    """Encurta o texto com reticências para caber numa célula."""
    texto = str(texto)
    if largura_texto(texto, tamanho, negrito) <= largura:
        return texto
    while texto and largura_texto(texto + "...", tamanho, negrito) > largura:
        texto = texto[:-1]
    return texto.rstrip() + "..."


def _escapar(texto):
    return str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _cor(rgb):
    return " ".join(f"{c:.3f}" for c in rgb)


class DocumentoPDF:
    """Uso: doc = DocumentoPDF("Orçamento", "OS nº 5"); doc.texto(...); doc.tabela(...); doc.salvar(caminho).

    As coordenadas y são medidas a partir do topo da página (como nas telas); a conversão para o PDF,
    que mede de baixo para cima, é feita aqui dentro. self.y é a posição atual de escrita.
    """

    def __init__(self, titulo, subtitulo=""):
        self.titulo, self.subtitulo = titulo, subtitulo
        self.gerado_em = datetime.now().strftime("%d/%m/%Y às %H:%M")
        self.paginas = []
        self.nova_pagina()

    # ---------------------------------------------------------------- página
    def nova_pagina(self):
        self.ops = []
        self.paginas.append(self.ops)
        self.retangulo(0, 0, LARGURA, 74, AZUL)
        self.texto(MARGEM, 34, "OficinaFácil", 20, True, BRANCO)
        self.texto(MARGEM, 54, "Gestão de ordens de serviço", 9, cor=(0.80, 0.87, 0.94))
        self.texto(LARGURA - MARGEM, 34, self.titulo, 15, True, BRANCO, alinhar="direita")
        if self.subtitulo:
            self.texto(LARGURA - MARGEM, 54, self.subtitulo, 10, cor=(0.80, 0.87, 0.94), alinhar="direita")
        self.y = 100

    def garantir_espaco(self, altura):
        """Abre outra página se o que vem a seguir não couber acima do rodapé."""
        if self.y + altura > ALTURA - 60:
            self.nova_pagina()

    # ---------------------------------------------------------------- primitivas
    def texto(self, x, y, texto, tamanho=10, negrito=False, cor=PRETO, alinhar="esquerda"):
        if alinhar == "direita":
            x -= largura_texto(texto, tamanho, negrito)
        elif alinhar == "centro":
            x -= largura_texto(texto, tamanho, negrito) / 2
        fonte = "F2" if negrito else "F1"
        self.ops.append(f"BT {_cor(cor)} rg /{fonte} {tamanho} Tf {x:.2f} {ALTURA - y:.2f} Td "
                        f"({_escapar(texto)}) Tj ET")

    def retangulo(self, x, y, larg, alt, preenchimento=None, borda=None):
        partes = [f"{x:.2f} {ALTURA - y - alt:.2f} {larg:.2f} {alt:.2f} re"]
        if preenchimento and borda:
            self.ops.append(f"{_cor(preenchimento)} rg {_cor(borda)} RG 0.6 w {partes[0]} B")
        elif preenchimento:
            self.ops.append(f"{_cor(preenchimento)} rg {partes[0]} f")
        else:
            self.ops.append(f"{_cor(borda or BORDA)} RG 0.6 w {partes[0]} S")

    def linha(self, x1, y1, x2, y2, cor=BORDA, espessura=0.6):
        self.ops.append(f"{_cor(cor)} RG {espessura} w {x1:.2f} {ALTURA - y1:.2f} m {x2:.2f} {ALTURA - y2:.2f} l S")

    # ---------------------------------------------------------------- blocos
    def secao(self, titulo):
        """Título de seção com um traço azul embaixo."""
        self.garantir_espaco(40)
        self.y += 8
        self.texto(MARGEM, self.y + 10, titulo.upper(), 10, True, AZUL)
        self.linha(MARGEM, self.y + 15, LARGURA - MARGEM, self.y + 15, AZUL, 1.2)
        self.y += 24

    def campos(self, pares, colunas=2):
        """Rótulo pequeno em cinza com o valor embaixo, em colunas, dentro de uma caixa clara."""
        largura_col = (LARGURA - 2 * MARGEM - 16) / colunas
        linhas = [pares[i:i + colunas] for i in range(0, len(pares), colunas)]
        altura = 30 * len(linhas) + 8
        self.garantir_espaco(altura)
        self.retangulo(MARGEM, self.y, LARGURA - 2 * MARGEM, altura, CINZA_CLARO, BORDA)
        y = self.y + 6
        for linha in linhas:
            for i, (rotulo, valor) in enumerate(linha):
                x = MARGEM + 8 + i * largura_col
                self.texto(x, y + 9, rotulo, 7.5, cor=CINZA)
                self.texto(x, y + 22, cortar(valor if valor not in (None, "") else "-", largura_col - 10, 10), 10, True)
            y += 30
        self.y += altura + 6

    def paragrafo(self, texto, tamanho=10, cor=PRETO):
        for linha in quebrar(texto, LARGURA - 2 * MARGEM, tamanho):
            self.garantir_espaco(tamanho + 4)
            self.texto(MARGEM, self.y + tamanho, linha, tamanho, cor=cor)
            self.y += tamanho + 4
        self.y += 4

    def tabela(self, colunas, linhas, vazio="Nenhum item."):
        """colunas: lista de (título, largura relativa, alinhamento 'esquerda' ou 'direita').
        Cabeçalho azul repetido em cada página e linhas zebradas."""
        total_rel = sum(c[1] for c in colunas)
        util = LARGURA - 2 * MARGEM
        larguras = [util * c[1] / total_rel for c in colunas]
        alt = 18

        def cabecalho():
            self.retangulo(MARGEM, self.y, util, alt, AZUL)
            self._celulas([c[0] for c in colunas], larguras, colunas, 8.5, True, BRANCO)
            self.y += alt

        self.garantir_espaco(alt * 2)
        cabecalho()
        if not linhas:
            self.retangulo(MARGEM, self.y, util, alt, None, BORDA)
            self.texto(MARGEM + 6, self.y + 12, vazio, 9, cor=CINZA)
            self.y += alt
        for n, valores in enumerate(linhas):
            if self.y + alt > ALTURA - 60:
                self.nova_pagina()
                cabecalho()
            if n % 2:
                self.retangulo(MARGEM, self.y, util, alt, CINZA_CLARO)
            self._celulas(valores, larguras, colunas, 9.5, False, PRETO)
            self.y += alt
        self.linha(MARGEM, self.y, LARGURA - MARGEM, self.y, BORDA)
        self.y += 10

    def _celulas(self, valores, larguras, colunas, tamanho, negrito, cor):
        x = MARGEM
        for valor, larg, coluna in zip(valores, larguras, colunas):
            texto = cortar(valor, larg - 12, tamanho, negrito)
            if coluna[2] == "direita":
                self.texto(x + larg - 6, self.y + 12.5, texto, tamanho, negrito, cor, "direita")
            else:
                self.texto(x + 6, self.y + 12.5, texto, tamanho, negrito, cor)
            x += larg

    def totais(self, pares, destaque):
        """Quadro de totais à direita; destaque: (rótulo, valor) da última linha, em azul."""
        larg, x = 230, LARGURA - MARGEM - 230
        self.garantir_espaco(20 * len(pares) + 34)
        for rotulo, valor in pares:
            self.texto(x + 8, self.y + 13, rotulo, 9.5, cor=CINZA)
            self.texto(x + larg - 8, self.y + 13, valor, 9.5, alinhar="direita")
            self.y += 19
        self.retangulo(x, self.y + 2, larg, 26, AZUL)
        self.texto(x + 8, self.y + 19, destaque[0], 11, True, BRANCO)
        self.texto(x + larg - 8, self.y + 19, destaque[1], 13, True, BRANCO, "direita")
        self.y += 40

    def cartoes(self, pares):
        """Indicadores em destaque, lado a lado: (rótulo, valor)."""
        n = len(pares)
        espaco = 10
        larg = (LARGURA - 2 * MARGEM - espaco * (n - 1)) / n
        self.garantir_espaco(62)
        for i, (rotulo, valor) in enumerate(pares):
            x = MARGEM + i * (larg + espaco)
            self.retangulo(x, self.y, larg, 54, AZUL_CLARO, (0.70, 0.80, 0.90))
            self.texto(x + larg / 2, self.y + 26, cortar(valor, larg - 10, 16, True), 16, True, AZUL, "centro")
            self.texto(x + larg / 2, self.y + 43, cortar(rotulo, larg - 10, 8), 8, cor=CINZA, alinhar="centro")
        self.y += 66

    def barras(self, pares, vazio="Nenhum registro."):
        """Gráfico de barras horizontais: (rótulo, quantidade)."""
        if not pares:
            self.paragrafo(vazio, 9, CINZA)
            return
        maior = max(q for _, q in pares) or 1
        x_barra, larg_max = MARGEM + 150, LARGURA - 2 * MARGEM - 190
        for rotulo, qtd in pares:
            self.garantir_espaco(18)
            self.texto(MARGEM, self.y + 11, cortar(rotulo, 145, 9.5), 9.5)
            self.retangulo(x_barra, self.y + 2, larg_max, 12, CINZA_CLARO)
            self.retangulo(x_barra, self.y + 2, max(larg_max * qtd / maior, 2), 12, AZUL)
            self.texto(LARGURA - MARGEM, self.y + 11, str(qtd), 9.5, True, alinhar="direita")
            self.y += 18
        self.y += 8

    def assinaturas(self, nomes):
        """Linhas de assinatura lado a lado, no fim do documento."""
        self.garantir_espaco(70)
        self.y += 40
        larg = (LARGURA - 2 * MARGEM - 40) / len(nomes)
        for i, nome in enumerate(nomes):
            x = MARGEM + i * (larg + 40)
            self.linha(x, self.y, x + larg, self.y, PRETO, 0.8)
            self.texto(x + larg / 2, self.y + 12, nome, 9, cor=CINZA, alinhar="centro")
        self.y += 24

    # ---------------------------------------------------------------- arquivo
    def salvar(self, caminho):
        total = len(self.paginas)
        for n, ops in enumerate(self.paginas, 1):  # rodapé com a numeração "Página n de total"
            self.ops = ops
            self.linha(MARGEM, ALTURA - 40, LARGURA - MARGEM, ALTURA - 40)
            self.texto(MARGEM, ALTURA - 26, f"Gerado pelo OficinaFácil em {self.gerado_em}", 8, cor=CINZA)
            self.texto(LARGURA - MARGEM, ALTURA - 26, f"Página {n} de {total}", 8, cor=CINZA, alinhar="direita")
        kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(total))
        objetos = [b"<< /Type /Catalog /Pages 2 0 R >>",
                   f"<< /Type /Pages /Kids [{kids}] /Count {total} >>".encode(),
                   b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
                   b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
        for i, ops in enumerate(self.paginas):
            dados = "\n".join(ops).encode("cp1252", errors="replace")
            objetos.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGURA} {ALTURA}] "
                           f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {6 + 2 * i} 0 R >>".encode())
            objetos.append(f"<< /Length {len(dados)} >>\nstream\n".encode() + dados + b"\nendstream")
        saida = bytearray(b"%PDF-1.4\n")
        posicoes = []
        for n, obj in enumerate(objetos, start=1):
            posicoes.append(len(saida))
            saida += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
        inicio_xref = len(saida)
        saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
        for p in posicoes:
            saida += f"{p:010d} 00000 n \n".encode()
        saida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
        with open(caminho, "wb") as f:
            f.write(saida)

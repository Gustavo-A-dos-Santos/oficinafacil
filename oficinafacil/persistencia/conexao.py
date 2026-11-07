"""Conexao: abre o banco SQLite, cria as 14 tabelas (Quadro 29), carrega os dados iniciais e faz o backup diário."""
import os
import sqlite3
from datetime import date

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL CHECK (perfil IN ('ATENDENTE','MECANICO','GERENTE')),
    ativo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cliente (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL,
    cpf TEXT UNIQUE,
    email TEXT,
    ativo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS veiculo (
    id INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    placa TEXT NOT NULL UNIQUE,
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    ano INTEGER,
    km INTEGER
);
CREATE TABLE IF NOT EXISTS ordem_servico (
    id INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    veiculo_id INTEGER NOT NULL REFERENCES veiculo(id),
    usuario_abertura_id INTEGER NOT NULL REFERENCES usuario(id),
    mecanico_id INTEGER REFERENCES usuario(id),
    problema TEXT NOT NULL,
    km_entrada INTEGER,
    status TEXT NOT NULL,
    data_abertura TEXT NOT NULL,
    data_execucao TEXT,
    data_conclusao TEXT,
    data_aviso_cliente TEXT,
    motivo_cancelamento TEXT
);
CREATE TABLE IF NOT EXISTS servico (
    id INTEGER PRIMARY KEY,
    descricao TEXT NOT NULL,
    valor_base REAL NOT NULL CHECK (valor_base > 0),
    ativo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS peca (
    id INTEGER PRIMARY KEY,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL CHECK (valor >= 0),
    qtd_estoque INTEGER NOT NULL DEFAULT 0 CHECK (qtd_estoque >= 0),
    estoque_minimo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS fornecedor (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    telefone TEXT,
    email TEXT
);
CREATE TABLE IF NOT EXISTS diagnostico (
    id INTEGER PRIMARY KEY,
    os_id INTEGER NOT NULL UNIQUE REFERENCES ordem_servico(id),
    mecanico_id INTEGER NOT NULL REFERENCES usuario(id),
    descricao TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orcamento (
    id INTEGER PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordem_servico(id),
    gerente_id INTEGER REFERENCES usuario(id),
    versao INTEGER NOT NULL,
    valor_total REAL NOT NULL,
    situacao TEXT NOT NULL,
    data TEXT NOT NULL,
    data_hora_decisao_cliente TEXT
);
CREATE TABLE IF NOT EXISTS item_servico_os (
    id INTEGER PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordem_servico(id),
    servico_id INTEGER NOT NULL REFERENCES servico(id),
    valor REAL NOT NULL CHECK (valor >= 0),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0)
);
CREATE TABLE IF NOT EXISTS item_peca_os (
    id INTEGER PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordem_servico(id),
    peca_id INTEGER NOT NULL REFERENCES peca(id),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    valor REAL NOT NULL CHECK (valor >= 0),
    destinacao_residuo TEXT
);
CREATE TABLE IF NOT EXISTS solicitacao_compra (
    id INTEGER PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordem_servico(id),
    peca_id INTEGER NOT NULL REFERENCES peca(id),
    fornecedor_id INTEGER REFERENCES fornecedor(id),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    situacao TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pagamento (
    id INTEGER PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordem_servico(id),
    valor REAL NOT NULL CHECK (valor > 0),
    forma_pagamento TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historico_status (
    id INTEGER PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordem_servico(id),
    status TEXT NOT NULL,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    data_hora TEXT NOT NULL
);
"""


class Conexao:

    def __init__(self, caminho="oficinafacil.db"):
        self.caminho = caminho

    def conectar(self):
        """Abre o banco, cria as tabelas e carrega os dados iniciais se estiver vazio."""
        conn = sqlite3.connect(self.caminho)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(ESQUEMA)
        if conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0:
            self.carregar_dados_iniciais(conn)
        return conn

    def carregar_dados_iniciais(self, conn):
        """Um usuário de cada perfil e alguns itens de catálogo (do diagrama de objetos, item 7d)."""
        from ..servico.seguranca import ServicoSeguranca
        seg = ServicoSeguranca()
        for nome, login, perfil in [("Marcos Lima", "gerente", "GERENTE"), ("Ana Souza", "atendente", "ATENDENTE"),
                                    ("João Pereira", "mecanico", "MECANICO")]:
            conn.execute("INSERT INTO usuario (nome, login, senha_hash, perfil) VALUES (?,?,?,?)",
                         (nome, login, seg.gerar_hash("123"), perfil))
        conn.executemany("INSERT INTO servico (descricao, valor_base) VALUES (?,?)",
                         [("Troca de amortecedores", 250.0), ("Troca de óleo", 60.0),
                          ("Revisão de freios", 120.0), ("Alinhamento e balanceamento", 90.0)])
        conn.executemany("INSERT INTO peca (descricao, valor, qtd_estoque, estoque_minimo) VALUES (?,?,?,?)",
                         [("Amortecedor dianteiro", 265.0, 0, 2), ("Óleo 5W30 (litro)", 45.0, 20, 8),
                          ("Filtro de óleo", 35.0, 6, 3), ("Pastilha de freio (jogo)", 140.0, 4, 2)])
        conn.execute("INSERT INTO fornecedor (nome, telefone, email) VALUES (?,?,?)",
                     ("Auto Peças Triângulo", "(34) 3831-0000", "vendas@autopecastriangulo.com.br"))
        conn.execute("INSERT INTO cliente (nome, telefone, email) VALUES (?,?,?)",
                     ("Carlos Mendes", "(34) 99999-0001", "carlos@email.com"))
        conn.execute("INSERT INTO veiculo (cliente_id, placa, marca, modelo, ano, km) VALUES (1,?,?,?,?,?)",
                     ("ABC1D23", "Fiat", "Uno", 2012, 148500))
        conn.commit()

    def backup_diario(self, conn, pasta):
        """RNF05: grava uma cópia do banco por dia (backups/oficinafacil_AAAA-MM-DD.db) e guarda as 30 últimas."""
        os.makedirs(pasta, exist_ok=True)
        destino = os.path.join(pasta, f"oficinafacil_{date.today().isoformat()}.db")
        if not os.path.exists(destino):
            copia = sqlite3.connect(destino)
            conn.backup(copia)
            copia.close()
        antigos = sorted(f for f in os.listdir(pasta) if f.startswith("oficinafacil_") and f.endswith(".db"))
        for nome in antigos[:-30]:
            os.remove(os.path.join(pasta, nome))
        return destino

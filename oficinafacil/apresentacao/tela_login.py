"""Tela de login (RF01): painel da marca à esquerda e formulário à direita."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..modelo import RegraNegocioError
from .componentes import TITULO, Botao, Campo, Interruptor, entrada, rotulo, sombra
from .tema import ESPACO, Tema, icone, logotipo


class TelaLogin(QWidget):

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("Pagina")
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # painel da marca
        marca = QFrame()
        marca.setObjectName("Lateral")
        marca.setMinimumWidth(360)
        m = QVBoxLayout(marca)
        m.setContentsMargins(48, 48, 48, 36)
        m.setSpacing(ESPACO["m"])
        logo = QLabel()
        logo.setPixmap(logotipo(56))
        m.addWidget(logo)
        nome = QLabel(TITULO)
        nome.setObjectName("Marca")
        nome.setStyleSheet("font-size: 28px;")
        m.addWidget(nome)
        frase = QLabel("Ordens de serviço da oficina, do balcão à entrega do veículo.")
        frase.setWordWrap(True)
        frase.setStyleSheet("font-size: 16px;")
        m.addWidget(frase)
        m.addSpacing(ESPACO["l"])
        for ic, texto in (("clipboard-list", "Abertura e acompanhamento das OS"),
                          ("file-text", "Orçamento aprovado pelo gerente e pelo cliente"),
                          ("package", "Peças, compras e estoque"),
                          ("chart-column", "Painel e relatórios gerenciais")):
            item = QHBoxLayout()
            item.setSpacing(12)
            ico = QLabel()
            ico.setPixmap(icone(ic, Tema.cor("destaque"), 20).pixmap(20, 20))
            item.addWidget(ico)
            item.addWidget(QLabel(texto), 1)
            m.addLayout(item)
        m.addStretch(1)
        rodape = QLabel("IFTM Patrocínio · TCD de Engenharia de Software 3")
        rodape.setStyleSheet("font-size: 12px;")
        m.addWidget(rodape)
        raiz.addWidget(marca, 4)

        # formulário
        lado = QWidget()
        lado.setObjectName("Pagina")
        d = QVBoxLayout(lado)
        d.setContentsMargins(ESPACO["xl"], ESPACO["m"], ESPACO["xl"], ESPACO["xl"])
        topo = QHBoxLayout()
        topo.addStretch(1)
        self.tema = Interruptor("Tema escuro")
        self.tema.definir_sem_animar(Tema.nome == "escuro")
        self.tema.toggled.connect(lambda _: app.alternar_tema())
        topo.addWidget(self.tema)
        d.addLayout(topo)
        d.addStretch(1)
        cartao = QFrame()
        cartao.setProperty("papel", "cartao")
        cartao.setFixedWidth(400)
        sombra(cartao, 2)
        c = QVBoxLayout(cartao)
        c.setContentsMargins(36, 32, 36, 32)
        c.setSpacing(ESPACO["m"])
        c.addWidget(rotulo("Entrar", "titulo"))
        c.addWidget(rotulo("Use o login e a senha fornecidos pelo gerente.", "subtitulo"))
        self.servidor = entrada("Ex.: 192.168.0.10:8765")
        self.servidor.setText(app.servidor)
        self.c_servidor = Campo("Servidor da oficina", self.servidor, "Endereço do computador central na rede local.", obrigatorio=True)
        self.login = entrada("Seu login")
        self.senha = entrada("Sua senha", senha=True)
        self.c_login = Campo("Login", self.login, obrigatorio=True)
        self.c_senha = Campo("Senha", self.senha, obrigatorio=True)
        c.addWidget(self.c_servidor)
        c.addWidget(self.c_login)
        c.addWidget(self.c_senha)
        self.aviso = rotulo("", "erro", True)
        self.aviso.hide()
        c.addWidget(self.aviso)
        self.entrar_btn = Botao("Entrar", "primario", None, None, self.entrar)
        self.entrar_btn.setMinimumHeight(40)
        c.addWidget(self.entrar_btn)
        dica = rotulo("Usuários de teste: gerente, atendente e mecanico\ncom a senha 123", "ajuda")
        dica.setAlignment(Qt.AlignCenter)
        c.addWidget(dica)
        cartao.setMinimumHeight(cartao.sizeHint().height())
        d.addWidget(cartao, 0, Qt.AlignHCenter)
        d.addStretch(2)
        raiz.addWidget(lado, 6)

        self.servidor.returnPressed.connect(self.login.setFocus)
        self.login.returnPressed.connect(self.senha.setFocus)
        self.senha.returnPressed.connect(self.entrar)
        self.setTabOrder(self.servidor, self.login)
        self.setTabOrder(self.login, self.senha)
        self.setTabOrder(self.senha, self.entrar_btn)

    def showEvent(self, e):
        super().showEvent(e)
        (self.login if self.servidor.text() else self.servidor).setFocus()

    def entrar(self):
        ok_login, ok_senha = self.c_login.validar(), self.c_senha.validar()
        if not (ok_login and ok_senha):
            return
        self.entrar_btn.carregando(True)
        try:
            if not self.c_servidor.validar():
                return
            self.app.conectar(self.servidor.text())
            usuario = self.app.ctrl.auth.autenticar(self.login.text().strip(), self.senha.text())
        except RegraNegocioError as e:                 # servidor desligado ou endereço fora da rede local
            self.aviso.setText(str(e))
            self.aviso.show()
            return
        finally:
            self.entrar_btn.carregando(False)
        if not usuario:
            self.aviso.setText("Login ou senha inválidos, ou usuário inativo.")
            self.aviso.show()
            self.senha.selectAll()
            self.senha.setFocus()
            return
        self.app.abrir_principal(usuario)

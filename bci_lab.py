#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DABOIT-BCI Lab v2 · programe cacos interativos e veja o cérebro reagir (funciona no celular)
============================================================================================
Só biblioteca padrão do Python (sem pip). Rode:   python bci_lab.py   (ou:  python bci_lab.py 9000)

  - No próprio celular (Pydroid 3 / Termux / Pythonista): abra http://localhost:8000
  - No PC, com o celular na mesma Wi-Fi: abra o endereço que aparece no terminal

Um "caco" é um programa que roda 30 vezes por segundo e decide quanto cada sentido
(14 sentidos: visao audicao tato olfato paladar equilibrio temperatura propriocepcao dor coracao fome senso_tempo bussola radar) é injetado no córtex. 0 = nada, 1 = forte, >1 = sobrecarga.

    nome    = Meu jogo
    duracao = 30
    botoes  = ACELERAR, FREAR          # até 4 botões na tela (variáveis b1..b4 / p1..p4)
    var vel = 0                        # variável que lembra o valor entre quadros
    vel     = limita(vel + (0.3*b1 - 0.4*b2)*dt, 0, 1)
    visao   = 0.2 + 0.8*vel
    audicao = 0.1 + 0.7*vel
    fim     = 1 if foco < 0.05 and t > 5 else 0   # opcional: termina quando for verdadeiro

Variáveis prontas : t (segundos)  d (duração)  dt  pi
                    b1..b4 (botão segurado)  p1..p4 (1 só no quadro em que apertou)
                    foco calma euforia estresse imersao  (estado mental estimado, 0..1, quadro anterior)
                    r_visao r_audicao r_tato r_olfato r_paladar  (reação efetiva anterior de cada setor)
Funções           : rampa degrau pulso onda ruido rand limita sin cos abs min max sqrt exp
Condição          : valor_a if condicao else valor_b   (aceita and, or, not, <, >, ==)

MODO PYTHON (Python de verdade: import, classes, laços, funções...)
  Se o código tiver  def quadro(c):  ele roda como um programa Python comum:
      NOME = "Meu jogo"; DURACAO = 30; BOTOES = ["PULAR"]    # opcionais
      def inicio(c): ...                                       # opcional, roda 1 vez
      def quadro(c): ...                                       # roda 30 vezes por segundo
  Entradas: c.t c.d c.dt c.b1..c.b4 c.p1..c.p4 c.foco c.calma c.euforia c.estresse c.imersao c.r_visao ...
  Saídas  : c.visao c.audicao c.tato c.olfato c.paladar c.equilibrio c.temperatura c.propriocepcao c.dor
            c.coracao c.fome c.senso_tempo c.bussola c.radar
            (0 a 1.5; se não setar, fica 0.05)
  Extras  : c.hud["pontos"] = 3 (aparece na tela) · c.msg = texto que a pessoa digitou/falou neste quadro ("" se nada)
            · c.diz("texto", "Nome") mostra uma fala na conversa · c.fim() encerra · c.qualquer_coisa = x guarda estado
            variáveis globais também guardam estado (use  global x  dentro de quadro)
  ATENÇÃO : o modo Python roda com as mesmas permissões do script no seu aparelho. Rode só código em que confia.
            Por padrão o servidor só aceita o próprio aparelho; com --rede (celular ligando no PC) o modo
            Python exige o PIN que aparece no terminal.

AVISO: é uma simulação fictícia (modelo simples, sem base clínica). Nada aqui afeta uma pessoa real.
"""
import ast
import ipaddress
import json
import math
import os
import random
import re
import secrets
import socket
import sys
import time
import traceback
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(PASTA, "cacos.json")
# Tabela de sentidos: para criar um novo, basta acrescentar uma linha aqui.
# (chave no código, rótulo, cor, inércia em s, centro no cérebro (x,y), raio, nº de eletrodos)
SENTIDOS = [
    ("visao", "VISÃO", "#4696ff", 0.10, (.16, .52), .12, 26),
    ("audicao", "AUDIÇÃO", "#46e68c", 0.08, (.40, .68), .12, 26),
    ("tato", "TATO", "#ffaa3c", 0.20, (.46, .22), .13, 26),
    ("olfato", "OLFATO", "#c86eff", 0.60, (.84, .62), .07, 14),
    ("paladar", "PALADAR", "#ff5a6e", 0.80, (.62, .48), .06, 14),
    ("equilibrio", "EQUILÍBRIO", "#2ee6d6", 0.15, (.27, .74), .06, 12),       # vestibular
    ("temperatura", "TEMPERATURA", "#ffe14a", 0.90, (.70, .30), .07, 12),     # calor / frio
    ("propriocepcao", "PROPRIOCEPÇÃO", "#9be564", 0.12, (.27, .34), .07, 12), # posição e movimento do corpo
    ("dor", "DOR", "#ff3030", 0.12, (.70, .68), .06, 12),                     # dor simulada
    ("coracao", "CORAÇÃO", "#ff7bb0", 0.30, (.38, .46), .05, 10),             # batimento (interocepção)
    ("fome", "FOME/SEDE", "#c8a46e", 2.00, (.54, .76), .05, 10),              # fome e sede (muito lento)
    ("senso_tempo", "SENSO DE TEMPO", "#a9b4c9", 1.00, (.84, .42), .06, 10),  # tempo "esticando" ou "voando"
    ("bussola", "BÚSSOLA", "#7a7aff", 0.25, (.66, .20), .05, 10),             # direção / campo magnético
    ("radar", "RADAR", "#f2f2f2", 0.15, (.50, .54), .04, 8),                  # proximidade (ecolocalização)
]
SETORES = [x[0] for x in SENTIDOS]
ROTULO = [x[1] for x in SENTIDOS]
NS = len(SENTIDOS)
SENTIDOS_JS = [{"rot": x[1], "cor": x[2], "c": list(x[4]), "r": x[5], "n": x[6]} for x in SENTIDOS]
MENTE = ["foco", "calma", "euforia", "estresse", "imersao"]
ROT_MENTE = ["FOCO", "CALMA", "EUFORIA", "ESTRESSE", "IMERSÃO"]
FPS = 30
TAU = [x[3] for x in SENTIDOS]            # inércia de cada setor (s): olfato/paladar/temperatura são lentos
LIMITE_SOBRECARGA = 5.5                    # soma dos setores
TEMPO_DESARME = 1.5                        # s acima do limite até o disjuntor desarmar

EXEMPLOS = {
    "Jogo: reflexo": """nome = Jogo: reflexo
duracao = 60
botoes = REAGIR
# Um estímulo (luz + bipe) aparece em horário aleatório. Toque em REAGIR antes de 1,2 s.
var alvo = 0
var espera = 2
var janela = 0
var pontos = 0
var erros = 0
var bip = 0
var vibra = 0
var amargo = 0
espera  = espera - dt if alvo < 0.5 else espera
liga    = 1 if (alvo < 0.5 and espera <= 0) else 0
alvo    = 1 if liga > 0.5 else alvo
janela  = 1.2 if liga > 0.5 else janela - dt
acerto  = 1 if (alvo > 0.5 and p1 > 0.5) else 0
perdeu  = 1 if (alvo > 0.5 and janela <= 0) else 0
pontos  = pontos + acerto
erros   = erros + perdeu
troca   = acerto + perdeu
alvo    = 0 if troca > 0.5 else alvo
espera  = 1 + 2*rand() if troca > 0.5 else espera
bip     = 1 if liga > 0.5 else bip*0.85
vibra   = 1 if acerto > 0.5 else vibra*0.92
amargo  = 1 if perdeu > 0.5 else amargo*0.96
visao   = 0.2 + 0.9*alvo
audicao = 0.15 + 0.8*bip
tato    = 0.15 + 0.7*vibra
olfato  = 0.2
paladar = 0.05 + 0.6*amargo
fim     = 1 if erros >= 5 else 0
""",
    "Jogo: moto": """nome = Jogo: moto
duracao = 60
botoes = ACELERAR, FREAR, BUZINA, DESVIAR
# Segure ACELERAR/FREAR. Quando um obstáculo se aproxima, toque DESVIAR (ou bata!).
var vel = 0
var buz = 0
var bat = 0
var prox = 5
var ok = 0
var quase = 0
var inseto = 0
vel    = limita(vel + (0.22*b1 - 0.5*b2 - 0.06)*dt, 0, 1)
buz    = 1 if p3 > 0.5 else buz*0.9
perigo = 1 if prox < 1.2 else 0
ok     = 1 if (perigo > 0.5 and p4 > 0.5) else ok
prox   = prox - dt*(0.4 + 1.2*vel)
bate   = 1 if (prox <= 0 and ok < 0.5 and vel > 0.15) else 0
passou = 1 if (prox <= 0 and ok > 0.5) else 0
bat    = 1 if bate > 0.5 else bat*0.92
quase  = 1 if passou > 0.5 else quase*0.93
vel    = vel*0.4 if bate > 0.5 else vel
inseto = 1 if (rand() < 0.002 and vel > 0.4) else inseto*0.985
prox   = 3 + 4*rand() if prox <= 0 else prox
ok     = 0 if prox > 2.5 else ok
visao   = 0.25 + 0.6*vel + 0.3*quase + 0.5*bat
audicao = 0.2 + 0.6*vel + 0.9*buz + 1.0*bat
tato    = 0.12 + 0.35*vel + 0.4*quase + 0.9*bat + 0.3*inseto
olfato  = 0.25
paladar = 0.05 + 0.7*inseto
""",
    "Mente adaptativa (feedback)": """nome = Mente adaptativa (feedback)
duracao = 40
# Circuito fechado: o código LÊ o estresse estimado e ajusta a intensidade sozinho.
var forca = 0.2
forca   = limita(forca + (0.08 if estresse < 0.35 else -0.15)*dt, 0.1, 1.3)
visao   = 0.8*forca + 0.1*onda(t,0.3)
audicao = 0.7*forca
tato    = 0.6*forca + 0.2*onda(t,0.2)
olfato  = 0.3
paladar = 0.1
""",
    "Python: ritmo": """# Caco em Python puro: roda como qualquer programa Python.
import math

NOME = "Python: ritmo"
DURACAO = 40
BOTOES = ["BATIDA"]

BPM = 80
passo = 60 / BPM
pontos = combo = ultima = 0
brilho = vibra = amargo = 0.0


def inicio(c):
    c.hud["pontos"] = 0


def quadro(c):
    global pontos, combo, ultima, brilho, vibra, amargo
    n = int(c.t // passo)
    fase = (c.t % passo) / passo           # 0..1 dentro da batida
    if n != ultima:                        # nova batida: luz + som
        ultima, brilho = n, 1.0
    erro = min(fase, 1 - fase)             # distância da batida (0 = perfeito)
    if c.p1:                               # tocou no botão neste quadro
        if erro < 0.15:
            pontos += 1 + combo // 4
            combo += 1
            vibra = 1.0
        else:
            combo, amargo = 0, 1.0
    brilho *= 0.88
    vibra *= 0.93
    amargo *= 0.95
    c.visao = 0.2 + 0.9 * brilho
    c.audicao = 0.15 + 0.7 * brilho + 0.1 * math.sin(c.t)
    c.tato = 0.15 + 0.7 * vibra
    c.olfato = 0.25
    c.paladar = 0.05 + 0.6 * amargo
    c.hud["pontos"], c.hud["combo"] = pontos, combo
    if c.estresse > 0.9:
        c.fim()
""",
    "Montanha-russa": """nome = Montanha-russa
duracao = 30
botoes = GRITAR, SEGURAR
# Usa os sentidos novos: equilibrio, propriocepcao, temperatura e dor (solavanco).
var susto = 0
subida = rampa(t,0,10)
queda  = pulso(t,12,1.2) + pulso(t,22,0.9)
susto  = 1 if p1 > 0.5 else susto*0.9
visao         = 0.3 + 0.3*subida + 0.6*queda
audicao       = 0.2 + 0.2*subida + 0.5*queda + 0.4*susto
tato          = 0.2 + 0.3*b2 + 0.4*queda
olfato        = 0.1
paladar       = 0.05
equilibrio    = 0.15 + 0.3*subida + 1.0*queda + 0.15*onda(t,0.8)
propriocepcao = 0.2 + 0.5*queda + 0.3*b2
temperatura   = 0.35 - 0.25*queda
dor           = 0.05 + 0.25*queda*(1 - b2)
""",
    "Caverna escura (eco)": """nome = Caverna escura (eco)
duracao = 40
botoes = PING, ANDAR
# Sem visão: toque PING para "ouvir" a parede (radar) e ANDAR para avançar. Bater dói.
var parede = 6
var eco = 0
var medo = 0
var baque = 0
parede = parede - 1.0*b2*dt
bate   = 1 if parede <= 0 else 0
baque  = 1 if bate > 0.5 else baque*0.93
parede = 4 + 4*rand() if bate > 0.5 else parede
eco    = 1 if p1 > 0.5 else eco*0.9
perto  = 1 if parede < 1.5 else 0
medo   = limita(medo + (0.5 if perto > 0.5 else -0.25)*dt, 0, 1)
visao         = 0.03
audicao       = 0.15 + 0.5*eco
radar         = 0.1 + eco*(1 - parede/8)
coracao       = 0.2 + 0.7*medo + 0.3*baque
propriocepcao = 0.15 + 0.4*b2
bussola       = 0.3 + 0.2*onda(t,0.1)
tato          = 0.1 + 0.5*baque
dor           = 0.05 + 0.6*baque
""",
    "Fome e jantar": """nome = Fome e jantar
duracao = 40
botoes = COMER
# A fome sobe devagar; COMER abaixa, dá prazer (paladar/olfato) e muda o senso de tempo.
var nivel = 0.2
var prazer = 0
nivel       = limita(nivel + 0.03*dt - 0.35*p1, 0, 1)
prazer      = 1 if p1 > 0.5 else prazer*0.95
fome        = 0.1 + 0.8*nivel
paladar     = 0.05 + 0.8*prazer
olfato      = 0.15 + 0.6*prazer + 0.2*nivel
coracao     = 0.2 + 0.2*nivel + 0.2*prazer
senso_tempo = 0.3 + 0.6*nivel
tato        = 0.1 + 0.3*prazer
""",
    "Tomar vinho": """nome = Tomar vinho
duracao = 12
paladar = 0.1 + 0.8*rampa(t,2,4) + 0.2*onda(t,0.3)
olfato  = 0.2 + 0.7*pulso(t,2,1.5)
tato    = 0.2 + 0.3*pulso(t,2.5,0.8)
visao   = 0.25
audicao = 0.1
""",
    "Sobrecarga (teste do disjuntor)": """nome = Sobrecarga (teste do disjuntor)
duracao = 12
visao   = 1.4*rampa(t,0,4)
audicao = 1.4*rampa(t,0,4)
tato    = 1.3*rampa(t,0,5)
olfato  = 1.0*rampa(t,1,5)
paladar = 1.0*rampa(t,2,5)
equilibrio    = 1.2*rampa(t,0,5)
temperatura   = 1.0*rampa(t,1,6)
propriocepcao = 1.0*rampa(t,0,5)
dor           = 1.2*rampa(t,2,6)
coracao       = 1.1*rampa(t,1,6)
radar         = 1.0*rampa(t,0,6)
""",
}


# ---------------------------------------------------------------------------
# Linguagem dos cacos (expressões validadas por AST: nada de import, atributos, etc.)
# ---------------------------------------------------------------------------
def _frac(v):
    return v - math.floor(v)


def _clamp(v, a=0.0, b=1.0):
    return a if v < a else (b if v > b else v)


FUNCS = {
    "sin": math.sin, "cos": math.cos, "abs": abs, "min": min, "max": max,
    "sqrt": lambda x: math.sqrt(max(0.0, x)),
    "exp": lambda x: math.exp(max(-50.0, min(50.0, x))),
    "rampa": lambda t, a, b: (min(1.0, max(0.0, (t - a) / (b - a))) if b != a else float(t >= a)),
    "degrau": lambda t, a: 1.0 if t >= a else 0.0,
    "pulso": lambda t, a, l=0.5: math.exp(-((t - a) / max(l, 1e-3)) ** 2),
    "onda": lambda t, f: math.sin(2 * math.pi * f * t),
    "ruido": lambda t, s=1: _frac(math.sin(t * 12.9898 + s * 78.233) * 43758.5453) * 2 - 1,
    "limita": lambda x, a, b: max(a, min(b, x)),
    "rand": random.random,
}
ENTRADAS = ["b%d" % i for i in range(1, 5)] + ["p%d" % i for i in range(1, 5)]
PRONTOS = {"t", "d", "dt", "pi"} | set(MENTE) | set(ENTRADAS) | {"r_" + s for s in SETORES}
RESERVADOS = set(FUNCS) | PRONTOS | {"var", "nome", "duracao", "botoes"}
PERMITIDOS = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Call, ast.Load,
              ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.USub, ast.UAdd, ast.Not, ast.Compare,
              ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.Eq, ast.NotEq, ast.IfExp, ast.BoolOp, ast.And, ast.Or)


def _norm(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().strip().lower()


def _validar(arvore, conhecidos):
    for n in ast.walk(arvore):
        if not isinstance(n, PERMITIDOS):
            raise ValueError("operação não permitida (use * para multiplicar; não existe ** nem [ ])")
        if isinstance(n, ast.Constant) and (isinstance(n.value, bool) or not isinstance(n.value, (int, float))):
            raise ValueError("só números são permitidos")
        if isinstance(n, ast.Call) and (not isinstance(n.func, ast.Name) or n.func.id not in FUNCS or n.keywords):
            raise ValueError("função desconhecida")
        if isinstance(n, ast.Name) and n.id not in conhecidos and n.id not in FUNCS:
            raise ValueError("nome desconhecido: " + n.id)


def _compilar(texto, conhecidos):
    try:
        arv = ast.parse(texto, mode="eval")
        _validar(arv, conhecidos)
        return compile(arv, "<caco>", "eval")
    except ValueError:
        raise
    except SyntaxError:
        raise ValueError("expressão com erro de sintaxe")
    except Exception:
        raise ValueError("expressão inválida")


def interpretar(codigo):
    if len(codigo) > 8000:
        raise ValueError("código muito grande (máx. 8000 caracteres)")
    nome, dur, prog, inits, botoes = "Caco sem nome", 10.0, [], {}, []
    conhecidos = set(PRONTOS)
    for i, bruta in enumerate(codigo.splitlines(), 1):
        linha = bruta.split("#")[0].strip()
        if not linha:
            continue
        eh_var = linha.lower().startswith("var ")
        if eh_var:
            linha = linha[4:].strip()
        if "=" not in linha:
            raise ValueError("linha %d: use  nome = expressão" % i)
        k, v = linha.split("=", 1)
        k, v = _norm(k), v.strip()
        try:
            if not eh_var and k == "nome":
                nome = v[:40] or nome
            elif not eh_var and k == "duracao":
                try:
                    dur = float(v.replace(",", "."))
                except ValueError:
                    raise ValueError("duracao precisa ser um número")
                if not 1 <= dur <= 120:
                    raise ValueError("duracao deve ficar entre 1 e 120 segundos")
            elif not eh_var and k == "botoes":
                botoes = [x.strip()[:12] for x in v.split(",") if x.strip()][:4]
            else:
                if not k.isidentifier() or k in RESERVADOS or (eh_var and (k in SETORES or k == "fim")):
                    raise ValueError("nome de variável inválido: " + k)
                if eh_var:
                    inits[k] = _compilar(v, {"d", "pi"})
                else:
                    prog.append((i, k, _compilar(v, conhecidos)))
                conhecidos.add(k)
        except ValueError as e:
            raise ValueError("linha %d: %s" % (i, e))
    return {"nome": nome, "dur": dur, "prog": prog, "inits": inits, "botoes": botoes}


def eh_python(codigo):
    return re.search(r"^\s*def\s+quadro\s*\(", codigo, re.M) is not None


def nome_python(codigo):
    m = re.search(r"^\s*NOME\s*=\s*[\"'](.{1,40}?)[\"']", codigo, re.M)
    return m.group(1) if m else "Caco Python"


def com_limite(fn, *args, limite=0.25):
    """Roda fn; se o código do caco passar do tempo (laço infinito), levanta TimeoutError."""
    fim = time.time() + limite

    def local(frame, ev, arg):
        if time.time() > fim:
            raise TimeoutError("o código demorou demais (laço infinito?)")
        return local

    def glob(frame, ev, arg):
        return local if frame.f_code.co_filename == "<caco>" else None

    antigo = sys.gettrace()
    sys.settrace(glob)
    try:
        return fn(*args)
    finally:
        sys.settrace(antigo)


def erro_py(e):
    if isinstance(e, SyntaxError):
        return ValueError("linha %s: erro de sintaxe: %s" % (e.lineno, e.msg))
    tb, ln = e.__traceback__, None
    while tb:
        if tb.tb_frame.f_code.co_filename == "<caco>":
            ln = tb.tb_lineno
        tb = tb.tb_next
    msg = "%s: %s" % (type(e).__name__, e)
    return ValueError(("linha %d: " % ln + msg) if ln else msg)


def _num(v):
    try:
        v = float(v)
    except Exception:
        return 0.0
    return 0.0 if v != v else max(-1e9, min(1e9, v))


class Ctx:
    """Objeto 'c' que o código Python do caco recebe a cada quadro."""

    def __init__(self):
        self.hud = {}
        self._fim = False
        self.msg = ""          # texto que a pessoa digitou/falou neste quadro ("" se nada)
        self._falas = []

    def diz(self, texto, quem=""):
        """Mostra uma fala na conversa da tela."""
        if len(self._falas) < 3:
            self._falas.append([str(quem)[:20], str(texto)[:200]])

    def fim(self):
        self._fim = True


class Sessao:
    """Um 'caco' em execução: roda quadro a quadro, recebendo os botões do celular."""

    def __init__(self, codigo, py_ok=True):
        self.ctx, self.py_q, self.estado, self.msg = None, None, {}, ""
        if eh_python(codigo):
            if not py_ok:
                raise ValueError("modo Python em rede: digite o PIN que aparece no terminal")
            if len(codigo) > 20000:
                raise ValueError("código muito grande")
            self.prog, inits = [], {}
            self._iniciar_py(codigo)
        else:
            c = interpretar(codigo)
            self.nome, self.dur, self.prog, self.botoes = c["nome"], c["dur"], c["prog"], c["botoes"]
            inits = c["inits"]
        base = dict(FUNCS)
        base.update(d=self.dur, pi=math.pi)
        for k, cod in inits.items():
            try:
                self.estado[k] = float(eval(cod, {"__builtins__": {}}, dict(base)))
            except Exception as e:
                raise ValueError("var %s: %s" % (k, e))
        self.total, self.n, self.parar = int(self.dur * FPS), 0, False
        self.r, self.a, self.m, self.ef = [0.0] * NS, [0.0] * NS, [0.0] * 5, [0.0] * NS
        self.sobre, self.desarme, self.fim_em = 0.0, None, None
        self.levels, self.msoma, self.vista = [], [0.0] * 5, time.time()

    def _iniciar_py(self, codigo):
        ns = {"__name__": "caco"}
        ns.update(FUNCS)
        try:
            cod = compile(codigo, "<caco>", "exec")
            com_limite(exec, cod, ns, limite=2.0)
        except Exception as e:
            raise erro_py(e)
        self.py_q = ns.get("quadro")
        if not callable(self.py_q):
            raise ValueError("defina  def quadro(c):")
        self.nome = str(ns.get("NOME", "Caco Python"))[:40]
        try:
            self.dur = float(ns.get("DURACAO", 30))
        except Exception:
            raise ValueError("DURACAO precisa ser um número")
        if not 1 <= self.dur <= 120:
            raise ValueError("DURACAO deve ficar entre 1 e 120 segundos")
        bt = ns.get("BOTOES", [])
        self.botoes = [str(x)[:12] for x in bt][:4] if isinstance(bt, (list, tuple)) else []
        self.ctx = Ctx()
        c = self.ctx
        c.t, c.d, c.dt = 0.0, self.dur, 1.0 / FPS
        for j in range(4):
            setattr(c, "b%d" % (j + 1), 0)
            setattr(c, "p%d" % (j + 1), 0)
        for s in SETORES:
            setattr(c, s, 0.05)
            setattr(c, "r_" + s, 0.0)
        for m in MENTE:
            setattr(c, m, 0.0)
        ini = ns.get("inicio")
        if callable(ini):
            try:
                com_limite(ini, c, limite=1.0)
            except Exception as e:
                raise erro_py(e)

    def _quadro_py(self, t, dt, b, p):
        c = self.ctx
        c.t, c.d, c.dt = t, self.dur, dt
        for j in range(4):
            setattr(c, "b%d" % (j + 1), int(b[j]))
            setattr(c, "p%d" % (j + 1), int(p[j]))
        c.b, c.p = [int(x) for x in b], [int(x) for x in p]
        c.msg = self.msg
        for j, s in enumerate(SETORES):
            setattr(c, "r_" + s, self.ef[j])
            setattr(c, s, 0.05)
        for j, m in enumerate(MENTE):
            setattr(c, m, self.m[j])
        try:
            com_limite(self.py_q, c)
        except Exception as e:
            raise erro_py(e)
        if c._fim:
            self.parar = True
        return [_num(getattr(c, s, 0.05)) for s in SETORES]

    def terminou(self):
        return self.parar or self.n >= self.total or (self.fim_em is not None and self.n / FPS >= self.fim_em)

    def hud(self):
        if self.ctx is not None:
            h = {}
            for k, v in list(self.ctx.hud.items())[:12]:
                ok = isinstance(v, (int, float)) and math.isfinite(v)
                h[str(k)[:16]] = round(v, 2) if ok else str(v)[:24]
            return h
        return {k: round(v, 2) for k, v in self.estado.items()}

    def quadro(self, b, p, kill):
        dt = 1.0 / FPS
        t = self.n * dt
        if self.ctx is not None:
            ent = self._quadro_py(t, dt, b, p)
        else:
            env = dict(FUNCS)
            env.update(self.estado)
            env.update(t=t, d=self.dur, dt=dt, pi=math.pi)
            for j in range(4):
                env["b%d" % (j + 1)] = float(b[j])
                env["p%d" % (j + 1)] = float(p[j])
            for j, s in enumerate(SETORES):
                env["r_" + s] = self.ef[j]
            for j, m in enumerate(MENTE):
                env[m] = self.m[j]
            for (i, k, cod) in self.prog:
                try:
                    v = float(eval(cod, {"__builtins__": {}}, env))
                except Exception as e:
                    raise ValueError("linha %d: %s" % (i, e))
                env[k] = 0.0 if v != v else max(-1e9, min(1e9, v))
            for k in self.estado:
                self.estado[k] = env[k]
            if env.get("fim", 0) > 0.5:
                self.parar = True
            ent = [env.get(s, 0.05) for s in SETORES]

        if self.desarme is not None:
            saida = [0.0] * NS
            self.r = [0.0] * NS
        else:
            lv = [0.0] * NS if kill else [min(1.5, max(0.0, x)) for x in ent]
            media = sum(lv) / NS
            saida = []
            for j in range(NS):
                alvo = lv[j] * 0.92 + media * 0.08             # contaminação cruzada (sinestesia)
                self.r[j] += (alvo - self.r[j]) * min(1.0, dt / TAU[j])   # inércia do setor
                self.a[j] += (self.r[j] - self.a[j]) * dt / 8.0           # adaptação neural lenta
                saida.append(max(0.0, self.r[j] - 0.30 * self.a[j]))
            self.sobre = self.sobre + dt if sum(saida) > LIMITE_SOBRECARGA else max(0.0, self.sobre - dt)
            if self.sobre >= TEMPO_DESARME:
                self.desarme, self.fim_em = t, t + 1.5
        vis, aud, tat, olf, pal, equ, tem, pro, dor, cor, fom, tmp, bus, rad = saida
        imers = _clamp((vis + aud + tat) / 3 / 0.8 + 0.1 * (pro + equ) + 0.05 * (bus + tmp + rad))
        estr = _clamp((0.4 * aud + 0.35 * tat + 0.25 * vis + 0.8 * dor + 0.15 * equ + 0.25 * cor + 0.1 * fom - 0.35) / 0.5
                      + (0.3 if self.sobre > 0 else 0.0))
        alvo_m = [_clamp(0.55 * vis + 0.45 * aud + 0.1 * pro + 0.1 * rad - 0.35 * estr), _clamp(1 - estr),
                  _clamp(0.5 * (olf + pal) + 0.35 * imers + 0.2 * equ + 0.15 * cor), estr, imers]
        for j in range(5):
            self.m[j] += (alvo_m[j] - self.m[j]) * dt / 0.8
            self.msoma[j] += self.m[j]
        self.ef = saida
        self.levels.append([round(x, 3) for x in saida])
        self.n += 1
        f = {"l": self.levels[-1], "m": [round(x, 3) for x in self.m]}
        if self.desarme is not None:
            f["x"] = 1
        return f

    def passo(self, n, b, p, kill, msg=""):
        self.vista = time.time()
        out = []
        for q in range(n):
            if self.terminou():
                break
            self.msg = msg if q == 0 else ""
            f = self.quadro(b, p if q == 0 else [0, 0, 0, 0], kill)
            if self.ctx is not None and self.ctx._falas:
                f["fala"], self.ctx._falas = self.ctx._falas, []
            out.append(f)
        self.msg = ""
        return out

    def resumo(self):
        dt, stats = 1.0 / FPS, []
        for j in range(NS):
            col = [f[j] for f in self.levels] or [0.0]
            pico = max(col)
            stats.append({"setor": ROTULO[j], "pico": round(pico, 2), "tpico": round(col.index(pico) * dt, 1),
                          "media": round(sum(col) / len(col), 2),
                          "ativo": round(sum(1 for x in col if x > 0.5) * dt, 1)})
        n = max(1, len(self.levels))
        mente = [round(x / n, 2) for x in self.msoma]
        dom = max(stats, key=lambda s: s["pico"])
        if self.desarme is not None:
            ver = "⚠ SOBRECARGA: o disjuntor desarmou em %.1f s. Reduza a soma dos setores." % self.desarme
        elif dom["pico"] < 0.3:
            ver = "Reação fraca: quase nada chegou a disparar no córtex."
        else:
            ver = "Reação dominante: %s (pico %.2f em %.1f s)." % (dom["setor"], dom["pico"], dom["tpico"])
        return {"stats": stats, "mente": mente, "veredito": ver, "hud": self.hud()}


# ---------------------------------------------------------------------------
# Armazenamento dos cacos (cacos.json ao lado do script)
# ---------------------------------------------------------------------------
def carregar():
    salvos = {}
    try:
        with open(ARQ, encoding="utf-8") as f:
            salvos = json.load(f)
    except Exception:
        pass
    todos = dict(EXEMPLOS)
    todos.update(salvos)
    return todos, salvos


def gravar(salvos):
    with open(ARQ, "w", encoding="utf-8") as f:
        json.dump(salvos, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------------
SESSOES = {}
REDE = False                              # True só com --rede
PIN = ""                                  # PIN do modo Python em rede
TOKEN = secrets.token_urlsafe(16)         # exigido em todo POST (barra outros sites abrindo o servidor)


def _limpar():
    agora = time.time()
    for k in [k for k, s in SESSOES.items() if agora - s.vista > 300]:
        SESSOES.pop(k, None)
    while len(SESSOES) > 8:
        SESSOES.pop(min(SESSOES, key=lambda k: SESSOES[k].vista))


def _quatro(v):
    v = list(v) if isinstance(v, list) else []
    return [1 if (i < len(v) and v[i]) else 0 for i in range(4)]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _resp(self, corpo, tipo="application/json; charset=utf-8", cod=200):
        if not isinstance(corpo, bytes):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(cod)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _host_ok(self):
        h = (self.headers.get("Host") or "").strip()
        if h.startswith("[") and "]" in h:
            h = h[1:h.index("]")]
        elif ":" in h:
            h = h.rsplit(":", 1)[0]
        if h.lower() == "localhost":
            return True
        try:
            ipaddress.ip_address(h)
            return True
        except ValueError:
            return False

    def do_GET(self):
        if not self._host_ok():
            return self._resp({"erro": "host não permitido"}, cod=403)
        if self.path in ("/", "/index.html"):
            self._resp(PAGINA.replace("__TOKEN__", TOKEN).replace("__SENTIDOS__", json.dumps(SENTIDOS_JS)).encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/info":
            self._resp({"rede": REDE})
        elif self.path == "/api/cacos":
            self._resp(carregar()[0])
        else:
            self._resp({"erro": "não encontrado"}, cod=404)

    def do_POST(self):
        if not self._host_ok():
            return self._resp({"erro": "host não permitido"}, cod=403)
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 20000:
                raise ValueError("pedido grande demais")
            d = json.loads(self.rfile.read(n) or b"{}")
            if not secrets.compare_digest(str(d.get("tk", "")), TOKEN):
                raise ValueError("token inválido; recarregue a página")
            if self.path == "/api/iniciar":
                py_ok = (not REDE) or secrets.compare_digest(str(d.get("pin", "")), PIN)
                s = Sessao(str(d.get("codigo", "")), py_ok)
                _limpar()
                sid = secrets.token_hex(8)
                SESSOES[sid] = s
                self._resp({"sid": sid, "nome": s.nome, "fps": FPS, "total": s.total,
                            "botoes": s.botoes, "hud": s.hud(), "texto": s.ctx is not None})
            elif self.path == "/api/passo":
                s = SESSOES.get(str(d.get("sid", "")))
                if s is None:
                    raise ValueError("a sessão expirou; toque em Rodar de novo")
                fr = s.passo(max(1, min(15, int(d.get("n", 4)))), _quatro(d.get("b")), _quatro(d.get("p")),
                             bool(d.get("kill")), str(d.get("msg", ""))[:200])
                r = {"frames": fr, "hud": s.hud(), "fim": s.terminou()}
                if r["fim"]:
                    r["resumo"] = s.resumo()
                    SESSOES.pop(str(d.get("sid")), None)
                self._resp(r)
            elif self.path == "/api/salvar":
                cod = str(d.get("codigo", ""))
                if eh_python(cod):
                    try:
                        compile(cod, "<caco>", "exec")
                    except SyntaxError as e:
                        raise erro_py(e)
                    nome = nome_python(cod)
                else:
                    nome = interpretar(cod)["nome"]
                _, salvos = carregar()
                salvos[nome] = cod
                gravar(salvos)
                self._resp({"ok": True, "nome": nome})
            elif self.path == "/api/apagar":
                _, salvos = carregar()
                salvos.pop(str(d.get("nome", "")), None)
                gravar(salvos)
                self._resp({"ok": True})
            else:
                self._resp({"erro": "não encontrado"}, cod=404)
        except Exception as e:
            if not isinstance(e, ValueError):
                traceback.print_exc()      # erro inesperado: aparece no terminal
            self._resp({"erro": str(e)})


def ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    global REDE, PIN
    args = sys.argv[1:]
    REDE = "--rede" in args
    nums = [a for a in args if a.isdigit()]
    porta = int(nums[0]) if nums else 8000
    srv = ThreadingHTTPServer(("0.0.0.0" if REDE else "127.0.0.1", porta), H)
    print("DABOIT-BCI Lab v2.6 no ar.")
    print("  Neste aparelho: http://localhost:%d" % porta)
    if REDE:
        PIN = "%06d" % secrets.randbelow(10 ** 6)
        print("  Outro aparelho na Wi-Fi: http://%s:%d" % (ip_local(), porta))
        print("  PIN do modo Python (digite no app): %s" % PIN)
    else:
        print("  (só este aparelho acessa; para o celular acessar o PC use:  python bci_lab.py --rede)")
    print("  (Ctrl+C para parar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


# ---------------------------------------------------------------------------
# Interface (HTML/JS embutido)
# ---------------------------------------------------------------------------
PAGINA = r"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no,interactive-widget=resizes-content">
<title>DABOIT-BCI Lab</title>
<style>
:root{--bg:#0d0f14;--card:#171a22;--tx:#e8eaf0;--mut:#8b93a7;--ln:#2a2f3c}
*{box-sizing:border-box}body{margin:0 auto;background:var(--bg);color:var(--tx);font:15px system-ui,sans-serif;padding:10px;padding-top:max(10px,env(safe-area-inset-top));padding-bottom:max(10px,env(safe-area-inset-bottom));max-width:720px}
h1{font-size:18px;margin:4px 0 8px}h2{font-size:12px;color:var(--mut);margin:8px 0 2px;font-weight:600}.card{background:var(--card);border:1px solid var(--ln);border-radius:12px;padding:10px;margin-bottom:10px}
canvas{width:100%;display:block}#cerebro{height:300px}#linha{height:80px;margin-top:6px}
.bar{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:12px}.bar b{width:116px;color:var(--mut);font-weight:600}.bar i{flex:1;height:7px;background:#232736;border-radius:4px;overflow:hidden}.bar u{display:block;height:100%;width:0}
#hud{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}#hud span{background:#10131a;border-radius:8px;padding:4px 8px;font-size:12px;color:#cfe3ff}
#dock{display:none;position:fixed;left:0;right:0;bottom:0;max-width:720px;margin:0 auto;background:rgba(13,15,20,.97);border-top:1px solid var(--ln);padding:8px 10px;padding-bottom:max(8px,env(safe-area-inset-bottom));z-index:20}
#chat{max-height:92px;overflow-y:auto;font-size:13px;margin-bottom:6px}#chat:empty{display:none}#chat .eu{color:#9fc2ff}#chat .ele{color:#ffb4a0}#chat div{margin:2px 0}
#talk{display:none;gap:6px;margin-bottom:6px}#talk input{flex:1;min-width:0;padding:10px;border-radius:8px;border:1px solid var(--ln);background:#0b0d12;color:var(--tx);font:inherit}#talk button{padding:10px 12px}#bMic{display:none}#bMic.on{background:#b3202f;border-color:#b3202f}
#pad{display:none;gap:8px}#pad button{flex:1 1 0;min-width:0;padding:8px 2px;height:64px;font-weight:800;font-size:13px;touch-action:none;user-select:none;-webkit-user-select:none;background:#2a3350}#pad button.d{background:#2f6fed}
#ver{margin:8px 0 2px;font-weight:600}#st{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px;font-size:12px;color:var(--mut)}#st div{background:#10131a;border-radius:8px;padding:6px}
textarea{width:100%;height:260px;background:#0b0d12;color:#cfe3ff;border:1px solid var(--ln);border-radius:8px;padding:8px;font:13px ui-monospace,monospace;resize:vertical;margin-top:6px}
select,button{font:inherit;border-radius:8px;border:1px solid var(--ln);background:#222737;color:var(--tx);padding:10px 12px}
.row{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}.row>*{flex:1}
button.go{background:#2f6fed;border-color:#2f6fed;font-weight:700}button.kill.on{background:#b3202f;border-color:#b3202f}
#erro{color:#ff6b7a;font-size:13px;min-height:16px;margin-top:6px}details{font-size:13px;color:var(--mut)}code{color:#cfe3ff}p{margin:6px 0}
</style></head><body>
<h1>🧠 DABOIT-BCI Lab <small style="color:var(--mut);font-weight:400">v2.6</small></h1>
<div class="card">
 <canvas id="cerebro"></canvas>
 <h2>Reação por setor</h2><div id="bars"></div>
 <h2>Estado mental estimado (modelo fictício)</h2><div id="mbars"></div>
 <div id="hud"></div>
 <div id="ver">Escolha um exemplo ou escreva o seu e toque em ▶ Rodar</div>
 <canvas id="linha"></canvas>
 <div id="st"></div>
</div>
<div class="card">
 <select id="sel" style="width:100%"></select>
 <textarea id="cod" spellcheck="false" autocapitalize="off" autocorrect="off" autocomplete="off"></textarea>
 <input id="pin" type="password" inputmode="numeric" placeholder="PIN do terminal (necessário p/ Python em rede)" style="display:none;width:100%;margin-top:6px;padding:10px;border-radius:8px;border:1px solid var(--ln);background:#0b0d12;color:var(--tx)">
 <div id="erro"></div>
 <div class="row"><button class="go" id="bRodar">▶ Rodar</button><button id="bParar">■ Parar</button><button id="bKill" class="kill">⏻ Disjuntor</button></div>
 <div class="row"><button id="bSalvar">💾 Salvar</button><button id="bApagar">🗑 Apagar</button><button id="bReset">🔄 Resetar</button></div>
</div>
<details class="card"><summary>Como programar um caco</summary>
<p>Uma linha por item, no formato <code>nome = expressão</code>. O programa roda 30 vezes por segundo. Comentário com <code>#</code>.</p>
<p><b>Saídas (14 sentidos):</b> <code>visao audicao tato olfato paladar equilibrio temperatura propriocepcao dor coracao fome senso_tempo bussola radar</code> (0 = nada, 1 = forte, acima = sobrecarga).</p>
<p><b>Config:</b> <code>nome</code>, <code>duracao</code> (1–120 s), <code>botoes = A, B, C, D</code> (até 4 botões de toque), <code>fim = condição</code> (encerra quando for verdadeira).</p>
<p><b>Memória:</b> <code>var x = 0</code> declara uma variável que mantém o valor entre quadros; depois <code>x = x + dt</code> a atualiza. Sem <code>var</code>, é só um valor temporário do quadro.</p>
<p><b>Entradas:</b> <code>t d dt pi</code> · <code>b1..b4</code> botão segurado · <code>p1..p4</code> só no quadro do toque · <code>foco calma euforia estresse imersao</code> e <code>r_visao … r_radar</code> (a reação do cérebro no quadro anterior: dá para criar circuitos de feedback).</p>
<p><b>Funções:</b> <code>rampa(t,a,b) degrau(t,a) pulso(t,centro,larg) onda(t,freq) ruido(t,s) rand() limita(x,a,b) sin cos abs min max sqrt exp</code>. Condição: <code>a if cond else b</code> com <code>and or not &lt; &gt; ==</code>. Teclas 1–4 também apertam os botões no PC.</p>
<p><b>Modo Python:</b> se o código tiver <code>def quadro(c):</code>, ele roda como Python de verdade (import, classes, laços…). Opcionais: <code>NOME</code>, <code>DURACAO</code>, <code>BOTOES = ["A","B"]</code> e <code>def inicio(c)</code>. Entradas: <code>c.t c.dt c.b1 c.p1 c.foco c.estresse c.r_visao</code>… Saídas: <code>c.visao c.audicao c.tato c.olfato c.paladar c.equilibrio c.temperatura c.propriocepcao c.dor c.coracao c.fome c.senso_tempo c.bussola c.radar</code>. Extras: <code>c.msg</code> (o que você escreveu/falou), <code>c.diz("oi","Nome")</code> (resposta na conversa), <code>c.hud["pontos"]=3</code>, <code>c.fim()</code>, estado em <code>c.x</code> ou <code>global</code>. Veja o exemplo "Python: ritmo". Esse modo tem acesso total ao aparelho: rode só código em que confia.</p>
<p>O modelo dá inércia a cada setor, adaptação neural e leve contaminação entre sentidos; se a soma passar de 5.5 por 1,5 s o disjuntor desarma. É uma simulação fictícia, sem base clínica.</p></details>
<div id="dock"><div id="chat"></div>
 <div id="talk"><input id="msg" type="text" placeholder="Fale com ele..." maxlength="200" autocomplete="off" enterkeyhint="send"><button id="bMic" title="falar no microfone">🎤</button><button id="bEnv" class="go">Enviar</button></div>
 <div id="pad"></div></div>
<script>
const $=id=>document.getElementById(id);
addEventListener('error',e=>{const m=String(e.message||'');if(/ResizeObserver/i.test(m))return;const x=$('erro');if(x)x.textContent='⚠ erro na página: '+m+(e.lineno?' (linha '+e.lineno+')':'')});
addEventListener('unhandledrejection',e=>{const m=String(e.reason&&e.reason.message||e.reason);if(/ResizeObserver/i.test(m))return;const x=$('erro');if(x)x.textContent='⚠ erro: '+m});
const TK='__TOKEN__';
const S=__SENTIDOS__;
const R=S.map(s=>s.rot),C=S.map(s=>s.cor),CEN=S.map(s=>s.c),RAIO=S.map(s=>s.r),NEL=S.map(s=>s.n),Z=()=>S.map(_=>0);
const MR=["FOCO","CALMA","EUFORIA","ESTRESSE","IMERSÃO"],MC=["#e0e0ff","#7be0d0","#ffd24a","#ff7a59","#a0a8ff"];
const cv=$('cerebro'),cx=cv.getContext('2d'),tl=$('linha'),tx=tl.getContext('2d');
let sid=null,run=0,rodando=false,killed=false,pend=false,fimSrv=false,res=null,fila=[],all=[],cur=null,acc=0,last=0,total=1,cacos={};
let held=[0,0,0,0],pres=[0,0,0,0],msgs=[];
let seed=7;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
const EL=[];R.forEach((_,k)=>{let n=0,g=0;while(n<NEL[k]&&g++<3000){const a=rnd()*6.283,r=Math.sqrt(rnd())*RAIO[k];
 const x=CEN[k][0]+Math.cos(a)*r,y=CEN[k][1]+Math.sin(a)*r*1.4;if(((x-.5)/.46)**2+((y-.48)/.38)**2<.9){EL.push({k,x,y,f:0});n++}}});
const barras=(box,id,N,CC)=>$(box).innerHTML=N.map((n,k)=>`<div class="bar"><b>${n}</b><i><u id="${id}${k}" style="background:${CC[k]}"></u></i></div>`).join('');
barras('bars','b',R,C);barras('mbars','m',MR,MC);
function fit(c){const d=devicePixelRatio||1;c.width=c.clientWidth*d;c.height=c.clientHeight*d;c.getContext('2d').setTransform(d,0,0,d,0,0)}
function hex(x,y,r){cx.beginPath();for(let i=0;i<6;i++){const a=i*Math.PI/3;cx[i?'lineTo':'moveTo'](x+r*Math.cos(a),y+r*Math.sin(a))}cx.closePath()}
function cerebro(lv,morto){const w=cv.clientWidth,h=cv.clientHeight;cx.clearRect(0,0,w,h);
 cx.fillStyle='#3a322f';cx.beginPath();cx.ellipse(.24*w,.84*h,.14*w,.1*h,0,0,7);cx.fill();cx.fillRect(.4*w,.78*h,.06*w,.2*h);
 cx.fillStyle='#22232b';cx.strokeStyle='#555';cx.lineWidth=2;cx.beginPath();cx.ellipse(.5*w,.48*h,.48*w,.4*h,0,0,7);cx.fill();cx.stroke();
 for(const e of EL){if(!morto&&Math.random()<lv[e.k]*.35)e.f=1;e.f*=.85;
  cx.shadowBlur=e.f>.3?12:0;cx.shadowColor=C[e.k];cx.globalAlpha=.16+.84*e.f;cx.fillStyle=C[e.k];hex(e.x*w,e.y*h,w*.016);cx.fill()}
 cx.shadowBlur=0;cx.globalAlpha=1;cx.font='8px system-ui';cx.fillStyle='#8b93a7';cx.textAlign='center';
 R.forEach((n,k)=>cx.fillText(n,CEN[k][0]*w,(CEN[k][1]+RAIO[k]*1.4+.05)*h));
 if(morto){cx.fillStyle='rgba(179,32,47,.9)';cx.font='bold 15px system-ui';cx.fillText('DISJUNTOR DESARMADO',w/2,.1*h)}}
function linha(){const w=tl.clientWidth,h=tl.clientHeight;tx.clearRect(0,0,w,h);const n=all.length;if(!n)return;
 C.forEach((c,k)=>{tx.strokeStyle=c;tx.lineWidth=1.5;tx.beginPath();for(let p=0;p<n;p+=2){const x=p/total*w,y=h-2-Math.min(1.5,all[p][k])/1.5*(h-4);tx[p?'lineTo':'moveTo'](x,y)}tx.stroke()});
 tx.strokeStyle='#fff';tx.beginPath();tx.moveTo(n/total*w,0);tx.lineTo(n/total*w,h);tx.stroke()}
function mostrar(f){const morto=killed||!!f.x,v=morto?Z():f.l;cerebro(v,morto);
 v.forEach((x,k)=>$('b'+k).style.width=Math.min(100,x/1.2*100)+'%');f.m.forEach((x,k)=>$('m'+k).style.width=Math.min(100,x*100)+'%')}
function dock(){const d=$('dock');if(d.style.display==='block')document.body.style.paddingBottom=(d.offsetHeight+16)+'px'}
if(window.ResizeObserver)new ResizeObserver(()=>dock()).observe($('dock'));
function chat(q,t){const c=$('chat'),d=document.createElement('div');d.className=q;d.textContent=t;c.appendChild(d);
 while(c.children.length>30)c.removeChild(c.firstChild);c.scrollTop=c.scrollHeight;dock()}
function enviar(){const i=$('msg'),t=i.value.trim();if(!t||!rodando)return;msgs.push(t);chat('eu','Você: '+t);i.value='';i.focus()}
function hud(h){$('hud').innerHTML=Object.entries(h||{}).map(([k,v])=>`<span>${k}: <b>${v}</b></span>`).join('')}
let tm=0,t0=0,resp0=0,avisoSrv=0;
function tick(){if(!rodando){clearInterval(tm);tm=0;return}
 try{loop(performance.now())}catch(e){rodando=false;clearInterval(tm);$('erro').textContent='⚠ erro na animação: '+e.message}}
function loop(now){const dtm=Math.min(100,Math.max(0,now-last||0));acc=Math.min(3,acc+dtm/1000*30);last=now;
 while(acc>=1){if(fila.length){cur=fila.shift();all.push(cur.l);acc-=1;if(cur.fala)cur.fala.forEach(f=>chat('ele',(f[0]?f[0]+': ':'')+f[1]))}else{if(fimSrv){terminar();return}acc=Math.min(acc,1);break}}
 if(cur){mostrar(cur);linha();if(avisoSrv){$('erro').textContent='';avisoSrv=0}}else if(pend&&now-Math.max(t0,resp0)>8000){$('erro').textContent='⚠ o servidor não está respondendo. O Lab ainda está rodando no terminal?';avisoSrv=1}pedir()}
const pinv=()=>{try{return sessionStorage.pin||''}catch(_){return ''}};
async function api(u,b){const r=await fetch(u,{method:'POST',body:JSON.stringify(Object.assign({tk:TK,pin:pinv()},b))});return r.json()}
function erroSrv(m){const x=$('erro');if(/token inválido/.test(m)){x.textContent='⚠ página desatualizada (o Lab foi reiniciado). Recarregando...';setTimeout(()=>location.reload(),900)}else x.textContent='⚠ '+m}
function pedir(){if(pend||fimSrv||fila.length>=6)return;pend=true;const my=run;
 const b=held.map((h,i)=>h|pres[i]),p=pres.slice();pres=[0,0,0,0];const msg=msgs.shift()||'';
 api('/api/passo',{sid,n:4,b,p,kill:killed,msg}).then(j=>{if(my!==run)return;pend=false;resp0=performance.now();
  if(j.erro){rodando=false;erroSrv(j.erro);return}
  fila.push(...j.frames);hud(j.hud);if(j.fim){fimSrv=true;res=j.resumo}}).catch(e=>{if(my===run){pend=false;rodando=false;$('erro').textContent='⚠ falha ao falar com o servidor ('+(e&&e.message||e)+'). Veja o terminal: o Lab ainda está rodando?'}})}
function terminar(){rodando=false;if(res){$('ver').textContent=res.veredito;hud(res.hud);
 $('st').innerHTML=res.stats.map((s,k)=>`<div style="border-left:3px solid ${C[k]}"><b style="color:#e8eaf0">${s.setor}</b><br>pico ${s.pico} (${s.tpico}s) · média ${s.media}<br>ativo ${s.ativo}s</div>`).join('')+
 `<div style="grid-column:1/3">Média mental: ${MR.map((n,k)=>n+' '+Math.round(res.mente[k]*100)+'%').join(' · ')}</div>`}}
$('bRodar').onclick=async()=>{$('erro').textContent='';const my=++run;rodando=false;$('ver').textContent='⏳ iniciando...';
 let j;try{j=await api('/api/iniciar',{codigo:$('cod').value})}catch(e){if(my===run)$('erro').textContent='⚠ sem conexão com o servidor';return}if(my!==run)return;
 if(j.erro){erroSrv(j.erro);return}
 sid=j.sid;total=j.total;fila=[];all=[];cur=null;res=null;fimSrv=false;pend=false;killed=false;$('bKill').classList.remove('on');
 held=[0,0,0,0];pres=[0,0,0,0];msgs=[];$('chat').innerHTML='';$('st').innerHTML='';$('ver').textContent='▶ '+j.nome;hud(j.hud);
 const pad=$('pad');pad.style.display=j.botoes.length?'flex':'none';$('talk').style.display=j.texto?'flex':'none';$('dock').style.display='block';dock();
 pad.innerHTML=j.botoes.map((n,i)=>`<button data-i="${i}">${n.replace(/</g,'&lt;')}</button>`).join('');
 pad.querySelectorAll('button').forEach(b=>{const i=+b.dataset.i;
  const dn=e=>{e.preventDefault();held[i]=1;pres[i]=1;b.classList.add('d')},up=e=>{e.preventDefault();held[i]=0;b.classList.remove('d')};
  b.addEventListener('pointerdown',dn);['pointerup','pointercancel','pointerleave'].forEach(ev=>b.addEventListener(ev,up))});
 rodando=true;last=t0=performance.now();acc=0;clearInterval(tm);tm=setInterval(tick,33)};
$('bParar').onclick=()=>{run++;rodando=false;$('ver').textContent='■ parado'};
$('bKill').onclick=()=>{killed=!killed;$('bKill').classList.toggle('on',killed);if(!rodando)cerebro(Z(),killed)};
addEventListener('keydown',e=>{if(['TEXTAREA','INPUT'].includes(document.activeElement.tagName)||!'1234'.includes(e.key)||e.repeat)return;const i=+e.key-1;held[i]=1;pres[i]=1});
addEventListener('keyup',e=>{if('1234'.includes(e.key)&&e.key)held[+e.key-1]=0});
async function lista(escolher){cacos=await (await fetch('/api/cacos')).json();const s=$('sel');
 s.innerHTML=Object.keys(cacos).map(n=>`<option>${n.replace(/</g,'&lt;')}</option>`).join('');
 if(escolher&&cacos[escolher])s.value=escolher;$('cod').value=cacos[s.value]||''}
$('sel').onchange=()=>{$('cod').value=cacos[$('sel').value]};
$('bSalvar').onclick=async()=>{const j=await api('/api/salvar',{codigo:$('cod').value});
 if(j.erro){erroSrv(j.erro);return}$('erro').textContent='✔ salvo como "'+j.nome+'"';await lista(j.nome)};
$('bReset').onclick=()=>{try{if($('cod').value!==(cacos[$('sel').value]||'')&&!confirm('Resetar a página? As alterações não salvas no código serão perdidas.'))return}catch(_){}
 run++;rodando=false;clearInterval(tm);try{location.reload()}catch(_){location.href=location.pathname}};
$('bApagar').onclick=async()=>{if(!confirm('Apagar "'+$('sel').value+'"? (os exemplos voltam sozinhos)'))return;
 await api('/api/apagar',{nome:$('sel').value});await lista()};
addEventListener('resize',()=>{dock();fit(cv);fit(tl);if(!rodando)cerebro(Z(),killed)});
fit(cv);fit(tl);cerebro(Z(),false);lista();
try{$('bEnv').onclick=enviar;$('msg').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();enviar()}});
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){$('bMic').style.display='block';let rec=null;$('bMic').onclick=()=>{try{if(rec){rec.stop();return}
 rec=new SR();rec.lang='pt-BR';rec.interimResults=false;
 rec.onresult=e=>{$('msg').value=e.results[0][0].transcript;enviar()};
 rec.onend=()=>{rec=null;$('bMic').classList.remove('on')};rec.onerror=()=>{};
 $('bMic').classList.add('on');rec.start()}catch(_){rec=null}}}
}catch(e){console.error(e)}
fetch('/api/info').then(r=>r.json()).then(j=>{if(j.rede){$('pin').style.display='block';$('pin').value=pinv();$('pin').oninput=()=>{try{sessionStorage.pin=$('pin').value}catch(_){}}}}).catch(()=>{});
</script></body></html>
"""

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DABOIT-BCI-1 · SIMULADOR SINESTÉSICO
====================================
Duas janelas rodando ao mesmo tempo (dois processos):

  JANELA 1 - o jogo (3 cenários):  1) Tomar vinho   2) Correr na praia   3) Dirigir moto
  JANELA 2 - cérebro 3D girável com a malha de eletrodos hexagonais de grafeno.
             Conforme você age no jogo, os eletrodos do setor correspondente
             disparam (VISÃO, AUDIÇÃO, TATO, OLFATO, PALADAR), como no README
             "daboit-bci-architecture".

Instalação:   pip install pygame numpy
Execução:     python daboit_bci_game.py

Teclas globais (janela do jogo):  1/2/3 escolhe o jogo · ESC volta ao menu · K disjuntor (kill switch)
Janela do cérebro:                arrastar com o mouse gira · roda do mouse dá zoom · ESPAÇO liga/desliga rotação automática
"""
import math
import multiprocessing as mp
import os
import random
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import numpy as np
import pygame

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------------------------
GAME_W, GAME_H = 880, 540
BRAIN_W, BRAIN_H = 640, 540
GAME_POS = (30, 50)
BRAIN_POS = (GAME_POS[0] + GAME_W + 12, GAME_POS[1])

SETORES = ["VISAO", "AUDICAO", "TATO", "OLFATO", "PALADAR"]
ROTULO = {"VISAO": "VISÃO", "AUDICAO": "AUDIÇÃO", "TATO": "TATO", "OLFATO": "OLFATO", "PALADAR": "PALADAR"}
LOBO = {"VISAO": "Occipital", "AUDICAO": "Temporal", "TATO": "Parietal",
        "OLFATO": "Orbitofrontal", "PALADAR": "Insular"}
COR = {"VISAO": (70, 150, 255), "AUDICAO": (70, 230, 140), "TATO": (255, 170, 60),
       "OLFATO": (200, 110, 255), "PALADAR": (255, 90, 110)}
COR_ARR = np.array([COR[s] for s in SETORES] + [(0, 0, 0)], dtype=float)
# Proporção do README (10/10/10/5/5 hexágonos) multiplicada por 4 para ficar bonito na tela
HEX_POR_SETOR = {"VISAO": 40, "AUDICAO": 40, "TATO": 40, "OLFATO": 20, "PALADAR": 20}


# ----------------------------------------------------------------------------
# UTILITÁRIOS
# ----------------------------------------------------------------------------
def clamp(v, a=0.0, b=1.0):
    return a if v < a else (b if v > b else v)


def lerp(a, b, t):
    return a + (b - a) * t


def _c(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


def mix(c1, c2, t):
    return (_c(c1[0] + (c2[0] - c1[0]) * t), _c(c1[1] + (c2[1] - c1[1]) * t), _c(c1[2] + (c2[2] - c1[2]) * t))


def esc(c, f):
    return (_c(c[0] * f), _c(c[1] * f), _c(c[2] * f))


def ease_in(a, b, p):
    return a + (b - a) * (p * p)


def ease_inout(a, b, p):
    return a + (b - a) * ((-math.cos(p * math.pi) / 2) + 0.5)


def txt(tela, fonte, s, x, y, cor=(240, 240, 240), centro=False, sombra=True):
    img = fonte.render(s, True, cor)
    px = x - img.get_width() // 2 if centro else x
    if sombra:
        tela.blit(fonte.render(s, True, (0, 0, 0)), (px + 1, y + 1))
    tela.blit(img, (px, y))


_cache_grad = {}


def gradiente(w, h, topo, base):
    k = (w, h, topo, base)
    s = _cache_grad.get(k)
    if s is None:
        s = pygame.Surface((w, h))
        for y in range(h):
            pygame.draw.line(s, mix(topo, base, y / max(1, h - 1)), (0, y), (w, y))
        _cache_grad[k] = s
    return s


def glow_surf(cor, raio, inten):
    s = pygame.Surface((raio * 2, raio * 2))
    s.fill((0, 0, 0))
    for r in range(raio, 1, -2):
        f = (1 - r / raio) ** 1.6 * inten
        pygame.draw.circle(s, (int(cor[0] * f), int(cor[1] * f), int(cor[2] * f)), (raio, raio), r)
    return s


# ----------------------------------------------------------------------------
# MODELO 3D DO CÉREBRO (numpy puro)
# ----------------------------------------------------------------------------
class ModeloCerebro:
    """Córtex procedural (nuvem de pontos) + cerebelo + tronco + eletrodos hexagonais por setor."""

    def __init__(self, n=3000, seed=11):
        rng = np.random.default_rng(seed)
        i = np.arange(n) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        th = math.pi * (1 + 5 ** 0.5) * i
        ux = np.cos(th) * np.sin(phi)
        uy = np.cos(phi)
        uz = np.sin(th) * np.sin(phi)          # +z = frente do cérebro, +y = topo

        giro = np.sin(11 * ux + 2 * uy) * np.sin(9 * uy + 3 * uz) * np.sin(10 * uz + ux)   # "giros/sulcos"
        r = 1 + 0.05 * giro
        r = r - 0.20 * np.exp(-(ux / 0.07) ** 2) * (uy > -0.15)                            # fissura longitudinal
        py = 0.62 * uy * r
        py = np.where(uy < 0, py * 0.72, py)
        cort = np.stack([0.80 * ux * r, py, 1.0 * uz * r], axis=1)

        # Mapeamento cortical (README): 0 visão, 1 audição, 2 tato, 3 olfato, 4 paladar, -1 = frontal motor (sem malha)
        ax = np.abs(ux)
        reg = np.full(n, -1)
        reg[(ax > 0.38) & (uy < 0.15) & (uy > -0.78) & (uz > -0.55) & (uz < 0.5)] = 1
        reg[(uy > 0.15) & (uz > -0.55) & (uz < 0.08)] = 2
        reg[(uz <= -0.55) & (uy > -0.6)] = 0
        reg[(uz > 0.45) & (uy < -0.05) & (ax < 0.6)] = 3
        reg[(ax > 0.72) & (uy > -0.12) & (uy < 0.22) & (uz > 0.02) & (uz < 0.45)] = 4

        cinza = np.array([150.0, 142.0, 150.0])
        cores = np.tile(cinza, (n, 1)) * (0.88 + 0.12 * giro)[:, None]
        for k, s in enumerate(SETORES):
            mk = reg == k
            cores[mk] = cores[mk] * 0.62 + np.array(COR[s], dtype=float) * 0.38
        cores[reg == -1] *= 0.80

        # cerebelo e tronco encefálico
        m = 420
        v = rng.normal(size=(m, 3))
        v /= np.linalg.norm(v, axis=1)[:, None]
        cer = np.stack([0.42 * v[:, 0], -0.52 + 0.20 * v[:, 1], -0.72 + 0.30 * v[:, 2]], axis=1)
        cc = np.array([128.0, 104.0, 98.0])[None, :] * (0.85 + 0.15 * np.sin(38 * v[:, 1]))[:, None]
        a = rng.random(100) * 2 * math.pi
        t = rng.random(100)
        tr = np.stack([0.07 * np.cos(a), -0.40 - 0.50 * t, -0.28 - 0.10 * t + 0.07 * np.sin(a)], axis=1)
        ct = np.tile(np.array([140.0, 118.0, 112.0]), (100, 1))

        self.n_cort = n
        self.pos = np.vstack([cort, cer, tr])
        self.cor = np.vstack([cores, cc, ct])
        self.reg = np.concatenate([reg, np.full(m + 100, -1)])
        self.reg_idx = np.where(self.reg >= 0, self.reg, 5)       # 5 = sem setor
        self.centros = np.array([cort[reg == k].mean(axis=0) if (reg == k).any() else np.zeros(3) for k in range(5)])
        dist = np.zeros(len(self.pos))
        for k in range(5):
            mk = self.reg == k
            dist[mk] = np.linalg.norm(self.pos[mk] - self.centros[k], axis=1)
        self.dist_centro = dist

        # eletrodos (hexágonos): amostragem de pontos mais distantes entre si dentro de cada setor
        el_pos, el_set, el_nor = [], [], []
        for k, s in enumerate(SETORES):
            idx = np.where(reg == k)[0]
            sel = self._amostrar(cort[idx], min(HEX_POR_SETOR[s], len(idx)), rng)
            for j in sel:
                p = idx[j]
                el_pos.append(cort[p] * 1.02)
                el_set.append(k)
                el_nor.append(np.array([ux[p], uy[p], uz[p]]))
        self.el_pos = np.array(el_pos)
        self.el_set = np.array(el_set)
        self.el_nor = np.array(el_nor)
        E = len(self.el_pos)
        self.vizinhos = [[] for _ in range(E)]
        arestas = set()
        for k in range(5):
            ids = np.where(self.el_set == k)[0]
            if len(ids) < 2:
                continue
            P = self.el_pos[ids]
            D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
            np.fill_diagonal(D, 1e9)
            for aa in range(len(ids)):
                for bb in np.argsort(D[aa])[:3]:
                    i1, j1 = int(ids[aa]), int(ids[bb])
                    self.vizinhos[i1].append(j1)
                    arestas.add((min(i1, j1), max(i1, j1)))
        self.arestas = sorted(arestas)
        self.qtd = [int((self.el_set == k).sum()) for k in range(5)]

    @staticmethod
    def _amostrar(pts, k, rng):
        idx = [int(rng.integers(len(pts)))]
        d = np.linalg.norm(pts - pts[idx[0]], axis=1)
        for _ in range(k - 1):
            j = int(np.argmax(d))
            idx.append(j)
            d = np.minimum(d, np.linalg.norm(pts - pts[j], axis=1))
        return idx


def matriz_rot(yaw, pitch):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return rx @ ry


# ----------------------------------------------------------------------------
# PROCESSO 2: JANELA DO CÉREBRO
# ----------------------------------------------------------------------------
def processo_cerebro(fila, max_frames=None):
    os.environ["SDL_VIDEO_WINDOW_POS"] = "%d,%d" % BRAIN_POS
    pygame.init()
    tela = pygame.display.set_mode((BRAIN_W, BRAIN_H))
    pygame.display.set_caption("DABOIT-BCI-1 · Córtex 3D · Malha de grafeno")
    relogio = pygame.time.Clock()
    mono = "dejavusansmono,consolas,menlo,couriernew,monospace"
    f_p = pygame.font.SysFont(mono, 13)
    f_n = pygame.font.SysFont(mono, 14, bold=True)
    f_t = pygame.font.SysFont(mono, 11)

    m = ModeloCerebro()
    E = len(m.el_pos)
    glows = {s: [glow_surf(COR[s], 30, f) for f in (0.30, 0.55, 0.8, 1.0)] for s in SETORES}
    rng = np.random.default_rng(3)

    alvo = np.zeros(5)
    niv = np.zeros(5)
    cena_nome, sens, kill = "STANDBY", "Aguardando fluxo sensorial", False
    yaw, pitch, zoom = -1.25, 0.18, 1.0
    arrastando, auto, auto_t = False, True, 0.0
    t_msg = time.time()
    fogo = np.zeros(E)
    pend = []
    uv = np.random.uniform(8, 45, 5)
    t_uv = 0.0
    tempo = 0.0
    frames = 0
    CX, CY = BRAIN_W // 2, 232
    rodando = True

    while rodando:
        dt = min(0.05, relogio.tick(60) / 1000.0)
        agora = time.time()
        tempo += dt
        frames += 1
        if max_frames is not None and frames > max_frames:
            break

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                rodando = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                arrastando, auto = True, False
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                arrastando = False
            elif ev.type == pygame.MOUSEMOTION and arrastando:
                yaw += ev.rel[0] * 0.01
                pitch = clamp(pitch + ev.rel[1] * 0.01, -1.3, 1.3)
            elif ev.type == pygame.MOUSEWHEEL:
                zoom = clamp(zoom * (1 + 0.08 * ev.y), 0.5, 2.2)
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                auto = not auto

        # mensagens do jogo
        try:
            while True:
                msg = fila.get_nowait()
                if msg.get("sair"):
                    rodando = False
                else:
                    alvo = np.array(msg["niv"], dtype=float)
                    cena_nome, sens, kill = msg["cena"], msg["sens"], msg["kill"]
                    t_msg = agora
        except Exception:
            pass
        if kill or agora - t_msg > 2.0:
            alvo = np.zeros(5)
        niv += (alvo - niv) * min(1.0, dt * 7)

        # leitura simulada (µV) para setores em repouso
        t_uv -= dt
        if t_uv <= 0:
            uv = np.random.uniform(8, 45, 5)
            t_uv = 0.3

        # disparo dos eletrodos + propagação para vizinhos
        prob = np.clip(niv[m.el_set] * 0.11 * dt * 60, 0, 0.6)
        disp = rng.random(E) < prob
        for i in np.nonzero(disp)[0].tolist():
            fogo[i] = 1.0
            for j in m.vizinhos[i]:
                if rng.random() < 0.5:
                    pend.append((agora + 0.06 + 0.05 * rng.random(), j))
        if pend:
            resto = []
            for tt, j in pend:
                if tt <= agora:
                    fogo[j] = max(fogo[j], 0.75)
                else:
                    resto.append((tt, j))
            pend = resto[-400:]
        fogo = np.maximum(fogo - dt * 3.5, 0.0)

        # ---- câmera
        if auto:
            auto_t += dt
        yaw_ef = yaw + (0.85 * math.sin(auto_t * 0.35) if auto else 0.0)
        R = matriz_rot(yaw_ef, pitch)
        D = 3.6
        base_esc = 235.0 * zoom

        P = m.pos @ R.T
        z2 = P[:, 2]
        persp = D / (D - z2)
        sx = (CX + P[:, 0] * persp * base_esc).astype(int)
        sy = (CY - P[:, 1] * persp * base_esc).astype(int)

        # cores: base * sombra de profundidade + brilho do setor com onda viajante
        sombra = 0.50 + 0.50 * np.clip((z2 + 1.0) / 2.0, 0, 1)
        niv_ext = np.append(niv, 0.0)
        onda = 0.55 + 0.45 * np.sin(m.dist_centro * 9.0 - tempo * 7.0)
        brilho = niv_ext[m.reg_idx] * onda
        cores = np.clip(m.cor * sombra[:, None] + COR_ARR[m.reg_idx] * brilho[:, None] * 0.9, 0, 255).astype(int)

        # ---- desenho
        tela.fill((7, 9, 16))
        ordem = np.argsort(z2).tolist()
        cl = cores.tolist()
        sxl, syl = sx.tolist(), sy.tolist()
        grande = (z2 > 0.25).tolist()
        for k in ordem:
            tm = 3 if grande[k] else 2
            tela.fill(cl[k], (sxl[k], syl[k], tm, tm))

        # eletrodos
        Pe = (m.el_pos * (1.0 + 0.05 * fogo)[:, None]) @ R.T
        Ne = m.el_nor @ R.T
        pe = D / (D - Pe[:, 2])
        ex = (CX + Pe[:, 0] * pe * base_esc)
        ey = (CY - Pe[:, 1] * pe * base_esc)
        vis = (Ne[:, 2] > -0.05).tolist()
        exl, eyl, pel = ex.tolist(), ey.tolist(), pe.tolist()
        fl = fogo.tolist()
        for (i, j) in m.arestas:
            if vis[i] and vis[j]:
                f = max(fl[i], fl[j])
                c0 = COR[SETORES[int(m.el_set[i])]]
                pygame.draw.line(tela, esc(c0, 0.16 + 0.75 * f), (exl[i], eyl[i]), (exl[j], eyl[j]), 1)
        for i in range(E):
            if not vis[i]:
                continue
            s = SETORES[int(m.el_set[i])]
            f = fl[i]
            raio = (5.5 + 3.5 * f) * pel[i] * zoom
            cx_, cy_ = exl[i], eyl[i]
            if f > 0.12:
                g = glows[s][min(3, int(f * 4))]
                tela.blit(g, (cx_ - 30, cy_ - 30), special_flags=pygame.BLEND_RGB_ADD)
            cor_h = mix(esc(COR[s], 0.35 + 0.08), (255, 255, 255), 0.0)
            cor_h = mix(cor_h, mix(COR[s], (255, 255, 255), 0.55), f)
            pts = [(cx_ + raio * math.cos(math.radians(60 * q + 30)),
                    cy_ + raio * math.sin(math.radians(60 * q + 30))) for q in range(6)]
            pygame.draw.polygon(tela, cor_h, pts)
            pygame.draw.polygon(tela, esc(cor_h, 0.55), pts, 1)

        # rótulos dos lobos
        for k, s in enumerate(SETORES):
            c = m.centros[k] * 1.12
            pc = R @ c
            nrm = R @ (m.centros[k] / (np.linalg.norm(m.centros[k]) + 1e-9))
            if nrm[2] > 0.25:
                pp = D / (D - pc[2])
                txt(tela, f_t, LOBO[s].upper(), int(CX + pc[0] * pp * base_esc), int(CY - pc[1] * pp * base_esc) - 6,
                    esc(COR[s], 0.9), centro=True)

        # ---- cabeçalho (inspirado no painel do README)
        escrita = float(niv.max()) > 0.15
        modo = "ESCRITA / INJEÇÃO SINESTÉSICA DIRETA" if escrita else "LEITURA / CAPTURA MULTISENSORIAL"
        txt(tela, f_n, "CONGLOMERADO DABOIT · SISTEMA OPERACIONAL NEURAL", 10, 6, (230, 235, 255))
        txt(tela, f_p, "ARQUITETURA DE SINESTESIA TOTAL (DABOIT-BCI-1)", 10, 24, (140, 150, 180))
        txt(tela, f_p, "MODO ATUAL: [ %s ]" % modo, 10, 40, (255, 210, 120) if escrita else (130, 220, 255))
        txt(tela, f_p, ("CENÁRIO: %s | SENSAÇÃO: %s" % (cena_nome, sens))[:80], 10, 56, (200, 205, 220))

        # ---- painel dos setores
        y0 = 392
        for k, s in enumerate(SETORES):
            y = y0 + k * 24
            txt(tela, f_p, ROTULO[s], 12, y, COR[s])
            txt(tela, f_t, LOBO[s], 84, y + 2, (130, 138, 160))
            pygame.draw.rect(tela, (28, 32, 46), (176, y + 3, 170, 12))
            pygame.draw.rect(tela, COR[s], (176, y + 3, int(170 * clamp(float(niv[k]))), 12))
            if niv[k] > 0.10:
                ativos = int((fogo[m.el_set == k] > 0.3).sum())
                txt(tela, f_p, "INJETANDO ESTÍMULO %d/%d" % (ativos, m.qtd[k]), 356, y, (255, 215, 130))
            else:
                txt(tela, f_p, "LENDO TRÁFEGO: %.1fµV" % uv[k], 356, y, (140, 150, 175))
        txt(tela, f_t, "mouse: girar · roda: zoom · ESPAÇO: rotação auto · área frontal-motora sem malha (cinza)",
            10, BRAIN_H - 16, (100, 108, 130), sombra=False)

        if kill:
            ov = pygame.Surface((BRAIN_W, BRAIN_H), pygame.SRCALPHA)
            ov.fill((120, 0, 0, 90))
            tela.blit(ov, (0, 0))
            txt(tela, f_n, "DISJUNTOR MECÂNICO ACIONADO · SISTEMA ISOLADO", BRAIN_W // 2, 300, (255, 120, 120), centro=True)

        pygame.display.flip()
    pygame.quit()


# ----------------------------------------------------------------------------
# SONS (gerados por código - sem arquivos externos)
# ----------------------------------------------------------------------------
class Sons:
    SR = 22050

    def __init__(self):
        self.ok = False
        self.s = {}
        self.canais = {}
        try:
            import pygame.sndarray as _snd
            self._snd = _snd
            if not pygame.mixer.get_init():
                pygame.mixer.init(self.SR, -16, 2, 512)
            self.canais_n = pygame.mixer.get_init()[2]
            self._gerar()
            self.ok = True
        except Exception:
            self.ok = False

    def _som(self, mono, vol=0.5):
        a = (np.clip(mono, -1, 1) * 32767 * vol).astype(np.int16)
        if self.canais_n >= 2:
            a = np.ascontiguousarray(np.column_stack((a, a)))
        return self._snd.make_sound(a)

    def _gerar(self):
        SR = self.SR
        rng = np.random.default_rng(1)

        def tt(d):
            return np.arange(int(d * SR)) / SR

        def passa_baixa(x, k):
            return np.convolve(x, np.ones(k) / k, mode="same")

        t = tt(0.9)
        env = np.exp(-t * 7)
        self.s["clink"] = self._som((np.sin(2 * np.pi * 2480 * t) + 0.6 * np.sin(2 * np.pi * 3720 * t)
                                     + 0.3 * np.sin(2 * np.pi * 5410 * t)) * env / 1.9, 0.6)
        t = tt(1.0)
        self.s["servir"] = self._som(passa_baixa(rng.normal(size=len(t)), 6) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t)) * 2.2, 0.35)
        t = tt(0.4)
        self.s["gole"] = self._som(np.sin(2 * np.pi * (180 - 100 * t / 0.4) * t) * np.exp(-((t - 0.15) / 0.1) ** 2), 0.5)
        t = tt(0.14)
        self.s["passo"] = self._som(passa_baixa(rng.normal(size=len(t)), 10) * np.exp(-t * 35) * 3, 0.5)
        t = tt(0.3)
        self.s["splash"] = self._som(passa_baixa(rng.normal(size=len(t)), 3) * np.exp(-t * 12) * 1.8, 0.5)
        t = tt(4.0)
        self.s["onda"] = self._som(passa_baixa(rng.normal(size=len(t)), 14) * (np.sin(np.pi * t / 4.0) ** 2) * 3.0, 0.5)
        t = tt(1.0)
        for nome, f in (("motor1", 55), ("motor2", 95), ("motor3", 150)):
            w = sum(np.sin(2 * np.pi * k * f * t) / k for k in range(1, 7))
            self.s[nome] = self._som(w * (0.75 + 0.25 * np.sin(2 * np.pi * 8 * t)) / 2.2, 0.5)
        t = tt(0.5)
        self.s["buzina"] = self._som(np.sign(np.sin(2 * np.pi * 420 * t)) * 0.4 + np.sign(np.sin(2 * np.pi * 530 * t)) * 0.4, 0.35)
        t = tt(0.5)
        self.s["batida"] = self._som((passa_baixa(rng.normal(size=len(t)), 5) * 2 + np.sin(2 * np.pi * 70 * t)) * np.exp(-t * 9) / 2, 0.8)

    def tocar(self, nome, vol=1.0):
        if self.ok and nome in self.s:
            c = self.s[nome].play()
            if c is not None:
                c.set_volume(vol)

    def loop(self, nome, vol):
        if not self.ok or nome not in self.s:
            return
        c = self.canais.get(nome)
        if vol > 0.01:
            if c is None or not c.get_busy():
                c = self.s[nome].play(-1)
                self.canais[nome] = c
            if c is not None:
                c.set_volume(clamp(vol))
        elif c is not None:
            c.stop()
            self.canais.pop(nome, None)

    def parar_tudo(self):
        if self.ok:
            pygame.mixer.stop()
        self.canais = {}


# ----------------------------------------------------------------------------
# SPRITES VETORIAIS (desenhados com formas)
# ----------------------------------------------------------------------------
ALTURA_SPR = {"pinheiro": 2800, "arbusto": 700, "palmeira": 3000, "guarda_sol": 1100, "barraca": 1000,
              "pedra": 500, "veleiro": 1500, "predio": 4200, "poste": 2200, "placa": 1000}


def spr_pinheiro(t, x, y, h, var):
    w = h * 0.45
    pygame.draw.rect(t, (80, 50, 30), (x - w * 0.06, y - h * 0.2, w * 0.12, h * 0.2))
    for i in range(3):
        by = y - h * (0.12 + 0.22 * i)
        half = w * (0.5 - 0.12 * i)
        pygame.draw.polygon(t, (24 + 10 * i, 92 + 14 * i, 48 + 6 * i), [(x - half, by), (x + half, by), (x, by - h * 0.38)])


def spr_arbusto(t, x, y, h, var):
    pygame.draw.ellipse(t, (50, 120, 55), (x - h * 0.45, y - h * 0.6, h * 0.9, h * 0.6))
    pygame.draw.ellipse(t, (70, 145, 65), (x - h * 0.2, y - h * 0.95, h * 0.6, h * 0.65))


def spr_palmeira(t, x, y, h, var):
    w = h * 0.5
    pygame.draw.polygon(t, (120, 85, 50), [(x - w * 0.05, y), (x + w * 0.05, y), (x + w * 0.15, y - h * 0.86), (x + w * 0.05, y - h * 0.86)])
    cx, cy = x + w * 0.1, y - h * 0.88
    lw = max(2, int(h * 0.05))
    for a in (-170, -140, -110, -70, -40, -10):
        r = math.radians(a)
        mx, my = cx + math.cos(r) * h * 0.22, cy + math.sin(r) * h * 0.18 - h * 0.04
        tx, ty = cx + math.cos(r) * h * 0.42, cy + math.sin(r) * h * 0.18 + h * 0.12
        pygame.draw.line(t, (38, 140, 66), (cx, cy), (mx, my), lw)
        pygame.draw.line(t, (50, 165, 78), (mx, my), (tx, ty), lw)
    pygame.draw.circle(t, (110, 70, 30), (int(cx), int(cy + h * 0.03)), max(2, int(h * 0.035)))


def spr_guarda_sol(t, x, y, h, var):
    pygame.draw.line(t, (230, 230, 230), (x, y), (x, y - h * 0.95), max(1, int(h * 0.03)))
    cores = ((235, 60, 60), (250, 250, 250)) if var % 2 == 0 else ((60, 140, 235), (250, 250, 250))
    rx, ry, base = h * 0.5, h * 0.2, y - h * 0.72
    for i in range(6):
        a0, a1 = math.pi * i / 6, math.pi * (i + 1) / 6
        pygame.draw.polygon(t, cores[i % 2], [(x, y - h), (x + rx * math.cos(a0), base + ry * math.sin(a0)),
                                              (x + rx * math.cos(a1), base + ry * math.sin(a1))])


def spr_barraca(t, x, y, h, var):
    w = h * 1.2
    pygame.draw.rect(t, (205, 150, 90), (x - w / 2, y - h * 0.6, w, h * 0.6))
    pygame.draw.rect(t, (70, 45, 30), (x - w * 0.35, y - h * 0.5, w * 0.7, h * 0.25))
    pygame.draw.polygon(t, (235, 70, 70), [(x - w * 0.6, y - h * 0.6), (x + w * 0.6, y - h * 0.6), (x + w * 0.45, y - h * 0.9), (x - w * 0.45, y - h * 0.9)])
    pygame.draw.polygon(t, (250, 250, 250), [(x - w * 0.1, y - h * 0.6), (x + w * 0.1, y - h * 0.6), (x + w * 0.08, y - h * 0.9), (x - w * 0.08, y - h * 0.9)])


def spr_pedra(t, x, y, h, var):
    pygame.draw.ellipse(t, (110, 112, 118), (x - h * 0.7, y - h * 0.8, h * 1.4, h * 0.8))
    pygame.draw.ellipse(t, (140, 142, 148), (x - h * 0.4, y - h * 0.75, h * 0.7, h * 0.4))


def spr_veleiro(t, x, y, h, var):
    pygame.draw.polygon(t, (60, 60, 70), [(x - h * 0.5, y - h * 0.08), (x + h * 0.5, y - h * 0.08), (x + h * 0.3, y + h * 0.05), (x - h * 0.35, y + h * 0.05)])
    pygame.draw.polygon(t, (250, 250, 250), [(x, y - h), (x, y - h * 0.12), (x + h * 0.45, y - h * 0.12)])
    pygame.draw.polygon(t, (235, 235, 245), [(x - h * 0.05, y - h * 0.85), (x - h * 0.05, y - h * 0.12), (x - h * 0.4, y - h * 0.12)])


def spr_predio(t, x, y, h, var):
    w = h * 0.55
    cor = ((120, 125, 140), (150, 120, 110), (95, 110, 130))[var % 3]
    pygame.draw.rect(t, cor, (x - w / 2, y - h, w, h))
    if h > 60:
        for r in range(7):
            for c in range(3):
                lit = (r * 3 + c + var) % 3 != 0
                pygame.draw.rect(t, (255, 225, 140) if lit else (60, 70, 90),
                                 (x - w * 0.38 + c * w * 0.27, y - h * 0.93 + r * h * 0.12, w * 0.17, h * 0.07))


def spr_poste(t, x, y, h, var):
    pygame.draw.line(t, (60, 60, 66), (x, y), (x, y - h), max(1, int(h * 0.03)))
    pygame.draw.line(t, (60, 60, 66), (x, y - h), (x + h * 0.15, y - h), max(1, int(h * 0.025)))
    pygame.draw.circle(t, (255, 235, 150), (int(x + h * 0.15), int(y - h * 0.98)), max(2, int(h * 0.04)))


def spr_placa(t, x, y, h, var):
    pygame.draw.line(t, (90, 90, 95), (x, y), (x, y - h * 0.8), max(1, int(h * 0.03)))
    pygame.draw.rect(t, (245, 245, 245), (x - h * 0.22, y - h, h * 0.44, h * 0.32))
    pygame.draw.polygon(t, (220, 40, 40), [(x - h * 0.12, y - h * 0.7), (x + h * 0.12, y - h * 0.7), (x, y - h * 0.95)])


SPRITES = {"pinheiro": spr_pinheiro, "arbusto": spr_arbusto, "palmeira": spr_palmeira, "guarda_sol": spr_guarda_sol,
           "barraca": spr_barraca, "pedra": spr_pedra, "veleiro": spr_veleiro, "predio": spr_predio,
           "poste": spr_poste, "placa": spr_placa}


def desenhar_sprite(tela, tipo, x, y, k, var):
    h = ALTURA_SPR[tipo] * k
    if h < 2 or x < -h or x > GAME_W + h:
        return
    SPRITES[tipo](tela, x, y, h, var)


def spr_carro(t, x, y, h, cor):
    w = h * 1.5
    pygame.draw.rect(t, (20, 20, 22), (x - w * 0.46, y - h * 0.2, w * 0.16, h * 0.2))
    pygame.draw.rect(t, (20, 20, 22), (x + w * 0.30, y - h * 0.2, w * 0.16, h * 0.2))
    pygame.draw.rect(t, cor, (x - w / 2, y - h * 0.62, w, h * 0.45))
    pygame.draw.polygon(t, esc(cor, 0.85), [(x - w * 0.38, y - h * 0.62), (x + w * 0.38, y - h * 0.62), (x + w * 0.28, y - h), (x - w * 0.28, y - h)])
    pygame.draw.polygon(t, (30, 40, 60), [(x - w * 0.31, y - h * 0.66), (x + w * 0.31, y - h * 0.66), (x + w * 0.23, y - h * 0.94), (x - w * 0.23, y - h * 0.94)])
    pygame.draw.rect(t, (255, 50, 50), (x - w * 0.47, y - h * 0.52, w * 0.2, h * 0.09))
    pygame.draw.rect(t, (255, 50, 50), (x + w * 0.27, y - h * 0.52, w * 0.2, h * 0.09))
    pygame.draw.rect(t, (35, 35, 40), (x - w / 2, y - h * 0.2, w, h * 0.06))
    pygame.draw.rect(t, (245, 245, 245), (x - w * 0.1, y - h * 0.4, w * 0.2, h * 0.07))


# ----------------------------------------------------------------------------
# MOTOR PSEUDO-3D DE ESTRADA (projeção em perspectiva de segmentos)
# ----------------------------------------------------------------------------
SEG_LEN = 200
ROAD_W = 2000
CAM_H = 1000
CAM_DEPTH = 1 / math.tan(math.radians(50))
DRAW = 110
RUMBLE = 3
PLAYER_Z = CAM_H * CAM_DEPTH


class Seg:
    __slots__ = ("i", "y1", "y2", "curva", "faixa", "zona", "sprites", "carros")

    def __init__(self, i, y1, y2, curva):
        self.i, self.y1, self.y2, self.curva = i, y1, y2, curva
        self.faixa = (i // RUMBLE) % 2
        self.zona = 0
        self.sprites = []
        self.carros = []


class Pista:
    def __init__(self, segs):
        self.segs = segs
        self.n = len(segs)
        self.comp = self.n * SEG_LEN

    def seg_em(self, z):
        return self.segs[int(z // SEG_LEN) % self.n]

    def renderizar(self, tela, pos, cam_x, cam_y, estilo, t):
        W, H = GAME_W, GAME_H
        base = self.seg_em(pos)
        pct = (pos % SEG_LEN) / SEG_LEN
        x = 0.0
        dx = -(base.curva * pct)
        maxy = float(H)
        mx, my, mw = W / 2, H / 2, W / 2
        vis = []
        for n in range(DRAW):
            gi = base.i + n
            seg = self.segs[gi % self.n]
            cz1 = gi * SEG_LEN - pos
            cz2 = cz1 + SEG_LEN
            clip = maxy
            if cz1 > 1.0:
                e1, e2 = CAM_DEPTH / cz1, CAM_DEPTH / cz2
                sy1 = my - e1 * (seg.y1 - cam_y) * my
                sy2 = my - e2 * (seg.y2 - cam_y) * my
                if sy2 < sy1 and sy2 < maxy:
                    sx1 = mx + e1 * (x - cam_x) * mw
                    sx2 = mx + e2 * (x + dx - cam_x) * mw
                    sw1, sw2 = e1 * ROAD_W * mw, e2 * ROAD_W * mw
                    tela.set_clip((0, 0, W, max(0, int(clip) + 1)))
                    estilo.segmento(tela, W, seg, sx1, sy1, sw1, sx2, sy2, sw2, t)
                    vis.append((seg, sx1, sy1, e1, sx2, sy2, e2, clip))
                    maxy = sy1
            x += dx
            dx += seg.curva
        for (seg, sx1, sy1, e1, sx2, sy2, e2, clip) in reversed(vis):
            tela.set_clip((0, 0, W, max(0, int(clip) + 1)))
            for (tipo, off, var) in seg.sprites:
                estilo.sprite(tela, tipo, sx1 + e1 * off * ROAD_W * mw, sy1, e1 * mw, var)
            for c in seg.carros:
                p = (c.z % SEG_LEN) / SEG_LEN
                e = lerp(e1, e2, p)
                estilo.carro(tela, c, lerp(sx1, sx2, p) + e * c.x * ROAD_W * mw, lerp(sy1, sy2, p), e * mw)
        tela.set_clip(None)


def construir_segmentos(secoes):
    segs = []

    def add(curva, y):
        y1 = segs[-1].y2 if segs else 0.0
        segs.append(Seg(len(segs), y1, y, curva))

    def trecho(ent, man, sai, curva, alt):
        iy = segs[-1].y2 if segs else 0.0
        fy = iy + alt * SEG_LEN
        total = ent + man + sai
        for n in range(ent):
            add(ease_in(0, curva, n / ent), ease_inout(iy, fy, n / total))
        for n in range(man):
            add(curva, ease_inout(iy, fy, (ent + n) / total))
        for n in range(sai):
            add(ease_inout(curva, 0, n / sai), ease_inout(iy, fy, (ent + man + n) / total))

    for s in secoes:
        trecho(*s)
    trecho(40, 20, 40, 0, -segs[-1].y2 / SEG_LEN)     # fecha o circuito na altura zero
    return segs


SECOES_MOTO = [(25, 25, 25, 0, 0), (25, 50, 25, 2, 18), (20, 30, 20, -3, -12), (25, 40, 25, 4, 22),
               (25, 25, 25, -2, -25), (30, 50, 30, 0, 30), (25, 40, 25, -5, -18), (20, 25, 20, 3, 0),
               (30, 40, 30, 0, -35), (25, 45, 25, 5, 24), (20, 30, 20, -4, -8), (40, 60, 40, 2, 28),
               (25, 30, 25, -6, -30), (30, 60, 30, 0, 0), (25, 40, 25, 4, 15), (20, 30, 20, -3, -15),
               (30, 50, 30, 3, 20), (25, 35, 25, -4, -10), (40, 80, 40, 0, -6), (25, 40, 25, 3, 12),
               (25, 40, 25, -3, -12), (30, 60, 30, 0, 0)]
SECOES_PRAIA = [(40, 80, 40, 0, 0), (40, 70, 40, 1.5, 4), (40, 70, 40, -2, -4), (40, 90, 40, 2.5, 6),
                (40, 70, 40, -1.5, -6), (40, 100, 40, 0, 3), (40, 70, 40, 2, -3), (40, 70, 40, -2.5, 0),
                (40, 90, 40, 1, 5), (40, 80, 40, -1, -5), (40, 100, 40, 0, 0)]

ZONAS_MOTO = [
    {"nome": "Campo", "cheiro": "capim cortado e terra molhada", "dens": 0.45,
     "tipos": ["arbusto", "arbusto", "poste", "placa"], "lado": ((96, 166, 62), (86, 154, 56))},
    {"nome": "Floresta", "cheiro": "pinho e resina", "dens": 0.85,
     "tipos": ["pinheiro", "pinheiro", "pinheiro", "arbusto"], "lado": ((34, 104, 52), (28, 94, 46))},
    {"nome": "Costa", "cheiro": "maresia e protetor solar", "dens": 0.5,
     "tipos": ["palmeira", "palmeira", "pedra", "placa"], "lado": ((226, 202, 146), (216, 192, 136))},
    {"nome": "Cidade", "cheiro": "asfalto quente e escapamento", "dens": 0.7,
     "tipos": ["predio", "predio", "poste"], "lado": ((122, 122, 128), (112, 112, 118))},
]


class Carro:
    def __init__(self, z, x, vel, cor):
        self.z, self.x, self.vel, self.cor, self.rel_ant = z, x, vel, cor, 0.0


def construir_pista_moto(rng):
    segs = construir_segmentos(SECOES_MOTO)
    for s in segs:
        s.zona = (s.i // 320) % 4
        z = ZONAS_MOTO[s.zona]
        if s.i % 4 == 0:
            for lado in (-1, 1):
                if rng.random() < z["dens"]:
                    s.sprites.append((rng.choice(z["tipos"]), lado * (1.45 + rng.random() * 1.6), int(rng.integers(0, 3))))
    return Pista(segs)


def construir_pista_praia(rng):
    segs = construir_segmentos(SECOES_PRAIA)
    for s in segs:
        if s.i % 5 == 0 and rng.random() < 0.45:
            s.sprites.append(("palmeira", -(1.35 + rng.random() * 2.2), 0))
        if s.i % 17 == 0 and rng.random() < 0.7:
            s.sprites.append(("guarda_sol", -(1.2 + rng.random() * 0.6), int(rng.integers(0, 2))))
        if s.i % 140 == 70:
            s.sprites.append(("barraca", -1.55, 0))
        if s.i % 9 == 0 and rng.random() < 0.18:
            s.sprites.append(("pedra", 1.3 + rng.random() * 1.2, 0))
        if s.i % 45 == 0 and rng.random() < 0.7:
            s.sprites.append(("veleiro", 3.5 + rng.random() * 6.0, 0))
    return Pista(segs)


def banda(tela, c, x1, w1, x2, w2, u0, u1, y1, y2):
    pygame.draw.polygon(tela, c, [(x1 + u0 * w1, y1), (x1 + u1 * w1, y1), (x2 + u1 * w2, y2), (x2 + u0 * w2, y2)])


def limite_agua(seg, t):
    """Fronteira (em largura de pista) entre areia molhada e espuma - se move com as ondas."""
    return 0.42 + 0.10 * math.sin(1.3 * t + seg.i * 0.09)


class EstiloMoto:
    def segmento(self, tela, W, seg, x1, y1, w1, x2, y2, w2, t):
        z = ZONAS_MOTO[seg.zona]
        pygame.draw.rect(tela, z["lado"][seg.faixa], (0, y2, W, y1 - y2 + 1))
        r1, r2 = w1 / 7, w2 / 7
        cr = (205, 35, 40) if seg.faixa == 0 else (238, 238, 238)
        pygame.draw.polygon(tela, cr, [(x1 - w1 - r1, y1), (x1 - w1, y1), (x2 - w2, y2), (x2 - w2 - r2, y2)])
        pygame.draw.polygon(tela, cr, [(x1 + w1 + r1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 + w2 + r2, y2)])
        pygame.draw.polygon(tela, (92, 92, 98) if seg.faixa == 0 else (86, 86, 92),
                            [(x1 - w1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 - w2, y2)])
        if seg.faixa == 0:
            l1, l2 = w1 / 28, w2 / 28
            pygame.draw.polygon(tela, (236, 236, 236), [(x1 - l1, y1), (x1 + l1, y1), (x2 + l2, y2), (x2 - l2, y2)])

    def sprite(self, tela, tipo, x, y, k, var):
        desenhar_sprite(tela, tipo, x, y, k, var)

    def carro(self, tela, c, x, y, k):
        h = 650 * k
        if h >= 2:
            spr_carro(tela, x, y, h, c.cor)


class EstiloPraia:
    def segmento(self, tela, W, seg, x1, y1, w1, x2, y2, w2, t):
        f = seg.faixa
        pygame.draw.rect(tela, (226, 202, 146) if f == 0 else (219, 195, 139), (0, y2, W, y1 - y2 + 1))
        pygame.draw.polygon(tela, (30, 120, 182) if f == 0 else (26, 112, 172),
                            [(x1 + w1, y1), (W, y1), (W, y2), (x2 + w2, y2)])
        b = limite_agua(seg, t)
        banda(tela, (242, 222, 170) if f == 0 else (235, 213, 161), x1, w1, x2, w2, -1.0, -0.35, y1, y2)
        banda(tela, (198, 170, 120) if f == 0 else (190, 162, 114), x1, w1, x2, w2, -0.35, b, y1, y2)
        banda(tela, (250, 252, 255), x1, w1, x2, w2, b, b + 0.07, y1, y2)
        banda(tela, (94, 198, 208) if f == 0 else (86, 190, 202), x1, w1, x2, w2, b + 0.07, 1.0, y1, y2)

    def sprite(self, tela, tipo, x, y, k, var):
        desenhar_sprite(tela, tipo, x, y, k, var)

    def carro(self, tela, c, x, y, k):
        pass


# ----------------------------------------------------------------------------
# APLICAÇÃO / CENAS
# ----------------------------------------------------------------------------
def N(v, a, t, o, p):
    return [clamp(v), clamp(a), clamp(t), clamp(o), clamp(p)]


class App:
    def __init__(self, fila, tela):
        self.fila = fila
        self.tela = tela
        self.f_p = pygame.font.Font(None, 22)
        self.f_m = pygame.font.Font(None, 30)
        self.f_g = pygame.font.Font(None, 52)
        self.sons = Sons()
        self.kill = False
        self.ult_niv = [0.0] * 5
        self.t_envio = 0.0
        self.cena = None

    def trocar(self, cena):
        self.sons.parar_tudo()
        self.cena = cena

    def enviar(self, niv, cena_nome, sens):
        niv = [0.0] * 5 if self.kill else niv
        self.ult_niv = niv
        try:
            self.fila.put_nowait({"niv": niv, "cena": cena_nome, "sens": sens, "kill": self.kill})
        except Exception:
            pass

    def hud(self, tela, titulo, linhas, dica):
        s = pygame.Surface((GAME_W, 34), pygame.SRCALPHA)
        s.fill((0, 0, 0, 120))
        tela.blit(s, (0, 0))
        txt(tela, self.f_m, titulo, 12, 7, (255, 255, 255))
        for i, l in enumerate(linhas):
            txt(tela, self.f_p, l, 14, 42 + i * 20, (255, 255, 255))
        for i, sname in enumerate(SETORES):
            x = GAME_W - 150 + i * 28
            pygame.draw.rect(tela, (20, 20, 28), (x, 8, 18, 40))
            hh = int(40 * clamp(self.ult_niv[i]))
            pygame.draw.rect(tela, COR[sname], (x, 48 - hh, 18, hh))
            txt(tela, self.f_p, ROTULO[sname][0], x + 4, 50, COR[sname])
        s2 = pygame.Surface((GAME_W, 26), pygame.SRCALPHA)
        s2.fill((0, 0, 0, 130))
        tela.blit(s2, (0, GAME_H - 26))
        txt(tela, self.f_p, dica, 12, GAME_H - 21, (230, 230, 230))
        if self.kill:
            ov = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            tela.blit(ov, (0, 0))
            txt(tela, self.f_g, "DISJUNTOR ACIONADO", GAME_W // 2, GAME_H // 2 - 30, (255, 90, 90), centro=True)
            txt(tela, self.f_m, "sistema isolado · aperte K para religar", GAME_W // 2, GAME_H // 2 + 14, (255, 200, 200), centro=True)


class Cena:
    titulo = ""
    dica = ""

    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def evento(self, ev):
        pass

    def atualizar(self, dt, k):
        self.t += dt

    def desenhar(self, tela):
        pass

    def sensores(self):
        return N(0, 0, 0, 0, 0), "—"

    def hud_linhas(self):
        return []


# ---------------------------------------------------------------- MENU
class Menu(Cena):
    titulo = "MENU"

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_1, pygame.K_KP1):
                self.app.trocar(Vinho(self.app))
            elif ev.key in (pygame.K_2, pygame.K_KP2):
                self.app.trocar(Praia(self.app))
            elif ev.key in (pygame.K_3, pygame.K_KP3):
                self.app.trocar(Moto(self.app))

    def desenhar(self, tela):
        tela.blit(gradiente(GAME_W, GAME_H, (14, 18, 40), (40, 20, 60)), (0, 0))
        a = self.app
        txt(tela, a.f_g, "SIMULADOR SINESTÉSICO", GAME_W // 2, 90, (255, 255, 255), centro=True)
        txt(tela, a.f_m, "DABOIT-BCI-1 · malha de grafeno · 5 setores corticais", GAME_W // 2, 140, (170, 180, 230), centro=True)
        for i, (n, c) in enumerate((("1", "TOMAR VINHO   (olfato e paladar)"), ("2", "CORRER NA PRAIA   (tato e audição)"),
                                    ("3", "DIRIGIR MOTO   (visão e velocidade)"))):
            txt(tela, a.f_m, "[%s]  %s" % (n, c), GAME_W // 2, 230 + i * 56, (255, 235, 160), centro=True)
        txt(tela, a.f_p, "Olhe a outra janela: o cérebro 3D mostra os eletrodos disparando conforme você joga.",
            GAME_W // 2, 440, (200, 205, 225), centro=True)
        txt(tela, a.f_p, "K = disjuntor mecânico de emergência · ESC = voltar ao menu", GAME_W // 2, 468, (150, 158, 185), centro=True)

    def sensores(self):
        return N(0.05, 0.05, 0.05, 0.05, 0.05), "Aguardando escolha do cenário"


# ---------------------------------------------------------------- JOGO 1: VINHO
SABORES = ["doce", "azedo", "amargo", "salgado", "umami"]
PICO_SABOR = {"doce": (0.6, 0.9), "azedo": (1.4, 1.0), "amargo": (2.6, 1.6), "salgado": (1.0, 1.5), "umami": (3.2, 1.2)}
VINHOS = [
    {"nome": "Tinto · Malbec", "cor": (118, 12, 36), "garrafa": (30, 50, 34),
     "aromas": ["frutas vermelhas", "ameixa e cassis", "carvalho tostado", "baunilha", "couro e especiarias"],
     "sabor": {"doce": 0.30, "azedo": 0.50, "amargo": 0.60, "salgado": 0.05, "umami": 0.25}},
    {"nome": "Branco · Chardonnay", "cor": (226, 204, 112), "garrafa": (70, 92, 50),
     "aromas": ["maçã verde", "limão siciliano", "flor de laranjeira", "manteiga", "mel"],
     "sabor": {"doce": 0.25, "azedo": 0.75, "amargo": 0.15, "salgado": 0.12, "umami": 0.05}},
    {"nome": "Rosé · Provence", "cor": (232, 128, 150), "garrafa": (60, 80, 60),
     "aromas": ["morango", "pêssego", "pétalas de rosa", "melão", "toranja"],
     "sabor": {"doce": 0.40, "azedo": 0.55, "amargo": 0.12, "salgado": 0.08, "umami": 0.05}},
]


class Vinho(Cena):
    titulo = "Tomar vinho"
    dica = "R servir · Q girar a taça · E cheirar · ESPAÇO beber · C brindar · T trocar de vinho"

    def __init__(self, app):
        super().__init__(app)
        self.v = 0
        self.nivel = 0.0
        self.servindo = self.giro = self.cheirar = self.beber = self.brinde = 0.0
        self.fase = 0.0
        self.t_gole = 99.0
        self.t_beb = 0.0
        self.provou = False
        self.prox_gole = 0.0
        self.pulso_gole = 0.0
        self.aroma_i = 0
        self.t_aroma = 0.0
        self.sabor = {s: 0.0 for s in SABORES}
        self.sup_taca = pygame.Surface((300, 380), pygame.SRCALPHA)
        self.fundo = self._fundo()
        self.glow_vela = self._glow_vela()
        self.garrafa = self._garrafa()

    # ---- recursos visuais
    def _fundo(self):
        s = pygame.Surface((GAME_W, GAME_H))
        s.blit(gradiente(GAME_W, GAME_H, (16, 8, 16), (60, 24, 34)), (0, 0))
        bk = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        rr = random.Random(5)
        for _ in range(18):
            c = rr.choice(((255, 190, 90), (255, 150, 70), (255, 220, 140)))
            pygame.draw.circle(bk, c + (rr.randint(25, 60),), (rr.randint(0, GAME_W), rr.randint(40, 300)), rr.randint(14, 38))
        s.blit(bk, (0, 0))
        pygame.draw.polygon(s, (92, 22, 34), [(170, 330), (710, 330), (GAME_W, GAME_H), (0, GAME_H)])
        for i in range(9):
            y = 334 + i * i * 2.6
            pygame.draw.line(s, (110, 30, 44) if i % 2 else (80, 18, 30), (170 - (y - 330) * 0.8, y), (710 + (y - 330) * 0.8, y), 2)
        pygame.draw.line(s, (150, 60, 70), (170, 330), (710, 330), 2)
        return s

    def _glow_vela(self):
        s = pygame.Surface((260, 260), pygame.SRCALPHA)
        for r in range(130, 4, -5):
            pygame.draw.circle(s, (255, 170, 70, int(70 * (1 - r / 130) ** 2)), (130, 130), r)
        return s

    def _garrafa(self):
        s = pygame.Surface((110, 400), pygame.SRCALPHA)
        c = VINHOS[self.v]["garrafa"]
        pygame.draw.rect(s, c, (20, 150, 70, 240), border_radius=14)
        pygame.draw.polygon(s, c, [(20, 160), (90, 160), (65, 90), (45, 90)])
        pygame.draw.rect(s, c, (45, 40, 20, 100))
        pygame.draw.rect(s, (150, 20, 30), (43, 20, 24, 36), border_radius=4)
        pygame.draw.rect(s, (238, 228, 200), (28, 235, 54, 82))
        pygame.draw.line(s, (110, 90, 60), (36, 255), (74, 255), 2)
        pygame.draw.line(s, (110, 90, 60), (36, 270), (74, 270), 2)
        pygame.draw.line(s, (170, 150, 110), (36, 290), (74, 290), 1)
        pygame.draw.line(s, (255, 255, 255, 90), (30, 180), (30, 380), 3)
        return s

    @staticmethod
    def _raio(t):
        if t < 0.25:
            return 62 - 6 * (0.25 - t) / 0.25
        u = (t - 0.25) / 0.75
        return 12 + 50 * math.sqrt(max(0.0, 1 - u * u))

    def _taca(self):
        s = self.sup_taca
        s.fill((0, 0, 0, 0))
        cx, top, bot = 150, 40, 200
        vinho = VINHOS[self.v]
        N_ = 24
        esq = [(cx - self._raio(i / N_), top + (bot - top) * i / N_) for i in range(N_ + 1)]
        dire = [(cx + self._raio(i / N_), top + (bot - top) * i / N_) for i in range(N_ + 1)]
        pygame.draw.polygon(s, (210, 230, 245, 38), esq + dire[::-1])
        if self.nivel > 0.01:
            ts = 1 - min(1.0, self.nivel) * 0.62
            amp = self.giro * 6
            pe, pd = [], []
            for i in range(N_ + 1):
                tt = ts + (1 - ts) * i / N_
                y = top + (bot - top) * tt
                w = math.sin(self.fase + tt * 7) * amp
                r = self._raio(tt) * 0.93
                pe.append((cx - r + w, y))
                pd.append((cx + r + w, y))
            pygame.draw.polygon(s, vinho["cor"] + (232,), pe + pd[::-1])
            rs = self._raio(ts) * 0.93
            ys = top + (bot - top) * ts
            ox = math.cos(self.fase) * rs * 0.25 * self.giro
            pygame.draw.ellipse(s, mix(vinho["cor"], (255, 255, 255), 0.25) + (240,),
                                (cx - rs + ox, ys - rs * 0.2, max(2, rs * 2), max(2, rs * 0.4)))
        pygame.draw.lines(s, (225, 238, 255, 150), False, esq[::2], 2)
        pygame.draw.lines(s, (225, 238, 255, 150), False, dire[::2], 2)
        pygame.draw.ellipse(s, (235, 245, 255, 170), (cx - 56, top - 11, 112, 22), 2)
        pygame.draw.rect(s, (215, 230, 245, 150), (cx - 3, bot, 6, 125))
        pygame.draw.ellipse(s, (215, 230, 245, 140), (cx - 52, 318, 104, 22))
        pygame.draw.ellipse(s, (240, 248, 255, 110), (cx - 52, 318, 104, 22), 2)
        pygame.draw.lines(s, (255, 255, 255, 120), False,
                          [(cx - self._raio(q / 10 * 0.6 + 0.1) * 0.78, top + (bot - top) * (q / 10 * 0.6 + 0.1)) for q in range(11)], 3)
        return s

    # ---- lógica
    def evento(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key == pygame.K_t:
            self.v = (self.v + 1) % len(VINHOS)
            self.garrafa = self._garrafa()
            self.provou = False
            self.sabor = {s: 0.0 for s in SABORES}
        elif ev.key == pygame.K_c and self.nivel > 0.02:
            self.brinde = 1.0
            self.app.sons.tocar("clink")
        elif ev.key == pygame.K_SPACE and self.nivel > 0.02:
            self.t_gole, self.t_beb, self.provou = 0.0, 0.0, True

    def atualizar(self, dt, k):
        self.t += dt
        s = self.app.sons
        v = VINHOS[self.v]
        pode_servir = k[pygame.K_r] and self.nivel < 1.0 and self.beber < 0.2
        if pode_servir:
            self.servindo = min(1.0, self.servindo + dt * 4)
            if self.servindo > 0.6:
                self.nivel = min(1.0, self.nivel + dt * 0.28)
        else:
            self.servindo = max(0.0, self.servindo - dt * 4)
        s.loop("servir", 0.9 if (pode_servir and self.servindo > 0.6) else 0)

        if k[pygame.K_q] and self.nivel > 0.05:
            self.giro = min(1.0, self.giro + dt * 1.6)
        else:
            self.giro = max(0.0, self.giro - dt * 0.45)
        self.fase += dt * (2 + 10 * self.giro)

        bebendo = bool(k[pygame.K_SPACE]) and self.nivel > 0.02
        self.beber += ((1.0 if bebendo else 0.0) - self.beber) * min(1.0, dt * 4)
        cheirando = bool(k[pygame.K_e]) and not bebendo
        self.cheirar += ((1.0 if cheirando else 0.0) - self.cheirar) * min(1.0, dt * 5)
        if bebendo and self.beber > 0.6:
            self.nivel = max(0.0, self.nivel - dt * 0.11)
            self.t_beb += dt
            self.prox_gole -= dt
            if self.prox_gole <= 0:
                self.pulso_gole = 1.0
                self.prox_gole = 1.3
                s.tocar("gole")
        self.pulso_gole *= math.exp(-dt * 4)
        self.t_gole += dt
        self.brinde = max(0.0, self.brinde - dt * 1.2)

        if self.cheirar > 0.3 or self.giro > 0.3:
            self.t_aroma += dt
            if self.t_aroma > 1.7:
                self.t_aroma = 0.0
                self.aroma_i = (self.aroma_i + 1) % len(v["aromas"])

        # envelope de sabores (doce -> azedo -> amargo/tanino -> umami)
        forca = 0.35 + 0.65 * clamp(self.t_beb / 1.2)
        for nome in SABORES:
            tp, w = PICO_SABOR[nome]
            e = math.exp(-((self.t_gole - tp) / w) ** 2) if self.provou else 0.0
            self.sabor[nome] = v["sabor"][nome] * e * forca * 1.5

    def desenhar(self, tela):
        v = VINHOS[self.v]
        tela.blit(self.fundo, (0, 0))
        # vela
        flick = math.sin(self.t * 13) * 2 + math.sin(self.t * 7.3) * 1.5
        tela.blit(self.glow_vela, (20, 160 + int(flick)))
        pygame.draw.rect(tela, (240, 230, 200), (140, 312, 20, 62))
        pygame.draw.polygon(tela, (255, 190, 60), [(150, 270 + flick * 0.5), (142, 304), (158, 304)])
        pygame.draw.polygon(tela, (255, 240, 170), [(150, 282 + flick * 0.5), (146, 304), (154, 304)])
        # sombra da taça
        sh = pygame.Surface((160, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), (0, 0, 160, 24))
        tela.blit(sh, (340, 452))

        # pose da taça
        ox = 14 * math.cos(self.fase) * self.giro
        oy = 6 * math.sin(self.fase) * self.giro
        p = 1 - self.brinde
        ox += 130 * math.sin(math.pi * p) if self.brinde > 0 else 0
        ang = 42 * self.beber + 10 * math.sin(self.t * 1.2) * self.giro + (12 * math.sin(math.pi * p) if self.brinde > 0 else 0)
        escala = 1 + 0.25 * self.beber + 0.4 * self.cheirar
        gx, gy = 420 + ox, 325 + oy - 150 * self.beber - 115 * self.cheirar
        img = pygame.transform.rotozoom(self._taca(), ang, escala)
        tela.blit(img, img.get_rect(center=(gx, gy)))
        if self.brinde > 0.6:
            for a in range(0, 360, 45):
                r = math.radians(a)
                pygame.draw.line(tela, (255, 255, 230), (gx + 150 + 12 * math.cos(r), gy - 120 + 12 * math.sin(r)),
                                 (gx + 150 + 34 * math.cos(r), gy - 120 + 34 * math.sin(r)), 3)

        # garrafa e fio de vinho
        L = 180
        th = 55 * self.servindo
        tip = (420 + 45, 175 - 30)
        pc = (tip[0] + L * math.sin(math.radians(th)), tip[1] + L * math.cos(math.radians(th)))
        e = ease_inout(0, 1, self.servindo)
        cb = (lerp(790, pc[0], e), lerp(360, pc[1], e))
        if self.servindo > 0.6 and self.nivel < 1.0:
            ys = 135 + 40 + 160 * (1 - min(1.0, self.nivel) * 0.62)
            bx = cb[0] - L * math.sin(math.radians(th))
            by = cb[1] - L * math.cos(math.radians(th))
            pygame.draw.line(tela, v["cor"], (bx, by), (420 + math.sin(self.t * 20) * 2, ys), 5)
        gimg = pygame.transform.rotozoom(self.garrafa, th, 1.0)
        tela.blit(gimg, gimg.get_rect(center=cb))

        # HUD
        a = self.app
        taste = [("DOCE", self.sabor["doce"]), ("AZEDO", self.sabor["azedo"]), ("AMARGO", self.sabor["amargo"]),
                 ("SALGADO", self.sabor["salgado"]), ("UMAMI", self.sabor["umami"])]
        for i, (nome, val) in enumerate(taste):
            x = 16 + i * 104
            txt(tela, a.f_p, nome, x, GAME_H - 62, (255, 190, 200))
            pygame.draw.rect(tela, (30, 20, 26), (x, GAME_H - 42, 92, 10))
            pygame.draw.rect(tela, COR["PALADAR"], (x, GAME_H - 42, int(92 * clamp(val)), 10))
        a.hud(tela, "TOMAR VINHO · " + v["nome"], self.hud_linhas(), self.dica)

    def hud_linhas(self):
        v = VINHOS[self.v]
        return ["Taça: %d%%" % int(self.nivel * 100), "Aroma: " + v["aromas"][self.aroma_i]]

    def sensores(self):
        v = VINHOS[self.v]
        forca_ar = clamp((0.2 + 0.55 * self.giro + 0.65 * self.cheirar) * (0.35 + 0.65 * min(1.0, self.nivel * 5)))
        paladar = max(self.sabor.values())
        tato = max(0.10 if self.nivel > 0 else 0.0, 0.45 * self.giro, 0.7 * self.beber, 0.25 * self.servindo, 0.5 * self.brinde)
        visao = 0.25 + 0.4 * self.servindo + 0.3 * self.giro + 0.25 * self.beber + 0.25 * self.cheirar + 0.35 * self.brinde
        audicao = 0.1 + 0.85 * self.servindo + 0.2 * self.giro + 1.0 * self.brinde + 0.5 * self.pulso_gole
        if paladar > 0.2 or self.beber > 0.4:
            dom = max(self.sabor, key=self.sabor.get)
            sens = "Provando o vinho · sabor %s" % dom
        elif self.cheirar > 0.4:
            sens = "Cheirando a taça · %s" % v["aromas"][self.aroma_i]
        elif self.giro > 0.3:
            sens = "Girando a taça · aromas se abrem"
        elif self.servindo > 0.3:
            sens = "Servindo o vinho · som do líquido"
        elif self.brinde > 0.2:
            sens = "Brinde · tilintar das taças"
        else:
            sens = "Observando a taça à luz de vela"
        return N(visao, audicao, tato, forca_ar, paladar), sens


# ---------------------------------------------------------------- BASE DOS JOGOS DE ESTRADA
class CenaPista(Cena):
    def __init__(self, app, pista, estilo, ceu, hor, montanha):
        super().__init__(app)
        self.pista, self.estilo = pista, estilo
        self.ceu, self.hor, self.montanha = ceu, hor, montanha
        self.pos = 0.0
        self.x = 0.0
        self.vel = 0.0
        self.bg = 0.0
        self.tremor = 0.0
        self.nuvens = [(random.randint(0, GAME_W), random.randint(30, 150), random.randint(50, 110)) for _ in range(6)]

    def seg_jogador(self):
        return self.pista.seg_em(self.pos + PLAYER_Z)

    def y_jogador(self):
        s = self.seg_jogador()
        return lerp(s.y1, s.y2, ((self.pos + PLAYER_Z) % SEG_LEN) / SEG_LEN)

    def desenhar_fundo(self, tela, praia=False):
        H2 = GAME_H // 2
        tela.blit(gradiente(GAME_W, H2, self.ceu, self.hor), (0, 0))
        pygame.draw.circle(tela, (255, 245, 200), (int(GAME_W * 0.72 - self.bg * 0.05) % GAME_W, 110), 38)
        for (nx, ny, nw) in self.nuvens:
            px = (nx - self.bg * 0.15) % (GAME_W + 200) - 100
            pygame.draw.ellipse(tela, (255, 255, 255), (px, ny, nw * 1.6, nw * 0.4))
            pygame.draw.ellipse(tela, (250, 250, 255), (px + nw * 0.3, ny - nw * 0.15, nw, nw * 0.4))
        for camada, (alt, cor) in enumerate(((46, self.montanha), (24, esc(self.montanha, 0.8)))):
            off = self.bg * (0.5 + 0.5 * camada)
            pts = [(0, H2)]
            for px in range(0, GAME_W + 20, 20):
                yy = H2 - 6 - alt * (0.55 + 0.45 * abs(math.sin((px + off) * (0.006 + 0.004 * camada))))
                if praia:
                    yy = H2 - 4 - 8 * abs(math.sin((px + off) * 0.01))
                pts.append((px, yy))
            pts.append((GAME_W, H2))
            pygame.draw.polygon(tela, cor, pts)
        pygame.draw.rect(tela, self.hor if not praia else (226, 202, 146), (0, H2, GAME_W, H2))
        if praia:
            pygame.draw.rect(tela, (30, 120, 182), (GAME_W // 2, H2, GAME_W // 2, H2))

    def mundo(self, tela, cam_dx=0.0, cam_dy=0.0):
        self.pista.renderizar(tela, self.pos, self.x * ROAD_W + cam_dx, self.y_jogador() + CAM_H + cam_dy, self.estilo, self.t)


# ---------------------------------------------------------------- JOGO 2: PRAIA
class Praia(CenaPista):
    titulo = "Correr na praia"
    dica = "W/SETA CIMA correr · A/D ou SETAS desviar (vá até a água!) · ESPAÇO beber água de coco"
    VMAX = 3800

    def __init__(self, app):
        super().__init__(app, construir_pista_praia(np.random.default_rng(4)), EstiloPraia(),
                         (96, 180, 235), (205, 232, 248), (86, 130, 150))
        self.x = 0.1
        self.estam = 1.0
        self.fase = 0.0
        self.passo_i = 0
        self.pulso = 0.0
        self.lado = 1
        self.sal = 0.0
        self.doce = 0.0
        self.dist = 0.0
        self.zona = "molhada"
        self.cheiro, self.cheiro_nome = 0.3, "maresia"
        self.respingos = []

    def _zona(self):
        b = limite_agua(self.seg_jogador(), self.t)
        if self.x < -1.05:
            return "dunas"
        if self.x < -0.35:
            return "seca"
        return "molhada" if self.x < b else "agua"

    def _cheiro_local(self):
        base = self.pista.seg_em(self.pos + PLAYER_Z).i
        melhor, nome = 0.28 + 0.5 * clamp((self.x + 0.5) / 1.6), "maresia"
        for d in range(-4, 6):
            seg = self.pista.segs[(base + d) % self.pista.n]
            for (tipo, off, var) in seg.sprites:
                f = {"guarda_sol": (0.75, "protetor solar"), "barraca": (0.9, "coco e frituras"),
                     "palmeira": (0.40, "folhas de coqueiro")}.get(tipo)
                if f:
                    val = f[0] * clamp(1 - abs(self.x - off) / 3.5) * clamp(1 - abs(d) / 7)
                    if val > melhor:
                        melhor, nome = val, f[1]
        return melhor, nome

    def atualizar(self, dt, k):
        self.t += dt
        seg = self.seg_jogador()
        self.zona = zona = self._zona()
        correr = k[pygame.K_UP] or k[pygame.K_w]
        esq = k[pygame.K_LEFT] or k[pygame.K_a]
        dire = k[pygame.K_RIGHT] or k[pygame.K_d]
        bebe = bool(k[pygame.K_SPACE])
        vm = self.VMAX * {"seca": 0.82, "molhada": 1.0, "agua": 0.72, "dunas": 0.5}[zona]
        if self.estam < 0.08:
            vm *= 0.45
        if bebe:
            self.estam = min(1.0, self.estam + dt * 0.5)
        alvo = vm if (correr and not bebe) else 0.0
        ac = 3500 * dt if alvo > self.vel else 4500 * dt
        self.vel = min(alvo, self.vel + ac) if self.vel < alvo else max(alvo, self.vel - ac)
        vp = self.vel / self.VMAX
        if vp > 0.55:
            self.estam = max(0.0, self.estam - dt * 0.045 * vp)
        elif not bebe:
            self.estam = min(1.0, self.estam + dt * 0.03)
        dx = dt * (0.6 + 1.4 * vp)
        if esq:
            self.x -= dx
        if dire:
            self.x += dx
        self.x = clamp(self.x - dt * vp * seg.curva * 0.18, -1.6, 1.5)
        self.pos = (self.pos + self.vel * dt) % self.pista.comp
        self.dist += self.vel * dt
        self.bg += seg.curva * vp * dt * 40

        # passadas
        self.fase += self.vel * dt / 1100
        if int(self.fase) != self.passo_i:
            self.passo_i = int(self.fase)
            self.lado = -self.lado
            self.pulso = max(self.pulso, {"seca": 0.8, "molhada": 1.0, "agua": 0.65, "dunas": 0.7}[zona] * (0.5 + 0.5 * vp))
            self.app.sons.tocar("splash" if zona == "agua" else "passo", 0.5)
            if zona == "agua":
                for _ in range(7):
                    self.respingos.append([GAME_W / 2 + random.uniform(-160, 160), GAME_H - 40,
                                           random.uniform(-90, 90), random.uniform(-330, -140), 0.7])
        self.pulso *= math.exp(-dt * 6)
        for r in self.respingos:
            r[0] += r[2] * dt
            r[1] += r[3] * dt
            r[3] += 700 * dt
            r[4] -= dt
        self.respingos = [r for r in self.respingos if r[4] > 0]

        self.sal = min(1.0, self.sal + dt * 3) if zona == "agua" else self.sal * math.exp(-dt * 0.5)
        self.doce += ((0.9 if bebe else 0.0) - self.doce) * min(1.0, dt * 3)
        c, nome = self._cheiro_local()
        self.cheiro += (c - self.cheiro) * min(1.0, dt * 3)
        self.cheiro_nome = nome
        prox = clamp((self.x + 0.5) / 1.6)
        self.app.sons.loop("onda", 0.25 + 0.5 * prox)

    def desenhar(self, tela):
        self.desenhar_fundo(tela, praia=True)
        vp = self.vel / self.VMAX
        bob = math.sin(self.fase * math.pi) * 35 * vp
        self.mundo(tela, 0, bob)
        for r in self.respingos:
            pygame.draw.circle(tela, (235, 248, 255), (int(r[0]), int(r[1])), 3)
        # pés (primeira pessoa)
        for lado in (-1, 1):
            levanta = max(0.0, math.sin(self.fase * math.pi)) if lado == self.lado else 0.0
            fx = GAME_W // 2 + lado * 95
            fy = GAME_H - 28 - 38 * levanta * vp
            pygame.draw.ellipse(tela, (224, 172, 130), (fx - 38, fy - 14, 76, 30))
            for q in range(4):
                pygame.draw.circle(tela, (214, 160, 120), (fx - 24 + q * 14, int(fy - 18)), 6)
        self.app.hud(tela, "CORRER NA PRAIA", self.hud_linhas(), self.dica)
        pygame.draw.rect(tela, (30, 30, 40), (14, 100, 120, 10))
        pygame.draw.rect(tela, (90, 220, 120) if self.estam > 0.25 else (240, 90, 80), (14, 100, int(120 * self.estam), 10))
        txt(self.app.tela, self.app.f_p, "fôlego", 142, 97, (255, 255, 255))

    def hud_linhas(self):
        return ["Distância: %d m" % int(self.dist / 400), "Cadência: %d passos/min" % int(self.vel / 1100 * 60)]

    def sensores(self):
        vp = self.vel / self.VMAX
        z = self.zona
        prox = clamp((self.x + 0.5) / 1.6)
        visao = 0.30 + 0.65 * vp
        audicao = 0.30 + 0.35 * prox + 0.55 * self.pulso
        tato = 0.12 + 0.28 * vp + 1.0 * self.pulso + (0.5 if z == "agua" else 0.0)
        paladar = max(0.75 * self.sal, self.doce)
        txt_z = {"seca": "areia seca e morna", "molhada": "areia úmida e firme", "agua": "água fria nos pés",
                 "dunas": "areia fofa das dunas"}[z]
        sens = "%s · cheiro de %s" % (txt_z, self.cheiro_nome)
        if self.doce > 0.3:
            sens = "Bebendo água de coco gelada · sabor doce"
        elif self.sal > 0.3:
            sens = "Respingo de mar · sabor salgado · " + txt_z
        return N(visao, audicao, tato, self.cheiro, paladar), sens


# ---------------------------------------------------------------- JOGO 3: MOTO
class Moto(CenaPista):
    titulo = "Dirigir moto"
    dica = "SETA CIMA/W acelerar · SETA BAIXO/S frear · ESQ/DIR inclinar · H buzina"
    VMAX = 11000

    def __init__(self, app):
        rng = np.random.default_rng(9)
        super().__init__(app, construir_pista_moto(rng), EstiloMoto(), (86, 150, 230), (205, 228, 246), (70, 104, 140))
        self.incl = 0.0
        self.quase = self.batida = self.buzina = self.inseto = 0.0
        self.t_inseto = random.uniform(10, 20)
        self.pos_inseto = (random.randint(250, 650), random.randint(70, 180))
        self.carros = []
        for _ in range(16):
            z = random.uniform(3000, self.pista.comp - 1000)
            c = Carro(z, random.choice((-0.5, 0.5)), self.VMAX * random.uniform(0.18, 0.5),
                      random.choice(((200, 40, 40), (40, 90, 200), (230, 200, 50), (60, 160, 90), (230, 230, 235))))
            self.carros.append(c)
            self.pista.seg_em(z).carros.append(c)
        self.moto = self._moto()

    def _moto(self):
        s = pygame.Surface((300, 320), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 80), (60, 288, 180, 22))
        pygame.draw.rect(s, (24, 24, 28), (133, 190, 34, 112), border_radius=14)
        for q in range(6):
            pygame.draw.line(s, (60, 60, 66), (136, 200 + q * 17), (164, 200 + q * 17), 2)
        pygame.draw.polygon(s, (200, 30, 30), [(118, 205), (182, 205), (172, 150), (128, 150)])
        pygame.draw.rect(s, (255, 60, 60), (140, 172, 20, 10))
        pygame.draw.rect(s, (50, 50, 56), (104, 172, 26, 42), border_radius=5)
        pygame.draw.rect(s, (50, 50, 56), (170, 172, 26, 42), border_radius=5)
        pygame.draw.polygon(s, (30, 38, 70), [(122, 150), (178, 150), (172, 98), (128, 98)])
        pygame.draw.polygon(s, (40, 96, 205), [(120, 100), (180, 100), (172, 40), (128, 40)])
        pygame.draw.line(s, (240, 240, 240), (150, 42), (150, 98), 4)
        pygame.draw.line(s, (40, 96, 205), (130, 58), (72, 94), 15)
        pygame.draw.line(s, (40, 96, 205), (170, 58), (228, 94), 15)
        pygame.draw.circle(s, (20, 20, 22), (70, 96), 10)
        pygame.draw.circle(s, (20, 20, 22), (230, 96), 10)
        pygame.draw.line(s, (60, 60, 66), (62, 84), (56, 66), 3)
        pygame.draw.line(s, (60, 60, 66), (238, 84), (244, 66), 3)
        pygame.draw.circle(s, (244, 244, 246), (150, 26), 23)
        pygame.draw.rect(s, (210, 30, 40), (146, 6, 8, 40))
        return s

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_h:
            self.buzina = 1.0
            self.app.sons.tocar("buzina")

    def atualizar(self, dt, k):
        self.t += dt
        s = self.app.sons
        seg = self.seg_jogador()
        vp = self.vel / self.VMAX
        acel = k[pygame.K_UP] or k[pygame.K_w]
        freia = k[pygame.K_DOWN] or k[pygame.K_s]
        esq = k[pygame.K_LEFT] or k[pygame.K_a]
        dire = k[pygame.K_RIGHT] or k[pygame.K_d]
        if acel:
            self.vel += self.VMAX / 4.5 * dt
        elif freia:
            self.vel -= self.VMAX * 0.9 * dt
        else:
            self.vel -= self.VMAX / 5 * dt
        if abs(self.x) > 1.0 and self.vel > self.VMAX / 4:
            self.vel -= self.VMAX / 2 * dt
        self.vel = clamp(self.vel, 0.0, self.VMAX)
        vp = self.vel / self.VMAX
        dx = dt * 2.0 * vp
        if esq:
            self.x -= dx
        if dire:
            self.x += dx
        self.x -= dx * vp * seg.curva * 0.22
        self.x = clamp(self.x, -2.2, 2.2)
        self.incl += ((float(bool(dire)) - float(bool(esq))) - seg.curva * 0.12 * vp - self.incl) * min(1.0, dt * 6)

        L = self.pista.comp
        self.pos = (self.pos + self.vel * dt) % L
        self.bg += seg.curva * vp * dt * 40

        # tráfego
        pz = self.pos + PLAYER_Z
        for c in self.carros:
            velha = self.pista.seg_em(c.z)
            c.z = (c.z + c.vel * dt) % L
            nova = self.pista.seg_em(c.z)
            if velha is not nova:
                velha.carros.remove(c)
                nova.carros.append(c)
            rel = (c.z - pz + L / 2) % L - L / 2
            if abs(rel) < 220 and abs(self.x - c.x) < 0.34 and self.vel > c.vel:
                self.vel = c.vel * 0.5
                self.pos = (c.z - PLAYER_Z - 260) % L
                self.x += random.choice((-1, 1)) * 0.25
                self.batida, self.tremor = 1.0, 1.0
                s.tocar("batida")
            elif c.rel_ant > 0 >= rel and abs(self.x - c.x) < 0.65 and self.vel > c.vel:
                self.quase = 1.0
            c.rel_ant = rel

        self.t_inseto -= dt
        if self.t_inseto <= 0 and vp > 0.45:
            self.inseto = 1.0
            self.t_inseto = random.uniform(15, 28)
            self.pos_inseto = (random.randint(250, 650), random.randint(70, 180))
        self.batida *= math.exp(-dt * 3)
        self.quase *= math.exp(-dt * 2.5)
        self.buzina = max(0.0, self.buzina - dt * 2)
        self.inseto *= math.exp(-dt * 0.35)
        self.tremor *= math.exp(-dt * 4)

        s.loop("motor1", clamp(1 - vp * 3) * 0.55 + 0.15)
        s.loop("motor2", clamp(1 - abs(vp - 0.45) / 0.35) * 0.55)
        s.loop("motor3", clamp((vp - 0.4) * 1.7) * 0.55)

    def desenhar(self, tela):
        self.desenhar_fundo(tela)
        sh = self.tremor * 60
        self.mundo(tela, random.uniform(-sh, sh), random.uniform(-sh, sh) * 0.6)
        vp = self.vel / self.VMAX
        if vp > 0.7:
            for _ in range(10):
                a = random.uniform(0, 2 * math.pi)
                r1, r2 = random.uniform(300, 380), random.uniform(430, 520)
                pygame.draw.line(tela, (230, 235, 245), (GAME_W / 2 + r1 * math.cos(a), GAME_H / 2 + r1 * math.sin(a) * 0.6),
                                 (GAME_W / 2 + r2 * math.cos(a), GAME_H / 2 + r2 * math.sin(a) * 0.6), 1)
        img = pygame.transform.rotozoom(self.moto, -self.incl * 14, 1.0)
        tela.blit(img, img.get_rect(center=(GAME_W // 2 + self.incl * 20 + random.uniform(-1, 1) * vp * 2, GAME_H - 160)))
        if self.inseto > 0.15:
            pygame.draw.circle(tela, (210, 220, 90), self.pos_inseto, int(4 + 6 * self.inseto))
        self.app.hud(tela, "DIRIGIR MOTO", self.hud_linhas(), self.dica)

    def hud_linhas(self):
        z = ZONAS_MOTO[self.seg_jogador().zona]
        return ["%d km/h" % int(self.vel / self.VMAX * 190), "Região: " + z["nome"]]

    def sensores(self):
        vp = self.vel / self.VMAX
        z = ZONAS_MOTO[self.seg_jogador().zona]
        visao = 0.28 + 0.62 * vp + 0.3 * self.quase + 0.4 * self.batida
        audicao = 0.22 + 0.7 * vp + 0.9 * self.buzina + 1.0 * self.batida
        tato = 0.12 + 0.35 * vp + 0.35 * abs(self.incl) + 0.45 * self.quase + 0.9 * self.batida + 0.3 * self.inseto
        olfato = 0.25 + 0.45 * (0.5 + 0.5 * math.sin(self.t * 0.4))
        paladar = 0.05 + 0.7 * self.inseto
        if self.batida > 0.3:
            sens = "COLISÃO · impacto no guidão e estrondo"
        elif self.inseto > 0.3:
            sens = "Inseto no capacete · gosto amargo"
        elif self.quase > 0.3:
            sens = "Ultrapassagem rente · adrenalina"
        else:
            sens = "%d km/h · vento e vibração · cheiro de %s" % (int(vp * 190), z["cheiro"])
        return N(visao, audicao, tato, olfato, paladar), sens


# ----------------------------------------------------------------------------
# PROCESSO 1: JANELA DO JOGO
# ----------------------------------------------------------------------------
def executar_jogo(fila, max_frames=None):
    os.environ["SDL_VIDEO_WINDOW_POS"] = "%d,%d" % GAME_POS
    try:
        pygame.mixer.pre_init(22050, -16, 2, 512)
    except Exception:
        pass
    pygame.init()
    tela = pygame.display.set_mode((GAME_W, GAME_H))
    pygame.display.set_caption("DABOIT-BCI-1 · Simulador Sinestésico")
    relogio = pygame.time.Clock()
    app = App(fila, tela)
    app.cena = Menu(app)
    rodando, frames = True, 0
    while rodando:
        dt = min(0.05, relogio.tick(60) / 1000.0)
        frames += 1
        if max_frames is not None and frames > max_frames:
            break
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                rodando = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if isinstance(app.cena, Menu):
                        rodando = False
                    else:
                        app.trocar(Menu(app))
                elif ev.key == pygame.K_k:
                    app.kill = not app.kill
                else:
                    app.cena.evento(ev)
        k = pygame.key.get_pressed()
        cena = app.cena
        cena.atualizar(dt, k)
        cena.desenhar(tela)
        if isinstance(cena, Menu):
            app.hud(tela, "MENU", [], "1/2/3 escolhe o jogo · K disjuntor · ESC sai")
        app.t_envio += dt
        if app.t_envio >= 1 / 30:
            app.t_envio = 0.0
            niv, sens = cena.sensores()
            app.enviar(niv, cena.titulo, sens)
        pygame.display.flip()
    app.sons.parar_tudo()
    pygame.quit()


def main():
    mp.freeze_support()
    ctx = mp.get_context("spawn")
    fila = ctx.Queue(maxsize=60)
    cerebro = ctx.Process(target=processo_cerebro, args=(fila,), daemon=True)
    cerebro.start()
    try:
        executar_jogo(fila)
    finally:
        try:
            fila.put_nowait({"sair": True})
        except Exception:
            pass
        time.sleep(0.2)
        if cerebro.is_alive():
            cerebro.terminate()


if __name__ == "__main__":
    main()

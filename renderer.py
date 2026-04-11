# ============================================================
# renderer.py — Renderização completa e tratamento de UI
# ============================================================

import math
import random
import pygame

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TOP_H, MAIN_H, BOTTOM_H, LOG_H,
    LOG_SIDEBAR_W, LEFT_W, CENTER_W, RIGHT_W,
    BLACK, DARK_BG, PANEL_BG, PANEL_BDR, CAVE_BG,
    DARK_BROWN, MED_BROWN, LIGHT_BROWN,
    WHITE, GRAY, DARK_GRAY,
    RED, DARK_RED, GREEN, DARK_GREEN, BLUE, YELLOW, ORANGE, PURPLE, CYAN, GOLD, PINK,
    RARITY_COLORS, RESOURCES, RESOURCE_ORDER, MINE_UPGRADES, UPGRADE_ORDER,
    MINE_DEPTHS, ACHIEVEMENTS, PRESTIGE_GOLD_REQ, GROWTH_TIME,
)


# ============================================================
# COMPONENTE: BOTÃO
# ============================================================

class Btn:
    """Botão simples com estado hover e desativado."""

    def __init__(self, x, y, w, h, texto, cor=None, cor_txt=None, disabled=False):
        self.rect     = pygame.Rect(x, y, w, h)
        self.texto    = texto
        self.cor      = cor or MED_BROWN
        self.cor_txt  = cor_txt or WHITE
        self.disabled = disabled
        self.hovered  = False

    def update(self, mp):
        self.hovered = self.rect.collidepoint(mp) and not self.disabled

    def draw(self, surf, font):
        if self.disabled:
            c = DARK_GRAY
        elif self.hovered:
            c = tuple(min(255, v + 35) for v in self.cor)
        else:
            c = self.cor
        pygame.draw.rect(surf, c, self.rect, border_radius=4)
        pygame.draw.rect(surf, PANEL_BDR, self.rect, 1, border_radius=4)
        ts = font.render(self.texto, True, GRAY if self.disabled else self.cor_txt)
        surf.blit(ts, ts.get_rect(center=self.rect.center))

    def clicked(self, ev):
        return (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.rect.collidepoint(ev.pos) and not self.disabled)


# ============================================================
# RENDERER PRINCIPAL
# ============================================================

class Renderer:
    """
    Layout (1280×720) com barra lateral de log à esquerda:
      Log sidebar : (0,   0,   185, 720)   — log full-height com scroll
      Top bar     : (185, 0,   1095, 40)
      Mine        : (185, 40,  360,  480)  — mina com pixel art
      Center      : (545, 40,  445,  480)  — lista de escravos
      Right       : (990, 40,  290,  480)  — recursos / stats
      Bottom      : (185, 520, 1095, 160)  — abas
      Log strip   : (185, 680, 1095, 40)   — última mensagem
    """

    TABS = ["Loja", "Upgrades", "Breeding", "Mercado", "Prestígio", "Conquistas"]
    OX   = LOG_SIDEBAR_W  # offset x de todos os painéis principais

    def __init__(self, screen, game):
        self.screen = screen
        self.game   = game

        pygame.font.init()
        self.f_big    = pygame.font.SysFont("monospace", 20, bold=True)
        self.f_title  = pygame.font.SysFont("monospace", 15, bold=True)
        self.f_normal = pygame.font.SysFont("monospace", 13)
        self.f_small  = pygame.font.SysFont("monospace", 11)

        OX = self.OX
        # Regiões
        self.r_sidebar = pygame.Rect(0,           0,          LOG_SIDEBAR_W,          SCREEN_HEIGHT)
        self.r_top     = pygame.Rect(OX,          0,          SCREEN_WIDTH - OX,      TOP_H)
        self.r_left    = pygame.Rect(OX,          TOP_H,      LEFT_W,                 MAIN_H)
        self.r_center  = pygame.Rect(OX+LEFT_W,   TOP_H,      CENTER_W,               MAIN_H)
        self.r_right   = pygame.Rect(OX+LEFT_W+CENTER_W, TOP_H, RIGHT_W,             MAIN_H)
        self.r_bottom  = pygame.Rect(OX,          TOP_H+MAIN_H, SCREEN_WIDTH - OX,   BOTTOM_H)
        self.r_log     = pygame.Rect(OX,          TOP_H+MAIN_H+BOTTOM_H, SCREEN_WIDTH-OX, LOG_H)

        # Estado UI
        self.tab          = 0
        self.slave_scroll = 0
        self.log_scroll   = 0
        self.tooltip_slave = None
        self.selected_id  = None
        self.show_tutorial = True

        self._build_topbar_buttons()
        self._build_tab_buttons()

        self.dyn_btns: list[tuple[Btn, tuple]] = []

        self._cave       = self._gen_cave()
        self._particles: list[list] = []
        self._flash: dict[int, float] = {}

    # ------------------------------------------------------------------
    # Botões estáticos
    # ------------------------------------------------------------------

    def _build_topbar_buttons(self):
        bw   = 72
        base = SCREEN_WIDTH
        self.btn_aceler = Btn(base-bw*6-36, 5, bw+14, 30, "Acelerar", cor=(80, 40, 90))
        self.btn_save   = Btn(base-bw*5-24, 5, bw,    30, "Salvar",   cor=(30, 55, 100))
        self.btn_pause  = Btn(base-bw*4-16, 5, bw,    30, "Pause",    cor=(70, 45, 15))
        self.btn_1x     = Btn(base-bw*3-8,  5, bw-10, 30, "1x",       cor=(30, 70, 30))
        self.btn_2x     = Btn(base-bw*2-2,  5, bw-10, 30, "2x",       cor=(70, 70, 20))
        self.btn_4x     = Btn(base-bw*1+4,  5, bw-10, 30, "4x",       cor=(90, 30, 30))
        self._top_btns  = [self.btn_aceler, self.btn_save, self.btn_pause,
                           self.btn_1x, self.btn_2x, self.btn_4x]

    def _build_tab_buttons(self):
        OX = self.OX
        tw  = (SCREEN_WIDTH - OX) // len(self.TABS)
        self.tab_btns = [
            Btn(OX + i * tw, TOP_H+MAIN_H, tw-2, 22, t)
            for i, t in enumerate(self.TABS)
        ]

    # ------------------------------------------------------------------
    # Cave background (gerado proceduralmente com seed fixa)
    # ------------------------------------------------------------------

    def _gen_cave(self):
        surf = pygame.Surface((LEFT_W, MAIN_H))
        surf.fill(CAVE_BG)
        rng = random.Random(1337)

        # Pedras / textura
        for _ in range(220):
            x = rng.randint(0, LEFT_W-1)
            y = rng.randint(0, MAIN_H-1)
            r = rng.randint(8, 30)
            g = rng.randint(6, 14)
            b = rng.randint(3, 8)
            w = rng.randint(10, 45)
            h = rng.randint(5, 20)
            pygame.draw.ellipse(surf, (r, g, b), (x, y, w, h))

        # Vigas horizontais
        for yv in range(80, MAIN_H, 90):
            pygame.draw.rect(surf, (50, 32, 10), (0, yv, LEFT_W, 9))
            pygame.draw.rect(surf, (70, 46, 18), (0, yv, LEFT_W, 3))

        # Trilhos verticais
        mx = LEFT_W // 2
        pygame.draw.rect(surf, (75, 75, 75), (mx-42, 0, 7, MAIN_H))
        pygame.draw.rect(surf, (75, 75, 75), (mx+34, 0, 7, MAIN_H))
        for yi in range(0, MAIN_H, 25):
            pygame.draw.rect(surf, (55, 35, 12), (mx-42, yi, 83, 4))

        # Brilhos de minério decorativos
        vein_colors = [c["cor"] for c in RESOURCES.values() if c["raridade"] < 0.15]
        for _ in range(22):
            x = rng.randint(5, LEFT_W-10)
            y = rng.randint(5, MAIN_H-10)
            cor = rng.choice(vein_colors)
            pygame.draw.circle(surf, cor, (x, y), rng.randint(2, 5))

        return surf

    # ------------------------------------------------------------------
    # DRAW PRINCIPAL
    # ------------------------------------------------------------------

    def draw(self):
        self.dyn_btns.clear()
        self.tooltip_slave = None
        mp = pygame.mouse.get_pos()
        OX = self.OX

        self.screen.fill(DARK_BG)

        self._draw_log_sidebar()
        self._draw_topbar(mp)
        self._draw_left(mp)
        self._draw_center(mp)
        self._draw_right(mp)
        self._draw_bottom(mp)
        self._draw_log()

        # Divisórias
        def vline(x, y1, y2): pygame.draw.line(self.screen, PANEL_BDR, (x, y1), (x, y2), 1)
        def hline(y, x1, x2): pygame.draw.line(self.screen, PANEL_BDR, (x1, y), (x2, y), 1)
        vline(OX,                 0,     SCREEN_HEIGHT)
        hline(TOP_H,              OX,    SCREEN_WIDTH)
        hline(TOP_H+MAIN_H,       OX,    SCREEN_WIDTH)
        hline(TOP_H+MAIN_H+BOTTOM_H, OX, SCREEN_WIDTH)
        vline(OX+LEFT_W,          TOP_H, TOP_H+MAIN_H)
        vline(OX+LEFT_W+CENTER_W, TOP_H, TOP_H+MAIN_H)

        # Overlays
        if self.tooltip_slave:
            self._draw_tooltip(mp)
        if self.game.notificacao:
            self._draw_notif()
        if self.show_tutorial:
            self._draw_tutorial()

    # ------------------------------------------------------------------
    # BARRA LATERAL DE LOG (altura total da tela)
    # ------------------------------------------------------------------

    def _draw_log_sidebar(self):
        OX  = self.OX
        log = self.game.log

        pygame.draw.rect(self.screen, (8, 5, 2), self.r_sidebar)

        # Header
        pygame.draw.rect(self.screen, PANEL_BG, (0, 0, OX, 22))
        self.screen.blit(self.f_small.render("EVENTOS", True, LIGHT_BROWN), (5, 5))
        pygame.draw.line(self.screen, PANEL_BDR, (0, 22), (OX, 22), 1)

        LINE_H    = 14
        area_y    = 23
        area_h    = SCREEN_HEIGHT - area_y
        max_vis   = area_h // LINE_H
        total     = len(log)
        max_scroll = max(0, total - max_vis)
        self.log_scroll = max(0, min(max_scroll, self.log_scroll))

        for i, entry in enumerate(log[self.log_scroll: self.log_scroll + max_vis]):
            y = area_y + i * LINE_H
            # barra colorida à esquerda
            pygame.draw.rect(self.screen, entry["cor"], (0, y+1, 3, LINE_H-2))
            txt = entry["msg"][:24]
            self.screen.blit(self.f_small.render(txt, True, entry["cor"]), (5, y+1))

        # Scrollbar (4px à direita da sidebar)
        if total > max_vis and max_scroll > 0:
            sb_h     = area_h
            th       = max(16, int(sb_h * max_vis / total))
            ty       = area_y + int((self.log_scroll / max_scroll) * (sb_h - th))
            pygame.draw.rect(self.screen, DARK_GRAY,  (OX-5, area_y, 4, sb_h))
            pygame.draw.rect(self.screen, MED_BROWN,  (OX-5, ty, 4, th))

    # ------------------------------------------------------------------
    # TOP BAR
    # ------------------------------------------------------------------

    def _draw_topbar(self, mp):
        OX = self.OX
        pygame.draw.rect(self.screen, PANEL_BG, self.r_top)

        self.screen.blit(self.f_title.render("MINA DOS ESCRAVOS ETERNOS", True, LIGHT_BROWN), (OX+8, 12))

        ouro_s = f"Ouro: {self.game.ouro:>12,.0f}g"
        self.screen.blit(self.f_title.render(ouro_s, True, GOLD), (OX+230, 12))

        vi = self.game.valor_inventario
        if vi:
            self.screen.blit(self.f_small.render(f"+{vi:,.0f}g inv", True, YELLOW), (OX+450, 14))

        if self.game.prestigios:
            self.screen.blit(
                self.f_small.render(f"Prest.{self.game.prestigios} | Almas:{self.game.almas_eternas}", True, GOLD),
                (OX+560, 14)
            )

        if self.game.mercado_negro:
            self.screen.blit(
                self.f_small.render(f"MERCADO NEGRO {self.game.mercado_negro_timer:.0f}s", True, CYAN),
                (OX+8, 26)
            )

        for btn in self._top_btns:
            btn.update(mp)
            btn.draw(self.screen, self.f_small)

        for btn, spd in [(self.btn_1x, 1), (self.btn_2x, 2), (self.btn_4x, 4)]:
            if self.game.velocidade == spd and not self.game.pausado:
                pygame.draw.rect(self.screen, GOLD, btn.rect, 2, border_radius=4)
        if self.game.pausado:
            pygame.draw.rect(self.screen, RED, self.btn_pause.rect, 2, border_radius=4)

    # ------------------------------------------------------------------
    # PAINEL ESQUERDO — MINA COM PIXEL ART
    # ------------------------------------------------------------------

    def _draw_left(self, mp):
        OX = self.OX
        self.screen.blit(self._cave, (OX, TOP_H))

        game   = self.game
        vivos  = game.escravos_vivos
        bebes  = game.bebes
        todos  = vivos + bebes
        t_real = pygame.time.get_ticks() * 0.001

        COLS = 4
        CW   = LEFT_W // COLS
        CH   = 72

        self.screen.set_clip(pygame.Rect(OX, TOP_H, LEFT_W, MAIN_H))

        for i, e in enumerate(todos[:24]):
            col = i % COLS
            row = i // COLS
            cx  = OX + col * CW + CW // 2
            cy  = TOP_H + 40 + row * CH

            e.anim_x = cx
            e.anim_y = cy

            self._draw_miner_pixel(cx, cy, e, t_real)

        self.screen.set_clip(None)

        # Atualiza flashes
        dt = 1.0 / 60
        for eid in list(self._flash.keys()):
            self._flash[eid] -= dt
            if self._flash[eid] <= 0:
                del self._flash[eid]

        self._update_particles()

        # Info na base do painel
        depth_txt = MINE_DEPTHS[game.nivel_mina]["nome"]
        self.screen.blit(self.f_small.render(depth_txt, True, LIGHT_BROWN), (OX+4, TOP_H + MAIN_H - 26))
        cnt_txt = f"{len(vivos)} trab. | {len(bebes)} bebe(s)"
        self.screen.blit(self.f_small.render(cnt_txt, True, GRAY), (OX+4, TOP_H + MAIN_H - 13))

    def _draw_miner_pixel(self, cx, cy, e, t_real):
        """Desenha um minerador em pixel art na posição (cx, cy)."""
        flash_t  = self._flash.get(e.id, 0)
        cor_raro = e.cor_raridade()
        cor_gen  = BLUE if e.genero == "M" else PINK

        # Bob suave
        bob = math.sin(t_real * 2.5 + e.anim_frame * 0.4) * 2.5
        yo  = int(bob)

        if e.eh_bebe:
            # ---- BEBÊ ----
            cap_cor = (100, 105, 115)
            pygame.draw.rect(self.screen, cap_cor,          (cx-5, cy-13+yo, 10, 3))   # aba chapéu
            pygame.draw.rect(self.screen, cap_cor,          (cx-4, cy-16+yo, 8,  3))   # topo chapéu
            pygame.draw.rect(self.screen, (220, 185, 145),  (cx-4, cy-10+yo, 8,  8))   # cabeça
            pygame.draw.rect(self.screen, (30, 20, 10),     (cx+1, cy-8+yo,  2,  2))   # olhinho
            pygame.draw.rect(self.screen, cor_gen,          (cx-4, cy-2+yo,  8,  7))   # corpo
            pygame.draw.rect(self.screen, (50, 45, 65),     (cx-4, cy+5+yo,  3,  5))   # perna e
            pygame.draw.rect(self.screen, (50, 45, 65),     (cx+1, cy+5+yo,  3,  5))   # perna d
            # borda de raridade
            pygame.draw.rect(self.screen, cor_raro, (cx-7, cy-18+yo, 14, 32), 1, border_radius=2)
            return

        # ---- ADULTO ----
        skin   = (220, 185, 145)
        helm   = (108, 114, 124)
        helm_d = (78,  84,  94)
        body   = (88,  56,  20)
        body_d = (65,  40,  12)
        pants  = (46,  42,  70)
        pants_d= (32,  30,  52)
        boot   = (40,  24,  8)
        lamp_c = (255, 215, 70)

        swing = math.sin(t_real * 5.5 + e.anim_frame * 0.6) * 30
        vp    = e.vida / e.vida_max
        vc    = GREEN if vp > 0.5 else (YELLOW if vp > 0.25 else RED)

        # --- GLOW DE RARIDADE (sempre visível como borda) ---
        alpha_glow = 90 + int(45 * math.sin(t_real * 3 + e.anim_frame))
        if flash_t > 0:
            alpha_glow = 230
        gs = pygame.Surface((34, 52), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*cor_raro, alpha_glow), (0, 0, 34, 52), 2, border_radius=3)
        self.screen.blit(gs, (cx-17, cy-40+yo))

        # --- BARRA DE VIDA (acima do capacete) ---
        bw = 26; bh = 3
        bx = cx - bw // 2
        pygame.draw.rect(self.screen, DARK_RED, (bx, cy-45+yo, bw, bh))
        pygame.draw.rect(self.screen, vc,       (bx, cy-45+yo, int(bw*vp), bh))

        # --- CAPACETE ---
        pygame.draw.rect(self.screen, helm_d, (cx-10, cy-37+yo, 20, 6))   # aba
        pygame.draw.rect(self.screen, helm,   (cx-8,  cy-43+yo, 16, 7))   # cúpula
        pygame.draw.rect(self.screen, helm_d, (cx-8,  cy-43+yo, 16, 2))   # sombra topo
        pygame.draw.rect(self.screen, lamp_c, (cx-3,  cy-38+yo, 6,  3))   # lâmpada
        pygame.draw.rect(self.screen, (255,255,200), (cx-1, cy-37+yo, 2, 1))  # brilho lâmpada

        # --- CABEÇA ---
        pygame.draw.rect(self.screen, skin,          (cx-6, cy-31+yo, 12, 12))  # rosto
        pygame.draw.rect(self.screen, (200,160,120), (cx-6, cy-20+yo, 12, 2))   # queixo/pescoço
        # Olho
        eye_x = cx+2 if e.genero == "M" else cx+1
        pygame.draw.rect(self.screen, (30, 20, 10),  (eye_x, cy-28+yo, 2, 2))
        # Brilho olho
        pygame.draw.rect(self.screen, WHITE,         (eye_x+1, cy-28+yo, 1, 1))
        # Boca
        pygame.draw.rect(self.screen, (175,120,105), (cx-2, cy-22+yo, 4, 1))

        # --- CORPO / TORSO ---
        pygame.draw.rect(self.screen, body,   (cx-7, cy-18+yo, 14, 14))
        pygame.draw.rect(self.screen, body_d, (cx-7, cy-18+yo, 2,  14))   # sombra lateral
        pygame.draw.rect(self.screen, body_d, (cx-7, cy-5+yo,  14, 1))    # cinto
        # Bolso
        pygame.draw.rect(self.screen, body_d, (cx-6, cy-16+yo, 5, 5))
        pygame.draw.rect(self.screen, (70,46,14), (cx-5, cy-15+yo, 3, 3))
        # Suspensórios
        pygame.draw.rect(self.screen, (65,42,14), (cx-4, cy-18+yo, 2, 10))
        pygame.draw.rect(self.screen, (65,42,14), (cx+2, cy-18+yo, 2, 10))

        # --- PERNAS ---
        pygame.draw.rect(self.screen, pants,   (cx-7, cy-4+yo,  6, 11))
        pygame.draw.rect(self.screen, pants,   (cx+1, cy-4+yo,  6, 11))
        pygame.draw.rect(self.screen, pants_d, (cx-7, cy-4+yo,  1, 11))   # sombra esq
        pygame.draw.rect(self.screen, pants_d, (cx+6, cy-4+yo,  1, 11))   # sombra dir
        # Joelhos
        pygame.draw.rect(self.screen, (56,52,80), (cx-7, cy+2+yo, 6, 2))
        pygame.draw.rect(self.screen, (56,52,80), (cx+1, cy+2+yo, 6, 2))

        # --- BOTAS ---
        pygame.draw.rect(self.screen, boot,      (cx-8, cy+7+yo,  7, 5))
        pygame.draw.rect(self.screen, boot,      (cx+1, cy+7+yo,  7, 5))
        pygame.draw.rect(self.screen, (26,14,4), (cx-9, cy+11+yo, 8, 2))  # sola esq
        pygame.draw.rect(self.screen, (26,14,4), (cx,   cy+11+yo, 8, 2))  # sola dir

        # --- BRAÇO ESQUERDO (balance oposto) ---
        arm_bob = math.sin(t_real * 2.5 + e.anim_frame * 0.4) * 3
        pygame.draw.rect(self.screen, skin, (cx-12, cy-16+yo+int(arm_bob), 4, 10))
        pygame.draw.rect(self.screen, body, (cx-12, cy-18+yo+int(arm_bob), 4, 4))   # manga

        # --- BRAÇO DIREITO + PICARETA ---
        if not e.eh_bebe and e.minerando:
            rad = math.radians(swing - 80)
            # Manga
            pygame.draw.rect(self.screen, body, (cx+8, cy-18+yo, 4, 5))
            # Braço
            pygame.draw.rect(self.screen, skin, (cx+8, cy-13+yo, 4, 8))
            # Cabo da picareta
            px0 = cx + 10; py0 = cy - 8 + yo
            px1 = px0 + int(18 * math.cos(rad))
            py1 = py0 + int(18 * math.sin(rad))
            pygame.draw.line(self.screen, (138, 92, 38), (px0, py0), (px1, py1), 2)
            # Cabeça metálica
            head_x = px1 - 3; head_y = py1 - 3
            pygame.draw.rect(self.screen, (185, 185, 200), (head_x, head_y, 6, 6))
            pygame.draw.rect(self.screen, (210, 210, 225), (head_x, head_y, 6, 2))  # highlight
            pygame.draw.rect(self.screen, (130, 130, 145), (head_x, head_y+4, 6, 2))  # sombra
        else:
            # Braço em repouso
            pygame.draw.rect(self.screen, body, (cx+8, cy-18+yo, 4, 5))
            pygame.draw.rect(self.screen, skin, (cx+8, cy-13+yo, 4, 10))

    def _update_particles(self):
        nxt = []
        for p in self._particles:
            p[0] += p[2]; p[1] += p[3]; p[3] += 0.08; p[4] -= 1
            if p[4] > 0:
                a = min(255, p[4] * 12)
                s = pygame.Surface((4, 4), pygame.SRCALPHA)
                s.fill((*p[5], a))
                self.screen.blit(s, (int(p[0]), int(p[1])))
                nxt.append(p)
        self._particles = nxt

    def spawn_particles(self, x, y, cor):
        """Cria partículas de mineração na posição (cx, cy) do escravo."""
        for _ in range(6):
            self._particles.append([
                float(x), float(y),
                random.uniform(-1.5, 1.5), random.uniform(-2.8, -0.5),
                random.randint(18, 35), cor
            ])

    # ------------------------------------------------------------------
    # PAINEL CENTRAL — LISTA DE ESCRAVOS
    # ------------------------------------------------------------------

    def _draw_center(self, mp):
        OX  = self.OX
        cx0 = OX + LEFT_W
        game = self.game
        pygame.draw.rect(self.screen, PANEL_BG, self.r_center)

        self.screen.blit(self.f_title.render("ESCRAVOS", True, LIGHT_BROWN), (cx0+8, TOP_H+6))
        n = len(game.escravos_vivos); b = len(game.bebes)
        self.screen.blit(self.f_small.render(f"{n} ativos | {b} bebê(s)", True, GRAY), (cx0+8, TOP_H+22))

        clip_top = TOP_H + 40
        clip_h   = MAIN_H - 40
        self.screen.set_clip(pygame.Rect(cx0, clip_top, CENTER_W, clip_h))

        LINHA_H = 55
        todos   = game.escravos_vivos + game.bebes

        for i, e in enumerate(todos):
            y0 = clip_top + i * LINHA_H - self.slave_scroll
            if y0 + LINHA_H < clip_top or y0 > clip_top + clip_h:
                continue

            bg = (30, 20, 10) if i % 2 == 0 else (24, 16, 8)
            pygame.draw.rect(self.screen, bg,             (cx0, y0, CENTER_W, LINHA_H-2))
            pygame.draw.rect(self.screen, e.cor_raridade(),(cx0, y0, 3, LINHA_H-2))

            if self.selected_id == e.id:
                pygame.draw.rect(self.screen, CYAN, (cx0, y0, CENTER_W-2, LINHA_H-2), 1)

            gc = BLUE if e.genero == "M" else PINK
            gs = "M" if e.genero == "M" else "F"
            self.screen.blit(self.f_small.render(gs, True, gc), (cx0+5, y0+6))

            nome = e.nome[:17] + (" bebe" if e.eh_bebe else "")
            self.screen.blit(self.f_normal.render(nome, True, WHITE), (cx0+18, y0+4))

            # Barra de vida
            bw = 110; bh = 7
            bx = cx0+18; by2 = y0+20
            pygame.draw.rect(self.screen, DARK_RED, (bx, by2, bw, bh), border_radius=3)
            vp = e.vida / e.vida_max
            vc = GREEN if vp > 0.5 else (YELLOW if vp > 0.25 else RED)
            pygame.draw.rect(self.screen, vc, (bx, by2, int(bw * vp), bh), border_radius=3)

            # Atributos
            attrs = [("F",e.forca),("V",e.velocidade),("R",e.resistencia),
                     ("Fe",e.fertilidade),("S",e.sorte),("L",e.lealdade)]
            atx = cx0+18; my0 = y0+34
            for j, (lbl, val) in enumerate(attrs):
                ax = atx + j * 37
                rc = RARITY_COLORS.get(e.raridade_attr(val), GRAY)
                self.screen.blit(self.f_small.render(f"{lbl}:{val}", True, rc), (ax, my0))

            if e.eh_bebe:
                pct = 1 - e.tempo_crescimento / GROWTH_TIME
                ss  = self.f_small.render(f"Cres.{pct*100:.0f}%", True, CYAN)
                self.screen.blit(ss, (atx + 6*37 + 2, my0))
            elif e.par_id:
                self.screen.blit(self.f_small.render("Par", True, PINK), (atx + 6*37 + 2, my0))

            # Botões de ação
            bx2 = cx0 + CENTER_W - 110
            if not e.eh_bebe:
                bv = Btn(bx2,    y0+5, 50, 19, "Vend.", cor=(100,50,20), cor_txt=YELLOW)
                bp = Btn(bx2+54, y0+5, 46, 19, "Par",   cor=(20,60,80))
                bv.update(mp); bv.draw(self.screen, self.f_small)
                bp.update(mp); bp.draw(self.screen, self.f_small)
                self.dyn_btns.append((bv, ("vender", e.id)))
                self.dyn_btns.append((bp, ("par",    e.id)))
            else:
                bvb = Btn(bx2, y0+5, 50, 19, "Vend.", cor=(100,50,20), cor_txt=YELLOW)
                bvb.update(mp); bvb.draw(self.screen, self.f_small)
                self.dyn_btns.append((bvb, ("vender", e.id)))

            if pygame.Rect(cx0, y0, CENTER_W-114, LINHA_H).collidepoint(mp):
                self.tooltip_slave = e

        self.screen.set_clip(None)

        # Scrollbar
        total_h = len(todos) * LINHA_H
        if total_h > clip_h:
            ratio = clip_h / total_h
            bh2   = max(20, int(clip_h * ratio))
            max_s = total_h - clip_h
            by2   = clip_top + int((self.slave_scroll / max_s) * (clip_h - bh2))
            xsb   = cx0 + CENTER_W - 5
            pygame.draw.rect(self.screen, PANEL_BDR, (xsb, clip_top, 5, clip_h))
            pygame.draw.rect(self.screen, MED_BROWN,  (xsb, by2, 5, bh2))

    # ------------------------------------------------------------------
    # PAINEL DIREITO — RECURSOS E STATS
    # ------------------------------------------------------------------

    def _draw_right(self, mp):
        OX   = self.OX
        rx   = OX + LEFT_W + CENTER_W
        game = self.game
        pygame.draw.rect(self.screen, PANEL_BG, self.r_right)

        y = TOP_H + 6
        self.screen.blit(self.f_title.render("RECURSOS", True, LIGHT_BROWN), (rx+6, y)); y += 18

        for nome in RESOURCE_ORDER:
            qtd = game.inventario.get(nome, 0)
            cor = RESOURCES[nome]["cor"]
            val = RESOURCES[nome]["valor"]
            tc  = WHITE if qtd else DARK_GRAY
            pygame.draw.circle(self.screen, cor, (rx+12, y+7), 6)
            self.screen.blit(self.f_normal.render(nome, True, tc),               (rx+22, y))
            self.screen.blit(self.f_normal.render(str(qtd), True, tc),           (rx+RIGHT_W-80, y))
            self.screen.blit(self.f_small.render(f"({val}g)", True, DARK_GRAY),  (rx+RIGHT_W-46, y+2))
            y += 19

        vt = game.valor_inventario
        pygame.draw.line(self.screen, PANEL_BDR, (rx+4, y+1), (rx+RIGHT_W-4, y+1), 1); y += 5
        self.screen.blit(self.f_normal.render(f"Inv: {vt:,.0f}g", True, GOLD), (rx+6, y)); y += 18

        bvt = Btn(rx+6, y, 100, 20, "Vender Tudo", cor=(80,58,18), cor_txt=GOLD)
        bvt.update(mp); bvt.draw(self.screen, self.f_small)
        self.dyn_btns.append((bvt, ("vender_tudo", None))); y += 26

        pygame.draw.line(self.screen, PANEL_BDR, (rx+4, y), (rx+RIGHT_W-4, y), 1); y += 5
        self.screen.blit(self.f_title.render("ESTATÍSTICAS", True, LIGHT_BROWN), (rx+6, y)); y += 16

        def stat(txt, cor=GRAY):
            self.screen.blit(self.f_small.render(txt, True, cor), (rx+6, y))

        st = game.stats
        stat(f"Comprados: {st['escravos_total']}");          y += 14
        stat(f"Mortos:    {st['mortos_total']}");            y += 14
        stat(f"Filhos:    {st['filhos_nascidos']}");         y += 14
        stat(f"Max simul: {st['max_simult']}");              y += 14
        stat(f"Ouro total:{st['ouro_total']:,.0f}g");        y += 14
        stat(f"Intervalo: {game.intervalo_efetivo:.1f}s");   y += 14
        stat(f"Raridade:  {game.mult_raridade:.2f}x");       y += 14
        stat(f"Recursos:  {game.mult_recursos:.2f}x");       y += 14
        stat(f"Risco:     {game.risco_morte*100:.1f}%");     y += 14
        stat(f"Lealdade:  {game.lealdade_media:.0f}");       y += 14
        stat(f"Prestigio: {game.bonus_prestigio:.1f}x",
             GOLD if game.prestigios else GRAY);             y += 16

        if y < TOP_H + MAIN_H - 50:
            pygame.draw.line(self.screen, PANEL_BDR, (rx+4, y), (rx+RIGHT_W-4, y), 1); y += 4
            dep = MINE_DEPTHS[game.nivel_mina]
            self.screen.blit(self.f_small.render(f"Mina: {dep['nome']}", True, LIGHT_BROWN), (rx+6, y)); y += 14
            if game.nivel_mina < len(MINE_DEPTHS)-1:
                prox = MINE_DEPTHS[game.nivel_mina+1]
                pode = game.ouro >= prox["custo"]
                self.screen.blit(
                    self.f_small.render(f"Prox: {prox['nome']} ({prox['custo']:,}g)", True, GREEN if pode else GRAY),
                    (rx+6, y)
                ); y += 14
                bap = Btn(rx+6, y, RIGHT_W-12, 20, "Aprofundar Mina",
                          cor=(50,80,28) if pode else (40,40,40), disabled=not pode)
                bap.update(mp); bap.draw(self.screen, self.f_small)
                self.dyn_btns.append((bap, ("aprofundar", None)))

    # ------------------------------------------------------------------
    # PAINEL INFERIOR — ABAS
    # ------------------------------------------------------------------

    def _draw_bottom(self, mp):
        pygame.draw.rect(self.screen, PANEL_BG, self.r_bottom)

        for i, btn in enumerate(self.tab_btns):
            btn.cor = MED_BROWN if i == self.tab else DARK_BROWN
            btn.update(mp)
            btn.draw(self.screen, self.f_small)

        cy = TOP_H + MAIN_H + 24

        if   self.tab == 0: self._tab_loja(mp, cy)
        elif self.tab == 1: self._tab_upgrades(mp, cy)
        elif self.tab == 2: self._tab_breeding(mp, cy)
        elif self.tab == 3: self._tab_mercado(mp, cy)
        elif self.tab == 4: self._tab_prestigio(mp, cy)
        elif self.tab == 5: self._tab_conquistas(mp, cy)

    # ABA 0: LOJA
    def _tab_loja(self, mp, cy):
        OX    = self.OX
        game  = self.game
        CW    = 192
        x     = OX + 6
        CH    = BOTTOM_H - 28

        for i, e in enumerate(game.loja):
            cx = x + i * (CW+4)
            if cx + CW > SCREEN_WIDTH - 148:
                break

            cor_r = e.cor_raridade()
            pygame.draw.rect(self.screen, (26,17,9), (cx, cy, CW, CH), border_radius=5)
            pygame.draw.rect(self.screen, cor_r, (cx, cy, CW, CH), 1, border_radius=5)

            gy = cy + 3
            gc = BLUE if e.genero=="M" else PINK
            gs = "M" if e.genero=="M" else "F"
            self.screen.blit(self.f_small.render(gs, True, gc), (cx+3, gy))
            self.screen.blit(self.f_small.render(e.nome[:15], True, WHITE), (cx+14, gy)); gy += 14
            self.screen.blit(self.f_small.render(e.raridade_geral(), True, cor_r), (cx+3, gy)); gy += 13

            attrs = [("For",e.forca),("Vel",e.velocidade),("Res",e.resistencia),
                     ("Fer",e.fertilidade),("Sor",e.sorte),("Lea",e.lealdade)]
            for j, (lbl, val) in enumerate(attrs):
                ax = cx+3 + (j%2)*92
                ay = gy + (j//2)*14
                rc = RARITY_COLORS.get(e.raridade_attr(val), GRAY)
                self.screen.blit(self.f_small.render(f"{lbl}:{val}", True, rc), (ax, ay))
            gy += 44

            preco = e.calcular_preco()
            self.screen.blit(self.f_small.render(f"{preco}g", True, GOLD), (cx+3, gy+1))
            pode = game.ouro >= preco
            bb = Btn(cx+CW-58, gy-1, 55, 20, "Comprar",
                     cor=(45,75,28) if pode else (40,40,40), disabled=not pode)
            bb.update(mp); bb.draw(self.screen, self.f_small)
            self.dyn_btns.append((bb, ("comprar_loja", i)))

        br = Btn(SCREEN_WIDTH-145, cy+8, 138, 26, f"Refresc. ({game.custo_refresco}g)", cor=(60,50,18))
        br.update(mp); br.draw(self.screen, self.f_small)
        self.dyn_btns.append((br, ("refresca", None)))

    # ABA 1: UPGRADES
    def _tab_upgrades(self, mp, cy):
        OX   = self.OX
        game = self.game
        UW   = 235
        for i, tipo in enumerate(UPGRADE_ORDER):
            ux  = OX + 6 + i * (UW+5)
            ud  = MINE_UPGRADES[tipo]
            lvl = game.upgrades[tipo]
            niveis = ud["niveis"]

            pygame.draw.rect(self.screen, (24,17,8), (ux, cy, UW, BOTTOM_H-28), border_radius=4)
            pygame.draw.rect(self.screen, PANEL_BDR, (ux, cy, UW, BOTTOM_H-28), 1, border_radius=4)

            gy = cy+4
            self.screen.blit(self.f_normal.render(ud["nome"], True, LIGHT_BROWN), (ux+4, gy)); gy += 16
            cur = niveis[lvl]["nome"]
            self.screen.blit(self.f_small.render(f"Atual: {cur}", True, GRAY), (ux+4, gy)); gy += 13

            bw2  = UW-10
            prog = lvl / (len(niveis)-1)
            pygame.draw.rect(self.screen, DARK_GRAY, (ux+4, gy, bw2, 5), border_radius=2)
            pygame.draw.rect(self.screen, CYAN, (ux+4, gy, int(bw2*prog), 5), border_radius=2)
            gy += 10

            desc = ud["desc"][:30]
            self.screen.blit(self.f_small.render(desc, True, DARK_GRAY), (ux+4, gy)); gy += 13

            if lvl < len(niveis)-1:
                prox  = niveis[lvl+1]
                custo = prox["custo"]
                pode  = game.ouro >= custo
                self.screen.blit(
                    self.f_small.render(f"Prox: {prox['nome']}", True, GREEN if pode else GRAY),
                    (ux+4, gy)
                ); gy += 12
                self.screen.blit(
                    self.f_small.render(f"Custo: {custo}g", True, GREEN if pode else GRAY),
                    (ux+4, gy)
                ); gy += 13
                bup = Btn(ux+4, gy, UW-8, 20, "Melhorar",
                          cor=(45,75,28) if pode else (40,40,40), disabled=not pode)
                bup.update(mp); bup.draw(self.screen, self.f_small)
                self.dyn_btns.append((bup, ("upgrade", tipo)))
            else:
                self.screen.blit(self.f_small.render("NIVEL MAXIMO", True, GOLD), (ux+4, gy))

    # ABA 2: BREEDING
    def _tab_breeding(self, mp, cy):
        OX = self.OX
        x  = OX + 8
        game = self.game
        self.screen.blit(
            self.f_normal.render("Use 'Par' na lista para formar um casal.", True, GRAY), (x, cy)
        )
        y = cy + 18

        if not game.pares:
            self.screen.blit(self.f_small.render("Nenhum par formado.", True, DARK_GRAY), (x, y))
        else:
            for hid, fid in game.pares[:6]:
                hm = game.get_escravo(hid); fm = game.get_escravo(fid)
                if not hm or not fm: continue
                txt = f"M {hm.nome[:12]}  x  F {fm.nome[:12]}"
                self.screen.blit(self.f_small.render(txt, True, CYAN), (x, y))
                bd = Btn(x+300, y-2, 62, 16, "Desfazer", cor=(80,28,18))
                bd.update(mp); bd.draw(self.screen, self.f_small)
                self.dyn_btns.append((bd, ("remover_par", hid)))
                y += 17

        bebes = game.bebes
        if bebes:
            y += 4
            self.screen.blit(self.f_small.render(f"Bebes crescendo: {len(bebes)}", True, PINK), (x, y))
            for e in bebes[:4]:
                y += 14
                pct = 1 - e.tempo_crescimento / GROWTH_TIME
                self.screen.blit(
                    self.f_small.render(f"  {e.nome} — {pct*100:.0f}% crescido", True, GRAY), (x, y)
                )

    # ABA 3: MERCADO
    def _tab_mercado(self, mp, cy):
        OX   = self.OX
        game = self.game
        x    = OX + 8
        y    = cy

        if game.mercado_negro:
            self.screen.blit(
                self.f_normal.render(f"MERCADO NEGRO ATIVO! +50%. {game.mercado_negro_timer:.0f}s", True, CYAN),
                (x, y)
            )
            y += 18

        cols = 4; cw2 = 268
        for i, nome in enumerate(RESOURCE_ORDER):
            qtd   = game.inventario.get(nome, 0)
            val   = RESOURCES[nome]["valor"]
            cor2  = RESOURCES[nome]["cor"]
            vef   = int(val*1.5) if game.mercado_negro else val
            total = qtd * vef

            cx2 = x + (i%cols)*cw2
            cy2 = y + (i//cols)*28
            pygame.draw.circle(self.screen, cor2, (cx2+8, cy2+10), 7)
            tc = WHITE if qtd else DARK_GRAY
            self.screen.blit(
                self.f_small.render(f"{nome}: {qtd}  ({total}g)", True, tc), (cx2+20, cy2+4)
            )
            if qtd:
                bv2 = Btn(cx2+175, cy2+1, 65, 18, "Vender", cor=(80,58,18), cor_txt=GOLD)
                bv2.update(mp); bv2.draw(self.screen, self.f_small)
                self.dyn_btns.append((bv2, ("vender_recurso", nome)))

        bvt2 = Btn(SCREEN_WIDTH-145, cy+4, 138, 24, "Vender Tudo", cor=(80,58,18))
        bvt2.update(mp); bvt2.draw(self.screen, self.f_small)
        self.dyn_btns.append((bvt2, ("vender_tudo", None)))

    # ABA 4: PRESTÍGIO
    def _tab_prestigio(self, mp, cy):
        OX   = self.OX
        game = self.game
        x    = OX + 8; y = cy
        req  = PRESTIGE_GOLD_REQ
        tot  = game.stats["ouro_total"]
        pode = game.pode_prestigiar()

        self.screen.blit(self.f_normal.render("PRESTIGIO — Reseta a mina, ganha bonus permanentes.", True, GOLD), (x,y)); y += 18
        self.screen.blit(self.f_small.render(f"Prestigios: {game.prestigios}  |  Almas: {game.almas_eternas}  |  Bonus: {game.bonus_prestigio:.1f}x", True, GRAY), (x,y)); y += 14
        self.screen.blit(self.f_small.render(f"Requisito: {req:,}g ouro total  (atual: {tot:,.0f}g)", True, GREEN if pode else GRAY), (x,y)); y += 14

        prog = min(1.0, tot/req)
        bw3  = 380
        pygame.draw.rect(self.screen, DARK_GRAY, (x, y, bw3, 10), border_radius=4)
        pygame.draw.rect(self.screen, GOLD if pode else LIGHT_BROWN, (x, y, int(bw3*prog), 10), border_radius=4)
        y += 14

        if pode:
            self.screen.blit(self.f_small.render(f"Recebe: +{1+game.prestigios} Almas  | +10% bonus global permanente", True, GOLD), (x,y))

        bp2 = Btn(SCREEN_WIDTH-165, cy+4, 155, 50, "FAZER PRESTIGIO",
                  cor=(80,25,110) if pode else (40,40,40), disabled=not pode)
        bp2.update(mp); bp2.draw(self.screen, self.f_normal)
        self.dyn_btns.append((bp2, ("prestigio", None)))

    # ABA 5: CONQUISTAS
    def _tab_conquistas(self, mp, cy):
        OX   = self.OX
        cols = 3; cw3 = (SCREEN_WIDTH - OX - 16) // cols
        for i, ach in enumerate(ACHIEVEMENTS):
            cx3 = OX + 8 + (i%cols)*cw3
            cy3 = cy + (i//cols)*36
            if cy3 > cy + BOTTOM_H - 10: break
            desbloq = ach["id"] in self.game.conquistas
            bg2  = (32,25,10) if desbloq else (18,14,8)
            cor3 = GOLD if desbloq else PANEL_BDR
            pygame.draw.rect(self.screen, bg2,  (cx3, cy3, cw3-4, 32), border_radius=3)
            pygame.draw.rect(self.screen, cor3,  (cx3, cy3, cw3-4, 32), 1, border_radius=3)
            self.screen.blit(self.f_small.render(ach["nome"], True, GOLD if desbloq else GRAY), (cx3+4, cy3+4))
            self.screen.blit(self.f_small.render(ach["desc"][:42], True, (110,110,110) if desbloq else DARK_GRAY), (cx3+4, cy3+18))

    # ------------------------------------------------------------------
    # LOG STRIP — última mensagem no rodapé
    # ------------------------------------------------------------------

    def _draw_log(self):
        pygame.draw.rect(self.screen, (10, 6, 3), self.r_log)
        if self.game.log:
            entry = self.game.log[0]
            ts = self.f_small.render(entry["msg"][:180], True, entry["cor"])
            self.screen.blit(ts, (self.OX + 8, self.r_log.y + 14))

    # ------------------------------------------------------------------
    # TOOLTIP DO ESCRAVO
    # ------------------------------------------------------------------

    def _draw_tooltip(self, mp):
        e = self.tooltip_slave
        if not e: return

        attrs = [
            (f"Forca:       {e.forca:3d}",       e.raridade_attr(e.forca)),
            (f"Velocidade:  {e.velocidade:3d}",   e.raridade_attr(e.velocidade)),
            (f"Resistencia: {e.resistencia:3d}",  e.raridade_attr(e.resistencia)),
            (f"Fertilidade: {e.fertilidade:3d}",  e.raridade_attr(e.fertilidade)),
            (f"Sorte:       {e.sorte:3d}",         e.raridade_attr(e.sorte)),
            (f"Lealdade:    {e.lealdade:3d}",      e.raridade_attr(e.lealdade)),
        ]

        lines = [
            (e.nome, WHITE),
            (f"{'Homem' if e.genero=='M' else 'Mulher'} | Idade {e.idade} | {e.raridade_geral()}", e.cor_raridade()),
            ("", None),
        ] + [(f"{txt}  [{rar}]", RARITY_COLORS.get(rar, GRAY)) for txt, rar in attrs] + [
            ("", None),
            (f"Vida: {e.vida:.0f}/{e.vida_max}", GREEN),
            (f"Tempo na mina: {e.tempo_na_mina/60:.1f} min", GRAY),
            (f"Valor total encontrado: {e.valor_total}g", GOLD),
            (f"Preco de venda: {e.calcular_preco()}g", YELLOW),
        ]

        TW = 238; LH = 13
        TH = len(lines)*LH + 12
        tx = min(mp[0]+14, SCREEN_WIDTH-TW-4)
        ty = max(4, mp[1]-TH//2)
        ty = min(ty, SCREEN_HEIGHT-TH-4)

        s = pygame.Surface((TW, TH), pygame.SRCALPHA)
        s.fill((8,5,2,220))
        pygame.draw.rect(s, PANEL_BDR, (0,0,TW,TH), 1, border_radius=4)
        self.screen.blit(s, (tx, ty))

        for i, (txt, cor) in enumerate(lines):
            if txt:
                self.screen.blit(self.f_small.render(txt, True, cor or WHITE), (tx+5, ty+5+i*LH))

    # ------------------------------------------------------------------
    # NOTIFICAÇÃO DE EVENTO
    # ------------------------------------------------------------------

    def _draw_notif(self):
        n  = self.game.notificacao
        W  = 420; H = 145
        px = (SCREEN_WIDTH-W)//2; py = (SCREEN_HEIGHT-H)//2
        s  = pygame.Surface((W,H), pygame.SRCALPHA)
        s.fill((12,8,4,230))
        self.screen.blit(s, (px,py))
        pygame.draw.rect(self.screen, n["cor"], (px,py,W,H), 2, border_radius=8)
        t1 = self.f_big.render(n["titulo"], True, n["cor"])
        self.screen.blit(t1, (px+(W-t1.get_width())//2, py+18))
        t2 = self.f_normal.render(n["msg"], True, WHITE)
        self.screen.blit(t2, (px+(W-t2.get_width())//2, py+58))
        t3 = self.f_small.render("(Clique para fechar)", True, GRAY)
        self.screen.blit(t3, (px+(W-t3.get_width())//2, py+100))

    # ------------------------------------------------------------------
    # TUTORIAL
    # ------------------------------------------------------------------

    def _draw_tutorial(self):
        W = 640; H = 430
        px = (SCREEN_WIDTH-W)//2; py = (SCREEN_HEIGHT-H)//2
        s  = pygame.Surface((W,H), pygame.SRCALPHA)
        s.fill((8,5,2,245))
        self.screen.blit(s, (px,py))
        pygame.draw.rect(self.screen, GOLD, (px,py,W,H), 2, border_radius=10)

        content = [
            ("MINA DOS ESCRAVOS ETERNOS", self.f_big, GOLD),
            ("", self.f_small, WHITE),
            ("COMO JOGAR:", self.f_title, LIGHT_BROWN),
            ("1. Compre escravos na aba 'Loja' (painel inferior)", self.f_normal, WHITE),
            ("2. Eles minerarao automaticamente a cada poucos segundos", self.f_normal, WHITE),
            ("3. Venda recursos no painel direito ou aba 'Mercado'", self.f_normal, WHITE),
            ("4. Upgrades -> mineracao mais eficiente e recursos raros", self.f_normal, WHITE),
            ("5. Use 'Par' na lista de escravos para reproducao", self.f_normal, WHITE),
            ("6. Aprofunde a mina para recursos raros (mais risco!)", self.f_normal, WHITE),
            ("7. Acumule riqueza e faca Prestigio para bonus permanentes", self.f_normal, WHITE),
            ("", self.f_small, WHITE),
            ("ATRIBUTOS:", self.f_title, LIGHT_BROWN),
            ("Forca -> + recursos  |  Resist. -> vive mais  |  Sorte -> raros", self.f_small, GRAY),
            ("Fertilidade -> + filhos  |  Lealdade -> - rebeliao", self.f_small, GRAY),
            ("", self.f_small, WHITE),
            (">> Clique em qualquer lugar para comecar! <<", self.f_normal, YELLOW),
        ]

        ty = py + 14
        for txt, font, cor in content:
            ts = font.render(txt, True, cor)
            self.screen.blit(ts, (px+(W-ts.get_width())//2, ty))
            ty += font.get_height() + 5

    # ------------------------------------------------------------------
    # TRATAMENTO DE EVENTOS
    # ------------------------------------------------------------------

    def handle_event(self, ev):
        mp   = pygame.mouse.get_pos()
        game = self.game

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if game.notificacao:
                game.notificacao = None
                return
            if self.show_tutorial:
                self.show_tutorial = False
                game.primeiro_jogo = False
                return

        # Scroll — lista de escravos
        if ev.type == pygame.MOUSEWHEEL and self.r_center.collidepoint(mp):
            todos = game.escravos_vivos + game.bebes
            max_s = max(0, len(todos)*55 - (MAIN_H-40))
            self.slave_scroll = max(0, min(max_s, self.slave_scroll - ev.y*30))

        # Scroll — sidebar de log
        if ev.type == pygame.MOUSEWHEEL and self.r_sidebar.collidepoint(mp):
            total    = len(game.log)
            LINE_H   = 14
            max_vis  = (SCREEN_HEIGHT - 23) // LINE_H
            max_scroll = max(0, total - max_vis)
            self.log_scroll = max(0, min(max_scroll, self.log_scroll - ev.y * 3))

        # Botões topbar
        if self.btn_pause.clicked(ev):  game.pausado = not game.pausado
        if self.btn_1x.clicked(ev):     game.velocidade = 1
        if self.btn_2x.clicked(ev):     game.velocidade = 2
        if self.btn_4x.clicked(ev):     game.velocidade = 4
        if self.btn_save.clicked(ev):
            game.save(); game.log_add("Jogo salvo!", GREEN)
        if self.btn_aceler.clicked(ev):
            game.acelerar_mineracao()

        for i, btn in enumerate(self.tab_btns):
            if btn.clicked(ev):
                self.tab = i

        for btn, (acao, param) in self.dyn_btns:
            if btn.clicked(ev):
                self._exec(acao, param)
                break

    def _exec(self, acao: str, param):
        game = self.game

        if acao == "vender":
            e = game.get_escravo(param)
            if e: game.vender_escravo(e)

        elif acao == "par":
            e = game.get_escravo(param)
            if not e: return
            if e.par_id:
                hid = param if e.genero=="M" else e.par_id
                game.remover_par(hid)
                self.selected_id = None
            elif self.selected_id and self.selected_id != param:
                sel    = game.get_escravo(self.selected_id)
                target = e
                if sel and target:
                    if sel.genero=="M" and target.genero=="F":
                        game.adicionar_par(sel.id, target.id)
                    elif sel.genero=="F" and target.genero=="M":
                        game.adicionar_par(target.id, sel.id)
                    else:
                        game.log_add("Selecione um M e uma F.", RED)
                self.selected_id = None
            else:
                self.selected_id = param
                game.log_add(f"Selecionado: {e.nome}. Clique 'Par' em outro.", CYAN)

        elif acao == "comprar_loja":
            idx = param
            if 0 <= idx < len(game.loja):
                game.comprar_escravo(game.loja[idx])

        elif acao == "upgrade":
            game.comprar_upgrade(param)

        elif acao == "aprofundar":
            ok, msg = game.aprofundar_mina()
            if not ok: game.log_add(msg, RED)

        elif acao == "vender_tudo":
            game.vender_tudo()

        elif acao == "vender_recurso":
            t = game.vender_recurso(param)
            game.log_add(f"Vendeu {param} por {t}g.", YELLOW)

        elif acao == "refresca":
            ok, msg = game.refresca_loja()
            if not ok: game.log_add(msg, RED)

        elif acao == "remover_par":
            game.remover_par(param)

        elif acao == "prestigio":
            ok, msg = game.fazer_prestigio()
            game.log_add(msg, GOLD if ok else RED)

    def notify_mining(self, escravo_id: int, cor):
        """Chamado pelo game loop quando um escravo acabou de minerar."""
        self._flash[escravo_id] = 0.28
        game = self.game
        e    = game.get_escravo(escravo_id)
        if e and hasattr(e, "anim_x"):
            self.spawn_particles(e.anim_x, e.anim_y, cor)

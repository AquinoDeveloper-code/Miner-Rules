# ============================================================
# renderer.py — Renderização completa e tratamento de UI
# ============================================================

import math
import random
import pygame

from src.contexts.shared.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TOP_H, MAIN_H, BOTTOM_H, LOG_H, TITLE,
    LOG_SIDEBAR_W, LEFT_W, CENTER_W, RIGHT_W,
    BLACK, DARK_BG, PANEL_BG, PANEL_BDR, CAVE_BG,
    DARK_BROWN, MED_BROWN, LIGHT_BROWN,
    WHITE, GRAY, DARK_GRAY,
    RED, DARK_RED, GREEN, DARK_GREEN, BLUE, YELLOW, ORANGE, PURPLE, CYAN, GOLD, PINK,
    RARITY_COLORS, RESOURCES, RESOURCE_ORDER, MINE_UPGRADES, UPGRADE_ORDER,
    MINE_DEPTHS, ACHIEVEMENTS,
    SLOTS, SLOT_NOMES, ITEMS, RETIREMENT_AGE,
)

BASE_SCREEN_WIDTH = SCREEN_WIDTH
BASE_SCREEN_HEIGHT = SCREEN_HEIGHT
BASE_TOP_H = TOP_H
BASE_BOTTOM_H = BOTTOM_H
BASE_LOG_H = LOG_H
BASE_MAIN_H = MAIN_H
BASE_LOG_SIDEBAR_W = LOG_SIDEBAR_W
BASE_LEFT_W = LEFT_W
BASE_CENTER_W = CENTER_W
BASE_RIGHT_W = RIGHT_W


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

    TABS = ["Loja", "Upgrades", "Breeding", "Mercado", "Prestígio", "Conquistas", "Histórico", "Inventário"]
    OX   = LOG_SIDEBAR_W  # offset x de todos os painéis principais

    def __init__(self, screen, game):
        self.screen = screen
        self.game   = game
        self.view_scale = 1.0
        self.view_offset = (0, 0)

        pygame.font.init()

        # Estado UI
        self.tab          = 0
        self.slave_scroll = 0
        self.shop_scroll  = 0
        self.shop_scroll_max = 0
        self.log_scroll   = 0
        self.tooltip_slave = None
        self.selected_id  = None
        self.show_tutorial = True
        self.confirm_reset = False
        self.request_quit = False

        # Tela de detalhe de escravo
        self.slave_detalhe_id  = None   # ID do escravo sendo exibido no modal
        self.detalhe_slot_sel  = None   # slot selecionado no modal de detalhe
        self.inv_selecionados  = set()  # IDs únicos de itens do inventário a serem deletados

        self.btn_reset_confirm = None
        self.btn_reset_cancel  = None

        self.dyn_btns: list[tuple[Btn, tuple]] = []

        self._particles: list[list] = []
        self._flash: dict[int, float] = {}
        self.refresh_layout()

    def refresh_layout(self):
        global SCREEN_WIDTH, SCREEN_HEIGHT, TOP_H, BOTTOM_H, LOG_H, MAIN_H
        global LOG_SIDEBAR_W, LEFT_W, CENTER_W, RIGHT_W

        SCREEN_WIDTH = self.screen.get_width()
        SCREEN_HEIGHT = self.screen.get_height()

        cfg = self.game.ui_config
        base_scale = min(SCREEN_WIDTH / 1280.0, SCREEN_HEIGHT / 720.0)
        self.ui_scale = cfg.get("ui_scale", base_scale)
        ui_scale = self.ui_scale

        TOP_H = max(44, int(BASE_TOP_H * ui_scale))
        LOG_H = max(40, int(BASE_LOG_H * ui_scale))
        BOTTOM_H = max(175, int(BASE_BOTTOM_H * cfg.get("bottom_factor", 1.0) * ui_scale))
        max_bottom = SCREEN_HEIGHT - TOP_H - LOG_H - 240
        BOTTOM_H = min(BOTTOM_H, max(170, max_bottom))
        MAIN_H = SCREEN_HEIGHT - TOP_H - BOTTOM_H - LOG_H

        mins = [180, 340, 430, 240]
        weights = [
            BASE_LOG_SIDEBAR_W * cfg.get("sidebar_factor", 1.0),
            BASE_LEFT_W * cfg.get("mine_factor", 1.0),
            BASE_CENTER_W * cfg.get("center_factor", 1.0),
            BASE_RIGHT_W * cfg.get("right_factor", 1.0),
        ]
        extra_total = max(0, SCREEN_WIDTH - sum(mins))
        weight_sum = max(1.0, sum(weights))
        raw_widths = [mins[i] + extra_total * (weights[i] / weight_sum) for i in range(4)]
        widths = [int(v) for v in raw_widths]
        widths[-1] += SCREEN_WIDTH - sum(widths)
        LOG_SIDEBAR_W, LEFT_W, CENTER_W, RIGHT_W = widths
        self.OX = LOG_SIDEBAR_W

        self.f_big    = pygame.font.SysFont("monospace", max(20, int(20 * ui_scale)), bold=True)
        self.f_title  = pygame.font.SysFont("monospace", max(15, int(15 * ui_scale)), bold=True)
        self.f_normal = pygame.font.SysFont("monospace", max(13, int(13 * ui_scale)))
        self.f_small  = pygame.font.SysFont("monospace", max(11, int(11 * ui_scale)))

        OX = self.OX
        self.r_sidebar = pygame.Rect(0, 0, LOG_SIDEBAR_W, SCREEN_HEIGHT)
        self.r_top     = pygame.Rect(OX, 0, SCREEN_WIDTH - OX, TOP_H)
        self.r_left    = pygame.Rect(OX, TOP_H, LEFT_W, MAIN_H)
        self.r_center  = pygame.Rect(OX + LEFT_W, TOP_H, CENTER_W, MAIN_H)
        self.r_right   = pygame.Rect(OX + LEFT_W + CENTER_W, TOP_H, RIGHT_W, MAIN_H)
        self.r_bottom  = pygame.Rect(OX, TOP_H + MAIN_H, SCREEN_WIDTH - OX, BOTTOM_H)
        self.r_log     = pygame.Rect(OX, TOP_H + MAIN_H + BOTTOM_H, SCREEN_WIDTH - OX, LOG_H)

        self._build_topbar_buttons()
        self._build_tab_buttons()
        self._cave = self._gen_cave()
        self.shop_scroll = max(0, min(self.shop_scroll, self.shop_scroll_max))

    def set_view_transform(self, scale: float, offset_x: int, offset_y: int):
        self.view_scale = max(0.001, scale)
        self.view_offset = (offset_x, offset_y)

    def _to_logical_pos(self, pos):
        return (
            int((pos[0] - self.view_offset[0]) / self.view_scale),
            int((pos[1] - self.view_offset[1]) / self.view_scale),
        )

    def _mouse_pos(self):
        return self._to_logical_pos(pygame.mouse.get_pos())

    def _normalize_event(self, ev):
        if hasattr(ev, "pos"):
            data = ev.dict.copy()
            data["pos"] = self._to_logical_pos(ev.pos)
            return pygame.event.Event(ev.type, data)
        return ev

    # ------------------------------------------------------------------
    # Botões estáticos
    # ------------------------------------------------------------------

    def _build_topbar_buttons(self):
        base = SCREEN_WIDTH - 10
        
        bw_exit = 84; bx_exit = base - bw_exit; base = bx_exit - 8
        bw_4x = 46; bx_4x = base - bw_4x; base = bx_4x - 8
        bw_2x = 46; bx_2x = base - bw_2x; base = bx_2x - 8
        bw_1x = 46; bx_1x = base - bw_1x; base = bx_1x - 8
        bw_pause = 72; bx_pause = base - bw_pause; base = bx_pause - 8
        bw_save = 72; bx_save = base - bw_save; base = bx_save - 8
        bw_ace = 88; bx_ace = base - bw_ace; base = bx_ace - 8
        bw_res = 72; bx_res = base - bw_res
        
        self.btn_reset  = Btn(bx_res, 5, bw_res, 30, "Reset",    cor=(110, 28, 28))
        self.btn_aceler = Btn(bx_ace, 5, bw_ace, 30, "Acelerar", cor=(80, 40, 90))
        self.btn_save   = Btn(bx_save, 5, bw_save, 30, "Salvar",   cor=(30, 55, 100))
        self.btn_pause  = Btn(bx_pause, 5, bw_pause, 30, "Pause",    cor=(70, 45, 15))
        self.btn_1x     = Btn(bx_1x, 5, bw_1x, 30, "1x",       cor=(30, 70, 30))
        self.btn_2x     = Btn(bx_2x, 5, bw_2x, 30, "2x",       cor=(70, 70, 20))
        self.btn_4x     = Btn(bx_4x, 5, bw_4x, 30, "4x",       cor=(90, 30, 30))
        self.btn_exit   = Btn(bx_exit, 5, bw_exit, 30, "Encerrar", cor=(95, 22, 22))
        self._top_btns  = [
            self.btn_reset,
            self.btn_aceler,
            self.btn_save,
            self.btn_pause,
            self.btn_1x,
            self.btn_2x,
            self.btn_4x,
            self.btn_exit,
        ]

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
        mp = self._mouse_pos()
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
        if self.tooltip_slave and not self.slave_detalhe_id:
            self._draw_tooltip(mp)
        if self.game.notificacao:
            self._draw_notif()
        if self.show_tutorial:
            self._draw_tutorial()

        # Modal de detalhe (por cima de tudo)
        if self.slave_detalhe_id:
            self._draw_slave_detail(mp)
        if self.confirm_reset:
            self._draw_reset_confirm(mp)

    # ------------------------------------------------------------------
    # BARRA LATERAL DE LOG (altura total da tela)
    # ------------------------------------------------------------------

    def _draw_log_sidebar(self):
        OX  = self.OX
        log = list(reversed(self.game.log))

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
        start = self.log_scroll
        
        # Clip para evitar qualquer texto fora da sidebar
        clip_rect = pygame.Rect(0, area_y, OX - 6, area_h)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(clip_rect)

        # Usando wrapping simples para que o log seja "visto por inteiro"
        render_y = area_y
        max_w = OX - 20
        
        # Como o log agora pode ter várias linhas, o scroll precisa ser baseado em entradas,
        # mas a renderização precisa ser cuidadosa.
        # Para simplificar e manter a performance, vamos apenas desenhar o que cabe
        # baseado no start index.
        
        for entry in log[start:]:
            msg = entry["msg"]
            words = msg.split(' ')
            line = ""
            lines_to_draw = []
            
            for word in words:
                test_line = line + word + " "
                if self.f_small.size(test_line)[0] < max_w:
                    line = test_line
                else:
                    lines_to_draw.append(line)
                    line = word + " "
            lines_to_draw.append(line)
            
            for l_txt in lines_to_draw:
                if render_y + LINE_H > SCREEN_HEIGHT: break
                pygame.draw.rect(self.screen, entry["cor"], (0, render_y, 3, LINE_H))
                self.screen.blit(self.f_small.render(l_txt.strip(), True, entry["cor"]), (10, render_y))
                render_y += LINE_H
            
            if render_y > SCREEN_HEIGHT: break

        self.screen.set_clip(old_clip)

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

        # Title and Time
        title_surf = self.f_title.render(f"{TITLE.upper()} | Ano {self.game.ano_atual}, Mês {self.game.mes_atual}", True, LIGHT_BROWN)
        self.screen.blit(title_surf, (OX+8, 12))

        # Dynamic positioning for Ouro - Anchored to the right before buttons
        # The first button (btn_reset) starts at bx_res. Let's place Gold before it.
        # We'll calculate a safe X for the right-aligned stats.
        right_base_x = self.btn_reset.rect.x - 10
        
        ouro_surf = self.f_title.render(f"Ouro: {self.game.ouro:>8,.0f}g", True, GOLD)
        ouro_x = right_base_x - ouro_surf.get_width()
        self.screen.blit(ouro_surf, (ouro_x, 12))

        vi = self.game.valor_inventario
        if vi:
            inv_surf = self.f_small.render(f"(+{vi:,.0f}inv)", True, YELLOW)
            inv_x = ouro_x - inv_surf.get_width() - 8
            self.screen.blit(inv_surf, (inv_x, 14))

        if self.game.mercado_negro:
            self.screen.blit(
                self.f_small.render(f"MERCADO NEGRO {self.game.mercado_negro_timer:.0f}s", True, CYAN),
                (OX+8, 26)
            )

        if self.game.prestigios:
            self.screen.blit(
                self.f_small.render(f"Prestigiado:{self.game.prestigios} | Almas:{self.game.almas_eternas}", True, GOLD),
                (OX+160, 26)
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
            # Aumentando o offset de 40 para 50 para evitar corte da "rarity glow" na linha do topo
            cy  = TOP_H + 50 + row * CH

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

        # Cores dinâmicas dos equipamentos
        def get_item_color(slot, default):
            item = e._item_em_slot(slot)
            return item.get("cor_visual", default) if item else default

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
        helm   = get_item_color("capacete", (108, 114, 124))
        helm_d = (max(0, helm[0]-30), max(0, helm[1]-30), max(0, helm[2]-30))
        body   = get_item_color("camiseta", (88,  56,  20))
        body_d = (max(0, body[0]-23), max(0, body[1]-16), max(0, body[2]-12))
        pants  = get_item_color("calcas", (46,  42,  70))
        pants_d = (max(0, pants[0]-14), max(0, pants[1]-14), max(0, pants[2]-14))
        boot   = get_item_color("botas", (40,  24,  8))
        lamp_c = (255, 215, 70)
        
        pic_cor = get_item_color("picareta", (185, 185, 200))
        pic_item = e._item_em_slot("picareta")
        is_pic_top = pic_item and pic_item["raridade"] in ("épico", "lendário")

        swing = math.sin(t_real * 5.5 + e.anim_frame * 0.6) * 30
        vp    = e.stamina / 100.0  # stamina como "barra de vida" no pixel art
        vc    = GREEN if vp > 0.5 else (YELLOW if vp > 0.25 else RED)

        # --- GLOW DE RARIDADE OU CONSUMÍVEL ---
        alpha_glow = 90 + int(45 * math.sin(t_real * 3 + e.anim_frame))
        if flash_t > 0:
            alpha_glow = 230
        
        # Glow especial (doença ou consumível com aura)
        if hasattr(e, "efeito_aura") and e.efeito_aura and hasattr(e, "aura_timer") and e.aura_timer > 0:
            alpha_glow = 180 + int(60 * math.sin(t_real * 6))
            cor_raro = getattr(e, "cor_aura", GREEN)
            # Emit particles
            if random.random() < 0.2:
                self._particles.append([cx + random.randint(-15, 15), cy + yo + random.randint(-20, 20), 0, -0.5, 30, cor_raro])
        elif e.doente:
            alpha_glow = 180 + int(60 * math.sin(t_real * 4))
            cor_raro   = PURPLE

        gs = pygame.Surface((34, 52), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*cor_raro, alpha_glow), (0, 0, 34, 52), 2, border_radius=3)
        self.screen.blit(gs, (cx-17, cy-40+yo))

        # --- BARRA DE STAMINA ---
        bw = 26; bh = 3
        bx = cx - bw // 2
        pygame.draw.rect(self.screen, DARK_RED, (bx, cy-48+yo, bw, bh))
        pygame.draw.rect(self.screen, vc,       (bx, cy-48+yo, int(bw*vp), bh))

        # --- CABELO FEMININO (FUNDO) ---
        hair_c = (42, 22, 12)
        if e.genero == "F":
            # Cabelo mais volumoso e flutuante
            pygame.draw.rect(self.screen, hair_c, (cx-9, cy-34+yo, 18, 18)) # base volume
            pygame.draw.rect(self.screen, hair_c, (cx-7, cy-16+yo, 14, 12)) # comprimento longo
            # Mechas extras pontiagudas
            pygame.draw.rect(self.screen, hair_c, (cx-10, cy-22+yo, 3, 10))
            pygame.draw.rect(self.screen, hair_c, (cx+7,  cy-22+yo, 3, 10))

        # --- CORPO / TORSO ---
        pygame.draw.rect(self.screen, body,   (cx-7, cy-18+yo, 14, 14))
        pygame.draw.rect(self.screen, body_d, (cx-7, cy-18+yo, 2,  14))   # sombra lateral
        pygame.draw.rect(self.screen, body_d, (cx-7, cy-5+yo,  14, 1))    # cinto
        # Bolso
        pygame.draw.rect(self.screen, body_d, (cx-6, cy-16+yo, 5, 5))
        pygame.draw.rect(self.screen, (max(0,body[0]-40),max(0,body[1]-30),max(0,body[2]-20)), (cx-5, cy-15+yo, 3, 3))
        # Suspensórios
        pygame.draw.rect(self.screen, body_d, (cx-4, cy-18+yo, 2, 10))
        pygame.draw.rect(self.screen, body_d, (cx+2, cy-18+yo, 2, 10))

        # --- PERNAS ---
        pygame.draw.rect(self.screen, pants,   (cx-7, cy-4+yo,  6, 11))
        pygame.draw.rect(self.screen, pants,   (cx+1, cy-4+yo,  6, 11))
        pygame.draw.rect(self.screen, pants_d, (cx-7, cy-4+yo,  1, 11))   # sombra esq
        pygame.draw.rect(self.screen, pants_d, (cx+6, cy-4+yo,  1, 11))   # sombra dir
        # Joelhos
        pygame.draw.rect(self.screen, pants_d, (cx-7, cy+2+yo, 6, 2))
        pygame.draw.rect(self.screen, pants_d, (cx+1, cy+2+yo, 6, 2))

        # --- BOTAS ---
        pygame.draw.rect(self.screen, boot,      (cx-8, cy+7+yo,  7, 5))
        pygame.draw.rect(self.screen, boot,      (cx+1, cy+7+yo,  7, 5))
        pygame.draw.rect(self.screen, (16,8,2), (cx-9, cy+11+yo, 8, 2))  # sola esq
        pygame.draw.rect(self.screen, (16,8,2), (cx,   cy+11+yo, 8, 2))  # sola dir

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

        # --- CABELO FEMININO (FRENTE) ---
        # --- CABELO FEMININO (FRENTE) ---
        if e.genero == "F":
            # Franja e mechas laterais (frente)
            pygame.draw.rect(self.screen, hair_c, (cx-7, cy-33+yo, 14, 4))   # franja
            pygame.draw.rect(self.screen, hair_c, (cx-8, cy-33+yo, 3, 16))   # mecha esq
            pygame.draw.rect(self.screen, hair_c, (cx+5, cy-33+yo, 3, 16))   # mecha dir
            # Brilho no cabelo
            pygame.draw.rect(self.screen, (70, 40, 25), (cx-5, cy-32+yo, 2, 2))
            pygame.draw.rect(self.screen, (70, 40, 25), (cx+3, cy-32+yo, 2, 2))

        # --- CAPACETE ---
        pygame.draw.rect(self.screen, helm_d, (cx-10, cy-37+yo, 20, 6))   # aba
        pygame.draw.rect(self.screen, helm,   (cx-8,  cy-43+yo, 16, 7))   # cúpula
        pygame.draw.rect(self.screen, helm_d, (cx-8,  cy-43+yo, 16, 2))   # sombra topo
        pygame.draw.rect(self.screen, lamp_c, (cx-3,  cy-38+yo, 6,  3))   # lâmpada
        pygame.draw.rect(self.screen, (255,255,200), (cx-1, cy-37+yo, 2, 1))  # brilho lâmpada

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
            pygame.draw.rect(self.screen, pic_cor, (head_x, head_y, 6, 6))
            pygame.draw.rect(self.screen, (min(255,pic_cor[0]+25), min(255,pic_cor[1]+25), min(255,pic_cor[2]+25)), (head_x, head_y, 6, 2))  # highlight
            pygame.draw.rect(self.screen, (max(0,pic_cor[0]-25), max(0,pic_cor[1]-25), max(0,pic_cor[2]-25)), (head_x, head_y+4, 6, 2))  # sombra
            if is_pic_top:
                pygame.draw.rect(self.screen, (255, 255, 255), (head_x+2, head_y-2, 2, 8)) # Lâmina central estendida
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

        self.screen.blit(self.f_title.render("SERVOS", True, LIGHT_BROWN), (cx0+8, TOP_H+6))
        n = len(game.escravos_vivos); b = len(game.bebes)
        self.screen.blit(
            self.f_small.render(
                f"{n} ativos | {b} bebe(s) | Cap {game.servos_na_mina}/{game.capacidade_servos} | Clique p/ detalhe",
                True,
                GRAY,
            ),
            (cx0+8, TOP_H+22),
        )

        # Botão de Auto-Equip Geral (Destaque no Header)
        btn_ae = Btn(cx0 + CENTER_W - 160, TOP_H + 8, 150, 24, "⚡ AUTO-EQUIP GERAL", cor=(30, 80, 110))
        btn_ae.update(mp); btn_ae.draw(self.screen, self.f_small)
        self.dyn_btns.append((btn_ae, ("auto_equipar_todos", None)))

        clip_top = TOP_H + 40
        clip_h   = MAIN_H - 40
        self.screen.set_clip(pygame.Rect(cx0, clip_top, CENTER_W, clip_h))

        LINHA_H = max(78, int(84 * self.ui_scale))
        todos   = game.escravos_vivos + game.bebes

        for i, e in enumerate(todos):
            y0 = clip_top + i * LINHA_H - self.slave_scroll
            if y0 + LINHA_H < clip_top or y0 > clip_top + clip_h:
                continue

            bg = (30, 20, 10) if i % 2 == 0 else (24, 16, 8)
            rect_row = pygame.Rect(cx0, y0, CENTER_W, LINHA_H-2)
            pygame.draw.rect(self.screen, bg, rect_row)
            
            # Borda colorida baseada na raridade (Épico, Lendário etc)
            cor_r = e.cor_raridade()
            # Se for lendário ou épico, desenha uma borda mais grossa pra dar destaque
            raridade = e.raridade_geral()
            b_width = 2 if raridade in ("épico", "lendário") else 1
            pygame.draw.rect(self.screen, cor_r, rect_row, b_width, border_radius=2)

            if self.selected_id == e.id:
                pygame.draw.rect(self.screen, CYAN, (cx0, y0, CENTER_W-2, LINHA_H-2), 1)

            gc = BLUE if e.genero == "M" else PINK
            gs = "M" if e.genero == "M" else "F"
            self.screen.blit(self.f_small.render(gs, True, gc), (cx0+5, y0+6))

            nome = e.nome[:17] + (" bebe" if e.eh_bebe else "")
            self.screen.blit(self.f_normal.render(nome, True, WHITE), (cx0+18, y0+4))

            # Ícones de status (doente, maldição)
            status_x = cx0 + 200
            if not e.eh_bebe:
                if e.doente:
                    self.screen.blit(self.f_small.render("D", True, RED), (status_x, y0+4))
                    status_x += 12
                if e.tem_maldicao_ativa():
                    self.screen.blit(self.f_small.render("M", True, PURPLE), (status_x, y0+4))

            # Idade com cor
            if not e.eh_bebe:
                idade_i = int(e.idade)
                if   e.idade < 35:  cor_idade = GREEN
                elif e.idade < 50:  cor_idade = YELLOW
                elif e.idade < 60:  cor_idade = ORANGE
                else:               cor_idade = RED
                self.screen.blit(self.f_small.render(f"{idade_i}a", True, cor_idade), (cx0+235, y0+4))

            # Barra de stamina
            bw = 110; bh = 5
            bx = cx0+18; by_stam = y0+20
            stam_p = e.stamina / 100.0 if not e.eh_bebe else 1.0
            stam_c = GREEN if stam_p > 0.5 else (YELLOW if stam_p > 0.25 else RED)
            pygame.draw.rect(self.screen, DARK_GRAY, (bx, by_stam, bw, bh), border_radius=2)
            pygame.draw.rect(self.screen, stam_c, (bx, by_stam, int(bw * stam_p), bh), border_radius=2)
            self.screen.blit(self.f_small.render("STM", True, DARK_GRAY), (bx + bw + 3, by_stam - 1))

            # Atributos
            attrs = [("F",e.forca),("V",e.velocidade),("R",e.resistencia),
                     ("Fe",e.fertilidade),("S",e.sorte),("L",e.lealdade)]
            atx = cx0+18; my0 = y0+34
            for j, (lbl, val) in enumerate(attrs):
                ax = atx + j * 37
                rc = RARITY_COLORS.get(e.raridade_attr(val), GRAY)
                self.screen.blit(self.f_small.render(f"{lbl}:{val}", True, rc), (ax, my0))

            # Info crescimento / par
            info_x = atx + 6*37 + 2
            if e.eh_bebe:
                growth_time = max(1.0, self.game.rules["growth_time"])
                pct = 1 - e.tempo_crescimento / growth_time
                ss  = self.f_small.render(f"Cres.{pct*100:.0f}%", True, CYAN)
                self.screen.blit(ss, (info_x, my0))
            elif e.par_id:
                self.screen.blit(self.f_small.render("Par", True, PINK), (info_x, my0))

            # Status de humor na lista de servos
            if not e.eh_bebe:
                humor = e.status_humor()
                COR_HUMOR_MINI = {
                    "Muito Feliz":   (140, 230, 100),
                    "Satisfeito":    (100, 200, 80),
                    "Normal":        GRAY,
                    "Cansado":       ORANGE,
                    "Muito Cansado": (200, 80, 30),
                    "Doente":        RED,
                    "Faminto":       (230, 130, 0),
                    "Amaldi\u00e7oado":  PURPLE,
                }
                cor_h = COR_HUMOR_MINI.get(humor, GRAY)
                self.screen.blit(self.f_small.render(f"[{humor}]", True, cor_h), (cx0+18, y0+50))
            
                if e.par_honeymoon > 0:
                    self.screen.blit(self.f_small.render("\u2665 Lua de mel", True, PINK), (cx0+140, y0+50))
                elif e.par_id:
                    self.screen.blit(self.f_small.render("\u2665 Par", True, PINK), (cx0+140, y0+50))

            # Botões de ação (agora inclui "Det." para abrir detalhe)
            bx2 = cx0 + CENTER_W - 146
            if not e.eh_bebe:
                if e.em_repouso:
                    b_volt = Btn(bx2, y0+58, 142, 20, "Voltar à Mina", cor=(30, 80, 40) if e.stamina > 10 else (40, 40, 40), disabled=e.stamina <= 10)
                    b_volt.update(mp); b_volt.draw(self.screen, self.f_small)
                    self.dyn_btns.append((b_volt, ("voltar_mina", e.id)))
                else:
                    bdet = Btn(bx2,      y0+58, 44, 20, "Det.",  cor=(30, 55, 90))
                    bv   = Btn(bx2+48,   y0+58, 50, 20, "Vend.", cor=(100,50,20), cor_txt=YELLOW)
                    bp   = Btn(bx2+102,  y0+58, 40, 20, "Par",   cor=(20,60,80))
                    bdet.update(mp); bdet.draw(self.screen, self.f_small)
                    bv.update(mp);   bv.draw(self.screen, self.f_small)
                    bp.update(mp);   bp.draw(self.screen, self.f_small)
                    self.dyn_btns.append((bdet, ("detalhe", e.id)))
                    self.dyn_btns.append((bv,   ("vender",  e.id)))
                    self.dyn_btns.append((bp,   ("par",     e.id)))
            else:
                bvb = Btn(cx0 + CENTER_W - 54, y0+58, 50, 20, "Vend.", cor=(100,50,20), cor_txt=YELLOW)
                bvb.update(mp); bvb.draw(self.screen, self.f_small)
                self.dyn_btns.append((bvb, ("vender", e.id)))

            if pygame.Rect(cx0, y0, CENTER_W-150, LINHA_H).collidepoint(mp):
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

        # Itens no inventário (resumo)
        n_itens = len(game.inventario_itens)
        if n_itens > 0:
            pygame.draw.line(self.screen, PANEL_BDR, (rx+4, y), (rx+RIGHT_W-4, y), 1); y += 4
            self.screen.blit(self.f_small.render(f"Itens: {n_itens}", True, CYAN), (rx+6, y)); y += 14

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
        stat(f"Capacidade:{game.servos_na_mina}/{game.capacidade_servos}"); y += 14
        stat(f"Intervalo: {game.intervalo_efetivo:.1f}s");   y += 14
        stat(f"Raridade:  {game.mult_raridade:.2f}x");       y += 14
        stat(f"Recursos:  {game.mult_recursos:.2f}x");       y += 14
        stat(f"Risco base:{game.risco_morte*100:.1f}%");     y += 14
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
        elif self.tab == 6: self._tab_historico(mp, cy)
        elif self.tab == 7: self._tab_inventario(mp, cy)

    # ABA 0: LOJA
    def _tab_loja(self, mp, cy):
        OX    = self.OX
        game  = self.game
        CH    = BOTTOM_H - 34
        lh    = self.f_small.get_height()
        # Sincroniza com ITEM_PANEL_W (220) para evitar que cards de servos fiquem por baixo da loja de itens
        right_panel_w = 224
        usable_w = max(220, SCREEN_WIDTH - OX - right_panel_w - 12)
        card_w = max(int(206 * self.ui_scale), min(int(250 * self.ui_scale), usable_w // 3 - 8))
        card_h = max(96, int(96 * self.ui_scale))
        gap = 6
        cols = max(1, usable_w // (card_w + gap))
        row_h = card_h + gap
        total_rows = max(1, math.ceil(len(game.loja) / cols))
        content_h = total_rows * row_h - gap
        self.shop_scroll_max = max(0, content_h - CH)
        self.shop_scroll = max(0, min(self.shop_scroll, self.shop_scroll_max))

        viewport = pygame.Rect(OX + 6, cy, usable_w, CH)
        clip_prev = self.screen.get_clip()
        self.screen.set_clip(viewport)

        for i, oferta in enumerate(game.loja):
            e = oferta["servo"]
            row = i // cols
            col = i % cols
            cx = viewport.x + col * (card_w + gap)
            card_y = cy + row * row_h - self.shop_scroll
            if card_y + card_h < viewport.y or card_y > viewport.bottom:
                continue

            cor_r = e.cor_raridade()
            pygame.draw.rect(self.screen, (26, 17, 9), (cx, card_y, card_w, card_h), border_radius=5)
            # Borda mais grossa para raridades altas
            raridade = e.raridade_geral()
            b_width = 2 if raridade in ("épico", "lendário") else 1
            pygame.draw.rect(self.screen, cor_r, (cx, card_y, card_w, card_h), b_width, border_radius=5)

            gy = card_y + 4
            gc = BLUE if e.genero == "M" else PINK
            gs = "M" if e.genero == "M" else "F"
            self.screen.blit(self.f_small.render(gs, True, gc), (cx + 4, gy))
            self.screen.blit(self.f_small.render(e.nome[:16], True, WHITE), (cx + 18, gy))
            restante = max(0, int(game.tempo_restante_oferta(oferta["id"])))
            mins, secs = divmod(restante, 60)
            self.screen.blit(
                self.f_small.render(f"{mins:02d}:{secs:02d}", True, GOLD),
                (cx + card_w - 46, gy),
            )
            gy += lh + 2
            self.screen.blit(self.f_small.render(e.raridade_geral(), True, cor_r), (cx + 4, gy))
            gy += lh

            attrs = [("For", e.forca), ("Vel", e.velocidade), ("Res", e.resistencia),
                     ("Fer", e.fertilidade), ("Sor", e.sorte), ("Lea", e.lealdade)]
            for j, (lbl, val) in enumerate(attrs):
                ax = cx + 4 + (j % 2) * max(70, int(95 * self.ui_scale))
                ay = gy + (j // 2) * lh
                rc = RARITY_COLORS.get(e.raridade_attr(val), GRAY)
                self.screen.blit(self.f_small.render(f"{lbl}:{val}", True, rc), (ax, ay))

            preco = e.calcular_preco(bonus_nivel_mina=game.nivel_mina)
            pode = game.ouro >= preco and game.pode_adicionar_servo()
            price_y = card_y + card_h - int(24 * self.ui_scale)
            self.screen.blit(self.f_small.render(f"{preco}g", True, GOLD), (cx + 4, price_y + 2))
            btn_w = max(70, int(70 * self.ui_scale))
            bb = Btn(
                cx + card_w - btn_w - 4,
                price_y,
                btn_w,
                int(22 * self.ui_scale),
                "Comprar",
                cor=(45, 75, 28) if pode else (40, 40, 40),
                disabled=not pode,
            )
            bb.update(mp)
            bb.draw(self.screen, self.f_small)
            self.dyn_btns.append((bb, ("comprar_loja", oferta["id"])))

        self.screen.set_clip(clip_prev)

        if self.shop_scroll_max > 0:
            bar_x = viewport.right - 6
            pygame.draw.rect(self.screen, DARK_GRAY, (bar_x, viewport.y, 4, CH), border_radius=2)
            handle_h = max(16, int(CH * (CH / max(CH, content_h))))
            handle_y = viewport.y + int((CH - handle_h) * (self.shop_scroll / max(1, self.shop_scroll_max)))
            pygame.draw.rect(self.screen, LIGHT_BROWN, (bar_x, handle_y, 4, handle_h), border_radius=2)

        br = Btn(OX + 8, cy + CH - 30, 180, 24, f"Refrescar Loja ({game.custo_refresco}g)", cor=(60,50,18))
        br.update(mp); br.draw(self.screen, self.f_small)
        self.dyn_btns.append((br, ("refresca", None)))
        if not game.pode_adicionar_servo():
            self.screen.blit(self.f_small.render("Capacidade máxima da mina atingida.", True, ORANGE), (OX + 200, cy + CH - 26))

        # ============================================================
        # Loja de Itens Especial — painel fixo no canto direito
        # ============================================================
        ITEM_PANEL_W = 220
        item_x = SCREEN_WIDTH - ITEM_PANEL_W - 4
        item_y = cy
        
        # Fundo do painel
        pygame.draw.rect(self.screen, (18, 10, 25), (item_x, item_y, ITEM_PANEL_W, CH), border_radius=6)
        pygame.draw.rect(self.screen, PURPLE, (item_x, item_y, ITEM_PANEL_W, CH), 1, border_radius=6)
        
        self.screen.blit(self.f_normal.render("Mercador de Itens", True, PURPLE), (item_x + 6, item_y + 4))
        mins, secs = divmod(max(0, 300 - game.loja_itens_timer), 60)
        self.screen.blit(self.f_small.render(f"Reseta em {int(mins):02d}:{int(secs):02d}", True, GRAY), (item_x + 6, item_y + 20))
        pygame.draw.line(self.screen, PURPLE, (item_x + 4, item_y + 36), (item_x + ITEM_PANEL_W - 4, item_y + 36), 1)
        
        y_it = item_y + 42
        
        # Clip para conter dentro do painel
        old_clip2 = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(item_x, item_y + 38, ITEM_PANEL_W, CH - 42))
        
        if not game.loja_itens:
            self.screen.blit(self.f_small.render("Em estoque em 5min...", True, DARK_GRAY), (item_x + 8, y_it))
        else:
            for shop_item in game.loja_itens:
                iid = shop_item["id"]
                preco = shop_item["preco"]
                item_data = ITEMS.get(iid)
                if not item_data: continue
                
                pode_comprar = game.ouro >= preco
                cor_nome = RARITY_COLORS.get(item_data.get("raridade"), WHITE)
                pygame.draw.rect(self.screen, (28, 18, 35), (item_x + 4, y_it, ITEM_PANEL_W - 8, 34), border_radius=4)
                self.screen.blit(self.f_small.render(item_data["nome"][:22], True, cor_nome), (item_x + 8, y_it + 2))
                self.screen.blit(self.f_small.render(f"{preco:,}g", True, GOLD), (item_x + 8, y_it + 17))
                
                bb = Btn(item_x + ITEM_PANEL_W - 60, y_it + 7, 54, 20,
                         "Comprar", cor=(45, 75, 28) if pode_comprar else (40, 40, 40), disabled=not pode_comprar)
                bb.update(mp)
                bb.draw(self.screen, self.f_small)
                self.dyn_btns.append((bb, ("comprar_loja_item", (iid, preco))))
                y_it += 38
        
        self.screen.set_clip(old_clip2)

    def _tab_layout(self, mp, cy):
        OX = self.OX
        rows = [
            ("ui_scale", "Escala geral"),
            ("sidebar_factor", "Largura do log"),
            ("mine_factor", "Painel da mina"),
            ("center_factor", "Lista de servos"),
            ("right_factor", "Painel lateral"),
            ("bottom_factor", "Painel inferior"),
        ]
        self.screen.blit(
            self.f_normal.render("Personalize a interface em tempo real.", True, GRAY),
            (OX + 10, cy),
        )

        row_y = cy + 24
        for key, label in rows:
            valor = self.game.ui_config.get(key, 1.0)
            self.screen.blit(self.f_small.render(label, True, WHITE), (OX + 10, row_y + 5))
            self.screen.blit(self.f_small.render(f"{valor:.2f}x", True, GOLD), (OX + 210, row_y + 5))
            bminus = Btn(OX + 270, row_y, 26, 22, "-", cor=(70, 30, 24))
            bplus = Btn(OX + 300, row_y, 26, 22, "+", cor=(28, 70, 30))
            bminus.update(mp); bplus.update(mp)
            bminus.draw(self.screen, self.f_small); bplus.draw(self.screen, self.f_small)
            self.dyn_btns.append((bminus, ("layout_adj", (key, -0.05))))
            self.dyn_btns.append((bplus, ("layout_adj", (key, 0.05))))
            row_y += 28

        breset = Btn(OX + 10, row_y + 8, 160, 24, "Restaurar layout", cor=(60, 50, 18))
        breset.update(mp)
        breset.draw(self.screen, self.f_small)
        self.dyn_btns.append((breset, ("layout_reset", None)))

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
            growth_time = max(1.0, self.game.rules["growth_time"])
            y += 4
            self.screen.blit(self.f_small.render(f"Bebes crescendo: {len(bebes)}", True, PINK), (x, y))
            for e in bebes[:4]:
                y += 14
                pct = 1 - e.tempo_crescimento / growth_time
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
        req  = max(1.0, self.game.rules["prestige_gold_req"])
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

    def _draw_reset_confirm(self, mp):
        W = 430
        H = 165
        px = (SCREEN_WIDTH - W) // 2
        py = (SCREEN_HEIGHT - H) // 2

        s = pygame.Surface((W, H), pygame.SRCALPHA)
        s.fill((12, 8, 4, 240))
        self.screen.blit(s, (px, py))
        pygame.draw.rect(self.screen, RED, (px, py, W, H), 2, border_radius=8)

        linhas = [
            ("RESETAR PROGRESSO", self.f_big, RED),
            ("Isso apaga o save atual e reinicia a mina.", self.f_normal, WHITE),
            ("As regras do admin continuam salvas.", self.f_small, GRAY),
        ]

        ty = py + 18
        for texto, fonte, cor in linhas:
            surface = fonte.render(texto, True, cor)
            self.screen.blit(surface, (px + (W - surface.get_width()) // 2, ty))
            ty += fonte.get_height() + 10

        self.btn_reset_cancel = Btn(px + 48, py + H - 44, 130, 28, "Cancelar", cor=(50, 50, 50))
        self.btn_reset_confirm = Btn(px + W - 178, py + H - 44, 130, 28, "Resetar", cor=(110, 28, 28))
        self.btn_reset_cancel.update(mp)
        self.btn_reset_confirm.update(mp)
        self.btn_reset_cancel.draw(self.screen, self.f_normal)
        self.btn_reset_confirm.draw(self.screen, self.f_normal)

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
            self.screen.blit(self.f_small.render(ach["desc"][:42], True, (110,110,110) if desbloq else DARK_GRAY), (cx3+4, cy3+18))

    # ABA 6: HISTÓRICO
    def _tab_historico(self, mp, cy):
        OX = self.OX
        x = OX + 8
        y = cy + 4
        self.screen.blit(self.f_small.render("Linha do Tempo de Eventos Marcantes", True, LIGHT_BROWN), (x, y))
        y += 24
        
        # Desenha os ultimos 10 eventos
        historico_recente = list(reversed(self.game.historico))[:8]
        if not historico_recente:
            self.screen.blit(self.f_small.render("Nenhum evento registrado ainda.", True, DARK_GRAY), (x, y))
        else:
            for t_jogo, msg in historico_recente:
                ano = int(t_jogo / 50.0) + 1
                mes = int((t_jogo % 50.0) / 4.16) + 1
                tempo_str = f"[Ano {ano}, Mês {mes:02d}]"
                
                cor = GRAY
                if "NASCIMENTO" in msg: cor = PINK
                elif "MORTO" in msg: cor = RED
                elif "MÍTICO" in msg or "LENDÁRIO" in msg: cor = GOLD
                elif "DOENÇA" in msg: cor = ORANGE
                
                self.screen.blit(self.f_small.render(tempo_str, True, CYAN), (x, y))
                self.screen.blit(self.f_small.render(msg, True, cor), (x + 130, y))
                y += 16

    # ABA 7: INVENTÁRIO (Nova funcionalidade)
    def _tab_inventario(self, mp, cy):
        OX = self.OX
        x = OX + 8
        y = cy
        
        # Botão Global Auto-Equip
        bae = Btn(x, y, 220, 24, "⚡ EQUIPAR MELHORES (TODOS)", cor=(30, 80, 110))
        bae.update(mp); bae.draw(self.screen, self.f_small)
        self.dyn_btns.append((bae, ("auto_equipar_todos", None)))
        
        # Botões de Deleção (deslocados para baixo)
        btns_y = y + 30
        b_del_comum = Btn(x, btns_y, 140, 24, "Deletar Comuns", cor=(80, 20, 20), cor_txt=WHITE)
        b_del_incomum = Btn(x + 145, btns_y, 140, 24, "Deletar Incomuns", cor=(80, 20, 20), cor_txt=WHITE)
        b_del_sel = Btn(x + 290, btns_y, 180, 24, "Deletar Selecionados", cor=(100, 40, 20), cor_txt=YELLOW)
        b_del_unsel = Btn(x + 475, btns_y, 200, 24, "Deletar NÃO Selecionados", cor=(100, 40, 20), cor_txt=YELLOW)

        # Update and Draw
        for b, acao in [(b_del_comum, "del_comum"), (b_del_incomum, "del_incomum"), (b_del_sel, "del_sel"), (b_del_unsel, "del_unsel")]:
            b.update(mp); b.draw(self.screen, self.f_small)
            self.dyn_btns.append((b, ("inv_mass_delete", acao)))
            
        y = btns_y + 30
        self.screen.blit(self.f_small.render(f"Itens Selecionados: {len(self.inv_selecionados)}", True, CYAN), (x, y))
        y += 18
        
        # Grid de itens
        inv = self.game.inventario_itens
        cols = 5
        cw = 180
        h_item = 22
        
        clip_rect = pygame.Rect(x, y, SCREEN_WIDTH - x - 10, BOTTOM_H - 60)
        self.screen.set_clip(clip_rect)
        
        # Em vez de fazer scroll nesta aba para não complexificar demais (dado o BOTTOM_H),
        # renderizamos o máximo que couber, ou os itens selecionáveis
        for i, iid in enumerate(inv):
            if iid not in ITEMS: continue
            
            c_col = i % cols
            c_row = i // cols
            ix = x + c_col * cw
            iy = y + c_row * h_item
            
            if iy + h_item > clip_rect.bottom:
                break # Acabou espaço visível
                
            item_data = ITEMS[iid]
            cor_item = RARITY_COLORS.get(item_data["raridade"], GRAY)
            is_sel = (i, iid) in self.inv_selecionados
            
            bg_col = (40, 50, 80) if is_sel else (20, 15, 10)
            rect = pygame.Rect(ix, iy, cw - 4, h_item - 2)
            
            pygame.draw.rect(self.screen, bg_col, rect, border_radius=3)
            pygame.draw.rect(self.screen, cor_item, rect, 1, border_radius=3)
            
            nome_str = item_data["nome"][:18]
            self.screen.blit(self.f_small.render(nome_str, True, WHITE), (ix + 4, iy + 2))
            
            # Hover no inventário geral para mostrar atributo
            if rect.collidepoint(mp):
                pygame.draw.rect(self.screen, CYAN, rect, 1, border_radius=3)
                
            self.dyn_btns.append((_RectBtn(rect), ("inv_toggle_sel", (i, iid))))

        self.screen.set_clip(None)

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
    # MODAL DE DETALHE DO ESCRAVO
    # ------------------------------------------------------------------

    def _draw_slave_detail(self, mp):
        """
        Modal 860×560 centralizado com detalhe completo do escravo:
        - Coluna esquerda: stats, status, comida, aposentar
        - Coluna central: 6 slots de equipamento
        - Coluna direita: inventário de itens do jogador
        """
        game = self.game
        e    = game.get_escravo(self.slave_detalhe_id)
        if not e:
            e = game._get_aposentado(self.slave_detalhe_id)
        if not e:
            self.slave_detalhe_id = None
            return

        W = 860; H = 580
        px = (SCREEN_WIDTH - W) // 2
        py = (SCREEN_HEIGHT - H) // 2

        # Fundo semitransparente
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Painel principal
        pygame.draw.rect(self.screen, (18, 12, 6), (px, py, W, H), border_radius=8)
        pygame.draw.rect(self.screen, e.cor_raridade(), (px, py, W, H), 2, border_radius=8)

        # ---- TÍTULO ----
        gc = BLUE if e.genero == "M" else PINK
        self.screen.blit(self.f_big.render(e.nome, True, WHITE), (px+10, py+8))
        self.screen.blit(self.f_small.render(
            f"{'Homem' if e.genero=='M' else 'Mulher'} | {e.raridade_geral()} | {'APOSENTADO' if e.aposentado else 'Ativo'}",
            True, e.cor_raridade()), (px+10, py+32))

        # Linha divisória
        pygame.draw.line(self.screen, PANEL_BDR, (px+6, py+48), (px+W-6, py+48), 1)

        COL1_X = px + 10
        COL2_X = px + 230
        COL3_X = px + 530
        COL_TOP = py + 55
        COL_W1  = 210
        COL_W2  = 285
        COL_W3  = 310

        # ================================================================
        # COLUNA 1 — ATRIBUTOS E STATUS
        # ================================================================
        y = COL_TOP
        self.screen.blit(self.f_title.render("ATRIBUTOS EFETIVOS", True, LIGHT_BROWN), (COL1_X, y)); y += 16

        attrs_ef = [
            ("Forca",      e.forca_efetiva(),       e.forca),
            ("Velocidade", e.velocidade_efetiva(),  e.velocidade),
            ("Resistencia",e.resistencia_efetiva(), e.resistencia),
            ("Fertilidade",e.fertilidade_efetiva(), e.fertilidade),
            ("Sorte",      e.sorte_efetiva(),       e.sorte),
            ("Lealdade",   e.lealdade_efetiva(),    e.lealdade),
        ]
        for lbl, ef, base in attrs_ef:
            cor_ef = GREEN if ef >= base else RED
            linha = f"{lbl[:8]:<8} {ef:3d}"
            if ef != base:
                linha += f" ({base:+d})" if False else f" [base:{base}]"
            self.screen.blit(self.f_small.render(f"{lbl[:10]:<10} {ef:3d}", True, cor_ef), (COL1_X, y)); y += 13

        y += 6
        # Idade
        if   e.idade < 35: cor_idade = GREEN
        elif e.idade < 50: cor_idade = YELLOW
        elif e.idade < 60: cor_idade = ORANGE
        else:              cor_idade = RED
        self.screen.blit(self.f_small.render(f"Idade: {e.idade:.1f} anos", True, cor_idade), (COL1_X, y)); y += 13
        mult_i = e.mult_idade()
        self.screen.blit(self.f_small.render(f"Mult.idade: {mult_i:.2f}x", True, GRAY), (COL1_X, y)); y += 13

        # Stamina
        stam_p = e.stamina / 100.0
        stam_c = GREEN if stam_p > 0.5 else (YELLOW if stam_p > 0.25 else RED)
        self.screen.blit(self.f_small.render(f"Stamina: {e.stamina:.0f}%", True, stam_c), (COL1_X, y)); y += 11
        pygame.draw.rect(self.screen, DARK_GRAY, (COL1_X, y, COL_W1, 6), border_radius=2)
        pygame.draw.rect(self.screen, stam_c, (COL1_X, y, int(COL_W1 * stam_p), 6), border_radius=2)
        y += 10

        # Status
        y += 4
        self.screen.blit(self.f_title.render("STATUS", True, LIGHT_BROWN), (COL1_X, y)); y += 14
        
        # Estado especial (Morto / Aposentado)
        if not e.vivo:
            self.screen.blit(self.f_small.render(f"[MORTO] {e.causa_morte or 'desconhecido'}", True, RED), (COL1_X, y)); y += 13
        elif e.aposentado:
            self.screen.blit(self.f_small.render("[APOSENTADO]", True, YELLOW), (COL1_X, y)); y += 13
        
        # Humor
        humor = e.status_humor()
        COR_HUMOR = {
            "Muito Feliz":    (140, 230, 100),
            "Satisfeito":     (100, 200, 80),
            "Normal":         GRAY,
            "Cansado":        ORANGE,
            "Muito Cansado":  (200, 80, 30),
            "Doente":         RED,
            "Faminto":        (230, 130, 0),
            "Amaldiçoado":    PURPLE,
        }
        cor_humor = COR_HUMOR.get(humor, GRAY)
        self.screen.blit(self.f_small.render(f"Humor: {humor}", True, cor_humor), (COL1_X, y)); y += 13
        
        if e.doente:
            self.screen.blit(self.f_small.render(f"DOENTE ({e.doenca_timer:.0f}s)", True, RED), (COL1_X, y)); y += 13

        if e.sem_comida:
            self.screen.blit(self.f_small.render("SEM COMIDA!", True, ORANGE), (COL1_X, y)); y += 13

        if e.tem_maldicao_ativa():
            self.screen.blit(self.f_small.render("MALDICAO ATIVA!", True, PURPLE), (COL1_X, y)); y += 13
        
        if e.par_honeymoon > 0:
            self.screen.blit(self.f_small.render(f"Lua de Mel: {e.par_honeymoon:.0f}s", True, PINK), (COL1_X, y)); y += 13
        elif e.breed_cooldown > 0:
            self.screen.blit(self.f_small.render(f"Cooldown reprod: {e.breed_cooldown:.0f}s", True, ORANGE), (COL1_X, y)); y += 13

        # Tempo na mina
        self.screen.blit(self.f_small.render(f"Tempo: {e.tempo_na_mina/60:.1f}min", True, GRAY), (COL1_X, y)); y += 13
        self.screen.blit(self.f_small.render(f"Valor: {e.valor_total}g", True, GOLD), (COL1_X, y)); y += 16

        # Comida (toggle)
        y += 4
        self.screen.blit(self.f_title.render("ALIMENTACAO", True, LIGHT_BROWN), (COL1_X, y)); y += 14
        cor_bas = CYAN if e.qualidade_comida == "basica" else DARK_GRAY
        cor_qal = GOLD if e.qualidade_comida == "qualidade" else DARK_GRAY
        btn_bas = Btn(COL1_X,    y, 90, 18, "Basica(5g)",    cor=(20,40,60) if e.qualidade_comida=="basica" else (30,30,30), cor_txt=cor_bas)
        btn_qal = Btn(COL1_X+95, y, 95, 18, "Qualid.(25g)",  cor=(50,40,10) if e.qualidade_comida=="qualidade" else (30,30,30), cor_txt=cor_qal)
        btn_bas.update(mp); btn_bas.draw(self.screen, self.f_small)
        btn_qal.update(mp); btn_qal.draw(self.screen, self.f_small)
        self.dyn_btns.append((btn_bas, ("toggle_comida", (e.id, "basica"))))
        self.dyn_btns.append((btn_qal, ("toggle_comida", (e.id, "qualidade"))))
        y += 24

        # Aposentar
        if not e.aposentado and e.idade >= RETIREMENT_AGE:
            btn_apo = Btn(COL1_X, y, COL_W1, 20, "Aposentar", cor=(60, 45, 10), cor_txt=YELLOW)
            btn_apo.update(mp); btn_apo.draw(self.screen, self.f_small)
            self.dyn_btns.append((btn_apo, ("aposentar", e.id)))
            y += 24

        # Consumíveis no inventário
        consumiveis = [iid for iid in game.inventario_itens if iid in ITEMS and ITEMS[iid].get("consumivel")]
        if consumiveis:
            y += 4
            self.screen.blit(self.f_small.render("CONSUMIVEIS:", True, LIGHT_BROWN), (COL1_X, y)); y += 13
            for iid in consumiveis[:3]:
                btn_use = Btn(COL1_X, y, COL_W1, 16, f"Usar: {ITEMS[iid]['nome'][:16]}", cor=(40,30,60))
                btn_use.update(mp); btn_use.draw(self.screen, self.f_small)
                self.dyn_btns.append((btn_use, ("usar_especial", (e.id, iid))))
                y += 18

        # ================================================================
        # COLUNA 2 — SLOTS DE EQUIPAMENTO
        # ================================================================
        y2 = COL_TOP
        self.screen.blit(self.f_title.render("EQUIPAMENTOS", True, LIGHT_BROWN), (COL2_X, y2)); y2 += 16
        pygame.draw.line(self.screen, PANEL_BDR, (COL2_X, y2), (COL2_X+COL_W2, y2), 1); y2 += 4

        # Botão Auto-Equip
        btn_auto = Btn(COL2_X, y2, COL_W2, 18, "⚡ Auto-Equip (Por Raridade)", cor=(30, 55, 80))
        btn_auto.update(mp); btn_auto.draw(self.screen, self.f_small)
        self.dyn_btns.append((btn_auto, ("auto_equipar", e.id)))
        y2 += 22

        for slot in SLOTS:
            item_id = e.equipamentos.get(slot)
            mald_t  = e.maldicoes.get(slot, 0.0)
            is_sel  = self.detalhe_slot_sel == slot

            # Cor de fundo do slot
            if is_sel:
                bg_slot = (30, 50, 80)
                bdr_c   = CYAN
            elif mald_t > 0:
                bg_slot = (40, 10, 40)
                bdr_c   = PURPLE
            else:
                bg_slot = (22, 15, 8)
                bdr_c   = PANEL_BDR

            slot_rect = pygame.Rect(COL2_X, y2, COL_W2, 34)
            pygame.draw.rect(self.screen, bg_slot, slot_rect, border_radius=3)
            pygame.draw.rect(self.screen, bdr_c, slot_rect, 1, border_radius=3)

            # Nome do slot
            nome_slot = SLOT_NOMES.get(slot, slot)
            self.screen.blit(self.f_small.render(f"{nome_slot}:", True, GRAY), (COL2_X+4, y2+4))

            # Item equipado
            if item_id and item_id in ITEMS:
                item_data = ITEMS[item_id]
                cor_item  = RARITY_COLORS.get(item_data["raridade"], GRAY)
                nome_item = item_data["nome"][:20]
                self.screen.blit(self.f_small.render(nome_item, True, cor_item), (COL2_X+60, y2+4))

                if mald_t > 0:
                    self.screen.blit(self.f_small.render(f"[MAL {mald_t:.0f}s]", True, PURPLE), (COL2_X+60, y2+18))
                else:
                    # Botão desequipar
                    btn_deq = Btn(COL2_X+COL_W2-40, y2+8, 36, 16, "[X]", cor=(80, 20, 20))
                    btn_deq.update(mp); btn_deq.draw(self.screen, self.f_small)
                    self.dyn_btns.append((btn_deq, ("desequipar", (e.id, slot))))
            else:
                self.screen.blit(self.f_small.render("---", True, DARK_GRAY), (COL2_X+60, y2+10))

            # Clique no slot seleciona para filtrar inventário
            if slot_rect.collidepoint(mp):
                pygame.draw.rect(self.screen, CYAN, slot_rect, 1, border_radius=3)

            # Guarda rect para clique
            self.dyn_btns.append((
                _RectBtn(slot_rect), ("sel_slot", slot)
            ))

            y2 += 38

        # ================================================================
        # COLUNA 3 — INVENTÁRIO DE ITENS
        # ================================================================
        y3 = COL_TOP
        inv_titulo = "INVENTARIO"
        if self.detalhe_slot_sel:
            inv_titulo += f" ({SLOT_NOMES.get(self.detalhe_slot_sel, self.detalhe_slot_sel)})"
        self.screen.blit(self.f_title.render(inv_titulo, True, LIGHT_BROWN), (COL3_X, y3)); y3 += 16
        pygame.draw.line(self.screen, PANEL_BDR, (COL3_X, y3), (COL3_X+COL_W3, y3), 1); y3 += 4

        # Filtra itens por slot selecionado (apenas não consumíveis para equipar)
        inv_itens = game.inventario_itens
        if self.detalhe_slot_sel:
            filtrado = [iid for iid in inv_itens
                        if iid in ITEMS and ITEMS[iid]["slot"] == self.detalhe_slot_sel
                        and not ITEMS[iid].get("consumivel", False)]
        else:
            filtrado = [iid for iid in inv_itens
                        if iid in ITEMS and not ITEMS[iid].get("consumivel", False)]

        if not filtrado:
            self.screen.blit(self.f_small.render("Nenhum item disponivel.", True, DARK_GRAY), (COL3_X, y3))
        else:
            for iid in filtrado[:12]:
                if y3 + 28 > py + H - 50:
                    break
                item_data = ITEMS[iid]
                cor_item  = RARITY_COLORS.get(item_data["raridade"], GRAY)

                item_rect = pygame.Rect(COL3_X, y3, COL_W3-4, 26)
                bg_col    = (28, 18, 10)
                pygame.draw.rect(self.screen, bg_col, item_rect, border_radius=3)
                pygame.draw.rect(self.screen, cor_item, item_rect, 1, border_radius=3)

                self.screen.blit(self.f_small.render(item_data["nome"][:22], True, cor_item), (COL3_X+4, y3+4))
                # Slot do item
                self.screen.blit(self.f_small.render(SLOT_NOMES.get(item_data["slot"], item_data["slot"]), True, DARK_GRAY), (COL3_X+4, y3+15))

                # Se maldito, avisa
                if item_data.get("maldito", False):
                    self.screen.blit(self.f_small.render("MALDITO", True, PURPLE), (COL3_X+150, y3+8))

                # Botão equipar (só se slot selecionado bate com o item)
                slot_item = item_data["slot"]
                pode_equip = (self.detalhe_slot_sel is None or self.detalhe_slot_sel == slot_item)
                if pode_equip:
                    btn_eq = Btn(COL3_X+COL_W3-60, y3+4, 54, 18, "Equipar",
                                 cor=(30,60,25), cor_txt=GREEN)
                    btn_eq.update(mp); btn_eq.draw(self.screen, self.f_small)
                    self.dyn_btns.append((btn_eq, ("equipar", (e.id, iid))))

                y3 += 30
                
                # Tooltip do item e comparações
                if item_rect.collidepoint(mp):
                    # Equipamento atual no mesmo slot para comparação
                    slot_item = item_data["slot"]
                    item_atual_id = e.equipamentos.get(slot_item)
                    bonus_atual = ITEMS[item_atual_id]["bonus"] if item_atual_id and item_atual_id in ITEMS else {}
                    
                    tt_w, tt_h = 220, max(60, 20 + len(item_data["bonus"]) * 14)
                    tt_x, tt_y = mp[0] - tt_w - 10, mp[1] - tt_h // 2
                    
                    s = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
                    s.fill((10, 8, 12, 230))
                    pygame.draw.rect(s, cor_item, (0, 0, tt_w, tt_h), 1, border_radius=4)
                    self.screen.blit(s, (tt_x, tt_y))
                    
                    self.screen.blit(self.f_normal.render(item_data["nome"], True, cor_item), (tt_x + 6, tt_y + 4))
                    for idx, (attr_key, attr_val) in enumerate(item_data["bonus"].items()):
                        val_atual = bonus_atual.get(attr_key, 0)
                        diff = attr_val - val_atual
                        
                        y_attr = tt_y + 24 + idx * 14
                        self.screen.blit(self.f_small.render(f"{attr_key}: {attr_val}", True, WHITE), (tt_x + 6, y_attr))
                        
                        if diff > 0:
                            self.screen.blit(self.f_small.render(f"▲ +{diff}", True, GREEN), (tt_x + 130, y_attr))
                        elif diff < 0:
                            self.screen.blit(self.f_small.render(f"▼ {diff}", True, RED), (tt_x + 130, y_attr))

        # ================================================================
        # BOTÃO FECHAR
        # ================================================================
        btn_fechar = Btn(px + W - 90, py + H - 30, 80, 22, "[FECHAR]", cor=(70, 20, 20), cor_txt=RED)
        btn_fechar.update(mp); btn_fechar.draw(self.screen, self.f_normal)
        self.dyn_btns.append((btn_fechar, ("fechar_detalhe", None)))

        # Divisórias verticais do modal
        pygame.draw.line(self.screen, PANEL_BDR, (COL2_X-5, py+50), (COL2_X-5, py+H-10), 1)
        pygame.draw.line(self.screen, PANEL_BDR, (COL3_X-5, py+50), (COL3_X-5, py+H-10), 1)

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
            (f"{'Homem' if e.genero=='M' else 'Mulher'} | Idade {e.idade:.0f} | {e.raridade_geral()}", e.cor_raridade()),
            (f"Stamina: {e.stamina:.0f}%", GREEN if e.stamina > 50 else (YELLOW if e.stamina > 25 else RED)),
            ("", None),
        ] + [(f"{txt}  [{rar}]", RARITY_COLORS.get(rar, GRAY)) for txt, rar in attrs] + [
            ("", None),
            (f"Tempo na mina: {e.tempo_na_mina/60:.1f} min", GRAY),
            (f"Valor total encontrado: {e.valor_total}g", GOLD),
            (f"Preco de venda: {e.calcular_preco(bonus_nivel_mina=self.game.nivel_mina)}g", YELLOW),
        ]
        if e.doente:
            lines.append((f"DOENTE! {e.doenca_timer:.0f}s restantes", RED))
        if e.tem_maldicao_ativa():
            lines.append(("MALDICAO ATIVA!", PURPLE))

        TW = 248; LH = 13
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
            ("1. Compre servos na aba 'Loja' (painel inferior)", self.f_normal, WHITE),
            ("2. Eles minerarao automaticamente a cada poucos segundos", self.f_normal, WHITE),
            ("3. Venda recursos no painel direito ou aba 'Mercado'", self.f_normal, WHITE),
            ("4. Upgrades -> mineracao mais eficiente e recursos raros", self.f_normal, WHITE),
            ("5. Use 'Par' na lista de servos para reproducao", self.f_normal, WHITE),
            ("6. Aprofunde a mina para recursos raros (mais risco!)", self.f_normal, WHITE),
            ("7. Clique 'Det.' para ver equipamentos e detalhes do servo", self.f_normal, WHITE),
            ("8. Itens caem durante a mineracao — equipe nos servos!", self.f_normal, WHITE),
            ("", self.f_small, WHITE),
            ("ATRIBUTOS:", self.f_title, LIGHT_BROWN),
            ("Forca -> + recursos  |  Resist. -> stamina  |  Sorte -> raros", self.f_small, GRAY),
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
        ev = self._normalize_event(ev)
        mp   = self._mouse_pos()
        game = self.game

        if self.confirm_reset:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.confirm_reset = False
                return
            if self.btn_reset_cancel and self.btn_reset_cancel.clicked(ev):
                self.confirm_reset = False
                return
            if self.btn_reset_confirm and self.btn_reset_confirm.clicked(ev):
                game.reset_progress()
                self.confirm_reset = False
                self.show_tutorial = True
                self.slave_detalhe_id = None
                self.detalhe_slot_sel = None
                self.selected_id = None
                self.slave_scroll = 0
                self.log_scroll = 0
                self.tab = 0
                return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                return

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if game.notificacao:
                game.notificacao = None
                return
            if self.show_tutorial:
                self.show_tutorial = False
                game.primeiro_jogo = False
                return

        # Se o modal de detalhe estiver aberto, ESC fecha
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.slave_detalhe_id is not None:
                self.slave_detalhe_id = None
                self.detalhe_slot_sel = None
                return

        # Scroll — lista de escravos (só quando modal fechado)
        if ev.type == pygame.MOUSEWHEEL and self.r_center.collidepoint(mp) and not self.slave_detalhe_id:
            todos = game.escravos_vivos + game.bebes
            # Usando a mesma altura LINHA_H definida no renderer (aprox 84)
            lh = max(78, int(84 * self.ui_scale))
            max_s = max(0, len(todos) * lh - (MAIN_H - 40))
            self.slave_scroll = max(0, min(max_s, self.slave_scroll - ev.y * 30))

        if ev.type == pygame.MOUSEWHEEL and self.r_bottom.collidepoint(mp) and self.tab == 0:
            self.shop_scroll = max(0, min(self.shop_scroll_max, self.shop_scroll - ev.y * 28))

        # Scroll — sidebar de log
        if ev.type == pygame.MOUSEWHEEL and self.r_sidebar.collidepoint(mp):
            total    = len(game.log)
            LINE_H   = 14
            max_vis  = (SCREEN_HEIGHT - 23) // LINE_H
            max_scroll = max(0, total - max_vis)
            # InPygame, ev.y > 0 is scroll up. We want scroll up to go back in history (older messages).
            # Since log[0] is newest, we increase log_scroll to go to older messages.
            self.log_scroll = max(0, min(max_scroll, self.log_scroll + ev.y * 3))

        # Botões topbar
        if self.btn_pause.clicked(ev):  game.pausado = not game.pausado
        if self.btn_1x.clicked(ev):     game.velocidade = 1
        if self.btn_2x.clicked(ev):     game.velocidade = 2
        if self.btn_4x.clicked(ev):     game.velocidade = 4
        if self.btn_reset.clicked(ev):  self.confirm_reset = True
        if self.btn_exit.clicked(ev):   self.request_quit = True
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
            ok, msg = game.comprar_oferta_loja(param)
            if not ok:
                game.log_add(msg, RED)

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

        elif acao == "voltar_mina":
            e = game.get_escravo(param)
            if e and e.em_repouso and e.stamina > 10:
                e.em_repouso = False
                game.log_add(f"{e.nome} voltou ao trabalho!", GREEN)

        elif acao == "remover_par":
            game.remover_par(param)

        elif acao == "prestigio":
            ok, msg = game.fazer_prestigio()
            game.log_add(msg, GOLD if ok else RED)

        # ---- Novas ações do modal de detalhe ----

        elif acao == "detalhe":
            self.slave_detalhe_id = param
            self.detalhe_slot_sel = None

        elif acao == "fechar_detalhe":
            self.slave_detalhe_id = None
            self.detalhe_slot_sel = None

        elif acao == "sel_slot":
            # Toggle seleção de slot
            if self.detalhe_slot_sel == param:
                self.detalhe_slot_sel = None
            else:
                self.detalhe_slot_sel = param

        elif acao == "auto_equipar":
            game.auto_equipar_melhores(param)
            
        elif acao == "auto_equipar_todos":
            game.auto_equipar_melhores_todos()

        elif acao == "aposentar":
            ok, msg = game.aposentar_escravo(param)
            game.log_add(msg, YELLOW if ok else RED)
            if ok:
                self.slave_detalhe_id = None
                self.detalhe_slot_sel = None

        elif acao == "toggle_comida":
            escravo_id, qualidade = param
            e = game.get_escravo_qualquer(escravo_id)
            if e:
                e.qualidade_comida = qualidade

        elif acao == "usar_especial":
            escravo_id, item_id = param
            ok, msg = game.usar_item_especial(escravo_id, item_id)
            game.log_add(msg, GREEN if ok else RED)

        elif acao == "layout_adj":
            key, delta = param
            if game.adjust_ui_config(key, delta):
                self.refresh_layout()

        elif acao == "layout_reset":
            game.reset_ui_config()
            self.refresh_layout()

        elif acao == "auto_equipar":
            ok, msg = game.auto_equipar_melhores(param)
            game.log_add(msg, GREEN if ok else RED)

        elif acao == "comprar_loja_item":
            iid, preco = param
            ok, msg = game.comprar_item_loja(iid, preco)
            game.log_add(msg, GREEN if ok else RED)

        elif acao == "inv_toggle_sel":
            inv_idx, iid = param
            pair = (inv_idx, iid)
            if pair in self.inv_selecionados:
                self.inv_selecionados.remove(pair)
            else:
                self.inv_selecionados.add(pair)
                
        elif acao == "inv_mass_delete":
            to_delete = []
            inv = self.game.inventario_itens
            
            if param == "del_comum":
                for i, iid in enumerate(inv):
                    if iid in ITEMS and ITEMS[iid]["raridade"] == "comum":
                        to_delete.append(iid)
            elif param == "del_incomum":
                for i, iid in enumerate(inv):
                    if iid in ITEMS and ITEMS[iid]["raridade"] == "incomum":
                        to_delete.append(iid)
            elif param == "del_sel":
                # Sort by index descending to safely remove if we were popping, but we just remove by element (actually we can just remove all matches or reconstruct the list)
                to_delete = [p[1] for p in self.inv_selecionados]
                self.inv_selecionados.clear()
            elif param == "del_unsel":
                sel_ids = [p[1] for p in self.inv_selecionados]
                for i, iid in enumerate(inv):
                    if iid not in sel_ids:
                        to_delete.append(iid)
                self.inv_selecionados.clear()
                
            if to_delete:
                new_inv = []
                # Remove occurrences. If an ID is in to_delete, we remove it. We'll count frequencies to handle multiple identical items properly.
                from collections import Counter
                del_counts = Counter(to_delete)
                for iid in inv:
                    if del_counts[iid] > 0:
                        del_counts[iid] -= 1
                    else:
                        new_inv.append(iid)
                        
                self.game.inventario_itens = new_inv
                self.game.log_add(f"{len(to_delete)} itens deletados do inventário.", RED)
                # clear valid selection cache since indices shifted
                self.inv_selecionados.clear()

    def notify_mining(self, escravo_id: int, cor):
        """Chamado pelo game loop quando um escravo acabou de minerar."""
        self._flash[escravo_id] = 0.28
        game = self.game
        e    = game.get_escravo(escravo_id)
        if e and hasattr(e, "anim_x"):
            self.spawn_particles(e.anim_x, e.anim_y, cor)


# ============================================================
# HELPER INTERNO — botão baseado em Rect simples
# ============================================================

class _RectBtn:
    """Rect-like mínimo que satisfaz a interface de Btn para dyn_btns."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect

    def clicked(self, ev):
        return (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.rect.collidepoint(ev.pos))

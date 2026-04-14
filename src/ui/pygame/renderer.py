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
    RED, DARK_RED, GREEN, DARK_GREEN, BLUE, YELLOW, ORANGE, PURPLE, CYAN, GOLD, SILVER, PINK,
    RARITY_COLORS, RESOURCES, RESOURCE_ORDER, MINE_UPGRADES, UPGRADE_ORDER,
    MINE_DEPTHS, ACHIEVEMENTS,
    SLOTS, SLOT_NOMES, ITEMS, RETIREMENT_AGE,
    GUARD_SLOTS, GUARD_SLOT_NOMES, GUARD_ITEMS, GUARD_TIERS, MAX_GUARDAS,
    DELIVERY_ATTACKS,
    MANAGER_TIERS, MANAGER_AUTONOMIA, MANAGER_AUTONOMIA_NOMES, MAX_GERENTES,
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

    TABS = ["Loja", "Upgrades", "Breeding", "Mercado", "Prestígio", "Conquistas", "Histórico", "Inventário", "Guardas", "Gerência", "Ranking"]
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
        self.guards_scroll = 0
        self.guards_scroll_max = 0
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

        # Guardas
        self.guarda_detalhe_id  = None   # guarda selecionado no modal
        self.guarda_slot_sel    = None   # slot selecionado no modal de guarda
        self.guardas_scroll     = 0

        self.show_tutorial      = game.primeiro_jogo
        self.show_vendedor      = False
        self.show_notifications = False
        self.confirm_reset      = False

        # Gerentes
        self.gerente_modal_id  = None    # ID do gerente com modal de config aberto
        self.gerencia_scroll   = 0

        self.dyn_btns: list[tuple[Btn, tuple]] = []

        self._particles: list[list] = []
        self._flash: dict[int, float] = {}
        
        # --- NOVO: ESTADO DE LOGIN / CLOUD ---
        self.state = "login"
        self.login_user = ""
        self.login_pass = ""
        self.login_focus = 0 # 0=user, 1=pass
        self.login_msg = ""
        self.login_loading = False
        self.ranking_data = None
        self.ranking_loading = False
        self.selected_tab_old = None # Para voltar do ranking

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
        BOTTOM_H = max(175, int(BASE_BOTTOM_H * cfg.get("bottom_factor", 1.0) * ui_scale))
        max_bottom = SCREEN_HEIGHT - TOP_H - 240
        BOTTOM_H = min(BOTTOM_H, max(170, max_bottom))
        MAIN_H = SCREEN_HEIGHT - TOP_H - BOTTOM_H

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
        self.f_tiny   = pygame.font.SysFont("monospace", max(9, int(9 * ui_scale)))

        OX = self.OX
        self.r_sidebar = pygame.Rect(0, 0, LOG_SIDEBAR_W, SCREEN_HEIGHT)
        self.r_top     = pygame.Rect(OX, 0, SCREEN_WIDTH - OX, TOP_H)
        self.r_left    = pygame.Rect(OX, TOP_H, LEFT_W, MAIN_H)
        self.r_center  = pygame.Rect(OX + LEFT_W, TOP_H, CENTER_W, MAIN_H)
        self.r_right   = pygame.Rect(OX + LEFT_W + CENTER_W, TOP_H, RIGHT_W, MAIN_H)
        self.r_bottom  = pygame.Rect(OX, TOP_H + MAIN_H, SCREEN_WIDTH - OX, BOTTOM_H)

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
        bw_bell = 44; bx_bell = base - bw_bell; base = bx_bell - 8
        bw_res = 72; bx_res = base - bw_res
        
        self.btn_reset  = Btn(bx_res, 5, bw_res, 30, "Reset",    cor=(110, 28, 28))
        self.btn_aceler = Btn(bx_ace, 5, bw_ace, 30, "Acelerar", cor=(80, 40, 90))
        self.btn_bell   = Btn(bx_bell, 5, bw_bell, 30, "🔔", cor=(50, 50, 80))
        self.btn_save   = Btn(bx_save, 5, bw_save, 30, "Salvar",   cor=(30, 55, 100))
        self.btn_pause  = Btn(bx_pause, 5, bw_pause, 30, "Pause",    cor=(70, 45, 15))
        self.btn_1x     = Btn(bx_1x, 5, bw_1x, 30, "1x",       cor=(30, 70, 30))
        self.btn_2x     = Btn(bx_2x, 5, bw_2x, 30, "2x",       cor=(70, 70, 20))
        self.btn_4x     = Btn(bx_4x, 5, bw_4x, 30, "4x",       cor=(90, 30, 30))
        self.btn_exit   = Btn(bx_exit, 5, bw_exit, 30, "Encerrar", cor=(95, 22, 22))
        self._top_btns  = [
            self.btn_reset,
            self.btn_aceler,
            self.btn_bell,
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

        if self.state == "login":
            self._draw_login_screen_bg()
            self._draw_login_form(mp)
            return

        self.screen.fill(DARK_BG)

        # Detecta novas mensagens e reseta scroll
        curr_log_len = len(self.game.log)
        if not hasattr(self, "_last_log_len"): self._last_log_len = 0
        if curr_log_len > self._last_log_len:
            self.log_scroll = 0
            self._last_log_len = curr_log_len

        self._draw_log_sidebar()
        self._draw_topbar(mp)
        self._draw_left(mp)
        self._draw_center(mp)
        self._draw_right(mp)
        self._draw_bottom(mp)
        
        # Pop-ups Proativos
        if self.game.rec_importante_pendente:
            self._draw_manager_popup(mp)
        elif self.game.notificacao:
             # Nota: _draw_vendedor_modal era usado aqui erroneamente. 
             # O _draw_notif() ja e chamado no bloco de Overlays abaixo.
             pass

        # Divisórias
        def vline(x, y1, y2): pygame.draw.line(self.screen, PANEL_BDR, (x, y1), (x, y2), 1)
        def hline(y, x1, x2): pygame.draw.line(self.screen, PANEL_BDR, (x1, y), (x2, y), 1)
        vline(OX,                 0,     SCREEN_HEIGHT)
        hline(TOP_H,              OX,    SCREEN_WIDTH)
        hline(TOP_H+MAIN_H+BOTTOM_H, OX, SCREEN_WIDTH)
        vline(OX+LEFT_W,          TOP_H, TOP_H+MAIN_H)
        vline(OX+LEFT_W+CENTER_W, TOP_H, TOP_H+MAIN_H)

        # Overlays
        if self.tooltip_slave and not self.slave_detalhe_id and not self.guarda_detalhe_id:
            self._draw_tooltip(mp)
        if self.game.notificacao:
            self._draw_notif()
        
        self._draw_toasts()

        if self.show_tutorial:
            self._draw_tutorial()

        # Modal vendedor (por cima da notificação)
        if self.show_vendedor and self.game.vendedor_atual:
            self._draw_vendedor_modal(mp)

        # Modal de detalhe (por cima de tudo)
        if self.slave_detalhe_id:
            self._draw_slave_detail(mp)
        if self.guarda_detalhe_id:
            self._draw_guarda_detail(mp)
        if self.gerente_modal_id is not None:
            self._draw_gerente_modal(mp)
        if self.confirm_reset:
            self._draw_reset_confirm(mp)

    # ------------------------------------------------------------------
    # BARRA LATERAL DE LOG (altura total da tela)
    # ------------------------------------------------------------------

    def _draw_log_sidebar(self):
        OX  = self.OX
        # Log: Newest at top
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

        # --- Badge de Notificações ---
        n_count = sum(1 for n in self.game.notificacoes_history if not n["lida"])
        if n_count > 0:
            bx, by = self.btn_bell.rect.x + 30, self.btn_bell.rect.y + 5
            pygame.draw.circle(self.screen, RED, (bx, by), 8)
            num_txt = self.f_small.render(str(min(9, n_count)), True, WHITE)
            self.screen.blit(num_txt, (bx - num_txt.get_width()//2, by - num_txt.get_height()//2))

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

        # Divide a área entre mineração e entrega
        MINE_GRID_H = int(MAIN_H * 0.65)
        self.screen.set_clip(pygame.Rect(OX, TOP_H, LEFT_W, MINE_GRID_H))

        # Desenha apenas 4x4 miners (16) para dar espaço ao transporte
        for i, e in enumerate(todos[:16]):
            col = i % COLS
            row = i // COLS
            cx  = OX + col * CW + CW // 2
            cy  = TOP_H + 50 + row * CH

            e.anim_x = cx
            e.anim_y = cy
            self._draw_miner_pixel(cx, cy, e, t_real)

        # ---- NOVO: Desenha o Gerente se houver ----
        if game.gerentes:
            g = game.gerentes[0] # Exibe o primeiro gerente
            # O gerente caminha horizontalmente no topo
            g_path_w = LEFT_W - 60
            g_x = OX + 30 + (math.sin(t_real * 0.5) * 0.5 + 0.5) * g_path_w
            self._draw_manager_unit(g_x, TOP_H + 25, g, t_real)

        self.screen.set_clip(None)

        # ---- NOVO: Desenha Guardas patrulhando a estrada ----
        if game.guardas:
            ROAD_Y = TOP_H + MINE_GRID_H
            ROAD_H = MAIN_H - MINE_GRID_H
            self.screen.set_clip(pygame.Rect(OX, ROAD_Y, LEFT_W, ROAD_H))
            for i, g in enumerate(game.guardas):
                if not g.ativo: continue
                # Posiciona guardas em locais fixos de vigia ou patrulha curta
                gx = OX + 40 + i * 45
                gy = ROAD_Y + 15
                self._draw_guard_unit(gx, gy, g, t_real)
            self.screen.set_clip(None)

        # ----------------------------------------------------------
        # ZONA DE ENTREGA (Road & Environment)
        # ----------------------------------------------------------
        ROAD_Y = TOP_H + MINE_GRID_H
        ROAD_H = MAIN_H - MINE_GRID_H
        
        # 1. Desenha Ambiente (Grama/Terra/Árvores)
        self._draw_road_environment(OX, ROAD_Y, LEFT_W, ROAD_H, t_real)

        # 2. Desenha Entregas Ativas (Cavalos e Carroças)
        self.screen.set_clip(pygame.Rect(OX, ROAD_Y, LEFT_W, ROAD_H))
        
        for delivery in game.entregas:
            if delivery.timer_max <= 0: continue
            
            # Distribuição Vertical (Lanes)
            # Cada ID de entrega fica em uma "faixa" diferente da estrada
            lane = delivery.id % 3
            lane_off = 35 + (lane * 35) # Distribui entre y+35, y+70, y+105
            
            prog = 1.0 - (delivery.timer / delivery.timer_max)
            margin = 55 # Margem para entrar no forte
            dx = OX + LEFT_W - (prog * (LEFT_W + margin)) + margin - 20
            
            if delivery.status == "entregue":
                if prog > 1.15: continue
                self._draw_delivery_unit(dx, ROAD_Y + lane_off, delivery, t_real)
                if 1.0 <= prog <= 1.05:
                    self._spawn_coin_explosion(OX + 20, ROAD_Y + lane_off)
            
            elif delivery.status == "perdido":
                if prog > 1.3: continue 
                self._draw_delivery_unit(dx, ROAD_Y + lane_off, delivery, t_real)
                self._draw_delivery_attack(dx, ROAD_Y + lane_off, delivery, t_real)
            else:
                self._draw_delivery_unit(dx, ROAD_Y + lane_off, delivery, t_real)

        self.screen.set_clip(None)

        # 3. Desenha Portal do Forte (Acima dos cavalos que entram)
        self._draw_fortress_gate(OX, ROAD_Y, ROAD_H)

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

        # --- VARIÁVEIS DE ESTADO (Cansado / Idoso) ---
        is_tired = e.stamina < 30
        is_old   = e.idade >= 55
        
        # Velocidade da animação: servos cansados mineram 50% mais devagar visualmente
        anim_speed = 3.0 if is_tired else 6.0
        swing_cycle = (t_real * anim_speed + e.anim_frame * 0.4) % 1.0
        # p: [0..1]
        if swing_cycle < 0.5:
            # 1. ANTECIPAÇÃO (Lento para trás)
            p = swing_cycle / 0.5
            swing = p * 60
            lean  = -p * 4   # inclina para trás
            vib   = 0
            impact = False
        elif swing_cycle < 0.6:
            # 2. IMPACTO (Explosivo para frente)
            p = (swing_cycle - 0.5) / 0.1
            swing = 60 - (p * 140) # Swing amplo até -80
            lean  = -4 + (p * 14)  # Inclina muito para frente
            vib   = (p * 3) if p < 0.5 else (-3 if p < 0.8 else 0)
            impact = True
        elif swing_cycle < 0.7:
            # 3. KICKBACK / IMPACT FLASH (Rápido travamento)
            swing = -80
            lean  = 10
            vib   = random.uniform(-2, 2)
            impact = True # Mantém faíscas/flash por 2 frames
        else:
            # 4. RESET (Lento retorno)
            p = (swing_cycle - 0.7) / 0.3
            swing = -80 + (p * 80)
            lean  = 10 - (p * 10)
            vib   = 0
            impact = False
            
        yo += int(lean)
        if is_tired:
            yo += 2 # Cabeça mais "caída"
            
        # Tremor de idoso
        if is_old:
            cx += random.randint(-1, 1)
            cy += random.randint(-1, 1)

        cx += int(vib) # Vibração horizontal no impacto

        vp    = e.stamina / 100.0  
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
            # Rastro de Movimento (Motion Blur)
            if impact:
                trail_s = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.arc(trail_s, (200, 200, 200, 100), (0, 0, 30, 30), 0.5, 2.5, 2)
                self.screen.blit(trail_s, (cx + 5, cy - 20 + yo))
                
                # Impact Flash
                pygame.draw.circle(self.screen, WHITE, (px1, py1), 5)

            # Partículas de Pedra no Impacto
            if impact and random.random() < 0.4:
                self._particles.append([
                    px1, py1,
                    random.uniform(2, 6), random.uniform(-6, -2),
                    25, (130, 120, 110)
                ])

            if is_pic_top:
                pygame.draw.rect(self.screen, (255, 255, 255), (head_x+2, head_y-2, 2, 8)) # Lâmina central estendida
        else:
            # Braço em repouso
            pygame.draw.rect(self.screen, body, (cx+8, cy-18+yo, 4, 5))
            pygame.draw.rect(self.screen, skin, (cx+8, cy-13+yo, 4, 10))

    def _draw_delivery_unit(self, x, y, delivery, t_real):
        """Desenha o cavalo detalhado puxando a carroça (VETORIZADO PARA A ESQUERDA)."""
        leg_frame = int(t_real * 12) % 4
        bob = int(math.sin(t_real * 10.0) * 1.8)
        
        # Sombra projetada
        pygame.draw.ellipse(self.screen, (15, 10, 5), (x-25, y+10, 55, 12))
        
        h_cor = (95, 65, 35) # Marrom
        c_cor = (85, 55, 30) # Madeira
        b_cor = RESOURCES.get(delivery.recurso, {}).get("cor", GOLD)
        
        # 1. CAVALO (Olhando para a ESQUERDA)
        # O cavalo puxa, então ele fica na FRENTE da carroça (à esquerda da carroça no movimento R->L)
        hx, hy = x - 22, y + bob
        # Corpo
        pygame.draw.rect(self.screen, h_cor, (hx, hy, 14, 9), border_radius=2)
        # Pescoço e Cabeça (Forma mais curva para a esquerda)
        pygame.draw.rect(self.screen, h_cor, (hx-1, hy-8, 5, 10))
        pygame.draw.rect(self.screen, h_cor, (hx-6, hy-9, 7, 5), border_radius=1)
        # Rabo (na direita agora)
        pygame.draw.line(self.screen, (40, 25, 10), (hx+14, hy+2), (hx+18, hy+6+bob), 2)
        # Pernas Animadas
        legs_y = hy + 8
        if leg_frame in (0, 2):
            pygame.draw.line(self.screen, (20, 15, 10), (hx+3, legs_y), (hx+1, legs_y+5), 2)
            pygame.draw.line(self.screen, (20, 15, 10), (hx+11, legs_y), (hx+13, legs_y+5), 2)
        else:
            pygame.draw.line(self.screen, (20, 15, 10), (hx+3, legs_y), (hx+5, legs_y+5), 2)
            pygame.draw.line(self.screen, (20, 15, 10), (hx+11, legs_y), (hx+9, legs_y+5), 2)

        # 2. CARROÇA (Atrás do cavalo, à DIREITA dele)
        cx, cy = hx + 16, y
        # Conexão (Eixo)
        pygame.draw.line(self.screen, (60, 60, 60), (hx+5, hy+4), (cx, cy+4), 1)
        # Base
        pygame.draw.rect(self.screen, c_cor, (cx, cy-2, 24, 13))
        for line_y in range(cy, cy+10, 4):
            pygame.draw.line(self.screen, (55, 35, 20), (cx, line_y), (cx+23, line_y), 1)
        # Rodas
        for rx_off in (6, 18):
            rx, ry = cx + rx_off, cy + 12
            pygame.draw.circle(self.screen, (35, 35, 35), (rx, ry), 5)
            ang = (t_real * 15) % 360
            pygame.draw.line(self.screen, (80, 80, 80), (rx, ry), (rx + math.cos(ang)*4, ry + math.sin(ang)*4), 1)

        # 3. SACOS
        for i in range(2):
            sx, sy = cx + 4 + i*9, cy - 6 + (i%2)*1
            pygame.draw.circle(self.screen, b_cor, (sx+4, sy+5), 5)
            pygame.draw.rect(self.screen, b_cor, (sx+3, sy, 4, 3))
            pygame.draw.rect(self.screen, (max(0, b_cor[0]-60), max(0, b_cor[1]-60), max(0, b_cor[2]-60)), (sx+3, sy+1, 4, 2))
            if RESOURCES.get(delivery.recurso, {}).get("valor", 0) >= 25:
                pygame.draw.circle(self.screen, WHITE, (sx+4, sy+4), 2)

    def _draw_delivery_attack(self, x, y, delivery, t_real):
        """Desenha o sprite do inimigo com silhueta característica."""
        jump_t = (t_real * 12) % 6
        off_y = int(math.sin(jump_t) * 18)
        a_cor = delivery.ataque_cor
        ex, ey = x + 8, y - 35 + off_y
        
        # Silhueta característica baseada no nome
        name_low = delivery.ataque_nome.lower()
        if "lobo" in name_low:
            # Lobo: Orelhas pontudas
            pygame.draw.rect(self.screen, a_cor, (ex, ey, 11, 8), border_radius=2)
            pygame.draw.polygon(self.screen, a_cor, [(ex, ey), (ex+3, ey-4), (ex+5, ey)])
            pygame.draw.polygon(self.screen, a_cor, [(ex+6, ey), (ex+8, ey-4), (ex+11, ey)])
        elif "orca" in name_low or "orc" in name_low:
            # Orc: Mais largo, ombros
            pygame.draw.rect(self.screen, a_cor, (ex-2, ey+2, 14, 9), border_radius=1)
            pygame.draw.rect(self.screen, a_cor, (ex+1, ey-4, 8, 8), border_radius=4)
        else:
            # Genérico/Ladrão: Capuz
            pygame.draw.rect(self.screen, a_cor, (ex, ey, 10, 10), border_radius=5)
        
        # Efeito de Impacto (Substituindo texto fixo por ícone e flash)
        if int(t_real * 6) % 2 == 0:
            pygame.draw.circle(self.screen, WHITE, (ex+5, ey+5), 8, 1)

    def _draw_manager_unit(self, x, y, g, t_real):
        """Desenha o Gerente com prancheta e visual de inspetor."""
        bob = int(math.sin(t_real * 3.0) * 2)
        skin = (235, 200, 160)
        suit = (35, 35, 45) # Terno escuro
        
        # Sombra
        pygame.draw.ellipse(self.screen, (15, 10, 5), (x-6, y+16, 12, 5))
        
        # Corpo
        pygame.draw.rect(self.screen, suit, (x-4, y, 8, 12), border_radius=2)
        # Cabeça
        pygame.draw.rect(self.screen, skin, (x-4, y-8 + bob, 8, 8), border_radius=3)
        # Chapéu / Cartola
        pygame.draw.rect(self.screen, (10, 10, 10), (x-5, y-8 + bob, 10, 2))
        pygame.draw.rect(self.screen, (10, 10, 10), (x-3, y-13 + bob, 6, 6))
        
        # Prancheta (Clipboard)
        pygame.draw.rect(self.screen, (180, 160, 130), (x+4, y + bob, 6, 8))
        pygame.draw.rect(self.screen, (240, 240, 240), (x+5, y+1 + bob, 4, 6))
        
        # Nome flutuante
        txt = self.f_small.render(g.nome.split("#")[0], True, CYAN)
        self.screen.blit(txt, (x - txt.get_width()//2, y - 25 + bob))

    def _draw_guard_unit(self, x, y, g, t_real):
        """Desenha o Guarda com variações baseadas em Força e Agilidade."""
        # Se agilidade alta, ele fica mais "inquieto" (bob mais rápido)
        agitacao = 1.0 + (g.agilidade_efetiva() / 100.0)
        bob = int(math.sin(t_real * 2.0 * agitacao) * 2)
        
        # Cor da armadura baseada em força
        # Força alta = armadura mais brilhante/metálica
        f_factor = min(1.0, g.forca_efetiva() / 100.0)
        armor_c = (100 + 100*f_factor, 105 + 100*f_factor, 120 + 100*f_factor)
        
        # Sombra
        pygame.draw.ellipse(self.screen, (15, 10, 5), (x-7, y+18, 14, 6))
        
        # 1. Pernas
        pygame.draw.rect(self.screen, (30, 30, 40), (x-4, y+12, 3, 7))
        pygame.draw.rect(self.screen, (30, 30, 40), (x+1, y+12, 3, 7))
        
        # 2. Corpo (Armadura)
        # Se força for muito alta, ele fica mais "largo"
        width = 10 if g.forca_efetiva() < 80 else 12
        pygame.draw.rect(self.screen, armor_c, (x - width//2, y, width, 14), border_radius=2)
        
        # 3. Cabeça (Elmo)
        pygame.draw.rect(self.screen, armor_c, (x-4, y-9 + bob, 8, 9), border_radius=3)
        # Fresta do elmo
        pygame.draw.rect(self.screen, (10, 10, 10), (x-3, y-6 + bob, 6, 2))
        
        # 4. Lança/Arma
        weapon_c = (150, 150, 160)
        pygame.draw.line(self.screen, (80, 50, 20), (x+5, y+15), (x+5, y-15 + bob), 2)
        pygame.draw.polygon(self.screen, weapon_c, [(x+3, y-15+bob), (x+7, y-15+bob), (x+5, y-22+bob)])

    def _draw_road_environment(self, ox, ry, rw, rh, t_real):
        """Desenha grama, árvores e detalhes do terreno na estrada."""
        # Chão de terra batida
        pygame.draw.rect(self.screen, (40, 30, 15), (ox, ry, rw, rh))
        
        # Margem de grama superior e inferior
        pygame.draw.rect(self.screen, (15, 40, 10), (ox, ry, rw, 12))
        pygame.draw.rect(self.screen, (15, 35, 10), (ox, ry + rh - 12, rw, 12))
        
        # Variação de pedras e terra (sem usar random puro todo frame)
        seed = 42
        for i in range(12):
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            px = ox + (seed % rw)
            py = ry + 15 + (seed % (rh - 30))
            pygame.draw.rect(self.screen, (55, 45, 30), (px, py, 3, 2))
            
        # Árvores de fundo (limitadas a 3 para não poluir)
        for tx in [ox + 80, ox + 220, ox + 360]:
            # Tronco
            pygame.draw.rect(self.screen, (60, 40, 20), (tx, ry - 15, 8, 20))
            # Copa (Mini Pixel Art)
            pygame.draw.circle(self.screen, (20, 55, 15), (tx + 4, ry - 20), 12)
            pygame.draw.circle(self.screen, (30, 70, 20), (tx + 8, ry - 22), 8)

        # Tufos de grama na estrada
        for gx in [ox + 40, ox + 150, ox + 280, ox + 410]:
            pygame.draw.line(self.screen, (40, 80, 20), (gx, ry + rh - 10), (gx - 3, ry + rh - 16), 2)
            pygame.draw.line(self.screen, (40, 80, 20), (gx, ry + rh - 10), (gx + 3, ry + rh - 18), 2)

    def _draw_fortress_gate(self, ox, ry, rh):
        """Desenha a entrada do Forte/Vila (ponto de chegada)."""
        gate_w = 60
        # 1. Base/Pilares (Pedra)
        pygame.draw.rect(self.screen, (60, 60, 65), (ox, ry, 35, rh))           # Parede lateral
        pygame.draw.rect(self.screen, (45, 45, 50), (ox + 35, ry, 10, rh))     # Sombra interna
        
        # 2. Topo/Torre de vigia
        pygame.draw.rect(self.screen, (70, 70, 75), (ox, ry - 15, 55, 25), border_radius=2)
        # Merlões (Ameias) da torre
        for i in range(0, 50, 15):
            pygame.draw.rect(self.screen, (70, 70, 75), (ox + i, ry - 25, 10, 12))
            
        # 3. Janela/Fresta de vigia
        pygame.draw.rect(self.screen, (10, 10, 10), (ox + 15, ry - 5, 12, 6))
        
        # 4. Detalhes de madeira (Portão aberto)
        pygame.draw.rect(self.screen, (90, 60, 30), (ox + 40, ry + 10, 6, rh - 20))

    def _spawn_coin_explosion(self, x, y):
        """Cria uma explosão ultrarrápida (0.5s) e concentrada."""
        for _ in range(3): # Apenas 3 moedas
            self._particles.append([
                float(x), float(y),
                random.uniform(-1.5, 1.5), random.uniform(-4, -2), # Campo pequeno
                30, GOLD # 30 frames = 0.5s
            ])

    def _spawn_glow_particles(self, x, y, color):
        """Cria partículas com brilho suave (usando alpha se possível)."""
        for _ in range(5):
            self._particles.append([
                float(x), float(y),
                random.uniform(-2, 2), random.uniform(-2, 2),
                20, color
            ])

    def _update_particles(self):
        nxt = []
        GRAVITY = 0.26
        for p in self._particles:
            # p: [x, y, vx, vy, life, color]
            p[0] += p[2]
            p[1] += p[3]
            p[3] += GRAVITY
            p[4] -= 1
            if p[4] > 0:
                # Fade out suave se a vida for longa
                alpha = 255
                if p[4] < 20: 
                    alpha = int(255 * (p[4] / 20))
                
                if alpha < 255:
                    # Desenha com alpha (Surface temporária ou pixel simples se performance for chave)
                    s = pygame.Surface((3, 3), pygame.SRCALPHA)
                    s.fill((*p[5], alpha))
                    self.screen.blit(s, (int(p[0]), int(p[1])))
                else:
                    pygame.draw.rect(self.screen, p[5], (int(p[0]), int(p[1]), 3, 3))
                
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

        # ── Vendedor disponível ──────────────────────────────────────────
        if game.vendedor_atual:
            v = game.vendedor_atual
            qual_cor = {
                "barato": GRAY, "raro": BLUE, "ruim": RED, "maldito": PURPLE,
            }.get(v["qualidade"], GOLD)
            qual_nomes = {
                "barato": "Mercador de Bugigangas",
                "raro":   "Comerciante Raro",
                "ruim":   "Mascate Duvidoso",
                "maldito":"Vendedor das Sombras",
            }
            pygame.draw.rect(self.screen, (30,20,40), (rx+4, y, RIGHT_W-8, 40), border_radius=4)
            pygame.draw.rect(self.screen, qual_cor,  (rx+4, y, RIGHT_W-8, 40), 1, border_radius=4)
            self.screen.blit(self.f_small.render(
                f"{qual_nomes.get(v['qualidade'],'Vendedor')} [{v['timer']:.0f}s]",
                True, qual_cor), (rx+8, y+2))
            bvend = Btn(rx+6, y+16, RIGHT_W-12, 22, "⚡ Ver Itens", cor=(60,25,80), cor_txt=GOLD)
            bvend.update(mp); bvend.draw(self.screen, self.f_small)
            self.dyn_btns.append((bvend, ("abrir_vendedor", None)))
            y += 44

        # ── Entregas em trânsito ─────────────────────────────────────────
        em_transito = [d for d in game.entregas if d.status == "transito"]
        if em_transito:
            pygame.draw.line(self.screen, PANEL_BDR, (rx+4, y), (rx+RIGHT_W-4, y), 1); y += 3
            self.screen.blit(
                self.f_small.render(f"ENTREGAS ({len(em_transito)})", True, YELLOW), (rx+6, y)
            ); y += 13
            for d in em_transito[:5]:
                cor_rec = RESOURCES.get(d.recurso, {}).get("cor", GRAY)
                frac    = max(0.0, d.timer / max(0.1, d.timer_max))
                bw      = RIGHT_W - 12
                pygame.draw.rect(self.screen, DARK_GRAY, (rx+6, y, bw, 12), border_radius=3)
                pygame.draw.rect(self.screen, cor_rec,   (rx+6, y, int(bw*frac), 12), border_radius=3)
                lbl = f"{d.qtd}x {d.recurso[:8]} ({d.timer:.0f}s)"
                self.screen.blit(self.f_small.render(lbl, True, WHITE), (rx+8, y+1))
                y += 14
            if y < TOP_H + MAIN_H - 4:
                y += 2

        # ── Resumo itens ─────────────────────────────────────────────────
        n_itens = len(game.inventario_itens)
        if n_itens > 0:
            pygame.draw.line(self.screen, PANEL_BDR, (rx+4, y), (rx+RIGHT_W-4, y), 1); y += 4
            self.screen.blit(self.f_small.render(f"Itens: {n_itens}", True, CYAN), (rx+6, y)); y += 14

        # ── Guardas resumo ───────────────────────────────────────────────
        if game.guardas:
            ativos = sum(1 for g in game.guardas if g.ativo)
            agi_red = game.guardas_ataque_reducao()
            rec_bon = game.guardas_recuperacao_bonus()
            pygame.draw.line(self.screen, PANEL_BDR, (rx+4, y), (rx+RIGHT_W-4, y), 1); y += 3
            self.screen.blit(self.f_small.render(f"Guardas: {ativos}/{len(game.guardas)}", True, CYAN), (rx+6, y)); y += 12
            self.screen.blit(self.f_small.render(f"-Atq: {agi_red*100:.0f}%  +Rec: {rec_bon*100:.0f}%", True, GREEN), (rx+6, y)); y += 14

        self.screen.blit(self.f_title.render("ESTATÍSTICAS", True, LIGHT_BROWN), (rx+6, y))
        
        # Botão para alternar modo de visão de estatísticas (Normal / Gráfico)
        btn_graf = Btn(rx + RIGHT_W - 85, y, 75, 18, 
                       "GRÁFICO" if getattr(self, "stat_view", 0) == 0 else "RESUMO",
                       cor=(60, 40, 20))
        btn_graf.update(mp); btn_graf.draw(self.screen, self.f_tiny)
        self.dyn_btns.append((btn_graf, ("toggle_stat_view", None)))
        y += 18
        
        if getattr(self, "stat_view", 0) == 1:
            self._draw_mortality_chart(rx + 6, y)
            return

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
        elif self.tab == 8: self._tab_guardas(mp, cy)
        elif self.tab == 9: self._tab_gerencia(mp, cy)
        elif self.tab == 10: self._tab_ranking(mp, cy)

    # ABA 0: LOJA
    def _tab_loja(self, mp, cy):
        OX    = self.OX
        game  = self.game
        CH    = BOTTOM_H - 34
        lh    = self.f_small.get_height()
        # Sincroniza com ITEM_PANEL_W (230) para evitar que cards de servos fiquem por baixo da loja de itens
        right_panel_w = 236 
        usable_w = max(220, SCREEN_WIDTH - OX - right_panel_w - 4)
        card_w = max(int(206 * self.ui_scale), min(int(250 * self.ui_scale), usable_w // 3 - 8))
        card_h = max(96, int(96 * self.ui_scale))
        gap = 6
        cols = max(1, usable_w // (card_w + gap))
        row_h = card_h + gap
        total_rows = max(1, math.ceil(len(game.loja) / cols))
        content_h = total_rows * row_h - gap
        # Viewport dos Cards (Configurações agora calculadas ANTES do scroll max)
        cards_y_start = cy + 32
        cards_h = CH - 36
        self.shop_scroll_max = max(0, content_h - (cards_h - 10)) # Margem de segurança
        self.shop_scroll = max(0, min(self.shop_scroll, self.shop_scroll_max))

        # HEADER FIXO (Botão e Status)
        header_y = cy + 4
        br = Btn(OX + 8, header_y, 180, 24, f"🔄 Refrescar Loja ({game.custo_refresco}g)", cor=(55, 45, 30))
        br.update(mp); br.draw(self.screen, self.f_small)
        self.dyn_btns.append((br, ("refresca", None)))
        
        if not game.pode_adicionar_servo():
            self.screen.blit(self.f_small.render("⚠️ Capacidade máxima atingida!", True, ORANGE), (OX + 200, header_y + 4))

        # Viewport dos Cards
        viewport = pygame.Rect(OX + 6, cards_y_start, usable_w, cards_h)
        clip_prev = self.screen.get_clip()
        self.screen.set_clip(viewport)

        for i, oferta in enumerate(game.loja):
            e = oferta["servo"]
            row = i // cols
            col = i % cols
            cx = viewport.x + col * (card_w + gap)
            card_y = cards_y_start + row * row_h - self.shop_scroll
            if card_y + card_h < viewport.y or card_y > viewport.bottom:
                continue

            cor_r = e.cor_raridade()
            # Fundo transparente com borda (removemos o fundo preto sólido)
            # pygame.draw.rect(self.screen, (20, 14, 8), (cx, card_y, card_w, card_h), border_radius=5)
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
            pygame.draw.rect(self.screen, DARK_GRAY, (bar_x, viewport.y, 4, viewport.height), border_radius=2)
            handle_h = max(16, int(viewport.height * (viewport.height / max(viewport.height, content_h))))
            handle_y = viewport.y + int((viewport.height - handle_h) * (self.shop_scroll / max(1, self.shop_scroll_max)))
            pygame.draw.rect(self.screen, LIGHT_BROWN, (bar_x, handle_y, 4, handle_h), border_radius=2)

        # ============================================================
        # Loja de Itens Especial — painel fixo no canto direito
        # ============================================================
        ITEM_PANEL_W = 230
        item_x = SCREEN_WIDTH - ITEM_PANEL_W - 6
        item_y = cy
        
        # Fundo do painel (Totalmente integrado/transparente)
        pygame.draw.rect(self.screen, (100, 60, 140), (item_x, item_y, ITEM_PANEL_W, CH), 1, border_radius=6)
        
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
        for i, it_obj in enumerate(inv):
            # Segurança contra strings se por algum motivo escaparem à sanitização
            if isinstance(it_obj, str):
                iid = it_obj
                added_at = self.game.tempo_jogo
            else:
                iid = it_obj.get("id", "item_erro")
                added_at = it_obj.get("added_at", self.game.tempo_jogo)
            
            if iid not in ITEMS: continue
            
            # Cálculo de tempo restante (120s - tempo decorrido)
            tempo_decorrido = self.game.tempo_jogo - added_at
            tempo_restante = max(0, 120.0 - tempo_decorrido)
            
            c_col = i % cols
            c_row = i // cols
            ix = x + c_col * cw
            iy = y + c_row * h_item
            
            if iy + h_item > clip_rect.bottom:
                break # Acabou espaço visível
                
            item_data = ITEMS[iid]
            cor_item = RARITY_COLORS.get(item_data["raridade"], GRAY)
            is_sel = id(it_obj) in self.inv_selecionados
            
            bg_col = (40, 50, 80) if is_sel else (20, 15, 10)
            rect = pygame.Rect(ix, iy, cw - 4, h_item - 2)
            
            pygame.draw.rect(self.screen, bg_col, rect, border_radius=3)
            pygame.draw.rect(self.screen, cor_item, rect, 1, border_radius=3)
            
            # Nome e Tempo
            nome_str = item_data["nome"][:14]
            timer_str = f"{tempo_restante:.0f}s"
            timer_cor = RED if tempo_restante < 30 else YELLOW
            
            self.screen.blit(self.f_small.render(nome_str, True, WHITE), (ix + 4, iy + 2))
            self.screen.blit(self.f_tiny.render(timer_str, True, timer_cor), (ix + cw - 40, iy + 4))
            
            # Hover no inventário geral
            if rect.collidepoint(mp):
                pygame.draw.rect(self.screen, CYAN, rect, 1, border_radius=3)
                
            self.dyn_btns.append((_RectBtn(rect), ("inv_toggle_sel", id(it_obj))))

        self.screen.set_clip(None)


    def _draw_manager_popup(self, mp):
        """Modal proativo de recomendação urgente do gerente."""
        rec = self.game.rec_importante_pendente
        if not rec: return
        
        # Dimming
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        
        mw, mh = 500, 240
        mx = (SCREEN_WIDTH - mw) // 2
        my = (SCREEN_HEIGHT - mh) // 2
        rect = pygame.Rect(mx, my, mw, mh)
        
        pygame.draw.rect(self.screen, (35, 30, 45), rect, border_radius=10)
        pygame.draw.rect(self.screen, CYAN, rect, 2, border_radius=10)
        
        # Cabeçalho
        title = f"CONSELHO DE {rec['gerente_nome']}"
        self.screen.blit(self.f_normal.render(title, True, CYAN), (mx + 20, my + 20))
        
        # Avatar do Gerente (Miniatura)
        self._draw_manager_unit(mx + 60, my + 80, self.game.get_gerente(rec["gerente_id"]), 0)
        
        # Mensagem
        lines = self._wrap_text(rec["msg"], mw - 140)
        for i, line in enumerate(lines):
            self.screen.blit(self.f_small.render(line, True, WHITE), (mx + 110, my + 60 + i*16))
            
        # Botões
        bx, by = mx + 110, my + mh - 60
        if rec.get("acao_tipo"):
            b_exec = Btn(bx, by, 160, 32, "Executar Ação", cor=(30, 80, 50))
            b_exec.update(mp); b_exec.draw(self.screen, self.f_normal)
            self.dyn_btns.append((b_exec, ("gerente_exec_rec", rec)))
            bx += 170
            
        b_close = Btn(bx, by, 120, 32, "Dispensar", cor=(60, 30, 30))
        b_close.update(mp); b_close.draw(self.screen, self.f_normal)
        self.dyn_btns.append((b_close, ("gerente_dimiss_rec", None)))

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
        consumiveis = [it["id"] for it in game.inventario_itens if it["id"] in ITEMS and ITEMS[it["id"]].get("consumivel")]
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
            filtrado = [it["id"] for it in inv_itens
                        if it["id"] in ITEMS and ITEMS[it["id"]]["slot"] == self.detalhe_slot_sel
                        and not ITEMS[it["id"]].get("consumivel", False)]
        else:
            filtrado = [it["id"] for it in inv_itens
                        if it["id"] in ITEMS and not ITEMS[it["id"]].get("consumivel", False)]

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
    # ABA 8: GUARDAS
    # ------------------------------------------------------------------

    def _tab_guardas(self, mp, cy):
        OX   = self.OX
        game = self.game
        W    = SCREEN_WIDTH - OX
        # Divide em dois: lista de guardas (esquerda) e compra/loja (direita)
        split = W // 2

        # ── LADO ESQUERDO — lista de guardas ────────────────────────────
        x = OX + 6; y = cy
        self.screen.blit(self.f_title.render("GUARDAS CONTRATADOS", True, CYAN), (x, y)); y += 16

        if not game.guardas:
            self.screen.blit(self.f_small.render("Nenhum guarda contratado.", True, DARK_GRAY), (x, y)); y += 14
        else:
            # Lista scrollable de guardas
            list_rect = pygame.Rect(x, cy, split - 10, BOTTOM_H - 10)
            self.screen.set_clip(list_rect)
            
            gw = split - 20
            yy = y - getattr(self, "guards_scroll", 0)
            for g in game.guardas:
                cor_r = g.cor_raridade()
                gy    = yy
                pygame.draw.rect(self.screen, (18,14,8), (x, gy, gw, 38), border_radius=4)
                pygame.draw.rect(self.screen, cor_r,     (x, gy, gw, 38), 1, border_radius=4)

                # Info básica
                gen = "M" if g.genero == "M" else "F"
                self.screen.blit(self.f_small.render(
                    f"{gen} {g.nome[:14]}  [{g.raridade}]",
                    True, cor_r), (x+4, gy+3))
                self.screen.blit(self.f_small.render(
                    f"F:{g.forca_efetiva()} R:{g.resistencia_efetiva()} A:{g.agilidade_efetiva()}",
                    True, GRAY), (x+4, gy+14))

                # Equipamentos
                eq_x = x + 4
                for slot in GUARD_SLOTS:
                    iid = g.equipamentos.get(slot)
                    cor = GUARD_ITEMS[iid].get("cor_visual", WHITE) if iid and iid in GUARD_ITEMS else DARK_GRAY
                    pygame.draw.circle(self.screen, cor, (eq_x + 5, gy + 28), 4)
                    eq_x += 16

                # Botões (ajustados para scroll)
                bdet = Btn(x+gw-95, gy+3, 44, 14, "Det.", cor=(35,50,70))
                bdet.update(mp); bdet.draw(self.screen, self.f_small)
                self.dyn_btns.append((bdet, ("guarda_detalhe", g.id)))

                bdis = Btn(x+gw-48,  gy+3, 44, 14, "Disp.", cor=(70,25,18))
                bdis.update(mp); bdis.draw(self.screen, self.f_small)
                self.dyn_btns.append((bdis, ("demitir_guarda", g.id)))

                yy += 42
            
            self.guards_scroll_max = max(0, (len(game.guardas) * 42) - (BOTTOM_H - 40))
            self.screen.set_clip(None)

        # Bônus coletivo
        if game.guardas:
            ar = game.guardas_ataque_reducao()
            rb = game.guardas_recuperacao_bonus()
            self.screen.blit(self.f_small.render(
                f"Reducao de ataque: {ar*100:.0f}%   Bonus recuperacao: {rb*100:.0f}%",
                True, GREEN), (x, cy + BOTTOM_H - 20))

        # ── LADO DIREITO — compra e loja ─────────────────────────────────
        rx2 = OX + split + 6; y2 = cy
        self.screen.blit(self.f_title.render("CONTRATAR GUARDA", True, LIGHT_BROWN), (rx2, y2)); y2 += 16

        for tier in GUARD_TIERS:
            cor_t = RARITY_COLORS.get(tier["raridade"], GRAY)
            pode  = (game.ouro >= tier["preco"] and len(game.guardas) < MAX_GUARDAS)
            pygame.draw.rect(self.screen, (20,14,8), (rx2, y2, split-12, 22), border_radius=3)
            pygame.draw.rect(self.screen, cor_t,     (rx2, y2, split-12, 22), 1, border_radius=3)
            self.screen.blit(self.f_small.render(
                f"{tier['nome']}  [{tier['attr_range'][0]}-{tier['attr_range'][1]} attrs]",
                True, cor_t), (rx2+4, y2+4))
            bcmp = Btn(rx2 + split - 90, y2+2, 80, 18, f"{tier['preco']}g",
                       cor=(45,70,25) if pode else (35,35,35), disabled=not pode)
            bcmp.update(mp); bcmp.draw(self.screen, self.f_small)
            self.dyn_btns.append((bcmp, ("comprar_guarda", tier["tipo"])))
            y2 += 26

        # Loja de itens de guardas
        pygame.draw.line(self.screen, PANEL_BDR, (rx2, y2), (rx2+split-12, y2), 1); y2 += 4
        self.screen.blit(self.f_title.render("LOJA DE EQUIPAMENTOS", True, LIGHT_BROWN), (rx2, y2)); y2 += 14

        if not game.loja_guard_itens:
            self.screen.blit(self.f_small.render("(sem itens em estoque)", True, DARK_GRAY), (rx2, y2))
        else:
            for it in game.loja_guard_itens[:5]:
                iid   = it["id"]
                preco = it["preco"]
                data  = GUARD_ITEMS.get(iid, {})
                cor_i = RARITY_COLORS.get(data.get("raridade","comum"), GRAY)
                pode_c= game.ouro >= preco
                self.screen.blit(self.f_small.render(
                    f"{data.get('nome',iid)[:22]}  [{data.get('raridade','?')}]",
                    True, cor_i), (rx2, y2))
                bci = Btn(rx2 + split - 90, y2-1, 80, 16, f"{preco}g",
                          cor=(45,70,25) if pode_c else (35,35,35), disabled=not pode_c)
                bci.update(mp); bci.draw(self.screen, self.f_small)
                self.dyn_btns.append((bci, ("comprar_guard_item", (iid, preco))))
                y2 += 16

        # Inventário de guardas
        n_gi = len(game.inventario_guard_itens)
        if n_gi:
            self.screen.blit(self.f_small.render(f"Inventário guardas: {n_gi} itens", True, CYAN),
                             (rx2, cy + BOTTOM_H - 20))

    # ------------------------------------------------------------------
    # MODAL: DETALHE DO GUARDA
    # ------------------------------------------------------------------

    def _draw_guarda_detail(self, mp):
        game = self.game
        g    = game.get_guarda(self.guarda_detalhe_id)
        if not g:
            self.guarda_detalhe_id = None
            return

        W, H = 720, 480
        px   = (SCREEN_WIDTH - W) // 2
        py   = (SCREEN_HEIGHT - H) // 2

        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        surf.fill((10, 7, 3, 240))
        self.screen.blit(surf, (px, py))
        cor_r = g.cor_raridade()
        pygame.draw.rect(self.screen, cor_r, (px, py, W, H), 2, border_radius=8)

        # Título
        gen_str = "Homem" if g.genero == "M" else "Mulher"
        self.screen.blit(self.f_title.render(
            f"{g.nome}  —  {gen_str} | Idade {g.idade:.0f} | {g.raridade}",
            True, cor_r), (px+10, py+8))

        # Col 1: stats
        COL1_X = px + 10
        y1     = py + 34
        self.screen.blit(self.f_small.render("ATRIBUTOS", True, LIGHT_BROWN), (COL1_X, y1)); y1 += 14
        for lbl, base, ef in [
            ("Forca",       g.forca,       g.forca_efetiva()),
            ("Resistencia", g.resistencia, g.resistencia_efetiva()),
            ("Agilidade",   g.agilidade,   g.agilidade_efetiva()),
        ]:
            bonus = ef - base
            b_txt = f"(+{bonus})" if bonus > 0 else ""
            self.screen.blit(self.f_small.render(
                f"{lbl}: {base} → {ef} {b_txt}", True, WHITE), (COL1_X, y1))
            y1 += 13

        y1 += 6
        # Contribuição aos guardas
        self.screen.blit(self.f_small.render("CONTRIBUIÇÃO", True, LIGHT_BROWN), (COL1_X, y1)); y1 += 14
        self.screen.blit(self.f_small.render(f"Red. Ataques:  -{g.agilidade_efetiva()/400*100:.1f}%", True, GREEN), (COL1_X, y1)); y1 += 13
        self.screen.blit(self.f_small.render(f"Bon. Recuper.: +{g.forca_efetiva()/300*100:.1f}%", True, CYAN), (COL1_X, y1)); y1 += 13
        poder = sum(g2.poder_total() for g2 in game.guardas)
        self.screen.blit(self.f_small.render(f"Poder Total: {poder}", True, GRAY), (COL1_X, y1)); y1 += 20
            
        # Col 2: slots de equipamento
        COL2_X = px + 210
        y2     = py + 34
        self.screen.blit(self.f_small.render("EQUIPAMENTOS (clique slot → seleciona)", True, LIGHT_BROWN), (COL2_X, y2)); y2 += 16

        for slot in GUARD_SLOTS:
            nome_slot = GUARD_SLOT_NOMES.get(slot, slot)
            iid       = g.equipamentos.get(slot)
            selecionado = (self.guarda_slot_sel == slot)

            # Cor de fundo
            slot_cor = DARK_BROWN if not selecionado else (60, 40, 10)
            pygame.draw.rect(self.screen, slot_cor, (COL2_X, y2, 200, 22), border_radius=4)
            if selecionado:
                pygame.draw.rect(self.screen, GOLD, (COL2_X, y2, 200, 22), 1, border_radius=4)

            if iid and iid in GUARD_ITEMS:
                idata = GUARD_ITEMS[iid]
                cor_i = RARITY_COLORS.get(idata.get("raridade","comum"), GRAY)
                self.screen.blit(self.f_small.render(
                    f"{nome_slot}: {idata['nome'][:16]}", True, cor_i), (COL2_X+4, y2+5))
                bdeq = Btn(COL2_X+142, y2+3, 54, 16, "Tir.", cor=(70,25,18))
                bdeq.update(mp); bdeq.draw(self.screen, self.f_small)
                self.dyn_btns.append((bdeq, ("deseq_guard", (g.id, slot))))
            else:
                self.screen.blit(self.f_small.render(f"{nome_slot}: — vazio —", True, DARK_GRAY), (COL2_X+4, y2+5))

            bsel = Btn(COL2_X+2, y2+3, 136, 16, "", cor=(0,0,0,0))  # área clicável invisível
            bsel.update(mp)
            self.dyn_btns.append((bsel, ("sel_guard_slot", slot)))
            y2 += 26

        # Col 3: inventário de guardas filtrado pelo slot selecionado
        COL3_X = px + 430
        y3     = py + 34
        self.screen.blit(self.f_small.render("INVENTÁRIO GUARDAS", True, LIGHT_BROWN), (COL3_X, y3)); y3 += 16

        filtrado = []
        for it_obj in game.inventario_guard_itens:
            # Defensivo: suporta tanto o novo sistema (dict) quanto o antigo (str) se houver falha na sanitização
            iid = it_obj["id"] if isinstance(it_obj, dict) else it_obj
            if iid in GUARD_ITEMS:
                if not self.guarda_slot_sel or GUARD_ITEMS[iid]["slot"] == self.guarda_slot_sel:
                    filtrado.append(iid)

        if not filtrado:
            self.screen.blit(self.f_small.render("(sem itens compatíveis)", True, DARK_GRAY), (COL3_X, y3))
        else:
            inv_w = W - (COL3_X - px) - 10
            for iid in filtrado[:10]:
                idata  = GUARD_ITEMS[iid]
                cor_i  = idata.get("cor_visual", WHITE)
                pygame.draw.rect(self.screen, (18,12,6), (COL3_X, y3, inv_w, 20), border_radius=3)
                self.screen.blit(self.f_small.render(f"{idata['nome'][:20]}", True, cor_i), (COL3_X+4, y3+4))
                beq = Btn(COL3_X + inv_w - 52, y3+2, 48, 16, "Equip.", cor=(35,60,22))
                beq.update(mp); beq.draw(self.screen, self.f_small)
                self.dyn_btns.append((beq, ("equip_guard", (g.id, iid))))
                y3 += 24

        # Auto-equipar
        bae = Btn(COL2_X, py+H-30, 100, 22, "Auto-Equipar", cor=(35,60,22))
        bae.update(mp); bae.draw(self.screen, self.f_small)
        self.dyn_btns.append((bae, ("auto_equip_guard", g.id)))

        # Fechar
        bfch = Btn(px+W-100, py+H-30, 90, 22, "[FECHAR]", cor=(70,20,20), cor_txt=RED)
        bfch.update(mp); bfch.draw(self.screen, self.f_normal)
        self.dyn_btns.append((bfch, ("fechar_guarda_detalhe", None)))

        pygame.draw.line(self.screen, PANEL_BDR, (COL2_X-5, py+28), (COL2_X-5, py+H-10), 1)
        pygame.draw.line(self.screen, PANEL_BDR, (COL3_X-5, py+28), (COL3_X-5, py+H-10), 1)

    def _draw_notifications_panel(self):
        """Painel lateral que exibe o histórico de notificações estruturado."""
        W, H = int(RIGHT_W), MAIN_H + TOP_H
        X = SCREEN_WIDTH - W
        Y = 0
        
        # Overlay de fundo
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        surf.fill((10, 10, 15, 250))
        self.screen.blit(surf, (X, Y))
        pygame.draw.line(self.screen, CYAN, (X, Y), (X, Y + H), 2)
        
        # Título
        self.screen.blit(self.f_normal.render("NOTIFICAÇÕES", True, CYAN), (X + 15, Y + 15))
        
        # Botão Fechar
        bfch = Btn(X + W - 40, Y + 10, 30, 30, "X", cor=(60,20,20))
        bfch.update(self._mouse_pos()); bfch.draw(self.screen, self.f_normal)
        self.dyn_btns.append((bfch, ("toggle_notifications", None)))
        
        # Lista de Notificações
        notifs = self.game.notificacoes_history
        ny = Y + 60
        for n in notifs[:20]: # Exibe as 20 mais recentes
            cor_urgencia = WHITE if n["urgencia"] < 2 else (GOLD if n["urgencia"] == 2 else RED)
            if not n["lida"]:
                # Destaque para não lidas
                pygame.draw.rect(self.screen, (30, 30, 50), (X + 5, ny - 2, W - 10, 38), border_radius=4)
            
            # Ícone baseado no tipo
            icon_txt = "!"
            if n["tipo"] == "death": icon_txt = "☠"
            elif n["tipo"] == "birth": icon_txt = "👶"
            elif n["tipo"] == "item": icon_txt = "💎"
            elif n["tipo"] == "manager": icon_txt = "👔"
            
            self.screen.blit(self.f_normal.render(icon_txt, True, n["cor"]), (X + 10, ny))
            
            # Texto da mensagem (wrap se necessário)
            msg_lines = self._wrap_text(n["msg"], W - 50)
            for i, line in enumerate(msg_lines[:2]):
                self.screen.blit(self.f_small.render(line, True, cor_urgencia), (X + 35, ny + i*13))
            
            # Botão invisível para marcar como lida
            notif_rect = _RectBtn(pygame.Rect(X + 5, ny - 2, W - 10, 38))
            self.dyn_btns.append((notif_rect, ("read_notif", n["id"])))
            
            ny += 45
            if ny > H - 20: break

    # ------------------------------------------------------------------
    # ABA 9: GERÊNCIA
    # ------------------------------------------------------------------

    def _tab_gerencia(self, mp, cy):
        OX   = self.OX
        game = self.game
        W    = SCREEN_WIDTH - OX
        split = W // 2

        # ── LADO ESQUERDO — gerentes contratados ────────────────────────
        x = OX + 6; y = cy
        self.screen.blit(self.f_title.render("CAPATAZES CONTRATADOS", True, GOLD), (x, y)); y += 16

        if not game.gerentes:
            self.screen.blit(self.f_small.render("Nenhum gerente contratado.", True, DARK_GRAY), (x, y))
            y += 14
        else:
            gw = split - 12
            for g in game.gerentes:
                cor_r = g.cor_raridade()
                gy    = y
                pygame.draw.rect(self.screen, (14,12,6), (x, gy, gw, 44), border_radius=4)
                pygame.draw.rect(self.screen, cor_r,     (x, gy, gw, 44), 1, border_radius=4)

                # Linha 1: nome + raridade
                self.screen.blit(self.f_small.render(
                    f"{g.nome[:20]}  [{g.raridade}]  ef:{g.eficiencia:.0%}",
                    True, cor_r), (x+4, gy+3))

                # Linha 2: autonomia + tipo
                auto_nome = MANAGER_AUTONOMIA_NOMES.get(g.autonomia, g.autonomia)
                self.screen.blit(self.f_small.render(
                    f"{g.tipo.capitalize()}  |  {auto_nome}  |  {g.acoes_realizadas} acoes",
                    True, GRAY), (x+4, gy+16))

                # Linha 3: ações/recs
                self.screen.blit(self.f_small.render(
                    f"Recs geradas: {g.recomendacoes_geradas}",
                    True, DARK_GRAY), (x+4, gy+28))

                # Botões
                bcfg = Btn(x+gw-100, gy+4, 46, 16, "Config", cor=(35,50,70))
                bcfg.update(mp); bcfg.draw(self.screen, self.f_small)
                self.dyn_btns.append((bcfg, ("abrir_gerente_modal", g.id)))

                bdem = Btn(x+gw-50, gy+4, 44, 16, "Dem.", cor=(70,25,18))
                bdem.update(mp); bdem.draw(self.screen, self.f_small)
                self.dyn_btns.append((bdem, ("demitir_gerente", g.id)))

                y += 48
                if y > cy + BOTTOM_H - 30:
                    break

        # ── FILA DE RECOMENDAÇÕES ────────────────────────────────────────
        if game.gerentes:
            fila = game.fila_recomendacoes
            urgencia_cor = {1: GRAY, 2: ORANGE, 3: RED}
            if not fila:
                self.screen.blit(self.f_small.render("Nenhuma recomendação pendente.", True, DARK_GRAY),
                                 (x, y)); y += 13
            else:
                self.screen.blit(self.f_small.render(f"RECOMENDAÇÕES ({len(fila)}):", True, LIGHT_BROWN),
                                 (x, y)); y += 13
                for i, rec in enumerate(fila[:4]):
                    if y + 26 > cy + BOTTOM_H - 6:
                        break
                    urg  = rec.get("urgencia", 1)
                    cor  = rec.get("cor", urgencia_cor.get(urg, GRAY))
                    msg  = rec.get("msg", "")[:55]
                    pygame.draw.rect(self.screen, (16,12,6), (x, y, split-12, 24), border_radius=3)
                    pygame.draw.rect(self.screen, cor,       (x, y, split-12, 24), 1, border_radius=3)
                    self.screen.blit(self.f_small.render(msg, True, cor), (x+4, y+4))

                    # Botão Executar (só se tem acao_tipo)
                    if rec.get("acao_tipo"):
                        bex = Btn(x + split - 130, y+4, 56, 16, "Exec.", cor=(35,60,22))
                        bex.update(mp); bex.draw(self.screen, self.f_small)
                        self.dyn_btns.append((bex, ("exec_rec", i)))

                    big = Btn(x + split - 70, y+4, 52, 16, "Ign.", cor=(60,25,18))
                    big.update(mp); big.draw(self.screen, self.f_small)
                    self.dyn_btns.append((big, ("ignorar_rec", i)))

                    y += 27

        # ── LADO DIREITO — contratar ─────────────────────────────────────
        rx2 = OX + split + 6; y2 = cy
        self.screen.blit(self.f_title.render("CONTRATAR GERENTE", True, LIGHT_BROWN), (rx2, y2)); y2 += 16

        slots_livres = MAX_GERENTES - len(game.gerentes)
        self.screen.blit(self.f_small.render(
            f"Slots: {len(game.gerentes)}/{MAX_GERENTES}",
            True, CYAN), (rx2, y2)); y2 += 14

        for tier in MANAGER_TIERS:
            cor_t = RARITY_COLORS.get(tier["raridade"], GRAY)
            pode  = (game.ouro >= tier["preco"] and slots_livres > 0)
            already = any(g.tipo == tier["tipo"] for g in game.gerentes)
            disabled = not pode or already

            rw = split - 16
            pygame.draw.rect(self.screen, (20,14,8), (rx2, y2, rw, 30), border_radius=3)
            pygame.draw.rect(self.screen, cor_t,     (rx2, y2, rw, 30), 1, border_radius=3)

            self.screen.blit(self.f_small.render(
                f"{tier['nome']}  (ef {tier['eficiencia']:.0%})", True, cor_t), (rx2+4, y2+4))
            self.screen.blit(self.f_small.render(tier["desc"][:45], True, DARK_GRAY), (rx2+4, y2+17))

            btn_lbl = "Já tem" if already else f"{tier['preco']//1000}k g"
            bcmp = Btn(rx2 + rw - 74, y2+6, 68, 18, btn_lbl,
                       cor=(45,70,25) if pode and not already else (35,35,35), disabled=disabled)
            bcmp.update(mp); bcmp.draw(self.screen, self.f_small)
            self.dyn_btns.append((bcmp, ("contratar_gerente", tier["tipo"])))

            y2 += 34

        # Info geral
        if game.gerentes:
            pygame.draw.line(self.screen, PANEL_BDR, (rx2, y2), (rx2+split-16, y2), 1); y2 += 6
            total_recs = sum(g.recomendacoes_geradas for g in game.gerentes)
            total_acao = sum(g.acoes_realizadas       for g in game.gerentes)
            self.screen.blit(self.f_small.render(
                f"Total recomendações: {total_recs}  |  Ações auto: {total_acao}",
                True, GRAY), (rx2, y2))

    # ------------------------------------------------------------------
    # MODAL: CONFIG DO GERENTE
    # ------------------------------------------------------------------

    def _draw_gerente_modal(self, mp):
        game = self.game
        g    = game.get_gerente(self.gerente_modal_id)
        if not g:
            self.gerente_modal_id = None
            return

        W, H = 680, 480
        px   = (SCREEN_WIDTH - W) // 2
        py   = (SCREEN_HEIGHT - H) // 2

        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        surf.fill((10, 8, 2, 245))
        self.screen.blit(surf, (px, py))
        cor_r = g.cor_raridade()
        pygame.draw.rect(self.screen, cor_r, (px, py, W, H), 2, border_radius=8)

        # Título
        self.screen.blit(self.f_title.render(
            f"{g.nome}  [{g.raridade}]  ef:{g.eficiencia:.0%}",
            True, cor_r), (px+10, py+8))

        # ── AUTONOMIA ──────────────────────────────────────────────────
        y = py + 30
        self.screen.blit(self.f_small.render("MODO DE AUTONOMIA:", True, LIGHT_BROWN), (px+10, y)); y += 14
        for modo in MANAGER_AUTONOMIA:
            cor_btn = GOLD if g.autonomia == modo else (35,35,35)
            btn_auto = Btn(px+10 + MANAGER_AUTONOMIA.index(modo)*140, y, 132, 18,
                           MANAGER_AUTONOMIA_NOMES[modo], cor=cor_btn)
            btn_auto.update(mp); btn_auto.draw(self.screen, self.f_small)
            self.dyn_btns.append((btn_auto, ("set_autonomia", (g.id, modo))))
        y += 24

        pygame.draw.line(self.screen, PANEL_BDR, (px+8, y), (px+W-8, y), 1); y += 6

        # ── CONFIGURAÇÕES ──────────────────────────────────────────────
        # 2 colunas
        C1X = px + 10
        C2X = px + W // 2 + 10
        cy1 = y
        cy2 = y

        def toggle_row(cx, cy, lbl, attr, val):
            """Desenha linha toggle. Retorna cy + altura."""
            ativo = getattr(g, attr)
            cor   = GREEN if ativo else DARK_GRAY
            self.screen.blit(self.f_small.render(lbl, True, WHITE), (cx, cy+2))
            btxt = "[ON]" if ativo else "[OFF]"
            bcor = (30,60,22) if ativo else (50,20,20)
            btn = Btn(cx + 200, cy, 44, 14, btxt, cor=bcor)
            btn.update(mp); btn.draw(self.screen, self.f_small)
            self.dyn_btns.append((btn, ("toggle_cfg", (g.id, attr))))
            return cy + 18

        def val_row(cx, cy, lbl, attr, mn, mx, step):
            """Linha com valor numérico ajustável. Retorna cy + altura."""
            val = getattr(g, attr)
            self.screen.blit(self.f_small.render(f"{lbl}: {val}", True, WHITE), (cx, cy+2))
            bm = Btn(cx + 200, cy, 18, 14, "-", cor=(60,30,20))
            bp = Btn(cx + 220, cy, 18, 14, "+", cor=(30,60,20))
            bm.update(mp); bm.draw(self.screen, self.f_small)
            bp.update(mp); bp.draw(self.screen, self.f_small)
            self.dyn_btns.append((bm, ("adj_cfg", (g.id, attr, -step, mn, mx))))
            self.dyn_btns.append((bp, ("adj_cfg", (g.id, attr,  step, mn, mx))))
            return cy + 18

        # Coluna 1: venda / descanso
        self.screen.blit(self.f_small.render("VENDA AUTOMÁTICA", True, GOLD), (C1X, cy1)); cy1 += 14
        cy1 = toggle_row(C1X, cy1, "Vender idosos",   "cfg_vender_idosos",  None)
        cy1 = val_row   (C1X, cy1, "Idade mín. venda","cfg_vender_idade_min", 30, 80, 5)
        cy1 = toggle_row(C1X, cy1, "Vender fracos",   "cfg_vender_fracos",   None)
        cy1 = val_row   (C1X, cy1, "Attr máx (fraco)","cfg_vender_attr_max",  5, 60, 5)
        cy1 = toggle_row(C1X, cy1, "Vender doentes",  "cfg_vender_doentes",  None)
        cy1 += 6
        self.screen.blit(self.f_small.render("DESCANSO", True, GOLD), (C1X, cy1)); cy1 += 14
        cy1 = toggle_row(C1X, cy1, "Descanso auto",   "cfg_descanso_auto",   None)
        cy1 = val_row   (C1X, cy1, "Stamina mín.","cfg_descanso_stamina",    5, 40, 5)

        # Coluna 2: compra / outros
        self.screen.blit(self.f_small.render("COMPRA AUTOMÁTICA", True, GOLD), (C2X, cy2)); cy2 += 14
        cy2 = toggle_row(C2X, cy2, "Comprar auto",    "cfg_comprar_auto",    None)
        cy2 = val_row   (C2X, cy2, "Attr mín. compra","cfg_comprar_attr_min", 20, 80, 5)
        cy2 = val_row   (C2X, cy2, "Idade máx. compra","cfg_comprar_idade_max",18, 60, 2)
        cy2 += 6
        self.screen.blit(self.f_small.render("OUTROS", True, GOLD), (C2X, cy2)); cy2 += 14
        cy2 = toggle_row(C2X, cy2, "Auto-equip servos","cfg_equip_auto",     None)
        cy2 = toggle_row(C2X, cy2, "Auto-equip guardas","cfg_guardas_auto",  None)

        # ── ESTATÍSTICAS ───────────────────────────────────────────────
        ey = py + H - 50
        pygame.draw.line(self.screen, PANEL_BDR, (px+8, ey), (px+W-8, ey), 1); ey += 6
        self.screen.blit(self.f_small.render(
            f"Intervalo análise: {g.check_interval:.0f}s  |  "
            f"Recomendações: {g.recomendacoes_geradas}  |  "
            f"Ações auto: {g.acoes_realizadas}",
            True, GRAY), (px+10, ey))

        # ── FECHAR ─────────────────────────────────────────────────────
        bfch = Btn(px+W-100, py+H-28, 90, 22, "[FECHAR]", cor=(70,20,20), cor_txt=RED)
        bfch.update(mp); bfch.draw(self.screen, self.f_normal)
        self.dyn_btns.append((bfch, ("fechar_gerente_modal", None)))

    # ------------------------------------------------------------------
    # MODAL: VENDEDOR AMBULANTE
    # ------------------------------------------------------------------

    def _draw_vendedor_modal(self, mp):
        # Bloqueio de fundo (Overlay)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        game = self.game
        v    = game.vendedor_atual
        if not v:
            self.show_vendedor = False
            return

        qual_cor = {
            "barato": GRAY, "raro": BLUE, "ruim": RED, "maldito": PURPLE,
        }.get(v["qualidade"], GOLD)
        qual_nomes = {
            "barato": "Mercador de Bugigangas",
            "raro":   "Comerciante Raro",
            "ruim":   "Mascate Duvidoso",
            "maldito":"Vendedor das Sombras",
        }

        W, H  = 560, 310
        px    = (SCREEN_WIDTH - W) // 2
        py    = (SCREEN_HEIGHT - H) // 2

        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        surf.fill((8, 5, 14, 245))
        self.screen.blit(surf, (px, py))
        pygame.draw.rect(self.screen, qual_cor, (px, py, W, H), 2, border_radius=8)

        self.screen.blit(self.f_title.render(
            f"  {qual_nomes.get(v['qualidade'],'Vendedor')}  —  {v['timer']:.0f}s restantes",
            True, qual_cor), (px+10, py+8))
        
        # Saldo de Ouro Interno
        self.screen.blit(self.f_normal.render(f"Seu Ouro: {game.ouro}g", True, GOLD), (px+W-180, py+10))

        if not v["itens"]:
            self.screen.blit(self.f_normal.render("Sem itens disponíveis.", True, GRAY), (px+20, py+60))
        else:
            item_w = (W - 20) // len(v["itens"])
            all_vendor_items = {**ITEMS, **GUARD_ITEMS}
            for i, it in enumerate(v["itens"]):
                data   = all_vendor_items.get(it["id"], {})
                cor_i  = RARITY_COLORS.get(data.get("raridade","comum"), GRAY)
                ix     = px + 10 + i * item_w
                iy     = py + 34

                pygame.draw.rect(self.screen, (20,14,30), (ix, iy, item_w-8, H-70), border_radius=6)
                pygame.draw.rect(self.screen, cor_i,      (ix, iy, item_w-8, H-70), 1, border_radius=6)

                nome = data.get("nome", it["id"])
                for j, parte in enumerate(self._wrap(nome, item_w-16, self.f_small)):
                    self.screen.blit(self.f_small.render(parte, True, cor_i), (ix+4, iy+4+j*13))

                tipo_tag = "[GUARDA]" if it["tipo"]=="guard" else "[SERVO]"
                self.screen.blit(self.f_small.render(tipo_tag, True, CYAN), (ix+4, iy+34))
                rar = data.get("raridade","?")
                self.screen.blit(self.f_small.render(rar, True, cor_i), (ix+4, iy+48))

                # Bônus
                bonus_y = iy + 62
                for attr, val in list(data.get("bonus",{}).items())[:4]:
                    self.screen.blit(self.f_small.render(f"{attr}:{int(val):+d}", True, GREEN if val>0 else RED),
                                     (ix+4, bonus_y)); bonus_y += 12

                pode_c = game.ouro >= it["preco"]
                bcv = Btn(ix+4, iy+H-110, item_w-16, 22, f"Comprar {it['preco']}g",
                          cor=(45,70,22) if pode_c else (35,35,35), disabled=not pode_c)
                bcv.update(mp); bcv.draw(self.screen, self.f_normal)
                self.dyn_btns.append((bcv, ("comprar_vendedor", (it["id"], it["preco"]))))

        bfch = Btn(px+W-100, py+H-30, 90, 22, "[FECHAR]", cor=(70,20,20), cor_txt=RED)
        bfch.update(mp); bfch.draw(self.screen, self.f_normal)
        self.dyn_btns.append((bfch, ("fechar_vendedor", None)))

    @staticmethod
    def _wrap(text: str, max_px: int, font) -> list[str]:
        words  = text.split()
        lines  = []
        line   = ""
        for w in words:
            test = line + w + " "
            if font.size(test)[0] <= max_px:
                line = test
            else:
                if line:
                    lines.append(line.strip())
                line = w + " "
        if line:
            lines.append(line.strip())
        return lines or [""]

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
        # Atalho Global para Captura de Tela
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F12:
            import os
            from datetime import datetime
            path = os.path.join(os.getcwd(), f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.save_screenshot(path)
            return

        ev = self._normalize_event(ev)
        mp   = self._mouse_pos()

        if self.state == "login":
            self._handle_login_events(ev)
            return

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
            if game.rec_importante_pendente:
                return 
            if game.notificacao:
                # Só limpa se o clique não atingiu nenhum botão dinâmico anterior (como o do vendedor)
                # Na verdade, a notificação central deve ser limpa por qualquer clique que NÃO seja em modal.
                if not (self.show_vendedor or self.slave_detalhe_id or self.guarda_detalhe_id or self.gerente_modal_id):
                    game.notificacao = None
                    return
            if self.show_tutorial:
                self.show_tutorial = False
                game.primeiro_jogo = False
                return

        # Se o modal de detalhe estiver aberto, ESC fecha
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.show_vendedor:
                self.show_vendedor = False
                return
            if self.gerente_modal_id is not None:
                self.gerente_modal_id = None
                return
            if self.guarda_detalhe_id is not None:
                self.guarda_detalhe_id = None
                self.guarda_slot_sel   = None
                return
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

        if ev.type == pygame.MOUSEWHEEL and self.r_bottom.collidepoint(mp) and self.tab == 8:
            self.guards_scroll = max(0, min(getattr(self, "guards_scroll_max", 0), self.guards_scroll - ev.y * 30))

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
        if self.btn_bell.clicked(ev):
            self.show_notifications = not self.show_notifications
            # Resetar scroll ao abrir
            if self.show_notifications: self.notif_scroll = 0
            return
            
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
                if i == 10: self.ranking_data = None # Forçar recarga

        for btn, (acao, param) in reversed(self.dyn_btns):
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

        elif acao == "refresh_ranking":
            if not self.ranking_loading:
                self.ranking_loading = True
                self.game.worker.add_task("ranking", (10,), callback=self._on_ranking_loaded)
                game.log_add("Atualizando ranking em background...", CYAN)

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

        # ── Guardas ──────────────────────────────────────────────────────
        elif acao == "guarda_detalhe":
            self.guarda_detalhe_id = param
            self.guarda_slot_sel   = None

        elif acao == "fechar_guarda_detalhe":
            self.guarda_detalhe_id = None
            self.guarda_slot_sel   = None

        elif acao == "sel_guard_slot":
            self.guarda_slot_sel = param if self.guarda_slot_sel != param else None

        elif acao == "comprar_guarda":
            ok, msg = game.comprar_guarda(param)
            game.log_add(msg, CYAN if ok else RED)

        elif acao == "demitir_guarda":
            ok, msg = game.demitir_guarda(param)
            game.log_add(msg, ORANGE if ok else RED)
            if ok and self.guarda_detalhe_id == param:
                self.guarda_detalhe_id = None

        elif acao == "equip_guard":
            gid, iid = param
            ok, msg  = game.equipar_item_guarda(gid, iid)
            game.log_add(msg, CYAN if ok else RED)

        elif acao == "deseq_guard":
            gid, slot = param
            ok, msg   = game.desequipar_item_guarda(gid, slot)
            game.log_add(msg, GRAY if ok else RED)

        elif acao == "auto_equip_guard":
            ok, msg = game.auto_equipar_guarda(param)
            game.log_add(msg, GREEN if ok else GRAY)

        elif acao == "comprar_guard_item":
            iid, preco = param
            ok, msg    = game.comprar_item_guarda_loja(iid, preco)
            game.log_add(msg, GOLD if ok else RED)

        # ── Vendedor ─────────────────────────────────────────────────────
        elif acao == "abrir_vendedor":
            self.show_vendedor = True

        elif acao == "fechar_vendedor":
            self.show_vendedor = False

        elif acao == "comprar_vendedor":
            iid, preco = param
            ok, msg    = game.comprar_item_vendedor(iid, preco)
            game.log_add(msg, GOLD if ok else RED)

        # ── Gerentes ──────────────────────────────────────────────────────
        elif acao == "contratar_gerente":
            ok, msg = game.contratar_gerente(param)
            game.log_add(msg, GOLD if ok else RED)

        elif acao == "demitir_gerente":
            ok, msg = game.demitir_gerente(param)
            game.log_add(msg, ORANGE if ok else RED)
            if ok and self.gerente_modal_id == param:
                self.gerente_modal_id = None

        elif acao == "abrir_gerente_modal":
            self.gerente_modal_id = param

        elif acao == "fechar_gerente_modal":
            self.gerente_modal_id = None

        elif acao == "set_autonomia":
            gid, modo = param
            ok, msg = game.set_autonomia_gerente(gid, modo)
            game.log_add(msg, CYAN if ok else RED)

        elif acao == "toggle_cfg":
            gid, attr = param
            g = game.get_gerente(gid)
            if g and hasattr(g, attr):
                setattr(g, attr, not getattr(g, attr))

        elif acao == "adj_cfg":
            gid, attr, delta, mn, mx = param
            g = game.get_gerente(gid)
            if g and hasattr(g, attr):
                setattr(g, attr, max(mn, min(mx, getattr(g, attr) + delta)))

        elif acao == "exec_rec":
            ok, msg = game.executar_recomendacao(param)
            game.log_add(msg, GREEN if ok else RED)

        elif acao == "ignorar_rec":
            game.ignorar_recomendacao(param)
            game.log_add("Recomendação ignorada.", GRAY)

        elif acao == "gerente_exec_rec":
            rec = param
            # Executa usando o método existente no GameManager
            executado = game._executar_acao_rec(rec)
            if executado:
                game.log_add(f"Ação executada: {rec['msg']}", GREEN)
                # Remove da fila original
                game.fila_recomendacoes = [r for r in game.fila_recomendacoes if r != rec]
            game.rec_importante_pendente = None

        elif acao == "gerente_dimiss_rec":
            game.rec_importante_pendente = None

        elif acao == "toggle_notifications":
            self.show_notifications = not self.show_notifications
            
        elif acao == "toggle_stat_view":
            self.stat_view = 1 if getattr(self, "stat_view", 0) == 0 else 0
            
        elif acao == "set_mortality_window":
            self.mortality_window = param

        elif acao == "read_notif":
            notif_id = param
            for n in game.notificacoes_history:
                if n["id"] == notif_id:
                    n["lida"] = True
                    break

        elif acao == "inv_toggle_sel":
            obj_id = param
            if obj_id in self.inv_selecionados:
                self.inv_selecionados.remove(obj_id)
            else:
                self.inv_selecionados.add(obj_id)
                
        elif acao == "inv_mass_delete":
            to_delete_objs = []
            inv = self.game.inventario_itens
            
            if param == "del_comum":
                for it_obj in inv:
                    iid = it_obj["id"] if isinstance(it_obj, dict) else it_obj
                    if iid in ITEMS and ITEMS[iid]["raridade"] == "comum":
                        to_delete_objs.append(it_obj)
            elif param == "del_incomum":
                for it_obj in inv:
                    iid = it_obj["id"] if isinstance(it_obj, dict) else it_obj
                    if iid in ITEMS and ITEMS[iid]["raridade"] == "incomum":
                        to_delete_objs.append(it_obj)
            elif param == "del_sel":
                # Filtra o inventário mantendo apenas os NÃO selecionados
                to_delete_objs = [it for it in inv if id(it) in self.inv_selecionados]
                self.inv_selecionados.clear()
            elif param == "del_unsel":
                # Filtra o inventário mantendo apenas os selecionados
                to_delete_objs = [it for it in inv if id(it) not in self.inv_selecionados]
                self.inv_selecionados.clear()
                
            if to_delete_objs:
                new_inv = [it for it in inv if it not in to_delete_objs]
                self.game.inventario_itens = new_inv
                self.game.log_add(f"{len(to_delete_objs)} itens deletados do inventário.", RED)
                self.inv_selecionados.clear()

        elif acao == "toggle_stat_view":
            self.stat_view = 1 if getattr(self, "stat_view", 0) == 0 else 0
            
        elif acao == "set_mortality_window":
            self.mortality_window = param

    def _draw_mortality_chart(self, x, y):
        """Desenha um gráfico de barras simples com as causas de morte."""
        now = self.game.tempo_jogo
        windows = [900, 1800, 3600] # 15m, 30m, 1h
        w_idx = getattr(self, "mortality_window", 0)
        max_t = windows[w_idx]
        
        # Filtra histórico
        recente = [h for h in self.game.mortalidade_history if now - h["t"] <= max_t]
        
        # Seletor de tempo
        labels = ["15m", "30m", "1h"]
        for i, lbl in enumerate(labels):
            bx = x + i * 45
            b = Btn(bx, y, 40, 16, lbl, cor=(40, 50, 60) if w_idx == i else (20, 25, 30))
            b.update(self._mouse_pos()); b.draw(self.screen, self.f_tiny)
            self.dyn_btns.append((b, ("set_mortality_window", i)))
        y += 22
        
        if notrecente := [h for h in self.game.mortalidade_history if now - h["t"] <= max_t]:
            # Reutiliza o filtro para garantir consistência
            pass
            
        if not recente:
            self.screen.blit(self.f_small.render("Sem dados p/ este período.", True, (100, 100, 100)), (x, y))
            return
            
        # Agrupa por causa
        contagem = {}
        for h in recente:
            c = h["causa"]
            contagem[c] = contagem.get(c, 0) + 1
            
        total = len(recente)
        causas_sorted = sorted(contagem.items(), key=lambda i: i[1], reverse=True)
        
        # Desenha barras
        bar_max_w = RIGHT_W - 40
        for causa, qtd in causas_sorted[:6]:
            pct = qtd / total
            # Barra
            pygame.draw.rect(self.screen, (30, 20, 10), (x, y, bar_max_w, 14))
            c_low = causa.lower()
            bar_cor = (200, 50, 50) if "mald" in c_low or "acid" in c_low else (200, 150, 50)
            pygame.draw.rect(self.screen, bar_cor, (x, y, int(bar_max_w * pct), 14))
            txt = f"{causa[:12]}: {qtd} ({pct*100:.0f}%)"
            self.screen.blit(self.f_tiny.render(txt, True, (255, 255, 255)), (x + 4, y + 1))
            y += 16

    def notify_mining(self, escravo_id: int, cor):
        """Chamado pelo game loop quando um escravo acabou de minerar."""
        self._flash[escravo_id] = 0.28
        game = self.game
        e    = game.get_escravo(escravo_id)
        if e and hasattr(e, "anim_x"):
            self.spawn_particles(e.anim_x, e.anim_y, cor)

    def _draw_toasts(self):
        """Desenha notificações temporárias (toasts) sobre a barra lateral de logs."""
        now = self.game.tempo_jogo
        toasts = [n for n in self.game.notificacoes_history if now - n["tempo"] < 5.0]
        
        if not toasts:
            return
            
        toast_w = self.OX - 10
        tx = 5
        ty = 25
        
        for n in toasts[:4]:  # Mostra no máximo as 4 últimas
            msg_lines = self._wrap_text(n["msg"], toast_w - 30)
            toast_h = 20 + len(msg_lines) * 14
            
            # Fundo mais opaco para legibilidade sobre o log
            s = pygame.Surface((toast_w, toast_h), pygame.SRCALPHA)
            s.fill((15, 12, 20, 240))
            self.screen.blit(s, (tx, ty))
            pygame.draw.rect(self.screen, n["cor"], (tx, ty, toast_w, toast_h), 1, border_radius=4)
            
            # Ícone
            self.screen.blit(self.f_normal.render("!", True, n["cor"]), (tx + 4, ty + 2))
            
            # Mensagens
            for i, line in enumerate(msg_lines):
                self.screen.blit(self.f_small.render(line.strip(), True, WHITE), (tx + 22, ty + 5 + i*14))
            
            ty += (toast_h + 4)

    def save_screenshot(self, filename: str):
        """Salva a superfície de renderização atual como uma imagem PNG."""
        try:
            pygame.image.save(self.screen, filename)
            self.game.log_add(f"[SISTEMA] Captura salva: {filename}", (0, 255, 255))
        except Exception as e:
            self.game.log_add(f"[ERRO] Falha ao capturar tela: {e}", (255, 0, 0))


# ============================================================
# HELPER INTERNO — botão baseado em Rect simples
# ============================================================

    def _handle_login_events(self, ev):
        """Trata teclado e cliques na tela de login."""
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_TAB:
                self.login_focus = (self.login_focus + 1) % 2
            elif ev.key == pygame.K_BACKSPACE:
                if self.login_focus == 0: self.login_user = self.login_user[:-1]
                else: self.login_pass = self.login_pass[:-1]
            elif ev.key == pygame.K_RETURN:
                self._action_login()
            else:
                if len(ev.unicode) > 0 and ev.unicode.isprintable():
                    if self.login_focus == 0: self.login_user += ev.unicode
                    else: self.login_pass += ev.unicode

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for btn, (act, param) in self.dyn_btns:
                if btn.clicked(ev):
                    self._handle_login_action(act)

    def _handle_login_action(self, act):
        if act == "focus_user": self.login_focus = 0
        elif act == "focus_pass": self.login_focus = 1
        elif act == "login": self._action_login()
        elif act == "register": self._action_register()

    def _action_login(self):
        if self.login_loading: return
        self.login_msg = "Conectando..."
        self.login_loading = True
        self.game.worker.add_task("login", (self.login_user, self.login_pass), callback=self._on_login_done)

    def _on_login_done(self, result):
        self.login_loading = False
        if not result:
            self.login_msg = "Erro de conexão com o servidor."
            return
            
        succ, msg, pid = result
        self.login_msg = msg
        if succ:
            self.game.player_id = pid
            self.game.username = self.login_user
            # Sincroniza estado inicial em background (opcional mas mantemos síncrono aqui por simplicidade no start)
            online_state = self.game.storage.load_game_state(pid)
            if online_state:
                self.game._apply_loaded_state(online_state)
                self.login_msg = "Sincronizado com a nuvem!"
            else:
                self.login_msg = "Iniciando nova jornada online..."
            
            self.state = "game"
            self.show_tutorial = False

    def _action_register(self):
        if self.login_loading: return
        self.login_msg = "Registrando..."
        self.login_loading = True
        self.game.worker.add_task("register", (self.login_user, self.login_pass), callback=self._on_register_done)

    def _on_register_done(self, result):
        self.login_loading = False
        if not result:
            self.login_msg = "Erro ao registrar (conexão)."
            return
        succ, msg = result
        self.login_msg = msg

    def _draw_login_screen_bg(self):
        # Fundo temático escuro
        self.screen.fill((10, 8, 12))
        # Desenha algumas "pedras" procedurais no fundo para ambiência
        rng = random.Random(999)
        for _ in range(40):
            x, y = rng.randint(0, SCREEN_WIDTH), rng.randint(0, SCREEN_HEIGHT)
            sz = rng.randint(20, 100)
            pygame.draw.ellipse(self.screen, (20, 15, 25), (x, y, sz, sz//2))

    def _draw_login_form(self, mp):
        cw, ch = 360, 420
        cx, cy = (SCREEN_WIDTH - cw) // 2, (SCREEN_HEIGHT - ch) // 2
        
        # Painel central
        pygame.draw.rect(self.screen, PANEL_BG, (cx, cy, cw, ch), border_radius=12)
        pygame.draw.rect(self.screen, PANEL_BDR, (cx, cy, cw, ch), 2, border_radius=12)
        
        # Título
        title_surf = self.f_big.render("MINA DOS ESCRAVOS", True, GOLD)
        self.screen.blit(title_surf, (cx + (cw - title_surf.get_width())//2, cy + 30))
        sub_surf = self.f_small.render("Acesso ao Cofre Real", True, GRAY)
        self.screen.blit(sub_surf, (cx + (cw - sub_surf.get_width())//2, cy + 60))

        # Inputs
        curr_y = cy + 110
        for i, (label, val) in enumerate([("Usuário", self.login_user), ("Senha", "*" * len(self.login_pass))]):
            # Label
            self.screen.blit(self.f_normal.render(label, True, LIGHT_BROWN), (cx + 40, curr_y))
            curr_y += 22
            
            # Box
            box_rect = pygame.Rect(cx + 40, curr_y, cw - 80, 36)
            is_focused = (self.login_focus == i)
            cor_box = (40, 40, 60) if is_focused else (25, 25, 35)
            pygame.draw.rect(self.screen, cor_box, box_rect, border_radius=6)
            pygame.draw.rect(self.screen, GOLD if is_focused else PANEL_BDR, box_rect, 1, border_radius=6)
            
            txt_surf = self.f_normal.render(val + ("|" if is_focused and (pygame.time.get_ticks() // 500) % 2 == 0 else ""), True, WHITE)
            self.screen.blit(txt_surf, (box_rect.x + 10, box_rect.y + (box_rect.h - txt_surf.get_height())//2))
            
            # Botão invisível para foco
            self.dyn_btns.append((_RectBtn(box_rect), ("focus_user" if i == 0 else "focus_pass", None)))
            curr_y += 55

        # Mensagem de Erro/Status
        if self.login_msg:
            msg_surf = self.f_small.render(self.login_msg, True, RED if "Erro" in self.login_msg or "incorreta" in self.login_msg else ORANGE)
            self.screen.blit(msg_surf, (cx + (cw - msg_surf.get_width())//2, curr_y))
        
        # Botões
        curr_y += 35
        btn_login = Btn(cx + 40, curr_y, cw - 80, 44, "ENTRAR", cor=DARK_GREEN)
        btn_login.update(mp); btn_login.draw(self.screen, self.f_title)
        self.dyn_btns.append((btn_login, ("login", None)))
        
        curr_y += 60
        btn_reg = Btn(cx + 80, curr_y, cw - 160, 32, "Registrar Novo", cor=MED_BROWN)
        btn_reg.update(mp); btn_reg.draw(self.screen, self.f_normal)
        self.dyn_btns.append((btn_reg, ("register", None)))

        curr_y += 50
        hint = self.f_tiny.render("Salva e sincroniza automaticamente na nuvem.", True, DARK_GRAY)
        self.screen.blit(hint, (cx + (cw - hint.get_width())//2, curr_y))

    def _on_ranking_loaded(self, data):
        self.ranking_data = data
        self.ranking_loading = False

    def _tab_ranking(self, mp, cy):
        """Aba especial para mostrar o Cloud Ranking."""
        if not self.ranking_data and not self.ranking_loading:
            self.ranking_loading = True
            # Busca em background
            self.game.worker.add_task("ranking", (10,), callback=self._on_ranking_loaded)
        
        OX = self.OX
        tx, ty = OX + 20, cy + 10
        
        self.screen.blit(self.f_title.render("Ranking Global dos Magnatas", True, GOLD), (tx, ty))
        
        if self.ranking_loading:
            self.screen.blit(self.f_normal.render("Sincronizando com a Nuvem...", True, GRAY), (tx, ty + 40))
            return

        ty += 30
        
        # Colunas: Top Dinheiro | Top Tempo
        col_w = (SCREEN_WIDTH - OX) // 2 - 20
        
        def draw_list(title, items, start_x, start_y, is_money=True):
            self.screen.blit(self.f_normal.render(title, True, SILVER if not is_money else GOLD), (start_x, start_y))
            start_y += 22
            for i, (uname, val) in enumerate(items):
                color = WHITE if i > 2 else (GOLD if i == 0 else (SILVER if i == 1 else (205, 127, 50)))
                pref = f"{i+1}. "
                name_surf = self.f_small.render(f"{pref}{uname}", True, color)
                self.screen.blit(name_surf, (start_x, start_y))
                
                val_str = f"${val:,.0f}" if is_money else f"{val/3600:.1f}h"
                val_surf = self.f_small.render(val_str, True, color)
                self.screen.blit(val_surf, (start_x + 140, start_y))
                start_y += 18

        if self.ranking_data:
            draw_list("Mais Ricos", self.ranking_data["money"][:6], tx, ty, True)
            draw_list("Mais Veteranos", self.ranking_data["time"][:6], tx + col_w, ty, False)

        # Botão de atualizar
        btn_refresh = Btn(tx, cy + BOTTOM_H - 120, 150, 24, "Atualizar Ranking", cor=BLUE)
        btn_refresh.update(mp); btn_refresh.draw(self.screen, self.f_small)
        self.dyn_btns.append((btn_refresh, ("refresh_ranking", None)))

    def _wrap_text(self, text: str, max_w: int) -> list[str]:
        """Quebra um texto em várias linhas que cabem em max_w pixels."""
        words = text.split(' ')
        lines = []
        curr_line = ""
        for word in words:
            test_line = curr_line + word + " "
            if self.f_small.size(test_line)[0] < max_w:
                curr_line = test_line
            else:
                lines.append(curr_line.strip())
                curr_line = word + " "
        lines.append(curr_line.strip())
        return [l for l in lines if l]

    def save_screenshot(self, filename: str):
        """Salva a superfície de renderização atual como uma imagem PNG."""
        try:
            pygame.image.save(self.screen, filename)
            self.game.log_add(f"[SISTEMA] Captura salva: {filename}", (0, 255, 255))
        except Exception as e:
            self.game.log_add(f"[ERRO] Falha ao capturar tela: {e}", (255, 0, 0))

class _RectBtn:
    """Rect-like mínimo que satisfaz a interface de Btn para dyn_btns."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect

    def clicked(self, ev):
        return (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.rect.collidepoint(ev.pos))

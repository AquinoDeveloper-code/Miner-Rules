#!/usr/bin/env python3
# ============================================================
# main.py — Ponto de entrada: "Mina dos Escravos Eternos"
#
# Como executar:
#   pip install pygame
#   python main.py
#
# O jogo salva automaticamente a cada 30 segundos na pasta
# de dados do usuário.
# ============================================================

import sys
import time
import pygame

from src.contexts.gameplay.application.game_manager import GameManager
from src.contexts.shared.constants import BLACK, FPS, SCREEN_WIDTH, SCREEN_HEIGHT, TITLE
from src.ui.pygame.renderer import Renderer


def _compute_viewport(display_size):
    disp_w, disp_h = display_size
    scale = min(disp_w / SCREEN_WIDTH, disp_h / SCREEN_HEIGHT)
    view_w = int(SCREEN_WIDTH * scale)
    view_h = int(SCREEN_HEIGHT * scale)
    view_x = (disp_w - view_w) // 2
    view_y = (disp_h - view_h) // 2
    return scale, pygame.Rect(view_x, view_y, view_w, view_h)


def _get_initial_window_size():
    try:
        desktop_sizes = pygame.display.get_desktop_sizes()
        if desktop_sizes:
            return desktop_sizes[0]
    except Exception:
        pass

    info = pygame.display.Info()
    return info.current_w, info.current_h


def main():
    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------
    pygame.init()
    try:
        pygame.mixer.init()
        _has_sound = True
    except Exception:
        _has_sound = False

    initial_size = _get_initial_window_size()
    screen = pygame.display.set_mode(initial_size, pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()
    render_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()
    view_scale, view_rect = _compute_viewport(screen.get_size())

    # ------------------------------------------------------------------
    # Cria os objetos do jogo
    # ------------------------------------------------------------------
    game     = GameManager()
    renderer = Renderer(render_surface, game)
    renderer.set_view_transform(view_scale, view_rect.x, view_rect.y)

    # Tenta carregar save existente
    if game.load():
        renderer.show_tutorial = False   # não mostra tutorial se já jogou
    else:
        renderer.show_tutorial = True    # primeira vez

    # ------------------------------------------------------------------
    # Estado interno do loop
    # ------------------------------------------------------------------
    last_real_time = time.time()

    # Rastreamento de ciclos de mineração para partículas visuais
    # Guarda tempo_jogo do último ciclo de cada escravo para detectar novo ciclo
    _last_ciclos: dict[int, float] = {}

    # ------------------------------------------------------------------
    # LOOP PRINCIPAL
    # ------------------------------------------------------------------
    running = True
    while running:
        # --- Tempo ---
        now_real  = time.time()
        delta_real = min(now_real - last_real_time, 0.1)   # cap de 100ms para evitar spikes
        last_real_time = now_real

        # Delta de jogo (afetado pela velocidade; zero se pausado)
        delta_game = delta_real * game.velocidade if not game.pausado else 0.0

        # --- Eventos do Pygame ---
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                game.save()
                running = False
                break
            if ev.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                view_scale, view_rect = _compute_viewport(screen.get_size())
                renderer.set_view_transform(view_scale, view_rect.x, view_rect.y)
                continue
            renderer.handle_event(ev)
            if renderer.request_quit:
                game.save()
                running = False
                break

        if not running:
            break

        # --- Atualização da lógica do jogo ---
        if not game.pausado:
            game.update(delta_game, now_real)

        # --- Detecta novos ciclos de mineração (para efeitos visuais) ---
        for e in game.escravos_vivos:
            prev = _last_ciclos.get(e.id, -999)
            if e.ultimo_ciclo != prev and e.ultimo_ciclo > 0:
                _last_ciclos[e.id] = e.ultimo_ciclo
                # Pega cor do recurso mais recente (usa cor do ouro como default visual)
                cor = (220, 200, 60)
                renderer.notify_mining(e.id, cor)

        # Limpa escravos mortos do tracking
        ids_vivos = {e.id for e in game.escravos}
        for eid in list(_last_ciclos.keys()):
            if eid not in ids_vivos:
                del _last_ciclos[eid]

        # --- Renderização ---
        renderer.draw()
        screen.fill(BLACK)
        frame = pygame.transform.smoothscale(render_surface, view_rect.size)
        screen.blit(frame, view_rect.topleft)
        pygame.display.flip()

        # --- Limita FPS ---
        clock.tick(FPS)

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

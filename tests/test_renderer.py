from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from src.contexts.gameplay.application.game_manager import GameManager
from src.ui.pygame.renderer import Renderer
from tests.support import TempHomeTestCase


class RendererTests(TempHomeTestCase):
    def setUp(self):
        super().setUp()
        self.write_rules()
        pygame.init()
        self.addCleanup(pygame.quit)
        self.screen = pygame.display.set_mode((1600, 900))
        self.game = GameManager()
        self.renderer = Renderer(self.screen, self.game)
        self.renderer.show_tutorial = False

    def test_refresh_layout_uses_player_ui_preferences(self):
        widths_before = (
            self.renderer.r_sidebar.width,
            self.renderer.r_left.width,
            self.renderer.r_center.width,
            self.renderer.r_right.width,
        )

        self.game.adjust_ui_config("sidebar_factor", 0.5)
        self.game.adjust_ui_config("right_factor", -0.2)
        self.game.adjust_ui_config("bottom_factor", 0.3)
        self.renderer.refresh_layout()

        widths_after = (
            self.renderer.r_sidebar.width,
            self.renderer.r_left.width,
            self.renderer.r_center.width,
            self.renderer.r_right.width,
        )

        self.assertNotEqual(widths_before, widths_after)
        self.assertEqual(sum(widths_after), self.screen.get_width())
        self.assertEqual(self.renderer.r_bottom.bottom, self.screen.get_height())

    def test_exec_buy_offer_uses_offer_id(self):
        self.game.ouro = 100_000
        offer_id = self.game.loja[0]["id"]

        self.renderer._exec("comprar_loja", offer_id)

        self.assertEqual(len(self.game.escravos), 2)
        self.assertIsNone(self.game.get_oferta_loja(offer_id))

    def test_handle_event_clicks_pause_and_exit(self):
        pause_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": self.renderer.btn_pause.rect.center},
        )
        self.renderer.handle_event(pause_event)
        self.assertTrue(self.game.pausado)

        exit_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": self.renderer.btn_exit.rect.center},
        )
        self.renderer.handle_event(exit_event)
        self.assertTrue(self.renderer.request_quit)

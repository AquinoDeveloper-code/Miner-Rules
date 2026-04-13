from __future__ import annotations
import unittest
from unittest.mock import patch
from src.contexts.gameplay.application.game_manager import GameManager
from src.contexts.gameplay.domain.guard import Guarda, Delivery
from tests.support import TempHomeTestCase

class GuardTests(TempHomeTestCase):
    def test_guard_creation_and_attributes(self):
        # Teste de criação direta do domínio
        g = Guarda(tipo="basico")
        self.assertEqual(g.tipo, "basico")
        self.assertEqual(g.raridade, "comum")
        self.assertTrue(15 <= g.forca <= 40)
        
        g_expert = Guarda(tipo="normal")
        self.assertEqual(g_expert.raridade, "incomum")
        self.assertTrue(35 <= g_expert.forca <= 65)

    def test_guard_equipment_bonus(self):
        g = Guarda()
        g.forca = 10
        # Simula equipamento em um slot válido (espada)
        with patch("src.contexts.gameplay.domain.guard.GUARD_ITEMS", {
            "shield_wood": {"bonus": {"resistencia": 5, "forca": 2}}
        }):
            g.equipamentos["espada"] = "shield_wood"
            self.assertEqual(g.forca_efetiva(), 12)
            self.assertEqual(g.resistencia_efetiva(), g.resistencia + 5)

    def test_buying_guard_in_game_manager(self):
        game = GameManager()
        game.ouro = 10000
        initial_count = len(game.guardas)
        
        ok, msg = game.comprar_guarda("basico")
        self.assertTrue(ok)
        self.assertEqual(len(game.guardas), initial_count + 1)
        self.assertLess(game.ouro, 10000)

    def test_demitir_guarda(self):
        game = GameManager()
        game.ouro = 10000
        game.comprar_guarda("basico")
        gid = game.guardas[0].id
        
        game.demitir_guarda(gid)
        self.assertEqual(len(game.guardas), 0)

if __name__ == "__main__":
    unittest.main()

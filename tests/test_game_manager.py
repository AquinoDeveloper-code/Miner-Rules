from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

from src.contexts.gameplay.application.game_manager import GameManager
from src.contexts.shared.constants import MINE_DEPTHS, PRESTIGE_BONUS_STEP
from tests.support import TempHomeTestCase, make_servo


class GameManagerTests(TempHomeTestCase):
    def make_game(self, **rule_overrides) -> GameManager:
        self.write_rules(**rule_overrides)
        return GameManager()

    def test_initial_state_has_common_starter_servo_and_shop_offers(self):
        game = self.make_game(initial_gold=321.0)

        self.assertEqual(game.ouro, 321.0)
        self.assertEqual(len(game.escravos), 1)
        self.assertEqual(game.stats["escravos_total"], 1)
        self.assertEqual(game.capacidade_servos, 10)
        self.assertTrue(4 <= len(game.loja) <= 6)
        self.assertCountEqual(
            game.loja[0].keys(),
            ["id", "servo", "created_at", "duration", "expires_at"],
        )

        starter = game.escravos[0]
        for attr in ("forca", "velocidade", "resistencia", "fertilidade", "sorte", "lealdade"):
            self.assertLessEqual(getattr(starter, attr), 39)

    def test_buying_offer_adds_servo_and_removes_offer(self):
        game = self.make_game()
        game.ouro = 100_000
        oferta = deepcopy(game.loja[0])

        ok, msg = game.comprar_oferta_loja(oferta["id"])

        self.assertTrue(ok)
        self.assertEqual(msg, "Comprado!")
        self.assertEqual(len(game.escravos), 2)
        self.assertIsNone(game.get_oferta_loja(oferta["id"]))
        self.assertIn(oferta["servo"].nome, [servo.nome for servo in game.escravos])

    def test_refresh_keeps_old_offers_and_accelerates_old_expiration(self):
        game = self.make_game(shop_refresh_base_cost=10.0, shop_refresh_time=300.0)
        game.ouro = 1_000
        before_ids = [oferta["id"] for oferta in game.loja]
        oldest = min(game.loja, key=lambda item: item["created_at"])
        oldest_expiration = oldest["expires_at"]

        ok, _ = game.refresca_loja()

        self.assertTrue(ok)
        self.assertGreater(len(game.loja), len(before_ids))
        self.assertTrue(set(before_ids).issubset({oferta["id"] for oferta in game.loja}))
        self.assertEqual(game.custo_refresco, 15)
        self.assertLess(game.get_oferta_loja(oldest["id"])["expires_at"], oldest_expiration)

    def test_food_charge_consumes_gold_or_marks_hunger(self):
        game = self.make_game(food_cost_basic=5.0, food_cost_quality=20.0)
        quality = make_servo(genero="F", nome="Nobre")
        quality.qualidade_comida = "qualidade"
        game.escravos.append(quality)

        game.ouro = 25.0
        game._cobrar_comida()
        self.assertEqual(game.ouro, 0.0)
        self.assertFalse(game.escravos[0].sem_comida)
        self.assertFalse(quality.sem_comida)

        game.ouro = 0.0
        game._cobrar_comida()
        self.assertTrue(game.escravos[0].sem_comida)
        self.assertTrue(quality.sem_comida)

    def test_disease_check_can_infect_weakened_servo(self):
        game = self.make_game(disease_base_chance=0.01, disease_duration=9.0)
        servo = game.escravos[0]
        servo.idade = 50
        servo.sem_comida = True
        servo.stamina = 10.0

        with patch("random.random", return_value=0.0):
            game._verificar_doencas()

        self.assertTrue(servo.doente)
        self.assertEqual(servo.doenca_timer, 9.0)

    def test_equipment_and_consumable_flows(self):
        game = self.make_game()
        servo = game.escravos[0]
        game.inventario_itens = [{"id": i, "added_at": 0.0} for i in ["pic_ferro", "pic_maldita", "reza_simples", "pocao_cura"]]

        ok, _ = game.equipar_item(servo.id, "pic_ferro")
        self.assertTrue(ok)
        self.assertEqual(servo.equipamentos["picareta"], "pic_ferro")

        ok, _ = game.equipar_item(servo.id, "pic_maldita")
        self.assertTrue(ok)
        self.assertEqual(servo.equipamentos["picareta"], "pic_maldita")
        self.assertGreater(servo.maldicoes["picareta"], 0.0)
        self.assertIn("pic_ferro", [it["id"] for it in game.inventario_itens])

        ok, msg = game.desequipar_item(servo.id, "picareta")
        self.assertFalse(ok)
        self.assertIn("maldito", msg.lower())

        ok, _ = game.usar_item_especial(servo.id, "reza_simples")
        self.assertTrue(ok)
        self.assertEqual(servo.maldicoes["picareta"], 0.0)

        ok, _ = game.desequipar_item(servo.id, "picareta")
        self.assertTrue(ok)
        self.assertIn("pic_maldita", [it["id"] for it in game.inventario_itens])

        servo.doente = True
        servo.doenca_timer = 12.0
        servo.stamina = 7.0
        ok, _ = game.usar_item_especial(servo.id, "pocao_cura")
        self.assertTrue(ok)
        self.assertFalse(servo.doente)
        self.assertEqual(servo.doenca_timer, 0.0)
        self.assertEqual(servo.stamina, 100.0)

    def test_retirement_and_sale_remove_servo_from_active_roster(self):
        game = self.make_game()
        veterano = make_servo(nome="Veterano", idade=55)
        game.escravos.append(veterano)
        ouro_antes = game.ouro

        ok, _ = game.aposentar_escravo(veterano.id)
        self.assertTrue(ok)
        self.assertIn(veterano, game.aposentados)
        self.assertNotIn(veterano, game.escravos)

        valor = game.vender_escravo(veterano)
        self.assertGreater(valor, 0)
        self.assertGreater(game.ouro, ouro_antes)
        self.assertNotIn(veterano, game.aposentados)

    def test_breeding_generates_baby_and_capacity_blocks_new_births(self):
        game = self.make_game(growth_time=33.0)
        homem = make_servo(genero="M", nome="Pai", fertilidade=100, lealdade=100)
        mulher = make_servo(genero="F", nome="Mae", fertilidade=100, lealdade=100)
        game.escravos.extend([homem, mulher])

        ok, _ = game.adicionar_par(homem.id, mulher.id)
        self.assertTrue(ok)

        with patch("random.random", return_value=0.0):
            game._update_breeding()

        self.assertEqual(len(game.bebes), 1)
        bebe = game.bebes[0]
        self.assertEqual(bebe.tempo_crescimento, 33.0)
        self.assertEqual(game.stats["filhos_nascidos"], 1)

        while game.servos_na_mina < game.capacidade_servos:
            game.escravos.append(make_servo(nome=f"Extra{game.servos_na_mina}"))

        with patch("random.random", return_value=0.0):
            game._update_breeding()

        self.assertEqual(len(game.bebes), 1)

    def test_economy_upgrade_and_mine_depth_actions(self):
        game = self.make_game()
        game.ouro = 10_000
        game.inventario["Terra"] = 10
        game.inventario["Ouro"] = 2

        total = game.vender_tudo()
        self.assertEqual(total, 60)
        self.assertEqual(game.inventario["Terra"], 0)
        self.assertEqual(game.inventario["Ouro"], 0)

        ok, _ = game.comprar_upgrade("ferramentas")
        self.assertTrue(ok)
        self.assertEqual(game.upgrades["ferramentas"], 1)

        ok, _ = game.aprofundar_mina()
        self.assertTrue(ok)
        self.assertEqual(game.nivel_mina, 1)
        self.assertEqual(game.capacidade_servos, 20)

    def test_event_handlers_apply_expected_effects(self):
        game = self.make_game(black_market_duration=15.0)
        game.ouro = 1_000
        game.escravos.extend(
            [
                make_servo(nome="A"),
                make_servo(nome="B"),
                make_servo(nome="C"),
                make_servo(nome="D"),
            ]
        )

        with patch("random.sample", side_effect=lambda seq, n: list(seq)[:n]), patch(
            "random.randint", return_value=2
        ):
            vivos_antes = len(game.escravos_vivos)
            game._ev_mercado()
            game._ev_caverna()
            game._ev_mineral()
            game._ev_doacao()
            game._ev_rebelliao()

        self.assertTrue(game.mercado_negro)
        self.assertEqual(game.mercado_negro_timer, 15.0)
        self.assertEqual(game.inventario["Ouro"], 2)
        self.assertEqual(game.inventario["Esmeralda"], 2)
        self.assertEqual(game.inventario["Diamante"], 2)
        self.assertEqual(game.inventario["Adamantita"], 2)
        self.assertLess(len(game.escravos_vivos), vivos_antes + 1)
        self.assertGreater(game.stats["mortos_total"], 0)
        self.assertIsNotNone(game.notificacao)

    def test_prestige_keeps_permanent_progress_and_resets_run_state(self):
        game = self.make_game(prestige_gold_req=500.0)
        game.stats["ouro_total"] = 600.0
        game.inventario_itens = [{"id": "amu_sorte", "added_at": 0.0}]
        game.ouro = 2_000
        game.conquistas.add("primeiro")

        ok, _ = game.fazer_prestigio()

        self.assertTrue(ok)
        self.assertEqual(game.prestigios, 1)
        self.assertEqual(game.almas_eternas, 2)
        self.assertEqual(game.bonus_prestigio, 1.0 + PRESTIGE_BONUS_STEP)
        self.assertEqual(game.ouro, 140)
        self.assertEqual([it["id"] for it in game.inventario_itens], ["amu_sorte"])
        self.assertEqual(len(game.escravos), 1)
        self.assertIn("primeiro", game.conquistas)

    def test_update_triggers_mining_timers_events_and_autosave(self):
        game = self.make_game()
        servo = game.escravos[0]
        servo.eh_bebe = False
        servo.ultimo_ciclo = -999.0
        game._t_autosave = 0.0
        game._t_evento = 0.0
        game._t_breed = game.rules["breeding_interval"]
        game._t_comida = game.rules["food_check_interval"]
        game._t_doenca = 60.0

        with patch.object(game, "_ciclo_mineracao") as ciclo, patch.object(
            game, "_update_breeding"
        ) as breeding, patch.object(game, "_cobrar_comida") as comida, patch.object(
            game, "_verificar_doencas"
        ) as doenca, patch.object(game, "_tentar_evento") as evento, patch.object(
            game, "save", return_value=True
        ) as save:
            game.update(delta=1.0, agora_real=999.0)

        ciclo.assert_called_once_with(servo)
        breeding.assert_called_once()
        comida.assert_called_once()
        doenca.assert_called_once()
        evento.assert_called_once()
        save.assert_called_once()

    def test_ui_config_adjust_and_reset(self):
        game = self.make_game()

        self.assertTrue(game.adjust_ui_config("ui_scale", 5.0))
        self.assertEqual(game.ui_config["ui_scale"], 1.5)
        self.assertTrue(game.adjust_ui_config("sidebar_factor", -5.0))
        self.assertEqual(game.ui_config["sidebar_factor"], 0.7)
        self.assertFalse(game.adjust_ui_config("inexistente", 0.1))

        game.reset_ui_config()
        self.assertEqual(game.ui_config["ui_scale"], 1.0)
        self.assertEqual(game.ui_config["sidebar_factor"], 1.0)

    def test_mining_death_risk_scales_with_age_and_caps_at_seventy_percent(self):
        game = self.make_game()
        jovem = make_servo(nome="Jovem", idade=16)
        velho = make_servo(nome="Velho", idade=70)
        game.nivel_mina = len(MINE_DEPTHS) - 1
        game.upgrades["seguranca"] = 0

        risco_jovem = game.risco_morte_mineracao(jovem)
        risco_velho = game.risco_morte_mineracao(velho)

        self.assertLess(risco_jovem, game.risco_morte)
        self.assertGreater(risco_velho, risco_jovem)
        self.assertAlmostEqual(risco_velho, 0.70, places=3)

    def test_save_and_load_roundtrip_preserves_state(self):
        game = self.make_game()
        macho = make_servo(genero="M", nome="Brutus", fertilidade=80)
        femea = make_servo(genero="F", nome="Mara", fertilidade=90, idade=55)
        aposentado = make_servo(genero="M", nome="Ancião", idade=60, aposentado=True)
        game.escravos = [macho, femea]
        game.aposentados = [aposentado]
        game.pares = [(macho.id, femea.id)]
        macho.par_id = femea.id
        femea.par_id = macho.id
        game.ouro = 4321.0
        game.inventario["Diamante"] = 3
        game.inventario_itens = [{"id": "amu_forca", "added_at": 88.0}]
        game.nivel_mina = 2
        game.upgrades["ferramentas"] = 1
        game.upgrades["ventilacao"] = 2
        game.stats["recursos_enc"].add("Diamante")
        game.stats["rec_qtd"]["Diamante"] = 3
        game.conquistas.add("primeiro")
        game.prestigios = 2
        game.almas_eternas = 5
        game.bonus_prestigio = 1.2
        game.tempo_jogo = 88.0
        game.velocidade = 4
        game.custo_refresco = 75
        game.adjust_ui_config("center_factor", 0.25)

        self.assertTrue(game.save())

        loaded = self.make_game()
        self.assertTrue(loaded.load())
        self.assertEqual(loaded.ouro, 4321.0)
        self.assertEqual(loaded.inventario["Diamante"], 3)
        self.assertEqual([it["id"] for it in loaded.inventario_itens], ["amu_forca"])
        self.assertEqual(loaded.nivel_mina, 2)
        self.assertEqual(loaded.upgrades["ventilacao"], 2)
        self.assertEqual(loaded.ui_config["center_factor"], 1.25)
        self.assertEqual(len(loaded.escravos), 2)
        self.assertEqual(len(loaded.aposentados), 1)
        self.assertEqual(loaded.pares, [(macho.id, femea.id)])
        self.assertIn("Diamante", loaded.stats["recursos_enc"])
        self.assertIn("primeiro", loaded.conquistas)
        self.assertEqual(loaded.prestigios, 2)
        self.assertEqual(loaded.almas_eternas, 5)
        self.assertEqual(loaded.bonus_prestigio, 1.2)
        self.assertEqual(loaded.tempo_jogo, 88.0)
        self.assertEqual(loaded.velocidade, 4)
        self.assertEqual(loaded.custo_refresco, 75)
        self.assertGreater(len(loaded.loja), 0)

    def test_mortality_logging(self):
        game = self.make_game()
        servo = game.escravos[0]
        
        game._on_morte(servo, "Acidente")
        self.assertEqual(len(game.mortalidade_history), 1)
        self.assertEqual(game.mortalidade_history[0]["causa"], "Acidente")
        self.assertEqual(game.mortalidade_history[0]["nome"], servo.nome)

    def test_inventory_item_expiration(self):
        game = self.make_game()
        # Adiciona item com tempo antigo
        game.inventario_itens = [{"id": "pic_ferro", "added_at": 0.0}]
        game.tempo_jogo = 100.0
        
        # 100s < 120s -> deve ficar
        game._verificar_expiracao_itens()
        self.assertEqual(len(game.inventario_itens), 1)
        
        # 130s > 120s -> deve expirar
        game.tempo_jogo = 130.0
        game._verificar_expiracao_itens()
        self.assertEqual(len(game.inventario_itens), 0)

    def test_inventory_sanitization_legacy_support(self):
        game = self.make_game()
        # Simula save antigo com strings
        game.inventario_itens = ["pic_ferro", "amu_sorte"]
        game.tempo_jogo = 50.0
        
        game._sanitizar_inventario()
        
        self.assertIsInstance(game.inventario_itens[0], dict)
        self.assertEqual(game.inventario_itens[0]["id"], "pic_ferro")
        self.assertEqual(game.inventario_itens[0]["added_at"], 50.0)

if __name__ == "__main__":
    import unittest
    unittest.main()

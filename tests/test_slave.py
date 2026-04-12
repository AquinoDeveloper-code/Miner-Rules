from __future__ import annotations

from unittest.mock import patch

from src.contexts.gameplay.domain.slave import Escravo
from src.contexts.shared.constants import ITEMS, MAX_AGE
from tests.support import TempHomeTestCase, make_servo


class SlaveTests(TempHomeTestCase):
    def test_common_servo_starts_with_common_attributes(self):
        servo = Escravo(comum=True)

        for attr in ("forca", "velocidade", "resistencia", "fertilidade", "sorte", "lealdade"):
            self.assertGreaterEqual(getattr(servo, attr), 1)
            self.assertLessEqual(getattr(servo, attr), 39)

    def test_price_scales_with_quality_market_and_mine_level(self):
        ruim = make_servo(
            nome="Ruim",
            forca=10,
            velocidade=10,
            resistencia=10,
            fertilidade=10,
            sorte=10,
            lealdade=10,
            idade=45,
            stamina=40,
        )
        excelente = make_servo(
            nome="Bom",
            forca=95,
            velocidade=92,
            resistencia=90,
            fertilidade=88,
            sorte=96,
            lealdade=91,
            idade=27,
            stamina=100,
        )

        preco_ruim = ruim.calcular_preco()
        preco_bom = excelente.calcular_preco()

        self.assertGreater(preco_bom, preco_ruim * 5)
        self.assertGreater(excelente.calcular_preco(bonus_nivel_mina=3), preco_bom)
        self.assertGreater(excelente.calcular_preco(mercado_negro=True), preco_bom)

    def test_equipment_bonus_changes_effective_stats(self):
        servo = make_servo(forca=20, resistencia=20, sorte=20)
        servo.equipamentos["picareta"] = "pic_ouro"
        servo.equipamentos["especial"] = "amu_forca"

        self.assertEqual(servo.bonus_mineracao_equip(), ITEMS["pic_ouro"]["bonus"]["mineracao_mult"])
        self.assertEqual(servo.bonus_raridade_equip(), ITEMS["pic_ouro"]["bonus"]["raridade_mult"])
        self.assertGreater(servo.forca_efetiva(), servo.forca)
        self.assertGreater(servo.sorte_efetiva(), servo.sorte)

    def test_baby_growth_turns_servo_into_adult(self):
        servo = make_servo(nome="Bebe")
        servo.eh_bebe = True
        servo.tempo_crescimento = 1.0
        servo.minerando = False

        morreu = servo.update(2.0)

        self.assertFalse(morreu)
        self.assertFalse(servo.eh_bebe)
        self.assertTrue(servo.minerando)

    def test_old_age_and_disease_can_kill(self):
        velho = make_servo(nome="Velho", idade=MAX_AGE)
        self.assertTrue(velho.update(0.1))
        self.assertFalse(velho.vivo)
        self.assertEqual(velho.causa_morte, "Velhice")

        doente = make_servo(nome="Doente", stamina=1.0, doente=True, doenca_timer=0.5)
        self.assertTrue(doente.update(1.0))
        self.assertFalse(doente.vivo)
        self.assertEqual(doente.causa_morte, "Doença")

    def test_mining_consumes_stamina_and_records_loot(self):
        servo = make_servo(
            nome="Minerador",
            forca=90,
            resistencia=90,
            sorte=90,
            stamina=100.0,
        )

        with patch("random.randint", return_value=4), patch("random.random", return_value=0.0):
            recurso, qtd, valor = servo.executar_mineracao(tempo_jogo=10.0)

        self.assertEqual(recurso, "Terra")
        self.assertEqual(qtd, 4)
        self.assertEqual(valor, 4)
        self.assertLess(servo.stamina, 100.0)
        self.assertEqual(servo.rec_encontrados["Terra"], 4)
        self.assertEqual(servo.valor_total, 4)

    def test_serialization_roundtrip_preserves_extended_fields(self):
        servo = make_servo(nome="Serializado", doente=True, doenca_timer=12.5, sem_comida=True)
        servo.equipamentos["capacete"] = "cap_couro"
        servo.maldicoes["capacete"] = 5.0
        servo.par_id = 99
        servo.tempo_na_mina = 42.0

        restored = Escravo.from_dict(servo.to_dict())

        self.assertEqual(restored.nome, servo.nome)
        self.assertEqual(restored.equipamentos["capacete"], "cap_couro")
        self.assertEqual(restored.maldicoes["capacete"], 5.0)
        self.assertTrue(restored.doente)
        self.assertTrue(restored.sem_comida)
        self.assertEqual(restored.par_id, 99)
        self.assertEqual(restored.tempo_na_mina, 42.0)

from __future__ import annotations

import os
import random
import tempfile
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from src.contexts.configuration.application.game_rules import DEFAULT_RULES, save_rules
from src.contexts.gameplay.domain.slave import Escravo


def make_rules(**overrides):
    rules = deepcopy(DEFAULT_RULES)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(rules.get(key), dict):
            rules[key].update(value)
        else:
            rules[key] = value
    return rules


def make_servo(
    *,
    genero: str = "M",
    nome: str | None = None,
    comum: bool = True,
    **attrs,
) -> Escravo:
    servo = Escravo(genero=genero, comum=comum)
    if nome:
        servo.nome = nome

    defaults = {
        "idade": 28.0,
        "forca": 25,
        "velocidade": 25,
        "resistencia": 25,
        "fertilidade": 25,
        "sorte": 25,
        "lealdade": 25,
        "stamina": 100.0,
        "vivo": True,
        "eh_bebe": False,
        "tempo_crescimento": 0.0,
        "minerando": True,
        "aposentado": False,
        "sem_comida": False,
        "doente": False,
        "doenca_timer": 0.0,
        "par_id": None,
        "ultimo_ciclo": -999.0,
        "tempo_na_mina": 0.0,
    }
    defaults.update(attrs)

    for key, value in defaults.items():
        setattr(servo, key, value)

    servo.vida_max = servo._calc_vida_max()
    servo.vida = servo.vida_max
    return servo


class TempHomeTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self._stack = ExitStack()
        self.temp_dir = Path(self._stack.enter_context(tempfile.TemporaryDirectory()))
        self._stack.enter_context(
            patch.dict(
                os.environ,
                {
                    "HOME": str(self.temp_dir),
                    "XDG_DATA_HOME": str(self.temp_dir / ".local" / "share"),
                    "APPDATA": str(self.temp_dir / "AppData" / "Roaming"),
                    "LOCALAPPDATA": str(self.temp_dir / "AppData" / "Local"),
                },
                clear=False,
            )
        )
        random.seed(12345)
        Escravo._id_counter = 0
        from src.contexts.gameplay.domain.guard import Guarda, Delivery
        from src.contexts.gameplay.domain.manager import Gerente
        Guarda._id_counter = 0
        Delivery._id_counter = 0
        Gerente._id_counter = 0

    def tearDown(self):
        self._stack.close()
        super().tearDown()

    def write_rules(self, **overrides):
        rules = make_rules(**overrides)
        save_rules(rules)
        return rules

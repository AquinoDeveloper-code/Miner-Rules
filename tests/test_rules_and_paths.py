from __future__ import annotations

import json
from pathlib import Path

from src.contexts.configuration.application.game_rules import DEFAULT_RULES, load_rules, normalize_rules, save_rules
from src.contexts.configuration.infrastructure import app_paths
from src.contexts.configuration.infrastructure.app_paths import (
    delete_save_files,
    get_app_data_dir,
    get_legacy_save_path,
    get_rules_path,
    get_save_path,
)
from tests.support import TempHomeTestCase, make_rules


class RulesAndPathsTests(TempHomeTestCase):
    def test_app_paths_stay_inside_temp_home(self):
        app_dir = get_app_data_dir()

        self.assertTrue(str(app_dir).startswith(str(self.temp_dir)))
        self.assertEqual(get_save_path().parent, app_dir)
        self.assertEqual(get_rules_path().parent, app_dir)
        self.assertEqual(get_legacy_save_path(self.temp_dir), self.temp_dir / app_paths.SAVE_FILE_NAME)

    def test_normalize_rules_clamps_invalid_values(self):
        rules = normalize_rules(
            {
                "initial_gold": -100,
                "shop_refresh_time": 999999,
                "event_chances": {"doacao": 2.0},
                "food_cost_basic": "12.5",
            }
        )

        self.assertEqual(rules["initial_gold"], 0.0)
        self.assertEqual(rules["shop_refresh_time"], 10_000.0)
        self.assertEqual(rules["event_chances"]["doacao"], 1.0)
        self.assertEqual(rules["food_cost_basic"], 12.5)
        self.assertEqual(rules["growth_time"], DEFAULT_RULES["growth_time"])

    def test_save_and_load_rules_roundtrip(self):
        expected = make_rules(initial_gold=777.0, event_chances={"doacao": 0.33})

        save_rules(expected)
        loaded = load_rules()

        self.assertEqual(loaded["initial_gold"], 777.0)
        self.assertEqual(loaded["event_chances"]["doacao"], 0.33)
        self.assertEqual(loaded["growth_time"], expected["growth_time"])

    def test_load_rules_falls_back_when_storage_is_corrupted(self):
        path = get_rules_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{invalido", encoding="utf-8")

        loaded = load_rules()

        self.assertEqual(loaded, DEFAULT_RULES)

    def test_delete_save_files_removes_active_and_legacy_files(self):
        save_path = get_save_path()
        legacy_path = get_legacy_save_path(self.temp_dir)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text("ativo", encoding="utf-8")
        legacy_path.write_text("legado", encoding="utf-8")

        removed = delete_save_files(self.temp_dir)

        self.assertCountEqual(removed, [save_path, legacy_path])
        self.assertFalse(save_path.exists())
        self.assertFalse(legacy_path.exists())

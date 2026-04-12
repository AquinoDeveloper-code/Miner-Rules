from __future__ import annotations

import json

from src.contexts.configuration.infrastructure.app_paths import get_app_legacy_save_path, get_save_path
from src.contexts.gameplay.application.game_manager import GameManager
from tests.support import TempHomeTestCase


class StorageMigrationTests(TempHomeTestCase):
    def make_game(self) -> GameManager:
        self.write_rules()
        return GameManager()

    def test_save_creates_sqlite_database_file(self):
        game = self.make_game()

        self.assertTrue(game.save())
        self.assertTrue(get_save_path().exists())
        self.assertEqual(get_save_path().read_bytes()[:16], b"SQLite format 3\x00")

    def test_load_imports_legacy_json_when_database_is_missing(self):
        game = self.make_game()
        game.ouro = 987.0
        legacy_path = get_app_legacy_save_path()
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text(
            json.dumps(game._serialize_state(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        loaded = self.make_game()

        self.assertTrue(loaded.load())
        self.assertEqual(loaded.ouro, 987.0)
        self.assertTrue(get_save_path().exists())
        self.assertEqual(get_save_path().read_bytes()[:16], b"SQLite format 3\x00")

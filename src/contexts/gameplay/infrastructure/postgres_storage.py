from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any
import psycopg2
from psycopg2.extras import RealDictCursor


# String ofuscada da conexão
_ENV_OBF = "zVGb1J3XyVmbp12Lt92YuIXZk5WZy5yclJ3Z0N3bw1ibvdWZy9mLh1yZ5YHN1J2M3MWbxsGb3YHcuV2Nk1yZwRGQqpWcBtkWQB1dWV3NRVUUSRmdLNFa5FXa4tEM2kkVtNmOulWbkF2LvoDbxNXZydGdz9Gc"


def _get_db_url() -> str:
    # Desfaz a inversão e o base64
    return base64.b64decode(_ENV_OBF[::-1]).decode("utf-8")


def _hash_password(password: str) -> str:
    """Um hash simples para o password local."""
    # Adicionando um salt fixo apenas para não armazenar localmente o Hash puro
    return hashlib.sha256((password + "MINERS_SALT2026").encode("utf-8")).hexdigest()


class PostgresStorage:
    """Persistência principal do jogo em PostgreSQL (Nuvem)."""

    VERSION = "2.0"

    def __init__(self):
        self.url = _get_db_url()
        self._init_db()

    def _get_conn(self):
        # Cada requisição cria ou pega uma conexão para não travar na rede em idle prolongado
        return psycopg2.connect(self.url, cursor_factory=RealDictCursor)

    def _init_db(self):
        """Cria as tabelas necessárias no PostgreSQL."""
        query = """
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS game_states (
            player_id INTEGER PRIMARY KEY REFERENCES players(id),
            payload TEXT NOT NULL,
            version VARCHAR(50) NOT NULL,
            saved_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rankings (
            player_id INTEGER PRIMARY KEY REFERENCES players(id),
            total_money REAL DEFAULT 0.0,
            play_time REAL DEFAULT 0.0
        );
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                conn.commit()
        except Exception as e:
            print(f"[DB] Erro ao inicializar o banco de dados: {e}")

    # ==========================================
    # LOGIN / REGISTRO
    # ==========================================

    def login(self, username: str, password: str) -> tuple[bool, str, int | None]:
        """Tenta fazer login. Retorna (sucesso, mensagem, player_id)."""
        pw_hash = _hash_password(password)
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, password_hash FROM players WHERE username = %s LIMIT 1", (username,))
                    row = cur.fetchone()

                    if row:
                        if row["password_hash"] == pw_hash:
                            return True, "Login bem-sucedido!", row["id"]
                        else:
                            return False, "Senha incorreta.", None
                    else:
                        return False, "Usuário não existe. Use Registrar.", None
        except Exception as e:
            return False, f"Erro de conexão com o servidor.", None

    def register(self, username: str, password: str) -> tuple[bool, str]:
        """Registra novo usuário. Retorna (sucesso, mensagem)."""
        if len(username) < 3 or len(password) < 4:
            return False, "Usuário (min 3) e Senha (min 4) curtos."
            
        pw_hash = _hash_password(password)
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Verifica se existe
                    cur.execute("SELECT id FROM players WHERE username = %s", (username,))
                    if cur.fetchone():
                        return False, "Nome de usuário já está em uso."

                    # Insere
                    now = time.time()
                    cur.execute(
                        "INSERT INTO players (username, password_hash, created_at) VALUES (%s, %s, %s)",
                        (username, pw_hash, now)
                    )
                conn.commit()
                return True, "Registro concluído. Faça o login!"
        except Exception as e:
            return False, "Erro de conexão com o servidor."

    # ==========================================
    # SAVES E CARREGAMENTOS
    # ==========================================

    def load_game_state(self, player_id: int) -> dict[str, Any] | None:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT payload FROM game_states WHERE player_id = %s", (player_id,))
                    row = cur.fetchone()
                    if row and row["payload"]:
                        return json.loads(row["payload"])
        except Exception as e:
            print(f"[DB] Erro ao carregar o state: {e}")
        return None

    def save_game_state(self, player_id: int, data: dict[str, Any], total_money: float, play_time: float) -> bool:
        payload = json.dumps(data, ensure_ascii=False)
        now = time.time()
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Salva game state
                    cur.execute(
                        """
                        INSERT INTO game_states (player_id, payload, version, saved_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (player_id) DO UPDATE SET
                            payload = EXCLUDED.payload,
                            version = EXCLUDED.version,
                            saved_at = EXCLUDED.saved_at
                        """,
                        (player_id, payload, self.VERSION, now)
                    )

                    # Atualiza o ranking
                    cur.execute(
                        """
                        INSERT INTO rankings (player_id, total_money, play_time)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (player_id) DO UPDATE SET
                            total_money = EXCLUDED.total_money,
                            play_time = EXCLUDED.play_time
                        """,
                        (player_id, total_money, play_time)
                    )
                conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Erro ao salvar online: {e}")
            return False

    def clear_game_state(self, player_id: int):
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM game_states WHERE player_id = %s", (player_id,))
                    cur.execute("UPDATE rankings SET total_money = 0.0, play_time = 0.0 WHERE player_id = %s", (player_id,))
                conn.commit()
        except Exception as e:
            print(f"[DB] Erro ao limpar o estado do jogo: {e}")

    def close(self):
        pass

    # ==========================================
    # RANKING
    # ==========================================

    def get_top_rankings(self, limit: int = 10) -> dict[str, list]:
        """Retorna { money: [(username, val), ...], time: [(username, val), ...] }"""
        results = {"money": [], "time": []}
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Top Ouro
                    cur.execute("""
                        SELECT p.username, r.total_money 
                        FROM rankings r
                        JOIN players p ON p.id = r.player_id
                        ORDER BY r.total_money DESC 
                        LIMIT %s
                    """, (limit,))
                    results["money"] = [(row["username"], row["total_money"]) for row in cur.fetchall()]

                    # Top Tempo
                    cur.execute("""
                        SELECT p.username, r.play_time 
                        FROM rankings r
                        JOIN players p ON p.id = r.player_id
                        ORDER BY r.play_time DESC 
                        LIMIT %s
                    """, (limit,))
                    results["time"] = [(row["username"], row["play_time"]) for row in cur.fetchall()]
        except Exception as e:
            print(f"[DB] Erro ao buscar rankings: {e}")
        return results

# ============================================================
# src/db/database.py — Gerenciador do banco de dados SQLite
# ============================================================
#
# Tabelas:
#   game_state   — estado salvo do jogo (singleton row)
#   escravos     — histórico de todos os escravos criados
#   mortes       — log de mortes com causa e tempo de vida
#   mineracao    — eventos de mineração (últimos 2.000)
#   eventos      — eventos aleatórios (rebelião, doação…)
#   conquistas   — conquistas desbloqueadas com timestamp
#   prestigios   — estatísticas de cada run encerrada
#   sessoes      — sessões de jogo com tempo jogado
# ============================================================

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    """Encapsula todas as operações SQLite do jogo."""

    VERSION          = "1.1"
    MAX_MINING_ROWS  = 2_000   # Mantém apenas os últimos N registros de mineração

    def __init__(self, path: str = "data/eternal_mine.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection | None = None
        self._connect()
        self._create_tables()

    # ------------------------------------------------------------------
    # Conexão e esquema
    # ------------------------------------------------------------------

    def _connect(self):
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # WAL: escritas não bloqueiam leituras
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=NORMAL")

    def _create_tables(self):
        with self.conn:
            self.conn.executescript("""
                -- ------------------------------------------------
                -- Estado do jogo (linha única, substituída a cada save)
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS game_state (
                    id       INTEGER PRIMARY KEY CHECK (id = 1),
                    data     TEXT    NOT NULL,
                    version  TEXT    NOT NULL,
                    saved_at TEXT    NOT NULL
                );

                -- ------------------------------------------------
                -- Histórico de escravos criados/nascidos/doados
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS escravos (
                    db_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    slave_id      INTEGER NOT NULL,
                    uid           TEXT    NOT NULL,
                    nome          TEXT    NOT NULL,
                    genero        TEXT    NOT NULL,
                    idade         INTEGER NOT NULL,
                    forca         INTEGER NOT NULL,
                    velocidade    INTEGER NOT NULL,
                    resistencia   INTEGER NOT NULL,
                    fertilidade   INTEGER NOT NULL,
                    sorte         INTEGER NOT NULL,
                    lealdade      INTEGER NOT NULL,
                    vida_max      INTEGER NOT NULL,
                    raridade      TEXT    NOT NULL,
                    origem        TEXT    NOT NULL DEFAULT 'comprado',
                    pai_id        INTEGER,
                    mae_id        INTEGER,
                    run_numero    INTEGER NOT NULL DEFAULT 1,
                    registrado_em TEXT    NOT NULL
                );

                -- ------------------------------------------------
                -- Log de mortes
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS mortes (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    slave_id        INTEGER NOT NULL,
                    slave_nome      TEXT    NOT NULL,
                    causa           TEXT    NOT NULL,
                    tempo_na_mina   REAL    NOT NULL,
                    valor_produzido INTEGER NOT NULL,
                    run_numero      INTEGER NOT NULL DEFAULT 1,
                    morreu_em       TEXT    NOT NULL
                );

                -- ------------------------------------------------
                -- Eventos de mineração (janela deslizante de MAX_MINING_ROWS)
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS mineracao (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    slave_id    INTEGER NOT NULL,
                    slave_nome  TEXT    NOT NULL,
                    recurso     TEXT    NOT NULL,
                    quantidade  INTEGER NOT NULL,
                    valor       INTEGER NOT NULL,
                    run_numero  INTEGER NOT NULL DEFAULT 1,
                    criado_em   TEXT    NOT NULL
                );

                -- ------------------------------------------------
                -- Eventos aleatórios (rebelião, doação, etc.)
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS eventos (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo       TEXT NOT NULL,
                    mensagem   TEXT NOT NULL,
                    run_numero INTEGER NOT NULL DEFAULT 1,
                    ocorreu_em TEXT NOT NULL
                );

                -- ------------------------------------------------
                -- Conquistas desbloqueadas (INSERT OR IGNORE)
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS conquistas (
                    id             TEXT PRIMARY KEY,
                    nome           TEXT NOT NULL,
                    descricao      TEXT NOT NULL,
                    run_numero     INTEGER NOT NULL DEFAULT 1,
                    desbloqueou_em TEXT NOT NULL
                );

                -- ------------------------------------------------
                -- Histórico de prestígios (uma linha por run concluída)
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS prestigios (
                    run_numero      INTEGER PRIMARY KEY,
                    ouro_total      REAL    NOT NULL,
                    escravos_total  INTEGER NOT NULL,
                    mortos_total    INTEGER NOT NULL,
                    filhos_nascidos INTEGER NOT NULL,
                    tempo_jogo      REAL    NOT NULL,
                    almas_ganhas    INTEGER NOT NULL,
                    bonus_obtido    REAL    NOT NULL,
                    completado_em   TEXT    NOT NULL
                );

                -- ------------------------------------------------
                -- Sessões de jogo
                -- ------------------------------------------------
                CREATE TABLE IF NOT EXISTS sessoes (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_numero       INTEGER NOT NULL DEFAULT 1,
                    iniciou_em       TEXT    NOT NULL,
                    encerrou_em      TEXT,
                    tempo_jogado     REAL,
                    ouro_ao_iniciar  REAL    NOT NULL DEFAULT 0,
                    ouro_ao_encerrar REAL
                );

                -- ------------------------------------------------
                -- Índices para queries analíticas
                -- ------------------------------------------------
                CREATE INDEX IF NOT EXISTS idx_escravos_run   ON escravos  (run_numero);
                CREATE INDEX IF NOT EXISTS idx_mortes_run     ON mortes    (run_numero);
                CREATE INDEX IF NOT EXISTS idx_mortes_causa   ON mortes    (causa);
                CREATE INDEX IF NOT EXISTS idx_mineracao_run  ON mineracao (run_numero);
                CREATE INDEX IF NOT EXISTS idx_mineracao_rec  ON mineracao (recurso);
                CREATE INDEX IF NOT EXISTS idx_eventos_run    ON eventos   (run_numero);
            """)

    # ------------------------------------------------------------------
    # SAVE / LOAD do estado do jogo
    # ------------------------------------------------------------------

    def save_state(self, data: dict) -> bool:
        """Serializa o dicionário do jogo e sobrescreve a linha singleton."""
        try:
            payload = json.dumps(data, ensure_ascii=False)
            now     = datetime.now().isoformat(timespec="seconds")
            with self.conn:
                self.conn.execute("""
                    INSERT INTO game_state (id, data, version, saved_at)
                    VALUES (1, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        data     = excluded.data,
                        version  = excluded.version,
                        saved_at = excluded.saved_at
                """, (payload, self.VERSION, now))
            return True
        except Exception as exc:
            print(f"[DB] save_state: {exc}")
            return False

    def load_state(self) -> dict | None:
        """Carrega o estado salvo; retorna None se não existir."""
        try:
            row = self.conn.execute(
                "SELECT data FROM game_state WHERE id = 1"
            ).fetchone()
            return json.loads(row["data"]) if row else None
        except Exception as exc:
            print(f"[DB] load_state: {exc}")
            return None

    def last_save_time(self) -> str:
        """Retorna a data/hora do último save ou string vazia."""
        try:
            row = self.conn.execute(
                "SELECT saved_at FROM game_state WHERE id = 1"
            ).fetchone()
            return row["saved_at"] if row else ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # ESCRAVOS
    # ------------------------------------------------------------------

    def registrar_escravo(self, escravo, run: int, origem: str = "comprado",
                           pai_id: int | None = None, mae_id: int | None = None):
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO escravos
                        (slave_id, uid, nome, genero, idade,
                         forca, velocidade, resistencia, fertilidade, sorte, lealdade,
                         vida_max, raridade, origem, pai_id, mae_id,
                         run_numero, registrado_em)
                    VALUES (?,?,?,?,?, ?,?,?,?,?,?, ?,?,?,?,?, ?,?)
                """, (
                    escravo.id, escravo.uid, escravo.nome, escravo.genero, escravo.idade,
                    escravo.forca, escravo.velocidade, escravo.resistencia,
                    escravo.fertilidade, escravo.sorte, escravo.lealdade,
                    escravo.vida_max, escravo.raridade_geral(), origem,
                    pai_id, mae_id, run,
                    datetime.now().isoformat(timespec="seconds"),
                ))
        except Exception as exc:
            print(f"[DB] registrar_escravo: {exc}")

    def registrar_morte(self, escravo, run: int):
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO mortes
                        (slave_id, slave_nome, causa, tempo_na_mina,
                         valor_produzido, run_numero, morreu_em)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    escravo.id, escravo.nome,
                    escravo.causa_morte or "Desconhecida",
                    round(escravo.tempo_na_mina, 2),
                    escravo.valor_total,
                    run,
                    datetime.now().isoformat(timespec="seconds"),
                ))
        except Exception as exc:
            print(f"[DB] registrar_morte: {exc}")

    # ------------------------------------------------------------------
    # MINERAÇÃO (batch para não bater no disco a cada 5 s)
    # ------------------------------------------------------------------

    def flush_mineracao(self, batch: list[tuple], run: int):
        """
        Insere lista de (slave_id, slave_nome, recurso, qtd, valor)
        e limita a tabela a MAX_MINING_ROWS registros.
        """
        if not batch:
            return
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with self.conn:
                self.conn.executemany("""
                    INSERT INTO mineracao
                        (slave_id, slave_nome, recurso, quantidade, valor, run_numero, criado_em)
                    VALUES (?,?,?,?,?,?,?)
                """, [(*item, run, now) for item in batch])

                # Janela deslizante: remove os mais antigos
                self.conn.execute(f"""
                    DELETE FROM mineracao
                    WHERE id NOT IN (
                        SELECT id FROM mineracao ORDER BY id DESC LIMIT {self.MAX_MINING_ROWS}
                    )
                """)
        except Exception as exc:
            print(f"[DB] flush_mineracao: {exc}")

    # ------------------------------------------------------------------
    # EVENTOS ALEATÓRIOS
    # ------------------------------------------------------------------

    def log_evento(self, tipo: str, mensagem: str, run: int):
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO eventos (tipo, mensagem, run_numero, ocorreu_em)
                    VALUES (?,?,?,?)
                """, (tipo, mensagem, run, datetime.now().isoformat(timespec="seconds")))
        except Exception as exc:
            print(f"[DB] log_evento: {exc}")

    # ------------------------------------------------------------------
    # CONQUISTAS
    # ------------------------------------------------------------------

    def registrar_conquista(self, ach_id: str, nome: str, desc: str, run: int):
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR IGNORE INTO conquistas
                        (id, nome, descricao, run_numero, desbloqueou_em)
                    VALUES (?,?,?,?,?)
                """, (ach_id, nome, desc, run, datetime.now().isoformat(timespec="seconds")))
        except Exception as exc:
            print(f"[DB] registrar_conquista: {exc}")

    # ------------------------------------------------------------------
    # PRESTÍGIO
    # ------------------------------------------------------------------

    def registrar_prestigio(self, run: int, stats: dict, almas: int, bonus: float):
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO prestigios
                        (run_numero, ouro_total, escravos_total, mortos_total,
                         filhos_nascidos, tempo_jogo, almas_ganhas, bonus_obtido, completado_em)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    run,
                    stats.get("ouro_total", 0),
                    stats.get("escravos_total", 0),
                    stats.get("mortos_total", 0),
                    stats.get("filhos_nascidos", 0),
                    stats.get("tempo_total_jogo", 0),
                    almas, bonus,
                    datetime.now().isoformat(timespec="seconds"),
                ))
        except Exception as exc:
            print(f"[DB] registrar_prestigio: {exc}")

    # ------------------------------------------------------------------
    # SESSÕES
    # ------------------------------------------------------------------

    def iniciar_sessao(self, run: int, ouro: float) -> int:
        try:
            with self.conn:
                cur = self.conn.execute("""
                    INSERT INTO sessoes (run_numero, iniciou_em, ouro_ao_iniciar)
                    VALUES (?,?,?)
                """, (run, datetime.now().isoformat(timespec="seconds"), ouro))
                return cur.lastrowid or -1
        except Exception as exc:
            print(f"[DB] iniciar_sessao: {exc}")
            return -1

    def encerrar_sessao(self, sid: int, tempo: float, ouro: float):
        if sid < 0:
            return
        try:
            with self.conn:
                self.conn.execute("""
                    UPDATE sessoes
                    SET encerrou_em = ?, tempo_jogado = ?, ouro_ao_encerrar = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(timespec="seconds"), round(tempo, 1), ouro, sid))
        except Exception as exc:
            print(f"[DB] encerrar_sessao: {exc}")

    # ------------------------------------------------------------------
    # QUERIES ANALÍTICAS
    # ------------------------------------------------------------------

    def stats_globais(self) -> dict:
        """Estatísticas agregadas de todo o histórico gravado no banco."""
        try:
            c = self.conn
            esc   = c.execute("SELECT COUNT(*) FROM escravos").fetchone()[0]
            mort  = c.execute("SELECT COUNT(*) FROM mortes").fetchone()[0]
            prest = c.execute("SELECT COUNT(*) FROM prestigios").fetchone()[0]
            tempo = c.execute("SELECT COALESCE(SUM(tempo_jogado),0) FROM sessoes").fetchone()[0]

            top_causa = c.execute("""
                SELECT causa, COUNT(*) n FROM mortes
                GROUP BY causa ORDER BY n DESC LIMIT 1
            """).fetchone()

            top_rec = c.execute("""
                SELECT recurso, SUM(quantidade) total FROM mineracao
                GROUP BY recurso ORDER BY total DESC LIMIT 1
            """).fetchone()

            return {
                "escravos_criados":     esc,
                "mortes_totais":        mort,
                "prestigios":           prest,
                "tempo_total_h":        round(tempo / 3600, 2),
                "causa_morte_top":      dict(top_causa) if top_causa else {},
                "recurso_mais_minado":  dict(top_rec)   if top_rec   else {},
            }
        except Exception as exc:
            print(f"[DB] stats_globais: {exc}")
            return {}

    def melhores_escravos(self, limit: int = 10) -> list[dict]:
        """Top escravos por valor total produzido (cruzando escravos × mortes)."""
        try:
            rows = self.conn.execute("""
                SELECT e.nome, e.genero, e.raridade,
                       e.forca, e.resistencia, e.sorte,
                       m.valor_produzido, m.causa, m.tempo_na_mina, e.run_numero
                FROM escravos e
                JOIN mortes m ON e.slave_id = m.slave_id AND e.run_numero = m.run_numero
                ORDER BY m.valor_produzido DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as exc:
            print(f"[DB] melhores_escravos: {exc}")
            return []

    def historico_mineracao(self, recurso: str | None = None, limit: int = 50) -> list[dict]:
        """Últimos eventos de mineração, filtrável por recurso."""
        try:
            if recurso:
                rows = self.conn.execute("""
                    SELECT slave_nome, recurso, quantidade, valor, criado_em
                    FROM mineracao WHERE recurso = ?
                    ORDER BY id DESC LIMIT ?
                """, (recurso, limit)).fetchall()
            else:
                rows = self.conn.execute("""
                    SELECT slave_nome, recurso, quantidade, valor, criado_em
                    FROM mineracao ORDER BY id DESC LIMIT ?
                """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as exc:
            print(f"[DB] historico_mineracao: {exc}")
            return []

    def resumo_por_recurso(self) -> list[dict]:
        """Total histórico minerado, agrupado por tipo de recurso."""
        try:
            rows = self.conn.execute("""
                SELECT recurso,
                       SUM(quantidade) AS total_qtd,
                       SUM(valor)      AS total_valor,
                       COUNT(*)        AS num_eventos
                FROM mineracao
                GROUP BY recurso
                ORDER BY total_valor DESC
            """).fetchall()
            return [dict(r) for r in rows]
        except Exception as exc:
            print(f"[DB] resumo_por_recurso: {exc}")
            return []

    def historico_prestigios(self) -> list[dict]:
        """Todas as runs de prestígio concluídas."""
        try:
            rows = self.conn.execute(
                "SELECT * FROM prestigios ORDER BY run_numero"
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as exc:
            print(f"[DB] historico_prestigios: {exc}")
            return []

    def historico_eventos(self, limit: int = 50) -> list[dict]:
        """Últimos eventos aleatórios registrados."""
        try:
            rows = self.conn.execute("""
                SELECT tipo, mensagem, run_numero, ocorreu_em
                FROM eventos ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as exc:
            print(f"[DB] historico_eventos: {exc}")
            return []

    # ------------------------------------------------------------------
    # Utilitário
    # ------------------------------------------------------------------

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.contexts.configuration.infrastructure.app_paths import get_rules_path
from src.contexts.shared.constants import (
    AUTOSAVE_INTERVAL,
    BREEDING_INTERVAL,
    DISEASE_BASE_CHANCE,
    DISEASE_DURATION,
    EVENT_INTERVAL,
    FOOD_CHECK_INTERVAL,
    FOOD_COST_BASIC,
    FOOD_COST_QUALITY,
    GROWTH_TIME,
    MINING_INTERVAL,
    PRESTIGE_GOLD_REQ,
    RANDOM_EVENTS,
    SHOP_REFRESH_TIME,
)


DEFAULT_RULES = {
    "initial_gold": 250.0,
    "shop_refresh_base_cost": 50.0,
    "mining_interval": MINING_INTERVAL,
    "breeding_interval": BREEDING_INTERVAL,
    "growth_time": GROWTH_TIME,
    "autosave_interval": AUTOSAVE_INTERVAL,
    "event_interval": EVENT_INTERVAL,
    "shop_refresh_time": SHOP_REFRESH_TIME,
    "food_check_interval": FOOD_CHECK_INTERVAL,
    "food_cost_basic": FOOD_COST_BASIC,
    "food_cost_quality": FOOD_COST_QUALITY,
    "disease_base_chance": DISEASE_BASE_CHANCE,
    "disease_duration": DISEASE_DURATION,
    "prestige_gold_req": float(PRESTIGE_GOLD_REQ),
    "black_market_duration": 60.0,
    "event_chances": {event["id"]: float(event["chance"]) for event in RANDOM_EVENTS},
}


RULE_SECTIONS = [
    {
        "title": "Economia",
        "fields": [
            {
                "path": "initial_gold",
                "label": "Ouro inicial",
                "type": "float",
                "min": 0.0,
                "max": 1_000_000.0,
                "step": 10.0,
            },
            {
                "path": "shop_refresh_base_cost",
                "label": "Custo base do refresh da loja",
                "type": "float",
                "min": 0.0,
                "max": 50_000.0,
                "step": 5.0,
            },
            {
                "path": "prestige_gold_req",
                "label": "Ouro total exigido para prestigio",
                "type": "float",
                "min": 1.0,
                "max": 100_000_000.0,
                "step": 1_000.0,
            },
        ],
    },
    {
        "title": "Tempos",
        "fields": [
            {
                "path": "mining_interval",
                "label": "Intervalo base de mineracao (s)",
                "type": "float",
                "min": 0.1,
                "max": 600.0,
                "step": 0.1,
            },
            {
                "path": "breeding_interval",
                "label": "Intervalo de reproducao (s)",
                "type": "float",
                "min": 1.0,
                "max": 3_600.0,
                "step": 1.0,
            },
            {
                "path": "growth_time",
                "label": "Tempo de crescimento do bebe (s)",
                "type": "float",
                "min": 1.0,
                "max": 10_000.0,
                "step": 1.0,
            },
            {
                "path": "autosave_interval",
                "label": "Autosave (s)",
                "type": "float",
                "min": 5.0,
                "max": 3_600.0,
                "step": 5.0,
            },
            {
                "path": "event_interval",
                "label": "Intervalo entre eventos (s)",
                "type": "float",
                "min": 5.0,
                "max": 3_600.0,
                "step": 5.0,
            },
            {
                "path": "shop_refresh_time",
                "label": "Cooldown de refresh automatico da loja (s)",
                "type": "float",
                "min": 5.0,
                "max": 10_000.0,
                "step": 5.0,
            },
            {
                "path": "black_market_duration",
                "label": "Duracao do mercado negro (s)",
                "type": "float",
                "min": 1.0,
                "max": 3_600.0,
                "step": 1.0,
            },
        ],
    },
    {
        "title": "Alimentacao e Doenca",
        "fields": [
            {
                "path": "food_check_interval",
                "label": "Intervalo de cobranca de comida (s)",
                "type": "float",
                "min": 1.0,
                "max": 10_000.0,
                "step": 1.0,
            },
            {
                "path": "food_cost_basic",
                "label": "Custo da comida basica",
                "type": "float",
                "min": 0.0,
                "max": 100_000.0,
                "step": 1.0,
            },
            {
                "path": "food_cost_quality",
                "label": "Custo da comida de qualidade",
                "type": "float",
                "min": 0.0,
                "max": 100_000.0,
                "step": 1.0,
            },
            {
                "path": "disease_base_chance",
                "label": "Chance base de doenca",
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "step": 0.001,
            },
            {
                "path": "disease_duration",
                "label": "Duracao da doenca (s)",
                "type": "float",
                "min": 1.0,
                "max": 10_000.0,
                "step": 1.0,
            },
        ],
    },
    {
        "title": "Eventos",
        "fields": [
            {
                "path": f"event_chances.{event['id']}",
                "label": f"Chance: {event['nome']}",
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "step": 0.001,
            }
            for event in RANDOM_EVENTS
        ],
    },
]


RULE_SPECS = {
    field["path"]: field
    for section in RULE_SECTIONS
    for field in section["fields"]
}


def _rules_path() -> Path:
    return get_rules_path()


def get_rule_value(rules: dict[str, Any], path: str) -> Any:
    current: Any = rules
    for part in path.split("."):
        current = current[part]
    return current


def set_rule_value(rules: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current: Any = rules
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _coerce_value(path: str, value: Any) -> float | int:
    spec = RULE_SPECS[path]
    number = float(value)
    number = max(spec["min"], min(spec["max"], number))
    if spec["type"] == "int":
        return int(round(number))
    return number


def normalize_rules(raw_rules: dict[str, Any] | None) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_RULES)
    if not isinstance(raw_rules, dict):
        return normalized

    for path in RULE_SPECS:
        try:
            raw_value = get_rule_value(raw_rules, path)
        except (KeyError, TypeError):
            continue

        try:
            coerced = _coerce_value(path, raw_value)
        except (TypeError, ValueError):
            continue

        set_rule_value(normalized, path, coerced)

    return normalized


def load_rules() -> dict[str, Any]:
    path = _rules_path()
    if not path.exists():
        return deepcopy(DEFAULT_RULES)

    try:
        with path.open("r", encoding="utf-8") as file:
            return normalize_rules(json.load(file))
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_RULES)


def save_rules(rules: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_rules(rules)
    path = _rules_path()
    with path.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)
    return normalized


def reset_rules_file() -> dict[str, Any]:
    return save_rules(DEFAULT_RULES)

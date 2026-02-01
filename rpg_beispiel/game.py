from __future__ import annotations

import random
import os
import time
import subprocess
import sys
from collections import OrderedDict, Counter
from pathlib import Path

from i18n_wrapper import I18nEngine

BASE_DIR = Path(__file__).resolve().parent
BASE_CATALOG = BASE_DIR / "rpg_catalog.txt"
RUNTIME_CATALOG = BASE_DIR / "_runtime_catalog.txt"
RUNTIME_CATALOG_BIN = BASE_DIR / "_runtime_catalog.i18n"
LOGBOOK_FILE = BASE_DIR / "knowledge.bin"

SHARD_TOKENS = ["000W10", "000W11"]
DEFAULT_SHARD_TOKEN = SHARD_TOKENS[0]
DEFAULT_SECTOR_ID = "000W10"
CATALOG_CACHE = {}
sector_registry = OrderedDict()
STORY_DIR = BASE_DIR / "story_chapters"
DEFAULT_STORY_CHAPTER = 1


def update_catalog_cache_from_text(raw_text: str):
    CATALOG_CACHE.clear()
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("@") or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        CATALOG_CACHE[key.strip()] = value.strip()


def ensure_catalog_cache():
    if CATALOG_CACHE:
        return
    source = RUNTIME_CATALOG if RUNTIME_CATALOG.exists() else BASE_CATALOG
    if not source.exists():
        return
    text = source.read_text(encoding="utf-8")
    update_catalog_cache_from_text(text)


def catalog_lookup(token: str):
    ensure_catalog_cache()
    return CATALOG_CACHE.get(token)


def resolve_catalog_token(engine: I18nEngine, token: str):
    raw = engine.translate(token)
    if "⟦" not in raw:
        return raw
    fallback = catalog_lookup(token)
    return fallback or raw


def translate_with_fallback(engine: I18nEngine, token: str, args=None):
    text = resolve_catalog_token(engine, token)
    if args:
        for idx, arg in enumerate(args):
            text = text.replace(f"%{idx}", str(arg))
    return text

TRAIT_CONFIG = [
    {
        "id": "000E10",
        "cost": 250,
        "stability_penalty": 20,
        "damage_mul": 1.5,
        "name_token": "000E10",
        "desc_token": "000E12",
        "module_token": "000M01",
    },
    {
        "id": "000E11",
        "cost": 300,
        "stability_penalty": 0,
        "damage_mul": 1.2,
        "name_token": "000E11",
        "desc_token": "000E13",
        "module_token": "000M03",
    }
]

KNOWLEDGE_PACKAGES = {
    "pkg_alpha": {
        "file": BASE_DIR / "knowledge" / "knowledge_package_1.txt",
        "release": BASE_DIR / "knowledge" / "knowledge_package_1.i18n",
        "cost": 400,
        "tokens": ["000E20", "000E21", "000E22"],
    },
    "pkg_delta": {
        "file": BASE_DIR / "knowledge" / "knowledge_package_2.txt",
        "release": BASE_DIR / "knowledge" / "knowledge_package_2.i18n",
        "cost": 500,
        "tokens": ["000E23", "000E24", "000E25"],
    }
}

LOADED_KNOWLEDGE = set()
WORLD_EVENT_STATE_FILE = BASE_DIR / "world_event.raw"
EVENTS_DIR = BASE_DIR / "events"
ACTIVE_WORLD_EVENT_TOKEN = None

WORLD_EVENTS = {
    "000E99": {
        "name_token": "000E99",
        "file": EVENTS_DIR / "world_collapse.txt",
        "stability_shift": -25,
        "physics_bonus": 12,
        "battle_message_token": "000W97",
        "activation_token": "000W94",
    },
    "000E98": {
        "name_token": "000E98",
        "file": EVENTS_DIR / "world_aurora.txt",
        "stability_shift": 10,
        "physics_bonus": 5,
        "battle_message_token": "000W98",
        "activation_token": "000W96",
    },
}

UI_TOKENS = {
    "sector_discovered": "000W60",
    "shard_loaded": "000W61",
    "module_executed": "000W62",
    "inventory_header": "000W63",
    "inventory_empty": "000W64",
    "equipment_label": "000W65",
    "label_none": "000W66",
    "items_label": "000W67",
    "inventory_select_prompt": "000W68",
    "inventory_entry": "000W69",
    "inventory_equipped": "000W6A",
    "inventory_no_items": "000W6B",
    "resources_label": "000W6C",
    "resource_entry": "000W6D",
    "market_header": "000W6E",
    "price_factor": "000W6F",
    "market_prompt": "000W70",
    "market_no_items": "000W71",
    "market_item_entry": "000W72",
    "market_item_prompt": "000W73",
    "market_item_bought": "000W74",
    "market_no_resources": "000W75",
    "resource_prompt": "000W76",
    "resource_sold": "000W77",
    "invalid_selection": "000W78",
    "no_recipes": "000W79",
    "craft_header": "000W7A",
    "craft_entry": "000W7B",
    "craft_prompt": "000W7C",
    "craft_missing": "000W7D",
    "craft_success": "000W7E",
    "skills_header": "000W7F",
    "skill_entry": "000W80",
    "skill_prompt": "000W81",
    "skill_activated": "000W82",
    "skill_already": "000W83",
    "skill_prereq": "000W84",
    "boss_prompt": "000W85",
    "status_line": "000W86",
    "location_line": "000W87",
    "achievements_line": "000W88",
    "token_status_header": "000W89",
    "inventory_list_label": "000W8A",
    "inventory_empty_line": "000W8B",
    "skills_list_line": "000W8C",
    "skills_none_line": "000W8D",
    "inventory_hint": "000W8E",
    "sector_entry": "000W8F",
    "resource_filtered": "000W90",
    "skill_unlocked": "000W91",
    "full_hit": "000W92",
    "repair_action": "000W93",
    "boss_phase": "000W94",
    "current_marker": "000W95",
    "story_progress": "000W96",
    "story_header": "000W97",
    "story_no_chapters": "000W98",
    "story_node": "000WB3",
    "matrix_exit": "000WAE",
    "error_generic": "000WAF",
    "error_catalog": "000WB0",
    "battle_status": "000WB1",
}

SECTOR_NAME_TOKENS = {
    "alpha_prime": "000W5A",
    "daten_wuste": "000W5B",
    "nebula_drift": "000W5C",
    "iron_bastion": "000W5D",
    "pulse_abyss": "000W5E",
    "core": "000WA3",
}

SECTOR_TYPE_TOKENS = {
    "cosmic": "000WA0",
    "industrial": "000WA1",
    "corrupted": "000WA2",
    "matrix": "000WA4",
}

SKILL_STATUS_TOKENS = {
    "learned": "000WA5",
    "available": "000WA6",
    "active": "000WA7",
}

FACTION_SOURCE_TOKENS = {
    "sector": "000WA8",
    "world_event": "000WA9",
    "knowledge": "000WAA",
}

def resolve_player_shard_name(engine: I18nEngine, player: Player):
    token = getattr(player, "shard_name_token", None)
    if token:
        return translate_with_fallback(engine, token)
    return ""


def resolve_player_shard_type(engine: I18nEngine, player: Player):
    token = getattr(player, "shard_type_token", None)
    if token:
        return translate_with_fallback(engine, token)
    return ""

SECTOR_TEMPLATES = [
    {
        "name_token": SECTOR_NAME_TOKENS["nebula_drift"],
        "type_token": SECTOR_TYPE_TOKENS["cosmic"],
        "difficulty": 2,
        "level_req": 6,
        "description_token": "000W52",
    },
    {
        "name_token": SECTOR_NAME_TOKENS["iron_bastion"],
        "type_token": SECTOR_TYPE_TOKENS["industrial"],
        "difficulty": 3,
        "level_req": 9,
        "description_token": "000W53",
    },
    {
        "name_token": SECTOR_NAME_TOKENS["pulse_abyss"],
        "type_token": SECTOR_TYPE_TOKENS["corrupted"],
        "difficulty": 4,
        "level_req": 12,
        "description_token": "000W54",
    },
]

MARKET_PRICE_TOKEN = "000B200"
ITEM_SLOT_KEYS = ["weapon"]
DEFAULT_INVENTORY_TOKENS = ["000I100", "000N50"]
DEFAULT_EQUIPPED_ITEMS = {"weapon": "000I100"}
DEFAULT_SKILL_TOKENS = ["000K101"]
DEFAULT_ACTIVE_SKILL = None

SECTOR_RESOURCE_NODES = {
    "000W10": ["000N50", "000N51", "000N52"],
    "000W11": ["000N52", "000N53", "000N54"],
}
DEFAULT_RESOURCE_POOL = ["000N50", "000N51", "000N52", "000N53", "000N54"]

RESOURCE_BASE_VALUES = {
    "000N50": 45,
    "000N51": 35,
    "000N52": 60,
    "000N53": 25,
    "000N54": 30,
}

SKILL_TREE = {
    "000K101": {"desc_token": "000K10", "cost": 180, "type": "passive"},
    "000K102": {"desc_token": "000K11", "cost": 320, "type": "passive", "prereq": "000K101"},
    "000K200": {"desc_token": "000K12", "cost": 420, "type": "active"},
}

RECIPE_TOKENS = ["000C100", "000C101"]

CALR_TEMPLATES = {
    "core_collective": {
        "label_token": "000R50",
        "fragments": ["000R10", "000R11"],
        "threshold": 10,
        "priority": 1,
    },
    "aurora_syndicate": {
        "label_token": "000R51",
        "fragments": ["000R12", "000R13"],
        "threshold": 8,
        "priority": 2,
    },
}

CALR_EVENT_BINDINGS = {
    "000E99": "core_collective",
    "000E98": "aurora_syndicate",
}

CALR_KNOWLEDGE_FRAGMENTS = {
    "000E20": "000R20",
    "000E21": "000R21",
    "000E23": "000R22",
}

dynamic_sector_counter = 0


def register_sector_entry(sector_id, name_token, type_token, token=None, file=None, difficulty=0, level_offset=0, description_token=None, dynamic=False):
    sector_registry[sector_id] = {
        "name_token": name_token,
        "type_token": type_token,
        "token": token,
        "file": file,
        "difficulty": difficulty,
        "level_offset": level_offset,
        "description_token": description_token,
        "dynamic": dynamic,
    }


def init_sector_registry():
    sector_registry.clear()
    register_sector_entry(
        "000W10",
        SECTOR_NAME_TOKENS["alpha_prime"],
        SECTOR_TYPE_TOKENS["industrial"],
        token="000W10",
        file=BASE_DIR / "sector_alpha.txt",
        difficulty=0,
        level_offset=0,
        description_token="000W50",
    )
    register_sector_entry(
        "000W11",
        SECTOR_NAME_TOKENS["daten_wuste"],
        SECTOR_TYPE_TOKENS["corrupted"],
        token="000W11",
        file=BASE_DIR / "sector_wasteland.txt",
        difficulty=1,
        level_offset=1,
        description_token="000W51",
    )
 
init_sector_registry()


def set_sector_from_registry(engine: I18nEngine, player: Player, sector_id: str, announce=False):
    info = sector_registry.get(sector_id)
    if not info:
        return False
    player.current_sector_id = sector_id
    if info.get("name_token"):
        player.shard_name_token = info["name_token"]
    if info.get("type_token"):
        player.shard_type_token = info["type_token"]
    player.current_shard_file = info.get("file")
    if info.get("token"):
        player.current_shard_token = info["token"]
    if announce:
        description_token = info.get("description_token")
        if description_token:
            print(translate_with_fallback(engine, description_token))
    return True


def generate_dynamic_sector(template):
    global dynamic_sector_counter
    dynamic_sector_counter += 1
    sector_id = f"DYN{dynamic_sector_counter:02d}"
    register_sector_entry(
        sector_id,
        template["name_token"],
        template["type_token"],
        file=None,
        difficulty=template["difficulty"],
        level_offset=template["difficulty"],
        description_token=template.get("description_token"),
        dynamic=True,
    )
    return sector_id


def expand_sectors_for_level(player: Player, engine: I18nEngine):
    for template in SECTOR_TEMPLATES:
        exists = any(info.get("name_token") == template["name_token"] for info in sector_registry.values())
        if player.lvl >= template["level_req"] and not exists:
            new_id = generate_dynamic_sector(template)
            name_label = translate_with_fallback(engine, template["name_token"])
            type_label = translate_with_fallback(engine, template["type_token"])
            print(translate_with_fallback(engine, UI_TOKENS["sector_discovered"], [name_label, type_label]))
            return new_id
    return None


def get_sector_info(player: Player):
    info = sector_registry.get(player.current_sector_id)
    if info:
        return info
    return next(iter(sector_registry.values()), None)


FACTIONS = {
    "core_collective": {
        "name_token": "000G10",
        "desc_token": "000G11",
    },
    "aurora_syndicate": {
        "name_token": "000G12",
        "desc_token": "000G13",
    },
}

SHARD_FACTION_INFLUENCE = {
    "000W10": [("core_collective", 3)],
    "000W11": [("aurora_syndicate", 3)],
}

KNOWLEDGE_FACTION_INFLUENCE = {
    "pkg_alpha": [("core_collective", 7)],
    "pkg_delta": [("aurora_syndicate", 6)],
}

WORLD_EVENT_FACTION_EFFECTS = {
    "000E99": [("core_collective", -5)],
    "000E98": [("aurora_syndicate", 5)],
}

CALR_TEMPLATES = {
    "core_collective": {
        "label_token": "000R50",
        "fragments": ["000R10", "000R11"],
        "threshold": 10,
        "priority": 1,
    },
    "aurora_syndicate": {
        "label_token": "000R51",
        "fragments": ["000R12", "000R13"],
        "threshold": 8,
        "priority": 2,
    },
}

CALR_EVENT_BINDINGS = {
    "000E99": "core_collective",
    "000E98": "aurora_syndicate",
}

CALR_KNOWLEDGE_FRAGMENTS = {
    "000E20": "000R20",
    "000E21": "000R21",
    "000E23": "000R22",
}

KNOWLEDGE_DIALOGUE_MAP = {
    "shop": {
        "000E20": "000W20",
        "000E21": "000W21",
        "000E22": "000W22",
        "000E23": "000W23",
        "000E24": "000W24",
        "000E25": "000W25",
    }
}

class Player:
    def __init__(self, name):
        self.name, self.max_hp, self.hp, self.atk, self.lvl, self.xp = name, 100, 100, 15, 1, 0
        self.crit_chance, self.kits, self.kills, self.credits = 0.1, 1, 0, 0
        self.admin_mode = False
        self.inventory_tokens = list(DEFAULT_INVENTORY_TOKENS)
        self.equipped_items = dict(DEFAULT_EQUIPPED_ITEMS)
        self.skill_tokens = list(DEFAULT_SKILL_TOKENS)
        self.active_skill_token = DEFAULT_ACTIVE_SKILL
        self.quest_target, self.quest_kills = 5, 0
        self.achievements = []
        self.traits_active = []
        self.knowledge_packages = []
        self.current_shard_token = DEFAULT_SHARD_TOKEN
        self.current_shard_file = None
        self.shard_name_token = SECTOR_NAME_TOKENS["core"]
        self.shard_type_token = SECTOR_TYPE_TOKENS["matrix"]
        self.current_sector_id = DEFAULT_SECTOR_ID
        self.faction_standing = {k: 0 for k in FACTIONS}
        self.faction_standing = {k: 0 for k in FACTIONS}
        self.story_state = "intro"
        self.story_chapter = DEFAULT_STORY_CHAPTER
        self.story_nodes = {}
        self.story_history = []
        self.story_effects = {}
        self.story_state = "intro"
        self.story_history = []

    def trait_bits(self):
        return "".join("1" if trait["id"] in self.traits_active else "0" for trait in TRAIT_CONFIG)

    def load_traits(self, bit_string):
        for idx, trait in enumerate(TRAIT_CONFIG):
            if idx < len(bit_string) and bit_string[idx] == "1":
                self.traits_active.append(trait["id"])

    def has_trait(self, trait_id):
        return trait_id in self.traits_active

    def trait_stability_penalty(self):
        return sum(
            trait["stability_penalty"]
            for trait in TRAIT_CONFIG
            if trait["id"] in self.traits_active
        )

    def trait_damage_multiplier(self):
        mult = 1.0
        for trait in TRAIT_CONFIG:
            if trait["id"] in self.traits_active:
                mult *= trait.get("damage_mul", 1.0)
        return mult

    def save_game(self, engine):
        achs = ";".join(self.achievements)
        traits_bits = self.trait_bits()
        knowledge_str = ";".join(self.knowledge_packages)
        faction_str = ";".join(f"{k}:{int(self.faction_standing.get(k,0))}" for k in sorted(FACTIONS))
        sector_id = self.current_sector_id or DEFAULT_SECTOR_ID
        inventory_str = ";".join(self.inventory_tokens)
        equipped_str = ";".join(f"{slot}:{token}" for slot, token in self.equipped_items.items())
        skill_str = ";".join(self.skill_tokens)
        active_skill = self.active_skill_token or ""
        data = ",".join([
            str(int(self.lvl)),
            str(int(self.xp)),
            str(int(self.hp)),
            str(int(self.max_hp)),
            str(int(self.atk)),
            str(int(self.credits)),
            str(int(self.kills)),
            str(int(self.kits)),
            str(int(self.quest_target)),
            str(int(self.quest_kills)),
            achs,
            traits_bits,
            knowledge_str,
            faction_str,
            self.current_shard_token or DEFAULT_SHARD_TOKEN,
            sector_id,
            self.story_state,
            str(self.story_chapter),
            inventory_str,
            equipped_str,
            skill_str,
            active_skill,
        ])
        with open("savegame.raw", "w") as f: f.write(data)
        print(engine.translate("000107"))

    @staticmethod
    def load_game():
        if not os.path.exists("savegame.raw"): return None
        try:
            with open("savegame.raw", "r") as f:
                d = f.read().split(",")
                p = Player("Operator")
                v = list(map(float, d[:10]))
                p.lvl, p.xp, p.hp, p.max_hp, p.atk, p.credits, p.kills, p.kits, p.quest_target, p.quest_kills = v
                p.lvl, p.kills, p.kits = int(p.lvl), int(p.kills), int(p.kits)
                if len(d) > 10 and d[10]: p.achievements = d[10].split(";")
                if len(d) > 11:
                    p.load_traits(d[11])
                if len(d) > 12 and d[12]:
                    p.knowledge_packages = d[12].split(";")
                shard_token = ""
                if len(d) > 13:
                    faction_data = d[13]
                    if ":" in faction_data or ";" in faction_data:
                        for entry in faction_data.split(";"):
                            if ":" in entry:
                                key, value = entry.split(":", 1)
                                if key in FACTIONS:
                                    p.faction_standing[key] = int(value)
                        if len(d) > 14 and d[14]:
                            shard_token = d[14]
                        elif faction_data and ":" not in faction_data:
                            shard_token = faction_data
                    else:
                        shard_token = faction_data
                if not shard_token and len(d) > 14 and d[14]:
                    shard_token = d[14]
                if shard_token:
                    p.current_shard_token = shard_token
                if len(d) > 16 and d[16]:
                    p.story_state = d[16]
                if len(d) > 17 and d[17]:
                    try:
                        p.story_chapter = int(d[17])
                    except ValueError:
                        pass
                if len(d) > 18 and d[18]:
                    p.inventory_tokens = [tok for tok in d[18].split(";") if tok]
                if len(d) > 19 and d[19]:
                    for entry in d[19].split(";"):
                        if ":" in entry:
                            slot, tok = entry.split(":", 1)
                            p.equipped_items[slot] = tok
                if len(d) > 20 and d[20]:
                    p.skill_tokens = [tok for tok in d[20].split(";") if tok]
                if len(d) > 21 and d[21]:
                    p.active_skill_token = d[21]
                return p
        except: return None


def create_binary_package(txt_path: Path, out_path: Path) -> bool:
    script = BASE_DIR.parent / "i18n_crypt.py"
    if not script.exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--strict", str(txt_path), str(out_path)],
            check=False,
            cwd=BASE_DIR.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0 and out_path.exists()
    except Exception:
        return False


def load_knowledge_package(engine: I18nEngine, pkg_id: str):
    if pkg_id in LOADED_KNOWLEDGE or pkg_id not in KNOWLEDGE_PACKAGES:
        return
    pkg = KNOWLEDGE_PACKAGES[pkg_id]
    create_binary_package(pkg["file"], pkg["release"])
    LOADED_KNOWLEDGE.add(pkg_id)


def trait_message(engine: I18nEngine, player: Player):
    if not player.traits_active:
        return None
    parsed = []
    for trait_id in player.traits_active:
        text = engine.translate(trait_id)
        name = text.split("|", 1)[0]
        parsed.append(name)
    return "Traits: " + ", ".join(parsed)


def knowledge_messages(engine: I18nEngine, player: Player):
    if not player.knowledge_packages:
        return []
    messages = []
    for pkg_id in player.knowledge_packages:
        pkg = KNOWLEDGE_PACKAGES.get(pkg_id)
        if not pkg:
            continue
        for token in pkg["tokens"]:
            messages.append(engine.translate(token))
    entries = read_logbook_entries()
    for pkg_id, tokens in entries:
        if pkg_id not in player.knowledge_packages:
            continue
        resolved = ", ".join(engine.translate(tok) for tok in tokens)
        messages.append(f"[LOGBUCH] {pkg_id}: {resolved}")
    return messages


def player_known_tokens(player: Player):
    tokens = []
    for pkg_id in player.knowledge_packages:
        pkg = KNOWLEDGE_PACKAGES.get(pkg_id)
        if pkg:
            tokens.extend(pkg["tokens"])
    entries = read_logbook_entries()
    for pkg_id, token_list in entries:
        if pkg_id in player.knowledge_packages:
            tokens.extend(token_list)
    seen = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    for skill in player.skill_tokens:
        if skill not in seen:
            seen.append(skill)
    return seen


def knowledge_dialogue_lines(engine: I18nEngine, player: Player, context: str):
    mapping = KNOWLEDGE_DIALOGUE_MAP.get(context, {})
    if not mapping:
        return []
    lines = []
    tokens = player_known_tokens(player)
    for token in tokens:
        response = mapping.get(token)
        if response:
            text = translate_with_fallback(engine, response)
            if text not in lines:
                lines.append(text)
    return lines


def core_stabilizer_effect(player: Player):
    player.hp = min(player.max_hp, player.hp + 15)
    player.atk += 3


def aurora_relay_effect(player: Player):
    player.crit_chance = min(1.0, player.crit_chance + 0.1)
    player.kits += 1


def compose_calr_script(engine: I18nEngine, player: Player):
    leaders = []
    for faction_key, template in CALR_TEMPLATES.items():
        standing = player.faction_standing.get(faction_key, 0)
        if standing >= template["threshold"]:
            leaders.append((standing, template))
    event_token = get_active_world_event_token()
    if event_token:
        binding = CALR_EVENT_BINDINGS.get(event_token)
        if binding:
            template = CALR_TEMPLATES.get(binding)
            if template:
                standing = player.faction_standing.get(binding, 0) + 2
                leaders.append((standing, template))
    if not leaders:
        return None
    best = max(leaders, key=lambda item: (item[0], item[1].get("priority", 0)))
    template = best[1]
    fragments = []
    for token_id in template["fragments"]:
        fragments.append(translate_with_fallback(engine, token_id))
    for token in player_known_tokens(player):
        fragment = CALR_KNOWLEDGE_FRAGMENTS.get(token)
        if fragment:
            fragments.append(translate_with_fallback(engine, fragment))
    fragments = [f for f in fragments if f]
    if not fragments:
        return None
    label = translate_with_fallback(engine, template["label_token"])
    return "|".join([label] + fragments)


def adjust_faction(engine: I18nEngine, player: Player, faction_key: str, delta: int, source_token: str | None = None):
    if faction_key not in FACTIONS:
        return
    prev = player.faction_standing.get(faction_key, 0)
    value = prev + delta
    player.faction_standing[faction_key] = value
    name = translate_with_fallback(engine, FACTIONS[faction_key]["name_token"])
    if source_token and source_token.startswith("000"):
        label = translate_with_fallback(engine, source_token)
    else:
        label = source_token or translate_with_fallback(engine, FACTIONS[faction_key]["desc_token"])
    change = f"{delta:+d}"
    print(translate_with_fallback(engine, "000G20", [name, change]))


def apply_faction_influences(engine: I18nEngine, player: Player, influences, source=None):
    for faction_key, delta in influences:
        if delta == 0:
            continue
        adjust_faction(engine, player, faction_key, delta, source)


def faction_status_lines(engine: I18nEngine, player: Player):
    lines = []
    for key, info in FACTIONS.items():
        name = translate_with_fallback(engine, info["name_token"])
        value = player.faction_standing.get(key, 0)
        lines.append(translate_with_fallback(engine, "000G21", [name, value]))
    return lines


FACTION_SHOP_DEALS = [
    {
        "key": "core_stabilizer",
        "name_token": "000C30",
        "faction": "core_collective",
        "threshold": 5,
        "price": 400,
        "discount_threshold": 15,
        "discount": 0.25,
        "effect": core_stabilizer_effect,
    },
    {
        "key": "aurora_relay",
        "name_token": "000C31",
        "faction": "aurora_syndicate",
        "threshold": 5,
        "price": 320,
        "discount_threshold": 10,
        "discount": 0.20,
        "effect": aurora_relay_effect,
    },
]


def compute_deal_price(player: Player, deal):
    standing = player.faction_standing.get(deal["faction"], 0)
    price = deal["price"]
    threshold = deal.get("discount_threshold")
    discount = deal.get("discount", 0)
    if threshold and standing >= threshold:
        price = int(price * (1 - discount))
    return price


def get_available_faction_shop_deals(player: Player):
    result = []
    for deal in FACTION_SHOP_DEALS:
        standing = player.faction_standing.get(deal["faction"], 0)
        if standing >= deal["threshold"]:
            result.append(deal)
    return result
def load_active_world_event_state():
    global ACTIVE_WORLD_EVENT_TOKEN
    if not WORLD_EVENT_STATE_FILE.exists():
        ACTIVE_WORLD_EVENT_TOKEN = None
        return
    token = WORLD_EVENT_STATE_FILE.read_text().strip()
    if token in WORLD_EVENTS:
        ACTIVE_WORLD_EVENT_TOKEN = token
    else:
        ACTIVE_WORLD_EVENT_TOKEN = None


def set_active_world_event(token: str | None):
    global ACTIVE_WORLD_EVENT_TOKEN
    if token and token not in WORLD_EVENTS:
        return False
    ACTIVE_WORLD_EVENT_TOKEN = token
    WORLD_EVENT_STATE_FILE.write_text(token or "")
    return True


def get_active_world_event_token():
    if ACTIVE_WORLD_EVENT_TOKEN and ACTIVE_WORLD_EVENT_TOKEN not in WORLD_EVENTS:
        return None
    return ACTIVE_WORLD_EVENT_TOKEN


def get_active_world_event():
    token = get_active_world_event_token()
    if not token:
        return None
    return WORLD_EVENTS.get(token)


def world_event_menu(engine: I18nEngine, player: Player):
    print("\n" + translate_with_fallback(engine, "000W90"))
    active = get_active_world_event()
    status_label = translate_with_fallback(engine, "000W99") if not active else translate_with_fallback(engine, active["name_token"])
    print(translate_with_fallback(engine, "000W91", [status_label]))
    print(translate_with_fallback(engine, "000W92"))
    active_token = get_active_world_event_token()
    for idx, event_id in enumerate(WORLD_EVENTS, start=1):
        label = translate_with_fallback(engine, WORLD_EVENTS[event_id]["name_token"])
        marker = (
            f" ({translate_with_fallback(engine, SKILL_STATUS_TOKENS['active'])})"
            if event_id == active_token
            else ""
        )
        print(f"({idx}) {label}{marker}")
    print(translate_with_fallback(engine, "000W93"))
    choice = input("> ").strip()
    if choice == "0":
        if active:
            set_active_world_event(None)
            refresh_runtime_catalog(engine, player)
            print(translate_with_fallback(engine, "000W95"))
        return
    if not choice.isdigit():
        return
    target_idx = int(choice) - 1
    if target_idx < 0 or target_idx >= len(WORLD_EVENTS):
        return
    token = list(WORLD_EVENTS.keys())[target_idx]
    if token == get_active_world_event_token():
        print(translate_with_fallback(engine, "000W9A"))
        return
    if set_active_world_event(token):
        refresh_runtime_catalog(engine, player)
        apply_faction_influences(engine, player, WORLD_EVENT_FACTION_EFFECTS.get(token, []), FACTION_SOURCE_TOKENS["world_event"])
        label = translate_with_fallback(engine, WORLD_EVENTS[token]["name_token"])
        print(translate_with_fallback(engine, WORLD_EVENTS[token]["activation_token"], [label]))


def unlock_trait(engine: I18nEngine, player: Player, trait_id: str):
    if player.has_trait(trait_id):
        return False
    player.traits_active.append(trait_id)
    return True


def unlock_knowledge(engine: I18nEngine, player: Player, pkg_id: str):
    if pkg_id in player.knowledge_packages:
        return False
    pkg = KNOWLEDGE_PACKAGES.get(pkg_id)
    if not pkg:
        return False
    load_knowledge_package(engine, pkg_id)
    player.knowledge_packages.append(pkg_id)
    append_logbook_entry(pkg_id, pkg["tokens"])
    refresh_runtime_catalog(engine, player)
    apply_faction_influences(engine, player, KNOWLEDGE_FACTION_INFLUENCE.get(pkg_id, []), FACTION_SOURCE_TOKENS["knowledge"])
    return True


def trait_cost(trait_id: str):
    for trait in TRAIT_CONFIG:
        if trait["id"] == trait_id:
            return trait["cost"]
    return 0


def parse_shard_token(engine: I18nEngine, token_id: str):
    raw = resolve_catalog_token(engine, token_id)
    if "⟦" in raw or "|" not in raw:
        return {}
    parts = raw.split("|")
    info = {"filename": parts[0]}
    for part in parts[1:]:
        if ":" in part:
            key, value = part.split(":", 1)
            info[key] = value
    return info


def apply_shard_token(engine: I18nEngine, player: Player, token_id: str, announce=False):
    info = parse_shard_token(engine, token_id)
    filename = info.get("filename")
    if not filename:
        return False
    shard_path = BASE_DIR / filename
    if not shard_path.exists():
        if announce:
            print(engine.translate("000W05", [filename]))
        return False
    player.current_shard_token = token_id
    player.current_shard_file = shard_path
    success = set_sector_from_registry(engine, player, token_id)
    if announce and success:
        print(
            translate_with_fallback(
                engine,
                UI_TOKENS["shard_loaded"],
                [resolve_player_shard_name(engine, player), resolve_player_shard_type(engine, player)],
            )
        )
    return True


def refresh_runtime_catalog(engine: I18nEngine, player: Player):
    layers = [BASE_CATALOG.read_text()]
    if player.current_shard_file and player.current_shard_file.exists():
        layers.append(player.current_shard_file.read_text())
    for pkg_id in player.knowledge_packages:
        pkg = KNOWLEDGE_PACKAGES.get(pkg_id)
        if pkg and pkg["file"].exists():
            layers.append(pkg["file"].read_text())
    event = get_active_world_event()
    if event:
        path = event.get("file")
        if path and path.exists():
            layers.append(path.read_text())

    story_path = story_chapter_path(player)
    if story_path.exists():
        layers.append(story_path.read_text())
    payload = "\n".join(layers)
    update_catalog_cache_from_text(payload)
    RUNTIME_CATALOG.write_text(payload, encoding="utf-8")
    binary_created = create_binary_package(RUNTIME_CATALOG, RUNTIME_CATALOG_BIN)
    if binary_created and RUNTIME_CATALOG_BIN.exists():
        engine.load_file(str(RUNTIME_CATALOG_BIN))
    else:
        engine.load_file(str(RUNTIME_CATALOG))
    load_story_nodes(player)


def show_navigation(engine: I18nEngine, player: Player):
    print("\n" + translate_with_fallback(engine, "000W00"))
    current_name = resolve_player_shard_name(engine, player)
    current_type = resolve_player_shard_type(engine, player)
    print(translate_with_fallback(engine, "000W01", [current_name, current_type]))
    print(translate_with_fallback(engine, "000W02"))
    print(translate_with_fallback(engine, "000W06"))
    sector_ids = list(sector_registry.keys())
    deal_map = {}
    for idx, sector_id in enumerate(sector_ids, start=1):
        info = sector_registry[sector_id]
        marker = (
            translate_with_fallback(engine, UI_TOKENS["current_marker"])
            if sector_id == player.current_sector_id
            else ""
        )
        name_label = translate_with_fallback(engine, info.get("name_token", ""))
        type_label = translate_with_fallback(engine, info.get("type_token", ""))
        print(
            translate_with_fallback(
                engine,
                UI_TOKENS["sector_entry"],
                [idx, name_label, type_label, marker],
            )
        )
        deal_map[str(idx)] = sector_id
    choice = input("> ").strip()
    if not choice.isdigit():
        return
    target_idx = int(choice) - 1
    if target_idx < 0 or target_idx >= len(sector_ids):
        return
    target_sector = sector_ids[target_idx]
    info = sector_registry[target_sector]
    if target_sector == player.current_sector_id:
        print(translate_with_fallback(engine, "000W03", [current_name]))
        return
    if info.get("token"):
        if apply_shard_token(engine, player, info["token"], announce=True):
            set_sector_from_registry(engine, player, target_sector)
            refresh_runtime_catalog(engine, player)
            current_name = resolve_player_shard_name(engine, player)
            current_type = resolve_player_shard_type(engine, player)
            print(translate_with_fallback(engine, "000W04", [current_name, current_type]))
    else:
        set_sector_from_registry(engine, player, target_sector, announce=True)


def append_logbook_entry(pkg_id: str, tokens):
    LOGBOOK_FILE.parent.mkdir(exist_ok=True)
    existing = set()
    if LOGBOOK_FILE.exists():
        with LOGBOOK_FILE.open("rb") as f:
            for line in f:
                existing.add(line.strip().split(b":", 1)[0])
    if pkg_id.encode("utf-8") in existing:
        return
    entry = f"{pkg_id}:{','.join(tokens)}\n".encode("utf-8")
    with LOGBOOK_FILE.open("ab") as f:
        f.write(entry)


def read_logbook_entries():
    entries = []
    if not LOGBOOK_FILE.exists():
        return entries
    with LOGBOOK_FILE.open("rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pkg_id, rest = line.split(b":", 1)
            tokens = rest.decode("utf-8").split(",") if rest else []
            entries.append((pkg_id.decode("utf-8"), tokens))
    return entries


def parse_script(script: str):
    parts = script.split("|")
    if len(parts) > 1:
        return parts[0], parts[1:]
    return script, []


def run_script(player: Player, script: str, label: str, engine: I18nEngine):
    name, clauses = parse_script(script)
    effects = {}
    commands = []
    for clause in clauses:
        if not clause.strip():
            continue
        key, value = clause.split(":", 1)
        val = float(value)
        if key == "ATK_ADD":
            player.atk += val
            commands.append(f"{key}+{val}")
        elif key == "ATK_MUL":
            player.atk *= val
            commands.append(f"{key}*{val}")
        elif key in {"HP_ADD", "REPAIR"}:
            player.hp = min(player.max_hp, player.hp + val)
            commands.append(f"{key}+{val}")
        elif key == "HP_SUB":
            player.hp = max(0, player.hp - val)
            commands.append(f"{key}-{val}")
        elif key == "CRIT_MUL":
            player.crit_chance *= val
            commands.append(f"{key}*{val}")
        elif key == "CRIT_ADD":
            player.crit_chance += val
            commands.append(f"{key}+{val}")
        elif key == "STAB_SUB":
            effects["stability_penalty"] = effects.get("stability_penalty", 0) + val
            commands.append(f"{key}-{val}")
        elif key == "DEF_ADD":
            effects["defense"] = effects.get("defense", 0) + val
            commands.append(f"{key}+{val}")
        elif key == "ENEMY_HP_ADD":
            effects["enemy_hp_add"] = effects.get("enemy_hp_add", 0) + val
            commands.append(f"{key}+{val}")
        elif key == "ENEMY_HP_MUL":
            effects["enemy_hp_mul"] = effects.get("enemy_hp_mul", 1.0) * val
            commands.append(f"{key}*{val}")
        elif key == "ENEMY_ATK_ADD":
            effects["enemy_atk_add"] = effects.get("enemy_atk_add", 0) + val
            commands.append(f"{key}+{val}")
        elif key == "ENEMY_ATK_MUL":
            effects["enemy_atk_mul"] = effects.get("enemy_atk_mul", 1.0) * val
            commands.append(f"{key}*{val}")
    detail = f" ({name})" if name else ""
    print(
        translate_with_fallback(
            engine,
            UI_TOKENS["module_executed"],
            [label, detail, ", ".join(commands)],
        )
    )
    return effects


def apply_enemy_effects(e_hp: float, e_atk: float, effect_sources: list[dict] | None):
    hp_mul = 1.0
    atk_mul = 1.0
    hp_add = 0.0
    atk_add = 0.0
    for source in (effect_sources or []):
        if not source:
            continue
        hp_mul *= source.get("enemy_hp_mul", 1.0)
        atk_mul *= source.get("enemy_atk_mul", 1.0)
        hp_add += source.get("enemy_hp_add", 0.0)
        atk_add += source.get("enemy_atk_add", 0.0)
    scaled_hp = max(1, int((e_hp + hp_add) * hp_mul))
    scaled_atk = max(1, int((e_atk + atk_add) * atk_mul))
    return scaled_hp, scaled_atk


ENEMY_SCALING_TABLE = [
    {"level": 1, "token": "000S60"},
    {"level": 5, "token": "000S61"},
    {"level": 10, "token": "000S62"},
]


def compose_enemy_scaling_script(engine: I18nEngine, player: Player):
    choices = [entry for entry in ENEMY_SCALING_TABLE if player.lvl >= entry["level"]]
    if not choices:
        return None
    choice = max(choices, key=lambda item: item["level"])
    script = resolve_catalog_token(engine, choice["token"])
    if "⟦" in script:
        return None
    return script


def parse_menu_entries(engine: I18nEngine, token_id: str = "000M101"):
    raw = translate_with_fallback(engine, token_id)
    if not raw.strip():
        return []
    entries = []
    for part in raw.split("|"):
        segment = part.strip()
        if not segment:
            continue
        pieces = [p.strip() for p in segment.split(":", 2)]
        if len(pieces) != 3:
            continue
        number, key, label = pieces
        entries.append({"number": number, "key": key.upper(), "label": label})
    return entries


MENU_ACTIONS = {}


def register_menu_action(key):
    def decorator(func):
        MENU_ACTIONS[key] = func
        return func
    return decorator


@register_menu_action("INV")
def handle_inventory_action(engine: I18nEngine, player: Player):
    print("\n" + translate_with_fallback(engine, UI_TOKENS["inventory_header"]))
    counts = inventory_counts(player)
    if not counts:
        print(translate_with_fallback(engine, UI_TOKENS["inventory_empty"]))
        return
    active_weapon = player.equipped_items.get("weapon")
    equipment_label = (
        get_token_label(engine, active_weapon)
        if active_weapon
        else translate_with_fallback(engine, UI_TOKENS["label_none"])
    )
    print(
        translate_with_fallback(engine, UI_TOKENS["equipment_label"], [equipment_label])
    )
    items = sorted([tok for tok in counts if tok.startswith("000I")])
    resources = sorted([tok for tok in counts if tok.startswith("000N")])
    if items:
        print(translate_with_fallback(engine, UI_TOKENS["items_label"]))
        for idx, token in enumerate(items, start=1):
            print(
                translate_with_fallback(
                    engine,
                    UI_TOKENS["inventory_entry"],
                    [idx, get_token_label(engine, token), counts[token]],
                )
            )
        sel = input(translate_with_fallback(engine, UI_TOKENS["inventory_select_prompt"])).strip()
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(items):
                player.equipped_items["weapon"] = items[idx]
                print(
                    translate_with_fallback(
                        engine,
                        UI_TOKENS["inventory_equipped"],
                        [get_token_label(engine, items[idx])],
                    )
                )
    else:
        print(translate_with_fallback(engine, UI_TOKENS["inventory_no_items"]))
    if resources:
        print(translate_with_fallback(engine, UI_TOKENS["resources_label"]))
        for token in resources:
            print(
                translate_with_fallback(
                    engine,
                    UI_TOKENS["resource_entry"],
                    [get_token_label(engine, token), counts[token]],
                )
            )


@register_menu_action("MARK")
def handle_market_action(engine: I18nEngine, player: Player):
    price_map = parse_market_price_token(engine)
    multiplier, extra = get_price_modifiers(engine, player)
    print("\n" + translate_with_fallback(engine, UI_TOKENS["market_header"]))
    print(
        translate_with_fallback(
            engine, UI_TOKENS["price_factor"], [f"{multiplier:.2f}"]
        )
    )
    while True:
        print(translate_with_fallback(engine, UI_TOKENS["market_prompt"]))
        choice = input("> ").strip()
        if choice == "1":
            available = sorted(price_map["items"].items())
            if not available:
                print(translate_with_fallback(engine, UI_TOKENS["market_no_items"]))
                continue
            for idx, (token, base) in enumerate(available, start=1):
                price = max(1, int(round(base * multiplier + extra)))
                print(
                    translate_with_fallback(
                        engine,
                        UI_TOKENS["market_item_entry"],
                        [idx, get_token_label(engine, token), price],
                    )
                )
            sel = input(translate_with_fallback(engine, UI_TOKENS["market_item_prompt"])).strip()
            if not sel.isdigit():
                continue
            idx = int(sel) - 1
            if 0 <= idx < len(available):
                token, base = available[idx]
                price = max(1, int(round(base * multiplier + extra)))
                if player.credits >= price:
                    player.credits -= price
                    player.inventory_tokens.append(token)
                    print(
                        translate_with_fallback(
                            engine,
                            UI_TOKENS["market_item_bought"],
                            [get_token_label(engine, token), price],
                        )
                    )
                else:
                    print(engine.translate("000C26", [price]))
        elif choice == "2":
            resource_entries = sorted({
                tok for tok in player.inventory_tokens
                if tok in price_map["resources"] or tok in RESOURCE_BASE_VALUES
            })
            if not resource_entries:
                print(
                    translate_with_fallback(engine, UI_TOKENS["market_no_resources"])
                )
                continue
            for idx, token in enumerate(resource_entries, start=1):
                base_price = price_map["resources"].get(token, RESOURCE_BASE_VALUES.get(token, 0))
                price = max(1, int(round(base_price * 0.5 * multiplier + extra)))
                print(
                    translate_with_fallback(
                        engine,
                        UI_TOKENS["market_item_entry"],
                        [idx, get_token_label(engine, token), price],
                    )
                )
            sel = input(translate_with_fallback(engine, UI_TOKENS["resource_prompt"])).strip()
            if not sel.isdigit():
                continue
            idx = int(sel) - 1
            if 0 <= idx < len(resource_entries):
                token = resource_entries[idx]
                base_price = price_map["resources"].get(token, RESOURCE_BASE_VALUES.get(token, 0))
                price = max(1, int(round(base_price * 0.5 * multiplier + extra)))
                remove_inventory_tokens(player, [token])
                player.credits += price
                print(
                    translate_with_fallback(
                        engine,
                        UI_TOKENS["resource_sold"],
                        [get_token_label(engine, token), price],
                    )
                )
        elif choice == "3":
            break
        else:
            print(translate_with_fallback(engine, UI_TOKENS["invalid_selection"]))


@register_menu_action("CRAFT")
def handle_craft_action(engine: I18nEngine, player: Player):
    recipes = [parse_recipe_token(engine, tid) for tid in RECIPE_TOKENS]
    recipes = [recipe for recipe in recipes if recipe.get("requirements") and recipe.get("products")]
    if not recipes:
        print(translate_with_fallback(engine, UI_TOKENS["no_recipes"]))
        return
    print("\n" + translate_with_fallback(engine, UI_TOKENS["craft_header"]))
    for idx, recipe in enumerate(recipes, start=1):
        req_labels = ", ".join(get_token_label(engine, tok) for tok in recipe["requirements"])
        print(
            translate_with_fallback(
                engine,
                UI_TOKENS["craft_entry"],
                [idx, recipe["label"], req_labels, recipe["cost"]],
            )
        )
    sel = input(translate_with_fallback(engine, UI_TOKENS["craft_prompt"])).strip()
    if not sel.isdigit():
        return
    idx = int(sel) - 1
    if not (0 <= idx < len(recipes)):
        return
    recipe = recipes[idx]
    if recipe["cost"] and player.credits < recipe["cost"]:
        print(engine.translate("000C26", [recipe["cost"]]))
        return
    if not inventory_has_tokens(player, recipe["requirements"]):
        missing = [tok for tok in recipe["requirements"] if player.inventory_tokens.count(tok) < recipe["requirements"].count(tok)]
        missing_labels = ", ".join(get_token_label(engine, tok) for tok in missing)
        print(translate_with_fallback(engine, UI_TOKENS["craft_missing"], [missing_labels]))
        return
    remove_inventory_tokens(player, recipe["requirements"])
    player.credits -= recipe["cost"]
    for product in recipe["products"]:
        player.inventory_tokens.append(product)
    product_labels = ", ".join(get_token_label(engine, tok) for tok in recipe["products"])
    print(
        translate_with_fallback(engine, UI_TOKENS["craft_success"], [product_labels])
    )


@register_menu_action("SKL")
def handle_skill_action(engine: I18nEngine, player: Player):
    price_map = parse_market_price_token(engine)
    multiplier, extra = get_price_modifiers(engine, player)
    skill_ids = list(SKILL_TREE.keys())
    print("\n" + translate_with_fallback(engine, UI_TOKENS["skills_header"]))
    for idx, skill_id in enumerate(skill_ids, start=1):
        label = get_token_label(engine, skill_id)
        desc = translate_with_fallback(engine, SKILL_TREE[skill_id]["desc_token"])
        status_key = "learned" if skill_id in player.skill_tokens else "available"
        if skill_id == player.active_skill_token:
            status_key = "active"
        status = translate_with_fallback(engine, SKILL_STATUS_TOKENS[status_key])
        cost = price_map["skills"].get(skill_id, SKILL_TREE[skill_id]["cost"])
        final_cost = max(1, int(round(cost * multiplier + extra)))
        print(
            translate_with_fallback(
                engine,
                UI_TOKENS["skill_entry"],
                [idx, label, status, desc, final_cost],
            )
        )
    sel = input(translate_with_fallback(engine, UI_TOKENS["skill_prompt"])).strip()
    if not sel.isdigit():
        return
    idx = int(sel) - 1
    if not (0 <= idx < len(skill_ids)):
        return
    skill_id = skill_ids[idx]
    skill_config = SKILL_TREE[skill_id]
    if skill_id in player.skill_tokens:
        if skill_config.get("type") == "active":
            player.active_skill_token = skill_id
            print(
                translate_with_fallback(
                    engine,
                    UI_TOKENS["skill_activated"],
                    [get_token_label(engine, skill_id)],
                )
            )
        else:
            print(translate_with_fallback(engine, UI_TOKENS["skill_already"]))
        return
    prereq = skill_config.get("prereq")
    if prereq and prereq not in player.skill_tokens:
        print(translate_with_fallback(engine, UI_TOKENS["skill_prereq"]))
        return
    cost = price_map["skills"].get(skill_id, skill_config["cost"])
    final_cost = max(1, int(round(cost * multiplier + extra)))
    if player.credits < final_cost:
        print(engine.translate("000C26", [final_cost]))
        return
    player.credits -= final_cost
    acquire_skill(engine, player, skill_id)
def execute_menu_key(engine: I18nEngine, player: Player, key: str):
    handler = MENU_ACTIONS.get(key.upper())
    if not handler:
        return None
    return handler(engine, player)


LEGACY_MENU_MAP = {
    "1": "SCAN",
    "2": "NAV",
    "3": "SHOP",
    "4": "STATUS",
    "5": "HIGH",
    "6": "SAVE",
    "7": "EVENT",
    "9": "INV",
    "10": "MARK",
    "11": "CRAFT",
    "12": "SKL",
}


@register_menu_action("SCAN")
def handle_scan_action(engine: I18nEngine, player: Player):
    run_battle(player, engine)


@register_menu_action("NAV")
def handle_navigation_action(engine: I18nEngine, player: Player):
    show_navigation(engine, player)


@register_menu_action("SHOP")
def handle_shop_action(engine: I18nEngine, player: Player):
    if player.kills < 3:
        print(engine.translate("000701", [int(3 - player.kills)]))
        return
    print("\n" + engine.translate("000A04") + "\n" + engine.translate("000700"))
    for line in knowledge_dialogue_lines(engine, player, "shop"):
        print(line)
    print(engine.translate("000C20", [int(player.credits)]))
    available_deals = get_available_faction_shop_deals(player)
    deal_options = {}
    option_base = 8
    for deal in available_deals:
        price = compute_deal_price(player, deal)
        label = translate_with_fallback(engine, deal["name_token"])
        print(
            translate_with_fallback(
                engine,
                UI_TOKENS["market_item_entry"],
                [option_base, label, price],
            )
        )
        deal_options[str(option_base)] = (deal, price)
        option_base += 1
    sc = input(engine.translate("000C21") + "\n> ").strip()
    if sc == "1" and player.credits >= 150:
        player.credits -= 150
        player.kits += 1
        print(engine.translate("000C22"))
    elif sc == "2" and player.credits >= 500:
        player.credits -= 500
        player.atk += 5
        print(engine.translate("000C22"))
    elif sc == "3":
        next_trait = next((t for t in TRAIT_CONFIG if not player.has_trait(t["id"])), None)
        if not next_trait:
            print(engine.translate("000C27"))
        elif player.credits >= next_trait["cost"]:
            player.credits -= next_trait["cost"]
            unlock_trait(engine, player, next_trait["id"])
            print(
                engine.translate(
                    "000C24",
                    [
                        engine.translate(next_trait["name_token"]),
                        engine.translate(next_trait["desc_token"]),
                    ],
                )
            )
        else:
            print(engine.translate("000C26", [next_trait["cost"]]))
    elif sc == "4":
        next_pkg = next((pid for pid in KNOWLEDGE_PACKAGES if pid not in player.knowledge_packages), None)
        if not next_pkg:
            print(engine.translate("000C28"))
        else:
            cost = KNOWLEDGE_PACKAGES[next_pkg]["cost"]
            if player.credits >= cost:
                player.credits -= cost
                unlock_knowledge(engine, player, next_pkg)
                pkg_tokens = ", ".join(KNOWLEDGE_PACKAGES[next_pkg]["tokens"])
                print(engine.translate("000C25", [pkg_tokens]))
            else:
                print(engine.translate("000C26", [cost]))
    elif sc in deal_options:
        deal, price = deal_options[sc]
        if player.credits >= price:
            player.credits -= price
            deal["effect"](player)
            print(translate_with_fallback(engine, "000C32", [translate_with_fallback(engine, deal["name_token"]), price]))
        else:
            print(engine.translate("000C26", [price]))
    if input(translate_with_fallback(engine, UI_TOKENS["boss_prompt"]) + " ") == "j":
        run_battle(player, engine, True)


@register_menu_action("STATUS")
def handle_status_action(engine: I18nEngine, player: Player):
    print(
        translate_with_fallback(
            engine,
            UI_TOKENS["status_line"],
            [int(player.lvl), int(player.hp), int(player.credits)],
        )
    )
    print(
        translate_with_fallback(
            engine,
            UI_TOKENS["location_line"],
            [resolve_player_shard_name(engine, player), resolve_player_shard_type(engine, player)],
        )
    )
    print(engine.translate("000D01"))
    print(engine.translate("000D02", [int(player.quest_kills), int(player.quest_target)]))
    achievements_display = (
        ", ".join(engine.translate(a) for a in player.achievements)
        if player.achievements
        else translate_with_fallback(engine, UI_TOKENS["label_none"])
    )
    print(
        translate_with_fallback(engine, UI_TOKENS["achievements_line"], [achievements_display])
    )
    trait_line = trait_message(engine, player)
    if trait_line:
        print(trait_line)
    for line in knowledge_messages(engine, player):
        print(line)
    for line in faction_status_lines(engine, player):
        print(line)
    print("\n" + translate_with_fallback(engine, UI_TOKENS["token_status_header"]))
    active_weapon = player.equipped_items.get("weapon")
    equipment_label = (
        get_token_label(engine, active_weapon)
        if active_weapon
        else translate_with_fallback(engine, UI_TOKENS["label_none"])
    )
    print(
        translate_with_fallback(engine, UI_TOKENS["equipment_label"], [equipment_label])
    )
    inv_counts = inventory_counts(player)
    if inv_counts:
        print(translate_with_fallback(engine, UI_TOKENS["inventory_list_label"]))
        for token, amount in inv_counts.items():
            print(
                translate_with_fallback(
                    engine, UI_TOKENS["resource_entry"], [get_token_label(engine, token), amount]
                )
            )
    else:
        print(translate_with_fallback(engine, UI_TOKENS["inventory_empty_line"]))
    if player.skill_tokens:
        skill_lines = []
        for skill_id in player.skill_tokens:
            label = get_token_label(engine, skill_id)
        if skill_id == player.active_skill_token:
            suffix = f" ({translate_with_fallback(engine, SKILL_STATUS_TOKENS['active'])})"
        else:
            suffix = ""
        skill_lines.append(f"{label}{suffix}")
        print(
            translate_with_fallback(
                engine, UI_TOKENS["skills_list_line"], [", ".join(skill_lines)]
            )
        )
    else:
        print(translate_with_fallback(engine, UI_TOKENS["skills_none_line"]))
    sub = input(engine.translate("000202") + "\n> ")
    if sub == "1" and player.kits > 0:
        player.hp = min(player.max_hp, player.hp + 40)
        player.kits -= 1
    elif sub == "2":
        print(translate_with_fallback(engine, UI_TOKENS["inventory_hint"]))


@register_menu_action("HIGH")
def handle_highscore_action(engine: I18nEngine, player: Player):
    print("\n" + engine.translate("000105"))


@register_menu_action("SAVE")
def handle_save_action(engine: I18nEngine, player: Player):
    player.save_game(engine)
    return "EXIT"


@register_menu_action("EVENT")
def handle_event_action(engine: I18nEngine, player: Player):
    world_event_menu(engine, player)


def story_chapter_path(player: Player):
    chapter = player.story_chapter or DEFAULT_STORY_CHAPTER
    return STORY_DIR / f"story_chapter_{chapter}.txt"


def parse_story_nodes(chapter_num: int):
    path = STORY_DIR / f"story_chapter_{chapter_num}.txt"
    nodes = {}
    if not path.exists():
        return nodes
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("@"):
            continue
        if ":" not in line:
            continue
        token, body = line.split(":", 1)
        if "NODE" not in body.upper():
            continue
        node = {
            "token": token,
            "node_key": None,
            "text_token": None,
            "choices": [],
            "effects": [],
            "chapter": None,
        }
        for part in body.split("|"):
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            key = key.strip().upper()
            value = value.strip()
            if key == "NODE":
                node["node_key"] = value
            elif key == "TEXT":
                node["text_token"] = value
            elif key.startswith("CHOICE"):
                label_token, _, next_key = value.partition(":")
                node["choices"].append(
                    {"label_token": label_token, "next": next_key or node["node_key"]}
                )
            elif key == "CHAPTER":
                try:
                    node["chapter"] = int(value)
                except ValueError:
                    pass
            else:
                node["effects"].append((key.lower(), value))
        if node["node_key"] and node["text_token"]:
            nodes[node["node_key"]] = node
    return nodes


def load_story_nodes(player: Player):
    player.story_nodes = parse_story_nodes(player.story_chapter)


def apply_story_effects(player: Player, node: dict):
    effects = {}
    for key, value in node.get("effects", []):
        try:
            effects[key] = float(value)
        except ValueError:
            effects[key] = value
    player.story_effects = effects


def play_story_sequence(engine: I18nEngine, player: Player):
    while True:
        if player.story_state == "completed":
            return
        node = player.story_nodes.get(player.story_state)
        if not node:
            return
        text_args = [player.name, int(player.lvl), int(player.kills)]
        text = translate_with_fallback(engine, node["text_token"], text_args)
        print("\n" + ("-" * 40))
        print(
            translate_with_fallback(
                engine,
                UI_TOKENS["story_node"],
                [node["node_key"], text],
            )
        )
        apply_story_effects(player, node)
        if not node["choices"]:
            player.story_history.append((node["node_key"], "Abschluss"))
            player.story_state = "completed"
            print(translate_with_fallback(engine, UI_TOKENS["story_progress"]))
            return
        labels = []
        for idx, choice in enumerate(node["choices"], start=1):
            label = translate_with_fallback(engine, choice["label_token"])
            print(f"({idx}) {label}")
            labels.append((choice, label))
        sel = input("> ").strip()
        selected_entry = None
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(labels):
                selected_entry = labels[idx]
        if not selected_entry:
            selected_entry = labels[0]
        choice, label = selected_entry
        player.story_history.append((node["node_key"], label))
        player.story_state = choice["next"] or node["node_key"]
        next_chapter = node.get("chapter")
        if next_chapter and next_chapter != player.story_chapter:
            player.story_chapter = next_chapter
            refresh_runtime_catalog(engine, player)
            load_story_nodes(player)
            continue
        continue


def trigger_story_progress(engine: I18nEngine, player: Player):
    if player.story_state == "completed":
        return
    if not player.story_nodes:
        load_story_nodes(player)
    play_story_sequence(engine, player)


@register_menu_action("STORY")
def handle_story_action(engine: I18nEngine, player: Player):
    if player.story_history:
        print("\n" + translate_with_fallback(engine, UI_TOKENS["story_header"]))
        for idx, (title, choice) in enumerate(player.story_history, start=1):
            print(f"{idx}. {title} → {choice}")
    else:
        print(
            "\n"
            + translate_with_fallback(engine, UI_TOKENS["story_header"])
            + "\n"
            + translate_with_fallback(engine, UI_TOKENS["story_no_chapters"])
        )
    trigger_story_progress(engine, player)


def handle_menu_input(engine: I18nEngine, player: Player, choice: str, entries: list[dict]):
    if not choice:
        return None
    if entries:
        selected = next((entry for entry in entries if entry["number"] == choice), None)
        if not selected:
            return None
        return execute_menu_key(engine, player, selected["key"])
    key = LEGACY_MENU_MAP.get(choice)
    if not key:
        return None
    return execute_menu_key(engine, player, key)


def execute_token_script(player: Player, engine: I18nEngine, token_id: str):
    script = resolve_catalog_token(engine, token_id)
    if "⟦" in script:
        return {}
    return run_script(player, script, token_id, engine)


def execute_dynamic_script(player: Player, script: str, engine: I18nEngine, label: str = "CALR"):
    return run_script(player, script, label, engine)


def get_token_label(engine: I18nEngine, token: str) -> str:
    raw = resolve_catalog_token(engine, token)
    if not raw:
        return token
    label = raw.split("|", 1)[0]
    return label.strip() or token


def inventory_counts(player: Player) -> Counter:
    return Counter(player.inventory_tokens)


def inventory_has_tokens(player: Player, tokens: list[str]) -> bool:
    needed = Counter(tokens)
    available = inventory_counts(player)
    return all(available[token] >= amount for token, amount in needed.items())


def remove_inventory_tokens(player: Player, tokens: list[str]):
    needed = Counter(tokens)
    for token, count in needed.items():
        for _ in range(count):
            if token in player.inventory_tokens:
                player.inventory_tokens.remove(token)


def parse_script_effects(script: str) -> dict:
    _, clauses = parse_script(script)
    effects = {}
    for clause in clauses:
        if ":" not in clause:
            continue
        key, value = clause.split(":", 1)
        key = key.strip().lower()
        if not key:
            continue
        try:
            numeric = float(value)
        except ValueError:
            continue
        if key == "stab_sub":
            effects["stability_penalty"] = effects.get("stability_penalty", 0.0) + numeric
            continue
        if key.endswith("_mul"):
            effects[key] = effects.get(key, 1.0) * numeric
        else:
            effects[key] = effects.get(key, 0.0) + numeric
    return effects


def aggregate_equipped_item_effects(engine: I18nEngine, player: Player) -> dict:
    merged = {}
    for slot, token in player.equipped_items.items():
        if not token:
            continue
        script = resolve_catalog_token(engine, token)
        if "⟦" in script:
            continue
        token_effects = parse_script_effects(script)
        for key, value in token_effects.items():
            if key.endswith("_mul"):
                merged[key] = merged.get(key, 1.0) * value
            else:
                merged[key] = merged.get(key, 0.0) + value
    return merged


def skill_resource_multiplier(engine: I18nEngine, player: Player) -> float:
    multiplier = 1.0
    for skill_id in player.skill_tokens:
        script = resolve_catalog_token(engine, skill_id)
        if "⟦" in script:
            continue
        effects = parse_script_effects(script)
        multiplier *= effects.get("resource_mult", 1.0)
    return multiplier


def gather_resources(engine: I18nEngine, player: Player) -> list[str]:
    shard_token = player.current_shard_token or DEFAULT_SHARD_TOKEN
    nodes = SECTOR_RESOURCE_NODES.get(shard_token, DEFAULT_RESOURCE_POOL)
    if not nodes:
        nodes = DEFAULT_RESOURCE_POOL
    base_count = random.randint(1, 2)
    total = max(1, int(round(base_count * skill_resource_multiplier(engine, player))))
    gained = []
    for _ in range(total):
        token = random.choice(nodes)
        player.inventory_tokens.append(token)
        gained.append(token)
    if gained:
        labels = ", ".join(get_token_label(engine, tok) for tok in gained)
        print(
            translate_with_fallback(engine, UI_TOKENS["resource_filtered"], [labels])
        )
    return gained


def parse_recipe_token(engine: I18nEngine, token_id: str) -> dict:
    script = resolve_catalog_token(engine, token_id)
    if "⟦" in script:
        return {}
    label, clauses = parse_script(script)
    recipe = {"label": label, "requirements": [], "products": [], "cost": 0}
    for clause in clauses:
        if ":" not in clause:
            continue
        key, value = clause.split(":", 1)
        key = key.strip().upper()
        value = value.strip()
        if key == "REQ" and value:
            recipe["requirements"] = [tok.strip() for tok in value.split("+") if tok.strip()]
        elif key == "PROD" and value:
            recipe["products"] = [tok.strip() for tok in value.split("+") if tok.strip()]
        elif key == "COST":
            try:
                recipe["cost"] = int(float(value))
            except ValueError:
                recipe["cost"] = 0
    return recipe


def parse_market_price_token(engine: I18nEngine) -> dict:
    script = resolve_catalog_token(engine, MARKET_PRICE_TOKEN)
    price_map = {"items": {}, "resources": {}, "skills": {}}
    if "⟦" in script or "|" not in script:
        return price_map
    _, clauses = parse_script(script)
    for clause in clauses:
        if ":" not in clause:
            continue
        key, data = clause.split(":", 1)
        key = key.strip().upper()
        for entry in [e.strip() for e in data.split(",") if e.strip()]:
            if "=" not in entry:
                continue
            tid, value = entry.split("=", 1)
            try:
                price = int(float(value))
            except ValueError:
                continue
            tid = tid.strip()
            if key == "ITEM":
                price_map["items"][tid] = price
            elif key == "RESOURCE":
                price_map["resources"][tid] = price
            elif key == "SKILL":
                price_map["skills"][tid] = price
    return price_map


def get_price_modifiers(engine: I18nEngine, player: Player) -> tuple[float, float]:
    multiplier, extra = 1.0, 0.0
    sources = [get_active_world_event_token()] + player.skill_tokens
    for token in filter(None, sources):
        script = resolve_catalog_token(engine, token)
        if not script or "PRICE_" not in script:
            continue
        _, clauses = parse_script(script)
        for clause in clauses:
            if ":" not in clause:
                continue
            key, value = clause.split(":", 1)
            key = key.strip().upper()
            try:
                numeric = float(value)
            except ValueError:
                continue
            if key == "PRICE_MUL":
                multiplier *= numeric
            elif key == "PRICE_ADD":
                extra += numeric
    return multiplier, extra


def acquire_skill(engine: I18nEngine, player: Player, skill_id: str) -> bool:
    if skill_id in player.skill_tokens:
        return False
    player.skill_tokens.append(skill_id)
    append_logbook_entry(skill_id, [skill_id])
    if SKILL_TREE.get(skill_id, {}).get("type") == "active" and not player.active_skill_token:
        player.active_skill_token = skill_id
    print(
        translate_with_fallback(
            engine,
            UI_TOKENS["skill_unlocked"],
            [get_token_label(engine, skill_id)],
        )
    )
    return True

LORE_TOKENS = ["000B10", "000B11", "000B12", "000B13", "000B14", "000B15"]
MYCEL_ENEMY_TOKENS = [
    "3aa732c6",
    "57ee01d4",
    "3ec17a46",
    "1ba52628",
    "405adf78",
    "fa4cd27e",
    "aa822dc9",
    "2708dd0d",
    "29a599c7",
    "a562ca0d",
]
MYCEL_BOSS_TOKENS = [
    "4ef7303e",
    "1033a021",
    "42c50bea",
    "21dea3ef",
    "0dff43ae",
]


def run_battle(player, engine, is_boss=False):
    # GPU-CUBE PHYSIK LOGIK
    stability = random.randint(50, 100)
    physics_bonus = 0
    if is_boss:
        print("\n" + engine.translate("000B00"))
        stability = 30

    event = get_active_world_event()
    if event:
        stability += event.get("stability_shift", 0)
        physics_bonus += event.get("physics_bonus", 0)
        battle_msg = event.get("battle_message_token")
        if battle_msg:
            print("\n" + translate_with_fallback(engine, battle_msg))

    item_effects = aggregate_equipped_item_effects(engine, player)

    calr_script = compose_calr_script(engine, player)
    calr_effects = None
    if calr_script:
        calr_effects = execute_dynamic_script(player, calr_script, engine, "CALR")

    scaling_script = compose_enemy_scaling_script(engine, player)
    scaling_effects = None
    if scaling_script:
        scaling_effects = execute_dynamic_script(player, scaling_script, engine, "SCALING")

    lore = " ".join(engine.translate(tok) for tok in random.sample(LORE_TOKENS, 3))
    print("\n" + lore)

    total_module_penalty = player.trait_stability_penalty()
    total_module_penalty += item_effects.get("stability_penalty", 0)
    for trait in TRAIT_CONFIG:
        if player.has_trait(trait["id"]) and trait.get("module_token"):
            effects = execute_token_script(player, engine, trait["module_token"])
            total_module_penalty += effects.get("stability_penalty", 0)
    story_penalty = player.story_effects.get("stab_sub", 0) if player.story_effects else 0

    stability = max(15, stability - total_module_penalty - story_penalty)
    print("\n" + engine.translate("000C10", [int(stability)]))

    hp_add = item_effects.get("hp_add", 0)
    if hp_add:
        player.hp = min(player.max_hp, player.hp + hp_add)
    hp_sub = item_effects.get("hp_sub", 0)
    if hp_sub:
        player.hp = max(0, player.hp - hp_sub)

    if stability < 75:
        physics_bonus = random.randint(5, 20)
        print(engine.translate("000C12", [int(physics_bonus)]))

    enemy_token = random.choice(MYCEL_BOSS_TOKENS) if is_boss else random.choice(MYCEL_ENEMY_TOKENS)
    e_name = translate_with_fallback(engine, enemy_token)
    e_hp = 250 if is_boss else 40 + (player.lvl * 10)
    e_atk = 8 + player.lvl if not is_boss else 15
    boss_phase_triggered = not is_boss
    original_hp = e_hp
    
    story_effects = player.story_effects or {}
    e_hp, e_atk = apply_enemy_effects(e_hp, e_atk, [calr_effects, scaling_effects, story_effects, item_effects])
    print(
        engine.translate(
            "000300",
            [e_name, int(e_hp), resolve_player_shard_name(engine, player)],
        )
    )
    print(engine.translate("000A03" if is_boss else "000A01"))

    defense_bonus = item_effects.get("def_add", 0)
    skill_ready = bool(player.active_skill_token and player.active_skill_token in player.skill_tokens)
    trait_multiplier = player.trait_damage_multiplier()

    while e_hp > 0 and player.hp > 0:
        if is_boss and not boss_phase_triggered and e_hp <= original_hp / 2:
            boss_phase_triggered = True
            boss_effects = execute_token_script(player, engine, "000B50")
            if boss_effects.get("stability_penalty"):
                stability -= boss_effects.get("stability_penalty")
                print(translate_with_fallback(engine, UI_TOKENS["boss_phase"]))
        print(
            translate_with_fallback(
                engine,
                UI_TOKENS["battle_status"],
                [player.name, int(player.hp), e_name, int(e_hp)],
            )
        )
        prompt = engine.translate("000201")
        if skill_ready:
            prompt += " (S=Skill)"
        if player.admin_mode:
            prompt += " [K=ADMIN]"
        choice = input(prompt + "\n> ").strip()
        if skill_ready and choice.upper() == "S":
            execute_token_script(player, engine, player.active_skill_token)
            skill_ready = False
            continue
        if player.admin_mode and choice.lower() == 'k':
            e_hp = 0
            break

        dmg = 0
        atk_add = item_effects.get("atk_add", 0)
        atk_mul = item_effects.get("atk_mul", 1.0)
        current_atk = int((player.atk + atk_add + physics_bonus) * atk_mul * trait_multiplier)
        if choice == "1":
            dmg = current_atk + random.randint(-2, 2)
        elif choice == "2" and random.random() > 0.4:
            dmg = int(current_atk * 1.8)
            print(translate_with_fallback(engine, UI_TOKENS["full_hit"]))
        elif choice == "3":
            player.hp = min(player.max_hp, player.hp + 25)
            print(translate_with_fallback(engine, UI_TOKENS["repair_action"]))

        if dmg > 0:
            crit_add = item_effects.get("crit_add", 0)
            crit_mul = item_effects.get("crit_mul", 1.0)
            current_crit = (player.crit_chance + crit_add) * crit_mul
            if random.random() < current_crit:
                dmg *= 2
                print(engine.translate("000303", [player.name, int(dmg)]))
            e_hp -= dmg
            print(engine.translate("000301", [player.name, e_name, int(dmg)]))
            if e_hp <= 0:
                break
        if e_hp > 0:
            enemy_hit = max(1, int(e_atk - int(defense_bonus)))
            player.hp -= enemy_hit
            print(engine.translate("000301", [e_name, player.name, int(enemy_hit)]))

    if player.hp <= 0:
        return False

    if e_hp <= 0:
        cr = random.randint(40, 80)
        player.credits += cr
        player.xp += 50
        player.kills += 1
        player.quest_kills += 1
        apply_faction_influences(engine, player, SHARD_FACTION_INFLUENCE.get(player.current_shard_token, []), FACTION_SOURCE_TOKENS["sector"])
        print(engine.translate("000302", [e_name, 50, cr]))
        if is_boss:
            print(engine.translate("000B03"))
            if "000F03" not in player.achievements:
                player.achievements.append("000F03")
            return "WIN"
        if player.kills == 1 and "000F01" not in player.achievements:
            player.achievements.append("000F01")
            print(engine.translate("000F01"))
        if player.lvl >= 5 and "000F02" not in player.achievements:
            player.achievements.append("000F02")
            print(engine.translate("000F02"))
        if player.quest_kills >= player.quest_target:
            b = int(player.quest_target * 50)
            player.credits += b
            print("\n" + engine.translate("000D03", [b]))
            player.quest_kills, player.quest_target = 0, player.quest_target + 5
        if player.xp >= 100:
            player.lvl += 1
            player.atk += 5
            player.max_hp += 20
            player.hp = player.max_hp
            player.xp = 0
            print(engine.translate("000103", [player.name, int(player.lvl), int(player.atk)]))
        gather_resources(engine, player)
        trigger_story_progress(engine, player)
        return True

    return False
    return False

def main():
    try:
        engine = I18nEngine()
        engine.load_file(str(BASE_CATALOG))
    except Exception as e:
        print(translate_with_fallback(engine, UI_TOKENS["error_generic"], [e]))
        return

    player = Player.load_game() or Player("Operator")
    for pkg_id in player.knowledge_packages:
        load_knowledge_package(engine, pkg_id)
    load_active_world_event_state()
    if not apply_shard_token(engine, player, player.current_shard_token):
        apply_shard_token(engine, player, DEFAULT_SHARD_TOKEN)
    try:
        refresh_runtime_catalog(engine, player)
    except Exception as e:
        print(translate_with_fallback(engine, UI_TOKENS["error_catalog"], [e]))
        return
    trigger_story_progress(engine, player)
    print("\n" + engine.translate("000100"))

    while True:
        if player.hp <= 0:
            print("\n" + engine.translate("000B99"))
            break
        menu_entries = parse_menu_entries(engine)
        if menu_entries:
            header_text = translate_with_fallback(engine, "000M100").strip()
            if header_text:
                print("\n" + header_text)
            else:
                print()
            for entry in menu_entries:
                print(f"({entry['number']}) {entry['label']}")
        else:
            print("\n" + engine.translate("000200"))
        c = input("> ").strip()
        if c == "DEADBEEF":
            player.admin_mode = True
            print(engine.translate("000106"))
            continue
        outcome = handle_menu_input(engine, player, c, menu_entries)
        if outcome == "EXIT":
            break
    input("\n" + translate_with_fallback(engine, UI_TOKENS["matrix_exit"]))


if __name__ == "__main__":
    main()

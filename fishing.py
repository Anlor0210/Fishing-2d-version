# Python translation of the PowerShell Fishing Game
# Console-based fishing game with multiple zones, shop, and save/load system

import json
import math
import os
import random
import time
import sys
import select
import hashlib
from typing import Dict, List
from dataclasses import dataclass, asdict
try:
    import curses
except Exception:  # pragma: no cover - curses may be missing on some platforms
    curses = None

if sys.platform == 'win32':
    import msvcrt
else:
    import tty
    import termios

# --------------------------- Utility functions ---------------------------

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Simple ANSI color mapping (no external deps)
COLORS = {
    "DarkGray": "\033[90m",
    "Green": "\033[32m",
    "Magenta": "\033[35m",
    "Cyan": "\033[36m",
    "Yellow": "\033[33m",
    "DarkYellow": "\033[33m",
    "Red": "\033[31m",
    "White": "\033[37m",
    "Reset": "\033[0m",
}

def color_text(text: str, color: str) -> str:
    return f"{COLORS.get(color, COLORS['White'])}{text}{COLORS['Reset']}"

# Season helpers
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
SEASON_EMOJI = {
    "Spring": "🌸",
    "Summer": "☀️",
    "Autumn": "🍂",
    "Winter": "❄️",
}

# Non-blocking keyboard helpers
class RawInput:
    def __enter__(self):
        if sys.platform != 'win32':
            self.fd = sys.stdin.fileno()
            self.old_settings = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if sys.platform != 'win32':
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

def key_pressed():
    if sys.platform == 'win32':
        return msvcrt.kbhit()
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    return dr != []

def read_key():
    if sys.platform == 'win32':
        return msvcrt.getch().decode('utf-8')
    return sys.stdin.read(1)

ENTER_KEYS = ('\r', '\n', '\r\n', '\x0d')

# --------------------------- Fish data ---------------------------

FISH_LAKE = [
    {"name": "Carp", "rarity": "Common", "price": 1, "xp": 5, "seasons": ["Spring", "Summer"]},
    {"name": "Tilapia", "rarity": "Common", "price": 1.25, "xp": 5},
    {"name": "Grass carp", "rarity": "Uncommon", "price": 5, "xp": 7},
    {"name": "Catfish", "rarity": "Rare", "price": 10, "xp": 10, "time_of_day": ["Night"]},
    {"name": "Snakehead fish", "rarity": "Legendary", "price": 50, "xp": 50},
    {"name": "Bluegill", "rarity": "Common", "price": 3, "xp": 5, "time_of_day": ["Day"]},
    {"name": "Northern Pike", "rarity": "Uncommon", "price": 12, "xp": 15},
    {"name": "Largemouth Bass", "rarity": "Common", "price": 8, "xp": 10},
    {"name": "Rainbow Trout", "rarity": "Uncommon", "price": 15, "xp": 12, "time_of_day": ["Day"]},
    {"name": "Yellow Perch", "rarity": "Common", "price": 5, "xp": 7, "seasons": ["Autumn", "Winter"]},
    {"name": "Muskellunge", "rarity": "Legendary", "price": 40, "xp": 35, "seasons": ["Summer"]},
    {"name": "Walleye", "rarity": "Common", "price": 7, "xp": 9},
    {"name": "Lake Sturgeon", "rarity": "Rare", "price": 20, "xp": 25},
    {"name": "White Bass", "rarity": "Uncommon", "price": 6, "xp": 8},
    {"name": "Channel Catfish", "rarity": "Rare", "price": 18, "xp": 20},
]

FISH_SEA = [
    {"name": "Starfish", "rarity": "Uncommon", "base_price": 1.25, "xp": 7},
    {"name": "Tuna", "rarity": "Rare", "base_price": 2, "xp": 10},
    {"name": "Shark", "rarity": "Rare", "base_price": 7, "xp": 10},
    {"name": "Whale", "rarity": "Legendary", "base_price": 5, "xp": 50},
    {"name": "Flying Fish", "rarity": "Uncommon", "base_price": 2.5, "xp": 10},
    {"name": "Swordfish", "rarity": "Rare", "base_price": 18, "xp": 30},
    {"name": "Electric Eel", "rarity": "Rare", "base_price": 22, "xp": 30},
    {"name": "Lionfish", "rarity": "Epic", "base_price": 35, "xp": 100},
    {"name": "Giant Blue Marlin", "rarity": "Legendary", "base_price": 55, "xp": 1000},
    {"name": "Sunfish", "rarity": "Mythical", "base_price": 70, "xp": 1000},
    {"name": "Dolphin", "rarity": "Uncommon", "base_price": 15, "xp": 20},
    {"name": "Barracuda", "rarity": "Rare", "base_price": 30, "xp": 40},
    {"name": "Clownfish", "rarity": "Common", "base_price": 6, "xp": 8},
    {"name": "Mahi-Mahi", "rarity": "Rare", "base_price": 25, "xp": 30},
    {"name": "Blue Marlin", "rarity": "Legendary", "base_price": 90, "xp": 100},
    {"name": "Kingfish", "rarity": "Uncommon", "base_price": 18, "xp": 22},
    {"name": "Emperor Angelfish", "rarity": "Rare", "base_price": 35, "xp": 45},
    {"name": "Grouper", "rarity": "Uncommon", "base_price": 12, "xp": 16},
    {"name": "Triggerfish", "rarity": "Rare", "base_price": 20, "xp": 25},
    {"name": "Napoleon Wrasse", "rarity": "Legendary", "base_price": 60, "xp": 80},
]

FISH_BATHYAL = [
    {"name": "Deep-sea Dragonfish", "rarity": "Rare", "base_price": 35, "xp": 45},
    {"name": "Lanternfish", "rarity": "Uncommon", "base_price": 15, "xp": 18},
    {"name": "Anglerfish", "rarity": "Uncommon", "base_price": 20, "xp": 25},
    {"name": "Black Swallower", "rarity": "Legendary", "base_price": 90, "xp": 120},
    {"name": "Goblin Shark", "rarity": "Legendary", "base_price": 50, "xp": 70},
    {"name": "Cusk Eel", "rarity": "Rare", "base_price": 25, "xp": 30},
    {"name": "Viperfish", "rarity": "Rare", "base_price": 30, "xp": 40},
    {"name": "Giant Squid", "rarity": "Legendary", "base_price": 80, "xp": 100},
    {"name": "Brilliant Lanternfish", "rarity": "Rare", "base_price": 18, "xp": 22},
    {"name": "Swallowtail", "rarity": "Uncommon", "base_price": 12, "xp": 15},
]

FISH_ABYSS_TRENCH = [
    {"name": "Lanternfish", "rarity": "Common", "price": 15},
    {"name": "Angler Leviathan", "rarity": "Legendary", "price": 100, "xp": 150},
    {"name": "Giant Squid", "rarity": "Legendary", "price": 75, "xp": 100},
    {"name": "Ancient Key", "rarity": "Legendary", "price": 25},
    {"name": "Abyssal Octopus", "rarity": "Rare", "price": 50, "xp": 60},
    {"name": "Cusk Eel", "rarity": "Rare", "price": 40, "xp": 50},
    {"name": "Black Swallower", "rarity": "Legendary", "price": 80, "xp": 120},
    {"name": "Abyssal Dragonfish", "rarity": "Rare", "price": 60, "xp": 70},
    {"name": "Swallower Eel", "rarity": "Rare", "price": 50, "xp": 60},
    {"name": "Abyssal Squid", "rarity": "Rare", "price": 70, "xp": 80},
    {"name": "Giant Anglerfish", "rarity": "Legendary", "price": 100, "xp": 130},
    {"name": "Benthic Eel", "rarity": "Uncommon", "price": 30, "xp": 40},
    {"name": "Abyssal Leviathan", "rarity": "Legendary", "price": 200, "xp": 350},
    {"name": "Trench Dragonfish", "rarity": "Rare", "price": 80, "xp": 120},
    {"name": "Bioluminescent Squid", "rarity": "Rare", "price": 50, "xp": 75},
    {"name": "Ghost Shark", "rarity": "Legendary", "price": 150, "xp": 200},
    {"name": "Colossal Squid", "rarity": "Mythical", "price": 250, "xp": 400},
    {"name": "Abyssal Angler", "rarity": "Legendary", "price": 175, "xp": 250},
    {"name": "Barreleye Fish", "rarity": "Rare", "price": 40, "xp": 55},
    {"name": "Abyssal Cusk Eel", "rarity": "Common", "price": 20, "xp": 30},
    {"name": "Abyssal Lanternfish", "rarity": "Uncommon", "price": 25, "xp": 40},
    {"name": "Giant Fangtooth", "rarity": "Legendary", "price": 100, "xp": 150},
]

FISH_ANCIENT_SEA = [
    {"name": "Mosasaurus", "rarity": "Legendary", "price": 350, "xp": 500},
    {"name": "Dunkleosteus", "rarity": "Mythical", "price": 500, "xp": 700},
    {"name": "Megalodon", "rarity": "Mythical", "price": 1000, "xp": 1500},
    {"name": "Leedsichthys", "rarity": "Exotic", "price": 250, "xp": 300},
    {"name": "Shonisaurus", "rarity": "Legendary", "price": 300, "xp": 400},
    {"name": "Ichthyosaurus", "rarity": "Legendary", "price": 200, "xp": 250},
    {"name": "Tylosaurus", "rarity": "Legendary", "price": 250, "xp": 300},
    {"name": "Pliosaurus", "rarity": "Legendary", "price": 350, "xp": 500},
    {"name": "Tyrannosaurus Rex", "rarity": "Mythical", "price": 600, "xp": 800},
    {"name": "Sharksaurus", "rarity": "Legendary", "price": 450, "xp": 600},
    {"name": "Acanthodes", "rarity": "Exotic", "price": 300, "xp": 350},
]

FISH_MYSTIC_SPRING = [
    {"name": "Prism Trout", "rarity": "Rare", "price": 15, "xp": 10},
    {"name": "Spirit Koi", "rarity": "Epic", "price": 25, "xp": 25},
    {"name": "Phoenix Scale Carp", "rarity": "Mythical", "price": 50, "xp": 40},
    {"name": "Moonlit Koi", "rarity": "Mythical", "price": 100, "xp": 150},
    {"name": "Water Sprite", "rarity": "Epic", "price": 75, "xp": 100},
    {"name": "Crystal Trout", "rarity": "Legendary", "price": 120, "xp": 200},
    {"name": "Spirit Nymph", "rarity": "Epic", "price": 90, "xp": 120},
    {"name": "Water Dragonfish", "rarity": "Rare", "price": 45, "xp": 60},
    {"name": "Moonbeam Bass", "rarity": "Rare", "price": 40, "xp": 50},
    {"name": "Mystic Swallower", "rarity": "Legendary", "price": 150, "xp": 250},
    {"name": "Luminous Catfish", "rarity": "Uncommon", "price": 25, "xp": 35},
    {"name": "Frostfin Koi", "rarity": "Rare", "price": 50, "xp": 70},
    {"name": "Glimmering Angelfish", "rarity": "Epic", "price": 60, "xp": 80},
]

# Boss definitions for each zone
ZONE_BOSS_MAP = {
    "Lake": {
        "name": "The Drowned King",
        "warning": "🧱 The water trembles... The Drowned King is near!",
    },
    "Sea": {
        "name": "Kraken",
        "warning": "🌊 Tentacles rise! The Kraken is attacking!",
    },
    "Bathyal": {
        "name": "Ancient Leviathan",
        "warning": "🐉 A massive shadow looms... Leviathan emerges!",
    },
    "Mystic Spring": {
        "name": "Mystic Dragonfish",
        "warning": "✨ The water glows... A Mystic Dragonfish reveals itself!",
    },
    "Abyss Trench": {
        "name": "Abyss King",
        "warning": "🌑 Darkness thickens... The Abyss King awakens!",
    },
    "Ancient Sea": {
        "name": "Godfish Eternus",
        "warning": "🕯 Time stands still... Godfish Eternus appears!",
    },
}

# Inject boss fish into zone fish lists
FISH_LAKE.append({"name": ZONE_BOSS_MAP["Lake"]["name"], "rarity": "???", "price": 1000, "xp": 6000})
FISH_SEA.append({"name": ZONE_BOSS_MAP["Sea"]["name"], "rarity": "???", "base_price": 1000, "xp": 7000})
FISH_BATHYAL.append({"name": ZONE_BOSS_MAP["Bathyal"]["name"], "rarity": "???", "base_price": 1000, "xp": 8000})
FISH_MYSTIC_SPRING.append({"name": ZONE_BOSS_MAP["Mystic Spring"]["name"], "rarity": "???", "price": 1000, "xp": 9000})
FISH_ABYSS_TRENCH.append({"name": ZONE_BOSS_MAP["Abyss Trench"]["name"], "rarity": "???", "price": 1000, "xp": 9500})
FISH_ANCIENT_SEA.append({"name": ZONE_BOSS_MAP["Ancient Sea"]["name"], "rarity": "???", "price": 1000, "xp": 10000})

# Map zones to their fish lists for easy lookup throughout the game
ZONE_FISH_MAP = {
    "Lake": FISH_LAKE,
    "Sea": FISH_SEA,
    "Bathyal": FISH_BATHYAL,
    "Mystic Spring": FISH_MYSTIC_SPRING,
    "Abyss Trench": FISH_ABYSS_TRENCH,
    "Ancient Sea": FISH_ANCIENT_SEA,
}

# Base reward values per rarity used for quest reward calculation
RARITY_BASE_REWARD = {
    "Common": 10,
    "Uncommon": 20,
    "Rare": 40,
    "Epic": 80,
    "Legendary": 160,
    "Mythical": 320,
    "Exotic": 640,
}

EXOTIC_FISH_FULL_MOON = [
    {"name": "Phantom Shark", "rarity": "Exotic", "price": 100, "xp": 1000},
    {"name": "Shadowfin", "rarity": "Exotic", "price": 100, "xp": 1000},
    {"name": "Abyssal Ghost", "rarity": "Exotic", "price": 100, "xp": 1000},
]

SEA_PRICE_MULTIPLIER = {
    "Uncommon": 1.25,
    "Rare": 2,
    "Epic": 3,
    "Legendary": 5,
    "Mythical": 7,
}

SHOP_ITEMS = [
    {"name": "Boat", "price": 25000, "description": "Access Sea zone"},
    {"name": "Submarine", "price": 1000000, "description": "Access Bathyal zone"},
    {"name": "Torch", "price": 5000, "description": "Access Mystic Spring zone"},
    {"name": "Submarine Upgrade 01", "price": 10000000, "description": "Access Abyss Trench zone"},
    {"name": "Submarine Upgrade 02", "price": 100000000, "description": "Access Ancient Sea zone"},
]

@dataclass
class Quest:
    """Represents a quest tied to a specific zone."""

    quest_type: int  # 1: specific fish, 2: rarity
    zone: str
    target_fish: str | None = None
    rarity: str | None = None
    amount: int = 1
    progress: int = 0
    reward: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    def is_completed(self) -> bool:
        return self.progress >= self.amount


class QuestManager:
    """Manages quests for all zones."""

    def __init__(self, quests_data: Dict[str, List[Dict]] | None = None):
        self.zone_quests: Dict[str, List[Quest]] = {}
        # Initialize quests from saved data if provided
        if quests_data:
            for zone, quests in quests_data.items():
                self.zone_quests[zone] = [Quest(**q) for q in quests]
                for quest in self.zone_quests[zone]:
                    if quest.reward == 0:
                        rarity = quest.rarity
                        if quest.quest_type == 1 and not rarity:
                            fish_list = ZONE_FISH_MAP.get(zone, [])
                            for f in fish_list:
                                if f["name"] == quest.target_fish:
                                    rarity = f["rarity"]
                                    quest.rarity = rarity
                                    break
                        base = RARITY_BASE_REWARD.get(rarity, 10)
                        quest.reward = base * quest.amount
        # Ensure every zone has a quest list
        for zone in ZONE_FISH_MAP.keys():
            self.zone_quests.setdefault(zone, [])
            # Trim excess quests and fill up to 10
            self.zone_quests[zone] = self.zone_quests[zone][:10]
            while len(self.zone_quests[zone]) < 10:
                self.zone_quests[zone].append(self.generate_quest(zone))

    def to_dict(self) -> Dict[str, List[Dict]]:
        return {zone: [q.to_dict() for q in quests] for zone, quests in self.zone_quests.items()}

    def get_quests_for_zone(self, zone_name: str) -> List[Quest]:
        return self.zone_quests.get(zone_name, [])

    def generate_quest(self, zone: str) -> Quest:
        fish_list = [
            f for f in ZONE_FISH_MAP.get(zone, [])
            if f.get("rarity") not in ("???", "Exotic")
        ]
        if not fish_list:
            return Quest(1, zone, target_fish="Carp", amount=1, reward=10)
        quest_type = random.choice([1, 2])
        amount = random.randint(1, 20)
        if quest_type == 1:
            fish = random.choice(fish_list)
            rarity = fish["rarity"]
            target_fish = fish["name"]
        else:
            rarity = random.choice(list({f["rarity"] for f in fish_list}))
            target_fish = None

        max_amount = 15
        if rarity == "Legendary":
            max_amount = 5
        elif rarity == "Boss":
            max_amount = 1
        amount = min(amount, max_amount)

        base_values = {
            "Common": 10,
            "Uncommon": 20,
            "Rare": 100,
            "Epic": 175,
            "Mythical": 200,
            "Legendary": 500,
            "Boss": 10000,
        }
        reward = base_values.get(rarity, 0) * amount
        return Quest(
            quest_type,
            zone,
            target_fish=target_fish,
            rarity=rarity,
            amount=amount,
            reward=reward,
        )

    def finish_quest(self, zone: str, quest_index: int) -> int:
        quests = self.get_quests_for_zone(zone)
        if quest_index < 0 or quest_index >= len(quests):
            return 0
        quest = quests[quest_index]
        if not quest.is_completed():
            return 0
        reward = quest.reward
        quests[quest_index] = self.generate_quest(zone)
        return reward

    def show_quests_for_zone(self, zone_name: str):
        quests = self.get_quests_for_zone(zone_name)
        if not quests:
            print("No quests available here.")
            return
        print("Available quests:")
        for q in quests:
            if q.quest_type == 1:
                desc = f"Catch {q.amount} {q.target_fish}"
            else:
                desc = f"Catch {q.amount} {q.rarity} fish"
            status = f"{q.progress}/{q.amount}"
            print(f"- {desc} ({status})")

    def show_all_quests(self):
        for zone, quests in self.zone_quests.items():
            print(f"== {zone} ==")
            for q in quests:
                if q.quest_type == 1:
                    desc = f"Catch {q.amount} {q.target_fish}"
                else:
                    desc = f"Catch {q.amount} {q.rarity} fish"
                print(f"{desc} - {q.progress}/{q.amount}")

    def update_quest_progress(self, player_zone: str, fish_name: str, rarity: str):
        for q in self.get_quests_for_zone(player_zone):
            if q.quest_type == 1 and q.target_fish == fish_name and q.progress < q.amount:
                q.progress += 1
                print(f"Quest update: {q.target_fish} {q.progress}/{q.amount}")
            elif q.quest_type == 2 and q.rarity == rarity and q.progress < q.amount:
                q.progress += 1
                print(f"Quest update: {q.rarity} fish {q.progress}/{q.amount}")


# --------------------------- Game Class ---------------------------

class Game:
    def __init__(self):
        self.save_file = os.path.join(os.getcwd(), 'save_data.json')
        # default values
        self.balance = 100
        self.inventory: List[Dict] = []
        self.has_submarine = False
        self.has_boat = False
        self.has_torch = False
        self.has_abyss_trench_access = False
        self.has_ancient_sea_access = False
        self.has_ancient_key = False
        self.has_floating_key = False
        self.current_hour = 0
        self.current_day = 0
        self.event = "Nothing"
        self.level = 0
        self.xp = 0
        self.discovery: Dict[str, Dict] = {}
        self.current_zone = "Lake"
        self.current_fish_list = FISH_LAKE
        self.current_zone_catch_length = 5
        self.current_fish = None
        self.loaded_quests: Dict[str, List[Dict]] = {}
        # load existing data if any
        self.load_game()
        self.quest_manager = QuestManager(self.loaded_quests)

    # -------------- Save & Load --------------
    def save_game(self):
        data = {
            'balance': self.balance,
            'inventoryFish': self.inventory,
            'hasSubmarine': self.has_submarine,
            'hasBoat': self.has_boat,
            'hasTorch': self.has_torch,
            'hasAbyssTrenchAccess': self.has_abyss_trench_access,
              'hasAncientSeaAccess': self.has_ancient_sea_access,
              'hasAncientKey': self.has_ancient_key,
              'hasFloatingKey': self.has_floating_key,
              'currentHour': self.current_hour,
              'currentDay': self.current_day,
              'event': self.event,
              'level': self.level,
              'xp': self.xp,
            'discovery': self.discovery,
            'quests': self.quest_manager.to_dict(),
        }
        data_to_hash = data.copy()
        serialized = json.dumps(data_to_hash, sort_keys=True)
        data['hash'] = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_game(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            saved_hash = data.pop('hash', '')
            serialized = json.dumps(data, sort_keys=True)
            computed_hash = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
            if saved_hash != computed_hash:
                print("⚠️ Save file has been tampered with!")
                exit()
            self.balance = data.get('balance', 100)
            self.inventory = data.get('inventoryFish', [])
            self.has_submarine = data.get('hasSubmarine', False)
            self.has_boat = data.get('hasBoat', False)
            self.has_torch = data.get('hasTorch', False)
            self.has_abyss_trench_access = data.get('hasAbyssTrenchAccess', False)
            self.has_ancient_sea_access = data.get('hasAncientSeaAccess', False)
            self.has_ancient_key = data.get('hasAncientKey', False)
            self.has_floating_key = data.get('hasFloatingKey', False)
            self.current_hour = data.get('currentHour', 0)
            self.current_day = data.get('currentDay', 0)
            self.event = data.get('event', 'Nothing')
            self.level = data.get('level', 0)
            self.xp = data.get('xp', 0)
            self.discovery = data.get('discovery', {})
            self.loaded_quests = data.get('quests', {})
        else:
            # defaults already set
            self.loaded_quests = {}

    # -------------- Level & XP --------------
    def calculate_xp_for_level(self, level: int) -> int:
        if level == 0:
            return 100
        return 100 + (level * 100)

    def check_level_up(self):
        xp_needed = self.calculate_xp_for_level(self.level)
        while self.xp >= xp_needed and self.level < 100:
            self.xp -= xp_needed
            self.level += 1
            if self.level >= 100:
                self.level = 100
                self.xp = 0
                print("Congratulations! You reached max level 100!")
                return
            else:
                print(f"Congratulations! You leveled up to level {self.level}!")
            xp_needed = self.calculate_xp_for_level(self.level)
        if self.level >= 100:
            self.xp = 0

    # -------------- Rarity helpers --------------
    def get_rarity_color(self, rarity: str) -> str:
        mapping = {
            "Common": "DarkGray",
            "Uncommon": "Green",
            "Rare": "Magenta",
            "Epic": "Cyan",
            "Legendary": "Yellow",
            "Mythical": "DarkYellow",
            "Exotic": "Red",
            "???": "Red",
        }
        return mapping.get(rarity, "White")

    def get_xp_by_rarity(self, rarity: str) -> int:
        values = {
            "Common": 5,
            "Uncommon": 10,
            "Rare": 30,
            "Epic": 100,
            "Legendary": 1000,
            "Mythical": 1000,
            "Exotic": 100000,
        }
        return values.get(rarity, 0)

    # -------------- Zone helpers --------------
    def get_unlocked_zones(self) -> List[str]:
        zones = ["Lake"]
        if self.has_boat:
            zones.append("Sea")
        if self.has_submarine:
            zones.append("Bathyal")
        if self.has_torch:
            zones.append("Mystic Spring")
        if self.has_abyss_trench_access:
            zones.append("Abyss Trench")
        if self.has_ancient_sea_access:
            zones.append("Ancient Sea")
        return zones

    def get_fish_list_for_zone(self, zone: str) -> List[Dict]:
        return ZONE_FISH_MAP.get(zone, FISH_LAKE)

    def get_speed(self) -> float:
        speed = 0.1  # seconds
        if self.current_zone in ("Sea", "Mystic Spring"):
            speed = max(speed / 2, 0.01)
        elif self.current_zone == "Bathyal":
            speed = max(speed / 4, 0.01)
        elif self.current_zone == "Abyss Trench":
            speed = max(speed / 7, 0.01)
        elif self.current_zone == "Ancient Sea":
            speed = max(speed / 10, 0.01)
        return speed

    # -------------- Discovery --------------
    def update_discovery(self, zone: str, fish_name: str, weight: float, value: float):
        zone_data = self.discovery.setdefault(zone, {})
        entry = zone_data.setdefault(fish_name, {
            'count': 0,
            'maxWeight': 0,
            'maxValue': 0,
        })
        entry['count'] += 1
        if weight > entry['maxWeight']:
            entry['maxWeight'] = weight
        if value > entry['maxValue']:
            entry['maxValue'] = value
        zone_data[fish_name] = entry
        self.discovery[zone] = zone_data

    # -------------- Boss minigame --------------
    def run_boss_minigame_rounds(self, rounds: int = 5, zone_len: int = 3, speed: float = 0.02) -> bool:
        bar = "--------------------------"
        for _ in range(rounds):
            target_start = random.randint(5, len(bar) - zone_len - 1)
            target_end = target_start + zone_len - 1
            with RawInput():
                prev_i = -1
                for i in range(len(bar)):
                    clear_screen()
                    before = bar[:i]
                    after = bar[i + 1:]
                    line = before + "|" + after
                    target_line = ''.join('=' if target_start <= j <= target_end else ' ' for j in range(len(bar)))
                    print("Boss battle!")
                    print(line)
                    print(target_line)
                    time.sleep(speed)
                    if key_pressed():
                        ch = read_key()
                        if isinstance(ch, str):
                            is_enter = ch in ENTER_KEYS or ch == ' '
                        else:
                            codes = {10, 13, ord(' ')}
                            if curses:
                                codes.add(curses.KEY_ENTER)
                            is_enter = ch in codes
                        if is_enter:
                            in_zone = (target_start <= i <= target_end) or (
                                prev_i >= 0 and target_start <= prev_i <= target_end
                            )
                            if in_zone:
                                break
                            else:
                                print("\n>> Missed! The boss slips away! <<")
                                return False
                    prev_i = i
                else:
                    print("\n>> Time's up! The boss escaped! <<")
                    return False
        return True

    # -------------- Fish generation --------------
    def get_fish_by_weighted_random(self, fish_list: List[Dict]) -> Dict | None:
        # Chance to encounter zone boss
        if random.random() < 0.01 and self.current_zone in ZONE_BOSS_MAP:
            boss = ZONE_BOSS_MAP[self.current_zone]
            print(boss["warning"])
            success = self.run_boss_minigame_rounds()
            if success:
                weight = random.randint(1000, 10000)
                boss_entry = next((f for f in fish_list if f["name"] == boss["name"]), {})
                boss_xp = boss_entry.get("xp", 0)
                caught = {
                    "name": boss["name"],
                    "rarity": "???",
                    "price": 1000,
                    "weight": weight,
                    "zone": self.current_zone,
                }
                self.current_fish = caught.copy()
                self.inventory.append(self.current_fish.copy())
                self.xp += boss_xp
                self.check_level_up()
                color = self.get_rarity_color("???")
                print("\n" + color_text(f">> You caught {boss['name']} [???] - {weight} kg!", color))
                value = round(weight * 1000, 2)
                self.update_discovery(self.current_zone, boss["name"], weight, value)
                self.quest_manager.update_quest_progress(self.current_zone, boss["name"], "???")
                self.save_game()
                input("Press Enter to continue...")
            else:
                print("\n>> The boss escaped! <<")
                input("Press Enter to continue...")
            return None
        time_of_day = self.get_time_of_day()
        season = self.get_current_season()
        filtered: List[Dict] = []
        for fish in fish_list:
            if fish.get('rarity') == '???':
                continue
            allowed_times = fish.get('time_of_day')
            allowed_seasons = fish.get('seasons')
            if allowed_times and time_of_day not in allowed_times:
                continue
            if allowed_seasons and season not in allowed_seasons:
                continue
            filtered.append(fish)
        if not filtered:
            filtered = fish_list
        weighted = []
        for fish in filtered:
            rarity = fish.get('rarity', 'Common')
            weight = {
                'Common': 5,
                'Uncommon': 3,
                'Rare': 2,
                'Epic': 1,
                'Legendary': 1,
                'Mythical': 1,
                'Exotic': 0,
            }.get(rarity, 3)
            weighted.extend([fish] * weight)
        return random.choice(weighted)

    def generate_weight(self, name: str, rarity: str) -> float:
        if name == "Shark":
            return random.randint(50, 1000)
        if name == "Whale":
            return random.randint(100, 10000)
        if name == "Tuna":
            return random.randint(10, 75)
        if name == "Flying Fish":
            return random.uniform(1, 3)
        if name == "Swordfish":
            return random.randint(100, 300)
        if name == "Electric Eel":
            return random.randint(10, 50)
        if name == "Lionfish":
            return random.uniform(2, 6)
        if name == "Giant Blue Marlin":
            return random.randint(300, 800)
        if name == "Sunfish":
            return random.randint(500, 1500)
        if name == "Deep-sea Dragonfish":
            return random.randint(5, 20)
        if name == "Lanternfish":
            return random.randint(5, 15)
        if name == "Anglerfish":
            return random.randint(10, 25)
        if name == "Black Swallower":
            return random.randint(2, 10)
        if name == "Goblin Shark":
            return random.randint(50, 100)
        if name == "Angler Leviathan":
            return random.randint(15, 100)
        if name == "Giant Squid":
            return random.randint(1000, 5000)
        if name == "Ancient Key":
            return random.randint(100, 500)
        if name == "Mosasaurus" or name == "Dunkleosteus":
            return random.randint(1000, 3000)
        if name == "Megalodon":
            return random.randint(10000, 50000)
        if name == "Leedsichthys":
            return random.randint(100000, 1000000)
        if name == "Prism Trout":
            return random.randint(20, 80)
        if name == "Spirit Koi":
            return random.randint(20, 150)
        if name == "Phoenix Scale Carp":
            return random.randint(100, 300)
        # default by rarity
        if rarity == "Common":
            return random.uniform(0.5, 2.5)
        if rarity == "Uncommon":
            return random.uniform(1.0, 4.0)
        if rarity == "Rare":
            return random.uniform(2.0, 6.0)
        if rarity == "Epic":
            return random.uniform(3.0, 8.0)
        if rarity == "Legendary":
            return random.uniform(5.0, 12.0)
        if rarity == "Mythical":
            return random.uniform(8.0, 20.0)
        return random.uniform(1.0, 3.0)

    # -------------- Zone choosing --------------
    def choose_zone(self):
        clear_screen()
        print("Choose your fishing zone:")
        print("1. Sea (Need Boat)")
        print("2. Lake")
        print("3. Bathyal (Need Submarine)")
        print("4. Mystic Spring (Need Torch)")
        print("5. Abyss Trench (Need Submarine Upgrade 01)")
        print("6. Ancient Sea (Need Submarine Upgrade 02)")
        choice = input("Pick your choice (1/2/3/4/5/6): ")
        if choice == "1":
            if not self.has_boat:
                print("You don't have a boat to access Sea zone.")
                time.sleep(3)
                return
            self.current_zone = "Sea"
            self.current_fish_list = FISH_SEA
            self.current_zone_catch_length = 3
            print("You chose Sea zone. Catch zone length set to 3.")
        elif choice == "2":
            self.current_zone = "Lake"
            self.current_fish_list = FISH_LAKE
            self.current_zone_catch_length = 5
            print("You chose Lake zone. Catch zone length set to 5.")
        elif choice == "3":
            if not self.has_submarine:
                print("You don't have a submarine to access Bathyal zone.")
                time.sleep(3)
                return
            self.current_zone = "Bathyal"
            self.current_fish_list = FISH_BATHYAL
            self.current_zone_catch_length = 5
            print("You chose Bathyal zone. Minigame speed x4 faster.")
        elif choice == "4":
            if not self.has_torch:
                print("You don't have a Torch to access Mystic Spring.")
                time.sleep(3)
                return
            self.current_zone = "Mystic Spring"
            self.current_fish_list = FISH_MYSTIC_SPRING
            self.current_zone_catch_length = 5
            print("You chose Mystic Spring. Minigame speed x2 faster.")
        elif choice == "5":
            if not self.has_abyss_trench_access:
                print("You don't have Submarine Upgrade 01 to access Abyss Trench.")
                time.sleep(3)
                return
            self.current_zone = "Abyss Trench"
            self.current_fish_list = FISH_ABYSS_TRENCH
            self.current_zone_catch_length = 4
            print("You chose Abyss Trench. Minigame speed x7 faster.")
        elif choice == "6":
            if not self.has_ancient_sea_access:
                print("You don't have access to Ancient Sea.")
                time.sleep(3)
                return
            self.current_zone = "Ancient Sea"
            self.current_fish_list = FISH_ANCIENT_SEA
            self.current_zone_catch_length = 3
            print("You chose Ancient Sea. Minigame speed x10 faster.")
        else:
            print("Invalid choice, defaulting to Lake.")
            self.current_zone = "Lake"
            self.current_fish_list = FISH_LAKE
            self.current_zone_catch_length = 5
            time.sleep(2)
        self.quest_manager.show_quests_for_zone(self.current_zone)
        time.sleep(2)

    # -------------- Time & Events --------------
    def get_time_of_day(self) -> str:
        if 6 <= self.current_hour < 18:
            return "Day"
        if 18 <= self.current_hour < 22:
            return "Sunset"
        return "Night"

    def get_current_season(self) -> str:
        return SEASONS[(self.current_day // 7) % 4]

    def advance_time(self):
        prev_hour = self.current_hour
        self.current_hour = (self.current_hour + 1) % 24
        if self.current_hour == 0 and prev_hour == 23:
            self.current_day += 1
        if self.current_hour < 20:
            self.event = "Nothing"
        elif self.current_hour >= 20:
            if self.event == "Nothing":
                if random.randint(1, 100) <= 20:
                    self.event = "Full Moon"
                else:
                    self.event = "Nothing"

    # -------------- Quests --------------
    def show_quest_menu(self):
        while True:
            clear_screen()
            print(f"_____QUEST ZONE: {self.current_zone}_____")
            quests = self.quest_manager.get_quests_for_zone(self.current_zone)
            for idx, q in enumerate(quests, 1):
                if q.quest_type == 1:
                    desc = f"Catch {q.amount} {q.target_fish}"
                else:
                    desc = f"Catch {q.amount} {q.rarity} Fish"
                status = "Finished" if q.is_completed() else "Didn't Finish"
                print(f"{idx}. {desc} ({status})")
            print("0. Return to main menu")
            choice = input("Select a quest: ")
            if choice == '0':
                break
            if choice.isdigit() and 1 <= int(choice) <= len(quests):
                self.show_quest_detail(int(choice) - 1)

    def show_quest_detail(self, quest_index: int):
        while True:
            clear_screen()
            quests = self.quest_manager.get_quests_for_zone(self.current_zone)
            if quest_index < 0 or quest_index >= len(quests):
                return
            q = quests[quest_index]
            if q.quest_type == 1:
                requirement = f"Catch {q.amount} {q.target_fish}"
            else:
                requirement = f"Catch {q.amount} {q.rarity} Fish"
            print(f"___Quest{quest_index+1:02d}___")
            print(f"1. Requirement: {requirement}")
            print(f"2. Reward: Gain money: {q.reward}")
            print(f"3. Progress: {q.progress}/{q.amount}")
            print("4. Finish")
            print("0. Return")
            choice = input("Choose: ")
            if choice == '4':
                if q.is_completed():
                    reward = self.quest_manager.finish_quest(self.current_zone, quest_index)
                    self.balance += reward
                    self.save_game()
                    print(f"Quest completed! You gained {reward}$")
                    input("Press Enter to continue...")
                    break
                else:
                    print("You haven't met the requirements yet.")
                    input("Press Enter to continue...")
            elif choice == '0':
                break

    # -------------- Menu --------------
    def show_menu(self):
        clear_screen()
        xp_needed = self.calculate_xp_for_level(self.level)
        if self.level >= 100:
            xp_percent = 100
        else:
            xp_percent = round((self.xp / xp_needed) * 100, 2) if xp_needed else 0
        print("_____MENU_____")
        print(f"Level: {self.level} ({xp_percent}%)")
        print(f"Balance: {round(self.balance, 2)}$")
        time_of_day = self.get_time_of_day()
        season = self.get_current_season()
        emoji = SEASON_EMOJI.get(season, "")
        print(f"Time: {self.current_hour:02d}:00 ({time_of_day})")
        print(f"Day: {self.current_day} | Season: {season} {emoji}")
        print(f"Event: {self.event}")
        print("Version: Beta")
        print("1. Fishing")
        print("2. Zone")
        print("3. Sell fish")
        print("4. Inventory")
        print("5. Shop")
        print("6. Discovery Book")
        print("7. Quest")
        print("8. Exit game")

    # -------------- Fishing --------------
    def start_fishing(self):
        clear_screen()
        print(f"You cast your fishing rod in {self.current_zone} zone...")
        time.sleep(0.8)
        frames = [
            "        |",
            "        |",
            "        |",
            "        |",
            "       ---",
            r"      /   \ ",
            "     |     |",
            r"      \___/",
        ]
        for line in frames:
            print(line)
            time.sleep(0.3)
        is_exotic = False
        wait_seconds = 2
        while True:
            print("\nWaiting for a bite...")
            time.sleep(wait_seconds)
            fish_bite = random.randint(1, 100) <= 60
            if fish_bite:
                print("\n>>> Fish Bite! <<<")
                time.sleep(1)
                if (self.current_zone == "Bathyal" and self.event == "Full Moon" \
                        and random.randint(1, 100) <= 100):
                    is_exotic = True
                    print(">>> Something Stranger Bite! <<<")
                    print(">>> Your minigame will x10 speed! <<<")
                    print(">>> Your catch zone will be 2 <<<")
                    success = self.start_minigame(full_moon_event=True)
                else:
                    success = self.start_minigame()
                if success:
                    self.obtain_fish(full_moon_event=is_exotic)
                break
            else:
                wait_seconds = min(wait_seconds + 1, 6)

    def start_minigame(self, full_moon_event=False) -> bool:
        bar = "--------------------------"  # length 26
        if full_moon_event:
            zone_length = 2
            speed = 0.01
        else:
            zone_length = self.current_zone_catch_length
            speed = self.get_speed()
        target_start = random.randint(5, len(bar) - zone_length - 1)
        target_end = target_start + zone_length - 1
        with RawInput():
            prev_i = -1
            for i in range(len(bar)):
                clear_screen()
                before = bar[:i]
                after = bar[i+1:]
                line = before + "|" + after
                target_line = ''.join('=' if target_start <= j <= target_end else ' ' for j in range(len(bar)))
                print("Catch zone:")
                print(line)
                print(target_line)
                time.sleep(speed)
                if key_pressed():
                    ch = read_key()
                    if isinstance(ch, str):
                        is_enter = ch in ENTER_KEYS or ch == ' '
                    else:
                        codes = {10, 13, ord(' ')}
                        if curses:
                            codes.add(curses.KEY_ENTER)
                        is_enter = ch in codes
                    if is_enter:
                        in_zone = (target_start <= i <= target_end) or (
                            prev_i >= 0 and target_start <= prev_i <= target_end
                        )
                        if in_zone:
                            if random.randint(1, 100) <= 20:
                                print("\n>> Oh no! The fish run!")
                                return False
                            print("\n>> Success! You caught a fish!")
                            return True
                        else:
                            print("\n>> Missed! The fish got away...")
                            return False
                prev_i = i
            print("\n>> Time's up! The fish escaped!")
        return False

    def obtain_fish(self, full_moon_event=False):
        if full_moon_event:
            fish = random.choice(EXOTIC_FISH_FULL_MOON).copy()
            fish['weight'] = random.randint(1000, 100000)
            price = fish['price']
        else:
            fish = self.get_fish_by_weighted_random(self.current_fish_list)
            if fish is None:
                return
            fish = fish.copy()
            weight = self.generate_weight(fish['name'], fish['rarity'])
            fish['weight'] = round(weight, 1)
            if self.current_zone == "Sea":
                price_multiplier = SEA_PRICE_MULTIPLIER.get(fish['rarity'], 1)
                price = round(fish['base_price'] * price_multiplier, 2)
            elif self.current_zone == "Bathyal":
                price = fish['base_price']
            else:
                price = fish['price']
            fish['price'] = price
        weight = round(fish['weight'], 1)
        self.current_fish = {
            'name': fish['name'],
            'rarity': fish['rarity'],
            'price': fish['price'],
            'weight': weight,
            'zone': self.current_zone,
        }
        self.inventory.append(self.current_fish.copy())
        self.xp += self.get_xp_by_rarity(fish['rarity'])
        self.check_level_up()
        color = 'Red' if fish['rarity'] == 'Exotic' else self.get_rarity_color(fish['rarity'])
        print("\n" + color_text(f">> You caught a {fish['name']} [{fish['rarity']}] - {weight} kg.", color))
        value = round(weight * fish['price'], 2)
        self.update_discovery(self.current_zone, fish['name'], weight, value)
        self.quest_manager.update_quest_progress(self.current_zone, fish['name'], fish['rarity'])
        if fish['name'] == 'Ancient Key' and not self.has_ancient_key:
            self.has_ancient_key = True
            print(">> You obtained the Ancient Key!")
        if self.current_zone == "Sea" and not self.has_floating_key and random.random() < 0.01:
            self.has_floating_key = True
            print("🔑 You found a mysterious FLOATING KEY hidden inside the fish!")
            print("☁️ Now you can access the Floating Island when it appears!")
        self.save_game()
        input("Press Enter to continue...")

    # -------------- Inventory / Selling --------------
    def sell_fish(self):
        clear_screen()
        if not self.inventory:
            print("You have no fish to sell.")
            input("Press Enter to return to menu")
            return
        print("Fish in inventory:")
        for idx, f in enumerate(self.inventory, 1):
            color = self.get_rarity_color(f['rarity'])
            print(color_text(f"{idx}. {f['name']} [{f['rarity']}] - {f['weight']} kg", color))
        option = input("\nType 'all' to sell everything, or 'sell x Name' (e.g., sell x2 Carp): ")
        if option == 'all':
            total = sum(f['weight'] * f['price'] for f in self.inventory)
            total = round(total, 2)
            self.balance += total
            self.inventory = []
            print(f"\nYou earned {total}$ from selling all fish.")
            self.save_game()
            input("Press Enter to return to menu")
            return
        elif option.startswith('sell x'):
            try:
                parts = option.split()
                amount = int(parts[1][1:])  # after 'x'
                name = ' '.join(parts[2:])
            except Exception:
                print("\nInvalid input.")
                input("Press Enter to return to menu")
                return
            found = [f for f in self.inventory if f['name'] == name]
            if len(found) < amount:
                print(f"\nYou don't have enough '{name}' to sell.")
            else:
                sell_list = found[:amount]
                sell_value = 0
                for fish in sell_list:
                    sell_value += fish['weight'] * fish['price']
                    self.inventory.remove(fish)
                sell_value = round(sell_value, 2)
                self.balance += sell_value
                print(f"\nYou sold {amount} {name} for {sell_value}$")
                self.save_game()
            input("Press Enter to return to menu")
            return
        else:
            print("\nInvalid input.")
            input("Press Enter to return to menu")

    def show_inventory(self):
        clear_screen()
        if not self.inventory:
            print("Your fish inventory is empty.")
        else:
            print("Your Fish Inventory:")
            for idx, fish in enumerate(self.inventory, 1):
                color = self.get_rarity_color(fish['rarity'])
                print(color_text(f"{idx}. {fish['name']} [{fish['rarity']}] - {round(fish['weight'],1)} kg", color))
        input("Press Enter to return to menu")

    # -------------- Discovery Book --------------
    def show_discovery_book(self):
        clear_screen()
        print("Discovery Book:")
        print("1. Lake")
        print("2. Sea")
        print("3. Bathyal")
        print("4. Mystic Spring")
        print("5. Abyss Trench")
        print("6. Ancient Sea")
        choice = input("Pick a zone (1-6): ")
        mapping = {
            "1": ("Lake", FISH_LAKE),
            "2": ("Sea", FISH_SEA),
            "3": ("Bathyal", FISH_BATHYAL),
            "4": ("Mystic Spring", FISH_MYSTIC_SPRING),
            "5": ("Abyss Trench", FISH_ABYSS_TRENCH),
            "6": ("Ancient Sea", FISH_ANCIENT_SEA),
        }
        if choice not in mapping:
            return
        zone, fish_list = mapping[choice]
        clear_screen()
        zone_data = self.discovery.get(zone, {})
        total = len(fish_list)
        found = sum(1 for f in fish_list if f['name'] in zone_data)
        percent = round((found / total) * 100, 0) if total else 0
        print(f"→ You have discovered {found}/{total} fish ({percent}%)")
        print()
        for f in fish_list:
            if f['name'] in zone_data:
                entry = zone_data[f['name']]
                color = self.get_rarity_color(f['rarity'])
                value = round(entry['maxValue'], 2)
                print(color_text(
                    f"{f['name']} [{f['rarity']}] - Times: {entry['count']} - Heaviest: {entry['maxWeight']} kg - Max Value: {value}$",
                    color))
            else:
                print("??? [--] - Times: -- - Heaviest: -- kg - Max Value: --")
        input("Press Enter to return to menu")

    # -------------- Shop --------------
    def show_shop(self):
        clear_screen()
        print("Shop - Buy Items:")
        for idx, item in enumerate(SHOP_ITEMS, 1):
            print(f"{idx}. {item['name']} - Price: {item['price']}$")
            print(f"    {item['description']}")
        choice = input("Enter item number to buy, or '0' to return: ")
        if choice == '0':
            return
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(SHOP_ITEMS):
            print("Invalid choice.")
            time.sleep(2)
            return
        selected = SHOP_ITEMS[int(choice) - 1]
        if self.balance < selected['price']:
            print("Not enough money to buy this item.")
            time.sleep(2)
            return
        if selected['name'] == 'Submarine Upgrade 02' and not self.has_ancient_key:
            print("You need the Ancient Key to buy this upgrade.")
            time.sleep(2)
            return
        if selected['name'] == 'Submarine Upgrade 02' and not self.has_abyss_trench_access:
            print("You need Submarine Upgrade 01 first.")
            time.sleep(2)
            return
        self.balance -= selected['price']
        name = selected['name']
        if name == 'Submarine':
            self.has_submarine = True
            print("Congratulations! You bought a Submarine and can now access Bathyal zone.")
        elif name == 'Boat':
            self.has_boat = True
            print("Congratulations! You bought a Boat and can now access Sea zone.")
        elif name == 'Torch':
            self.has_torch = True
            print("Congratulations! You bought a Torch and can now access Mystic Spring.")
        elif name == 'Submarine Upgrade 01':
            self.has_abyss_trench_access = True
            print("Congratulations! You bought Submarine Upgrade 01 and can now access Abyss Trench.")
        elif name == 'Submarine Upgrade 02':
            self.has_ancient_sea_access = True
            print("Congratulations! You bought Submarine Upgrade 02 and can now access Ancient Sea.")
        else:
            print(f"You bought {name}.")
        self.save_game()
        time.sleep(2)

    # -------------- Main loop --------------
    def run(self):
        while True:
            self.show_menu()
            choice = input("Pick your choice (1/2/3/4/5/6/7): ")
            if choice == '1':
                self.start_fishing()
                self.advance_time()
            elif choice == '2':
                self.choose_zone()
            elif choice == '3':
                self.sell_fish()
            elif choice == '4':
                self.show_inventory()
            elif choice == '5':
                self.show_shop()
            elif choice == '6':
                self.show_discovery_book()
            elif choice == '7':
                self.show_quest_menu()
            elif choice == '8':
                break
            elif choice == 'admin':
                self.balance += 10000000
                print("🛠️ Admin mode activated! You received 10,000,000$")
                self.save_game()
                time.sleep(2)
            else:
                print("Invalid choice.")
                time.sleep(1)

# --------------------------- Main entry ---------------------------

def main():
    game = Game()
    game.run()

if __name__ == '__main__':
    main()

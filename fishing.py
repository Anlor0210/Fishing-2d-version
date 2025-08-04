# Python translation of the PowerShell Fishing Game
# Console-based fishing game with multiple zones, shop, and save/load system

import json
import math
import os
import random
import time
import sys
import select
import tty
import termios
from typing import Dict, List

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

# Non-blocking keyboard helpers
class RawInput:
    def __enter__(self):
        if os.name != 'nt':
            self.fd = sys.stdin.fileno()
            self.old_settings = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.name != 'nt':
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

def key_pressed():
    if os.name == 'nt':
        import msvcrt
        return msvcrt.kbhit()
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    return dr != []

def read_key():
    if os.name == 'nt':
        import msvcrt
        ch = msvcrt.getwch()
        return ch
    return sys.stdin.read(1)

# --------------------------- Fish data ---------------------------

FISH_LAKE = [
    {"name": "Carp", "rarity": "Common", "price": 1, "xp": 5},
    {"name": "Tilapia", "rarity": "Common", "price": 1.25, "xp": 5},
    {"name": "Grass carp", "rarity": "Uncommon", "price": 5, "xp": 7},
    {"name": "Catfish", "rarity": "Rare", "price": 10, "xp": 10},
    {"name": "Snakehead fish", "rarity": "Legendary", "price": 50, "xp": 50},
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
]

FISH_BATHYAL = [
    {"name": "Deep-sea dragonfish", "rarity": "Rare", "base_price": 5, "xp": 10},
    {"name": "Lanternfish", "rarity": "Rare", "base_price": 10, "xp": 10},
    {"name": "Anglerfish", "rarity": "Uncommon", "base_price": 13, "xp": 7},
    {"name": "Black swallower", "rarity": "Legendary", "base_price": 15, "xp": 50},
    {"name": "Goblin shark", "rarity": "Legendary", "base_price": 20, "xp": 50},
]

FISH_ABYSS_TRENCH = [
    {"name": "Lanternfish", "rarity": "Common", "price": 15},
    {"name": "Angler Leviathan", "rarity": "Rare", "price": 25},
    {"name": "Giant Squid", "rarity": "Legendary", "price": 75},
    {"name": "Ancient Key", "rarity": "Legendary", "price": 25},
]

FISH_ANCIENT_SEA = [
    {"name": "Mosasaurus", "rarity": "Legendary", "price": 75},
    {"name": "Dunkleost", "rarity": "Legendary", "price": 75},
    {"name": "Megalodon", "rarity": "Legendary", "price": 100},
    {"name": "Leedsichthys", "rarity": "Exotic", "price": 250},
]

FISH_MYSTIC_SPRING = [
    {"name": "Prism Trout", "rarity": "Rare", "price": 15, "xp": 10},
    {"name": "Spirit Koi", "rarity": "Epic", "price": 25, "xp": 25},
    {"name": "Phoenix Scale Carp", "rarity": "Mythical", "price": 50, "xp": 40},
]

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
        self.current_hour = 0
        self.event = "Nothing"
        self.level = 0
        self.xp = 0
        self.discovery: Dict[str, Dict] = {}
        self.current_zone = "Lake"
        self.current_fish_list = FISH_LAKE
        self.current_zone_catch_length = 5
        self.current_fish = None
        # load existing data if any
        self.load_game()

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
            'currentHour': self.current_hour,
            'event': self.event,
            'level': self.level,
            'xp': self.xp,
            'discovery': self.discovery,
        }
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_game(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.balance = data.get('balance', 100)
            self.inventory = data.get('inventoryFish', [])
            self.has_submarine = data.get('hasSubmarine', False)
            self.has_boat = data.get('hasBoat', False)
            self.has_torch = data.get('hasTorch', False)
            self.has_abyss_trench_access = data.get('hasAbyssTrenchAccess', False)
            self.has_ancient_sea_access = data.get('hasAncientSeaAccess', False)
            self.has_ancient_key = data.get('hasAncientKey', False)
            self.current_hour = data.get('currentHour', 0)
            self.event = data.get('event', 'Nothing')
            self.level = data.get('level', 0)
            self.xp = data.get('xp', 0)
            self.discovery = data.get('discovery', {})
        else:
            # defaults already set
            pass

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

    # -------------- Fish generation --------------
    def get_fish_by_weighted_random(self, fish_list: List[Dict]) -> Dict:
        weighted = []
        for fish in fish_list:
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
        if name == "Deep-sea dragonfish":
            return random.randint(5, 20)
        if name == "Lanternfish":
            return random.randint(5, 15)
        if name == "Anglerfish":
            return random.randint(10, 25)
        if name == "Black swallower":
            return random.randint(2, 10)
        if name == "Goblin shark":
            return random.randint(50, 100)
        if name == "Angler Leviathan":
            return random.randint(15, 100)
        if name == "Giant Squid":
            return random.randint(1000, 5000)
        if name == "Ancient Key":
            return random.randint(100, 500)
        if name == "Mosasaurus" or name == "Dunkleost":
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

    # -------------- Time & Events --------------
    def advance_time(self):
        self.current_hour = (self.current_hour + 1) % 24
        if self.current_hour < 20:
            self.event = "Nothing"
        elif self.current_hour >= 20:
            if self.event == "Nothing":
                if random.randint(1, 100) <= 20:
                    self.event = "Full Moon"
                else:
                    self.event = "Nothing"

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
        print(f"Time: {self.current_hour}:00")
        print(f"Event: {self.event}")
        print("Version: Beta")
        print("1. Fishing")
        print("2. Zone")
        print("3. Sell fish")
        print("4. Inventory")
        print("5. Shop")
        print("6. Discovery Book")
        print("7. Exit game")

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
                    if ch in ('\n', '\r', ' '):
                        if target_start <= i <= target_end:
                            if random.randint(1, 100) <= 20:
                                print("\n>> Oh no! The fish run!")
                                return False
                            print("\n>> Success! You caught a fish!")
                            return True
                        else:
                            print("\n>> Missed! The fish got away...")
                            return False
            print("\n>> Time's up! The fish escaped!")
        return False

    def obtain_fish(self, full_moon_event=False):
        if full_moon_event:
            fish = random.choice(EXOTIC_FISH_FULL_MOON).copy()
            fish['weight'] = random.randint(1000, 100000)
            price = fish['price']
        else:
            fish = self.get_fish_by_weighted_random(self.current_fish_list).copy()
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
        }
        self.inventory.append(self.current_fish.copy())
        self.xp += self.get_xp_by_rarity(fish['rarity'])
        self.check_level_up()
        if fish['name'] == 'Ancient Key':
            self.has_ancient_key = True
            print(">> You obtained the Ancient Key!")
        color = 'Red' if fish['rarity'] == 'Exotic' else self.get_rarity_color(fish['rarity'])
        print("\n" + color_text(f">> You caught a {fish['name']} [{fish['rarity']}] - {weight} kg.", color))
        value = round(weight * fish['price'], 2)
        self.update_discovery(self.current_zone, fish['name'], weight, value)
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

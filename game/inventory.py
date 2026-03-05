from __future__ import annotations

from dataclasses import dataclass
import random


RARITY_COLORS = {
    "common": (170, 170, 170),
    "magic": (90, 150, 255),
    "rare": (245, 205, 75),
}

SLOT_LABELS = {
    "weapon": "Arma",
    "helmet": "Capacete",
    "cape": "Capa",
    "belt": "Cinto",
    "boots": "Botas",
}


@dataclass
class GearItem:
    item_id: int
    name: str
    slot: str
    width: int
    height: int
    rarity: str
    damage_bonus: int = 0
    hp_bonus: int = 0
    mana_bonus: int = 0
    speed_bonus: float = 0.0
    weapon_mode: str | None = None
    value: int = 10
    icon_path: str | None = None
    spell_key: str | None = None
    mana_cost: int = 0
    cooldown: float = 0.0

    @property
    def color(self) -> tuple[int, int, int]:
        return RARITY_COLORS.get(self.rarity, (170, 170, 170))


class Inventory:
    def __init__(self, cols: int = 10, rows: int = 6):
        self.cols = cols
        self.rows = rows
        self.items: dict[int, GearItem] = {}
        self.grid_positions: dict[int, tuple[int, int]] = {}
        self.equipped: dict[str, int | None] = {
            "weapon": None,
            "helmet": None,
            "cape": None,
            "belt": None,
            "boots": None,
        }

    def get_item(self, item_id: int) -> GearItem:
        return self.items[item_id]

    def add_item(self, item: GearItem) -> bool:
        self.items[item.item_id] = item
        pos = self.find_first_fit(item)
        if pos is None:
            del self.items[item.item_id]
            return False
        self.grid_positions[item.item_id] = pos
        return True

    def remove_item(self, item_id: int):
        self.grid_positions.pop(item_id, None)
        for slot, equipped_id in self.equipped.items():
            if equipped_id == item_id:
                self.equipped[slot] = None
        self.items.pop(item_id, None)

    def get_item_at_cell(self, cx: int, cy: int) -> int | None:
        for item_id, (x, y) in self.grid_positions.items():
            item = self.items[item_id]
            if x <= cx < x + item.width and y <= cy < y + item.height:
                return item_id
        return None

    def get_equipped_item(self, slot: str) -> int | None:
        return self.equipped.get(slot)

    def unequip_item(self, slot: str) -> bool:
        item_id = self.equipped.get(slot)
        if item_id is None:
            return True
        item = self.items[item_id]
        pos = self.find_first_fit(item)
        if pos is None:
            return False
        self.equipped[slot] = None
        self.grid_positions[item_id] = pos
        return True

    def pickup_item(self, item_id: int):
        self.grid_positions.pop(item_id, None)
        for slot, equipped_id in self.equipped.items():
            if equipped_id == item_id:
                self.equipped[slot] = None

    def place_in_grid(self, item_id: int, gx: int, gy: int) -> bool:
        item = self.items[item_id]
        if not self.can_place(item, gx, gy, ignore_item_id=item_id):
            return False
        self.grid_positions[item_id] = (gx, gy)
        return True

    def place_in_slot(self, item_id: int, slot: str) -> bool:
        item = self.items[item_id]
        if item.slot != slot:
            return False
        old_item = self.equipped.get(slot)
        if old_item is not None and old_item != item_id:
            old = self.items[old_item]
            pos = self.find_first_fit(old, ignore_item_id=old_item)
            if pos is None:
                return False
            self.grid_positions[old_item] = pos
        self.grid_positions.pop(item_id, None)
        self.equipped[slot] = item_id
        return True

    def find_first_fit(self, item: GearItem, ignore_item_id: int | None = None) -> tuple[int, int] | None:
        for y in range(self.rows - item.height + 1):
            for x in range(self.cols - item.width + 1):
                if self.can_place(item, x, y, ignore_item_id=ignore_item_id):
                    return x, y
        return None

    def can_place(self, item: GearItem, gx: int, gy: int, ignore_item_id: int | None = None) -> bool:
        if gx < 0 or gy < 0 or gx + item.width > self.cols or gy + item.height > self.rows:
            return False
        for other_id, (ox, oy) in self.grid_positions.items():
            if other_id == ignore_item_id:
                continue
            other = self.items[other_id]
            overlap_x = not (gx + item.width <= ox or ox + other.width <= gx)
            overlap_y = not (gy + item.height <= oy or oy + other.height <= gy)
            if overlap_x and overlap_y:
                return False
        return True


def roll_rarity() -> str:
    value = random.random()
    if value < 0.65:
        return "common"
    if value < 0.92:
        return "magic"
    return "rare"


def create_random_gear(item_id: int) -> GearItem:
    slot = random.choice(["weapon", "helmet", "cape", "belt", "boots"])
    rarity = roll_rarity()
    mult = 1.0 if rarity == "common" else 1.35 if rarity == "magic" else 1.8

    if slot == "weapon":
        weapon_roll = random.random()
        if weapon_roll < 0.45:
            sword_skins = [
                "normal_sword",
                "fire_sword",
                "lighting_sword",
                "poison_sword",
                "power_sword",
                "bleeding_sword",
                "wind_sword",
                "two_sword",
            ]
            skin = random.choice(sword_skins)
            damage_bonus = int(random.randint(4, 9) * mult)
            return GearItem(
                item_id=item_id,
                name=f"Espada {skin.split('_')[0].title()} {rarity.title()}",
                slot="weapon",
                width=2,
                height=3,
                rarity=rarity,
                damage_bonus=damage_bonus,
                weapon_mode="sword",
                icon_path=f"assets/weapons/{skin}.png",
                value=46 + damage_bonus * 6,
            )
        if weapon_roll < 0.72:
            damage_bonus = int(random.randint(3, 7) * mult)
            mana_bonus = int(random.randint(4, 10) * mult)
            return GearItem(
                item_id=item_id,
                name=f"Arco {rarity.title()}",
                slot="weapon",
                width=2,
                height=3,
                rarity=rarity,
                damage_bonus=damage_bonus,
                mana_bonus=mana_bonus,
                weapon_mode="bow",
                icon_path="assets/Soldier/Arrow(projectile)/Arrow01(32x32).png",
                value=40 + damage_bonus * 5 + mana_bonus * 2,
            )

        spell_defs = [
            ("lighting_spell", "Raio", 14, 0.55),
            ("meteor_spell", "Meteoro", 22, 0.9),
            ("twister_spell", "Twister", 16, 0.6),
            ("field_spell", "Campo", 26, 1.15),
        ]
        spell_key, spell_name, mana_cost, cooldown = random.choice(spell_defs)
        damage_bonus = int(random.randint(2, 6) * mult)
        return GearItem(
            item_id=item_id,
            name=f"Spell {spell_name} {rarity.title()}",
            slot="weapon",
            width=2,
            height=3,
            rarity=rarity,
            damage_bonus=damage_bonus,
            mana_bonus=int(random.randint(8, 16) * mult),
            weapon_mode="spell",
            spell_key=spell_key,
            mana_cost=mana_cost,
            cooldown=cooldown,
            icon_path=f"assets/spells/{spell_key}.png",
            value=55 + damage_bonus * 6 + int(mana_cost * 1.8),
        )

    if slot == "helmet":
        hp_bonus = int(random.randint(8, 18) * mult)
        return GearItem(
            item_id=item_id,
            name=f"Capacete {rarity.title()}",
            slot="helmet",
            width=2,
            height=2,
            rarity=rarity,
            hp_bonus=hp_bonus,
            value=30 + hp_bonus * 3,
        )

    if slot == "cape":
        mana_bonus = int(random.randint(10, 20) * mult)
        return GearItem(
            item_id=item_id,
            name=f"Capa {rarity.title()}",
            slot="cape",
            width=2,
            height=2,
            rarity=rarity,
            mana_bonus=mana_bonus,
            value=30 + mana_bonus * 2,
        )

    if slot == "belt":
        hp_bonus = int(random.randint(5, 12) * mult)
        mana_bonus = int(random.randint(5, 12) * mult)
        return GearItem(
            item_id=item_id,
            name=f"Cinto {rarity.title()}",
            slot="belt",
            width=2,
            height=1,
            rarity=rarity,
            hp_bonus=hp_bonus,
            mana_bonus=mana_bonus,
            value=26 + hp_bonus * 2 + mana_bonus * 2,
        )

    speed_bonus = random.randint(8, 18) * mult
    return GearItem(
        item_id=item_id,
        name=f"Botas {rarity.title()}",
        slot="boots",
        width=2,
        height=2,
        rarity=rarity,
        speed_bonus=speed_bonus,
        value=30 + int(speed_bonus * 3),
    )

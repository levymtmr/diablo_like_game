import random
from dataclasses import dataclass

import pygame


@dataclass
class Entity:
    x: float
    y: float
    radius: float


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    damage: int
    ttl: float
    angle: float
    kind: str = "arrow"
    sprite_path: str | None = None
    pierce: int = 0
    aoe_radius: float = 0.0
    alive: bool = True


@dataclass
class GroundItem:
    x: float
    y: float
    kind: str
    amount: int
    radius: float = 12.0
    alive: bool = True
    payload: object | None = None


class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, radius=18)
        self.class_name = "warrior"
        self.base_speed = 280.0
        self.speed = self.base_speed
        self.base_max_hp = 100
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.base_max_mana = 100
        self.max_mana = self.base_max_mana
        self.mana = self.max_mana
        self.base_damage = 24
        self.current_damage = self.base_damage
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.level_up_flash_timer = 0.0
        self.gold = 0
        self.health_flasks = 1
        self.mana_flasks = 1
        self.weapon_mode = "sword"
        self.attack_cooldown = 0.0
        self.attack_timer = 0.0
        self.hurt_timer = 0.0
        self.death_timer = 0.0
        self.facing = pygame.Vector2(1, 0)
        self.facing_left = False
        self.attack_variant = "attack1"
        self.state = "idle"
        self.alive = True
        self.animator = None

    def add_xp(self, amount: int):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.3)
            self.base_max_hp += 18
            self.max_hp += 18
            self.hp = self.max_hp
            self.base_max_mana += 12
            self.max_mana += 12
            self.mana = self.max_mana
            self.base_damage += 4
            self.level_up_flash_timer = 1.2

    def use_health_flask(self) -> bool:
        if self.health_flasks <= 0 or self.hp >= self.max_hp:
            return False
        self.health_flasks -= 1
        self.hp = min(self.max_hp, self.hp + 55)
        return True

    def use_mana_flask(self) -> bool:
        if self.mana_flasks <= 0 or self.mana >= self.max_mana:
            return False
        self.mana_flasks -= 1
        self.mana = min(self.max_mana, self.mana + 50)
        return True


class Enemy(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, radius=15)
        self.speed = random.uniform(90.0, 130.0)
        self.hp = 45
        self.xp_reward = random.randint(20, 35)
        self.touch_damage = 12
        self.hurt_timer = 0.0
        self.attack_timer = 0.0
        self.attack_cooldown = random.uniform(0.1, 0.6)
        self.attack_variant = "attack1"
        self.state = "idle"
        self.facing_left = False
        self.alive = True
        self.pending_removal = False
        self.animator = None

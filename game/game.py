import random
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame

from game.animation import AnimationClip, Animator, load_strip
from game.combat_mixin import CombatMixin
from game.entities import GroundItem, Player, Projectile
from game.inventory import GearItem, Inventory, create_random_gear
from game.inventory_shop_mixin import InventoryShopMixin
from game.render_mixin import RenderMixin
from game.settings import (
    ENEMY_SPRITE_SIZE,
    PLAYER_SPRITE_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPRITE_FRAME_SIZE,
    TILE_SIZE,
)
from game.world import WorldMap


@dataclass
class SpellEffect:
    x: float
    y: float
    frames: list[pygame.Surface]
    fps: float
    elapsed: float = 0.0
    alive: bool = True


class Game(CombatMixin, InventoryShopMixin, RenderMixin):
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Python + pygame | ARPG 2D Prototype")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.font_small = pygame.font.SysFont("consolas", 18)
        self.font_big = pygame.font.SysFont("consolas", 30, bold=True)
        self.font_tiny = pygame.font.SysFont("consolas", 14)

        self.player_clips = self.build_player_clips()
        self.enemy_clips = self.build_enemy_clips()

        self.world = WorldMap()
        self.player = Player(self.world.width_px // 2, self.world.height_px // 2)
        self.player.animator = Animator(self.player_clips, initial_state="idle")

        self.enemies = []
        self.wave_phase = "prep"
        self.current_wave = 0
        self.pending_wave = 1
        self.projectiles: list[Projectile] = []
        self.ground_items: list[GroundItem] = []
        self.spell_effects: list[SpellEffect] = []

        self.arrow_sprite = pygame.image.load("assets/Soldier/Arrow(projectile)/Arrow01(32x32).png").convert_alpha()
        self.arrow_sprite = pygame.transform.smoothscale(self.arrow_sprite, (36, 36))
        self.coin_frames = [
            pygame.transform.smoothscale(pygame.image.load(f"assets/coin/coin_{idx}.png").convert_alpha(), (24, 24))
            for idx in range(1, 5)
        ]
        self.flask_hp_sprite = pygame.transform.smoothscale(
            pygame.image.load("assets/flasks/flasks_4_1.png").convert_alpha(), (30, 30)
        )
        self.flask_mana_sprite = pygame.transform.smoothscale(
            pygame.image.load("assets/flasks/flasks_3_1.png").convert_alpha(), (30, 30)
        )
        self.coin_anim_time = 0.0

        self.spell_cast_frames = self.load_spell_animation_sheet("assets/animation_spells/00.png", frame_size=64, scale=74)
        self.spell_impact_frames = self.load_spell_animation_sheet("assets/animation_spells/01.png", frame_size=64, scale=100)
        self.load_terrain_assets()

        self.inventory = Inventory(cols=10, rows=6)
        self.next_item_id = 1
        self.drag_item_id: int | None = None
        self.drag_origin: tuple[str, tuple[int, int] | str] | None = None
        self.class_selected = False
        self.refresh_player_from_equipment()

        self.item_icon_cache: dict[tuple[str, int], pygame.Surface] = {}
        self.spell_sprite_cache: dict[str, pygame.Surface] = {}

        self.show_overlay_map = False
        self.show_inventory = False
        self.show_shop = False
        self.show_exit_dialog = False

        self.shop_items: list[GearItem] = []
        self.shop_item_rects: dict[int, pygame.Rect] = {}
        self.explored_tiles: set[tuple[int, int]] = set()
        self.map_explore_radius = 4
        self.mark_explored_around_player()
        self.roll_shop_stock()

    def load_terrain_assets(self):
        def load_scaled(path: str) -> pygame.Surface:
            sprite = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))

        base_dir = Path("assets/dark_fantasy_terrain_pack")
        ground_dir = base_dir / "ground_32"
        props_dir = base_dir / "props_32"

        floor_patterns = ("grass_*.png", "dirt_*.png", "stone_*.png", "swamp_*.png")
        base_patterns = ("cobble_*.png", "stone_*.png")

        self.floor_tiles: list[pygame.Surface] = []
        for pattern in floor_patterns:
            for path in sorted(ground_dir.glob(pattern)):
                self.floor_tiles.append(load_scaled(str(path)))

        self.base_floor_tiles: list[pygame.Surface] = []
        for pattern in base_patterns:
            for path in sorted(ground_dir.glob(pattern)):
                self.base_floor_tiles.append(load_scaled(str(path)))

        obstacle_names = [
            "rock_01.png",
            "rock_02.png",
            "rock_03.png",
            "dead_tree_01.png",
            "dead_tree_02.png",
            "crate_01.png",
            "crate_02.png",
            "barrel_01.png",
            "barrel_02.png",
        ]
        self.blocked_tiles_sprites: list[pygame.Surface] = []
        for name in obstacle_names:
            path = props_dir / name
            if path.exists():
                self.blocked_tiles_sprites.append(load_scaled(str(path)))

    def alloc_item_id(self) -> int:
        item_id = self.next_item_id
        self.next_item_id += 1
        return item_id

    def create_default_loadout(self, class_name: str):
        self.inventory = Inventory(cols=10, rows=6)

        if class_name == "warrior":
            self.player.class_name = "warrior"
            self.player.base_max_hp = 135
            self.player.base_max_mana = 80
            self.player.base_damage = 28
            self.player.base_speed = 275
            weapon = GearItem(
                item_id=self.alloc_item_id(),
                name="Espada Normal",
                slot="weapon",
                width=2,
                height=3,
                rarity="common",
                damage_bonus=6,
                weapon_mode="sword",
                icon_path="assets/weapons/normal_sword.png",
                value=0,
            )
        elif class_name == "mage":
            self.player.class_name = "mage"
            self.player.base_max_hp = 95
            self.player.base_max_mana = 165
            self.player.base_damage = 20
            self.player.base_speed = 270
            weapon = GearItem(
                item_id=self.alloc_item_id(),
                name="Spell Raio",
                slot="weapon",
                width=2,
                height=3,
                rarity="common",
                damage_bonus=5,
                weapon_mode="spell",
                spell_key="lighting_spell",
                mana_cost=14,
                cooldown=0.55,
                icon_path="assets/spells/lighting_spell.png",
                value=0,
            )
        else:
            self.player.class_name = "archer"
            self.player.base_max_hp = 110
            self.player.base_max_mana = 120
            self.player.base_damage = 24
            self.player.base_speed = 300
            weapon = GearItem(
                item_id=self.alloc_item_id(),
                name="Arco Inicial",
                slot="weapon",
                width=2,
                height=3,
                rarity="common",
                damage_bonus=4,
                mana_bonus=8,
                weapon_mode="bow",
                icon_path="assets/Soldier/Arrow(projectile)/Arrow01(32x32).png",
                value=0,
            )

        self.player.max_hp = self.player.base_max_hp
        self.player.max_mana = self.player.base_max_mana
        self.player.hp = self.player.max_hp
        self.player.mana = self.player.max_mana
        self.player.speed = self.player.base_speed
        self.player.current_damage = self.player.base_damage

        self.inventory.add_item(weapon)
        self.inventory.place_in_slot(weapon.item_id, "weapon")
        self.refresh_player_from_equipment()

    def get_item_icon(self, path: str, size: int = 32) -> pygame.Surface:
        key = (path, size)
        if key in self.item_icon_cache:
            return self.item_icon_cache[key]
        icon = pygame.image.load(path).convert_alpha()
        icon = pygame.transform.smoothscale(icon, (size, size))
        self.item_icon_cache[key] = icon
        return icon

    def get_spell_sprite(self, path: str) -> pygame.Surface:
        if path in self.spell_sprite_cache:
            return self.spell_sprite_cache[path]
        sprite = pygame.image.load(path).convert_alpha()
        sprite = pygame.transform.smoothscale(sprite, (42, 42))
        self.spell_sprite_cache[path] = sprite
        return sprite

    def load_spell_animation_sheet(self, path: str, frame_size: int, scale: int) -> list[pygame.Surface]:
        sheet = pygame.image.load(path).convert_alpha()
        cols = sheet.get_width() // frame_size
        rows = sheet.get_height() // frame_size
        frames = []
        for row in range(rows):
            for col in range(cols):
                src = pygame.Rect(col * frame_size, row * frame_size, frame_size, frame_size)
                frame = sheet.subsurface(src).copy()
                if frame.get_bounding_rect().width == 0:
                    continue
                if scale != frame_size:
                    frame = pygame.transform.smoothscale(frame, (scale, scale))
                frames.append(frame)
        return frames

    def spawn_spell_effect(self, x: float, y: float, effect_kind: str):
        if effect_kind == "cast":
            frames, fps = self.spell_cast_frames, 24.0
        elif effect_kind == "impact_big":
            frames, fps = self.spell_impact_frames, 20.0
        else:
            frames, fps = self.spell_impact_frames, 24.0
        if frames:
            self.spell_effects.append(SpellEffect(x=x, y=y, frames=frames, fps=fps))

    def refresh_player_from_equipment(self):
        hp_bonus = mana_bonus = damage_bonus = 0
        speed_bonus = 0.0
        weapon_mode = "sword"
        for slot, item_id in self.inventory.equipped.items():
            if item_id is None:
                continue
            item = self.inventory.get_item(item_id)
            hp_bonus += item.hp_bonus
            mana_bonus += item.mana_bonus
            speed_bonus += item.speed_bonus
            damage_bonus += item.damage_bonus
            if slot == "weapon" and item.weapon_mode is not None:
                weapon_mode = item.weapon_mode
        self.player.max_hp = self.player.base_max_hp + hp_bonus
        self.player.max_mana = self.player.base_max_mana + mana_bonus
        self.player.speed = self.player.base_speed + speed_bonus
        self.player.mana = min(self.player.mana, self.player.max_mana)
        self.player.hp = min(self.player.hp, self.player.max_hp)
        self.player.weapon_mode = weapon_mode
        self.player.current_damage = self.player.base_damage + damage_bonus

    def get_base_spawn_point(self) -> tuple[float, float]:
        cx, cy = self.world.base_center
        return cx * TILE_SIZE + TILE_SIZE / 2, cy * TILE_SIZE + TILE_SIZE / 2

    def roll_shop_stock(self):
        self.shop_items = [create_random_gear(self.alloc_item_id()) for _ in range(6)]
        self.shop_item_rects = {}

    def build_player_clips(self) -> dict[str, AnimationClip]:
        return {
            "idle": AnimationClip(load_strip("assets/Soldier/Soldier/Soldier-Idle.png", SPRITE_FRAME_SIZE, PLAYER_SPRITE_SIZE), 0.12, True),
            "walk": AnimationClip(load_strip("assets/Soldier/Soldier/Soldier-Walk.png", SPRITE_FRAME_SIZE, PLAYER_SPRITE_SIZE), 0.08, True),
            "attack1": AnimationClip(load_strip("assets/Soldier/Soldier/Soldier-Attack01.png", SPRITE_FRAME_SIZE, PLAYER_SPRITE_SIZE), 0.07, False),
            "attack2": AnimationClip(load_strip("assets/Soldier/Soldier/Soldier-Attack02.png", SPRITE_FRAME_SIZE, PLAYER_SPRITE_SIZE), 0.07, False),
            "attack3": AnimationClip(load_strip("assets/Soldier/Soldier/Soldier-Attack03.png", SPRITE_FRAME_SIZE, PLAYER_SPRITE_SIZE), 0.07, False),
            "hurt": AnimationClip(load_strip("assets/Soldier/Soldier/Soldier-Hurt.png", SPRITE_FRAME_SIZE, PLAYER_SPRITE_SIZE), 0.08, False),
            "death": AnimationClip(load_strip("assets/Soldier/Soldier/Soldier-Death.png", SPRITE_FRAME_SIZE, PLAYER_SPRITE_SIZE), 0.12, False),
        }

    def build_enemy_clips(self) -> dict[str, AnimationClip]:
        return {
            "idle": AnimationClip(load_strip("assets/Orc/Orc/Orc-Idle.png", SPRITE_FRAME_SIZE, ENEMY_SPRITE_SIZE), 0.12, True),
            "walk": AnimationClip(load_strip("assets/Orc/Orc/Orc-Walk.png", SPRITE_FRAME_SIZE, ENEMY_SPRITE_SIZE), 0.08, True),
            "attack1": AnimationClip(load_strip("assets/Orc/Orc/Orc-Attack01.png", SPRITE_FRAME_SIZE, ENEMY_SPRITE_SIZE), 0.08, False),
            "attack2": AnimationClip(load_strip("assets/Orc/Orc/Orc-Attack02.png", SPRITE_FRAME_SIZE, ENEMY_SPRITE_SIZE), 0.08, False),
            "hurt": AnimationClip(load_strip("assets/Orc/Orc/Orc-Hurt.png", SPRITE_FRAME_SIZE, ENEMY_SPRITE_SIZE), 0.08, False),
            "death": AnimationClip(load_strip("assets/Orc/Orc/Orc-Death.png", SPRITE_FRAME_SIZE, ENEMY_SPRITE_SIZE), 0.12, False),
        }

    def make_enemy_animator(self):
        return Animator(self.enemy_clips, initial_state="idle")

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if self.show_exit_dialog:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_y, pygame.K_RETURN):
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_n, pygame.K_ESCAPE):
                    self.show_exit_dialog = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    yes_rect, no_rect = self.get_exit_dialog_buttons()
                    if yes_rect.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit(0)
                    if no_rect.collidepoint(event.pos):
                        self.show_exit_dialog = False
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.show_exit_dialog = True

            if not self.class_selected:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_1:
                    self.create_default_loadout("warrior")
                    self.class_selected = True
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_2:
                    self.create_default_loadout("mage")
                    self.class_selected = True
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_3:
                    self.create_default_loadout("archer")
                    self.class_selected = True
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                self.show_overlay_map = not self.show_overlay_map
            if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                if self.show_inventory and self.drag_item_id is not None:
                    self.cancel_drag_to_origin()
                self.show_inventory = not self.show_inventory
            if event.type == pygame.KEYDOWN and event.key == pygame.K_b:
                if self.wave_phase == "prep" and self.world.is_in_base_world(self.player.x, self.player.y):
                    self.show_shop = not self.show_shop
            if event.type == pygame.KEYDOWN and event.key == pygame.K_1:
                self.player.use_health_flask()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_2:
                self.player.use_mana_flask()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.show_shop and self.handle_shop_buy_click(event.pos):
                    continue
                if self.show_inventory:
                    self.handle_inventory_click(event.pos)
                else:
                    self.try_attack()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if self.show_shop and self.show_inventory:
                    self.handle_inventory_sell_click(event.pos)

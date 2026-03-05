import math
import random
import sys

import pygame

from game.entities import Enemy, GroundItem, Projectile
from game.inventory import GearItem, create_random_gear
from game.settings import ENEMY_COUNT, MAP_HEIGHT, MAP_WIDTH, TILE_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH


class CombatMixin:
    def spawn_enemies(self, count: int) -> list[Enemy]:
        enemies = []
        while len(enemies) < count:
            tx = random.randint(2, MAP_WIDTH - 3)
            ty = random.randint(2, MAP_HEIGHT - 3)
            if (tx, ty) in self.world.blocked_tiles or (tx, ty) in self.world.base_tiles:
                continue
            px = tx * TILE_SIZE + TILE_SIZE / 2
            py = ty * TILE_SIZE + TILE_SIZE / 2
            if math.dist((px, py), (self.player.x, self.player.y)) < 300:
                continue
            enemy = Enemy(px, py)
            enemy.animator = self.make_enemy_animator()
            enemies.append(enemy)
        return enemies

    def start_wave(self):
        if self.wave_phase != "prep":
            return
        count = ENEMY_COUNT + (self.pending_wave - 1) * 6
        self.enemies = self.spawn_enemies(count)
        self.current_wave = self.pending_wave
        self.pending_wave += 1
        self.wave_phase = "combat"
        self.show_shop = False

    def finish_wave(self):
        self.wave_phase = "prep"
        self.enemies = []
        self.projectiles.clear()
        self.ground_items.clear()
        self.player.x, self.player.y = self.get_base_spawn_point()
        self.player.hp = self.player.max_hp
        self.player.mana = self.player.max_mana
        self.roll_shop_stock()

    def try_attack(self):
        if not self.player.alive or self.player.attack_cooldown > 0:
            return
        if self.player.weapon_mode == "spell":
            self.perform_spell_attack()
        elif self.player.weapon_mode == "bow":
            self.perform_bow_attack()
        else:
            self.perform_sword_attack()

    def perform_sword_attack(self):
        self.player.attack_cooldown = 0.35
        self.player.attack_timer = 0.45
        self.player.attack_variant = random.choice(("attack1", "attack2"))
        attack_range = 72
        max_angle = 70
        damage = self.player.current_damage
        facing = self.player.facing.normalize() if self.player.facing.length_squared() > 0 else pygame.Vector2(1, 0)

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            to_enemy = pygame.Vector2(enemy.x - self.player.x, enemy.y - self.player.y)
            dist = to_enemy.length()
            if dist > attack_range + enemy.radius:
                continue
            if dist > 0 and abs(facing.angle_to(to_enemy)) > max_angle:
                continue
            enemy.hp -= damage
            enemy.hurt_timer = 0.22
            if enemy.hp <= 0:
                self.kill_enemy(enemy)

    def perform_bow_attack(self):
        mana_cost = 12
        if self.player.mana < mana_cost:
            return
        self.player.mana -= mana_cost
        self.player.attack_cooldown = 0.48
        self.player.attack_timer = 0.38
        self.player.attack_variant = "attack3"
        self.spawn_arrow()

    def spawn_arrow(self):
        direction = self.player.facing.normalize() if self.player.facing.length_squared() > 0 else pygame.Vector2(1, 0)
        speed = 620.0
        damage = max(1, int(self.player.current_damage * 0.85))
        self.projectiles.append(
            Projectile(
                self.player.x + direction.x * 26,
                self.player.y + direction.y * 26,
                direction.x * speed,
                direction.y * speed,
                7,
                damage,
                1.25,
                -math.degrees(math.atan2(direction.y, direction.x)),
                kind="arrow",
                sprite_path="assets/Soldier/Arrow(projectile)/Arrow01(32x32).png",
            )
        )

    def perform_spell_attack(self):
        weapon_id = self.inventory.get_equipped_item("weapon")
        if weapon_id is None:
            return
        weapon = self.inventory.get_item(weapon_id)
        mana_cost = weapon.mana_cost if weapon.mana_cost > 0 else 14
        cooldown = weapon.cooldown if weapon.cooldown > 0 else 0.6
        if self.player.mana < mana_cost:
            return
        self.player.mana -= mana_cost
        self.player.attack_cooldown = cooldown
        self.player.attack_timer = 0.45
        self.player.attack_variant = "attack3"
        self.spawn_spell_effect(self.player.x, self.player.y, "cast")

        spell_key = weapon.spell_key or "lighting_spell"
        if spell_key == "field_spell":
            self.cast_field_spell()
            return
        if spell_key == "meteor_spell":
            self.spawn_spell_projectile(spell_key, speed=360.0, damage_mult=1.45, ttl=1.8, aoe_radius=95.0)
        elif spell_key == "twister_spell":
            self.spawn_spell_projectile(spell_key, speed=500.0, damage_mult=1.0, ttl=1.4, pierce=2)
        else:
            self.spawn_spell_projectile(spell_key, speed=760.0, damage_mult=1.1, ttl=1.1)

    def spawn_spell_projectile(self, spell_key: str, speed: float, damage_mult: float, ttl: float, pierce: int = 0, aoe_radius: float = 0.0):
        direction = self.player.facing.normalize() if self.player.facing.length_squared() > 0 else pygame.Vector2(1, 0)
        damage = max(1, int(self.player.current_damage * damage_mult))
        self.projectiles.append(
            Projectile(
                self.player.x + direction.x * 24,
                self.player.y + direction.y * 24,
                direction.x * speed,
                direction.y * speed,
                10,
                damage,
                ttl,
                -math.degrees(math.atan2(direction.y, direction.x)),
                kind=f"spell_{spell_key}",
                sprite_path=f"assets/spells/{spell_key}.png",
                pierce=pierce,
                aoe_radius=aoe_radius,
            )
        )

    def cast_field_spell(self):
        radius = 130
        damage = int(self.player.current_damage * 1.2)
        self.spawn_spell_effect(self.player.x, self.player.y, "impact_big")
        for enemy in self.enemies:
            if enemy.alive and math.dist((enemy.x, enemy.y), (self.player.x, self.player.y)) <= radius:
                enemy.hp -= damage
                enemy.hurt_timer = 0.25
                if enemy.hp <= 0:
                    self.kill_enemy(enemy)

    def kill_enemy(self, enemy: Enemy):
        if not enemy.alive:
            return
        enemy.alive = False
        enemy.state = "death"
        enemy.animator.set_state("death", restart=True)
        self.player.add_xp(enemy.xp_reward)
        self.drop_loot(enemy.x, enemy.y)

    def drop_loot(self, x: float, y: float):
        self.ground_items.append(GroundItem(x + random.uniform(-10, 10), y + random.uniform(-10, 10), "gold", random.randint(8, 20)))
        if random.random() < 0.3:
            self.ground_items.append(GroundItem(x + random.uniform(-12, 12), y + random.uniform(-12, 12), "hp_flask", 1))
        if random.random() < 0.22:
            self.ground_items.append(GroundItem(x + random.uniform(-12, 12), y + random.uniform(-12, 12), "mana_flask", 1))
        if random.random() < 0.45:
            self.ground_items.append(
                GroundItem(x + random.uniform(-16, 16), y + random.uniform(-16, 16), "gear", 1, payload=create_random_gear(self.alloc_item_id()))
            )

    def kill_player(self):
        if not self.player.alive:
            return
        self.player.alive = False
        self.player.state = "death"
        self.player.death_timer = 1.2
        self.player.animator.set_state("death", restart=True)

    def set_entity_state(self, entity, state: str):
        if entity.state != state:
            entity.state = state
            entity.animator.set_state(state, restart=True)
        else:
            entity.animator.set_state(state, restart=False)

    def update(self, dt: float):
        if not self.class_selected:
            return

        self.player.attack_cooldown = max(0.0, self.player.attack_cooldown - dt)
        self.player.attack_timer = max(0.0, self.player.attack_timer - dt)
        self.player.hurt_timer = max(0.0, self.player.hurt_timer - dt)
        self.player.level_up_flash_timer = max(0.0, self.player.level_up_flash_timer - dt)
        self.coin_anim_time += dt
        if self.player.alive:
            self.player.mana = min(self.player.max_mana, self.player.mana + 10.0 * dt)

        if self.show_shop and (self.wave_phase != "prep" or not self.world.is_in_base_world(self.player.x, self.player.y)):
            self.show_shop = False

        self.refresh_player_from_equipment()
        self.update_player(dt)
        if self.wave_phase == "prep" and not self.world.is_in_base_world(self.player.x, self.player.y):
            self.start_wave()
        self.update_enemies(dt)
        self.update_projectiles(dt)
        self.update_spell_effects(dt)
        self.update_ground_items()
        self.mark_explored_around_player()

        if not self.player.alive:
            self.player.death_timer = max(0.0, self.player.death_timer - dt)
            if self.player.death_timer <= 0 and self.player.animator.finished:
                pygame.quit()
                sys.exit("Game Over")

        self.enemies = [enemy for enemy in self.enemies if not enemy.pending_removal]
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]
        self.spell_effects = [effect for effect in self.spell_effects if effect.alive]
        self.ground_items = [item for item in self.ground_items if item.alive]
        if self.wave_phase == "combat" and not any(enemy.alive for enemy in self.enemies):
            self.finish_wave()

    def update_player(self, dt: float):
        moving = False
        if self.player.alive:
            keys = pygame.key.get_pressed()
            axis_x = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            axis_y = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            velocity = pygame.Vector2(axis_x, axis_y)
            if velocity.length_squared() > 0:
                moving = True
                velocity = velocity.normalize() * self.player.speed
            self.move_entity_with_collision(self.player, velocity.x * dt, velocity.y * dt)

            mouse = pygame.Vector2(pygame.mouse.get_pos())
            cam = self.get_camera_offset()
            look = mouse + pygame.Vector2(cam) - pygame.Vector2(self.player.x, self.player.y)
            if look.length_squared() > 0:
                self.player.facing = look.normalize()
                self.player.facing_left = self.player.facing.x < 0
            if self.player.hp <= 0:
                self.kill_player()

        if not self.player.alive:
            state = "death"
        elif self.player.hurt_timer > 0:
            state = "hurt"
        elif self.player.attack_timer > 0:
            state = self.player.attack_variant
        elif moving:
            state = "walk"
        else:
            state = "idle"

        self.set_entity_state(self.player, state)
        self.player.animator.update(dt)

    def update_enemies(self, dt: float):
        for enemy in self.enemies:
            enemy.hurt_timer = max(0.0, enemy.hurt_timer - dt)
            enemy.attack_timer = max(0.0, enemy.attack_timer - dt)
            enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - dt)

            if not enemy.alive:
                self.set_entity_state(enemy, "death")
                enemy.animator.update(dt)
                if enemy.animator.finished:
                    enemy.pending_removal = True
                continue

            to_player = pygame.Vector2(self.player.x - enemy.x, self.player.y - enemy.y)
            dist = to_player.length()
            enemy.facing_left = to_player.x < 0
            attack_range = enemy.radius + self.player.radius + 12
            moving = False

            if self.player.alive and dist <= attack_range and enemy.attack_cooldown <= 0:
                enemy.attack_cooldown = 0.85
                enemy.attack_timer = 0.35
                enemy.attack_variant = random.choice(("attack1", "attack2"))
                self.player.hp = max(0, self.player.hp - enemy.touch_damage)
                self.player.hurt_timer = 0.22
                if self.player.hp <= 0:
                    self.kill_player()
            elif self.player.alive and dist > attack_range and enemy.attack_timer <= 0 and enemy.hurt_timer <= 0:
                move = to_player.normalize() * enemy.speed * dt if dist > 0 else pygame.Vector2()
                self.move_entity_with_collision(enemy, move.x, move.y)
                moving = move.length_squared() > 0

            if enemy.hurt_timer > 0:
                state = "hurt"
            elif enemy.attack_timer > 0:
                state = enemy.attack_variant
            elif moving:
                state = "walk"
            else:
                state = "idle"

            self.set_entity_state(enemy, state)
            enemy.animator.update(dt)

    def update_projectiles(self, dt: float):
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            projectile.ttl -= dt
            if projectile.ttl <= 0:
                projectile.alive = False
                continue
            projectile.x += projectile.vx * dt
            projectile.y += projectile.vy * dt
            if self.world.collides(projectile.radius, projectile.x, projectile.y):
                if projectile.kind.startswith("spell_"):
                    self.spawn_spell_effect(projectile.x, projectile.y, "impact_big" if "meteor" in projectile.kind else "impact")
                projectile.alive = False
                continue
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if math.dist((projectile.x, projectile.y), (enemy.x, enemy.y)) <= projectile.radius + enemy.radius:
                    self.damage_enemy(enemy, projectile.damage)
                    if projectile.kind.startswith("spell_"):
                        self.spawn_spell_effect(enemy.x, enemy.y, "impact_big" if "meteor" in projectile.kind else "impact")
                    if projectile.aoe_radius > 0:
                        for splash in self.enemies:
                            if splash.alive and splash is not enemy and math.dist((splash.x, splash.y), (enemy.x, enemy.y)) <= projectile.aoe_radius:
                                self.damage_enemy(splash, int(projectile.damage * 0.7))
                    if projectile.pierce > 0:
                        projectile.pierce -= 1
                    else:
                        projectile.alive = False
                    break

    def damage_enemy(self, enemy: Enemy, amount: int):
        enemy.hp -= amount
        enemy.hurt_timer = 0.2
        if enemy.hp <= 0:
            self.kill_enemy(enemy)

    def update_spell_effects(self, dt: float):
        for effect in self.spell_effects:
            if not effect.alive:
                continue
            effect.elapsed += dt
            total = len(effect.frames) / effect.fps if effect.fps > 0 else 0.0
            if total > 0 and effect.elapsed >= total:
                effect.alive = False

    def update_ground_items(self):
        for item in self.ground_items:
            if not item.alive:
                continue
            if math.dist((item.x, item.y), (self.player.x, self.player.y)) > self.player.radius + 18:
                continue
            if item.kind == "gold":
                self.player.gold += item.amount
                item.alive = False
            elif item.kind == "hp_flask":
                self.player.health_flasks += item.amount
                item.alive = False
            elif item.kind == "mana_flask":
                self.player.mana_flasks += item.amount
                item.alive = False
            elif item.kind == "gear" and isinstance(item.payload, GearItem):
                if self.inventory.add_item(item.payload):
                    item.alive = False

    def move_entity_with_collision(self, entity, dx: float, dy: float):
        nx = entity.x + dx
        if not self.world.collides(entity.radius, nx, entity.y):
            entity.x = nx
        ny = entity.y + dy
        if not self.world.collides(entity.radius, entity.x, ny):
            entity.y = ny

    def get_camera_offset(self) -> tuple[float, float]:
        cam_x = self.player.x - SCREEN_WIDTH / 2
        cam_y = self.player.y - SCREEN_HEIGHT / 2
        cam_x = max(0, min(cam_x, self.world.width_px - SCREEN_WIDTH))
        cam_y = max(0, min(cam_y, self.world.height_px - SCREEN_HEIGHT))
        return cam_x, cam_y

    def mark_explored_around_player(self):
        center_tx = int(self.player.x // TILE_SIZE)
        center_ty = int(self.player.y // TILE_SIZE)
        for ty in range(center_ty - self.map_explore_radius, center_ty + self.map_explore_radius + 1):
            for tx in range(center_tx - self.map_explore_radius, center_tx + self.map_explore_radius + 1):
                if 0 <= tx < MAP_WIDTH and 0 <= ty < MAP_HEIGHT:
                    self.explored_tiles.add((tx, ty))


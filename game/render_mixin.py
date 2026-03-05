import math

import pygame

from game.inventory import GearItem, SLOT_LABELS
from game.settings import (
    BG_COLOR,
    FLOOR_COLOR_A,
    FLOOR_COLOR_B,
    MAP_HEIGHT,
    MAP_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
    UI_BG_COLOR,
    UI_HP_COLOR,
    UI_MANA_COLOR,
    UI_TEXT_COLOR,
    UI_XP_COLOR,
    WALL_COLOR,
)


class RenderMixin:
    def draw(self):
        self.screen.fill(BG_COLOR)
        cam_x, cam_y = self.get_camera_offset()
        self.draw_world(cam_x, cam_y)
        self.draw_ground_items(cam_x, cam_y)
        self.draw_entities(cam_x, cam_y)
        self.draw_projectiles(cam_x, cam_y)
        self.draw_spell_effects(cam_x, cam_y)
        if self.show_overlay_map:
            self.draw_overlay_map()
        self.draw_minimap()
        self.draw_ui()
        if self.show_shop:
            self.draw_shop_panel()
        if self.show_inventory:
            self.draw_inventory_panel()
        if not self.class_selected:
            self.draw_class_selection()
        if self.show_exit_dialog:
            self.draw_exit_dialog()
        pygame.display.flip()

    def get_exit_dialog_buttons(self) -> tuple[pygame.Rect, pygame.Rect]:
        panel = pygame.Rect((SCREEN_WIDTH - 420) // 2, (SCREEN_HEIGHT - 180) // 2, 420, 180)
        yes_rect = pygame.Rect(panel.x + 72, panel.bottom - 62, 120, 40)
        no_rect = pygame.Rect(panel.right - 192, panel.bottom - 62, 120, 40)
        return yes_rect, no_rect

    def draw_exit_dialog(self):
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 155))
        self.screen.blit(shade, (0, 0))
        panel = pygame.Rect((SCREEN_WIDTH - 420) // 2, (SCREEN_HEIGHT - 180) // 2, 420, 180)
        pygame.draw.rect(self.screen, (24, 26, 35), panel, border_radius=12)
        pygame.draw.rect(self.screen, (182, 188, 205), panel, 2, border_radius=12)
        self.screen.blit(self.font.render("Deseja finalizar o jogo?", True, UI_TEXT_COLOR), (panel.x + 30, panel.y + 34))
        self.screen.blit(self.font_small.render("Y/Enter = Sim   |   N/Esc = Nao", True, (190, 195, 210)), (panel.x + 56, panel.y + 78))
        yes_rect, no_rect = self.get_exit_dialog_buttons()
        pygame.draw.rect(self.screen, (142, 52, 52), yes_rect, border_radius=8)
        pygame.draw.rect(self.screen, (54, 94, 64), no_rect, border_radius=8)
        self.screen.blit(self.font_small.render("Sim", True, (245, 245, 245)), (yes_rect.x + 44, yes_rect.y + 10))
        self.screen.blit(self.font_small.render("Nao", True, (245, 245, 245)), (no_rect.x + 44, no_rect.y + 10))

    def draw_world(self, cam_x: float, cam_y: float):
        start_x = int(cam_x // TILE_SIZE)
        end_x = int((cam_x + SCREEN_WIDTH) // TILE_SIZE) + 1
        start_y = int(cam_y // TILE_SIZE)
        end_y = int((cam_y + SCREEN_HEIGHT) // TILE_SIZE) + 1
        for ty in range(start_y, min(end_y, MAP_HEIGHT)):
            for tx in range(start_x, min(end_x, MAP_WIDTH)):
                rect = pygame.Rect(tx * TILE_SIZE - cam_x, ty * TILE_SIZE - cam_y, TILE_SIZE, TILE_SIZE)
                tile_hash = abs((tx * 73856093) ^ (ty * 19349663))
                if (tx, ty) in self.world.base_tiles:
                    color = (62, 74, 92) if (tx + ty) % 2 == 0 else (56, 66, 84)
                else:
                    color = FLOOR_COLOR_A if (tx + ty) % 2 == 0 else FLOOR_COLOR_B
                pygame.draw.rect(self.screen, color, rect)

                if (tx, ty) in self.world.blocked_tiles:
                    if self.blocked_tiles_sprites:
                        obstacle = self.blocked_tiles_sprites[tile_hash % len(self.blocked_tiles_sprites)]
                        self.screen.blit(obstacle, rect)
                    else:
                        pygame.draw.rect(self.screen, WALL_COLOR, rect.inflate(-10, -10), border_radius=6)

    def draw_entities(self, cam_x: float, cam_y: float):
        drawable = [enemy for enemy in self.enemies if not enemy.pending_removal] + [self.player]
        drawable.sort(key=lambda ent: ent.y)
        for entity in drawable:
            frame = entity.animator.current_frame()
            if entity.facing_left:
                frame = pygame.transform.flip(frame, True, False)
            self.screen.blit(frame, frame.get_rect(center=(int(entity.x - cam_x), int(entity.y - cam_y))))

    def draw_projectiles(self, cam_x: float, cam_y: float):
        for projectile in self.projectiles:
            if projectile.alive:
                if projectile.kind.startswith("spell_") and projectile.sprite_path:
                    base = self.get_spell_sprite(projectile.sprite_path)
                elif projectile.sprite_path:
                    base = self.get_item_icon(projectile.sprite_path, 36)
                else:
                    base = self.arrow_sprite
                frame = pygame.transform.rotate(base, projectile.angle)
                self.screen.blit(frame, frame.get_rect(center=(int(projectile.x - cam_x), int(projectile.y - cam_y))))

    def draw_spell_effects(self, cam_x: float, cam_y: float):
        for effect in self.spell_effects:
            if effect.alive and effect.frames:
                idx = min(int(effect.elapsed * effect.fps), len(effect.frames) - 1)
                frame = effect.frames[idx]
                self.screen.blit(frame, frame.get_rect(center=(int(effect.x - cam_x), int(effect.y - cam_y))))

    def draw_ground_items(self, cam_x: float, cam_y: float):
        coin = self.coin_frames[int(self.coin_anim_time * 10) % len(self.coin_frames)]
        for item in self.ground_items:
            if not item.alive:
                continue
            pos = (int(item.x - cam_x), int(item.y - cam_y))
            if item.kind == "gold":
                self.screen.blit(coin, coin.get_rect(center=pos))
            elif item.kind == "hp_flask":
                self.screen.blit(self.flask_hp_sprite, self.flask_hp_sprite.get_rect(center=pos))
            elif item.kind == "mana_flask":
                self.screen.blit(self.flask_mana_sprite, self.flask_mana_sprite.get_rect(center=pos))
            elif item.kind == "gear" and isinstance(item.payload, GearItem):
                rect = pygame.Rect(pos[0] - 11, pos[1] - 11, 22, 22)
                pygame.draw.rect(self.screen, (20, 22, 28), rect, border_radius=5)
                pygame.draw.rect(self.screen, item.payload.color, rect, 2, border_radius=5)
                if item.payload.icon_path:
                    icon = self.get_item_icon(item.payload.icon_path, 18)
                    self.screen.blit(icon, icon.get_rect(center=pos))
                else:
                    label = self.font_tiny.render(item.payload.slot[0].upper(), True, item.payload.color)
                    self.screen.blit(label, label.get_rect(center=pos))

    def draw_minimap(self):
        rect = pygame.Rect(SCREEN_WIDTH - 258, 18, 240, 240)
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel.fill((10, 10, 14, 190))
        cell_w = rect.width / MAP_WIDTH
        cell_h = rect.height / MAP_HEIGHT
        for ty in range(MAP_HEIGHT):
            for tx in range(MAP_WIDTH):
                if (tx, ty) in self.explored_tiles:
                    x = int(tx * cell_w)
                    y = int(ty * cell_h)
                    color = (105, 110, 122, 235) if (tx, ty) in self.world.blocked_tiles else (60, 66, 80, 220)
                    pygame.draw.rect(panel, color, pygame.Rect(x, y, max(1, int(math.ceil(cell_w))), max(1, int(math.ceil(cell_h)))))
        for enemy in self.enemies:
            tile = (int(enemy.x // TILE_SIZE), int(enemy.y // TILE_SIZE))
            if enemy.alive and tile in self.explored_tiles:
                pygame.draw.circle(panel, (220, 80, 80, 220), (int((enemy.x / self.world.width_px) * rect.width), int((enemy.y / self.world.height_px) * rect.height)), 2)
        pygame.draw.circle(panel, (120, 220, 120, 255), (int((self.player.x / self.world.width_px) * rect.width), int((self.player.y / self.world.height_px) * rect.height)), 3)
        self.screen.blit(panel, rect.topleft)
        pygame.draw.rect(self.screen, (190, 190, 205), rect, 2, border_radius=8)

    def draw_overlay_map(self):
        scale = 9
        map_rect = pygame.Rect(0, 0, MAP_WIDTH * scale, MAP_HEIGHT * scale)
        map_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        panel = pygame.Surface((map_rect.width, map_rect.height), pygame.SRCALPHA)
        panel.fill((20, 22, 30, 200))
        for ty in range(MAP_HEIGHT):
            for tx in range(MAP_WIDTH):
                if (tx, ty) in self.explored_tiles:
                    color = (135, 140, 155, 220) if (tx, ty) in self.world.blocked_tiles else (78, 85, 102, 190)
                    pygame.draw.rect(panel, color, pygame.Rect(tx * scale, ty * scale, scale, scale))
        for enemy in self.enemies:
            tile = (int(enemy.x // TILE_SIZE), int(enemy.y // TILE_SIZE))
            if enemy.alive and tile in self.explored_tiles:
                pygame.draw.circle(panel, (232, 90, 90, 230), (int((enemy.x / self.world.width_px) * map_rect.width), int((enemy.y / self.world.height_px) * map_rect.height)), 4)
        pygame.draw.circle(panel, (120, 230, 120, 255), (int((self.player.x / self.world.width_px) * map_rect.width), int((self.player.y / self.world.height_px) * map_rect.height)), 5)
        overlay.blit(panel, map_rect.topleft)
        pygame.draw.rect(overlay, (210, 210, 220, 230), map_rect, 2, border_radius=10)
        overlay.blit(self.font_small.render("TAB: fechar mapa", True, (225, 225, 235)), (map_rect.left, map_rect.bottom + 8))
        self.screen.blit(overlay, (0, 0))

    def draw_ui(self):
        panel = pygame.Rect(16, 16, 440, 186)
        pygame.draw.rect(self.screen, UI_BG_COLOR, panel, border_radius=10)
        hp = pygame.Rect(28, 52, 260, 20)
        mana = pygame.Rect(28, 76, 260, 16)
        xp = pygame.Rect(28, 100, 260, 16)
        pygame.draw.rect(self.screen, (55, 55, 65), hp, border_radius=6)
        pygame.draw.rect(self.screen, (55, 55, 65), mana, border_radius=6)
        pygame.draw.rect(self.screen, (55, 55, 65), xp, border_radius=6)
        pygame.draw.rect(self.screen, UI_HP_COLOR, pygame.Rect(hp.x, hp.y, int(hp.width * (self.player.hp / self.player.max_hp)), hp.height), border_radius=6)
        pygame.draw.rect(self.screen, UI_MANA_COLOR, pygame.Rect(mana.x, mana.y, int(mana.width * (self.player.mana / self.player.max_mana)), mana.height), border_radius=6)
        pygame.draw.rect(self.screen, UI_XP_COLOR, pygame.Rect(xp.x, xp.y, int(xp.width * (self.player.xp / self.player.xp_to_next)), xp.height), border_radius=6)
        self.screen.blit(self.font.render(f"LVL {self.player.level}", True, UI_TEXT_COLOR), (28, 22))
        self.screen.blit(self.font_small.render(f"HP: {self.player.hp}/{self.player.max_hp}", True, UI_TEXT_COLOR), (300, 52))
        self.screen.blit(self.font_small.render(f"MANA: {int(self.player.mana)}/{self.player.max_mana}", True, UI_TEXT_COLOR), (300, 74))
        self.screen.blit(self.font_small.render(f"XP: {self.player.xp}/{self.player.xp_to_next}", True, UI_TEXT_COLOR), (300, 98))
        self.screen.blit(self.font_small.render(f"ATK: {self.player.current_damage}", True, UI_TEXT_COLOR), (28, 126))
        self.screen.blit(self.font_small.render(f"SPD: {int(self.player.speed)}", True, UI_TEXT_COLOR), (118, 126))
        self.screen.blit(self.font_small.render(f"ARMA: {self.player.weapon_mode.upper()}", True, UI_TEXT_COLOR), (198, 126))
        self.screen.blit(self.font_small.render(f"CLASSE: {self.player.class_name.upper()}", True, UI_TEXT_COLOR), (320, 126))
        self.screen.blit(self.font_small.render(f"OURO: {self.player.gold}", True, (255, 221, 120)), (28, 148))
        self.screen.blit(self.font_small.render(f"FRASCOS HP/MP: {self.player.health_flasks}/{self.player.mana_flasks}", True, UI_TEXT_COLOR), (130, 148))
        phase_label = "BASE / PREPARO" if self.wave_phase == "prep" else "COMBATE"
        self.screen.blit(self.font_small.render(f"WAVE: {self.current_wave}  PROX: {self.pending_wave}  FASE: {phase_label}", True, UI_TEXT_COLOR), (16, 206))
        if self.wave_phase == "prep":
            self.screen.blit(self.font_small.render("Saia da base para iniciar a proxima wave | B: loja | I: inventario", True, (205, 210, 224)), (16, 228))
        elif self.show_shop:
            self.screen.blit(self.font_small.render("B: fechar loja", True, (205, 210, 224)), (16, 228))
        if self.player.level_up_flash_timer > 0:
            lbl = self.font_big.render("LEVEL UP!", True, (255, 220, 90))
            self.screen.blit(lbl, lbl.get_rect(center=(SCREEN_WIDTH // 2, 54)))

    def draw_shop_panel(self):
        panel = pygame.Rect(SCREEN_WIDTH - 370, 280, 350, 380)
        pygame.draw.rect(self.screen, (18, 20, 28), panel, border_radius=12)
        pygame.draw.rect(self.screen, (172, 178, 196), panel, 2, border_radius=12)
        self.screen.blit(self.font.render("LOJA DA BASE", True, UI_TEXT_COLOR), (panel.x + 14, panel.y + 12))
        self.screen.blit(self.font_small.render("Clique esquerdo: comprar | Clique direito no inventario: vender", True, (190, 195, 210)), (panel.x + 14, panel.y + 40))
        self.shop_item_rects = {}
        y = panel.y + 72
        for item in self.shop_items[:6]:
            item_rect = pygame.Rect(panel.x + 14, y, panel.width - 28, 44)
            self.shop_item_rects[item.item_id] = item_rect
            pygame.draw.rect(self.screen, (30, 34, 46), item_rect, border_radius=8)
            pygame.draw.rect(self.screen, item.color, item_rect, 2, border_radius=8)
            left = f"{item.name} [{SLOT_LABELS[item.slot]}]"
            right = f"{item.value}g"
            self.screen.blit(self.font_small.render(left, True, UI_TEXT_COLOR), (item_rect.x + 10, item_rect.y + 12))
            price_label = self.font_small.render(right, True, (255, 221, 120))
            self.screen.blit(price_label, (item_rect.right - price_label.get_width() - 10, item_rect.y + 12))
            y += 50
        if not self.shop_items:
            self.screen.blit(self.font_small.render("Estoque vazio (proxima wave reabastece).", True, (190, 195, 210)), (panel.x + 16, panel.y + 86))

    def draw_class_selection(self):
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 165))
        self.screen.blit(shade, (0, 0))
        panel = pygame.Rect((SCREEN_WIDTH - 720) // 2, (SCREEN_HEIGHT - 280) // 2, 720, 280)
        pygame.draw.rect(self.screen, (20, 22, 30), panel, border_radius=14)
        pygame.draw.rect(self.screen, (170, 178, 195), panel, 2, border_radius=14)
        self.screen.blit(self.font_big.render("Escolha sua classe", True, UI_TEXT_COLOR), (panel.x + 20, panel.y + 20))
        self.screen.blit(self.font_small.render("1) Guerreiro - espada default", True, (230, 210, 180)), (panel.x + 26, panel.y + 92))
        self.screen.blit(self.font_small.render("2) Mago - spell default (raio)", True, (180, 210, 250)), (panel.x + 26, panel.y + 132))
        self.screen.blit(self.font_small.render("3) Arqueiro - arco default", True, (200, 240, 200)), (panel.x + 26, panel.y + 172))
        self.screen.blit(self.font_small.render("Pressione 1, 2 ou 3 para iniciar.", True, (190, 195, 210)), (panel.x + 26, panel.y + 228))

    def draw_inventory_item(self, item: GearItem, rect: pygame.Rect):
        pygame.draw.rect(self.screen, (28, 30, 40), rect, border_radius=6)
        pygame.draw.rect(self.screen, item.color, rect, 2, border_radius=6)
        if item.icon_path:
            icon_size = max(14, min(rect.width, rect.height) - 10)
            icon = self.get_item_icon(item.icon_path, icon_size)
            self.screen.blit(icon, icon.get_rect(center=(rect.x + rect.width // 2, rect.y + rect.height // 2)))
        self.screen.blit(self.font_tiny.render(item.name.split()[0], True, item.color), (rect.x + 4, rect.y + 4))

    def draw_inventory_panel(self):
        panel, grid, cell, slots = self.inventory_layout()
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 95))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, (20, 22, 30), panel, border_radius=12)
        pygame.draw.rect(self.screen, (175, 180, 196), panel, 2, border_radius=12)
        self.screen.blit(self.font.render("INVENTARIO E EQUIPAMENTOS", True, UI_TEXT_COLOR), (panel.x + 16, panel.y + 14))
        self.screen.blit(self.font_small.render("Arraste itens na grade e nos slots de equipamento.", True, (190, 195, 210)), (panel.x + 16, panel.y + 42))
        pygame.draw.rect(self.screen, (32, 35, 48), grid, border_radius=8)
        for x in range(self.inventory.cols + 1):
            px = grid.x + x * cell
            pygame.draw.line(self.screen, (58, 62, 80), (px, grid.y), (px, grid.bottom))
        for y in range(self.inventory.rows + 1):
            py = grid.y + y * cell
            pygame.draw.line(self.screen, (58, 62, 80), (grid.x, py), (grid.right, py))
        for slot, rect in slots.items():
            pygame.draw.rect(self.screen, (34, 38, 52), rect, border_radius=8)
            pygame.draw.rect(self.screen, (86, 90, 112), rect, 2, border_radius=8)
            self.screen.blit(self.font_tiny.render(SLOT_LABELS[slot], True, (185, 190, 208)), (rect.x, rect.y - 16))
        for item_id, (gx, gy) in self.inventory.grid_positions.items():
            if self.drag_item_id != item_id:
                item = self.inventory.get_item(item_id)
                self.draw_inventory_item(item, pygame.Rect(grid.x + gx * cell, grid.y + gy * cell, item.width * cell, item.height * cell))
        for slot, item_id in self.inventory.equipped.items():
            if item_id is not None and self.drag_item_id != item_id:
                self.draw_inventory_item(self.inventory.get_item(item_id), slots[slot])
        if self.drag_item_id is not None:
            item = self.inventory.get_item(self.drag_item_id)
            mx, my = pygame.mouse.get_pos()
            self.draw_inventory_item(item, pygame.Rect(mx - (item.width * cell) // 2, my - (item.height * cell) // 2, item.width * cell, item.height * cell))
        info_y = panel.bottom - 56
        self.screen.blit(self.font_small.render(f"Ouro: {self.player.gold}", True, UI_TEXT_COLOR), (panel.x + 24, info_y))
        hp_icon_rect = self.flask_hp_sprite.get_rect(topleft=(panel.x + 190, info_y - 6))
        mana_icon_rect = self.flask_mana_sprite.get_rect(topleft=(panel.x + 320, info_y - 6))
        self.screen.blit(self.flask_hp_sprite, hp_icon_rect)
        self.screen.blit(self.flask_mana_sprite, mana_icon_rect)
        self.screen.blit(self.font_small.render(f"x {self.player.health_flasks}", True, UI_TEXT_COLOR), (hp_icon_rect.right + 8, info_y))
        self.screen.blit(self.font_small.render(f"x {self.player.mana_flasks}", True, UI_TEXT_COLOR), (mana_icon_rect.right + 8, info_y))
        self.screen.blit(self.font_small.render("I: fechar inventario", True, (190, 195, 210)), (panel.x + 24, panel.bottom - 28))

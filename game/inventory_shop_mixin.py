import pygame

from game.settings import SCREEN_HEIGHT, SCREEN_WIDTH


class InventoryShopMixin:
    def inventory_layout(self):
        panel = pygame.Rect((SCREEN_WIDTH - 780) // 2, (SCREEN_HEIGHT - 500) // 2, 780, 500)
        cell = 36
        grid = pygame.Rect(panel.x + 24, panel.y + 64, self.inventory.cols * cell, self.inventory.rows * cell)
        slots = {
            "weapon": pygame.Rect(panel.x + 440, panel.y + 84, 2 * cell, 3 * cell),
            "helmet": pygame.Rect(panel.x + 540, panel.y + 84, 2 * cell, 2 * cell),
            "cape": pygame.Rect(panel.x + 540, panel.y + 166, 2 * cell, 2 * cell),
            "belt": pygame.Rect(panel.x + 540, panel.y + 248, 2 * cell, 1 * cell),
            "boots": pygame.Rect(panel.x + 540, panel.y + 308, 2 * cell, 2 * cell),
        }
        return panel, grid, cell, slots

    def handle_shop_buy_click(self, pos: tuple[int, int]) -> bool:
        for item_id, rect in self.shop_item_rects.items():
            if not rect.collidepoint(pos[0], pos[1]):
                continue
            item = next((gear for gear in self.shop_items if gear.item_id == item_id), None)
            if item is None:
                return False
            if self.player.gold < item.value:
                return True
            if not self.inventory.add_item(item):
                return True
            self.player.gold -= item.value
            self.shop_items = [gear for gear in self.shop_items if gear.item_id != item_id]
            self.refresh_player_from_equipment()
            return True
        return False

    def sell_item(self, item_id: int):
        item = self.inventory.get_item(item_id)
        self.player.gold += max(1, item.value // 2)
        self.inventory.remove_item(item_id)
        if self.drag_item_id == item_id:
            self.drag_item_id = None
            self.drag_origin = None
        self.refresh_player_from_equipment()

    def handle_inventory_sell_click(self, pos: tuple[int, int]) -> bool:
        panel, grid, cell, slots = self.inventory_layout()
        mx, my = pos
        if grid.collidepoint(mx, my):
            gx = (mx - grid.x) // cell
            gy = (my - grid.y) // cell
            item_id = self.inventory.get_item_at_cell(gx, gy)
            if item_id is not None:
                self.sell_item(item_id)
                return True
        for slot, rect in slots.items():
            if rect.collidepoint(mx, my):
                item_id = self.inventory.get_equipped_item(slot)
                if item_id is not None:
                    self.sell_item(item_id)
                    return True
        return False

    def handle_inventory_click(self, pos: tuple[int, int]):
        panel, grid, cell, slots = self.inventory_layout()
        mx, my = pos
        if self.drag_item_id is None:
            for slot, rect in slots.items():
                if rect.collidepoint(mx, my):
                    item_id = self.inventory.get_equipped_item(slot)
                    if item_id is not None:
                        self.inventory.pickup_item(item_id)
                        self.drag_item_id = item_id
                        self.drag_origin = ("slot", slot)
                    return
            if grid.collidepoint(mx, my):
                gx = (mx - grid.x) // cell
                gy = (my - grid.y) // cell
                item_id = self.inventory.get_item_at_cell(gx, gy)
                if item_id is not None:
                    self.drag_origin = ("grid", self.inventory.grid_positions[item_id])
                    self.inventory.pickup_item(item_id)
                    self.drag_item_id = item_id
                return
            return

        placed = False
        for slot, rect in slots.items():
            if rect.collidepoint(mx, my):
                placed = self.inventory.place_in_slot(self.drag_item_id, slot)
                break
        if not placed and grid.collidepoint(mx, my):
            gx = (mx - grid.x) // cell
            gy = (my - grid.y) // cell
            placed = self.inventory.place_in_grid(self.drag_item_id, gx, gy)

        if placed:
            self.drag_item_id = None
            self.drag_origin = None
            self.refresh_player_from_equipment()
        elif not panel.collidepoint(mx, my) and self.drag_origin is not None:
            kind, ref = self.drag_origin
            if kind == "slot":
                self.inventory.place_in_slot(self.drag_item_id, ref)
            else:
                ox, oy = ref
                if not self.inventory.place_in_grid(self.drag_item_id, ox, oy):
                    fit = self.inventory.find_first_fit(self.inventory.get_item(self.drag_item_id), ignore_item_id=self.drag_item_id)
                    if fit:
                        self.inventory.place_in_grid(self.drag_item_id, fit[0], fit[1])
            self.drag_item_id = None
            self.drag_origin = None
            self.refresh_player_from_equipment()

    def cancel_drag_to_origin(self):
        if self.drag_item_id is None or self.drag_origin is None:
            return
        kind, ref = self.drag_origin
        if kind == "slot":
            self.inventory.place_in_slot(self.drag_item_id, ref)
        else:
            ox, oy = ref
            if not self.inventory.place_in_grid(self.drag_item_id, ox, oy):
                fit = self.inventory.find_first_fit(self.inventory.get_item(self.drag_item_id), ignore_item_id=self.drag_item_id)
                if fit:
                    self.inventory.place_in_grid(self.drag_item_id, fit[0], fit[1])
        self.drag_item_id = None
        self.drag_origin = None
        self.refresh_player_from_equipment()

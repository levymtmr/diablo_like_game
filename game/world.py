import random

from game.settings import MAP_HEIGHT, MAP_WIDTH, TILE_SIZE


class WorldMap:
    def __init__(self):
        self.base_half_size = 4
        self.base_center = (MAP_WIDTH // 2, MAP_HEIGHT // 2)
        self.base_tiles = self._build_base_tiles()
        self.blocked_tiles = self._build_map()

    @property
    def width_px(self) -> int:
        return MAP_WIDTH * TILE_SIZE

    @property
    def height_px(self) -> int:
        return MAP_HEIGHT * TILE_SIZE

    def _build_map(self) -> set[tuple[int, int]]:
        random.seed(7)
        blocked = set()

        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if x in (0, MAP_WIDTH - 1) or y in (0, MAP_HEIGHT - 1):
                    blocked.add((x, y))

        for _ in range(320):
            x = random.randint(2, MAP_WIDTH - 3)
            y = random.randint(2, MAP_HEIGHT - 3)
            blocked.add((x, y))

        for tx, ty in self.base_tiles:
            blocked.discard((tx, ty))

        return blocked

    def _build_base_tiles(self) -> set[tuple[int, int]]:
        cx, cy = self.base_center
        size = self.base_half_size
        tiles = set()
        for y in range(cy - size, cy + size + 1):
            for x in range(cx - size, cx + size + 1):
                if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                    tiles.add((x, y))
        return tiles

    def is_in_base_world(self, x: float, y: float) -> bool:
        tx = int(x // TILE_SIZE)
        ty = int(y // TILE_SIZE)
        return (tx, ty) in self.base_tiles

    def collides(self, radius: float, x: float, y: float) -> bool:
        min_tx = int((x - radius) // TILE_SIZE)
        max_tx = int((x + radius) // TILE_SIZE)
        min_ty = int((y - radius) // TILE_SIZE)
        max_ty = int((y + radius) // TILE_SIZE)

        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                if tx < 0 or ty < 0 or tx >= MAP_WIDTH or ty >= MAP_HEIGHT:
                    return True
                if (tx, ty) in self.blocked_tiles:
                    return True
        return False

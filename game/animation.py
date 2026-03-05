from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class AnimationClip:
    frames: list[pygame.Surface]
    frame_time: float
    loop: bool = True

    @property
    def duration(self) -> float:
        return len(self.frames) * self.frame_time

    def get_frame(self, elapsed: float) -> pygame.Surface:
        if not self.frames:
            raise ValueError("Animation clip has no frames.")

        frame_index = int(elapsed / self.frame_time) if self.frame_time > 0 else 0
        if self.loop:
            frame_index %= len(self.frames)
        else:
            frame_index = min(frame_index, len(self.frames) - 1)
        return self.frames[frame_index]


class Animator:
    def __init__(self, clips: dict[str, AnimationClip], initial_state: str = "idle"):
        if initial_state not in clips:
            raise ValueError(f"Unknown initial animation state: {initial_state}")
        self.clips = clips
        self.state = initial_state
        self.elapsed = 0.0
        self.finished = False

    def set_state(self, state: str, restart: bool = False):
        if state not in self.clips:
            raise ValueError(f"Unknown animation state: {state}")
        if state != self.state or restart:
            self.state = state
            self.elapsed = 0.0
            self.finished = False

    def update(self, dt: float):
        clip = self.clips[self.state]
        self.elapsed += dt
        if not clip.loop and self.elapsed >= clip.duration:
            self.finished = True

    def current_frame(self) -> pygame.Surface:
        clip = self.clips[self.state]
        return clip.get_frame(self.elapsed)


def load_strip(path: str, frame_size: int, scale_to: int) -> list[pygame.Surface]:
    sheet = pygame.image.load(path).convert_alpha()
    frame_count = sheet.get_width() // frame_size
    frames = []

    for frame_idx in range(frame_count):
        src = pygame.Rect(frame_idx * frame_size, 0, frame_size, frame_size)
        frame = sheet.subsurface(src).copy()
        if scale_to != frame_size:
            frame = pygame.transform.smoothscale(frame, (scale_to, scale_to))
        frames.append(frame)

    return frames


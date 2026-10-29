"""Небольшие переиспользуемые виджеты поверх theme.py."""
import math

import pygame

from . import theme


def draw_ring(screen, center, radius, thickness, fraction, color, track=theme.BORDER_SOFT):
    """Кольцо-индикатор. Рисуется в 3-кратном разрешении и уменьшается: края получаются гладкими."""
    scale = 3
    size = (radius + 2) * 2 * scale
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    mid = size // 2
    pygame.draw.circle(layer, track, (mid, mid), radius * scale, thickness * scale)
    fraction = max(0.0, min(1.0, fraction))
    if fraction > 0:
        start = -math.pi / 2
        steps = max(3, int(120 * fraction))
        outer, inner = [], []
        for i in range(steps + 1):
            angle = start + 2 * math.pi * fraction * i / steps
            outer.append((mid + radius * scale * math.cos(angle), mid + radius * scale * math.sin(angle)))
            inner.append((mid + (radius - thickness) * scale * math.cos(angle), mid + (radius - thickness) * scale * math.sin(angle)))
        pygame.draw.polygon(layer, color, outer + inner[::-1])
    small = pygame.transform.smoothscale(layer, (size // scale, size // scale))
    screen.blit(small, small.get_rect(center=center))


def draw_bar(screen, rect, fraction, color, track=theme.SURFACE_ALT, border=None):
    """Горизонтальная полоса-индикатор со скруглением."""
    radius = rect.height // 2
    pygame.draw.rect(screen, track, rect, border_radius=radius)
    fraction = max(0.0, min(1.0, fraction))
    if fraction > 0:
        fill = pygame.Rect(rect.x, rect.y, max(rect.height, int(rect.width * fraction)), rect.height)
        pygame.draw.rect(screen, color, fill, border_radius=radius)
    if border:
        pygame.draw.rect(screen, border, rect, 1, border_radius=radius)


def draw_hexagon(screen, center, radius, color, width=0):
    points = [(center[0] + radius * math.cos(math.radians(60 * i + 30)),
               center[1] + radius * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    pygame.draw.polygon(screen, color, points, width)


def wrap_lines(text, font, max_width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

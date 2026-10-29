"""Карта сети босс-уровня: узлы меняют цвет по ходу атаки, по рёбрам
бегут «пакеты» атакующего."""
import math

import pygame

from . import theme

STATE_STYLE = {
    "ok": (theme.SURFACE_ALT, theme.BORDER, theme.TEXT_SECONDARY),
    "suspicious": (theme.WARNING_DIM, theme.WARNING, theme.WARNING),
    "compromised": (theme.DANGER_DIM, theme.DANGER, theme.DANGER),
    "contained": (theme.ACCENT_DIM, theme.ACCENT, theme.ACCENT),
}
LEGEND = [("ok", "штатно"), ("suspicious", "под подозрением"), ("compromised", "взломан"), ("contained", "изолирован")]
NODE_RADIUS = 14


def _node_pos(rect, spec):
    x, y, _ = spec
    top, bottom = rect.y + 50, rect.bottom - 36
    return (rect.x + 26 + int((rect.width - 52) * x), top + int((bottom - top) * y))


def _point_on_path(points, progress):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    target = total * progress
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if target <= length and length > 0:
            k = target / length
            return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        target -= length
    return points[-1]


def draw_network_map(screen, rect, nodes, edges, states, now_ms, path=None, animate=True):
    theme.draw_panel(screen, rect, radius=theme.RADIUS_LG)
    prev_clip = screen.get_clip()
    screen.set_clip(rect)
    title = theme.font(theme.FONT_SM, bold=True).render("Карта сети «Нордтех»", True, theme.TEXT_PRIMARY)
    screen.blit(title, (rect.x + 16, rect.y + 10))

    positions = {node: _node_pos(rect, spec) for node, spec in nodes.items()}
    for a, b in edges:
        hot = states[a] == "compromised" and states[b] == "compromised"
        pygame.draw.line(screen, theme.DANGER_DIM if hot else theme.BORDER, positions[a], positions[b], 3 if hot else 2)

    if path and animate:
        points = [positions[node] for node in path]
        for k in range(3):
            progress = ((now_ms / 1400.0) + k / 3.0) % 1.0
            x, y = _point_on_path(points, progress)
            glow = pygame.Surface((26, 26), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*theme.DANGER, 70), (13, 13), 12)
            screen.blit(glow, (x - 13, y - 13))
            pygame.draw.circle(screen, theme.DANGER, (int(x), int(y)), 4)

    label_font = theme.font(12)
    pulse = (math.sin(now_ms / 260.0) + 1) / 2
    for node, (px, py) in positions.items():
        fill, border, text = STATE_STYLE[states[node]]
        if states[node] == "compromised":
            halo = pygame.Surface((70, 70), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*theme.DANGER, int(40 + 60 * pulse)), (35, 35), int(20 + 8 * pulse))
            screen.blit(halo, (px - 35, py - 35))
        pygame.draw.circle(screen, fill, (px, py), NODE_RADIUS)
        pygame.draw.circle(screen, border, (px, py), NODE_RADIUS, 2)
        if states[node] == "contained":
            theme.draw_check(screen, (px, py), size=6, color=theme.ACCENT, width=2)
        elif states[node] == "compromised":
            theme.draw_cross(screen, (px, py), size=5, color=theme.DANGER, width=2)
        elif states[node] == "suspicious":
            mark = theme.font(theme.FONT_XS, bold=True).render("?", True, theme.WARNING)
            screen.blit(mark, mark.get_rect(center=(px, py)))
        surf = label_font.render(nodes[node][2], True, text)
        label_x = min(max(px - surf.get_width() // 2, rect.x + 6), rect.right - surf.get_width() - 6)
        screen.blit(surf, (label_x, py + NODE_RADIUS + 2))

    legend_font = theme.font(12)
    x = rect.right - 16
    y = rect.y + 13
    for state, text in reversed(LEGEND):
        _, border, _ = STATE_STYLE[state]
        surf = legend_font.render(text, True, theme.TEXT_MUTED)
        x -= surf.get_width()
        screen.blit(surf, (x, y))
        x -= 12
        pygame.draw.circle(screen, border, (x + 4, y + 7), 4)
        x -= 14
    screen.set_clip(prev_clip)

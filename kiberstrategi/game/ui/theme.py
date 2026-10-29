"""Единая дизайн-система тренажёра: палитра, шрифты, переиспользуемые
примитивы отрисовки (панель с тенью, разделитель, статус-плашка).

Раньше почти каждый файл game/scenes/*.py задавал свои HEADER_COLOR /
BODY_COLOR / BORDER_COLOR и т.п. с одними и теми же значениями,
скопированными друг у друга. Теперь это один источник правды — экраны
выглядят согласованно, и палитру можно поменять в одном месте.
"""
import functools

import pygame

# --- Палитра: тёмная «SOC-дэшборд», три уровня возвышения + акценты ---
BG = (13, 17, 25)            # фон страницы
SURFACE = (22, 28, 40)       # панель первого уровня
SURFACE_ALT = (30, 38, 53)   # чуть светлее — карточки, поля ввода
ELEVATED = (39, 49, 68)      # наведённые/активные элементы

BORDER = (52, 64, 86)        # обычная граница панели
BORDER_SOFT = (38, 47, 64)   # едва заметная граница (разделители)

ACCENT = (56, 189, 248)      # основной акцент — голубой (кибер/SOC)
ACCENT_DIM = (30, 100, 140)
ACCENT_STRONG = (14, 165, 233)

SUCCESS = (52, 211, 153)
SUCCESS_DIM = (20, 90, 70)
SUCCESS_SOFT = (167, 243, 208)
DANGER = (248, 113, 113)
DANGER_DIM = (110, 35, 35)
WARNING = (251, 191, 36)
WARNING_DIM = (90, 70, 20)

TEXT_PRIMARY = (241, 245, 249)
TEXT_SECONDARY = (148, 163, 184)
TEXT_MUTED = (100, 116, 139)
TEXT_ON_ACCENT = (8, 20, 30)

# Уровни/ранги — сохраняем смысловые цвета из ВКР (зелёный/жёлтый/красный),
# но в тонах, согласованных с общей палитрой.
LEVEL_COLORS = {
    1: (52, 168, 128),   # Стажёр — зелёный
    2: (217, 164, 65),   # Аналитик — янтарный
    3: (220, 90, 90),    # Эксперт — красный
}

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 16


@functools.lru_cache(maxsize=None)
def _font_path():
    """Ищет современный системный шрифт один раз и кэширует путь (или None)."""
    for name in ("segoeui", "seguisb", "helveticaneue", "helvetica", "arial", "verdana", "dejavusans"):
        path = pygame.font.match_font(name)
        if path:
            return path
    return None


@functools.lru_cache(maxsize=None)
def font(size, bold=False):
    path = _font_path()
    f = pygame.font.Font(path, size)
    f.set_bold(bold)
    return f


# Шкала размеров шрифта — используем вместо произвольных чисел по месту.
FONT_XS = 16
FONT_SM = 18
FONT_MD = 20
FONT_LG = 24
FONT_XL = 28
FONT_XXL = 36
FONT_TITLE = 44


def draw_panel(screen, rect, radius=RADIUS_MD, fill=SURFACE, border=BORDER, border_width=1, shadow=True):
    """Панель с мягкой тенью и скруглёнными углами — базовый строительный блок экранов."""
    if shadow:
        shadow_rect = rect.move(0, 4)
        shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surface, (0, 0, 0, 70), shadow_surface.get_rect(), border_radius=radius)
        screen.blit(shadow_surface, shadow_rect.topleft)
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    if border_width:
        pygame.draw.rect(screen, border, rect, border_width, border_radius=radius)


def draw_header_bar(screen, rect, title_surface, accent=ACCENT):
    """Заголовок панели: тёмная плашка сверху с акцентной линией снизу (замена XP-шапки)."""
    pygame.draw.rect(screen, SURFACE_ALT, rect, border_top_left_radius=RADIUS_MD, border_top_right_radius=RADIUS_MD)
    pygame.draw.line(screen, accent, (rect.x, rect.bottom - 1), (rect.right, rect.bottom - 1), 2)
    screen.blit(title_surface, title_surface.get_rect(center=rect.center))


def draw_divider(screen, x, y, width, color=BORDER_SOFT):
    pygame.draw.line(screen, color, (x, y), (x + width, y), 1)


def draw_check(screen, center, size=9, color=SUCCESS, width=3):
    """Векторная галочка — не зависит от того, есть ли ✓ в системном шрифте."""
    x, y = center
    pygame.draw.lines(screen, color, False, [
        (x - size, y), (x - size * 0.3, y + size * 0.8), (x + size, y - size * 0.8)
    ], width)


def draw_cross(screen, center, size=8, color=DANGER, width=3):
    x, y = center
    pygame.draw.line(screen, color, (x - size, y - size), (x + size, y + size), width)
    pygame.draw.line(screen, color, (x - size, y + size), (x + size, y - size), width)


def draw_lock(screen, center, color=TEXT_MUTED, scale=1.0):
    """Маленький замочек — статус «ещё не разблокировано» (ачивки, карточка результата)."""
    x, y = center
    s = scale
    body = pygame.Rect(0, 0, int(10 * s), int(7 * s))
    body.center = (x, y + int(1 * s))
    pygame.draw.rect(screen, color, body, border_radius=max(1, int(1 * s)))
    arc_rect = pygame.Rect(0, 0, int(8 * s), int(8 * s))
    arc_rect.center = (x, y - int(3 * s))
    pygame.draw.arc(screen, color, arc_rect, 0.3, 2.85, max(1, int(2 * s)))


def draw_badge(screen, center, text, fg=TEXT_PRIMARY, bg=ELEVATED, pad_x=10, pad_y=4, font_size=FONT_XS):
    """Маленькая цветная плашка-статус (например, уровень сложности)."""
    surf = font(font_size, bold=True).render(text, True, fg)
    rect = pygame.Rect(0, 0, surf.get_width() + pad_x * 2, surf.get_height() + pad_y * 2)
    rect.center = center
    pygame.draw.rect(screen, bg, rect, border_radius=rect.height // 2)
    screen.blit(surf, surf.get_rect(center=rect.center))
    return rect

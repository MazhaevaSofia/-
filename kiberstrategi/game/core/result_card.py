"""Шаринг-карточка с результатом прохождения — как карточка Wordle, но
для тренажёра: счёт, оценка и ряд значков достижений в одной PNG-картинке,
которую можно переслать в чат класса, не открывая саму игру.

Полностью переиспользует game/ui/theme.py, чтобы карточка выглядела как
продолжение интерфейса, а не отдельная самодельная картинка.
"""
import datetime
import os

import pygame

from ..ui import theme
from .achievements import ACHIEVEMENTS
from .save_manager import _default_save_dir

CARD_WIDTH = 1000
CARD_HEIGHT = 600
RESULTS_DIR_NAME = "results"


def _grade_for_percent(percent):
    if percent >= 90:
        return "ОТЛИЧНО", theme.SUCCESS
    if percent >= 70:
        return "ХОРОШО", theme.WARNING
    if percent >= 40:
        return "УДОВЛЕТВОРИТЕЛЬНО", theme.WARNING
    return "ЕСТЬ НАД ЧЕМ ПОРАБОТАТЬ", theme.DANGER


def render_result_card(username, score, max_score, unlocked_achievement_ids=None, new_achievement_ids=None):
    """Возвращает готовую pygame.Surface с карточкой результата (без сохранения на диск)."""
    unlocked_ids = set(unlocked_achievement_ids or [])
    new_ids = set(new_achievement_ids or [])

    # Значков стало больше, чем помещается в один разборчивый ряд — с некоторого
    # количества переходим на два ряда, а карточку делаем на ряд выше.
    ach_items = list(ACHIEVEMENTS.items())
    max_per_row = 9
    rows = 1 if len(ach_items) <= max_per_row else 2
    card_height = CARD_HEIGHT if rows == 1 else CARD_HEIGHT + 90

    surface = pygame.Surface((CARD_WIDTH, card_height))
    surface.fill(theme.SURFACE)
    pygame.draw.rect(surface, theme.ACCENT, (0, 0, CARD_WIDTH, 6))
    pygame.draw.rect(surface, theme.BORDER, (0, 0, CARD_WIDTH, card_height), 1)

    title_font = theme.font(30, bold=True)
    subtitle_font = theme.font(18)
    title = title_font.render("КИБЕРСТРАТЕГИИ: БИТВА ЗА ДАННЫЕ", True, theme.TEXT_PRIMARY)
    surface.blit(title, (CARD_WIDTH // 2 - title.get_width() // 2, 34))
    subtitle = subtitle_font.render("Результат прохождения тренажёра по кибербезопасности", True, theme.TEXT_SECONDARY)
    surface.blit(subtitle, (CARD_WIDTH // 2 - subtitle.get_width() // 2, 74))
    theme.draw_divider(surface, 60, 108, CARD_WIDTH - 120)

    percent = round(score / max_score * 100) if max_score else 0
    grade_text, grade_color = _grade_for_percent(percent)

    score_font = theme.font(64, bold=True)
    score_surf = score_font.render(f"{score}/{max_score}", True, theme.ACCENT)
    surface.blit(score_surf, (CARD_WIDTH // 2 - score_surf.get_width() // 2, 130))

    percent_font = theme.font(22, bold=True)
    percent_surf = percent_font.render(f"{percent}%  ·  {grade_text}", True, grade_color)
    surface.blit(percent_surf, (CARD_WIDTH // 2 - percent_surf.get_width() // 2, 208))

    name_font = theme.font(18)
    date_str = datetime.date.today().strftime("%d.%m.%Y")
    name_surf = name_font.render(f"{username}  ·  {date_str}", True, theme.TEXT_SECONDARY)
    surface.blit(name_surf, (CARD_WIDTH // 2 - name_surf.get_width() // 2, 244))

    theme.draw_divider(surface, 60, 288, CARD_WIDTH - 120)

    header_font = theme.font(20, bold=True)
    header = header_font.render(f"Достижения: {len(unlocked_ids)}/{len(ach_items)}", True, theme.TEXT_PRIMARY)
    surface.blit(header, (60, 306))

    cols = -(-len(ach_items) // rows) if ach_items else 1  # округление вверх
    slot_w = (CARD_WIDTH - 120) / cols
    badge_radius = min(28, int(slot_w / 2) - 8)
    row_height = 90
    badge_y_start = 400
    label_font = theme.font(13 if rows == 1 else 12)
    for i, (achievement_id, data) in enumerate(ach_items):
        row, col = divmod(i, cols)
        cx = int(60 + slot_w * col + slot_w / 2)
        badge_y = badge_y_start + row * row_height
        is_unlocked = achievement_id in unlocked_ids
        is_new = achievement_id in new_ids

        fill = theme.SUCCESS_DIM if is_unlocked else theme.ELEVATED
        border = theme.SUCCESS if is_unlocked else theme.BORDER
        pygame.draw.circle(surface, fill, (cx, badge_y), badge_radius)
        pygame.draw.circle(surface, border, (cx, badge_y), badge_radius, 2)
        if is_unlocked:
            theme.draw_check(surface, (cx, badge_y), size=12, color=theme.SUCCESS, width=3)
        else:
            theme.draw_lock(surface, (cx, badge_y), color=theme.TEXT_MUTED, scale=1.1)

        if is_new:
            pygame.draw.circle(surface, theme.WARNING, (cx + badge_radius - 4, badge_y - badge_radius + 4), 7)

        for j, line in enumerate(_wrap_label(data["title"], label_font, int(slot_w) - 10)):
            surf = label_font.render(line, True, theme.TEXT_PRIMARY if is_unlocked else theme.TEXT_MUTED)
            surface.blit(surf, (cx - surf.get_width() // 2, badge_y + badge_radius + 6 + j * 15))

    footer_font = theme.font(14)
    footer = footer_font.render("Сгенерировано в тренажёре «Киберстратегии: Битва за данные»", True, theme.TEXT_MUTED)
    surface.blit(footer, (CARD_WIDTH // 2 - footer.get_width() // 2, card_height - 30))

    return surface


def _wrap_label(text, font, max_width):
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
    return lines[:2]


def save_result_card(surface, filename=None):
    """Сохраняет карточку в results/ рядом с игрой (там же, где savegame.json). Возвращает путь."""
    directory = os.path.join(_default_save_dir(), RESULTS_DIR_NAME)
    os.makedirs(directory, exist_ok=True)
    if filename is None:
        filename = f"result_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(directory, filename)
    pygame.image.save(surface, path)
    return path

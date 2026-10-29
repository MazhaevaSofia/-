# Экран «Достижения»: список всех ачивок с отметкой разблокированных.
import pygame
from ..ui.button import Button
from ..ui import theme
from ..core.achievements import ACHIEVEMENTS


class AchievementsScene:
    def __init__(self, screen_width, screen_height, unlocked_ids, on_back):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.unlocked_ids = set(unlocked_ids)
        self.font_large = theme.font(theme.FONT_XL, bold=True)
        self.font_medium = theme.font(theme.FONT_MD, bold=True)
        self.font_small = theme.font(theme.FONT_SM)
        self.scroll = 0
        self._max_scroll = 0

        self.back_button = Button(30, screen_height - 55, 120, 35, "Назад", theme.SURFACE_ALT, on_back)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self.back_button.rect.y = h - 55

    def handle_event(self, event):
        if self.back_button.handle_event(event):
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - event.y * 40, self._max_scroll))
            return True
        return False

    def update(self):
        self.back_button.update()

    def draw(self, screen):
        screen.fill(theme.BG)

        unlocked_count = len(self.unlocked_ids)
        total_count = len(ACHIEVEMENTS)
        title = self.font_large.render(f"Достижения ({unlocked_count}/{total_count})", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 20))

        panel = pygame.Rect(40, 66, self.screen_width - 80, self.screen_height - 136)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)

        content_width = panel.width - 90
        screen.set_clip(panel)
        y = panel.y + 16 - self.scroll
        for achievement_id, data in ACHIEVEMENTS.items():
            is_unlocked = achievement_id in self.unlocked_ids
            desc_lines = self._wrap(data["description"], self.font_small, content_width)
            card_height = 16 + self.font_medium.get_height() + 6 + len(desc_lines) * 20 + 10
            card_rect = pygame.Rect(panel.x + 20, y, panel.width - 40, card_height)

            fill = theme.SURFACE_ALT if is_unlocked else theme.SURFACE
            pygame.draw.rect(screen, fill, card_rect, border_radius=theme.RADIUS_SM)
            accent = theme.SUCCESS if is_unlocked else theme.BORDER
            pygame.draw.rect(screen, accent, (card_rect.x, card_rect.y, 4, card_rect.height), border_top_left_radius=theme.RADIUS_SM, border_bottom_left_radius=theme.RADIUS_SM)

            badge_center = (card_rect.x + 30, card_rect.y + card_rect.height // 2)
            pygame.draw.circle(screen, theme.SUCCESS_DIM if is_unlocked else theme.SURFACE, badge_center, 14)
            pygame.draw.circle(screen, accent, badge_center, 14, 1)
            if is_unlocked:
                theme.draw_check(screen, badge_center, size=6, color=theme.SUCCESS, width=2)
            else:
                theme.draw_lock(screen, badge_center, color=theme.TEXT_MUTED, scale=0.8)

            text_x = card_rect.x + 56
            title_color = theme.TEXT_PRIMARY if is_unlocked else theme.TEXT_MUTED
            title_surf = self.font_medium.render(data["title"], True, title_color)
            screen.blit(title_surf, (text_x, card_rect.y + 12))

            desc_y = card_rect.y + 12 + title_surf.get_height() + 4
            for line in desc_lines:
                surf = self.font_small.render(line, True, theme.TEXT_SECONDARY if is_unlocked else theme.TEXT_MUTED)
                screen.blit(surf, (text_x, desc_y))
                desc_y += 20

            y += card_height + 14

        screen.set_clip(None)
        total_height = y + self.scroll - (panel.y + 16)
        self._max_scroll = max(0, total_height - panel.height + 16)
        self.scroll = min(self.scroll, self._max_scroll)

        self.back_button.draw(screen)

    @staticmethod
    def _wrap(text, font, max_width):
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

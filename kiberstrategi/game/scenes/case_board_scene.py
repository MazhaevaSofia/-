# Доска расследований: история пройденных дел кампании (техника, счёт, оценка, дата).
import pygame
from ..ui.button import Button
from ..ui import theme

GRADE_COLOR = {
    "success": theme.SUCCESS,
    "warning": theme.WARNING,
    "danger": theme.DANGER,
}


class CaseBoardScene:
    def __init__(self, screen_width, screen_height, case_log, on_back):
        self.screen_width = screen_width
        self.screen_height = screen_height
        # Новые дела сверху
        self.cases = list(reversed(case_log or []))
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

        title = self.font_large.render(f"Доска расследований ({len(self.cases)})", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 20))

        panel = pygame.Rect(40, 66, self.screen_width - 80, self.screen_height - 136)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)

        if not self.cases:
            hint = self.font_medium.render("Пока нет ни одного законченного дела — пройдите расследование.", True, theme.TEXT_SECONDARY)
            screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.centery - 10))
            self.back_button.draw(screen)
            return

        card_height = 68
        gap = 12
        screen.set_clip(panel)
        y = panel.y + 16 - self.scroll
        for case in self.cases:
            card_rect = pygame.Rect(panel.x + 20, y, panel.width - 40, card_height)

            fill = theme.SURFACE_ALT
            accent = GRADE_COLOR.get(case.get("grade_tag"), theme.BORDER)
            pygame.draw.rect(screen, fill, card_rect, border_radius=theme.RADIUS_SM)
            pygame.draw.rect(screen, accent, (card_rect.x, card_rect.y, 4, card_rect.height), border_top_left_radius=theme.RADIUS_SM, border_bottom_left_radius=theme.RADIUS_SM)

            technique = self.font_medium.render(case.get("technique", "?"), True, theme.TEXT_PRIMARY)
            screen.blit(technique, (card_rect.x + 20, card_rect.y + 10))

            date_text = self.font_small.render(case.get("date", ""), True, theme.TEXT_MUTED)
            screen.blit(date_text, (card_rect.x + 20, card_rect.y + 38))

            # Бейдж оценки — ширина зависит от текста («УДОВЛЕТВОРИТЕЛЬНО» и т.п.),
            # поэтому считаем её заранее, чтобы бейдж не вылезал за край карточки.
            badge_text = case.get("grade_text", "")
            badge_pad_x = 12
            badge_font = theme.font(theme.FONT_XS, bold=True)
            badge_w = badge_font.size(badge_text)[0] + badge_pad_x * 2
            badge_cx = card_rect.right - 20 - badge_w // 2
            theme.draw_badge(screen, (badge_cx, card_rect.centery), badge_text, fg=accent, bg=theme.ELEVATED, pad_x=badge_pad_x, pad_y=6, font_size=theme.FONT_XS)

            score = case.get("score", 0)
            max_score = case.get("max_score", 30)
            score_text = self.font_small.render(f"{score}/{max_score} очков", True, theme.TEXT_SECONDARY)
            score_x = badge_cx - badge_w // 2 - 16 - score_text.get_width()
            screen.blit(score_text, (score_x, card_rect.centery - score_text.get_height() // 2))

            y += card_height + gap

        screen.set_clip(None)
        total_height = y + self.scroll - (panel.y + 16)
        self._max_scroll = max(0, total_height - panel.height + 16)
        self.scroll = min(self.scroll, self._max_scroll)

        self.back_button.draw(screen)

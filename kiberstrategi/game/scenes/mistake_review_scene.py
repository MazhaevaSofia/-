# Экран «Разбор ошибок»: неверно отвеченные вопросы викторин за сессию,
# сгруппированные по технике, с прокруткой и объяснением правильного ответа.
import pygame
from ..ui.button import Button
from ..ui import theme


class MistakeReviewScene:
    def __init__(self, screen_width, screen_height, mistakes, on_close_callback):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.mistakes = mistakes
        self.on_close = on_close_callback
        self.scroll = 0
        self._max_scroll = 0

        self.font_title = theme.font(theme.FONT_XL, bold=True)
        self.font_technique = theme.font(theme.FONT_MD, bold=True)
        self.font_text = theme.font(theme.FONT_SM)

        self.close_button = Button(0, 0, 140, 38, "Закрыть", theme.ACCENT_DIM, self.on_close)
        self._position_close_button()

    def _position_close_button(self):
        self.close_button.rect.centerx = self.screen_width // 2
        self.close_button.rect.bottom = self.screen_height - 20

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self._position_close_button()

    def handle_event(self, event):
        if self.close_button.handle_event(event):
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - event.y * 40, self._max_scroll))
            return True
        return False

    def update(self):
        self.close_button.update()

    def _wrap(self, text, font, max_width):
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

    def draw(self, screen):
        screen.fill(theme.BG)

        title = self.font_title.render("Разбор ошибок", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 16))

        panel = pygame.Rect(40, 66, self.screen_width - 80, self.screen_height - 136)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)

        if not self.mistakes:
            check_center = (panel.centerx, panel.centery - 20)
            pygame.draw.circle(screen, theme.SUCCESS_DIM, check_center, 26)
            theme.draw_check(screen, check_center, size=12, color=theme.SUCCESS, width=4)
            hint = self.font_technique.render("Ни одной ошибки — отличный результат!", True, theme.TEXT_PRIMARY)
            screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.centery + 16))
        else:
            content_width = panel.width - 76
            screen.set_clip(panel)
            y = panel.y + 15 - self.scroll
            for entry in self.mistakes:
                card_top = y
                header = self.font_technique.render(entry["technique"], True, theme.ACCENT)
                q_lines = self._wrap(entry["question"], self.font_text, content_width)
                inner_h = 30 + len(q_lines) * 22 + 22 + 24
                explanation_lines = []
                if entry.get("explanation"):
                    explanation_lines = self._wrap(entry["explanation"], self.font_text, content_width - 10)
                    inner_h += len(explanation_lines) * 20
                card_rect = pygame.Rect(panel.x + 20, card_top, panel.width - 40, inner_h + 16)

                card = pygame.Surface((card_rect.width, card_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(card, theme.SURFACE_ALT, card.get_rect(), border_radius=theme.RADIUS_SM)
                screen.blit(card, card_rect.topleft)
                pygame.draw.rect(screen, theme.DANGER, (card_rect.x, card_rect.y, 4, card_rect.height), border_top_left_radius=theme.RADIUS_SM, border_bottom_left_radius=theme.RADIUS_SM)

                cy = card_top + 10
                screen.blit(header, (panel.x + 38, cy))
                cy += 28

                for line in q_lines:
                    surf = self.font_text.render(line, True, theme.TEXT_PRIMARY)
                    screen.blit(surf, (panel.x + 38, cy))
                    cy += 22

                theme.draw_cross(screen, (panel.x + 46, cy + 8), size=6, color=theme.DANGER, width=2)
                chosen = self.font_text.render(f"Ваш ответ: {entry['chosen']}", True, theme.DANGER)
                screen.blit(chosen, (panel.x + 58, cy))
                cy += 22

                theme.draw_check(screen, (panel.x + 46, cy + 8), size=6, color=theme.SUCCESS, width=2)
                correct = self.font_text.render(f"Правильно: {entry['correct']}", True, theme.SUCCESS)
                screen.blit(correct, (panel.x + 58, cy))
                cy += 26

                for line in explanation_lines:
                    surf = self.font_text.render(line, True, theme.TEXT_SECONDARY)
                    screen.blit(surf, (panel.x + 38, cy))
                    cy += 20

                y = card_rect.bottom + 14
            screen.set_clip(None)

            total_height = y + self.scroll - (panel.y + 15)
            self._max_scroll = max(0, total_height - panel.height + 15)
            self.scroll = min(self.scroll, self._max_scroll)

        self.close_button.draw(screen)

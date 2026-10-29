# Экран после прохождения уровня: переход на следующий уровень или выбор уровня
import pygame
from ..ui.button import Button
from ..ui import theme

# start_day для следующего уровня: уровень 2 -> день 3, уровень 3 -> день 6
NEXT_LEVEL_START_DAY = {2: 3, 3: 6}


class LevelCompleteScene:
    """Экран «Уровень пройден»: кнопки «Следующий уровень» и «Выбрать уровень»."""

    def __init__(self, screen_width, screen_height, game_manager, completed_level_id):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.game_manager = game_manager
        self.completed_level_id = completed_level_id
        self.font_large = theme.font(theme.FONT_XXL, bold=True)
        self.font_medium = theme.font(theme.FONT_MD)

        self.panel_w = 520
        self.panel_h = 280
        self.panel_x = (screen_width - self.panel_w) // 2
        self.panel_y = (screen_height - self.panel_h) // 2

        btn_w, btn_h = 220, 46
        cx = screen_width // 2
        btn_y = self.panel_y + 190

        self.buttons = []
        if completed_level_id < 3:
            btn_next = Button(cx - btn_w - 10, btn_y, btn_w, btn_h, "Следующий уровень", theme.SUCCESS_DIM, self._on_next_level)
            self.buttons.append(btn_next)
        btn_select = Button(cx + 10 if completed_level_id < 3 else cx - btn_w // 2, btn_y, btn_w, btn_h, "Выбрать уровень", theme.ACCENT_DIM, self._on_select_level)
        self.buttons.append(btn_select)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self.panel_x = (w - self.panel_w) // 2
        self.panel_y = (h - self.panel_h) // 2
        btn_w, btn_h = 220, 46
        cx, btn_y = w // 2, self.panel_y + 190
        if self.buttons:
            if len(self.buttons) == 2:
                self.buttons[0].rect.x, self.buttons[0].rect.y = cx - btn_w - 10, btn_y
            self.buttons[-1].rect.x = cx + 10 if len(self.buttons) == 2 else cx - btn_w // 2
            self.buttons[-1].rect.y = btn_y

    def _on_next_level(self):
        self.game_manager.mark_level_completed(self.completed_level_id)
        next_id = self.completed_level_id + 1
        start_day = NEXT_LEVEL_START_DAY[next_id]
        self.game_manager.start_level(next_id, start_day)

    def _on_select_level(self):
        self.game_manager.mark_level_completed(self.completed_level_id)
        self.game_manager.show_level_select()

    def handle_event(self, event):
        for btn in self.buttons:
            if btn.handle_event(event):
                return True
        return False

    def update(self):
        for btn in self.buttons:
            btn.update()

    def draw(self, screen):
        screen.fill(theme.BG)
        panel = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG, fill=theme.SURFACE, border=theme.BORDER)

        badge_center = (self.screen_width // 2, self.panel_y + 54)
        pygame.draw.circle(screen, theme.SUCCESS_DIM, badge_center, 26)
        theme.draw_check(screen, badge_center, size=12, color=theme.SUCCESS, width=4)

        title = self.font_large.render("Уровень пройден!", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, self.panel_y + 92))

        msg = self.font_medium.render(f"Уровень {self.completed_level_id} завершён. Что дальше?", True, theme.TEXT_SECONDARY)
        screen.blit(msg, (self.screen_width // 2 - msg.get_width() // 2, self.panel_y + 140))

        for btn in self.buttons:
            btn.draw(screen)

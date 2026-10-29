# Экран выбора режима «Атакующий vs Защитник»: хотсит вдвоём или против ИИ.
import pygame
from ..ui.button import Button
from ..ui import theme


class VersusMenuScene:
    def __init__(self, screen_width, screen_height, on_start_pvp, on_start_pve, on_back):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_back = on_back
        self.font_large = theme.font(theme.FONT_XL, bold=True)
        self.font_medium = theme.font(theme.FONT_SM)

        self.panel_w = 560
        self.panel_h = 400
        self.panel_x = (screen_width - self.panel_w) // 2
        self.panel_y = (screen_height - self.panel_h) // 2

        btn_w, btn_h = 420, 60
        cx = screen_width // 2
        self.buttons = [
            Button(cx - btn_w // 2, self.panel_y + 170, btn_w, btn_h, "Игрок против Игрока (хотсит)", theme.SUCCESS_DIM, on_start_pvp),
            Button(cx - btn_w // 2, self.panel_y + 250, btn_w, btn_h, "Игрок против ИИ", theme.DANGER_DIM, on_start_pve),
        ]
        self.back_button = Button(30, screen_height - 55, 120, 35, "Назад", theme.SURFACE_ALT, on_back)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self.panel_x = (w - self.panel_w) // 2
        self.panel_y = (h - self.panel_h) // 2
        btn_w = 420
        cx = w // 2
        for i, btn in enumerate(self.buttons):
            btn.rect.x = cx - btn_w // 2
            btn.rect.y = self.panel_y + 170 + i * 80
        self.back_button.rect.y = h - 55

    def handle_event(self, event):
        for btn in self.buttons:
            if btn.handle_event(event):
                return True
        if self.back_button.handle_event(event):
            return True
        return False

    def update(self):
        for btn in self.buttons:
            btn.update()
        self.back_button.update()

    def draw(self, screen):
        screen.fill(theme.BG)
        panel = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)

        title = self.font_large.render("Атакующий vs Защитник", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, self.panel_y + 28))
        theme.draw_divider(screen, self.panel_x + 40, self.panel_y + 66, self.panel_w - 80)

        desc = [
            "Один игрок выбирает технику атаки из уже изученных вами",
            "сценариев, второй — расследует её как обычно. Побеждает тот,",
            "чей суммарный счёт за 4 раунда выше.",
        ]
        for i, line in enumerate(desc):
            surf = self.font_medium.render(line, True, theme.TEXT_SECONDARY)
            screen.blit(surf, (self.screen_width // 2 - surf.get_width() // 2, self.panel_y + 82 + i * 22))

        for btn in self.buttons:
            btn.draw(screen)
        self.back_button.draw(screen)

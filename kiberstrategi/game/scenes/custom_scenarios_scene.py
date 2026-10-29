# Список пользовательских сценариев из папки scenarios/ (см. SCENARIO_FORMAT.md).
from ..ui.button import Button
from ..ui import theme
from ..core.scenario_loader import list_custom_scenarios


class CustomScenariosScene:
    def __init__(self, screen_width, screen_height, on_select, on_back):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_back = on_back
        self.font_large = theme.font(theme.FONT_XL, bold=True)
        self.font_medium = theme.font(theme.FONT_SM)

        self.scenarios = list_custom_scenarios()  # [(path, dict), ...]
        self.buttons = []
        btn_w, btn_h = 520, 48
        start_y = 120
        for i, (path, data) in enumerate(self.scenarios):
            cb = (lambda d=data: on_select(d))
            self.buttons.append(Button(
                screen_width // 2 - btn_w // 2, start_y + i * 60,
                btn_w, btn_h, f"{data['title']} ({data['technique']})", theme.ACCENT_DIM, cb
            ))
        self.back_button = Button(30, screen_height - 55, 120, 35, "Назад", theme.SURFACE_ALT, on_back)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        btn_w = 520
        for i, btn in enumerate(self.buttons):
            btn.rect.x = w // 2 - btn_w // 2
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
        title = self.font_large.render("Пользовательские сценарии", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 24))
        theme.draw_divider(screen, self.screen_width // 2 - 260, 64, 520)

        if not self.scenarios:
            hint_lines = [
                "Пока нет ни одного файла в папке scenarios/.",
                "Формат описан в SCENARIO_FORMAT.md — можно добавить",
                "свой уровень, не трогая код игры.",
            ]
            for i, line in enumerate(hint_lines):
                surf = self.font_medium.render(line, True, theme.TEXT_SECONDARY)
                screen.blit(surf, (self.screen_width // 2 - surf.get_width() // 2, 150 + i * 26))

        for btn in self.buttons:
            btn.draw(screen)
        self.back_button.draw(screen)

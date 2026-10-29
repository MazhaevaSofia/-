# Переход между раундами режима ПРОТИВ: выбор техники атакующим (хотсит)
# или объявление хода ИИ, затем передача устройства защитнику.
import pygame
from ..ui.button import Button
from ..ui import theme
from ..core.versus_match import TECHNIQUES


class VersusRoundIntroScene:
    def __init__(self, screen_width, screen_height, round_number, total_rounds, available_techniques, on_ready, ai_pick=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.round_number = round_number
        self.total_rounds = total_rounds
        self.available_techniques = available_techniques
        self.on_ready = on_ready
        self.ai_pick = ai_pick
        self.chosen_key = ai_pick
        self.phase = "handoff" if ai_pick else "pick"

        self.font_large = theme.font(theme.FONT_XL, bold=True)
        self.font_medium = theme.font(theme.FONT_MD)

        self.buttons = []
        if self.phase == "pick":
            self._build_pick_buttons()
        self.continue_button = Button(
            screen_width // 2 - 140, screen_height - 100, 280, 46,
            "Начать расследование", theme.SUCCESS_DIM, self._continue
        )

    def _build_pick_buttons(self):
        self.buttons = []
        btn_w, btn_h = 420, 44
        start_x = self.screen_width // 2 - btn_w // 2
        start_y = 160
        for i, key in enumerate(self.available_techniques):
            label = TECHNIQUES[key]["label"]
            self.buttons.append(Button(
                start_x, start_y + i * 54, btn_w, btn_h,
                label, theme.SURFACE_ALT, lambda k=key: self._choose(k)
            ))

    def _choose(self, key):
        self.chosen_key = key
        self.phase = "handoff"

    def _continue(self):
        self.on_ready(self.chosen_key)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self.continue_button.rect.x = w // 2 - 140
        self.continue_button.rect.y = h - 100
        if self.phase == "pick":
            btn_w = 420
            for i, btn in enumerate(self.buttons):
                btn.rect.x = w // 2 - btn_w // 2

    def handle_event(self, event):
        if self.phase == "pick":
            for btn in self.buttons:
                if btn.handle_event(event):
                    return True
            return False
        return self.continue_button.handle_event(event)

    def update(self):
        if self.phase == "pick":
            for btn in self.buttons:
                btn.update()
        else:
            self.continue_button.update()

    def draw(self, screen):
        screen.fill(theme.BG)
        header = f"Раунд {self.round_number}/{self.total_rounds}"

        if self.phase == "pick":
            title = self.font_large.render(f"{header} — Атакующий выбирает технику", True, theme.TEXT_PRIMARY)
            screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 90))
            for btn in self.buttons:
                btn.draw(screen)
            return

        panel = pygame.Rect(self.screen_width // 2 - 280, self.screen_height // 2 - 130, 560, 220)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        title = self.font_large.render(header, True, theme.ACCENT)
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 24))

        if self.ai_pick:
            label = TECHNIQUES[self.ai_pick]["label"]
            lines = [f"ИИ атакует: {label}", "", "Защитник, приготовьтесь к расследованию."]
        else:
            lines = ["Атакующий подготовил атаку.", "", "Передайте устройство Защитнику и нажмите кнопку ниже."]
        for i, line in enumerate(lines):
            surf = self.font_medium.render(line, True, theme.TEXT_SECONDARY)
            screen.blit(surf, (panel.centerx - surf.get_width() // 2, panel.y + 68 + i * 26))

        self.continue_button.draw(screen)

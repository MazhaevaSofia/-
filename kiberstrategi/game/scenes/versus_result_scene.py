# Итоги матча «Атакующий vs Защитник»: счёт по раундам и победитель.
import pygame
from ..ui.button import Button
from ..ui import theme
from ..core import sound_manager

WINNER_TEXT = {
    "attacker": "Победил Атакующий!",
    "defender": "Победил Защитник!",
    "draw": "Ничья!",
}
WINNER_COLOR = {
    "attacker": theme.DANGER,
    "defender": theme.SUCCESS,
    "draw": theme.WARNING,
}
# Защитник — привычная роль игрока в кампании, поэтому его победа звучит
# как настоящий успех, а не просто нейтральный «клик».
WINNER_SOUND = {
    "attacker": "wrong",
    "defender": "success",
    "draw": "click",
}


class VersusResultScene:
    def __init__(self, screen_width, screen_height, match, on_close, new_achievements=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.match = match
        self.new_achievements = new_achievements or []
        self.font_large = theme.font(theme.FONT_XL, bold=True)
        self.font_medium = theme.font(theme.FONT_MD)
        self.font_small = theme.font(theme.FONT_SM)

        self.close_button = Button(
            screen_width // 2 - 110, screen_height - 70, 220, 44,
            "Вернуться в меню", theme.ACCENT_DIM, on_close
        )
        sound_manager.play(WINNER_SOUND[match.winner()])

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self.close_button.rect.x = w // 2 - 110
        self.close_button.rect.y = h - 70

    def handle_event(self, event):
        return self.close_button.handle_event(event)

    def update(self):
        self.close_button.update()

    def draw(self, screen):
        screen.fill(theme.BG)
        panel = pygame.Rect(self.screen_width // 2 - 320, 40, 640, self.screen_height - 130)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        title = self.font_large.render("Итоги матча", True, theme.TEXT_PRIMARY)
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 24))

        winner = self.match.winner()
        result_text = self.font_large.render(WINNER_TEXT[winner], True, WINNER_COLOR[winner])
        screen.blit(result_text, (panel.centerx - result_text.get_width() // 2, panel.y + 66))

        score_text = self.font_medium.render(
            f"Атакующий: {self.match.attacker_score} очков   —   Защитник: {self.match.defender_score} очков",
            True, theme.TEXT_SECONDARY
        )
        screen.blit(score_text, (panel.centerx - score_text.get_width() // 2, panel.y + 106))
        theme.draw_divider(screen, panel.x + 30, panel.y + 140, panel.width - 60)

        y = panel.y + 156
        rounds_title = self.font_medium.render("По раундам:", True, theme.ACCENT)
        screen.blit(rounds_title, (panel.x + 30, y))
        y += 32
        for i, entry in enumerate(self.match.rounds_log, start=1):
            line = f"{i}. {entry['label']} — защитник набрал {entry['defender_score']}/30"
            surf = self.font_small.render(line, True, theme.TEXT_SECONDARY)
            screen.blit(surf, (panel.x + 40, y))
            y += 26

        if self.new_achievements:
            y += 10
            ach_title = self.font_medium.render("Новые достижения:", True, theme.WARNING)
            screen.blit(ach_title, (panel.x + 30, y))
            y += 28
            for title in self.new_achievements:
                surf = self.font_small.render(f"• {title}", True, theme.WARNING)
                screen.blit(surf, (panel.x + 40, y))
                y += 24

        self.close_button.draw(screen)

# Выбор уровня: Уровень 1 (уровни сложности 1–2), Уровень 2 (3–5), Уровень 3 (6–7)
import math
import os
import pygame
from ..ui.button import Button
from ..ui import theme

OFFICE_BG_NAME = "office_bg.png"


class LevelSelectScene:
    """Экран выбора уровня: сложность Стажёр (1–2), Аналитик (3–5), Эксперт (6–7)."""

    LEVELS = [
        {
            "id": 1,
            "title": "Уровень 1: Задания 1–2",
            "subtitle": "Стажёр",
            "slogan": "Каждый эксперт когда-то был стажёром",
            "days": "Фишинг · Компрометация учётных записей",
            "color": theme.LEVEL_COLORS[1],
            "start_day": 1,
        },
        {
            "id": 2,
            "title": "Уровень 2: Задания 3–5",
            "subtitle": "Аналитик",
            "slogan": "Теория без практики мертва",
            "days": "Process Injection · DNS C2 · DoS",
            "color": theme.LEVEL_COLORS[2],
            "start_day": 3,
        },
        {
            "id": 3,
            "title": "Уровень 3: Задания 6–7",
            "subtitle": "Эксперт",
            "slogan": "Хакеры не спят — не спи и ты",
            "days": "Meterpreter · Брутфорс SSH",
            "color": theme.LEVEL_COLORS[3],
            "start_day": 6,
        },
    ]

    def __init__(self, screen_width, screen_height, game_manager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.game_manager = game_manager
        self.font_title = theme.font(theme.FONT_XXL, bold=True)
        self.font_subtitle = theme.font(theme.FONT_MD)
        self.font_slogan = theme.font(theme.FONT_SM)
        self.font_days = theme.font(theme.FONT_XS)
        self.font_foot = theme.font(theme.FONT_XS)

        # Фон: office_bg.png из папки assets, затемняем для контраста тёмной карточки
        self._bg_surface = None
        self._bg_original = None
        base = os.path.dirname(os.path.abspath(__file__))
        for rel in [os.path.join(base, "..", "assets", OFFICE_BG_NAME), os.path.join(base, "..", "..", "assets", OFFICE_BG_NAME)]:
            if os.path.exists(rel):
                try:
                    self._bg_original = pygame.image.load(rel).convert()
                    self._rebuild_bg(screen_width, screen_height)
                    break
                except Exception:
                    pass
        if self._bg_surface is None:
            self._bg_fill = theme.BG
        else:
            self._bg_fill = None

        self.panel_w = 720
        self.panel_h = 610
        self.panel_x = (screen_width - self.panel_w) // 2
        self.panel_y = (screen_height - self.panel_h) // 2

        self.buttons = []
        btn_w, btn_h = 420, 58
        start_y = self.panel_y + 150
        step = 108

        for i, lev in enumerate(self.LEVELS):
            btn_x = (screen_width - btn_w) // 2
            btn_y = start_y + i * step
            cb = (lambda d=lev["start_day"], lid=lev["id"]: self._on_level(lid, d))
            btn = Button(btn_x, btn_y, btn_w, btn_h, lev["title"], lev["color"], cb)
            self.buttons.append(btn)

        # Режим «Атакующий vs Защитник» и пользовательские сценарии —
        # доступны независимо от прогресса кампании
        self.versus_button = Button(
            screen_width - 210, 16, 190, 34,
            "Режим ПРОТИВ", (150, 55, 55), self.game_manager.show_versus_menu
        )
        self.custom_scenarios_button = Button(
            screen_width - 210, 56, 190, 34,
            "Свои сценарии", theme.ACCENT_DIM, self.game_manager.show_custom_scenarios
        )
        self.achievements_button = Button(
            screen_width - 210, 96, 190, 34,
            "Достижения", (150, 120, 40), self.game_manager.show_achievements
        )
        self.case_board_button = Button(
            screen_width - 210, 136, 190, 34,
            "Доска расследований", theme.SURFACE_ALT, self.game_manager.show_case_board
        )
        self.phishing_button = Button(
            screen_width - 210, 176, 190, 34,
            "Фишинг-детектор", (25, 110, 110), self.game_manager.show_phishing_detector
        )
        self.password_button = Button(
            screen_width - 210, 216, 190, 34,
            "Лаборатория паролей", (90, 70, 150), self.game_manager.show_password_lab
        )
        self.boss_button = Button(
            (screen_width - 420) // 2, self.panel_y + 486, 420, 52,
            "БОСС: Операция «Чёрный лёд»", (130, 35, 48), self.game_manager.show_boss_level,
            font=theme.font(theme.FONT_MD, bold=True)
        )

    def _rebuild_bg(self, w, h):
        scaled = pygame.transform.smoothscale(self._bg_original, (w, h))
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*theme.BG, 130))
        scaled.blit(overlay, (0, 0))
        self._bg_surface = scaled

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if self._bg_original:
            self._rebuild_bg(w, h)
        self.panel_x = (w - self.panel_w) // 2
        self.panel_y = (h - self.panel_h) // 2
        start_y = self.panel_y + 150
        step = 108
        btn_w, btn_h = 420, 58
        for i, btn in enumerate(self.buttons):
            btn.rect.x = (w - btn_w) // 2
            btn.rect.y = start_y + i * step
        self.versus_button.rect.x = w - 210
        self.custom_scenarios_button.rect.x = w - 210
        self.achievements_button.rect.x = w - 210
        self.case_board_button.rect.x = w - 210
        self.phishing_button.rect.x = w - 210
        self.password_button.rect.x = w - 210
        self.boss_button.rect.x = (w - 420) // 2
        self.boss_button.rect.y = self.panel_y + 486

    def _on_level(self, level_id, start_day):
        self.game_manager.start_level(level_id, start_day)

    def handle_event(self, event):
        if self.versus_button.handle_event(event):
            return True
        if self.custom_scenarios_button.handle_event(event):
            return True
        if self.achievements_button.handle_event(event):
            return True
        if self.case_board_button.handle_event(event):
            return True
        if self.phishing_button.handle_event(event):
            return True
        if self.password_button.handle_event(event):
            return True
        if self.boss_button.handle_event(event):
            return True
        completed = getattr(self.game_manager, "completed_levels", set())
        for i, btn in enumerate(self.buttons):
            if self.LEVELS[i]["id"] in completed:
                continue
            if btn.handle_event(event):
                return True
        return False

    def update(self):
        for btn in self.buttons:
            btn.update()
        self.versus_button.update()
        self.custom_scenarios_button.update()
        self.achievements_button.update()
        self.case_board_button.update()
        self.phishing_button.update()
        self.password_button.update()
        self.boss_button.update()

    def draw(self, screen):
        if self._bg_surface is not None:
            screen.blit(self._bg_surface, (0, 0))
        else:
            screen.fill(self._bg_fill)

        panel = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        card = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        pygame.draw.rect(card, (*theme.SURFACE, 235), card.get_rect(), border_radius=theme.RADIUS_LG)
        pygame.draw.rect(card, theme.BORDER, card.get_rect(), 1, border_radius=theme.RADIUS_LG)
        shadow = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=theme.RADIUS_LG)
        screen.blit(shadow, (panel.x, panel.y + 6))
        screen.blit(card, panel.topleft)

        title = self.font_title.render("Киберстратегия: Битва за данные", True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, self.panel_y + 26))
        theme.draw_divider(screen, self.panel_x + 40, self.panel_y + 70, self.panel_w - 80)

        sub = self.font_subtitle.render("Выберите уровень", True, theme.TEXT_SECONDARY)
        screen.blit(sub, (self.screen_width // 2 - sub.get_width() // 2, self.panel_y + 84))

        completed = getattr(self.game_manager, "completed_levels", set())
        for i, (lev, btn) in enumerate(zip(self.LEVELS, self.buttons)):
            is_done = lev["id"] in completed
            btn.draw(screen, disabled=is_done)
            if is_done:
                theme.draw_check(screen, (btn.rect.x + 22, btn.rect.centery), size=8)

            y_desc = btn.rect.y + btn.rect.height + 6
            slogan = self.font_slogan.render(lev["slogan"], True, theme.TEXT_SECONDARY)
            screen.blit(slogan, (self.screen_width // 2 - slogan.get_width() // 2, y_desc))
            days = self.font_days.render(lev["days"], True, theme.TEXT_MUTED)
            screen.blit(days, (self.screen_width // 2 - days.get_width() // 2, y_desc + 22))

        foot = self.font_foot.render("1–2: Стажёр  ·  3–5: Аналитик  ·  6–7: Эксперт", True, theme.TEXT_MUTED)
        screen.blit(foot, (self.screen_width // 2 - foot.get_width() // 2, self.panel_y + self.panel_h - 30))

        self.versus_button.draw(screen)
        self.custom_scenarios_button.draw(screen)
        self.achievements_button.draw(screen)
        self.case_board_button.draw(screen)
        self.phishing_button.draw(screen)
        self.password_button.draw(screen)
        self._draw_boss_button(screen)

    def _draw_boss_button(self, screen):
        btn = self.boss_button
        btn.draw(screen)
        pulse = (math.sin(pygame.time.get_ticks() / 380.0) + 1) / 2
        glow = pygame.Surface((btn.rect.width + 16, btn.rect.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*theme.DANGER, int(30 + 70 * pulse)), glow.get_rect(), 2, border_radius=theme.RADIUS_MD + 4)
        screen.blit(glow, (btn.rect.x - 8, btn.rect.y - 8))
        sm = self.game_manager.save_manager
        done = len(getattr(self.game_manager, "completed_levels", set()))
        status = f"Финальный инцидент  ·  Допуск {done} из 3"
        if sm.boss_attempts:
            status += f"  ·  Рекорд: {sm.boss_best_grade} {sm.boss_best_score}"
        surf = self.font_days.render(status, True, theme.TEXT_MUTED)
        screen.blit(surf, (self.screen_width // 2 - surf.get_width() // 2, btn.rect.bottom + 8))

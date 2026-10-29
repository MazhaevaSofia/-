# credits_scene.py
import os
import pygame
from ..ui import theme
from ..core.endings import ending_for_percent
from ..core import sound_manager

ENDING_COLOR_BY_TAG = {
    "success": theme.SUCCESS,
    "warning": theme.WARNING,
    "danger": theme.DANGER,
}


class CreditsScene:
    def __init__(self, screen_width, screen_height, on_submit_callback, on_quit_callback=None, total_score=0, max_score=210, best_score=None, on_review_mistakes_callback=None, new_achievements=None, unlocked_achievement_ids=None, new_achievement_ids=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_submit_callback = on_submit_callback
        self.on_quit_callback = on_quit_callback
        self.total_score = total_score
        self.max_score = max_score
        self.best_score = best_score
        self.on_review_mistakes_callback = on_review_mistakes_callback
        self.new_achievements = new_achievements or []
        self.unlocked_achievement_ids = unlocked_achievement_ids or []
        self.new_achievement_ids = new_achievement_ids or []
        self.card_saved_path = None
        self._card_button_hover = False
        
        self.submitted = False
        self.saved_username = ""
        self.saved_percent = 0.0
        
        self.font_title = theme.font(theme.FONT_XXL, bold=True)
        self.font_section = theme.font(theme.FONT_LG)
        self.font_item = theme.font(theme.FONT_MD)
        self.font_hint = theme.font(theme.FONT_SM)
        self.font_small = theme.font(theme.FONT_SM)
        
        # Титры: (заголовок секции, список имён/строк)
        self.sections = [
            ("Разработка", ["Ваша команда"]),
            ("Музыка и звук", ["Ваши композиторы"]),
            ("Оформление", ["Ваши художники"]),
        ]
        self.footer_text = "Благодарим за игру!"
        
        # Панель с титрами: фиксированный размер под её реальное содержимое —
        # остальные элементы выстраиваются от её нижнего края, а не от низа
        # экрана, чтобы между ними не было пустого провала.
        self.panel_width = min(480, screen_width - 40)
        self.panel_y = 40
        self.panel_height = 300

        # Блок ввода — сразу под панелью титров
        self.input_text = ""
        self.input_rect = pygame.Rect(0, 0, min(320, screen_width - 80), 38)
        self.input_rect.centerx = screen_width // 2
        self.input_rect.top = self.panel_y + self.panel_height + 56
        self.input_active = True
        self.submit_button = pygame.Rect(0, 0, 150, 40)
        self.submit_button.centerx = screen_width // 2
        self.submit_button.top = self.input_rect.bottom + 14
        self.submit_text = self.font_section.render("Продолжить", True, (255, 255, 255))
        self.hint_text = "Введите имя и нажмите Продолжить"
        
        # Кнопка "Закрыть игру" (показывается после отправки)
        self.close_button = pygame.Rect(0, 0, 160, 38)
        self.close_button.bottom = screen_height - 50
        self.close_text = self.font_section.render("Закрыть игру", True, (255, 255, 255))
        self._close_button_hover = False

        # Кнопка "Разбор ошибок" (только если есть что показать)
        self.review_button = pygame.Rect(0, 0, 160, 38)
        self.review_button.bottom = screen_height - 50
        self.review_text = self.font_section.render("Разбор ошибок", True, (255, 255, 255))
        self._review_button_hover = False

        # Кнопка "Скачать карточку" — шаринг-карточка результата (см. game/core/result_card.py)
        self.card_button = pygame.Rect(0, 0, 190, 38)
        self.card_button.bottom = screen_height - 50
        self.card_text = self.font_small.render("Скачать карточку", True, (255, 255, 255))

        self._layout_result_buttons(screen_width)
        
        # Цвета
        self.bg_color = theme.BG
        self.panel_color = theme.SURFACE
        self.title_color = theme.TEXT_PRIMARY
        self.section_color = theme.TEXT_PRIMARY
        self.item_color = theme.TEXT_SECONDARY
        self.border_color = theme.BORDER
        self.input_bg = theme.SURFACE_ALT
        self.button_color = theme.ACCENT_DIM
        self.button_hover = theme.ACCENT_STRONG
        self._button_hover = False

    def _show_review_button(self):
        return bool(self.on_review_mistakes_callback)

    def _layout_result_buttons(self, w):
        """Центрирует нижний ряд кнопок (разбор ошибок — опционально, карточка, закрыть)."""
        buttons = []
        if self._show_review_button():
            buttons.append(self.review_button)
        buttons.append(self.card_button)
        buttons.append(self.close_button)
        gap = 14
        total_width = sum(b.width for b in buttons) + gap * (len(buttons) - 1)
        x = w // 2 - total_width // 2
        for b in buttons:
            b.centerx = x + b.width // 2
            x += b.width + gap

    def handle_event(self, event):
        if self.submitted:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.close_button.collidepoint(event.pos):
                    if self.on_quit_callback:
                        self.on_quit_callback()
                elif self._show_review_button() and self.review_button.collidepoint(event.pos):
                    self.on_review_mistakes_callback()
                elif self.card_button.collidepoint(event.pos):
                    self._save_result_card()
            return
        if event.type == pygame.KEYDOWN:
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    self.submit_input()
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    self.input_text += event.unicode
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.submit_button.collidepoint(event.pos):
                self.submit_input()
            if self.input_rect.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False
    
    def submit_input(self):
        percent = round(self.total_score / self.max_score * 100, 1) if self.max_score else 0
        username = self.input_text.strip() or "Игрок"
        self.saved_username = username
        self.saved_percent = percent
        self.submitted = True
        sound_manager.play("success")

    def _save_result_card(self):
        """Сгенерировать и сохранить PNG-карточку результата (см. game/core/result_card.py)."""
        from ..core.result_card import render_result_card, save_result_card
        try:
            surface = render_result_card(
                self.saved_username, self.total_score, self.max_score,
                self.unlocked_achievement_ids, self.new_achievement_ids
            )
            self.card_saved_path = save_result_card(surface)
        except OSError:
            self.card_saved_path = None
    
    def update(self):
        try:
            pos = pygame.mouse.get_pos()
            if self.submitted:
                self._close_button_hover = self.close_button.collidepoint(pos)
                self._review_button_hover = self._show_review_button() and self.review_button.collidepoint(pos)
                self._card_button_hover = self.card_button.collidepoint(pos)
            else:
                self._button_hover = self.submit_button.collidepoint(pos)
        except Exception:
            self._button_hover = False
            self._close_button_hover = False
    
    def draw(self, screen):
        screen.fill(self.bg_color)
        
        if self.submitted:
            self._draw_result(screen)
            return
        
        panel_width = self.panel_width
        panel_x = (self.screen_width - panel_width) // 2
        panel_y = self.panel_y
        panel_height = self.panel_height
        panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG, fill=self.panel_color, border=self.border_color)
        
        # Заголовок (обрезаем по ширине панели)
        title_raw = "КИБЕРБЕЗОПАСНОСТЬ: РАССЛЕДОВАНИЕ"
        title_surface = self.font_title.render(title_raw, True, self.title_color)
        if title_surface.get_width() > panel_width - 40:
            title_surface = self.font_section.render(title_raw, True, self.title_color)
        if title_surface.get_width() > panel_width - 40:
            title_surface = self.font_item.render(title_raw, True, self.title_color)
        title_rect = title_surface.get_rect(center=(self.screen_width // 2, panel_y + 36))
        screen.blit(title_surface, title_rect)
        
        # Секции титров
        y = panel_y + 64
        line_h = 24
        for section_title, items in self.sections:
            if y > panel_y + panel_height - 50:
                break
            section_surface = self.font_section.render(section_title + ":", True, self.section_color)
            screen.blit(section_surface, (panel_x + 24, y))
            y += 28
            for line in items:
                if y > panel_y + panel_height - 40:
                    break
                item_surface = self.font_item.render("  " + line, True, self.item_color)
                screen.blit(item_surface, (panel_x + 24, y))
                y += line_h
            y += 8
        
        # Подпись внизу панели
        footer_surface = self.font_item.render(self.footer_text, True, self.item_color)
        footer_rect = footer_surface.get_rect(center=(self.screen_width // 2, panel_y + panel_height - 24))
        screen.blit(footer_surface, footer_rect)
        
        # Подсказка над полем ввода
        hint_surface = self.font_hint.render(self.hint_text, True, (140, 150, 170))
        hint_rect = hint_surface.get_rect(center=(self.screen_width // 2, self.input_rect.top - 16))
        screen.blit(hint_surface, hint_rect)
        
        # Поле ввода и текст (обрезаем длинное имя по ширине)
        pygame.draw.rect(screen, self.input_bg, self.input_rect, border_radius=6)
        pygame.draw.rect(screen, self.border_color, self.input_rect, 2, border_radius=6)
        pad_x = 10
        max_w = max(0, self.input_rect.width - 2 * pad_x)
        if self.input_text or self.input_active:
            text = self.input_text if self.input_text else ""
            input_surface = self.font_item.render(text, True, self.title_color)
            if input_surface.get_width() > max_w:
                while len(text) > 1 and self.font_item.render(text + "...", True, self.title_color).get_width() > max_w:
                    text = text[:-1]
                text = text.rstrip() + "..." if len(text) < len(self.input_text) else text
                input_surface = self.font_item.render(text, True, self.title_color)
            screen.blit(input_surface, (self.input_rect.x + pad_x, self.input_rect.y + 8))
        else:
            placeholder = self.font_item.render("Имя пользователя", True, (100, 110, 130))
            if placeholder.get_width() > max_w:
                placeholder = self.font_small.render("Имя", True, (100, 110, 130))
            screen.blit(placeholder, (self.input_rect.x + pad_x, self.input_rect.y + 8))
        
        # Кнопка
        btn_color = self.button_hover if self._button_hover else self.button_color
        pygame.draw.rect(screen, btn_color, self.submit_button, border_radius=6)
        pygame.draw.rect(screen, self.border_color, self.submit_button, 1, border_radius=6)
        submit_text_rect = self.submit_text.get_rect(center=self.submit_button.center)
        screen.blit(self.submit_text, submit_text_rect)
    
    def _draw_result(self, screen):
        """Экран результата: всё помещается, длинное имя обрезается."""
        panel_width = min(440, self.screen_width - 40)
        max_text_w = panel_width - 40

        ending_tag, ending_title, ending_description = ending_for_percent(self.saved_percent)
        ending_color = ENDING_COLOR_BY_TAG[ending_tag]
        ending_desc_lines = self._wrap_text(ending_description, self.font_small, max_text_w)

        # Высота считается по реальному содержимому — концовка не всегда
        # занимает одинаково места (описание переносится по-разному).
        content_height = 36 + 30 + 32 + 28 + 28  # результат + концовка + игрок + баллы + выполнено
        content_height += len(ending_desc_lines) * 20 + 6
        if self.best_score is not None:
            content_height += 24
        if self.new_achievements:
            content_height += 24
        panel_height = min(content_height + 40, self.screen_height - 120)

        panel_x = (self.screen_width - panel_width) // 2
        panel_y = max(20, (self.screen_height - panel_height) // 2 - 30)
        panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG, fill=self.panel_color, border=self.border_color)

        y = panel_y + 20
        result_title = self.font_title.render("Результат", True, self.title_color)
        if result_title.get_width() > max_text_w:
            result_title = self.font_section.render("Результат", True, self.title_color)
        screen.blit(result_title, result_title.get_rect(center=(self.screen_width // 2, y)))
        y += 34

        ending_title_surface = self.font_section.render(ending_title, True, ending_color)
        if ending_title_surface.get_width() > max_text_w:
            ending_title_surface = self.font_small.render(ending_title, True, ending_color)
        screen.blit(ending_title_surface, ending_title_surface.get_rect(center=(self.screen_width // 2, y)))
        y += 26
        for line in ending_desc_lines:
            line_surface = self.font_small.render(line, True, self.item_color)
            screen.blit(line_surface, line_surface.get_rect(center=(self.screen_width // 2, y)))
            y += 20
        y += 10

        name_text = f"Игрок: {self.saved_username}"
        name_surface = self.font_section.render(name_text, True, self.section_color)
        if name_surface.get_width() > max_text_w:
            short = self.saved_username
            while len(short) > 1 and self.font_section.render("Игрок: " + short + "...", True, self.section_color).get_width() > max_text_w:
                short = short[:-1]
            name_text = "Игрок: " + (short.rstrip() + "..." if len(short) < len(self.saved_username) else short)
            name_surface = self.font_section.render(name_text, True, self.section_color)
        screen.blit(name_surface, name_surface.get_rect(center=(self.screen_width // 2, y)))
        y += 28

        score_text = f"Баллы: {self.total_score} из {self.max_score}"
        score_surface = self.font_section.render(score_text, True, self.section_color)
        if score_surface.get_width() > max_text_w:
            score_surface = self.font_small.render(score_text, True, self.section_color)
        screen.blit(score_surface, score_surface.get_rect(center=(self.screen_width // 2, y)))
        y += 28

        percent_text = f"Выполнено: {self.saved_percent}%"
        percent_surface = self.font_section.render(percent_text, True, self.section_color)
        screen.blit(percent_surface, percent_surface.get_rect(center=(self.screen_width // 2, y)))
        y += 28

        if self.best_score is not None:
            record_text = f"Рекорд: {self.best_score}"
            record_surface = self.font_small.render(record_text, True, (200, 170, 60))
            screen.blit(record_surface, record_surface.get_rect(center=(self.screen_width // 2, y)))
            y += 24

        if self.new_achievements:
            ach_text = "Новые достижения: " + ", ".join(self.new_achievements)
            ach_surface = self.font_small.render(ach_text, True, theme.WARNING)
            if ach_surface.get_width() > max_text_w:
                ach_text = f"Новых достижений: {len(self.new_achievements)}"
                ach_surface = self.font_small.render(ach_text, True, theme.WARNING)
            screen.blit(ach_surface, ach_surface.get_rect(center=(self.screen_width // 2, y)))
            y += 24

        close_btn_color = self.button_hover if self._close_button_hover else self.button_color
        pygame.draw.rect(screen, close_btn_color, self.close_button, border_radius=6)
        pygame.draw.rect(screen, self.border_color, self.close_button, 1, border_radius=6)
        close_text_rect = self.close_text.get_rect(center=self.close_button.center)
        screen.blit(self.close_text, close_text_rect)

        if self._show_review_button():
            review_btn_color = self.button_hover if self._review_button_hover else self.button_color
            pygame.draw.rect(screen, review_btn_color, self.review_button, border_radius=6)
            pygame.draw.rect(screen, self.border_color, self.review_button, 1, border_radius=6)
            review_text_rect = self.review_text.get_rect(center=self.review_button.center)
            screen.blit(self.review_text, review_text_rect)

        card_btn_color = self.button_hover if self._card_button_hover else self.button_color
        pygame.draw.rect(screen, card_btn_color, self.card_button, border_radius=6)
        pygame.draw.rect(screen, self.border_color, self.card_button, 1, border_radius=6)
        card_text_rect = self.card_text.get_rect(center=self.card_button.center)
        screen.blit(self.card_text, card_text_rect)

        if self.card_saved_path is not None:
            status_font = theme.font(theme.FONT_XS)
            status_text = f"Карточка сохранена: {os.path.basename(os.path.dirname(self.card_saved_path))}/{os.path.basename(self.card_saved_path)}"
            status_surface = status_font.render(status_text, True, theme.SUCCESS)
            if status_surface.get_width() > self.screen_width - 40:
                status_surface = status_font.render("Карточка сохранена", True, theme.SUCCESS)
            status_rect = status_surface.get_rect(center=(self.screen_width // 2, self.close_button.top - 18))
            screen.blit(status_surface, status_rect)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self.panel_width = min(480, w - 40)
        self.input_rect.w = min(320, w - 80)
        self.input_rect.centerx = w // 2
        self.input_rect.top = self.panel_y + self.panel_height + 56
        self.submit_button.centerx = w // 2
        self.submit_button.top = self.input_rect.bottom + 14
        self.close_button.bottom = h - 50
        self.review_button.bottom = h - 50
        self.card_button.bottom = h - 50
        self._layout_result_buttons(w)

    @staticmethod
    def _wrap_text(text, font, max_width):
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

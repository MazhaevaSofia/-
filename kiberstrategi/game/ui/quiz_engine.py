"""Общий движок финального теста после сценария-расследования.

Раньше этот код (перемешивание вариантов, подсчёт очков, отрисовка
кнопок и результата) был продублирован почти дословно в каждом файле
game/scenes/*_minigame.py. Теперь каждая сцена создаёт один объект
QuizEngine и делегирует ему handle_event/update/draw, пока идёт тест.
"""
import random

import pygame

from .button import Button
from . import theme
from ..core import sound_manager

POINTS_PER_CORRECT = 10


class QuizEngine:
    def __init__(self, screen_width, screen_height, questions, title):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.questions = questions
        self.title = title

        self.font_large = theme.font(theme.FONT_XL, bold=True)
        self.font_medium = theme.font(theme.FONT_MD)
        self.font_small = theme.font(theme.FONT_SM)

        self.current_index = 0
        self.score = 0
        self.correct_count = 0
        self.answered = False
        self.selected_answer = None
        self.finished = False
        # Вопросы, отвеченные неверно — для системы анализа ошибок игрока
        self.mistakes = []

        self._correct_option = None
        self.buttons = []
        self.next_button = Button(
            screen_width - 190, screen_height - 130,
            130, 40, "Далее", theme.ACCENT_DIM, self._go_next
        )
        self._build_buttons()

    @property
    def total_questions(self):
        return len(self.questions)

    @property
    def max_score(self):
        return len(self.questions) * POINTS_PER_CORRECT

    def _build_buttons(self):
        self.buttons = []
        question = self.questions[self.current_index]
        options = list(question["options"])
        correct_value = options[question["correct"]]
        random.shuffle(options)
        self._correct_option = options.index(correct_value)

        button_width, button_height = 520, 40
        start_x = self.screen_width // 2 - button_width // 2
        start_y = 350
        for i, option in enumerate(options):
            self.buttons.append(Button(
                start_x, start_y + i * 50,
                button_width, button_height,
                option, theme.SURFACE_ALT, lambda idx=i: self._answer(idx)
            ))

    def _answer(self, index):
        if self.answered:
            return
        self.selected_answer = index
        self.answered = True
        question = self.questions[self.current_index]
        if index == self._correct_option:
            self.score += POINTS_PER_CORRECT
            self.correct_count += 1
            sound_manager.play("correct")
        else:
            sound_manager.play("wrong")
            self.mistakes.append({
                "question": question["question"],
                "chosen": self.buttons[index].text,
                "correct": self.buttons[self._correct_option].text,
                "explanation": question.get("explanation", ""),
            })

    def _go_next(self):
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            self.answered = False
            self.selected_answer = None
            self._build_buttons()
        else:
            self.finished = True

    def handle_event(self, event):
        if self.finished:
            return False
        if not self.answered:
            for button in self.buttons:
                if button.handle_event(event):
                    return True
        else:
            if self.next_button.handle_event(event):
                return True
        return False

    def update(self):
        if self.finished:
            return
        if not self.answered:
            for button in self.buttons:
                button.update()
        else:
            self.next_button.update()

    def on_resize(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.next_button.rect.topleft = (screen_width - 190, screen_height - 130)

    def draw(self, screen):
        quiz_bg = pygame.Rect(50, 70, self.screen_width - 100, self.screen_height - 150)
        theme.draw_panel(screen, quiz_bg, radius=theme.RADIUS_LG)

        question = self.questions[self.current_index]

        title = self.font_large.render(self.title, True, theme.TEXT_PRIMARY)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 92))

        self._draw_progress_dots(screen, (self.screen_width // 2, 138))

        question_surface = self.font_medium.render(question["question"], True, theme.ACCENT)
        screen.blit(question_surface, (self.screen_width // 2 - question_surface.get_width() // 2, 168))

        if not self.answered:
            for button in self.buttons:
                button.draw(screen)
            return

        for i, button in enumerate(self.buttons):
            if i == self._correct_option:
                self._draw_option_frame(screen, button.rect, theme.SUCCESS)
            elif i == self.selected_answer:
                self._draw_option_frame(screen, button.rect, theme.DANGER)
            button.draw(screen)
            if i == self._correct_option:
                theme.draw_check(screen, (button.rect.x - 16, button.rect.centery), size=7, color=theme.SUCCESS)
            elif i == self.selected_answer:
                theme.draw_cross(screen, (button.rect.x - 16, button.rect.centery), size=6, color=theme.DANGER)

        is_correct = self.selected_answer == self._correct_option
        result_color = theme.SUCCESS if is_correct else theme.DANGER
        result_text = "ВЕРНО!" if is_correct else "НЕВЕРНО"
        result = self.font_large.render(result_text, True, result_color)
        screen.blit(result, (self.screen_width // 2 - result.get_width() // 2, 300))

        explanation = question.get("explanation")
        if explanation:
            self._draw_explanation(screen, explanation)

        self.next_button.draw(screen)

    def _draw_progress_dots(self, screen, center):
        n = self.total_questions
        spacing = 18
        start_x = center[0] - (n - 1) * spacing // 2
        for i in range(n):
            x = start_x + i * spacing
            if i < self.current_index:
                pygame.draw.circle(screen, theme.SUCCESS, (x, center[1]), 5)
            elif i == self.current_index:
                pygame.draw.circle(screen, theme.ACCENT, (x, center[1]), 6)
            else:
                pygame.draw.circle(screen, theme.BORDER, (x, center[1]), 5, 1)

    @staticmethod
    def _draw_option_frame(screen, rect, color):
        frame = pygame.Rect(rect.x - 4, rect.y - 4, rect.width + 8, rect.height + 8)
        pygame.draw.rect(screen, color, frame, 2, border_radius=theme.RADIUS_MD + 2)

    def _draw_explanation(self, screen, explanation):
        max_width = self.screen_width - 160
        lines = self._wrap_text(explanation, self.font_small, max_width)
        box_rect = pygame.Rect(70, 500, self.screen_width - 140, 30 + len(lines) * 20)
        box_rect.height = min(box_rect.height, self.screen_height - 150 - box_rect.y)

        card = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(card, theme.SURFACE_ALT, card.get_rect(), border_radius=theme.RADIUS_SM)
        screen.blit(card, box_rect.topleft)
        pygame.draw.rect(screen, theme.ACCENT, (box_rect.x, box_rect.y, 4, box_rect.height), border_top_left_radius=theme.RADIUS_SM, border_bottom_left_radius=theme.RADIUS_SM)

        label = theme.font(theme.FONT_SM, bold=True).render("Пояснение", True, theme.ACCENT)
        screen.blit(label, (box_rect.x + 16, box_rect.y + 7))

        y = box_rect.y + 7 + label.get_height() + 3
        for line in lines:
            if y > box_rect.bottom - 18:
                break
            surf = self.font_small.render(line, True, theme.TEXT_SECONDARY)
            screen.blit(surf, (box_rect.x + 16, y))
            y += 20

    @staticmethod
    def _wrap_text(text, font, max_width):
        words = text.split(" ")
        lines = []
        current = ""
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

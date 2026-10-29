# Универсальная сцена расследования, целиком управляемая данными сценария
# (см. SCENARIO_FORMAT.md). Позволяет преподавателям добавлять новые уровни
# без изменения кода Python — визуально и по структуре повторяет 7
# «встроенных» сценариев, но берёт всё содержимое из JSON.
import pygame
from ..ui.button import Button
from ..ui import theme
from ..ui.quiz_engine import QuizEngine
from .command_prompt_common import get_blurred_background, create_back_button


class DataDrivenInvestigationScene:
    def __init__(self, screen_width, screen_height, scenario, on_complete_callback):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scenario = scenario
        self.on_complete = on_complete_callback

        self.completed_steps = []
        self.current_step = None
        self.show_command_prompt = False
        self.command_text = ""
        self.command_success = False
        self.command_history = []
        self.analysis_scroll = 0
        self._cmd_blurred_bg = get_blurred_background(screen_width, screen_height)
        self.command_back_button = create_back_button(screen_width, screen_height, self._close_command_prompt)

        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        self.font_mono = pygame.font.Font(None, 18)

        self.buttons = []
        self._create_buttons()

        self.show_final_quiz = False
        self.quiz = None
        self.show_report = False
        self.show_tutorial = True
        self.tutorial_close_rect = None

    def _create_buttons(self):
        button_width, button_height = 380, 35
        start_x = 50
        start_y = 200

        self.buttons = []
        for i, step in enumerate(self.scenario["analysis_steps"]):
            self.buttons.append(Button(
                start_x, start_y + i * 45, button_width, button_height,
                step["button_label"], theme.ACCENT, lambda s=step["id"]: self._open_step(s)
            ))
        unlock = self.scenario["unlock_action"]
        self.buttons.append(Button(
            start_x, start_y + len(self.scenario["analysis_steps"]) * 45 + 20,
            button_width, button_height,
            unlock["button_label"], (200, 0, 0), self._open_command_prompt
        ))

        self.back_button = Button(50, self.screen_height - 55, 120, 35, "Назад", (20, 120, 100), self._back_to_main)
        self.exit_to_desktop_button = Button(
            self.screen_width - 130, 20, 110, 36, "Назад", (120, 120, 120),
            lambda: self.on_complete(False)
        )

    def _step_by_id(self, step_id):
        return next(s for s in self.scenario["analysis_steps"] if s["id"] == step_id)

    def _open_step(self, step_id):
        self.current_step = step_id
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)

    def _back_to_main(self):
        self.current_step = None

    def _open_command_prompt(self):
        self.show_command_prompt = True
        self.command_text = ""
        self.command_success = False
        self.command_history = []

    def _close_command_prompt(self):
        self.show_command_prompt = False

    def _handle_command(self, command):
        unlock = self.scenario["unlock_action"]
        cmd = command.strip().lower()
        if cmd == "skip" or cmd == unlock["success_command"].strip().lower():
            self.command_success = True
            self.completed_steps.append(unlock["success_message"])
            self.show_command_prompt = False
            self.show_final_quiz = True
            title = f"ФИНАЛЬНЫЙ ТЕСТ — {self.scenario['title']}"
            self.quiz = QuizEngine(self.screen_width, self.screen_height, self.scenario["quiz"]["questions"], title)
            return True
        return False

    def handle_event(self, event):
        if self.show_tutorial and event.type == pygame.MOUSEBUTTONDOWN:
            if self.tutorial_close_rect and self.tutorial_close_rect.collidepoint(event.pos):
                self.show_tutorial = False
                return True
        if self.show_report:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.on_complete(True, self.quiz.score, self.quiz.mistakes)
                return True
            return False

        if self.show_final_quiz:
            handled = self.quiz.handle_event(event)
            if self.quiz.finished:
                self.show_final_quiz = False
                self.show_report = True
            return handled

        if self.show_command_prompt:
            if self.command_back_button.handle_event(event):
                return True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self._handle_command(self.command_text)
                    self.command_history.append(f"C:\\Windows\\System32>{self.command_text}")
                    self.command_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.command_text = self.command_text[:-1]
                else:
                    self.command_text += event.unicode
                return True
            return False

        if self.current_step is not None:
            if event.type == pygame.MOUSEWHEEL:
                step = self._step_by_id(self.current_step)
                line_height, empty_height = 25, 10
                total_h = sum(empty_height if line == "" else line_height for line in step["content"])
                visible_h = (self.screen_height - 200) - 60
                max_scroll = max(0, total_h - visible_h)
                self.analysis_scroll = max(0, min(self.analysis_scroll - event.y * 40, max_scroll))
                return True
            if self.back_button.handle_event(event):
                return True
            if self.exit_to_desktop_button.handle_event(event):
                return True
        else:
            if self.exit_to_desktop_button.handle_event(event):
                return True
            for button in self.buttons:
                if button.handle_event(event):
                    return True
        return False

    def update(self):
        if self.show_command_prompt:
            self.command_back_button.update()
        if self.current_step is not None:
            self.back_button.update()
            self.exit_to_desktop_button.update()
        else:
            self.exit_to_desktop_button.update()
            for button in self.buttons:
                button.update()
        if self.show_final_quiz:
            self.quiz.update()

    def draw(self, screen):
        screen.fill(theme.BG)
        title = self.font_large.render(f"РАССЛЕДОВАНИЕ: {self.scenario['technique']}", True, (255, 255, 255))
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 20))

        if self.show_report:
            self._draw_report(screen)
        elif self.show_final_quiz:
            self.quiz.draw(screen)
        elif self.show_command_prompt:
            self._draw_command_prompt(screen)
        elif self.current_step is not None:
            self._draw_analysis(screen)
        else:
            self._draw_main(screen)
        if self.show_tutorial:
            self._draw_tutorial(screen)

    def _draw_tutorial(self, screen):
        tutorial_rect = pygame.Rect(self.screen_width // 2 - 220, self.screen_height // 2 - 85, 440, 170)
        pygame.draw.rect(screen, theme.SURFACE, tutorial_rect, border_radius=10)
        pygame.draw.rect(screen, theme.ACCENT, tutorial_rect, 2, border_radius=10)
        self.tutorial_close_rect = pygame.Rect(tutorial_rect.right - 24, tutorial_rect.y + 8, 16, 16)
        pygame.draw.rect(screen, theme.DANGER, self.tutorial_close_rect)
        pygame.draw.rect(screen, (0, 0, 0), self.tutorial_close_rect, 1)
        title = self.font_medium.render(self.scenario["title"], True, theme.WARNING)
        screen.blit(title, (tutorial_rect.centerx - title.get_width() // 2, tutorial_rect.y + 15))
        small_font = pygame.font.Font(None, 18)
        instructions = [
            "1. Изучите все этапы анализа",
            "2. Выполните защитное действие",
            "3. Пройдите финальный тест",
        ]
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (255, 255, 255))
            screen.blit(text, (tutorial_rect.x + 20, tutorial_rect.y + 50 + i * 22))

    def _draw_main(self, screen):
        desc_font = pygame.font.Font(None, 22)
        for i, line in enumerate(self.scenario["description_lines"]):
            text = desc_font.render(line, True, (255, 255, 255) if line else (255, 255, 255))
            screen.blit(text, (50, 60 + i * 25))
        for button in self.buttons:
            button.draw(screen)
        self.exit_to_desktop_button.draw(screen)

    def _draw_analysis(self, screen):
        analysis_rect = pygame.Rect(50, 80, self.screen_width - 100, self.screen_height - 200)
        pygame.draw.rect(screen, theme.SURFACE_ALT, analysis_rect, border_radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.BORDER, analysis_rect, 2, border_radius=theme.RADIUS_LG)

        step = self._step_by_id(self.current_step)
        title = self.font_large.render(step["title"], True, (255, 255, 255))
        screen.blit(title, (70, 90))

        line_height, empty_height = 25, 10
        total_content_h = sum(empty_height if line == "" else line_height for line in step["content"])
        visible_h = analysis_rect.height - 60
        max_scroll = max(0, total_content_h - visible_h)
        self.analysis_scroll = max(0, min(self.analysis_scroll, max_scroll))

        y_pos = 140 - self.analysis_scroll
        screen.set_clip(analysis_rect)
        for line in step["content"]:
            if line == "":
                y_pos += empty_height
                continue
            color = (200, 200, 255) if line.startswith("-") else (255, 255, 255)
            text = self.font_small.render(line, True, color)
            screen.blit(text, (70, y_pos))
            y_pos += line_height
        screen.set_clip(None)

        self.back_button.draw(screen)
        self.exit_to_desktop_button.draw(screen)

    def _draw_command_prompt(self, screen):
        unlock = self.scenario["unlock_action"]
        screen.blit(self._cmd_blurred_bg, (0, 0))
        self.command_back_button.draw(screen)
        cmd_rect = pygame.Rect(100, 100, self.screen_width - 200, 400)
        pygame.draw.rect(screen, (0, 0, 0), cmd_rect)
        pygame.draw.rect(screen, (200, 200, 200), cmd_rect, 2)

        title_bar = pygame.Rect(100, 80, self.screen_width - 200, 20)
        pygame.draw.rect(screen, (0, 0, 128), title_bar)
        title_text = self.font_small.render(unlock["prompt_title"], True, (255, 255, 255))
        screen.blit(title_text, (110, 82))

        y_pos = cmd_rect.y + 20
        start_index = max(0, len(self.command_history) - 15)
        for i in range(start_index, len(self.command_history)):
            if y_pos > cmd_rect.y + cmd_rect.height - 40:
                break
            history_text = self.font_mono.render(self.command_history[i], True, (255, 255, 255))
            screen.blit(history_text, (cmd_rect.x + 10, y_pos))
            y_pos += 20

        prompt_text = self.font_mono.render("C:\\Windows\\System32>", True, (255, 255, 255))
        screen.blit(prompt_text, (cmd_rect.x + 10, y_pos))
        cmd_display = self.font_mono.render(self.command_text, True, (255, 255, 255))
        screen.blit(cmd_display, (cmd_rect.x + 180, y_pos))
        if pygame.time.get_ticks() % 1000 < 500:
            cursor_x = cmd_rect.x + 180 + cmd_display.get_width()
            pygame.draw.rect(screen, (255, 255, 255), (cursor_x, y_pos, 8, 18))

        instruction_rect = pygame.Rect(100, cmd_rect.y + cmd_rect.height + 10, self.screen_width - 200, 60)
        pygame.draw.rect(screen, theme.SURFACE_ALT, instruction_rect, border_radius=5)
        pygame.draw.rect(screen, theme.BORDER, instruction_rect, 1, border_radius=5)
        instruction1 = self.font_small.render(unlock["instruction"], True, theme.WARNING)
        screen.blit(instruction1, (instruction_rect.centerx - instruction1.get_width() // 2, instruction_rect.y + 10))
        instruction2 = self.font_mono.render(unlock["command_hint"], True, (200, 200, 255))
        screen.blit(instruction2, (instruction_rect.centerx - instruction2.get_width() // 2, instruction_rect.y + 35))

    def _draw_report(self, screen):
        report_rect = pygame.Rect(self.screen_width // 2 - 300, self.screen_height // 2 - 200, 600, 400)
        pygame.draw.rect(screen, theme.SURFACE, report_rect, border_radius=15)
        pygame.draw.rect(screen, theme.ACCENT, report_rect, 3, border_radius=15)

        title = self.font_large.render("ФИНАЛЬНЫЙ ОТЧЕТ", True, theme.SUCCESS)
        screen.blit(title, (report_rect.centerx - title.get_width() // 2, report_rect.y + 30))

        stats_font = pygame.font.Font(None, 28)
        small_font = pygame.font.Font(None, 22)
        y_pos = report_rect.y + 80

        score_text = stats_font.render(f"Набрано очков: {self.quiz.score}/{self.quiz.max_score}", True, theme.WARNING)
        screen.blit(score_text, (report_rect.centerx - score_text.get_width() // 2, y_pos))
        y_pos += 40

        n_steps = len(self.scenario["analysis_steps"])
        completed_analysis = len([s for s in self.completed_steps if s in {st["id"] for st in self.scenario["analysis_steps"]}])
        steps_text = small_font.render(f"Выполнено этапов анализа: {completed_analysis}/{n_steps}", True, theme.SUCCESS_SOFT)
        screen.blit(steps_text, (report_rect.centerx - steps_text.get_width() // 2, y_pos))
        y_pos += 30

        quiz_text = small_font.render(f"Правильных ответов в тесте: {self.quiz.correct_count}/{self.quiz.total_questions}", True, theme.SUCCESS_SOFT)
        screen.blit(quiz_text, (report_rect.centerx - quiz_text.get_width() // 2, y_pos))
        y_pos += 40

        if self.quiz.score >= self.quiz.max_score * 0.8:
            grade, color = "ОТЛИЧНО", theme.SUCCESS
        elif self.quiz.score >= self.quiz.max_score * 0.5:
            grade, color = "ХОРОШО", theme.WARNING
        elif self.quiz.score > 0:
            grade, color = "УДОВЛЕТВОРИТЕЛЬНО", theme.WARNING
        else:
            grade, color = "НЕУДОВЛЕТВОРИТЕЛЬНО", theme.DANGER
        grade_text = stats_font.render(f"ИТОГОВАЯ ОЦЕНКА: {grade}", True, color)
        screen.blit(grade_text, (report_rect.centerx - grade_text.get_width() // 2, y_pos))
        y_pos += 50

        instruction = small_font.render("Нажмите в любом месте для завершения", True, (200, 200, 255))
        screen.blit(instruction, (report_rect.centerx - instruction.get_width() // 2, report_rect.y + report_rect.height - 40))

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if self.quiz:
            self.quiz.on_resize(w, h)

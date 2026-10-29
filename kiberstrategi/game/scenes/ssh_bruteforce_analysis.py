# [file name]: ssh_bruteforce_analysis.py
# [file content begin]
import pygame
from ..ui.button import Button
from ..ui import theme
from ..ui.quiz_engine import QuizEngine
from ..data.quiz_data import get_quiz_questions
from .command_prompt_common import get_blurred_background, create_back_button

class SSHBruteforceAnalysis:
    def __init__(self, screen_width, screen_height, on_complete_callback):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        
        # Данные анализа брутфорс атаки на основе Брутфорс SSH.pdf
        self.attack_data = {
            "technique": "T1110 - Brute Force (SSH)",
            "description": "Подбор учетных данных для доступа по протоколу SSH",
            "analysis_steps": {
                "detection": {
                    "title": "1. Обнаружение атаки",
                    "content": [
                        "ОБНАРУЖЕНИЕ БРУТФОРС АТАКИ:",
                        "",
                        "- Дата атаки: 16.01.2025",
                        "- Всего сессий за период: 248",
                        "- Сессий на SSH (порт 22): 226",
                        "- Узел атакующего (клиент): 10.10.187.241",
                        "- Узел жертвы (сервер): 10.10.187.56",
                        "",
                        "ВЫВОД:",
                        "Подавляющее большинство сессий приходится на SSH, что нетипично."
                    ]
                },
                "failed_attempts": {
                    "title": "2. Анализ неудачных попыток",
                    "content": [
                        "АНАЛИЗ НЕУДАЧНЫХ ПОПЫТОК ВХОДА:",
                        "",
                        "- Просмотр карточек сессий SSH",
                        "- Поле 'Authentication' = 'failed'",
                        "- Поле 'Auth password failed' = 5 (попыток за сессию)",
                        "",
                        "ПРИЗНАКИ БРУТФОРСА:",
                        "- Множество сессий с failed аутентификацией",
                        "- Короткие промежутки времени между попытками",
                        "- Один и тот же источник (10.10.187.241)",
                        "",
                        "ВЫВОД:",
                        "Зафиксирована автоматизированная атака подбора паролей."
                    ]
                },
                "successful_login": {
                    "title": "3. Обнаружение успешного входа",
                    "content": [
                        "ПОИСК УСПЕШНОЙ АУТЕНТИФИКАЦИИ:",
                        "",
                        "- Фильтр в PT NAD: dst.port == 22 && ssh.auth == password",
                        "- Найдено 2 сессии с успешной аутентификацией",
                        "",
                        "ДЕТАЛИ УСПЕШНОЙ СЕССИИ:",
                        "- Время: 16:20:31",
                        "- Поле 'Authentication' = 'password' (успех)",
                        "- Поле 'Keypressed' присутствует (активность после входа)",
                        "- Client software: OpenSSH_9.2p1 Debian-2-red1t2u4",
                        "",
                        "ВЫВОД:",
                        "Злоумышленнику удалось подобрать пароль и получить доступ."
                    ]
                },
                "mitigation": {
                    "title": "4. Нейтрализация угрозы",
                    "content": [
                        "МЕТОДЫ ЗАЩИТЫ ОТ БРУТФОРСА:",
                        "",
                        "ОБНАРУЖЕНИЕ:",
                        "- Мониторинг множества неудачных попыток входа (SIEM/NAD)",
                        "- Алерты на превышение порога failed попыток с одного IP",
                        "",
                        "ПРЕДОТВРАЩЕНИЕ:",
                        "- Использование нестандартного порта для SSH",
                        "- Запрет входа для root напрямую",
                        "- Настройка Fail2ban (блокировка IP после N неудач)",
                        "- Использование ключей вместо паролей",
                        "",
                        "НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ ПРИ УСПЕХЕ:",
                        "- Сменить пароль на скомпрометированном сервере",
                        "- Проверить историю команд злоумышленника",
                        "- Заблокировать IP атакующего на firewall",
                    ]
                }
            }
        }
        
        # Состояние игры
        self.completed_steps = []
        self.current_step = None
        self.show_command_prompt = False
        self.command_text = ""
        self.command_success = False
        self.command_history = []
        self.analysis_scroll = 0
        self._cmd_blurred_bg = get_blurred_background(screen_width, screen_height)
        self.command_back_button = create_back_button(screen_width, screen_height, self._close_command_prompt)
        
        # Кнопки
        self.buttons = []
        self._create_buttons()
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        self.font_mono = pygame.font.Font(None, 18)
        
        # Финальный квиз (3 случайных из пула для уровня 7)
        self.show_final_quiz = False
        self.quiz_questions = get_quiz_questions(7, 3)
        self.quiz = None
        
        # Отчет
        self.show_report = False
        self.show_tutorial = True
        self.tutorial_close_rect = None

    def _create_buttons(self):
        """Создание кнопок для анализа"""
        button_width, button_height = 350, 35
        start_x = 50
        start_y = 350
        
        buttons_data = [
            ("1. Обнаружение аномалии", self.start_detection, theme.ACCENT),
            ("2. Анализ неудачных попыток", self.start_failed_analysis, (150, 100, 200)),
            ("3. Поиск успешного входа", self.start_success_analysis, (200, 100, 100)),
            ("4. Нейтрализация угрозы", self.start_mitigation, (100, 150, 50)),
            ("---", None, (0, 0, 0)),
            ("Заблокировать IP атакующего", self.show_command_prompt_window, (200, 0, 0)),
        ]
        
        for i, (text, callback, color) in enumerate(buttons_data):
            if text == "---":
                continue
            button = Button(
                start_x, start_y + i * 45,
                button_width, button_height,
                text, color, callback
            )
            self.buttons.append(button)
        
        self.back_button = Button(50, self.screen_height - 55, 120, 35, "Назад", (20, 120, 100), self.back_to_main)
        self.exit_to_desktop_button = Button(
            self.screen_width - 130, 20, 110, 36, "Назад", (120, 120, 120),
            lambda: self.on_complete(False)
        )

    def start_detection(self):
        self.current_step = "detection"
        if "detection" not in self.completed_steps:
            self.completed_steps.append("detection")

    def start_failed_analysis(self):
        self.current_step = "failed_attempts"
        if "failed_attempts" not in self.completed_steps:
            self.completed_steps.append("failed_attempts")

    def start_success_analysis(self):
        self.current_step = "successful_login"
        if "successful_login" not in self.completed_steps:
            self.completed_steps.append("successful_login")

    def start_mitigation(self):
        self.current_step = "mitigation"
        if "mitigation" not in self.completed_steps:
            self.completed_steps.append("mitigation")

    def show_command_prompt_window(self):
        self.show_command_prompt = True
        self.command_text = ""
        self.command_success = False
        self.command_history = []

    def _close_command_prompt(self):
        self.show_command_prompt = False

    def back_to_main(self):
        self.current_step = None
        self.show_command_prompt = False
        self.show_final_quiz = False

    def handle_command(self, command):
        cmd = command.strip().lower()
        if cmd == "skip" or cmd == "netsh advfirewall firewall add rule name=\"block ssh\" dir=in action=block remoteip=10.10.187.241":
            self.command_success = True
            self.completed_steps.append("IP атакующего (10.10.187.241) заблокирован")
            self.show_command_prompt = False
            self.show_final_quiz = True
            self.quiz = QuizEngine(self.screen_width, self.screen_height, self.quiz_questions, "ФИНАЛЬНЫЙ ТЕСТ (Уровень 7)")
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
            return

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
                    self.handle_command(self.command_text)
                    self.command_history.append(f"C:\\Windows\\System32>{self.command_text}")
                    self.command_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.command_text = self.command_text[:-1]
                else:
                    self.command_text += event.unicode
                return True
            return False
        
        if self.current_step is not None and not self.show_command_prompt:
            if event.type == pygame.MOUSEWHEEL:
                stage_data = self.attack_data["analysis_steps"].get(self.current_step)
                if stage_data:
                    line_height = 25
                    empty_height = 10
                    total_h = sum(empty_height if line == "" else line_height for line in stage_data["content"])
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
        
        title = self.font_large.render("РАССЛЕДОВАНИЕ: T1110 - Брутфорс SSH атака", True, (255, 255, 255))
        screen.blit(title, (self.screen_width//2 - title.get_width()//2, 20))
        
        if self.show_report:
            self.draw_report(screen)
        elif self.show_final_quiz:
            self.quiz.draw(screen)
        elif self.show_command_prompt:
            self.draw_command_prompt(screen)
        elif self.current_step is not None:
            self.draw_analysis(screen)
        else:
            self.draw_main(screen)
        if self.show_tutorial:
            self.draw_tutorial(screen)

    def draw_tutorial(self, screen):
        """Отрисовка инструкции с шагами, закрывается по крестику."""
        tutorial_rect = pygame.Rect(self.screen_width // 2 - 200, self.screen_height // 2 - 85, 400, 170)
        pygame.draw.rect(screen, theme.SURFACE, tutorial_rect, border_radius=10)
        pygame.draw.rect(screen, theme.ACCENT, tutorial_rect, 2, border_radius=10)
        self.tutorial_close_rect = pygame.Rect(tutorial_rect.right - 24, tutorial_rect.y + 8, 16, 16)
        pygame.draw.rect(screen, theme.DANGER, self.tutorial_close_rect)
        pygame.draw.rect(screen, (0, 0, 0), self.tutorial_close_rect, 1)
        pygame.draw.line(screen, (255, 255, 255), (self.tutorial_close_rect.x + 4, self.tutorial_close_rect.y + 4), (self.tutorial_close_rect.x + 12, self.tutorial_close_rect.y + 12), 2)
        pygame.draw.line(screen, (255, 255, 255), (self.tutorial_close_rect.x + 12, self.tutorial_close_rect.y + 4), (self.tutorial_close_rect.x + 4, self.tutorial_close_rect.y + 12), 2)
        tutorial_font = pygame.font.Font(None, 24)
        title = tutorial_font.render("ИНСТРУКЦИЯ (Уровень 7)", True, theme.WARNING)
        screen.blit(title, (tutorial_rect.centerx - title.get_width()//2, tutorial_rect.y + 15))
        small_font = pygame.font.Font(None, 18)
        instructions = [
            "1. Проведите анализ обнаружения и неудачных попыток",
            "2. Найдите успешный вход в логах",
            "3. Заблокируйте IP атакующего в Firewall",
            "4. Пройдите финальный тест"
        ]
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (255, 255, 255))
            screen.blit(text, (tutorial_rect.x + 20, tutorial_rect.y + 45 + i * 22))

    def draw_main(self, screen):
        desc_font = pygame.font.Font(None, 22)
        description = [
            "ОБНАРУЖЕНА БРУТФОРС-АТАКА НА SSH СЕРВЕР",
            "",
            "Атакующий: 10.10.187.241",
            "Жертва: 10.10.187.56:22",
            "Статистика: 226 сессий на порт 22 из 248",
            "Результат: УСПЕШНЫЙ ВХОД зафиксирован",
            "",
            "Проведите полное расследование:"
        ]
        
        for i, line in enumerate(description):
            color = theme.DANGER if "ОБНАРУЖЕНА" in line else (255, 255, 255)
            if "Атакующий:" in line: color = theme.DANGER
            if "Жертва:" in line: color = theme.WARNING
            if "Статистика:" in line: color = (100, 200, 255)
            if "Результат:" in line: color = theme.DANGER
            if "Проведите полное" in line: color = theme.WARNING
            
            text = desc_font.render(line, True, color)
            screen.blit(text, (50, 60 + i * 25))
        
        for button in self.buttons:
            button.draw(screen)
        self.exit_to_desktop_button.draw(screen)

    def draw_analysis(self, screen):
        analysis_rect = pygame.Rect(50, 80, self.screen_width - 100, self.screen_height - 200)
        pygame.draw.rect(screen, theme.SURFACE_ALT, analysis_rect, border_radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.BORDER, analysis_rect, 2, border_radius=theme.RADIUS_LG)
        
        stage_data = self.attack_data["analysis_steps"][self.current_step]
        
        title = self.font_large.render(stage_data["title"], True, (255, 255, 255))
        screen.blit(title, (70, 90))
        
        line_height = 25
        empty_height = 10
        total_content_h = sum(empty_height if line == "" else line_height for line in stage_data["content"])
        visible_h = analysis_rect.height - 60
        max_scroll = max(0, total_content_h - visible_h)
        self.analysis_scroll = max(0, min(self.analysis_scroll, max_scroll))
        
        y_pos = 140 - self.analysis_scroll
        screen.set_clip(analysis_rect)
        for line in stage_data["content"]:
            if line == "":
                y_pos += empty_height
                continue
            if line.startswith("-"):
                color = (200, 200, 255) if "Злоумышленнику" not in line else theme.DANGER
            else:
                color = (255, 255, 255)
            
            text = self.font_small.render(line, True, color)
            screen.blit(text, (70, y_pos))
            y_pos += line_height
        screen.set_clip(None)
        
        self.back_button.draw(screen)
        self.exit_to_desktop_button.draw(screen)

    def draw_command_prompt(self, screen):
        screen.blit(self._cmd_blurred_bg, (0, 0))
        self.command_back_button.draw(screen)
        cmd_rect = pygame.Rect(100, 100, self.screen_width - 200, 400)
        pygame.draw.rect(screen, (0, 0, 0), cmd_rect)
        pygame.draw.rect(screen, (200, 200, 200), cmd_rect, 2)
        
        title_bar = pygame.Rect(100, 80, self.screen_width - 200, 20)
        pygame.draw.rect(screen, (0, 0, 128), title_bar)
        title_text = self.font_small.render("Командная строка Windows - Блокировка IP атакующего", True, (255, 255, 255))
        screen.blit(title_text, (110, 82))
        
        y_pos = cmd_rect.y + 20
        max_history_lines = 15
        start_index = max(0, len(self.command_history) - max_history_lines)
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
        
        instruction1 = self.font_small.render("Введите команду для блокировки IP атакующего (10.10.187.241) в Windows Firewall:", True, theme.WARNING)
        screen.blit(instruction1, (instruction_rect.centerx - instruction1.get_width()//2, instruction_rect.y + 10))
        
        instruction2 = self.font_mono.render("netsh advfirewall firewall add rule name=\"block ssh\" dir=in action=block remoteip=10.10.187.241", True, (200, 200, 255))
        screen.blit(instruction2, (instruction_rect.centerx - instruction2.get_width()//2, instruction_rect.y + 35))

    def draw_report(self, screen):
        report_rect = pygame.Rect(self.screen_width//2 - 300, self.screen_height//2 - 200, 600, 400)
        pygame.draw.rect(screen, theme.SURFACE, report_rect, border_radius=15)
        pygame.draw.rect(screen, theme.ACCENT, report_rect, 3, border_radius=15)
        
        title = self.font_large.render("ФИНАЛЬНЫЙ ОТЧЕТ (Уровень 7)", True, theme.SUCCESS)
        screen.blit(title, (report_rect.centerx - title.get_width()//2, report_rect.y + 30))
        
        stats_font = pygame.font.Font(None, 28)
        small_font = pygame.font.Font(None, 22)
        
        y_pos = report_rect.y + 80
        score_text = stats_font.render(f"Набрано очков: {self.quiz.score}/{self.quiz.max_score}", True, theme.WARNING)
        screen.blit(score_text, (report_rect.centerx - score_text.get_width()//2, y_pos))
        y_pos += 40

        completed_steps = len([s for s in self.completed_steps if not s.startswith("IP")])
        steps_text = small_font.render(f"Выполнено этапов анализа: {completed_steps}/4", True, theme.SUCCESS_SOFT)
        screen.blit(steps_text, (report_rect.centerx - steps_text.get_width()//2, y_pos))
        y_pos += 30

        quiz_text = small_font.render(f"Правильных ответов в тесте: {self.quiz.correct_count}/{self.quiz.total_questions}", True, theme.SUCCESS_SOFT)
        screen.blit(quiz_text, (report_rect.centerx - quiz_text.get_width()//2, y_pos))
        y_pos += 40

        if self.quiz.score >= self.quiz.max_score * 0.8:
            grade = "ОТЛИЧНО"; color = theme.SUCCESS
        elif self.quiz.score >= self.quiz.max_score * 0.5:
            grade = "ХОРОШО"; color = theme.WARNING
        elif self.quiz.score > 0:
            grade = "УДОВЛЕТВОРИТЕЛЬНО"; color = theme.WARNING
        else:
            grade = "НЕУДОВЛЕТВОРИТЕЛЬНО"; color = theme.DANGER
        
        grade_text = stats_font.render(f"ИТОГОВАЯ ОЦЕНКА: {grade}", True, color)
        screen.blit(grade_text, (report_rect.centerx - grade_text.get_width()//2, y_pos))
        y_pos += 50
        
        instruction = small_font.render("Нажмите в любом месте для завершения", True, (200, 200, 255))
        screen.blit(instruction, (report_rect.centerx - instruction.get_width()//2, report_rect.y + report_rect.height - 40))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if self.quiz:
            self.quiz.on_resize(w, h)
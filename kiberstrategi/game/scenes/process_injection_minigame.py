import pygame
from ..ui.button import Button
from ..ui import theme
from ..ui.quiz_engine import QuizEngine
from ..data.quiz_data import get_quiz_questions
from .command_prompt_common import get_blurred_background, create_back_button

class ProcessInjectionMinigame:
    def __init__(self, screen_width, screen_height, on_complete_callback, game_manager=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        self.game_manager = game_manager
        
        # Данные атаки T1055
        self.attack_data = {
            "technique": "T1055 - Process Injection",
            "description": "Внедрение кода в процессы для обхода защиты и повышения привилегий",
            "malicious_process": "logonhelper.exe",
            "injected_into": "explorer.exe",
            "analysis_steps": {
                "behavior_analysis": {
                    "title": "1. Анализ поведения процесса",
                    "content": [
                        "АНАЛИЗ ПОВЕДЕНИЯ PROCESS INJECTION:",
                        "",
                        "- Процесс: logonhelper.exe маскируется под системную утилиту",
                        "- Родительский процесс: Неизвестен (обычно winlogon.exe)",
                        "- Потребление памяти: Аномально высокое для системного процесса",
                        "- Сетевые соединения: Попытки выхода на внешние IP-адреса",
                        "",
                        "ТИПИЧНЫЕ ПРИЗНАКИ T1055:",
                        "- Процесс без цифровой подписи Microsoft",
                        "- Высокое потребление ресурсов без видимой причины", 
                        "- Попытки доступа к памяти других процессов",
                        "- Нестандартные пути выполнения",
                        "",
                        "ВЫВОД:",
                        "Обнаружены явные признаки внедрения кода в процессы"
                    ]
                },
                "memory_analysis": {
                    "title": "2. Анализ памяти и DLL",
                    "content": [
                        "АНАЛИЗ ПАМЯТИ ПРОЦЕССА:",
                        "",
                        "- Обнаружена подозрительная DLL: kernel_helpers.dll",
                        "- DLL загружена в процесс explorer.exe",
                        "- Отсутствует цифровая подпись у DLL",
                        "- Попытки вызова API-функций для чтения памяти",
                        "",
                        "МЕТОДЫ ОБНАРУЖЕНИЯ (MITRE):",
                        "- Мониторинг вызовов API (OpenProcess, WriteProcessMemory)",
                        "- Анализ загруженных DLL в процессах",
                        "- Проверка цифровых подписей исполняемых файлов",
                        "- Мониторинг аномального поведения процессов",
                        "",
                        "ВЫВОД:",
                        "Подтверждено внедрение вредоносного кода через DLL"
                    ]
                },
                "mitigation": {
                    "title": "3. Методы предотвращения T1055",
                    "content": [
                        "МЕТОДЫ БОРЬБЫ С PROCESS INJECTION:",
                        "",
                        "- M1048: Блокировка подозрительных процессов",
                        "- M1038: Запрет выполнения кода в определенных областях памяти",
                        "- M1026: Принцип наименьших привилегий для процессов",
                        "- M1041: Шифрование конфиденциальной информации",
                        "- Мониторинг вызовов API для инъекции памяти",
                        "- Использование EDR-систем для поведенческого анализа",
                        "",
                        "НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ:",
                        "- Завершить вредоносный процесс logonhelper.exe",
                        "- Проверить систему на наличие persistence-механизмов",
                        "- Обновить сигнатуры антивируса",
                        "- Провести аудит системных процессов",
                        "",
                        "РЕКОМЕНДАЦИИ:",
                        "Внедрить контроль целостности процессов (Code Integrity)"
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
        
        # Финальный квиз (3 случайных из пула для уровня 3)
        self.show_final_quiz = False
        self.quiz_questions = get_quiz_questions(3, 3)
        self.quiz = None
        
        # Отчет
        self.show_report = False
        # Инструкция при старте (как в днях 1–2)
        self.show_tutorial = True
        self.tutorial_close_rect = None

    def _create_buttons(self):
        """Создание кнопок для анализа"""
        button_width, button_height = 350, 35
        start_x = 50
        start_y = 350  # Опустили кнопки ниже
        
        buttons_data = [
            ("1. Анализ поведения процесса", self.start_behavior_analysis, theme.ACCENT),
            ("2. Анализ памяти и DLL", self.start_memory_analysis, (150, 100, 200)),
            ("3. Методы предотвращения", self.start_mitigation_analysis, (200, 100, 100)),
            ("---", None, (0, 0, 0)),
            ("Завершить процесс", self.show_command_prompt_window, (200, 0, 0)),
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
        
        # Кнопка назад (к списку этапов)
        self.back_button = Button(50, self.screen_height - 55, 120, 35, "Назад", (20, 120, 100), self.back_to_main)
        # Кнопка «Назад» — выход из расследования на рабочий стол
        self.exit_to_desktop_button = Button(
            self.screen_width - 130, 20, 110, 36, "Назад", (120, 120, 120),
            lambda: self.on_complete(False)
        )

    # Методы для кнопок
    def start_behavior_analysis(self):
        self.current_step = "behavior_analysis"
        if "behavior_analysis" not in self.completed_steps:
            self.completed_steps.append("behavior_analysis")

    def start_memory_analysis(self):
        self.current_step = "memory_analysis"
        if "memory_analysis" not in self.completed_steps:
            self.completed_steps.append("memory_analysis")

    def start_mitigation_analysis(self):
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
        if cmd == "skip" or cmd == "taskkill /im logonhelper.exe /f":
            self.command_success = True
            self.completed_steps.append("Процесс logonhelper.exe завершен")
            # После успешной команды показываем квиз
            self.show_command_prompt = False
            self.show_final_quiz = True
            self.quiz = QuizEngine(self.screen_width, self.screen_height, self.quiz_questions, "ФИНАЛЬНЫЙ ТЕСТ (Уровень 3)")
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
                    cmd = self.command_text if isinstance(self.command_text, str) else ""
                    self.handle_command(cmd)
                    self.command_history.append(f"C:\\Windows\\System32>{cmd}")
                    self.command_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.command_text = (self.command_text or "")[:-1]
                else:
                    u = getattr(event, "unicode", None)
                    if isinstance(u, str) and u:
                        self.command_text = (self.command_text or "") + u
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
        if self.current_step is not None:
            self.back_button.update()
            self.exit_to_desktop_button.update()
        else:
            self.exit_to_desktop_button.update()
            for button in self.buttons:
                button.update()
        
        if self.show_command_prompt:
            self.command_back_button.update()
        if self.show_final_quiz:
            self.quiz.update()

    def draw(self, screen):
        screen.fill(theme.BG)
        
        # Заголовок
        title = self.font_large.render("РАССЛЕДОВАНИЕ: T1055 Process Injection", True, (255, 255, 255))
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
        title = tutorial_font.render("ИНСТРУКЦИЯ (Уровень 3)", True, theme.WARNING)
        screen.blit(title, (tutorial_rect.centerx - title.get_width()//2, tutorial_rect.y + 15))
        small_font = pygame.font.Font(None, 18)
        instructions = [
            "1. Изучите этапы анализа (поведение, память, методы)",
            "2. Откройте «Завершить процесс» и введите команду",
            "3. Завершите процесс logonhelper.exe (taskkill)",
            "4. Пройдите финальный тест"
        ]
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (255, 255, 255))
            screen.blit(text, (tutorial_rect.x + 20, tutorial_rect.y + 45 + i * 22))

    def draw_main(self, screen):
        """Отрисовка главного экрана расследования"""
        # Описание атаки
        desc_font = pygame.font.Font(None, 22)
        description = [
            "ОБНАРУЖЕНА ПРОДВИНУТАЯ АТАКА: Process Injection",
            "",
            "Вредоносный процесс: logonhelper.exe",
            "Техника MITRE: T1055 - Внедрение кода в легитимные процессы",
            "Цель: Обход антивирусной защиты и кража данных",
            "",
            "Проведите полное расследование:"
        ]
        
        for i, line in enumerate(description):
            color = theme.DANGER if "ОБНАРУЖЕНА" in line else (255, 255, 255)
            if "Вредоносный процесс" in line: color = theme.DANGER
            if "Техника MITRE" in line: color = theme.WARNING
            if line.startswith("Цель:"): color = (100, 200, 255)
            if "Проведите полное" in line: color = theme.SUCCESS
            
            text = desc_font.render(line, True, color)
            screen.blit(text, (50, 60 + i * 25))
        
        # Кнопки действий
        for button in self.buttons:
            button.draw(screen)
        self.exit_to_desktop_button.draw(screen)

    def draw_analysis(self, screen):
        """Отрисовка экрана анализа с прокруткой при переполнении"""
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
            if line.startswith("-"): color = (200, 200, 255)
            else: color = (255, 255, 255)
            text = self.font_small.render(line, True, color)
            screen.blit(text, (70, y_pos))
            y_pos += line_height
        screen.set_clip(None)
        
        self.back_button.draw(screen)
        self.exit_to_desktop_button.draw(screen)

    def draw_command_prompt(self, screen):
        """Отрисовка реалистичной командной строки"""
        screen.blit(self._cmd_blurred_bg, (0, 0))
        self.command_back_button.draw(screen)
        # Фон командной строки (черный как в реальной cmd)
        cmd_rect = pygame.Rect(100, 100, self.screen_width - 200, 400)
        pygame.draw.rect(screen, (0, 0, 0), cmd_rect)
        pygame.draw.rect(screen, (200, 200, 200), cmd_rect, 2)
        
        # Заголовок окна (как в реальной командной строке)
        title_bar = pygame.Rect(100, 80, self.screen_width - 200, 20)
        pygame.draw.rect(screen, (0, 0, 128), title_bar)
        title_text = self.font_small.render("Командная строка Windows", True, (255, 255, 255))
        screen.blit(title_text, (110, 82))
        
        # История команд (белый текст на черном фоне)
        y_pos = cmd_rect.y + 20
        max_history_lines = 15
        
        # Показать последние команды из истории (безопасный рендер для шрифта по умолчанию)
        def _safe_text(s):
            return "".join(c if ord(c) < 128 else "?" for c in (s or ""))
        start_index = max(0, len(self.command_history) - max_history_lines)
        for i in range(start_index, len(self.command_history)):
            if y_pos > cmd_rect.y + cmd_rect.height - 40:
                break
            history_text = self.font_mono.render(_safe_text(self.command_history[i]), True, (255, 255, 255))
            screen.blit(history_text, (cmd_rect.x + 10, y_pos))
            y_pos += 20
        
        # Текущая строка ввода
        prompt_text = self.font_mono.render("C:\\Windows\\System32>", True, (255, 255, 255))
        screen.blit(prompt_text, (cmd_rect.x + 10, y_pos))
        
        # Введенная команда (безопасный рендер)
        cmd_display = self.font_mono.render(_safe_text(self.command_text), True, (255, 255, 255))
        screen.blit(cmd_display, (cmd_rect.x + 180, y_pos))
        
        # Мигающий курсор (как в реальной cmd)
        if pygame.time.get_ticks() % 1000 < 500:
            cursor_x = cmd_rect.x + 180 + cmd_display.get_width()
            pygame.draw.rect(screen, (255, 255, 255), (cursor_x, y_pos, 8, 18))
        
        # Инструкция
        instruction_rect = pygame.Rect(100, cmd_rect.y + cmd_rect.height + 10, self.screen_width - 200, 55)
        pygame.draw.rect(screen, theme.SURFACE_ALT, instruction_rect, border_radius=5)
        pygame.draw.rect(screen, theme.BORDER, instruction_rect, 1, border_radius=5)
        
        instruction1 = self.font_small.render("Введите команду для завершения процесса logonhelper.exe:", True, theme.WARNING)
        screen.blit(instruction1, (instruction_rect.x + 15, instruction_rect.y + 8))
        
        instruction2 = self.font_small.render("Формат:  taskkill /im ИМЯ_ПРОЦЕССА /f", True, (200, 200, 255))
        screen.blit(instruction2, (instruction_rect.x + 15, instruction_rect.y + 28))
        
        if self.command_success:
            success_rect = pygame.Rect(100, instruction_rect.y + instruction_rect.height + 8, self.screen_width - 200, 40)
            pygame.draw.rect(screen, (0, 100, 0), success_rect, border_radius=5)
            success_text = self.font_medium.render("УСПЕХ: Процесс logonhelper.exe завершен!", True, (255, 255, 255))
            screen.blit(success_text, (success_rect.centerx - success_text.get_width()//2, success_rect.y + 10))

    def draw_report(self, screen):
        """Отрисовка финального отчета"""
        report_rect = pygame.Rect(self.screen_width//2 - 300, self.screen_height//2 - 200, 600, 400)
        pygame.draw.rect(screen, theme.SURFACE, report_rect, border_radius=15)
        pygame.draw.rect(screen, theme.ACCENT, report_rect, 3, border_radius=15)
        
        # Заголовок отчета
        title = self.font_large.render("ФИНАЛЬНЫЙ ОТЧЕТ (Уровень 3)", True, theme.SUCCESS)
        screen.blit(title, (report_rect.centerx - title.get_width()//2, report_rect.y + 30))
        
        # Статистика
        stats_font = pygame.font.Font(None, 28)
        small_font = pygame.font.Font(None, 22)
        
        y_pos = report_rect.y + 80
        
        # Очки
        score_text = stats_font.render(f"Набрано очков: {self.quiz.score}/{self.quiz.max_score}", True, theme.WARNING)
        screen.blit(score_text, (report_rect.centerx - score_text.get_width()//2, y_pos))
        y_pos += 40

        # Выполненные этапы
        completed_steps = len([s for s in self.completed_steps if not s.startswith("Процесс")])
        steps_text = small_font.render(f"Выполнено этапов анализа: {completed_steps}/3", True, theme.SUCCESS_SOFT)
        screen.blit(steps_text, (report_rect.centerx - steps_text.get_width()//2, y_pos))
        y_pos += 30

        # Правильные ответы
        quiz_text = small_font.render(f"Правильных ответов в тесте: {self.quiz.correct_count}/{self.quiz.total_questions}", True, theme.SUCCESS_SOFT)
        screen.blit(quiz_text, (report_rect.centerx - quiz_text.get_width()//2, y_pos))
        y_pos += 40

        # Итоговая оценка
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
        
        # Итоговая цепочка атаки
        chain_text = small_font.render("Цепочка атаки: Фишинг - Process Injection - Кража данных", True, (200, 200, 255))
        screen.blit(chain_text, (report_rect.centerx - chain_text.get_width()//2, y_pos))
        y_pos += 30
        
        # Инструкция
        instruction = small_font.render("Нажмите в любом месте для завершения", True, (200, 200, 255))
        screen.blit(instruction, (report_rect.centerx - instruction.get_width()//2, report_rect.y + report_rect.height - 40))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if self.quiz:
            self.quiz.on_resize(w, h)

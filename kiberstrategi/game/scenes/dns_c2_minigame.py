import pygame
import base64
from ..ui.button import Button
from ..ui import theme
from ..ui.quiz_engine import QuizEngine
from ..data.quiz_data import get_quiz_questions
from .command_prompt_common import get_blurred_background, create_back_button

class DNSC2Minigame:
    def __init__(self, screen_width, screen_height, on_complete_callback):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        
        # Данные атаки T1071
        self.attack_data = {
            "technique": "T1071.004 - DNS",
            "description": "C2 канал через DNS протокол для скрытного управления",
            "c2_domain": "system-updates-service.net",
            "analysis_steps": {
                "dns_analysis": {
                    "title": "1. Анализ DNS трафика C2",
                    "content": [
                        "ОБНАРУЖЕН СКРЫТЫЙ КАНАЛ УПРАВЛЕНИЯ ЧЕРЕЗ DNS",
                        "",
                        "КАК РАБОТАЕТ DNS C2:",
                        "КЛИЕНТ → СЕРВЕР:",
                        "   - Злоумышленник кодирует команды в Base64",
                        "   - Создает поддомены: [base64].бот_ид.C2-домен",
                        "   - Пример: aG9zdG5hbWU=.bot123.system-updates-service.net",
                        "   - DNS запрос выглядит как легитимный",
                        "",
                        "СЕРВЕР → КЛИЕНТ:",
                        "   - C2 сервер декодирует: aG9zdG5hbWU= → 'hostname'",
                        "   - Отправляет команду через TXT запись",
                        "   - Клиент выполняет команду и отправляет результат",
                        "",
                        "КЛЮЧЕВЫЕ ПРИЗНАКИ:",
                        "   - Высокоэнтропийные поддомены (Base64)",
                        "   - Частые TXT запросы к одному домену",
                        "   - Регулярные beacon-запросы каждые 5-10 сек",
                        "",
                        "ЦЕЛЬ АТАКИ:",
                        "   - Скрытное управление без открытия портов",
                        "   - Обход межсетевых экранов",
                        "   - Маскировка под легитимный DNS трафик"
                    ]
                },
                "c2_mechanism": {
                    "title": "2. Механизм обхода защиты",
                    "content": [
                        " КАК C2 ОБХОДИТ ЗАЩИТУ:",
                        "",
                        "МАСКИРОВКА ПОД ЛЕГИТИМНЫЙ ТРАФИК:",
                        "   - DNS запросы редко блокируются",
                        "   - Высокий уровень шума (тысячи легитимных запросов)",
                        "   - Сложность отличить C2 от нормального трафика",
                        "",
                        "ШИФРОВАНИЕ ДАННЫХ:",
                        "   - Base64 кодирование скрывает содержимое",
                        "   - Можно добавить AES/XOR шифрование",
                        "   - Энтропия выглядит как случайные данные",
                        "",
                        "ТАКТИКА ВРЕМЕНИ:",
                        "   - Запросы с случайными интервалами",
                        "   - Jitter (джиттер) для смазывания паттернов",
                        "   - Beaconing каждые 5-10 секунд с вариациями",
                        "",
                        "РАСПРЕДЕЛЕНИЕ:",
                        "   - Использование публичных DNS резолверов (8.8.8.8)",
                        "   - Легитимные домены для маскировки",
                        "   - Разные типы DNS записей (TXT, CNAME, A)"
                    ]
                },
                "mitigation": {
                    "title": "3. Обнаружение и нейтрализация",
                    "content": [
                        " МЕТОДЫ ОБНАРУЖЕНИЯ DNS C2:",
                        "",
                        "АНАЛИТИКА ТРАФИКА:",
                        "   - Мониторинг частоты DNS запросов",
                        "   - Анализ энтропии поддоменов",
                        "   - Выявление аномальных TXT запросов",
                        "   - Корреляция по источникам и времени",
                        "",
                        "АКТИВНЫЕ МЕРЫ БЛОКИРОВКИ:",
                        "   - DNS фильтрация подозрительных доменов",
                        "   - Ограничение внешних DNS запросов",
                        "   - DNS sinkholing (перенаправление на ловушку)",
                        "   - Блокировка по репутации доменов",
                        "",
                        "НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ:",
                        "   - Блокировка C2 домена в firewall",
                        "   - Добавление в черный список DNS",
                        "   - Изоляция зараженного хоста",
                        "   - Аудит процессов и сетевых соединений",
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
        
        # Финальный квиз
        self.show_final_quiz = False
        self.quiz_questions = get_quiz_questions(4, 3)
        self.quiz = None
        
        # Отчет
        self.show_report = False
        self.show_tutorial = True
        self.tutorial_close_rect = None
        self.game_active = True
        self.game_time = 600
        self.timer = self.game_time

    def _create_buttons(self):
        """Создание кнопок для анализа"""
        button_width, button_height = 450, 35
        start_x = 50
        start_y = 350
        
        buttons_data = [
            ("1. Анализ DNS трафика C2", self.start_dns_analysis, theme.ACCENT),
            ("2. Механизм обхода защиты", self.start_c2_mechanism, (150, 100, 200)),
            ("3. Обнаружение и нейтрализация", self.start_mitigation, (200, 100, 100)),
            ("---", None, (0, 0, 0)),
            ("Блокировать С-2", self.show_command_prompt_window, (200, 0, 0)),
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
        self.exit_to_desktop_button = Button(
            self.screen_width - 130, 20, 110, 36, "Назад", (120, 120, 120),
            lambda: self.on_complete(False)
        )

    # Методы для кнопок
    def start_dns_analysis(self):
        self.current_step = "dns_analysis"
        if "dns_analysis" not in self.completed_steps:
            self.completed_steps.append("dns_analysis")

    def start_c2_mechanism(self):
        self.current_step = "c2_mechanism"
        if "c2_mechanism" not in self.completed_steps:
            self.completed_steps.append("c2_mechanism")

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

    def handle_command(self, command):
        """Обработка команд для блокировки C2"""
        cmd_lower = command.strip().lower()

        # Правильная команда для блокировки домена в Windows Firewall
        if cmd_lower == 'skip' or cmd_lower == "netsh advfirewall firewall add rule name=\"block c2\" dir=out action=block remoteip=system-updates-service.net":
            self.command_success = True
            self.completed_steps.append("C2 домен заблокирован через firewall")
            # После успешной команды показываем квиз
            self.show_command_prompt = False
            self.show_final_quiz = True
            self.quiz = QuizEngine(self.screen_width, self.screen_height, self.quiz_questions, "ФИНАЛЬНЫЙ ТЕСТ")
            return True
        return False

    def handle_event(self, event):
        if self.show_tutorial and event.type == pygame.MOUSEBUTTONDOWN:
            if self.tutorial_close_rect and self.tutorial_close_rect.collidepoint(event.pos):
                self.show_tutorial = False
                return True
        if self.show_report:
            # В режиме отчета клик в любом месте закрывает мини-игру
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.on_complete(True, self.quiz.score, self.quiz.mistakes)
                return True
            return

        if not self.game_active and not self.show_final_quiz:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.on_complete(False)
            return

        if self.show_final_quiz:
            handled = self.quiz.handle_event(event)
            if self.quiz.finished:
                self.show_final_quiz = False
                self.show_report = True
                self.completed_steps.append("Финальный квиз завершен!")
                self.game_active = False
            return handled
        
        if self.show_command_prompt:
            if self.command_back_button.handle_event(event):
                return True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.command_history.append(f"C:\\Windows\\System32>{self.command_text}")
                    self.handle_command(self.command_text)
                    self.command_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.command_text = self.command_text[:-1]
                else:
                    self.command_text += event.unicode
                return True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Клик вне командной строки закрывает её
                cmd_rect = pygame.Rect(100, 150, self.screen_width - 200, 400)
                if not cmd_rect.collidepoint(event.pos):
                    self.show_command_prompt = False
                return True
        
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
        if self.show_report:
            return
            
        if not self.game_active and not self.show_final_quiz:
            return
            
        self.timer -= 1/60
        if self.timer <= 0:
            self.timer = 0
            self.game_active = False
            self.completed_steps.append("Время вышло! Атака успешна")
        
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
        
        # Заголовок
        title = self.font_large.render("РАССЛЕДОВАНИЕ: DNS C2", True, (255, 255, 255))
        screen.blit(title, (self.screen_width//2 - title.get_width()//2, 20))
        
        # Счет и таймер
        score_text = self.font_small.render(f"Очки: {self.quiz.score if self.quiz else 0}", True, theme.WARNING)
        screen.blit(score_text, (self.screen_width - 100, 20))

        timer_color = theme.DANGER if self.timer < 60 else (255, 255, 255)
        timer_text = self.font_medium.render(f"Время: {int(self.timer)}с", True, timer_color)
        screen.blit(timer_text, (self.screen_width - 150, 45))

        if self.show_report:
            self.draw_report_screen(screen)
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
        title = tutorial_font.render("ИНСТРУКЦИЯ (Уровень 4)", True, theme.WARNING)
        screen.blit(title, (tutorial_rect.centerx - title.get_width()//2, tutorial_rect.y + 15))
        small_font = pygame.font.Font(None, 18)
        instructions = [
            "1. Изучите анализ DNS трафика и механизм C2",
            "2. Откройте «Блокировать С-2» и введите команду",
            "3. Заблокируйте домен в Windows Firewall",
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
            "ОБНАРУЖЕН СКРЫТЫЙ КАНАЛ УПРАВЛЕНИЯ: DNS C2",
            "",
            "C2 домен: system-updates-service.net",
            "Техника MITRE: T1071.004 - Application Layer Protocol: DNS",
            "Механизм: Команды передаются через DNS поддомены",
            "Маскировка: Легитимный DNS трафик",
            "",
            "Проведите полное расследование:"
        ]
        
        for i, line in enumerate(description):
            color = theme.DANGER if "ОБНАРУЖЕН" in line else (255, 255, 255)
            if "C2 домен" in line: color = theme.DANGER
            if "Техника MITRE" in line: color = theme.WARNING
            if "Механизм" in line: color = (100, 200, 255)
            if "Маскировка" in line: color = (200, 100, 255)
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
            if line.startswith("   -"): color = (200, 200, 255)
            else: color = (255, 255, 255)
            text = self.font_small.render(line, True, color)
            screen.blit(text, (70, y_pos))
            y_pos += line_height
        screen.set_clip(None)
        
        self.back_button.draw(screen)
        self.exit_to_desktop_button.draw(screen)

    def draw_command_prompt(self, screen):
        """Отрисовка командной строки для блокировки C2"""
        screen.blit(self._cmd_blurred_bg, (0, 0))
        self.command_back_button.draw(screen)
        # Фон командной строки
        cmd_rect = pygame.Rect(100, 100, self.screen_width - 200, 400)
        pygame.draw.rect(screen, (0, 0, 0), cmd_rect)
        pygame.draw.rect(screen, (200, 200, 200), cmd_rect, 2)
        
        # Заголовок окна
        title_bar = pygame.Rect(100, 80, self.screen_width - 200, 20)
        pygame.draw.rect(screen, (0, 0, 128), title_bar)
        title_text = self.font_small.render("Командная строка Windows - Блокировка C2", True, (255, 255, 255))
        screen.blit(title_text, (110, 82))
        
        # История команд
        y_pos = cmd_rect.y + 20
        max_history_lines = 12
        
        # Показать последние команды из истории
        start_index = max(0, len(self.command_history) - max_history_lines)
        for i in range(start_index, len(self.command_history)):
            if y_pos > cmd_rect.y + cmd_rect.height - 60:
                break
            history_text = self.font_mono.render(self.command_history[i], True, (255, 255, 255))
            screen.blit(history_text, (cmd_rect.x + 10, y_pos))
            y_pos += 20
        
        # Текущая строка ввода
        prompt_text = self.font_mono.render("C:\\Windows\\System32>", True, (255, 255, 255))
        screen.blit(prompt_text, (cmd_rect.x + 10, y_pos))
        
        # Введенная команда
        cmd_display = self.font_mono.render(self.command_text, True, (255, 255, 255))
        screen.blit(cmd_display, (cmd_rect.x + 180, y_pos))
        
        # Мигающий курсор
        if pygame.time.get_ticks() % 1000 < 500:
            cursor_x = cmd_rect.x + 180 + cmd_display.get_width()
            pygame.draw.rect(screen, (255, 255, 255), (cursor_x, y_pos, 8, 18))
        
        # Инструкция внизу
        instruction_rect = pygame.Rect(100, cmd_rect.y + cmd_rect.height + 10, self.screen_width - 200, 80)
        pygame.draw.rect(screen, theme.SURFACE_ALT, instruction_rect, border_radius=5)
        pygame.draw.rect(screen, theme.BORDER, instruction_rect, 1, border_radius=5)
        
        instruction1 = self.font_small.render("Введите команду для блокировки C2 домена в Windows Firewall:", True, theme.WARNING)
        screen.blit(instruction1, (instruction_rect.centerx - instruction1.get_width()//2, instruction_rect.y + 10))
        
        instruction2 = self.font_mono.render("netsh advfirewall firewall add rule name=\"block c2\" dir=out action=block remoteip=system-updates-service.net", True, theme.SUCCESS_SOFT)
        screen.blit(instruction2, (instruction_rect.centerx - instruction2.get_width()//2, instruction_rect.y + 35))
        
        if self.command_success:
            success_rect = pygame.Rect(100, instruction_rect.y + 90, self.screen_width - 200, 40)
            pygame.draw.rect(screen, (0, 100, 0), success_rect, border_radius=5)
            success_text = self.font_medium.render("УСПЕХ: C2 домен system-updates-service.net заблокирован!", True, (255, 255, 255))
            screen.blit(success_text, (success_rect.centerx - success_text.get_width()//2, success_rect.y + 10))

    def draw_report_screen(self, screen):
        """Отрисовка финального отчета (как в phishing)"""
        report_rect = pygame.Rect(
            self.screen_width // 2 - 300,
            self.screen_height // 2 - 200,
            600, 400
        )
        pygame.draw.rect(screen, theme.SURFACE, report_rect, border_radius=15)
        pygame.draw.rect(screen, theme.ACCENT, report_rect, 3, border_radius=15)
        
        # Заголовок отчета
        title_font = pygame.font.Font(None, 36)
        title = title_font.render("ФИНАЛЬНЫЙ ОТЧЕТ", True, theme.SUCCESS)
        screen.blit(title, (report_rect.centerx - title.get_width()//2, report_rect.y + 30))
        
        # Статистика
        stats_font = pygame.font.Font(None, 28)
        small_font = pygame.font.Font(None, 22)
        
        y_pos = report_rect.y + 80
        
        # Очки
        score_text = stats_font.render(f"Набрано очков: {self.quiz.score}/{self.quiz.max_score}", True, theme.WARNING)
        screen.blit(score_text, (report_rect.centerx - score_text.get_width()//2, y_pos))
        y_pos += 40

        # Время
        time_text = small_font.render(f"Оставшееся время: {int(self.timer)}с", True, (200, 200, 255))
        screen.blit(time_text, (report_rect.centerx - time_text.get_width()//2, y_pos))
        y_pos += 30

        # Выполненные этапы анализа
        analysis_steps = ["dns_analysis", "c2_mechanism", "mitigation"]
        completed_analysis_steps = [step for step in analysis_steps if step in self.completed_steps]
        completed_text = small_font.render(f"Выполнено этапов анализа: {len(completed_analysis_steps)}/3", True, theme.SUCCESS_SOFT)
        screen.blit(completed_text, (report_rect.centerx - completed_text.get_width()//2, y_pos))
        y_pos += 30

        # Правильные ответы в квизе
        quiz_text = small_font.render(f"Правильных ответов в тесте: {self.quiz.correct_count}/{self.quiz.total_questions}", True, theme.SUCCESS_SOFT)
        screen.blit(quiz_text, (report_rect.centerx - quiz_text.get_width()//2, y_pos))
        y_pos += 40

        # Итоговая оценка
        if self.quiz.score >= self.quiz.max_score * 0.7:
            grade = "ОТЛИЧНО"
            color = theme.SUCCESS
        elif self.quiz.score >= self.quiz.max_score * (11 / 30):
            grade = "ХОРОШО"
            color = theme.WARNING
        else:
            grade = "НЕУДОВЛЕТВОРИТЕЛЬНО"
            color = theme.DANGER

        grade_text = stats_font.render(f"ИТОГОВАЯ ОЦЕНКА: {grade}", True, color)
        screen.blit(grade_text, (report_rect.centerx - grade_text.get_width()//2, y_pos))
        y_pos += 50

        # Рекомендации
        if self.quiz.score < self.quiz.max_score * (25 / 30):
            advice_text = small_font.render("Рекомендуется повторить материал по DNS C2 атакам", True, theme.WARNING)
            screen.blit(advice_text, (report_rect.centerx - advice_text.get_width()//2, y_pos))
        else:
            advice_text = small_font.render("Отличная работа! Вы успешно справились с угрозой", True, theme.SUCCESS)
            screen.blit(advice_text, (report_rect.centerx - advice_text.get_width()//2, y_pos))
        
        y_pos += 40
        
        # Инструкция для закрытия
        instruction_font = pygame.font.Font(None, 18)
        instruction = instruction_font.render("Нажмите в любом месте для возврата на рабочий стол", True, (200, 200, 255))
        screen.blit(instruction, (report_rect.centerx - instruction.get_width()//2, report_rect.y + report_rect.height - 40))

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if self.quiz:
            self.quiz.on_resize(w, h)

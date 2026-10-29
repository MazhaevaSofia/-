# game/scenes/valid_account_minigame.py

import pygame
from ..ui.button import Button
from ..ui import theme
from ..ui.quiz_engine import QuizEngine
from ..data.quiz_data import get_quiz_questions

class ValidAccountsMinigame:
    def __init__(self, screen_width, screen_height, on_complete_callback, game_manager=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        self.game_manager = game_manager
        
        # Данные инцидента
        self.incident_data = {
            "compromised_user": "Волков Д.С. (HR)",
            "siem_logs": [
                {"time": "23:40", "user": "Волков Д.С. (HR)", "action": "Вход в систему", "risk": "medium"},
                {"time": "23:42", "user": "Волков Д.С. (HR)", "action": "Доступ к финансовым отчетам", "risk": "high"},
                {"time": "23:45", "user": "Волков Д.С. (HR)", "action": "Попытка доступа к БД сотрудников", "risk": "critical"},
                {"time": "23:47", "user": "Волков Д.С. (HR)", "action": "Скачивание архивов с документами", "risk": "critical"},
                {"time": "23:50", "user": "Волков Д.С. (HR)", "action": "Попытка эскалации привилегий", "risk": "critical"},
            ],
            "analysis_steps": {
                "anomaly_analysis": {
                    "title": "1. Анализ аномальной активности (SIEM)",
                    "content": [
                        "АНАЛИЗ АНОМАЛИЙ:",
                        "",
                        "- Время: Вход в систему в 23:40 (нерабочее время)",
                        "- IP-адрес: 192.168.1.150 (нетипичный IP)",
                        "- Тактика MITRE: T1078 - Valid Accounts",
                        "",
                        "ВЫВОД:",
                        "Обнаружены явные признаки компрометации.",
                        "Активность в нерабочее время — главный индикатор."
                    ],
                    "highlight_logs": [0]
                },
                "account_analysis": {
                    "title": "2. Анализ учетной записи",
                    "content": [
                        "АНАЛИЗ УЧЕТНОЙ ЗАПИСИ:",
                        "",
                        "- Пользователь: Волков Д.С. (Отдел кадров - HR)",
                        "- Обычные часы: 09:00-18:00",
                        "- Типичный доступ: HR-системы, база сотрудников",
                        "",
                        "КРИТИЧЕСКИЕ ОТКЛОНЕНИЯ:",
                        "- Сотрудник HR обращается к 'финансовым отчетам'",
                        "- Попытка 'повысить привилегии'",
                        "",
                        "ВЫВОД:",
                        "Учетная запись определенно скомпрометирована."
                    ],
                    "highlight_logs": [1, 4]
                },
                "mitigation_steps": {
                    "title": "3. Методы борьбы (MITRE)",
                    "content": [
                        "МЕТОДЫ БОРЬБЫ (MITRE ATT&CK):",
                        "",
                        "- M1032: Многофакторная аутентификация (MFA)",
                        "  (Главный метод защиты от кражи пароля)",
                        "- M1027: Строгие политики паролей",
                        "- M1036: Политики условного доступа (блокировка по IP/времени)",
                        "- Мониторинг поведения (то, что сделала SIEM)",
                        "- M1026: Принцип наименьших привилегий",
                        "  (HR не должен иметь доступа к финансам)",
                        "",
                        "ВЫВОД:",
                        "Необходимо внедрение MFA и аудит привилегий."
                    ],
                    "highlight_logs": []
                }
            }
        }
        
        # Вопросы для финального квиза (3 случайных из пула для уровня 2)
        self.quiz_questions = get_quiz_questions(2, 3)

        # Состояние игры
        self.completed_steps = []
        self.current_analysis = None
        self.game_time = 600
        self.timer = self.game_time
        self.game_active = True

        # Финальный квиз
        self.show_final_quiz = False
        self.final_quiz_answered = False
        self.quiz = None

        self.show_report = False
        
        # Кнопки
        self.buttons = []
        self._create_buttons()
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)
        self.font_tiny = pygame.font.Font(None, 16)
        
        # Туториал
        self.show_tutorial = True
        self.tutorial_close_rect = None

    def _create_buttons(self):
        button_width, button_height = 320, 35
        start_x = 50
        start_y = 100
        
        buttons_data = [
            ("1. Анализ аномалий (SIEM)", self.start_anomaly_analysis, (0, 100, 200)),
            ("2. Анализ учетной записи", self.start_account_analysis, (0, 150, 100)),
            ("3. Изучить методы борьбы", self.start_mitigation_analysis, (100, 200, 255)),
            ("---", None, (0,0,0)),
            ("ИЗОЛИРОВАТЬ ХОСТ", self.isolate_host, (200, 0, 0)),
            ("ЗАБЛОКИРОВАТЬ АККАУНТ", self.block_account, (200, 100, 0)),
            ("СБРОСИТЬ ПАРОЛЬ", self.reset_password, (100, 0, 200)),
        ]
        
        i = 0
        for text, callback, color in buttons_data:
            if text == "---":
                i += 0.5
                continue
            
            button = Button(
                start_x, start_y + int(i * 42),
                button_width, button_height,
                text, color, callback
            )
            self.buttons.append(button)
            i += 1
        
        self.back_button = Button(
            50, self.screen_height - 55,
            120, 35, "Назад", (20, 120, 100), self.back_to_main
        )

    # Callbacks
    def start_anomaly_analysis(self):
        self.current_analysis = "anomaly_analysis"
        if "anomaly_analysis" not in self.completed_steps:
            self.completed_steps.append("anomaly_analysis")

    def start_account_analysis(self):
        self.current_analysis = "account_analysis"
        if "account_analysis" not in self.completed_steps:
            self.completed_steps.append("account_analysis")

    def start_mitigation_analysis(self):
        self.current_analysis = "mitigation_steps"
        if "mitigation_steps" not in self.completed_steps:
            self.completed_steps.append("mitigation_steps")

    def back_to_main(self):
        self.current_analysis = None

    _REQUIRED_DAY2_STEPS = ["isolate_host", "block_account", "reset_password"]

    def _is_day2_task_completed(self):
        """Задание дня 2 завершено: изолировать хост, заблокировать аккаунт, сбросить пароль."""
        return all(s in self.completed_steps for s in self._REQUIRED_DAY2_STEPS)

    def _try_start_final_quiz(self):
        """Запустить викторину только после всех 3 действий: изолировать хост, заблокировать аккаунт, сбросить пароль."""
        if self._is_day2_task_completed() and not self.show_final_quiz and not self.final_quiz_answered:
            self.start_final_quiz()

    def isolate_host(self):
        if "isolate_host" not in self.completed_steps:
            self.completed_steps.append("isolate_host")
            self.completed_steps.append("Хост 192.168.1.150 изолирован от сети")
            self._try_start_final_quiz()

    def block_account(self):
        if "block_account" not in self.completed_steps:
            self.completed_steps.append("block_account")
            self.completed_steps.append("Учетная запись Волкова Д.С. заблокирована")
            self._try_start_final_quiz()

    def reset_password(self):
        if "reset_password" not in self.completed_steps:
            self.completed_steps.append("reset_password")
            self.completed_steps.append("Пароль для Волкова Д.С. сброшен")
            self._try_start_final_quiz()

    def start_final_quiz(self):
        """Запуск финального квиза"""
        if self.show_final_quiz: return # Не запускать дважды
        self.show_final_quiz = True
        self.final_quiz_answered = False
        self.quiz = QuizEngine(self.screen_width, self.screen_height, self.quiz_questions, "ФИНАЛЬНЫЙ ТЕСТ")

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
                self.final_quiz_answered = True
                self.show_final_quiz = False
                self.show_report = True
                self.completed_steps.append("Финальный квиз завершен!")
                self.game_active = False
            return handled
        
        if self.current_analysis is not None:
            if self.back_button.handle_event(event): 
                return True
        else:
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
        
        if self.current_analysis is not None:
            self.back_button.update()
        else:
            for button in self.buttons: 
                button.update()
        
        if self.show_final_quiz:
            self.quiz.update()

    def draw(self, screen):
        screen.fill(theme.BG)
        
        title = self.font_large.render("РАССЛЕДОВАНИЕ ИНЦИДЕНТА: T1078 Valid Accounts", True, (255, 255, 255))
        screen.blit(title, (self.screen_width//2 - title.get_width()//2, 15))
        
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
        elif self.current_analysis is not None:
            self.draw_analysis_screen(screen)
        else:
            self.draw_incident_details(screen)
            for button in self.buttons: 
                button.draw(screen)
        
        if self.show_tutorial: 
            self.draw_tutorial(screen)

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
        analysis_steps = ["anomaly_analysis", "account_analysis", "mitigation_steps"]
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
            advice_text = small_font.render("Рекомендуется повторить материал по компрометации учетных записей", True, theme.WARNING)
            screen.blit(advice_text, (report_rect.centerx - advice_text.get_width()//2, y_pos))
        else:
            advice_text = small_font.render("Отличная работа! Вы успешно справились с угрозой", True, theme.SUCCESS)
            screen.blit(advice_text, (report_rect.centerx - advice_text.get_width()//2, y_pos))
        
        y_pos += 40
        
        # Инструкция для закрытия
        instruction_font = pygame.font.Font(None, 18)
        instruction = instruction_font.render("Нажмите в любом месте для возврата на рабочий стол", True, (200, 200, 255))
        screen.blit(instruction, (report_rect.centerx - instruction.get_width()//2, report_rect.y + report_rect.height - 40))

    def draw_analysis_screen(self, screen):
        analysis_bg = pygame.Rect(50, 70, self.screen_width - 100, self.screen_height - 150)
        pygame.draw.rect(screen, theme.SURFACE_ALT, analysis_bg, border_radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.BORDER, analysis_bg, 2, border_radius=theme.RADIUS_LG)
        
        # Отрисовка логов SIEM с выделениями
        siem_rect = pygame.Rect(60, 80, 450, 400)
        self.draw_siem_logs_mini(screen, siem_rect)
        
        # Выделение
        stage_data = self.incident_data["analysis_steps"][self.current_analysis]
        self.draw_highlights(screen, siem_rect, stage_data.get("highlight_logs", []))
        
        # Теоритический материал
        text_x = 530
        title = self.font_large.render(stage_data["title"], True, (255, 255, 255))
        screen.blit(title, (text_x, 80))
        
        y_pos = 130
        for line in stage_data["content"]:
            if line == "":
                y_pos += 10
                continue
            
            color = theme.WARNING if any(marker in line for marker in ["АНАЛИЗ", "КРИТИЧЕСКИЕ", "ВЫВОД"]) else (255, 255, 255)
            font = self.font_medium if any(marker in line for marker in ["АНАЛИЗ"]) else self.font_small
            
            text_surface = font.render(line, True, color)
            screen.blit(text_surface, (text_x, y_pos))
            y_pos += 25
        
        self.back_button.draw(screen)

    def draw_highlights(self, screen, siem_rect, log_indices):
        pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500
        border_color = theme.DANGER
        
        for index in log_indices:
            y_pos = siem_rect.y + 40 + index * 35
            highlight_rect = pygame.Rect(siem_rect.x, y_pos, siem_rect.width, 30)
            
            highlight_surface = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
            highlight_surface.fill((255, 100, 100, 100))
            screen.blit(highlight_surface, highlight_rect.topleft)
            
            pygame.draw.rect(screen, border_color, highlight_rect, int(2 + pulse * 2))

    def draw_siem_logs_mini(self, screen, siem_rect):
        pygame.draw.rect(screen, (255, 255, 255), siem_rect)
        pygame.draw.rect(screen, (200, 200, 200), siem_rect, 1)
        
        font_small = pygame.font.Font(None, 16)
        font_tiny = pygame.font.Font(None, 14)
        
        headers = ["Время", "Пользователь", "Событие", "Риск"]
        x_pos_list = [siem_rect.x + 10, siem_rect.x + 60, siem_rect.x + 180, siem_rect.x + 380]
        
        for i, header in enumerate(headers):
            header_text = font_small.render(header, True, (0, 0, 0))
            screen.blit(header_text, (x_pos_list[i], siem_rect.y + 10))
        
        pygame.draw.line(screen, (200, 200, 200), (siem_rect.x, siem_rect.y + 30), (siem_rect.right, siem_rect.y + 30), 1)

        for i, log in enumerate(self.incident_data["siem_logs"]):
            y_pos = siem_rect.y + 40 + i * 35
            
            risk_colors_bg = {
                "medium": (255, 255, 220), "high": (255, 230, 220), "critical": (255, 210, 210)
            }
            log_rect = pygame.Rect(siem_rect.x, y_pos, siem_rect.width, 30)
            pygame.draw.rect(screen, risk_colors_bg[log["risk"]], log_rect)
            
            risk_colors_text = {
                "medium": (200, 180, 0), "high": (200, 100, 0), "critical": (200, 0, 0)
            }
            color = risk_colors_text[log["risk"]]

            screen.blit(font_tiny.render(log["time"], True, color), (x_pos_list[0], y_pos + 8))
            screen.blit(font_tiny.render(log["user"], True, color), (x_pos_list[1], y_pos + 8))
            screen.blit(font_tiny.render(log["action"][:30], True, color), (x_pos_list[2], y_pos + 8))
            screen.blit(font_tiny.render(log["risk"].upper(), True, color), (x_pos_list[3], y_pos + 8))
            
    def draw_incident_details(self, screen):
        # Главный экран с логами SIEM
        siem_rect = pygame.Rect(400, 80, 500, 500)
        self.draw_siem_logs_mini(screen, siem_rect)
        
        # Задачи (лог действий), текст не выходит за границы
        tasks_rect = pygame.Rect(50, 420, 320, 200)
        pygame.draw.rect(screen, theme.SURFACE_ALT, tasks_rect, border_radius=5)
        pygame.draw.rect(screen, theme.BORDER, tasks_rect, 1, border_radius=5)
        tasks_title = self.font_medium.render("Выполненные задачи:", True, theme.WARNING)
        screen.blit(tasks_title, (tasks_rect.x + 10, tasks_rect.y + 10))
        pad = 15
        max_w = tasks_rect.width - 2 * pad
        y_pos = tasks_rect.y + 40
        for step in self.completed_steps:
            if y_pos > tasks_rect.bottom - 20:
                break
            raw = "- " + str(step)
            if self.font_tiny.size(raw)[0] > max_w:
                while len(raw) > 2 and self.font_tiny.size(raw + "...")[0] > max_w:
                    raw = raw[:-1]
                raw = raw.rstrip() + "..."
            step_text = self.font_tiny.render(raw, True, theme.SUCCESS)
            screen.blit(step_text, (tasks_rect.x + pad, y_pos))
            y_pos += 20

    def draw_tutorial(self, screen):
        tutorial_rect = pygame.Rect(self.screen_width // 2 - 200, self.screen_height // 2 - 75, 400, 150)
        pygame.draw.rect(screen, theme.SURFACE, tutorial_rect, border_radius=10)
        pygame.draw.rect(screen, theme.ACCENT, tutorial_rect, 2, border_radius=10)

        # Кнопка закрытия в стиле остальных окон проекта
        self.tutorial_close_rect = pygame.Rect(tutorial_rect.right - 24, tutorial_rect.y + 8, 16, 16)
        pygame.draw.rect(screen, theme.DANGER, self.tutorial_close_rect)
        pygame.draw.rect(screen, (0, 0, 0), self.tutorial_close_rect, 1)
        pygame.draw.line(
            screen,
            (255, 255, 255),
            (self.tutorial_close_rect.x + 4, self.tutorial_close_rect.y + 4),
            (self.tutorial_close_rect.x + 12, self.tutorial_close_rect.y + 12),
            2
        )
        pygame.draw.line(
            screen,
            (255, 255, 255),
            (self.tutorial_close_rect.x + 12, self.tutorial_close_rect.y + 4),
            (self.tutorial_close_rect.x + 4, self.tutorial_close_rect.y + 12),
            2
        )
        
        tutorial_font = pygame.font.Font(None, 24)
        title = tutorial_font.render("ИНСТРУКЦИЯ (Уровень 2)", True, theme.WARNING)
        screen.blit(title, (tutorial_rect.centerx - title.get_width()//2, tutorial_rect.y + 15))
        
        small_font = pygame.font.Font(None, 18)
        instructions = [
            "1. Изучите логи SIEM",
            "2. Проведите анализ всех этапов",
            "3. Выполните защитные действия (Блокировка)",
            "4. Пройдите финальный тест"
        ]
        
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (255, 255, 255))
            screen.blit(text, (tutorial_rect.x + 20, tutorial_rect.y + 45 + i * 20))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if self.quiz:
            self.quiz.on_resize(w, h)

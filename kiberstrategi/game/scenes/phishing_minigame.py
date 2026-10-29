import pygame
from ..ui.button import Button
from ..ui import theme
from ..ui.quiz_engine import QuizEngine
from ..data.quiz_data import get_quiz_questions

class PhishingMinigame:
    def __init__(self, screen_width, screen_height, on_complete_callback, game_manager=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        self.game_manager = game_manager
        
        # Данные фишинг атаки
        self.phishing_email = {
            "sender": "oshptu@mail.grodno.by",
            "subject": "С/ф проверить",
            "body": """
Уважаемый коллега,

Прошу проверить и обработать приложенный счет-фактуру. 
Документ требует срочного внимания - оплата должна быть произведена 
в течение сегодняшнего дня во избежание проблем с контрагентом.

В приложении находится файл со счетом. Пожалуйста, откройте его 
и проверьте все реквизиты.

С уважением,
Дарья Ларионова
Отдел бухгалтерии
            """,
            "attachment": "Oplata 18.02.001",
            "time": "22:45",
            "red_flags": [
                "Отправитель: oshptu@mail.grodno.by (личная почта)",
                "Время отправки: 22:45 (нерабочее время)",
                "Файл с расширением .001 (нестандартное для документов)",
                "Транслитерация в названии файла",
                "Срочность и эмоциональное давление",
                "Сотрудник не работает в бухгалтерии"
            ],
            "analysis_steps": {
                "sender_time_analysis": {
                    "title": "1. Анализ отправителя и времени отправления",
                    "content": [
                        "АНАЛИЗ ОТПРАВИТЕЛЯ И ВРЕМЕНИ:",
                        "",
                        "- Сообщение пришло от неизвестного сотруднику лица",
                        "- Время отправки: 22:45 (нерабочее время)",
                        "- Тактика нарушителя: 'ЛЮБОПЫТСТВО'",
                        "",
                        "КРИТИЧЕСКИЕ ПРИЗНАКИ:",
                        "- Деловая переписка в нерабочее время",
                        "- Сообщение отправлено не по назначению",
                        "- Эмоциональная окраска текста",
                        "",
                        "ВЫВОД:",
                        "Используется тактика 'любопытства' для побуждения к действию"
                    ],
                    "highlight": ["sender", "time", "urgency_text"]
                },
                "sender_address_analysis": {
                    "title": "2. Анализ почтового адреса отправителя",
                    "content": [
                        "АНАЛИЗ АДРЕСА ОТПРАВИТЕЛЯ:",
                        "",
                        "- Почтовый адрес: oshptu@mail.grodno.by",
                        "- Домен отправителя: mail.grodno.by",
                        "- Поставщик услуг: Белтелеком",
                        "",
                        "КРИТИЧЕСКИЕ ПРИЗНАКИ:",
                        "- Наименование 'oshptu' не соответствует 'Дарье Ларионовой'",
                        "- Личный домен вместо корпоративной почты",
                        "- Отсутствие связи с реальной организацией",
                        "",
                        "ВЫВОД:",
                        "Адрес отправителя является поддельным"
                    ],
                    "highlight": ["sender_address", "domain"]
                },
                "content_analysis": {
                    "title": "3. Анализ текста сообщения и оформления", 
                    "content": [
                        "АНАЛИЗ СОДЕРЖАНИЯ ПИСЬМА:",
                        "",
                        "- Тема: 'С/ф проверить' (счет-фактура)",
                        "- Содержание: просьба обработать финансовый документ",
                        "- Эмоциональная окраска: срочность, давление",
                        "",
                        "КРИТИЧЕСКИЕ ПРИЗНАКИ:",
                        "- Сотрудник не работает в бухгалтерии",
                        "- Счет-фактура - информация ограниченного распространения", 
                        "- Тактика управления действиями получателя",
                        "- Призыв к открытию подозрительного файла",
                        "",
                        "ВЫВОД:",
                        "Письмо использует давление для побуждения к открытию файла"
                    ],
                    "highlight": ["subject", "body_text", "urgency_phrase"]
                },
                "attachment_type_analysis": {
                    "title": "4. Анализ типа вложения",
                    "content": [
                        "АНАЛИЗ ТИПА ВЛОЖЕНИЯ:",
                        "",
                        "- Имя файла: Oplata 18.02.001",
                        "- Расширение: .001 (нестандартное)",
                        "- Ожидаемый формат: PDF или Excel",
                        "",
                        "КРИТИЧЕСКИЕ ПРИЗНАКИ:",
                        "- Нестандартное расширение для документа",
                        "- Должен быть PDF/Excel, а не .001",
                        "- Неизвестный бинарный формат",
                        "",
                        "ВЫВОД:",
                        "Файл имеет подозрительное расширение"
                    ],
                    "highlight": ["attachment_type"]
                },
                "attachment_name_analysis": {
                    "title": "5. Анализ наименования вложения",
                    "content": [
                        "АНАЛИЗ НАИМЕНОВАНИЯ ВЛОЖЕНИЯ:",
                        "",
                        "- Полное имя: Oplata 18.02.001",
                        "- Русское название: 'Оплата 18.02'",
                        "- Написание: транслитерация",
                        "",
                        "КРИТИЧЕСКИЕ ПРИЗНАКИ:",
                        "- Русское название в латинской транслитерации",
                        "- Подозрительное имя файла",
                        "- Отсутствие профессионального оформления",
                        "",
                        "ВЫВОД:",
                        "Наименование файла вызывает подозрения"
                    ],
                    "highlight": ["attachment_name"]
                }
            }
        }
        
        # Вопросы для финального квиза (3 случайных из пула для уровня 1)
        self.quiz_questions = get_quiz_questions(1, 3)

        # Состояние игры
        self.completed_steps = []
        self.current_step = "main"
        self.game_time = 600
        self.timer = self.game_time
        self.game_active = True

        # Текущий этап анализа
        self.current_analysis = None

        # Флаг для финального квиза
        self.show_final_quiz = False
        self.final_quiz_answered = False
        self.quiz = None

        # Лог выполненных действий (зелёный текст под кнопками)
        self.action_log = []
        
        # Флаг для показа отчета
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
        """Создание кнопок для анализа"""
        button_width, button_height = 320, 35
        start_x = 50
        start_y = 180
        
        buttons_data = [
            ("Анализ отправителя и времени", self.start_sender_time_analysis, (0, 100, 200)),
            ("Анализ почтового адреса", self.start_sender_address_analysis, (0, 150, 100)),
            ("Анализ текста сообщения", self.start_content_analysis, (100, 200, 255)),
            ("Анализ типа вложения", self.start_attachment_type_analysis, (150, 100, 0)),
            ("Анализ наименования вложения", self.start_attachment_name_analysis, (100, 0, 200)),
            ("Заблокировать отправителя", self.block_sender, (200, 0, 100)),
            ("Уведомить сотрудников", self.notify_employees, (200, 100, 0)),
            ("Удалить письмо", self.delete_email, (100, 0, 200))
        ]
        
        for i, (text, callback, color) in enumerate(buttons_data):
            button = Button(
                start_x, start_y + i * 42,
                button_width, button_height,
                text, color, callback
            )
            self.buttons.append(button)
        
        # Кнопка "Назад" для теории (как в остальных расследованиях)
        self.back_button = Button(
            50, self.screen_height - 55,
            120, 35, "Назад", (20, 120, 100), self.back_to_main
        )

    def start_sender_time_analysis(self):
        self.current_analysis = "sender_time_analysis"
        if "sender_time_analysis" not in self.completed_steps:
            self.completed_steps.append("sender_time_analysis")

    def start_sender_address_analysis(self):
        self.current_analysis = "sender_address_analysis"
        if "sender_address_analysis" not in self.completed_steps:
            self.completed_steps.append("sender_address_analysis")

    def start_content_analysis(self):
        self.current_analysis = "content_analysis"
        if "content_analysis" not in self.completed_steps:
            self.completed_steps.append("content_analysis")

    def start_attachment_type_analysis(self):
        self.current_analysis = "attachment_type_analysis"
        if "attachment_type_analysis" not in self.completed_steps:
            self.completed_steps.append("attachment_type_analysis")

    def start_attachment_name_analysis(self):
        self.current_analysis = "attachment_name_analysis"
        if "attachment_name_analysis" not in self.completed_steps:
            self.completed_steps.append("attachment_name_analysis")

    def back_to_main(self):
        """Возврат на главный экран"""
        self.current_analysis = None

    def _required_task_steps(self):
        """Три последние кнопки задания: все должны быть нажаты перед викториной."""
        return ["block_sender", "notify_employees", "delete_email"]

    def _is_task_completed(self):
        """Задание завершено, если нажаты все 3 последние кнопки."""
        return all(step in self.completed_steps for step in self._required_task_steps())

    def _try_start_final_quiz(self):
        """Запустить викторину только после завершения задания (все 3 последние кнопки)."""
        if self._is_task_completed() and not self.show_final_quiz and not self.final_quiz_answered:
            self.start_final_quiz()

    def block_sender(self):
        if "block_sender" not in self.completed_steps:
            self.completed_steps.append("block_sender")
            self.completed_steps.append("Отправитель добавлен в черный список")
            self.action_log.append("block_sender")
            self.action_log.append("Отправитель добавлен в черный список")
            self._try_start_final_quiz()

    def notify_employees(self):
        if "notify_employees" not in self.completed_steps:
            self.completed_steps.append("notify_employees")
            self.completed_steps.append("Сотрудники уведомлены об угрозе")
            self.action_log.append("notify_employees")
            self.action_log.append("Сотрудники уведомлены об угрозе")
            self._try_start_final_quiz()

    def delete_email(self):
        if "delete_email" not in self.completed_steps:
            self.completed_steps.append("delete_email")
            self.completed_steps.append("Письмо удалено из системы")
            self.action_log.append("delete_email")
            self.action_log.append("Письмо удалено из системы")
            self._try_start_final_quiz()

    def start_final_quiz(self):
        """Запуск финального квиза из 3 вопросов"""
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
                self.on_complete(True)
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
        # Фон
        screen.fill(theme.BG)
        
        # Заголовок и счет
        title = self.font_large.render("РАССЛЕДОВАНИЕ ФИШИНГ АТАКИ", True, (255, 255, 255))
        screen.blit(title, (self.screen_width//2 - title.get_width()//2, 15))
        
        # Счет очков
        score_text = self.font_small.render(f"Очки: {self.quiz.score if self.quiz else 0}", True, theme.WARNING)
        screen.blit(score_text, (self.screen_width - 100, 20))

        # Таймер
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
            # Подозрительное письмо
            self.draw_phishing_email(screen)
            
            # Кнопки действий
            for button in self.buttons:
                button.draw(screen)
            
            # Лог выполненных действий (зелёный текст под кнопками)
            self._draw_action_log(screen)
        
        # Туториал
        if self.show_tutorial:
            self.draw_tutorial(screen)
        
        # Результат (старый экран результата теперь не используется)
        if not self.game_active and not self.show_final_quiz and not self.show_report:
            self.draw_game_result(screen)

    def draw_report_screen(self, screen):
        """Отрисовка финального отчета"""
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
        analysis_steps = [
            "sender_time_analysis", "sender_address_analysis", "content_analysis",
            "attachment_type_analysis", "attachment_name_analysis"
        ]
        completed_analysis_steps = [step for step in analysis_steps if step in self.completed_steps]
        completed_text = small_font.render(f"Выполнено этапов анализа: {len(completed_analysis_steps)}/5", True, theme.SUCCESS_SOFT)
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
            advice_text = small_font.render("Рекомендуется повторить материал по фишинг атакам", True, theme.WARNING)
            screen.blit(advice_text, (report_rect.centerx - advice_text.get_width()//2, y_pos))
        else:
            advice_text = small_font.render("Отличная работа! Вы успешно справились с угрозой", True, theme.SUCCESS)
            screen.blit(advice_text, (report_rect.centerx - advice_text.get_width()//2, y_pos))
        
        y_pos += 40
        
        # Инструкция для закрытия
        instruction_font = pygame.font.Font(None, 18)
        instruction = instruction_font.render("Нажмите в любом месте для возврата на рабочий стол", True, (200, 200, 255))
        screen.blit(instruction, (report_rect.centerx - instruction.get_width()//2, report_rect.y + report_rect.height - 40))
        y_pos += 40
    
        # Инструкция для закрытия
        instruction_font = pygame.font.Font(None, 18)
        instruction = instruction_font.render("Нажмите в любом месте для возврата на рабочий стол", True, (200, 200, 255))
        screen.blit(instruction, (report_rect.centerx - instruction.get_width()//2, report_rect.y + report_rect.height - 40))


    def draw_analysis_screen(self, screen):
        """Отрисовка экрана с анализом"""
        # Фон анализа
        analysis_bg = pygame.Rect(50, 70, self.screen_width - 100, self.screen_height - 150)
        pygame.draw.rect(screen, theme.SURFACE_ALT, analysis_bg, border_radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.BORDER, analysis_bg, 2, border_radius=theme.RADIUS_LG)
        
        # Отрисовка письма с выделениями
        email_rect = pygame.Rect(60, 80, 400, 300)
        self.draw_phishing_email_mini(screen, email_rect)
        
        # Выделение элементов с пульсацией
        self.draw_highlights(screen, email_rect)
        
        # Теоритический материал
        text_x = 480
        stage_data = self.phishing_email["analysis_steps"][self.current_analysis]
        
        # Заголовок этапа
        title = self.font_large.render(stage_data["title"], True, (255, 255, 255))
        screen.blit(title, (text_x, 80))
        
        # Содержание (полное объяснение)
        y_pos = 130
        for line in stage_data["content"]:
            if line == "":
                y_pos += 10
                continue
                
            color = theme.WARNING if any(marker in line for marker in ["АНАЛИЗ", "КРИТИЧЕСКИЕ", "ВЫВОД", "ИТОГОВЫЙ", "РЕКОМЕНДАЦИИ"]) else (255, 255, 255)
            font = self.font_medium if any(marker in line for marker in ["АНАЛИЗ", "ИТОГОВЫЙ", "РЕКОМЕНДАЦИИ"]) else self.font_small
            
            text_surface = font.render(line, True, color)
            screen.blit(text_surface, (text_x, y_pos))
            y_pos += 25
        
        # Кнопка "Назад"
        self.back_button.draw(screen)

    def _truncate_for_width(self, font, text, max_width, suffix="..."):
        """Обрезает текст по ширине, чтобы не вылезал за границы."""
        if font.size(text)[0] <= max_width:
            return text
        while len(text) > 1 and font.size(text + suffix)[0] > max_width:
            text = text[:-1]
        return text.rstrip() + suffix

    def _draw_action_log(self, screen):
        """Отрисовка лога выполненных действий (зелёный текст под кнопками). Текст не выходит за границы."""
        log_y = 520
        log_height = self.screen_height - log_y - 25
        if log_height < 40:
            return
        log_rect = pygame.Rect(50, log_y, 320, log_height)
        pygame.draw.rect(screen, (35, 45, 55), log_rect, border_radius=5)
        pygame.draw.rect(screen, (80, 90, 110), log_rect, 1, border_radius=5)
        pad = 10
        max_w = log_rect.width - 2 * pad
        label = self.font_small.render("Лог действий:", True, theme.WARNING)
        screen.blit(label, (log_rect.x + pad, log_rect.y + 8))
        y = log_rect.y + 32
        prefix = "- "
        for msg in self.action_log:
            if y > log_rect.bottom - 28:
                break
            full = prefix + msg
            short = self._truncate_for_width(self.font_small, full, max_w)
            line = self.font_small.render(short, True, theme.SUCCESS)
            screen.blit(line, (log_rect.x + pad, y))
            y += 24
        if not self.action_log:
            hint = self.font_tiny.render("Нажмите кнопки действий выше", True, (120, 130, 140))
            screen.blit(hint, (log_rect.x + pad, log_rect.y + 32))

    def draw_highlights(self, screen, email_rect):
        """Выделение элементов письма с пульсацией"""
        stage_data = self.phishing_email["analysis_steps"][self.current_analysis]
        highlights = stage_data["highlight"]
        
        highlight_colors = {
            "sender": (255, 100, 100, 100),  # Красный - отправитель
            "time": (255, 200, 100, 100),    # Оранжевый - время
            "sender_address": (255, 100, 100, 100),  # Красный - адрес отправителя
            "domain": (255, 150, 100, 100),  # Оранжевый - домен
            "subject": (100, 200, 255, 100), # Синий - тема
            "body_text": (100, 200, 255, 100), # Синий - текст
            "urgency_text": (255, 100, 255, 100), # Фиолетовый - срочность
            "urgency_phrase": (255, 100, 255, 100), # Фиолетовый - фразы срочности
            "attachment_type": (100, 255, 100, 100), # Зеленый - тип вложения
            "attachment_name": (100, 255, 100, 100)  # Зеленый - название вложения
        }
        
        highlight_rects = {
            "sender": pygame.Rect(email_rect.x + 10, email_rect.y + 10, 380, 15),
            "time": pygame.Rect(email_rect.x + 10, email_rect.y + 50, 150, 15),
            "sender_address": pygame.Rect(email_rect.x + 10, email_rect.y + 10, 380, 15),
            "domain": pygame.Rect(email_rect.x + 10, email_rect.y + 10, 380, 15),
            "subject": pygame.Rect(email_rect.x + 10, email_rect.y + 30, 380, 15),
            "body_text": pygame.Rect(email_rect.x + 10, email_rect.y + 70, 380, 120),
            "urgency_text": pygame.Rect(email_rect.x + 10, email_rect.y + 90, 380, 40),
            "urgency_phrase": pygame.Rect(email_rect.x + 10, email_rect.y + 90, 380, 40),
            "attachment_type": pygame.Rect(email_rect.x + 10, email_rect.y + 279, 380, 15),
            "attachment_name": pygame.Rect(email_rect.x + 10, email_rect.y + 279, 380, 15)
        }
        
        for highlight in highlights:
            if highlight in highlight_rects:
                color = highlight_colors.get(highlight, (255, 255, 255, 100))
                highlight_surface = pygame.Surface((highlight_rects[highlight].width, highlight_rects[highlight].height), pygame.SRCALPHA)
                highlight_surface.fill(color)
                screen.blit(highlight_surface, highlight_rects[highlight])
                
                # Анимация пульсации
                pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500
                border_color = (color[0], color[1], color[2])
                pygame.draw.rect(screen, border_color, highlight_rects[highlight], int(2 + pulse * 2))

    def draw_phishing_email_mini(self, screen, email_rect):
        """Отрисовка миниатюры письма для теории"""
        # Фон письма
        pygame.draw.rect(screen, (255, 255, 255), email_rect)
        pygame.draw.rect(screen, (200, 200, 200), email_rect, 1)
        
        # Заголовок мини-письма
        font_small = pygame.font.Font(None, 16)
        
        y_pos = email_rect.y + 10
        
        # Отправитель
        sender_text = font_small.render(f"От: {self.phishing_email['sender']}", True, (0, 0, 0))
        screen.blit(sender_text, (email_rect.x + 10, y_pos))
        y_pos += 20
        
        # Тема
        subject_text = font_small.render(f"Тема: {self.phishing_email['subject']}", True, (0, 0, 0))
        screen.blit(subject_text, (email_rect.x + 10, y_pos))
        y_pos += 20
        
        # Время
        time_text = font_small.render(f"Время: {self.phishing_email['time']}", True, (128, 128, 128))
        screen.blit(time_text, (email_rect.x + 10, y_pos))
        y_pos += 20
        
        # Тело письма (первые несколько строк)
        body_lines = self.phishing_email['body'].strip().split('\n')
        for i, line in enumerate(body_lines[:3]):
            if y_pos > email_rect.y + email_rect.height - 30:
                break
            body_text = font_small.render(line[:40] + "..." if len(line) > 40 else line, True, (0, 0, 0))
            screen.blit(body_text, (email_rect.x + 10, y_pos))
            y_pos += 15
        
        # Вложение
        attachment_text = font_small.render(f"Вложение: {self.phishing_email['attachment']}", True, (0, 0, 128))
        screen.blit(attachment_text, (email_rect.x + 10, email_rect.y + email_rect.height - 20))

    def draw_phishing_email(self, screen):
        """Отрисовка полного письма для основного экрана"""
        # Область письма
        email_rect = pygame.Rect(400, 80, 500, 400)
        pygame.draw.rect(screen, (255, 255, 255), email_rect)
        pygame.draw.rect(screen, (200, 200, 200), email_rect, 2)
        
        # Заголовок письма
        header_font = pygame.font.Font(None, 20)
        body_font = pygame.font.Font(None, 18)
        
        y_pos = email_rect.y + 20
        
        # Отправитель
        sender_text = header_font.render(f"От: {self.phishing_email['sender']}", True, (200, 0, 0))
        screen.blit(sender_text, (email_rect.x + 20, y_pos))
        y_pos += 25
        
        # Тема
        subject_text = header_font.render(f"Тема: {self.phishing_email['subject']}", True, (200, 0, 0))
        screen.blit(subject_text, (email_rect.x + 20, y_pos))
        y_pos += 25
        
        # Время
        time_text = header_font.render(f"Время: {self.phishing_email['time']}", True, (128, 128, 128))
        screen.blit(time_text, (email_rect.x + 20, y_pos))
        y_pos += 30
        
        # Тело письма (полное как в оригинале)
        body_lines = self.phishing_email['body'].strip().split('\n')
        for line in body_lines:
            text_surface = body_font.render(line, True, (0, 0, 0))
            screen.blit(text_surface, (email_rect.x + 20, y_pos))
            y_pos += 20
        
        y_pos += 10
        
        # Вложение
        attachment_text = header_font.render(f"Вложение: {self.phishing_email['attachment']}", True, (0, 0, 200))
        screen.blit(attachment_text, (email_rect.x + 20, y_pos))
        y_pos += 30
        
        # Красные флаги
        flags_title = header_font.render("КРИТИЧЕСКИЕ ПРИЗНАКИ:", True, (200, 0, 0))
        screen.blit(flags_title, (email_rect.x + 20, y_pos + 30))
        y_pos += 55
        
        for i, flag in enumerate(self.phishing_email['red_flags']):
            flag_text = body_font.render("- " + flag, True, (200, 0, 0))
            screen.blit(flag_text, (email_rect.x + 40, y_pos))
            y_pos += 20

    def draw_tutorial(self, screen):
        """Отрисовка обучающего сообщения"""
        tutorial_rect = pygame.Rect(
            self.screen_width // 2 - 200, 
            self.screen_height // 2 - 75,
            400, 150
        )
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
        title = tutorial_font.render("ИНСТРУКЦИЯ", True, theme.WARNING)
        screen.blit(title, (tutorial_rect.centerx - title.get_width()//2, tutorial_rect.y + 15))
        
        small_font = pygame.font.Font(None, 18)
        instructions = [
            "1. Изучите подозрительное письмо",
            "2. Проведите анализ всех компонентов",
            "3. Выполните защитные действия",
            "4. Удалите письмо",
            "5. Пройдите финальный тест"
        ]
        
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (255, 255, 255))
            screen.blit(text, (tutorial_rect.x + 20, tutorial_rect.y + 45 + i * 20))

    def draw_game_result(self, screen):
        """Отрисовка результата игры"""
        result_rect = pygame.Rect(
            self.screen_width // 2 - 250,
            self.screen_height // 2 - 150,
            500, 300
        )
        pygame.draw.rect(screen, theme.SURFACE, result_rect, border_radius=15)
        pygame.draw.rect(screen, theme.ACCENT, result_rect, 3, border_radius=15)
        
        result_font = pygame.font.Font(None, 36)
        
        if self.final_quiz_answered:
            result_text = result_font.render("РАССЛЕДОВАНИЕ УСПЕШНО!", True, theme.SUCCESS)
            score_color = theme.WARNING
        else:
            result_text = result_font.render("РАССЛЕДОВАНИЕ ПРОВАЛЕНО!", True, theme.DANGER)
            score_color = (255, 150, 100)
        
        screen.blit(result_text, (result_rect.centerx - result_text.get_width()//2, result_rect.y + 40))
        
        time_font = pygame.font.Font(None, 24)
        if self.timer > 0:
            time_text = time_font.render(f"Оставшееся время: {int(self.timer)}с", True, (200, 200, 255))
        else:
            time_text = time_font.render("Время вышло!", True, (255, 150, 150))
        screen.blit(time_text, (result_rect.centerx - time_text.get_width()//2, result_rect.y + 150))
        
        instruction_font = pygame.font.Font(None, 20)
        instruction = instruction_font.render("Нажмите для возврата на рабочий стол", True, (200, 200, 255))
        screen.blit(instruction, (result_rect.centerx - instruction.get_width()//2, result_rect.y + 200))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if self.quiz:
            self.quiz.on_resize(w, h)

# [file name]: window.py
# [file content begin]
import pygame

from . import theme

class Window:
    def __init__(self, x, y, width, height, title, window_type, game_manager):
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.window_type = window_type
        self.game_manager = game_manager
        self.dragging = False
        self.drag_offset = (0, 0)
        self.minimized = False
        self.original_height = height
        
        # Цвета окна
        self.header_color = theme.SURFACE_ALT
        self.body_color = theme.SURFACE
        self.border_color = theme.BORDER
        
        # Кнопки
        button_size = 16
        self.close_button = pygame.Rect(
            x + width - button_size - 5, y + 7, button_size, button_size
        )
        self.minimize_button = pygame.Rect(
            x + width - button_size * 2 - 10, y + 7, button_size, button_size
        )
        
        # Шрифт
        self.font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 22)
        
        # Инициализируем emails ДО создания контента
        self.emails = []
        self.initial_emails_added = False
        self.phishing_email_added = False
        
        self.content_surface = pygame.Surface((width - 4, height - 30))
        self._create_content()
        
        self._update_button_positions()
    
    # --- МЕТОДЫ УПРАВЛЕНИЯ ЭЛЕКТРОННОЙ ПОЧТОЙ ---
    
    def add_initial_emails(self, emails):
        """Добавляет стартовые письма в почтовый ящик."""
        if self.window_type == "email" and not self.initial_emails_added:
            self.emails.extend(emails)
            self.initial_emails_added = True
            self._create_content() 
            
    def add_phishing_email(self, email):
        """Добавляет фишинговое письмо."""
        if self.window_type == "email" and not self.phishing_email_added:
            self.emails.append(email)
            self.phishing_email_added = True
            self._create_content()

    def remove_phishing_email(self):
        """Удаляет фишинговое письмо из списка (после выполнения задания дня 1)."""
        if self.window_type != "email":
            return
        self.emails = [e for e in self.emails if not e.get("phishing", False)]
        self._create_content()
    
    # --- КОНЕЦ МЕТОДОВ УПРАВЛЕНИЯ ПОЧТОЙ ---

    def _create_content(self):
        """Создание содержимого окна в зависимости от типа"""
        self.content_surface.fill(self.body_color)
        
        if self.window_type == "my_computer":
            self._draw_computer_content()
        elif self.window_type == "antivirus":
            self._draw_antivirus_content()
        elif self.window_type == "email":
            self._draw_email_content()
        elif self.window_type == "settings":
            self._draw_settings_content()
        elif self.window_type == "documents":
            self._draw_documents_content()
        elif self.window_type == "recycle_bin":
            self._draw_recycle_content()
        elif self.window_type == "phishing_investigation":
            self._draw_phishing_investigation_content()
        elif self.window_type == "valid_accounts_investigation":
            self._draw_valid_accounts_investigation_content()
        elif self.window_type == "process_injection_investigation":
            self._draw_process_injection_content()
        elif self.window_type == "dns_c2_investigation":
            self._draw_dns_c2_investigation_content()
        elif self.window_type == "siem_system":
            self._draw_siem_content()
        # --- НОВЫЕ ТИПЫ ОКОН ---
        elif self.window_type == "dos_investigation":
            self._draw_dos_investigation_content()
        elif self.window_type == "meterpreter_investigation":
            self._draw_meterpreter_investigation_content()
        elif self.window_type == "ssh_bruteforce_investigation":
            self._draw_ssh_bruteforce_investigation_content()
        # --- КОНЕЦ НОВЫХ ТИПОВ ---

    # --- СУЩЕСТВУЮЩИЕ МЕТОДЫ ОТРИСОВКИ ---
    
    def _draw_computer_content(self):
        font = pygame.font.Font(None, 24)
        text = font.render("Системная информация", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(text, (20, 20))
        
        # Диски
        drives = [
            ("Локальный диск (C:)", "58.2 GB свободно из 120 GB"),
            ("Локальный диск (D:)", "112.5 GB свободно из 200 GB"),
            ("CD-привод (E:)", "Нет диска")
        ]
        
        for i, (drive, space) in enumerate(drives):
            drive_text = font.render(drive, True, theme.ACCENT)
            space_text = font.render(space, True, theme.TEXT_PRIMARY)
            self.content_surface.blit(drive_text, (40, 60 + i * 40))
            self.content_surface.blit(space_text, (40, 80 + i * 40))
    
    def _draw_antivirus_content(self):
        font = pygame.font.Font(None, 24)
        title = font.render("Антивирус 'ТехноЩит Pro'", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        # Статус
        status_font = pygame.font.Font(None, 20)
        
        # Проверяем текущий день и показываем соответствующее сообщение
        day3_threat_active = (
            hasattr(self.game_manager, 'desktop')
            and self.game_manager.desktop.current_day == 3
            and not self.game_manager.desktop.is_day_threat_resolved(3)
        )

        if day3_threat_active:
            # Для дня 3 — предупреждение без названия процесса (игрок ищет сам)
            status_text = status_font.render("СТАТУС: ОБНАРУЖЕНА УГРОЗА!", True, theme.DANGER)
            self.content_surface.blit(status_text, (20, 50))
            
            threat_text = status_font.render("Подозрительная активность процессов в системе", True, theme.DANGER)
            self.content_surface.blit(threat_text, (20, 75))
            
            recommendation = status_font.render("Рекомендация: Проверить в Диспетчере задач", True, theme.ACCENT)
            self.content_surface.blit(recommendation, (20, 100))
        else:
            # Стандартное содержимое для других дней
            status_text = status_font.render("Статус защиты: АКТИВНА", True, theme.SUCCESS)
            self.content_surface.blit(status_text, (20, 50))
            
            scan_text = status_font.render("Последнее сканирование: 2 часа назад", True, theme.TEXT_PRIMARY)
            self.content_surface.blit(scan_text, (20, 75))
        
        # Кнопка быстрого сканирования
        quick_scan_rect = pygame.Rect(20, 120, 200, 30)
        pygame.draw.rect(self.content_surface, theme.ACCENT_DIM, quick_scan_rect, border_radius=3)
        pygame.draw.rect(self.content_surface, theme.TEXT_PRIMARY, quick_scan_rect, 1, border_radius=3)
        scan_text = font.render("Быстрое сканирование", True, (255, 255, 255))
        self.content_surface.blit(scan_text, (30, 125))

    def _draw_email_content(self):
        """Отрисовка содержимого почтового окна"""
        email_font = pygame.font.Font(None, 20)
        
        # Заголовки
        headers = ["Отправитель", "Тема", "Время"]
        x_positions = [10, 150, 480]
        y_pos = 10
        
        for i, header in enumerate(headers):
            header_text = email_font.render(header, True, theme.TEXT_SECONDARY)
            self.content_surface.blit(header_text, (x_positions[i], y_pos))

        y_pos += 25

        # Линия-разделитель
        pygame.draw.line(self.content_surface, theme.BORDER, (5, y_pos), (self.content_surface.get_width() - 5, y_pos), 1)
        y_pos += 5

        # Список писем
        for i, email in enumerate(self.emails):
            email_rect = pygame.Rect(5, y_pos, self.content_surface.get_width() - 10, 30)

            # Фон письма (красный для фишинга, жёлтый для непрочитанных, нейтральный для прочитанных)
            if email.get("phishing", False):
                pygame.draw.rect(self.content_surface, theme.DANGER_DIM, email_rect, border_radius=theme.RADIUS_SM)
                pygame.draw.rect(self.content_surface, theme.DANGER, email_rect, 1, border_radius=theme.RADIUS_SM)
            elif email["unread"]:
                pygame.draw.rect(self.content_surface, theme.WARNING_DIM, email_rect, border_radius=theme.RADIUS_SM)
                pygame.draw.rect(self.content_surface, theme.WARNING, email_rect, 1, border_radius=theme.RADIUS_SM)
            else:
                pygame.draw.rect(self.content_surface, theme.SURFACE_ALT, email_rect, border_radius=theme.RADIUS_SM)
                pygame.draw.rect(self.content_surface, theme.BORDER, email_rect, 1, border_radius=theme.RADIUS_SM)

            # Отправитель
            sender_color = theme.TEXT_PRIMARY
            if email["unread"]:
                sender_color = theme.WARNING
            if email.get("phishing", False):
                sender_color = theme.DANGER

            sender_text = email_font.render(email["sender"][:20], True, sender_color)
            self.content_surface.blit(sender_text, (x_positions[0], y_pos + 5))

            # Тема
            subject_color = theme.TEXT_PRIMARY
            if email.get("phishing", False):
                subject_color = theme.DANGER

            subject_text = email_font.render(email["subject"][:35], True, subject_color)
            self.content_surface.blit(subject_text, (x_positions[1], y_pos + 5))

            # Время
            time_text = email_font.render(email["time"], True, theme.TEXT_SECONDARY)
            self.content_surface.blit(time_text, (x_positions[2], y_pos + 5))
            
            email["rect"] = email_rect  # Сохраняем для обработки кликов
            y_pos += 35

    def _draw_settings_content(self):
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Панель управления - Системные настройки", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        # Раздел пароля
        self.content_surface.blit(font.render("Пароль учетной записи:", True, theme.TEXT_PRIMARY), (20, 70))
        
        self.password_button = pygame.Rect(200, 65, 200, 30)
        pygame.draw.rect(self.content_surface, theme.SUCCESS, self.password_button, border_radius=5)
        
        password_text = font.render("СМЕНИТЬ ПАРОЛЬ", True, (255, 255, 255))
        self.content_surface.blit(password_text, (220, 72))

    def _draw_documents_content(self):
        title_font = pygame.font.Font(None, 24)
        self.content_surface.blit(title_font.render("Корпоративные документы", True, theme.TEXT_PRIMARY), (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        files = [
            "Корпоративный план на 2025.docx",
            "Политика безопасности.pdf",
            "Важные данные.zip (зашифровано)",
            "Списки пользователей.xlsx"
        ]
        
        for i, file in enumerate(files):
            text_surface = font.render(file, True, theme.TEXT_PRIMARY)
            self.content_surface.blit(text_surface, (20, 50 + i * 25))

    def _draw_recycle_content(self):
        font = pygame.font.Font(None, 24)
        title = font.render("Корзина", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font_small = pygame.font.Font(None, 20)
        text = font_small.render("Корзина пуста.", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(text, (40, 60))

    def _draw_phishing_investigation_content(self):
        """Содержимое окна расследования фишинг атаки"""
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Расследование. Уровень 1: Фишинг атака", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        # Описание ситуации
        situation = [
            "Цель: Кража учетных данных сотрудников",
            "Метод: Подделка писем от лица бухгалтерии",
            "",
            "Характеристики атаки:",
            "- Отправитель: oshptu@mail.grodno.by",
            "- Цель: 45 сотрудников компании",
            "- Метод: Социальная инженерия",
            "",
            "Требуется немедленное реагирование!"
        ]
        
        for i, line in enumerate(situation):
            color = theme.DANGER if i == 0 else theme.TEXT_PRIMARY
            text_surface = font.render(line, True, color)
            self.content_surface.blit(text_surface, (40, 50 + i * 25))
        
        # Кнопка запуска расследования (единый стиль — зелёная, текст помещается)
        btn_font = pygame.font.Font(None, 20)
        self.investigate_button = pygame.Rect(40, 350, 260, 40)
        pygame.draw.rect(self.content_surface, theme.SUCCESS, self.investigate_button, border_radius=5)
        pygame.draw.rect(self.content_surface, theme.TEXT_PRIMARY, self.investigate_button, 2, border_radius=5)
        investigate_text = btn_font.render("Начать расследование", True, (255, 255, 255))
        tx = 40 + (260 - investigate_text.get_width()) // 2
        self.content_surface.blit(investigate_text, (tx, 358))

    def _draw_valid_accounts_investigation_content(self):
        """Содержимое окна расследования компрометации учетных записей"""
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Расследование. Уровень 2: Valid Accounts", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        # Описание ситуации
        situation = [
            "Цель: Несанкционированный доступ к данным",
            "Метод: Использование скомпрометированных учетных данных",
            "",
            "Характеристики инцидента:",
            "- Пользователь: Волков Д.С. (HR)",
            "- Время активности: 23:40-23:50",
            "- Действия: Доступ к финансовым отчетам, БД сотрудников",
            "- Риск: КРИТИЧЕСКИЙ",
            "",
            "Требуется немедленное реагирование!"
        ]
        
        for i, line in enumerate(situation):
            color = theme.DANGER if i == 0 else theme.TEXT_PRIMARY
            text_surface = font.render(line, True, color)
            self.content_surface.blit(text_surface, (40, 50 + i * 25))
        
        # Кнопка запуска расследования (единый стиль — зелёная, текст помещается)
        btn_font = pygame.font.Font(None, 20)
        self.valid_accounts_button = pygame.Rect(40, 350, 260, 40)
        pygame.draw.rect(self.content_surface, theme.SUCCESS, self.valid_accounts_button, border_radius=5)
        pygame.draw.rect(self.content_surface, theme.TEXT_PRIMARY, self.valid_accounts_button, 2, border_radius=5)
        investigate_text = btn_font.render("Начать расследование", True, (255, 255, 255))
        tx = 40 + (260 - investigate_text.get_width()) // 2
        self.content_surface.blit(investigate_text, (tx, 358))

    def _draw_process_injection_content(self):
        """Содержимое окна расследования Process Injection"""
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Расследование. Уровень 3: Process Injection", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        # Описание ситуации (без названия процесса — игрок определяет его сам в Диспетчере задач)
        situation = [
            "Обнаружено внедрение кода в процессы (Process Injection)",
            "Метод: Внедрение в легитимные процессы",
            "Цель: Обход антивирусной защиты",
            "",
            "Что искать в Диспетчере задач:",
            "- Процесс с аномально высоким CPU и потреблением памяти",
            "- Имя, похожее на системную утилиту (маскировка)",
            "- Внедрение часто связано с explorer.exe",
            "- Риск: КРИТИЧЕСКИЙ",
            "",
            "Откройте Диспетчер задач и выберите подозрительный процесс."
        ]
        
        for i, line in enumerate(situation):
            color = theme.DANGER if i == 0 else theme.TEXT_PRIMARY
            text_surface = font.render(line, True, color)
            self.content_surface.blit(text_surface, (40, 50 + i * 25))

    def _draw_dns_c2_investigation_content(self):
        """Содержимое окна расследования DNS C2"""
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Расследование. Уровень 4: DNS C2", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        # Описание ситуации
        situation = [
            "C2 домен: system-updates-service.net",
            "Метод: Скрытый канал управления через DNS",
            "Цель: Скрытное управление зараженными системами",
            "",
            "Характеристики атаки:",
            "- Домен: system-updates-service.net",
            "- Метод: Base64 кодирование в поддоменах",
            "- Тип запросов: TXT записи",
            "- Риск: КРИТИЧЕСКИЙ",
            "",
            "Требуется немедленное реагирование!"
        ]
        
        for i, line in enumerate(situation):
            color = theme.DANGER if i == 0 else theme.TEXT_PRIMARY
            text_surface = font.render(line, True, color)
            self.content_surface.blit(text_surface, (40, 50 + i * 25))

    def _draw_siem_content(self):
        font = pygame.font.Font(None, 24)
        title = font.render("SIEM-система: Обзор инцидентов", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font_small = pygame.font.Font(None, 20)
        
        # Кнопка открытия SIEM
        self.open_siem_button = pygame.Rect(20, 60, 250, 30)
        pygame.draw.rect(self.content_surface, theme.ACCENT_DIM, self.open_siem_button, border_radius=5)
        btn_text = font_small.render("ОТКРЫТЬ ИНТЕРФЕЙС SIEM", True, (255, 255, 255))
        self.content_surface.blit(btn_text, (30, 67))

    # --- НОВЫЕ МЕТОДЫ ДЛЯ ОТРИСОВКИ СОДЕРЖИМОГО ---
    def _draw_dos_investigation_content(self):
        """Содержимое окна расследования DoS атаки (Уровень 5)"""
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Расследование. Уровень 5: DoS атака", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        situation = [
            "Цель: Вывести из строя веб-сервер компании",
            "Метод: Атака типа 'Отказ в обслуживании' (DoS)",
            "",
            "Данные из PT NAD:",
            "- Дата: 18.01.2025",
            "- Атакуемый порт: 80 (HTTP) и 1234 (UDP)",
            "- Инструмент атаки: Siege/4.0.7",
            "- Сессий на 80 порт: 64 154",
            "- Критичность: ВЫСОКАЯ",
            "",
            "Требуется немедленное реагирование!"
        ]
        
        for i, line in enumerate(situation):
            color = theme.DANGER if i == 0 else theme.TEXT_PRIMARY
            text_surface = font.render(line, True, color)
            self.content_surface.blit(text_surface, (40, 50 + i * 25))
        
        # Кнопка запуска расследования (единый стиль — зелёная, текст помещается)
        btn_font = pygame.font.Font(None, 20)
        self.investigate_button = pygame.Rect(40, 350, 260, 40)
        pygame.draw.rect(self.content_surface, theme.SUCCESS, self.investigate_button, border_radius=5)
        pygame.draw.rect(self.content_surface, theme.TEXT_PRIMARY, self.investigate_button, 2, border_radius=5)
        investigate_text = btn_font.render("Начать расследование", True, (255, 255, 255))
        tx = 40 + (260 - investigate_text.get_width()) // 2
        self.content_surface.blit(investigate_text, (tx, 358))

    def _draw_meterpreter_investigation_content(self):
        """Содержимое окна расследования атаки Meterpreter (Уровень 6)"""
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Расследование. Уровень 6: Meterpreter", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        situation = [
            "Цель: Получение удаленного доступа к системе",
            "Метод: Многоступенчатая атака (Фишинг -> Вредонос)",
            "",
            "Данные из PT NAD:",
            "- Сработка: PAYLOAD [PTsecurity] Meterpreter",
            "- Жертва: 192.168.25.190",
            "- C2 Сервер: 32.17.0.10 (US)",
            "- Вредоносный файл: ChromeUpdate.exe",
            "- Вектор: Фишинговое письмо с HTML-вложением",
            "- Критичность: КРИТИЧЕСКАЯ",
            "",
            "Требуется немедленное реагирование!"
        ]
        
        for i, line in enumerate(situation):
            color = theme.DANGER if i == 0 else theme.TEXT_PRIMARY
            text_surface = font.render(line, True, color)
            self.content_surface.blit(text_surface, (40, 50 + i * 25))
        
        # Кнопка запуска расследования (единый стиль — зелёная, текст помещается)
        btn_font = pygame.font.Font(None, 20)
        self.investigate_button = pygame.Rect(40, 350, 260, 40)
        pygame.draw.rect(self.content_surface, theme.SUCCESS, self.investigate_button, border_radius=5)
        pygame.draw.rect(self.content_surface, theme.TEXT_PRIMARY, self.investigate_button, 2, border_radius=5)
        investigate_text = btn_font.render("Начать расследование", True, (255, 255, 255))
        tx = 40 + (260 - investigate_text.get_width()) // 2
        self.content_surface.blit(investigate_text, (tx, 358))

    def _draw_ssh_bruteforce_investigation_content(self):
        """Содержимое окна расследования брутфорс SSH атаки (Уровень 7)"""
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Расследование. Уровень 7: Брутфорс SSH", True, theme.TEXT_PRIMARY)
        self.content_surface.blit(title, (20, 20))
        
        font = pygame.font.Font(None, 20)
        
        situation = [
            "Цель: Подбор пароля для доступа к SSH серверу",
            "Метод: Автоматизированный перебор (брутфорс)",
            "",
            "Данные из PT NAD:",
            "- Дата: 16.01.2025",
            "- Атакующий: 10.10.187.241",
            "- Сервер-жертва: 10.10.187.56 (порт 22)",
            "- Попыток входа: 226 сессий",
            "- Статус: УСПЕШНЫЙ ВХОД зафиксирован в 16:20:31",
            "- Критичность: КРИТИЧЕСКАЯ",
            "",
            "Требуется немедленное реагирование!"
        ]
        
        for i, line in enumerate(situation):
            color = theme.DANGER if i == 0 else theme.TEXT_PRIMARY
            text_surface = font.render(line, True, color)
            self.content_surface.blit(text_surface, (40, 50 + i * 25))
        
        # Кнопка запуска расследования (единый стиль — зелёная, текст помещается)
        btn_font = pygame.font.Font(None, 20)
        self.investigate_button = pygame.Rect(40, 350, 260, 40)
        pygame.draw.rect(self.content_surface, theme.SUCCESS, self.investigate_button, border_radius=5)
        pygame.draw.rect(self.content_surface, theme.TEXT_PRIMARY, self.investigate_button, 2, border_radius=5)
        investigate_text = btn_font.render("Начать расследование", True, (255, 255, 255))
        tx = 40 + (260 - investigate_text.get_width()) // 2
        self.content_surface.blit(investigate_text, (tx, 358))

    # --- МЕТОДЫ ОБРАБОТКИ СОБЫТИЙ ---
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_pos = event.pos
                
                # Проверка кнопок закрытия/сворачивания
                if self.close_button.collidepoint(mouse_pos):
                    return "close"
                if self.minimize_button.collidepoint(mouse_pos):
                    # Свернуть в панель задач: окно перестаёт рисоваться, восстанавливается по клику на кнопку в панели
                    self.minimized = True
                    return True
                
                # Свёрнутое окно не обрабатывает клики — восстановление только через панель задач
                if self.minimized:
                    return False
                
                if self.rect.collidepoint(mouse_pos):
                    # Клик по заголовку — перетаскивание или вынос на передний план
                    if mouse_pos[1] < self.rect.y + 32:
                        self.dragging = True
                        self.drag_offset = (mouse_pos[0] - self.rect.x, mouse_pos[1] - self.rect.y)
                        return "bring_to_front"

                    # Проверка кликов на контенте
                    
                    # Кнопка смены пароля
                    if self.window_type == "settings" and self._check_password_button_click(mouse_pos):
                        return "password_changed"
                        
                    # Кнопка запуска расследования фишинга
                    if self.window_type == "phishing_investigation" and self._check_investigation_button_click(mouse_pos):
                        return "start_phishing_investigation"
                        
                    # Кнопка запуска расследования компрометации учетных записей
                    if self.window_type == "valid_accounts_investigation" and self._check_valid_accounts_button_click(mouse_pos):
                        return "start_valid_accounts_investigation"
                        
                    # Кнопка запуска расследования DoS
                    if self.window_type == "dos_investigation" and self._check_investigation_button_click(mouse_pos):
                        return "start_dos_investigation"
                        
                    # Кнопка запуска расследования Meterpreter
                    if self.window_type == "meterpreter_investigation" and self._check_investigation_button_click(mouse_pos):
                        return "start_meterpreter_investigation"
                        
                    # Кнопка запуска расследования SSH Brute Force
                    if self.window_type == "ssh_bruteforce_investigation" and self._check_investigation_button_click(mouse_pos):
                        return "start_ssh_bruteforce_investigation"
                        
                    # Кнопка открытия SIEM
                    if self.window_type == "siem_system" and self._check_siem_button_click(mouse_pos):
                        return "open_siem_interface"
                        
                    # Клик по письму
                    if self.window_type == "email":
                        result = self._check_email_click(mouse_pos)
                        if result == "phishing_detected":
                            # Уровень 1 — расследование фишинга; уровень 6 — расследование Meterpreter (не открывать уровень 1)
                            if self.game_manager.current_day == 1:
                                x = (self.game_manager.screen_width - 600) // 2
                                y = (self.game_manager.screen_height - 450) // 2
                                investigation_window = Window(x, y, 600, 450, "Расследование фишинг атаки", "phishing_investigation", self.game_manager)
                                self.game_manager.desktop.windows.append(investigation_window)
                            elif self.game_manager.current_day == 6:
                                self.game_manager.desktop._add_investigation_for_day_if_needed("meterpreter_investigation")
                                # Вынести окно расследования Meterpreter на передний план
                                for w in self.game_manager.desktop.windows:
                                    if getattr(w, 'window_type', None) == "meterpreter_investigation":
                                        self.game_manager.desktop.windows.remove(w)
                                        self.game_manager.desktop.windows.append(w)
                                        break
                            return True
                        elif result:
                            self._create_content()  # Обновить контент после прочтения
                            return True
                        
                    # Кнопка антивируса
                    if self.window_type == "antivirus" and self._check_antivirus_button_click(mouse_pos):
                        self.game_manager.complete_objective("Просканировать систему на угрозы")
                        return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = event.pos[0] - self.drag_offset[0]
                self.rect.y = event.pos[1] - self.drag_offset[1]
                # Обновить позиции кнопок при перетаскивании
                self._update_button_positions()
                return True
        
        return False

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ПРОВЕРКИ КЛИКОВ ---
    
    def _check_password_button_click(self, mouse_pos):
        content_x = mouse_pos[0] - self.rect.x - 2
        content_y = mouse_pos[1] - self.rect.y - 32
        
        if hasattr(self, 'password_button') and self.password_button.collidepoint(content_x, content_y):
            return True
        return False
        
    def _check_investigation_button_click(self, mouse_pos):
        """Общий метод для проверки клика по кнопке расследования"""
        content_x = mouse_pos[0] - self.rect.x - 2
        content_y = mouse_pos[1] - self.rect.y - 32
        
        if hasattr(self, 'investigate_button') and self.investigate_button.collidepoint(content_x, content_y):
            return True
        return False
        
    def _check_valid_accounts_button_click(self, mouse_pos):
        """Проверка клика по кнопке запуска расследования компрометации учетных записей"""
        content_x = mouse_pos[0] - self.rect.x - 2
        content_y = mouse_pos[1] - self.rect.y - 32
        
        if hasattr(self, 'valid_accounts_button') and self.valid_accounts_button.collidepoint(content_x, content_y):
            return True
        return False

    def _check_siem_button_click(self, mouse_pos):
        """Проверка клика по кнопке открытия SIEM"""
        content_x = mouse_pos[0] - self.rect.x - 2
        content_y = mouse_pos[1] - self.rect.y - 32
        
        if hasattr(self, 'open_siem_button') and self.open_siem_button.collidepoint(content_x, content_y):
            return True
        return False
        
    def _check_antivirus_button_click(self, mouse_pos):
        content_x = mouse_pos[0] - self.rect.x - 2
        content_y = mouse_pos[1] - self.rect.y - 32
        
        # Координаты кнопки быстрого сканирования (20, 120, 200, 30)
        scan_rect = pygame.Rect(20, 120, 200, 30)
        if scan_rect.collidepoint(content_x, content_y):
            return True
        return False

    def _check_email_click(self, mouse_pos):
        content_x = mouse_pos[0] - self.rect.x - 2
        content_y = mouse_pos[1] - self.rect.y - 32
        
        for i, email in enumerate(self.emails):
            if "rect" in email and email["rect"].collidepoint(content_x, content_y):
                email["unread"] = False
                self.game_manager.complete_objective("Проверить почту")
                
                # Проверка на фишинг
                if email.get("phishing", False):
                    return "phishing_detected"
                
                return True
        return False

    def _update_button_positions(self):
        """Обновление позиций кнопок при перетаскивании окна"""
        button_size = 16
        self.close_button.x = self.rect.x + self.rect.width - button_size - 5
        self.close_button.y = self.rect.y + 7
        self.minimize_button.x = self.rect.x + self.rect.width - button_size * 2 - 10
        self.minimize_button.y = self.rect.y + 7
        
    def update(self):
        if not self.minimized:
            pass

    def draw(self, screen):
        # Свёрнутое окно не рисуется — только кнопка в панели задач; восстановление по клику на неё
        if self.minimized:
            return
        # Обновляем содержимое для некоторых типов окон
        if self.window_type == "antivirus" or self.window_type == "siem_system":
            self._create_content()
            
        shadow_rect = self.rect.move(0, 5)
        shadow = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=theme.RADIUS_MD)
        screen.blit(shadow, shadow_rect.topleft)

        pygame.draw.rect(screen, self.body_color, self.rect, border_radius=theme.RADIUS_MD)
        pygame.draw.rect(screen, self.border_color, self.rect, 1, border_radius=theme.RADIUS_MD)
        header_rect = pygame.Rect(self.rect.x + 1, self.rect.y + 1, self.rect.width - 2, 30)
        pygame.draw.rect(screen, self.header_color, header_rect, border_top_left_radius=theme.RADIUS_MD, border_top_right_radius=theme.RADIUS_MD)
        pygame.draw.line(screen, theme.ACCENT_DIM, (header_rect.x, header_rect.bottom - 1), (header_rect.right, header_rect.bottom - 1), 2)
        title_surface = self.title_font.render(self.title, True, theme.TEXT_PRIMARY)
        screen.blit(title_surface, (self.rect.x + 10, self.rect.y + 5))
        self._draw_window_buttons(screen)
        screen.blit(self.content_surface, (self.rect.x + 2, self.rect.y + 32))

    def _draw_window_buttons(self, screen):
        """Отрисовка кнопок окна (закрыть и свернуть)"""
        # Кнопка закрытия
        pygame.draw.rect(screen, theme.DANGER, self.close_button, border_radius=theme.RADIUS_SM)

        # Крестик на кнопке закрытия
        pygame.draw.line(screen, theme.TEXT_ON_ACCENT,
                        (self.close_button.x + 4, self.close_button.y + 4),
                        (self.close_button.x + 12, self.close_button.y + 12), 2)
        pygame.draw.line(screen, theme.TEXT_ON_ACCENT,
                        (self.close_button.x + 12, self.close_button.y + 4),
                        (self.close_button.x + 4, self.close_button.y + 12), 2)

        # Кнопка сворачивания
        pygame.draw.rect(screen, theme.ELEVATED, self.minimize_button, border_radius=theme.RADIUS_SM)

        # Минус на кнопке сворачивания
        pygame.draw.line(screen, theme.TEXT_PRIMARY,
                        (self.minimize_button.x + 4, self.minimize_button.y + 8),
                        (self.minimize_button.x + 12, self.minimize_button.y + 8), 2)
# [file content end]
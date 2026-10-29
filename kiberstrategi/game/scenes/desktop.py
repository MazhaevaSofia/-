# [file name]: desktop.py
# [file content begin]
import pygame
import os
import random
from ..core.icon_generator import IconGenerator
from ..ui.icon import DesktopIcon
from ..ui.window import Window
from ..ui.button import Button
from ..ui import theme
from ..core import sound_manager
from ..data.game_data import OBJECTIVES, INITIAL_EMAILS, PHISHING_EMAIL, REQUIRED_TO_COMPLETE_DAY, NOISE_MESSAGES

class DesktopScene:
    def __init__(self, screen_width, screen_height, game_manager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.game_manager = game_manager
        self.icon_generator = IconGenerator()
        
        # Рабочий стол
        self.background_color = theme.BG
        self.background_image_original = None
        self.background_image = None
        self.icons = []
        self.windows = []

        # Панель задач
        self.taskbar_height = 44
        self.taskbar_color = theme.SURFACE
        
        # Сообщения
        self.message_text = ""
        self.message_timer = 0
        self.message_color = (0, 0, 0)
        self.show_message_flag = False
        self.message_clickable = False  # Флаг, что на сообщение можно кликнуть
        self.message_callback = None    # Функция, которая вызовется при клике

        # Тост о разблокированной ачивке — независим от message_*, чтобы не
        # затираться авто-скрытием алертов об угрозах (см. clear_threat_message)
        self.achievement_toast_text = ""
        self.achievement_toast_timer = 0

        # «Шум»: фоновые уведомления без угрозы, всплывают отдельно от
        # настоящего алерта, пока задание дня не выполнено (см. game_data.NOISE_MESSAGES)
        self.noise_text = ""
        self.noise_timer = 0
        self.noise_cooldown = 180  # первый шум — примерно через 3 секунды

        # Время в игре
        self.game_time = "09:00"
        self.time_update_timer = 0
        
        # Флаги событий
        self.initial_email_sent = False
        self.phishing_email_added = False
        self.siem_alert_shown = False
        self.antivirus_alert_shown = False
        self.dns_alert_shown = False
        # --- НОВЫЕ ФЛАГИ ---
        self.dos_alert_shown = False
        self.meterpreter_alert_shown = False
        self.ssh_alert_shown = False
        # --- КОНЕЦ НОВЫХ ФЛАГОВ ---
        
        # Кнопка следующего дня
        self.show_next_day_button = False
        self.next_day_button = None
        
        # Текущий день
        self.current_day = 1
        
        # Меню «Пуск» на панели задач
        self.show_start_menu = False
        self.start_menu_rect = None
        self.start_shutdown_rect = None
        
        self.initialize_desktop()
        self._load_background_image()
    
    def _load_background_image(self):
        """Загрузка и первичное масштабирование фоновой картинки рабочего стола."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            image_path = os.path.join(base_dir, "assets", "wallpap.jpg")
            if os.path.exists(image_path):
                self.background_image_original = pygame.image.load(image_path).convert()
                self._update_background_image()
        except Exception:
            self.background_image_original = None
            self.background_image = None

    def _update_background_image(self):
        """Пересчитать масштаб фоновой картинки под текущий размер окна."""
        if not self.background_image_original:
            return
        self.background_image = pygame.transform.smoothscale(
            self.background_image_original,
            (self.screen_width, self.screen_height)
        )
    
    def initialize_desktop(self):
        """Инициализация рабочего стола с иконками"""
        self.icons = []
        
        # Создаем иконки
        icon_data = [
            {"name": "Мой компьютер", "type": "my_computer"},
            {"name": "Почта", "type": "email"},
            {"name": "Антивирус", "type": "antivirus"},
            {"name": "Настройки", "type": "settings"},
            {"name": "Документы", "type": "documents"},
            {"name": "Корзина", "type": "recycle_bin"},
            {"name": "Интернет", "type": "internet"},
            {"name": "SIEM", "type": "siem_system"},
            {"name": "Диспетчер задач", "type": "task_manager"},
            {"name": "Сетевой монитор", "type": "traffic_analyzer"},
        ]
        
        # Расчет позиций иконок (столбцами)
        x_start, y_start = 10, 10
        y_step = 90
        x_step = 80
        
        for i, data in enumerate(icon_data):
            x = x_start + (i // 7) * x_step
            y = y_start + (i % 7) * y_step
            
            icon_image = self.icon_generator.generate_icon(data["type"])
            icon = DesktopIcon(x, y, icon_image, data["name"], data["type"], self.open_window)
            self.icons.append(icon)
            
    def initialize_day(self, day):
        """Инициализация сцены для нового дня."""
        self.current_day = day
        self.windows = []
        self.noise_timer = 0
        self.noise_cooldown = 180
        self.initial_email_sent = False
        self.phishing_email_added = False
        self.siem_alert_shown = False
        self.antivirus_alert_shown = False
        self.dns_alert_shown = False
        # --- СБРОС НОВЫХ ФЛАГОВ ---
        self.dos_alert_shown = False
        self.meterpreter_alert_shown = False
        self.ssh_alert_shown = False
        # --- КОНЕЦ СБРОСА ---
        self.show_next_day_button = False
        self.next_day_button = None
        
        # Унифицированные сообщения для каждого дня (только информирование, без открытия по клику)
        day_messages = {
            1: ("Уровень 1: Добро пожаловать в систему. Откройте «Почта» и проверьте письма на фишинг.", (0, 0, 150)),
            2: ("Уровень 2: Обнаружена подозрительная активность в SIEM. Откройте приложение «SIEM» для расследования.", (150, 0, 0)),
            3: ("Уровень 3: Антивирус обнаружил подозрительную активность процессов. Откройте «Антивирус» или «Диспетчер задач».", (200, 0, 0)),
            4: ("Уровень 4: SIEM обнаружил аномальный DNS-трафик. Откройте «Сетевой монитор» для расследования.", (150, 0, 150)),
            5: ("Уровень 5: Сетевой монитор фиксирует аномальный трафик (DoS). Откройте «Мой компьютер» для расследования.", (200, 100, 0)),
            6: ("Уровень 6: SIEM обнаружил подозрительное соединение и передачу файла. Откройте «Почта» для расследования.", (180, 0, 180)),
            7: ("Уровень 7: SIEM фиксирует массовые попытки входа по SSH. Откройте приложение «SIEM» для расследования.", (200, 50, 50)),
        }
        
        if day in day_messages and not self.is_day_threat_resolved(day):
            message, color = day_messages[day]
            self.display_message(message, color=color, clickable=False)
        
        # Показываем соответствующие алерты
        if day == 1:
            self.phishing_email_added = True
        elif day == 2 and not self.is_day_threat_resolved(day):
            self.show_siem_alert()
        elif day == 3 and not self.is_day_threat_resolved(day):
            self.show_antivirus_alert()
        elif day == 4 and not self.is_day_threat_resolved(day):
            self.show_dns_alert()
        # --- НОВЫЕ АЛЕРТЫ ---
        elif day == 5 and not self.is_day_threat_resolved(day):
            self.show_dos_alert()
        elif day == 6 and not self.is_day_threat_resolved(day):
            self.show_meterpreter_alert()
        elif day == 7 and not self.is_day_threat_resolved(day):
            self.show_ssh_alert()
        # --- КОНЕЦ НОВЫХ АЛЕРТОВ ---
        
    def _has_investigation_window(self, window_type):
        """Проверить, открыто ли уже окно расследования данного типа."""
        return any(getattr(w, 'window_type', None) == window_type for w in self.windows)

    def _add_investigation_for_day_if_needed(self, window_type):
        """Добавить окно расследования, если задание дня ещё не выполнено и окно ещё не открыто."""
        day_by_type = {
            "valid_accounts_investigation": 2,
            "process_injection_investigation": 3,
            "dns_c2_investigation": 4,
            "dos_investigation": 5,
            "meterpreter_investigation": 6,
            "ssh_bruteforce_investigation": 7,
        }
        day = day_by_type.get(window_type)
        if day is None or self.current_day != day or self.is_day_threat_resolved(day):
            return
        if self._has_investigation_window(window_type):
            return
        self.add_investigation_window(window_type)
        # Письмо о срочном обновлении только в 1-й день (PHISHING_EMAIL в add_phishing_email_to_window); в 6-й день в почту не добавляем

    # --- НОВЫЕ МЕТОДЫ ДЛЯ ПОКАЗА АЛЕРТОВ ---
    def show_dos_alert(self):
        """Показ уведомления о DoS атаке для дня 5 (расследование — через приложения)"""
        if not self.dos_alert_shown and not self.is_day_threat_resolved(5):
            self.display_message("СЕТЕВОЙ МОНИТОР: Аномальный трафик на 80 порт! Возможна DoS-атака. Откройте «Мой компьютер» для расследования.",
                               color=(200, 100, 0), duration=0)
            self.dos_alert_shown = True

    def show_meterpreter_alert(self):
        """Показ уведомления о Meterpreter для дня 6"""
        if not self.meterpreter_alert_shown and not self.is_day_threat_resolved(6):
            self.display_message("SIEM: Обнаружено подозрительное соединение и передача файла. Откройте «Почта» для расследования.",
                               color=(180, 0, 180))
            self.meterpreter_alert_shown = True

    def show_ssh_alert(self):
        """Показ уведомления о брутфорсе SSH для дня 7"""
        if not self.ssh_alert_shown and not self.is_day_threat_resolved(7):
            self.display_message("SIEM: Массовые неудачные попытки входа по SSH! Откройте приложение «SIEM» для расследования.",
                               color=(200, 50, 50))
            self.ssh_alert_shown = True
    # --- КОНЕЦ НОВЫХ МЕТОДОВ ---

    def show_antivirus_alert(self):
        """Показ уведомления от антивируса для дня 3 (расследование — через приложения)"""
        if not self.antivirus_alert_shown and not self.is_day_threat_resolved(3):
            self.display_message("АНТИВИРУС: Обнаружена подозрительная активность процессов! Откройте «Антивирус» или «Диспетчер задач».",
                               color=(200, 0, 0))
            self.antivirus_alert_shown = True
            
    def show_dns_alert(self):
        """Показ уведомления о DNS угрозе для дня 4"""
        if not self.dns_alert_shown and not self.is_day_threat_resolved(4):
            self.display_message("SIEM: Обнаружен подозрительный DNS-трафик! Откройте «Сетевой монитор» для расследования.",
                               color=(150, 0, 150))
            self.dns_alert_shown = True
            
    def handle_event(self, event):
        # Проверка клика по сообщению
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            taskbar_y = self.screen_height - self.taskbar_height
            start_button_rect = pygame.Rect(5, taskbar_y + 5, 80, 30)
            
            if self.show_message_flag and self.message_clickable:
                message_rect = self._get_message_rect()
                if message_rect and message_rect.collidepoint(event.pos):
                    if self.message_callback:
                        self.message_callback()
                        return True

            # Клик по шумовому уведомлению просто закрывает его — оно не ведёт никуда
            if self.noise_timer > 0 and self._get_noise_rect().collidepoint(event.pos):
                self.noise_timer = 0
                self.noise_cooldown = random.randint(360, 660)
                return True

            # Меню «Пуск»: клик по «Выключить»
            if self.show_start_menu and self.start_shutdown_rect and self.start_shutdown_rect.collidepoint(event.pos):
                self.show_start_menu = False
                if self.game_manager:
                    self.game_manager.show_credits_from_shutdown()
                return True
            # Клик вне меню «Пуск» — закрыть меню
            if self.show_start_menu and self.start_menu_rect and not self.start_menu_rect.collidepoint(event.pos) and not start_button_rect.collidepoint(event.pos):
                self.show_start_menu = False
            # Клик по кнопке «Пуск» на панели задач
            elif start_button_rect.collidepoint(event.pos):
                self.show_start_menu = not self.show_start_menu
                return True
            
            # Клик по панели задач: восстановление свёрнутого окна по кнопке (не по области часов)
            if event.pos[1] >= taskbar_y + 5 and event.pos[1] < taskbar_y + self.taskbar_height - 5 and event.pos[0] < self.screen_width - 80:
                x_offset = 95
                for window in self.windows:
                    task_rect = pygame.Rect(x_offset, taskbar_y + 5, 150, self.taskbar_height - 10)
                    if task_rect.collidepoint(event.pos):
                        if window.minimized:
                            window.minimized = False
                            window.rect.height = window.original_height
                        if window != self.windows[-1]:
                            self.windows.remove(window)
                            self.windows.append(window)
                        return True
                    x_offset += 155
        
        # Обработка событий в окнах
        window_to_close = None
        window_to_front = None
        
        for i in range(len(self.windows) - 1, -1, -1):
            window = self.windows[i]
            result = window.handle_event(event)
            
            if result == "close":
                window_to_close = window
                break
            elif result == "bring_to_front":
                window_to_front = window
                break
            elif result == "password_changed":
                self.game_manager.complete_objective("Сменить пароль учетной записи")
                break
            elif result == "start_phishing_investigation":
                self.game_manager.start_phishing_investigation()
                window_to_close = window
                break
            elif result == "start_valid_accounts_investigation":
                self.game_manager.start_valid_accounts_investigation()
                window_to_close = window
                break
            elif result == "start_process_injection_investigation":
                self.open_task_manager()
                window_to_close = window
                break
            elif result == "start_dns_c2_investigation":
                self.open_traffic_analyzer()
                window_to_close = window
                break
            elif result == "open_siem_interface":
                self.open_siem_system()
                window_to_close = window
                break
            # --- НОВЫЕ РЕЗУЛЬТАТЫ ДЛЯ ДНЕЙ 5, 6, 7 ---
            elif result == "start_dos_investigation":
                self.game_manager.start_dos_investigation()
                window_to_close = window
                break
            elif result == "start_meterpreter_investigation":
                self.game_manager.start_meterpreter_investigation()
                window_to_close = window
                break
            elif result == "start_ssh_bruteforce_investigation":
                self.game_manager.start_ssh_bruteforce_investigation()
                window_to_close = window
                break
            # --- КОНЕЦ НОВЫХ РЕЗУЛЬТАТОВ ---
            elif result is True:
                break
                
        if window_to_close:
            self.windows.remove(window_to_close)
            
        if window_to_front and window_to_front != self.windows[-1]:
            self.windows.remove(window_to_front)
            self.windows.append(window_to_front)
            
        if not window_to_close and not window_to_front:
            for icon in self.icons:
                if icon.handle_event(event):
                    return True
        
        if self.next_day_button:
            if self.next_day_button.handle_event(event):
                return True

        return False

    def update(self):
        self.time_update_timer += 1
        if self.time_update_timer >= 60 * 60:
            self._update_game_time()
            self.time_update_timer = 0
            
        for window in self.windows:
            window.update()
        
        for icon in self.icons:
            icon.update()
            
        if self.show_message_flag and self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.show_message_flag = False
        # duration=0 означает «без таймера» — плашка не скрывается сама

        if self.achievement_toast_timer > 0:
            self.achievement_toast_timer -= 1

        self._update_noise()

        self._check_time_events()

        # После завершения расследования текущего дня скрываем активный алерт угрозы (день 5 — плашка не скрывается)
        if self.is_day_threat_resolved() and self.current_day != 5:
            self.clear_threat_message()
        
        if self.next_day_button:
            self.next_day_button.update()

    def _update_noise(self):
        """Фоновые уведомления-«пустышки»: появляются периодически, пока задание
        дня не выполнено, отдельно от настоящего алерта (см. _draw_noise_toast)."""
        if self.is_day_threat_resolved():
            self.noise_timer = 0
            return
        if self.noise_timer > 0:
            self.noise_timer -= 1
            return
        if self.noise_cooldown > 0:
            self.noise_cooldown -= 1
            return
        self.noise_text = random.choice(NOISE_MESSAGES)
        self.noise_timer = 240
        self.noise_cooldown = random.randint(360, 660)
        sound_manager.play("noise")

    def _update_game_time(self):
        h, m = map(int, self.game_time.split(':'))
        m += 5
        if m >= 60:
            m = 0
            h += 1
        
        if h >= 18:
            self.game_time = "18:00"
        else:
            self.game_time = f"{h:02d}:{m:02d}"

    def _check_time_events(self):
        # Унифицированная логика показа алертов через 1 минуту игрового времени
        if self.game_time == "09:01":
            if self.current_day == 1 and not self.phishing_email_added and not self.is_day_threat_resolved(1):
                self.display_message("СИСТЕМА: Обнаружена подозрительная активность. Проверьте почту на наличие фишинга!", color=(150, 0, 0))
                self.phishing_email_added = True
            elif self.current_day == 2 and not self.siem_alert_shown and not self.is_day_threat_resolved(2):
                self.show_siem_alert()
                self.siem_alert_shown = True
            elif self.current_day == 3 and not self.antivirus_alert_shown and not self.is_day_threat_resolved(3):
                self.show_antivirus_alert()
                self.antivirus_alert_shown = True
            elif self.current_day == 4 and not self.dns_alert_shown and not self.is_day_threat_resolved(4):
                self.show_dns_alert()
                self.dns_alert_shown = True
            # --- НОВЫЕ УСЛОВИЯ ДЛЯ АЛЕРТОВ ПО ВРЕМЕНИ ---
            elif self.current_day == 5 and not self.dos_alert_shown and not self.is_day_threat_resolved(5):
                self.show_dos_alert()
            elif self.current_day == 6 and not self.meterpreter_alert_shown and not self.is_day_threat_resolved(6):
                self.show_meterpreter_alert()
            elif self.current_day == 7 and not self.ssh_alert_shown and not self.is_day_threat_resolved(7):
                self.show_ssh_alert()
            # --- КОНЕЦ НОВЫХ УСЛОВИЙ ---
        
    def show_siem_alert(self):
        if not self.is_day_threat_resolved(2):
            self.display_message("SIEM: Обнаружена подозрительная активность учётных записей! Откройте приложение «SIEM» для расследования.",
                               color=(150, 0, 0))

    def add_phishing_email_to_window(self, window):
        if window.window_type != "email" or window.phishing_email_added:
            return
        if self.current_day == 1 and self.is_day_threat_resolved(1):
            return
        window.add_phishing_email(PHISHING_EMAIL)
        window.phishing_email_added = True

    def remove_phishing_email_from_windows(self):
        """Убрать фишинговое письмо из всех окон почты после выполнения задания дня 1."""
        for w in self.windows:
            if getattr(w, 'window_type', None) == "email" and hasattr(w, 'remove_phishing_email'):
                w.remove_phishing_email()

    def add_investigation_window(self, window_type):
        x = (self.screen_width - 600) // 2
        y = (self.screen_height - 450) // 2
        
        if window_type == "process_injection":
            title = "Расследование угрозы"
        elif window_type == "valid_accounts_investigation":
            title = "Расследование угрозы"
        elif window_type == "phishing_investigation":
            title = "Расследование угрозы"
        elif window_type == "dns_c2_investigation":
            title = "Расследование угрозы"
        # --- НОВЫЕ ТИПЫ ОКОН ---
        elif window_type == "dos_investigation":
            title = "Расследование DoS атаки"
        elif window_type == "meterpreter_investigation":
            title = "Расследование атаки Meterpreter"
        elif window_type == "ssh_bruteforce_investigation":
            title = "Расследование брутфорс атаки"
        # --- КОНЕЦ НОВЫХ ТИПОВ ---
        else:
            title = "Расследование инцидента"
            
        window = Window(x, y, 600, 450, title, window_type, self.game_manager)
        self.windows.append(window)

    def can_complete_day(self, day=None):
        """Проверка: выполнены ли все обязательные действия для завершения дня."""
        day = day if day is not None else self.current_day
        required = REQUIRED_TO_COMPLETE_DAY.get(day, [])
        return all(obj in self.game_manager.completed_objectives for obj in required)

    def try_show_next_day_button(self):
        """Показать кнопку «Далее» только если все задания уровня выполнены."""
        if self.show_next_day_button:
            return
        if self.can_complete_day():
            self.add_next_day_button()

    def add_next_day_button(self):
        """Добавляет кнопку следующего дня"""
        self.show_next_day_button = True
        button_width, button_height = 200, 50
        x = self.screen_width - button_width - 10
        y = self.screen_height - self.taskbar_height - button_height - 10
        
        callback = self.complete_day
        text = "ДАЛЕЕ"
        
        self.next_day_button = Button(
            x, y, button_width, button_height, 
            text, (0, 100, 0), 
            callback
        )
        
    def complete_day(self):
        """Завершение текущего дня"""
        if self.game_manager.current_day == 1:
            self.game_manager.complete_day_one()
        elif self.game_manager.current_day == 2:
            self.game_manager.complete_day_two()
        elif self.game_manager.current_day == 3:
            self.game_manager.complete_day_three()
        elif self.game_manager.current_day == 4:
            self.game_manager.complete_day_four()
        # --- НОВЫЕ ДНИ ---
        elif self.game_manager.current_day == 5:
            self.game_manager.complete_day_five()
        elif self.game_manager.current_day == 6:
            self.game_manager.complete_day_six()
        elif self.game_manager.current_day == 7:
            self.game_manager.complete_day_seven()
        # --- КОНЕЦ НОВЫХ ДНЕЙ ---

    def display_message(self, text, color=(0, 0, 0), duration=300, clickable=False, callback=None, sound="alert"):
        """Отображение сообщения с возможностью клика"""
        self.message_text = text
        self.message_color = color
        self.message_timer = duration
        self.show_message_flag = True
        self.message_clickable = clickable
        self.message_callback = callback
        if sound:
            sound_manager.play(sound)

    def clear_threat_message(self):
        """Скрыть текущее сообщение об угрозе."""
        self.show_message_flag = False
        self.message_timer = 0
        self.message_clickable = False
        self.message_callback = None

    def show_achievement_toast(self, text, duration=240):
        """Показать тост о разблокированной ачивке (независим от сообщений об угрозах)."""
        self.achievement_toast_text = text
        self.achievement_toast_timer = duration
        sound_manager.play("achievement")

    def is_day_threat_resolved(self, day=None):
        """Проверка: завершено ли ключевое расследование для дня."""
        day = self.current_day if day is None else day
        objective_by_day = {
            1: "Расследовать фишинг атаку",
            2: "Расследовать инцидент компрометации учетных записей",
            3: "Расследовать Process Injection атаку",
            4: "Расследовать DNS C2 атаку",
            5: "Расследовать DoS атаку",
            6: "Расследовать атаку с Meterpreter",
            7: "Расследовать брутфорс SSH атаку",
        }
        objective_name = objective_by_day.get(day)
        return bool(objective_name and objective_name in self.game_manager.completed_objectives)
        
    def _get_message_rect(self):
        """Получить прямоугольник сообщения для проверки кликов (совпадает с _draw_message)."""
        message_font = theme.font(theme.FONT_MD)
        max_width = min(420, self.screen_width - 40)
        lines = self._wrap_message(self.message_text, message_font, max_width - 24)
        line_surfaces = [message_font.render(line, True, theme.TEXT_PRIMARY) for line in lines]

        padding = 14
        rect_width = max((s.get_width() for s in line_surfaces), default=0) + padding * 2 + 8
        rect_height = sum(s.get_height() + 4 for s in line_surfaces) + padding * 2 - 4

        return pygame.Rect(
            self.screen_width - rect_width - 14,
            self.screen_height - self.taskbar_height - rect_height - 14,
            rect_width, rect_height
        )
        
    def open_window(self, window_type, name):
        x, y, width, height = 50, 50, 600, 400
        title = name
        
        if window_type == "email":
            width, height = 600, 500
        elif window_type == "antivirus":
            width, height = 400, 250
        elif window_type == "settings":
            width, height = 500, 300
        elif window_type == "siem_system":
            width, height = 650, 450
        elif window_type == "task_manager":
            self.open_task_manager()
            return
        elif window_type == "traffic_analyzer":
            self.open_traffic_analyzer()
            return
        
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2
        
        for window in self.windows:
            if window.window_type == window_type:
                # Повторное открытие окна с иконки восстанавливает его после сворачивания
                if window.minimized:
                    window.minimized = False
                    window.rect.height = window.original_height

                self.windows.remove(window)
                self.windows.append(window)
                
                if window_type == "email" and self.current_day == 1:
                    self.add_phishing_email_to_window(window)
                elif window_type == "email" and self.current_day == 6:
                    self._add_investigation_for_day_if_needed("meterpreter_investigation")
                elif window_type == "siem_system":
                    self._add_investigation_for_day_if_needed("valid_accounts_investigation")
                    self._add_investigation_for_day_if_needed("ssh_bruteforce_investigation")
                elif window_type == "antivirus" and self.current_day == 3:
                    self._add_investigation_for_day_if_needed("process_injection_investigation")
                elif window_type == "my_computer" and self.current_day == 5:
                    self._add_investigation_for_day_if_needed("dos_investigation")
                return
        
        if window_type == "internet":
            self.game_manager.open_internet_browser()
            return
            
        if window_type == "siem_system":
            self.windows.append(Window(x, y, width, height, title, window_type, self.game_manager))
            self._add_investigation_for_day_if_needed("valid_accounts_investigation")
            self._add_investigation_for_day_if_needed("ssh_bruteforce_investigation")
            return
            
        new_window = Window(
            x, y, width, height, title, window_type, self.game_manager
        )
        self.windows.append(new_window)
        
        if window_type == "email":
            self.send_initial_emails(new_window)
            if self.current_day == 1:
                self.add_phishing_email_to_window(new_window)
            elif self.current_day == 6:
                self._add_investigation_for_day_if_needed("meterpreter_investigation")
        elif window_type == "antivirus" and self.current_day == 3:
            self._add_investigation_for_day_if_needed("process_injection_investigation")
        elif window_type == "my_computer" and self.current_day == 5:
            self._add_investigation_for_day_if_needed("dos_investigation")

    def open_task_manager(self):
        from ..scenes.task_manager import TaskManager

        def on_task_manager_complete(threat_detected):
            self.game_manager.scene_manager.pop_scene()
            if threat_detected and self.current_day == 3:
                self.game_manager.complete_objective("Расследовать Process Injection атаку")
                self.game_manager.try_show_next_day_button()
                self.display_message("Атака Process Injection успешно отражена!", (0, 150, 0), sound="success")
        
        threat_resolved = self.current_day == 3 and self.is_day_threat_resolved(3)
        task_manager = TaskManager(self.screen_width, self.screen_height, on_task_manager_complete, self.current_day, threat_resolved_for_day=threat_resolved)
        self.game_manager.scene_manager.push_scene(task_manager)

    def open_traffic_analyzer(self):
        from ..scenes.dns_analyzer import DNSAnalyzer

        def on_analyzer_complete(threat_detected):
            self.game_manager.scene_manager.pop_scene()
            if threat_detected and self.current_day == 4:
                self.game_manager.complete_objective("Расследовать DNS C2 атаку")
                self.game_manager.try_show_next_day_button()
                self.display_message("Атака DNS C2 успешно отражена!", (0, 150, 0), sound="success")
        
        threat_resolved = self.current_day == 4 and self.is_day_threat_resolved(4)
        analyzer = DNSAnalyzer(self.screen_width, self.screen_height, on_analyzer_complete, self.current_day, threat_resolved_for_day=threat_resolved)
        self.game_manager.scene_manager.push_scene(analyzer)

    def send_initial_emails(self, window):
        if not self.initial_email_sent and window.window_type == "email":
            window.add_initial_emails(INITIAL_EMAILS)
            self.initial_email_sent = True
            
    def open_siem_system(self):
        from ..scenes.siem_system import SIEMSystem
        
        def on_siem_complete(threat_detected):
            self.game_manager.scene_manager.pop_scene()
            # Плашку и окно расследования показываем только если задание дня 2 ещё не выполнено
            if threat_detected and not self.is_day_threat_resolved(2):
                self.display_message("ОБНАРУЖЕНА КОМПРОМЕТАЦИЯ УЧЕТНОЙ ЗАПИСИ! Запустите расследование!", (255, 0, 0))
                self.add_investigation_window("valid_accounts_investigation")
        
        # Плашки задания дня 2 не показывать в день 3 и позже, а также когда задание дня 2 уже выполнено
        threat_resolved = (self.current_day != 2) or self.is_day_threat_resolved(2)
        siem = SIEMSystem(self.screen_width, self.screen_height, on_siem_complete, self.current_day, threat_resolved_for_day=threat_resolved)
        self.game_manager.scene_manager.push_scene(siem)
        
    def draw(self, screen):
        if self.background_image:
            screen.blit(self.background_image, (0, 0))
        else:
            screen.fill(self.background_color)
        
        for icon in self.icons:
            icon.draw(screen)
            
        for window in self.windows:
            window.draw(screen)
            
        self._draw_taskbar(screen)
        
        if self.show_next_day_button and self.next_day_button:
            self.next_day_button.draw(screen)
            
        if self.show_message_flag:
            self._draw_message(screen)

        if self.achievement_toast_timer > 0:
            self._draw_achievement_toast(screen)

        if self.noise_timer > 0:
            self._draw_noise_toast(screen)

    def _draw_noise_toast(self, screen):
        """Фоновое уведомление без угрозы — нижний левый угол, нейтральный цвет
        (не красный/жёлтый, как настоящий алерт), чтобы его нужно было отличать
        по смыслу, а не просто по расположению или цвету."""
        font = theme.font(theme.FONT_XS)
        surf = font.render(self.noise_text, True, theme.TEXT_MUTED)
        padding = 10
        rect = self._get_noise_rect(surf)
        pygame.draw.rect(screen, theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_SM)
        pygame.draw.rect(screen, theme.BORDER_SOFT, rect, 1, border_radius=theme.RADIUS_SM)
        screen.blit(surf, (rect.x + padding, rect.y + padding))

    def _get_noise_rect(self, surf=None):
        if surf is None:
            surf = theme.font(theme.FONT_XS).render(self.noise_text, True, theme.TEXT_MUTED)
        padding = 10
        return pygame.Rect(
            14, self.screen_height - self.taskbar_height - surf.get_height() - padding * 2 - 10,
            surf.get_width() + padding * 2, surf.get_height() + padding * 2
        )

    def _draw_achievement_toast(self, screen):
        """Тост о разблокированной ачивке — верхний правый угол, отдельно от сообщений об угрозах."""
        font = theme.font(theme.FONT_SM, bold=True)
        label_font = theme.font(theme.FONT_XS)
        title_surf = font.render(self.achievement_toast_text, True, theme.TEXT_PRIMARY)
        label_surf = label_font.render("ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО", True, theme.WARNING)

        padding = 14
        width = max(title_surf.get_width(), label_surf.get_width()) + padding * 2 + 10
        height = title_surf.get_height() + label_surf.get_height() + padding * 2 + 4
        rect = pygame.Rect(self.screen_width - width - 16, 16, width, height)

        theme.draw_panel(screen, rect, radius=theme.RADIUS_MD, fill=theme.SURFACE, border=theme.WARNING)
        screen.blit(label_surf, (rect.x + padding, rect.y + padding // 2))
        screen.blit(title_surf, (rect.x + padding, rect.y + padding // 2 + label_surf.get_height() + 4))

    def _draw_taskbar(self, screen):
        taskbar_rect = pygame.Rect(0, self.screen_height - self.taskbar_height, self.screen_width, self.taskbar_height)
        pygame.draw.rect(screen, self.taskbar_color, taskbar_rect)
        pygame.draw.line(screen, theme.ACCENT_DIM, (0, self.screen_height - self.taskbar_height), (self.screen_width, self.screen_height - self.taskbar_height), 2)

        start_button_rect = pygame.Rect(6, self.screen_height - self.taskbar_height + 6, 84, self.taskbar_height - 12)
        pygame.draw.rect(screen, theme.ACCENT_DIM, start_button_rect, border_radius=theme.RADIUS_SM)
        start_font = theme.font(theme.FONT_SM, bold=True)
        start_text = start_font.render("ПУСК", True, theme.TEXT_PRIMARY)
        screen.blit(start_text, start_text.get_rect(center=start_button_rect.center))

        # Меню «Пуск» над панелью задач
        if self.show_start_menu:
            menu_w, menu_h = 170, 40
            menu_x, menu_y = 6, self.screen_height - self.taskbar_height - menu_h - 6
            self.start_menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
            theme.draw_panel(screen, self.start_menu_rect, radius=theme.RADIUS_SM)
            item_font = theme.font(theme.FONT_SM)
            self.start_shutdown_rect = pygame.Rect(menu_x + 6, menu_y + 4, menu_w - 12, menu_h - 8)
            shutdown_text = item_font.render("Выключить", True, theme.TEXT_PRIMARY)
            screen.blit(shutdown_text, (self.start_shutdown_rect.x + 8, self.start_shutdown_rect.centery - shutdown_text.get_height() // 2))
        else:
            self.start_menu_rect = None
            self.start_shutdown_rect = None

        x_offset = 100
        task_font = theme.font(theme.FONT_XS)

        # Кнопка для каждого окна (в т.ч. свёрнутого) — как в ОС
        for window in self.windows:
            task_rect = pygame.Rect(
                x_offset, self.screen_height - self.taskbar_height + 6,
                150, self.taskbar_height - 12
            )
            fill = theme.ELEVATED if window.minimized else theme.SURFACE_ALT
            pygame.draw.rect(screen, fill, task_rect, border_radius=theme.RADIUS_SM)
            pygame.draw.rect(screen, theme.BORDER, task_rect, 1, border_radius=theme.RADIUS_SM)
            task_name = window.title[:15] + "..." if len(window.title) > 15 else window.title
            task_text = task_font.render(task_name, True, theme.TEXT_PRIMARY)
            screen.blit(task_text, (task_rect.x + 8, task_rect.centery - task_text.get_height() // 2))
            x_offset += 158

        time_font = theme.font(theme.FONT_XS)
        time_text = time_font.render(self.game_time, True, theme.TEXT_SECONDARY)
        time_rect = time_text.get_rect()
        time_rect.right = self.screen_width - 14
        time_rect.centery = self.screen_height - self.taskbar_height // 2
        screen.blit(time_text, time_rect)

    def _draw_message(self, screen):
        message_font = theme.font(theme.FONT_MD)
        max_width = min(420, self.screen_width - 40)
        lines = self._wrap_message(self.message_text, message_font, max_width - 24)
        line_surfaces = [message_font.render(line, True, theme.TEXT_PRIMARY) for line in lines]

        padding = 14
        rect_width = max((s.get_width() for s in line_surfaces), default=0) + padding * 2 + 8
        rect_height = sum(s.get_height() + 4 for s in line_surfaces) + padding * 2 - 4

        message_rect = pygame.Rect(
            self.screen_width - rect_width - 14,
            self.screen_height - self.taskbar_height - rect_height - 14,
            rect_width, rect_height
        )

        accent = theme.ACCENT if self.message_clickable else theme.WARNING
        theme.draw_panel(screen, message_rect, radius=theme.RADIUS_MD, fill=theme.SURFACE, border=theme.BORDER)
        pygame.draw.rect(screen, accent, (message_rect.x, message_rect.y, 5, message_rect.height), border_top_left_radius=theme.RADIUS_MD, border_bottom_left_radius=theme.RADIUS_MD)

        y = message_rect.y + padding
        for surf in line_surfaces:
            screen.blit(surf, (message_rect.x + padding + 8, y))
            y += surf.get_height() + 4

        if self.message_clickable:
            hint = theme.font(theme.FONT_XS).render("Нажмите, чтобы открыть", True, theme.ACCENT)
            screen.blit(hint, (message_rect.x + padding + 8, message_rect.bottom - hint.get_height() - 6))

    @staticmethod
    def _wrap_message(text, font, max_width):
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
        return lines[:4]
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self._update_background_image()
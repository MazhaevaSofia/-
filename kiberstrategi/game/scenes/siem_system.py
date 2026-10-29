# [file name]: siem_system.py
# [file content begin]
import pygame
from ..ui.button import Button

class SIEMSystem:
    def __init__(self, screen_width, screen_height, on_complete_callback, day=1, threat_resolved_for_day=False):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        self.day = day
        self.threat_resolved_for_day = threat_resolved_for_day
        
        # Данные логов SIEM в зависимости от дня
        if day == 1:
            # День 1: только обычные процессы
            self.log_entries = [
                {"time": "08:15", "user": "Петров С.С.", "action": "Вход в систему", "ip": "192.168.1.100", "risk": "low"},
                {"time": "08:20", "user": "Иванова М.К.", "action": "Доступ к почте", "ip": "192.168.1.101", "risk": "low"},
                {"time": "08:25", "user": "Сидоров А.В.", "action": "Работа с документами", "ip": "192.168.1.102", "risk": "low"},
                {"time": "09:00", "user": "Козлова Е.П.", "action": "Вход в CRM", "ip": "192.168.1.103", "risk": "low"},
                {"time": "09:15", "user": "Федоров П.К.", "action": "Совещание в Teams", "ip": "192.168.1.104", "risk": "low"},
                {"time": "10:30", "user": "Смирнова О.Л.", "action": "Обновление отчетов", "ip": "192.168.1.105", "risk": "low"},
                {"time": "11:45", "user": "Кузнецов Д.М.", "action": "Работа с базой данных", "ip": "192.168.1.106", "risk": "low"},
                {"time": "14:20", "user": "Новикова Т.С.", "action": "Отправка документов", "ip": "192.168.1.107", "risk": "low"},
            ]
        else:
            # День 2: с подозрительной активностью
            self.log_entries = [
                {"time": "08:15", "user": "Петров С.С.", "action": "Вход в систему", "ip": "192.168.1.100", "risk": "low"},
                {"time": "08:20", "user": "Иванова М.К.", "action": "Доступ к почте", "ip": "192.168.1.101", "risk": "low"},
                {"time": "08:25", "user": "Сидоров А.В.", "action": "Работа с документами", "ip": "192.168.1.102", "risk": "low"},
                {"time": "09:00", "user": "Козлова Е.П.", "action": "Вход в CRM", "ip": "192.168.1.103", "risk": "low"},
                {"time": "23:40", "user": "Волков Д.С. (HR)", "action": "Вход в систему", "ip": "192.168.1.150", "risk": "medium"},
                {"time": "23:42", "user": "Волков Д.С. (HR)", "action": "Доступ к финансовым отчетам", "ip": "192.168.1.150", "risk": "high"},
                {"time": "23:45", "user": "Волков Д.С. (HR)", "action": "Попытка доступа к БД сотрудников", "ip": "192.168.1.150", "risk": "critical"},
                {"time": "23:47", "user": "Волков Д.С. (HR)", "action": "Скачивание архивов с документами", "ip": "192.168.1.150", "risk": "critical"},
                {"time": "23:50", "user": "Волков Д.С. (HR)", "action": "Попытка эскалации привилегий", "ip": "192.168.1.150", "risk": "critical"},
                {"time": "08:30", "user": "Федоров П.К.", "action": "Совещание в Teams", "ip": "192.168.1.104", "risk": "low"},
            ]
        
        self.threat_detected = False
        self.selected_log_index = None
        
        # Кнопка закрытия
        self.close_button = Button(
            self.screen_width - 120, self.screen_height - 60,
            100, 35, "Закрыть", (200, 100, 100), self.close_siem
        )
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 14)
    
    def close_siem(self):
        """Закрытие SIEM системы"""
        self.on_complete(self.threat_detected)
    
    def handle_event(self, event):
        # Обработка кнопки закрытия
        if self.close_button.handle_event(event):
            return True
        
        # Обработка кликов по записям логов
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, log in enumerate(self.log_entries):
                log_rect = pygame.Rect(50, 100 + i * 35, 900, 30)
                if log_rect.collidepoint(event.pos):
                    self.selected_log_index = i
                    if log["risk"] in ["high", "critical"] and not self.threat_detected and not self.threat_resolved_for_day:
                        self.threat_detected = True
                    return True
            
        return False
    
    def update(self):
        self.close_button.update()
    
    def draw(self, screen):
        # Фон
        screen.fill((20, 25, 35))
        
        # Заголовок
        title_text = f"SIEM СИСТЕМА МОНИТОРИНГА - Уровень {self.day}"
        title = self.font_large.render(title_text, True, (100, 200, 255))
        screen.blit(title, (self.screen_width//2 - title.get_width()//2, 20))
        
        # Заголовки колонок
        headers = ["Время", "Пользователь", "Событие", "IP-адрес", "Уровень риска"]
        x_pos = 50
        for header in headers:
            header_text = self.font_small.render(header, True, (255, 255, 100))
            screen.blit(header_text, (x_pos, 80))
            x_pos += 180
        
        # Записи логов (после выполнения дня 2 critical/high помечаются как решённые)
        for i, log in enumerate(self.log_entries):
            y_pos = 100 + i * 35
            
            risk_colors = {
                "low": (40, 45, 55),
                "medium": (80, 70, 30),
                "high": (100, 50, 30),
                "critical": (120, 30, 30)
            }
            resolved = self.threat_resolved_for_day and log["risk"] in ("high", "critical")
            if resolved:
                bg_color = (30, 60, 40)
                risk_display = "РЕШЕНО"
                risk_color = (100, 255, 100)
            else:
                bg_color = risk_colors[log["risk"]]
                risk_display = log["risk"].upper()
                risk_color = (100, 255, 100) if log["risk"] == "low" else (255, 255, 100) if log["risk"] == "medium" else (255, 150, 100) if log["risk"] == "high" else (255, 100, 100)
            
            log_rect = pygame.Rect(50, y_pos, 900, 30)
            pygame.draw.rect(screen, bg_color, log_rect)
            if i == self.selected_log_index:
                pygame.draw.rect(screen, (255, 255, 100), log_rect, 2)
            
            screen.blit(self.font_tiny.render(log["time"], True, (255, 255, 255)), (60, y_pos + 8))
            screen.blit(self.font_tiny.render(log["user"], True, (255, 255, 255)), (230, y_pos + 8))
            screen.blit(self.font_tiny.render(log["action"], True, (255, 255, 255)), (410, y_pos + 8))
            screen.blit(self.font_tiny.render(log["ip"], True, (255, 255, 255)), (590, y_pos + 8))
            screen.blit(self.font_tiny.render(risk_display, True, risk_color), (770, y_pos + 8))
        
        # Кнопка
        self.close_button.draw(screen)
        
        # Инструкция (без плашек задания дня 2 при заходе в день 3 или после выполнения дня 2)
        if self.threat_resolved_for_day:
            if self.day == 2:
                instruction = self.font_small.render("Журнал событий. Расследование по этому дню завершено.", True, (100, 255, 100))
            else:
                instruction = self.font_small.render("Журнал событий.", True, (150, 200, 255))
        elif self.day == 1:
            instruction = self.font_small.render("Проверьте журнал событий на наличие подозрительной активности", True, (255, 255, 100))
        elif not self.threat_detected:
            instruction = self.font_small.render("Найдите подозрительные записи в журнале событий", True, (255, 255, 100))
        else:
            instruction = self.font_small.render("Угроза обнаружена! Закройте SIEM для начала расследования", True, (255, 100, 100))
        screen.blit(instruction, (self.screen_width//2 - instruction.get_width()//2, self.screen_height - 100))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h

# [file name]: dns_analyzer.py
# [file content begin]
import pygame
import random
from ..ui.button import Button

class DNSAnalyzer:
    def __init__(self, screen_width, screen_height, on_complete_callback, current_day=1, threat_resolved_for_day=False):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        self.current_day = current_day
        self.threat_resolved_for_day = threat_resolved_for_day
        
        # Данные DNS трафика
        self.dns_logs = self._generate_dns_logs()
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_mono = pygame.font.Font(None, 16)
        
        # Состояние
        self.selected_log = None
        self.threat_detected = False
        self.threat_resolved_by_investigation = False  # True только после успешного завершения расследования
        self.show_investigation = False
        self.investigation_minigame = None
        
        # Кнопка закрытия
        self.close_button = Button(
            self.screen_width - 120, self.screen_height - 60,
            100, 35, "Закрыть", (200, 100, 100), self.close_analyzer
        )

    def _generate_dns_logs(self):
        """Генерация DNS логов (легитимные + подозрительные только в день 4)"""
        legitimate_logs = [
            {"time": "08:15:23", "source": "192.168.1.100", "query": "google.com", "type": "A", "status": "OK", "suspicious": False},
            {"time": "08:15:24", "source": "192.168.1.101", "query": "microsoft.com", "type": "A", "status": "OK", "suspicious": False},
            {"time": "08:15:25", "source": "192.168.1.102", "query": "github.com", "type": "AAAA", "status": "OK", "suspicious": False},
            {"time": "08:15:26", "source": "192.168.1.103", "query": "stackoverflow.com", "type": "A", "status": "OK", "suspicious": False},
            {"time": "08:15:27", "source": "192.168.1.104", "query": "youtube.com", "type": "CNAME", "status": "OK", "suspicious": False},
            {"time": "08:15:28", "source": "192.168.1.105", "query": "windowsupdate.com", "type": "A", "status": "OK", "suspicious": False},
            {"time": "08:15:29", "source": "192.168.1.106", "query": "live.com", "type": "A", "status": "OK", "suspicious": False},
            {"time": "08:15:30", "source": "192.168.1.107", "query": "aws.amazon.com", "type": "A", "status": "OK", "suspicious": False},
            {"time": "08:15:31", "source": "192.168.1.108", "query": "cloudflare.com", "type": "A", "status": "OK", "suspicious": False},
        ]
        
        # Подозрительные DNS запросы (C2 трафик) ТОЛЬКО для дня 4; после выполнения задания не показываем
        if self.current_day == 4 and not self.threat_resolved_for_day:
            suspicious_logs = [
                {"time": "08:15:32", "source": "192.168.1.150", "query": "aG9zdG5hbWU=.bot123.system-updates-service.net", "type": "TXT", "status": "OK", "suspicious": True},
                {"time": "08:15:37", "source": "192.168.1.150", "query": "d2hvYW1p.bot123.system-updates-service.net", "type": "TXT", "status": "OK", "suspicious": True},
                {"time": "08:15:42", "source": "192.168.1.150", "query": "cHdk.bot123.system-updates-service.net", "type": "TXT", "status": "OK", "suspicious": True},
                {"time": "08:15:47", "source": "192.168.1.150", "query": "bHM=.bot123.system-updates-service.net", "type": "TXT", "status": "OK", "suspicious": True},
            ]
            logs = legitimate_logs + suspicious_logs
        else:
            logs = legitimate_logs
            
        random.shuffle(logs)
        return sorted(logs, key=lambda x: x["time"])

    def close_analyzer(self):
        """Закрытие анализатора"""
        # Для дня 4 засчитываем угрозу только если расследование реально завершено успешно
        if self.current_day == 4:
            self.on_complete(self.threat_resolved_by_investigation)
        else:
            self.on_complete(self.threat_detected)

    def handle_event(self, event):
        # --- ИЗМЕНЕНО ---
        # Если активно расследование, передаем события ему
        if self.show_investigation and self.investigation_minigame:
            result = self.investigation_minigame.handle_event(event)
            if result:
                return True
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---
        
        if self.close_button.handle_event(event):
            return True
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Проверка кликов по логам
            if not self.show_investigation:
                for i, log in enumerate(self.dns_logs):
                    log_rect = pygame.Rect(50, 100 + i * 25, 900, 20)
                    if log_rect.collidepoint(event.pos):
                        self.selected_log = log
                        if log["suspicious"] and not self.threat_detected and self.current_day == 4 and not self.threat_resolved_for_day:
                            self.threat_detected = True
                            self.start_investigation()
                        return True
        return False

    def start_investigation(self):
        """
        --- ИЗМЕНЕНО ---
        Запуск мини-игры расследования DNS C2 (встраиваемый)
        """
        from ..scenes.dns_c2_minigame import DNSC2Minigame
        
        def on_investigation_complete(success, score=None):
            """Коллбэк при завершении расследования"""
            self.show_investigation = False
            self.investigation_minigame = None
            if success:
                self.threat_resolved_by_investigation = True
                self.close_analyzer()
        
        self.investigation_minigame = DNSC2Minigame(
            self.screen_width, self.screen_height, 
            on_investigation_complete
        )
        self.show_investigation = True

    def update(self):
        # --- ИЗМЕНЕНО ---
        # Если активно расследование, обновляем его
        if self.show_investigation and self.investigation_minigame:
            self.investigation_minigame.update()
            return
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---
        
        self.close_button.update()

    def draw(self, screen):
        # --- ИЗМЕНЕНО ---
        # Если активно расследование, рисуем его
        if self.show_investigation and self.investigation_minigame:
            self.investigation_minigame.draw(screen)
            return
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---
        
        # Иначе рисуем обычный интерфейс анализатора
        screen.fill((20, 30, 40))
        
        # Заголовок
        title = self.font_large.render("Анализатор сетевого трафика - DNS мониторинг", True, (255, 255, 255))
        screen.blit(title, (self.screen_width//2 - title.get_width()//2, 20))
        
        # Заголовки колонок
        headers = ["Время", "Источник", "DNS запрос", "Тип", "Статус"]
        x_positions = [50, 150, 350, 700, 800]
        
        for i, header in enumerate(headers):
            header_text = self.font_medium.render(header, True, (200, 200, 100))
            screen.blit(header_text, (x_positions[i], 70))
        
        # Список DNS логов
        for i, log in enumerate(self.dns_logs):
            y_pos = 100 + i * 25
            
            # Цвет фона для выбранного лога
            if log == self.selected_log:
                pygame.draw.rect(screen, (60, 60, 80), (45, y_pos, 910, 20))
            
            # Данные лога
            query_color = (255, 100, 100) if log["suspicious"] else (255, 255, 255)
            
            screen.blit(self.font_small.render(log["time"], True, (255, 255, 255)), (x_positions[0], y_pos))
            screen.blit(self.font_small.render(log["source"], True, (255, 255, 255)), (x_positions[1], y_pos))
            
            # Обрезаем длинные DNS запросы
            query_display = log["query"][:40] + "..." if len(log["query"]) > 40 else log["query"]
            screen.blit(self.font_small.render(query_display, True, query_color), (x_positions[2], y_pos))
            
            screen.blit(self.font_small.render(log["type"], True, (255, 255, 255)), (x_positions[3], y_pos))
            screen.blit(self.font_small.render(log["status"], True, (100, 255, 100)), (x_positions[4], y_pos))
        
        # Кнопка закрытия
        self.close_button.draw(screen)
        
        # Инструкция (без плашек «начать расследование», если задание дня 4 уже выполнено)
        if self.current_day == 4:
            if self.threat_resolved_for_day:
                instruction = self.font_small.render("Мониторинг DNS трафика. Расследование по этому дню завершено.", True, (100, 255, 100))
            elif self.threat_detected and not self.show_investigation:
                instruction = self.font_small.render("Обнаружен подозрительный DNS трафик! Нажмите на запрос к system-updates-service.net для расследования", True, (255, 100, 100))
            else:
                instruction = self.font_small.render("Найдите подозрительные DNS запросы с высокоэнтропийными поддоменами", True, (255, 255, 100))
        else:
            instruction = self.font_small.render("Мониторинг DNS трафика - все запросы в норме", True, (100, 255, 100))
        
        screen.blit(instruction, (self.screen_width//2 - instruction.get_width()//2, self.screen_height - 100))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
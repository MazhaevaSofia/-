# [file name]: task_manager.py
# [file content begin]
import pygame
import random
from ..ui.button import Button

class TaskManager:
    def __init__(self, screen_width, screen_height, on_complete_callback, current_day=1, threat_resolved_for_day=False):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        self.current_day = current_day
        self.threat_resolved_for_day = threat_resolved_for_day
        
        self.processes = self._generate_processes()
        
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 14)
        
        self.selected_process = None
        self.threat_detected = False
        self.threat_resolved_by_investigation = False  # True только после успешного завершения расследования
        self.show_investigation = False
        self.investigation_minigame = None
        # Обновление процентов раз в ~1.5 сек, чтобы не дёргалось 20 раз в секунду
        self._last_stats_update = pygame.time.get_ticks()
        self._STATS_UPDATE_INTERVAL_MS = 1500
        
        self.close_button = Button(
            self.screen_width - 120, self.screen_height - 60,
            100, 35, "Закрыть", (200, 100, 100), self.close_manager
        )

    # Общая «ёмкость» системы: суммарная нагрузка распределяется между процессами
    _TOTAL_CPU = 100
    _TOTAL_MEMORY_MB = 700
    # Доли легитимных процессов (сумма = 1), когда вредоносный есть — им достаётся остаток
    _LEGIT_CPU_WEIGHTS = [
        ("explorer.exe", 0.06),
        ("svchost.exe", 0.04),
        ("winlogon.exe", 0.02),
        ("csrss.exe", 0.02),
        ("taskhost.exe", 0.04),
        ("dwm.exe", 0.06),
        ("chrome.exe", 0.18),
        ("notepad.exe", 0.01),
    ]
    _LEGIT_MEM_WEIGHTS = [
        ("explorer.exe", 45),
        ("svchost.exe", 28),
        ("winlogon.exe", 14),
        ("csrss.exe", 10),
        ("taskhost.exe", 22),
        ("dwm.exe", 48),
        ("chrome.exe", 200),
        ("notepad.exe", 8),
    ]

    def _generate_processes(self):
        # Базовые легитимные процессы с весами (имя, доля CPU, вес памяти)
        name_to_mem = dict(self._LEGIT_MEM_WEIGHTS)
        legit = []
        for name, cpu_w in self._LEGIT_CPU_WEIGHTS:
            legit.append({
                "name": name,
                "cpu": 0,
                "memory": name_to_mem[name],
                "user": "User" if name == "chrome.exe" or name == "notepad.exe" else "SYSTEM",
                "suspicious": False,
                "_cpu_weight": cpu_w,
                "_mem_weight": name_to_mem[name],
            })
        
        if self.current_day == 3:
            if self.threat_resolved_for_day:
                # После устранения logonhelper нагрузка перераспределена на остальные
                self._apply_distribution(legit, self._TOTAL_CPU, self._TOTAL_MEMORY_MB)
                self.threat_detected = False
            else:
                # Доля легитимных ~35% CPU и ~380 MB — остальное забирает logonhelper (подозрительно много)
                legit_cpu_share = 35
                legit_mem_share = 380
                self._apply_distribution(legit, legit_cpu_share, legit_mem_share)
                malicious_process = {
                    "name": "logonhelper.exe",
                    "cpu": self._TOTAL_CPU - legit_cpu_share,
                    "memory": self._TOTAL_MEMORY_MB - legit_mem_share,
                    "user": "SYSTEM",
                    "suspicious": True,
                }
                legit.append(malicious_process)
                self.threat_detected = True
        elif self.current_day >= 4:
            # После выполнения задания дня 3 logonhelper.exe удалён до конца игры
            self._apply_distribution(legit, self._TOTAL_CPU, self._TOTAL_MEMORY_MB)
            self.threat_detected = False
        else:
            # Дни 1–2: logonhelper — обычный процесс
            legit_cpu = self._TOTAL_CPU - 2
            legit_mem = self._TOTAL_MEMORY_MB - 12
            self._apply_distribution(legit, legit_cpu, legit_mem)
            legit.append({
                "name": "logonhelper.exe",
                "cpu": 2,
                "memory": 12,
                "user": "SYSTEM",
                "suspicious": False,
            })
            self.threat_detected = False

        random.shuffle(legit)
        return legit

    def _apply_distribution(self, processes, total_cpu, total_mem):
        """Распределяет total_cpu и total_mem между процессами по весам (только у тех, у кого есть _cpu_weight/_mem_weight)."""
        has_weights = [p for p in processes if "_cpu_weight" in p]
        if not has_weights:
            return
        sum_cpu_w = sum(p["_cpu_weight"] for p in has_weights)
        sum_mem_w = sum(p["_mem_weight"] for p in has_weights)
        for p in has_weights:
            p["cpu"] = max(1, round((p["_cpu_weight"] / sum_cpu_w) * total_cpu))
            p["memory"] = max(5, round((p["_mem_weight"] / sum_mem_w) * total_mem))

    def _normalize_totals(self):
        """Подправляет значения процессов так, чтобы сумма CPU и память были константами (день 3)."""
        if self.current_day != 3 or not self.processes:
            return
        total_cpu = sum(p["cpu"] for p in self.processes)
        total_mem = sum(p["memory"] for p in self.processes)
        if total_cpu <= 0 or total_mem <= 0:
            return
        for p in self.processes:
            p["cpu"] = max(1, round(p["cpu"] * self._TOTAL_CPU / total_cpu))
            p["memory"] = max(5, round(p["memory"] * self._TOTAL_MEMORY_MB / total_mem))
        # Исправление округления: подгоним последний процесс под точную сумму
        total_cpu = sum(p["cpu"] for p in self.processes)
        total_mem = sum(p["memory"] for p in self.processes)
        if self.processes:
            self.processes[-1]["cpu"] += self._TOTAL_CPU - total_cpu
            self.processes[-1]["memory"] += self._TOTAL_MEMORY_MB - total_mem
            self.processes[-1]["cpu"] = max(1, self.processes[-1]["cpu"])
            self.processes[-1]["memory"] = max(5, self.processes[-1]["memory"])

    def close_manager(self):
        # Для дня 3 засчитываем угрозу только если расследование реально завершено успешно
        if self.current_day == 3:
            self.on_complete(self.threat_resolved_by_investigation)
        else:
            self.on_complete(self.threat_detected)

    def handle_event(self, event):
        if self.show_investigation and self.investigation_minigame:
            result = self.investigation_minigame.handle_event(event)
            if result:
                return True
        
        if self.close_button.handle_event(event):
            return True
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.show_investigation:
                for i, process in enumerate(self.processes):
                    process_rect = pygame.Rect(50, 100 + i * 25, 600, 20)
                    if process_rect.collidepoint(event.pos):
                        self.selected_process = process
                        if process["suspicious"] and not self.threat_detected and self.current_day == 3 and not self.threat_resolved_for_day:
                            self.threat_detected = True
                            self.start_investigation()
                        return True
        return False

    def start_investigation(self):
        from ..scenes.process_injection_minigame import ProcessInjectionMinigame
        
        def on_investigation_complete(success, score=None):
            self.show_investigation = False
            self.investigation_minigame = None
            if success:
                self.threat_resolved_by_investigation = True
                self.close_manager()
        
        self.investigation_minigame = ProcessInjectionMinigame(
            self.screen_width, self.screen_height, 
            on_investigation_complete
        )
        self.show_investigation = True

    def update(self):
        if self.show_investigation and self.investigation_minigame:
            self.investigation_minigame.update()
            return
        
        self.close_button.update()
        
        # Обновляем нагрузку раз в интервал (по времени), а не каждый кадр — выглядит реалистично
        now = pygame.time.get_ticks()
        if now - self._last_stats_update < self._STATS_UPDATE_INTERVAL_MS:
            return
        self._last_stats_update = now
        
        if self.current_day == 3:
            # Колебания только у легитимных; logonhelper остаётся стабильно с высокой нагрузкой (остаток от 100% / 700 MB)
            legit = [p for p in self.processes if "_cpu_weight" in p]
            suspicious_list = [p for p in self.processes if p.get("suspicious")]
            for p in legit:
                p["cpu"] = max(1, p["cpu"] + random.randint(-1, 1))
                p["memory"] = max(5, p["memory"] + random.randint(-2, 2))
            # Пересчитываем долю легитимных и даём остаток logonhelper — у него нагрузка постоянно высокая
            total_legit_cpu = sum(p["cpu"] for p in legit)
            total_legit_mem = sum(p["memory"] for p in legit)
            if suspicious_list:
                s = suspicious_list[0]
                s["cpu"] = max(1, self._TOTAL_CPU - total_legit_cpu)
                s["memory"] = max(5, self._TOTAL_MEMORY_MB - total_legit_mem)
            else:
                self._normalize_totals()
        else:
            for process in self.processes:
                if not process.get("suspicious"):
                    process["cpu"] = max(0, process["cpu"] + random.randint(-1, 1))
                    process["memory"] = max(5, process["memory"] + random.randint(-2, 2))

    def draw(self, screen):
        if self.show_investigation and self.investigation_minigame:
            self.investigation_minigame.draw(screen)
            return
        
        screen.fill((30, 30, 30))
        
        title = self.font_large.render("Диспетчер задач Windows", True, (255, 255, 255))
        screen.blit(title, (self.screen_width//2 - title.get_width()//2, 20))
        
        headers = ["Имя процесса", "ЦП", "Память", "Пользователь"]
        x_positions = [50, 300, 380, 480]
        
        for i, header in enumerate(headers):
            header_text = self.font_medium.render(header, True, (200, 200, 100))
            screen.blit(header_text, (x_positions[i], 70))
        
        for i, process in enumerate(self.processes):
            y_pos = 100 + i * 25
            
            if process == self.selected_process:
                pygame.draw.rect(screen, (60, 60, 80), (45, y_pos, 610, 20))
            
            # Все процессы одним цветом; подозрительность видна по высокой нагрузке, не по красному
            screen.blit(self.font_small.render(process["name"], True, (255, 255, 255)), (x_positions[0], y_pos))
            screen.blit(self.font_small.render(f"{process['cpu']}%", True, (255, 255, 255)), (x_positions[1], y_pos))
            screen.blit(self.font_small.render(f"{process['memory']} MB", True, (255, 255, 255)), (x_positions[2], y_pos))
            screen.blit(self.font_small.render(process["user"], True, (255, 255, 255)), (x_positions[3], y_pos))
        
        self.close_button.draw(screen)
        
        if self.current_day == 3:
            if self.threat_resolved_for_day:
                instruction = self.font_small.render("Мониторинг процессов. Расследование по этому дню завершено.", True, (100, 255, 100))
            elif self.threat_detected and not self.show_investigation:
                instruction = self.font_small.render("Подозрительный процесс выбран. Запустите расследование.", True, (255, 100, 100))
            else:
                instruction = self.font_small.render("Найдите процесс с аномально высоким CPU и памятью — выберите его для расследования", True, (255, 255, 100))
        else:
            instruction = self.font_small.render("Мониторинг системных процессов - все процессы в норме", True, (100, 255, 100))
        
        screen.blit(instruction, (self.screen_width//2 - instruction.get_width()//2, self.screen_height - 100))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
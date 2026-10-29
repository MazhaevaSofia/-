# [file name]: icon_generator.py
# [file content begin]
import pygame
import numpy as np
import math
import random  # Добавить эту строку

class IconGenerator:
    def __init__(self):
        self.colors = {
            'computer': (51, 153, 255),
            'antivirus': (76, 175, 80),
            'email': (244, 67, 54),
            'documents': (255, 193, 7),
            'recycle': (158, 158, 158),
            'settings': (156, 39, 176),
            'internet': (33, 150, 243),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'dark_blue': (0, 0, 139),
            'siem': (70, 130, 180),  # Steel blue для SIEM
            'task_manager': (60, 179, 113),  # Цвет для диспетчера задач
            'traffic_analyzer': (139, 0, 139)  # Темно-фиолетовый
        }
    
    def generate_icon(self, icon_type, size=64):
        """Генерация иконки указанного типа"""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        if icon_type == "my_computer":
            self._draw_my_computer(surface, size)
        elif icon_type == "antivirus":
            self._draw_antivirus(surface, size)
        elif icon_type == "email":
            self._draw_email(surface, size)
        elif icon_type == "documents":
            self._draw_documents(surface, size)
        elif icon_type == "recycle_bin":
            self._draw_recycle_bin(surface, size)
        elif icon_type == "settings":
            self._draw_settings(surface, size)
        elif icon_type == "internet":
            self._draw_internet(surface, size)
        elif icon_type == "siem_system":
            self._draw_siem_system(surface, size)
        elif icon_type == "task_manager":  # Добавить эту ветку
            self._draw_task_manager(surface, size)
        elif icon_type == "traffic_analyzer":
            self._draw_traffic_analyzer(surface, size)

        
        return surface
    
    def _draw_my_computer(self, surface, size):
        color = self.colors['computer']
        # Корпус
        pygame.draw.rect(surface, self.colors['white'], (8, 8, size-16, size-24))
        pygame.draw.rect(surface, color, (12, 12, size-24, size-32))
        
        # Экран
        pygame.draw.rect(surface, self.colors['black'], (16, 20, size-32, size-48))
        pygame.draw.rect(surface, self.colors['dark_blue'], (18, 22, size-36, size-52))
        
        # Кнопка
        pygame.draw.circle(surface, color, (size//2, size-10), 4)
    
    def _draw_antivirus(self, surface, size):
        color = self.colors['antivirus']
        center = (size//2, size//2)
        
        # Щит
        pygame.draw.circle(surface, self.colors['white'], center, size//2 - 8)
        pygame.draw.circle(surface, color, center, size//2 - 12)
        
        # Галочка
        points = [
            (center[0] - 8, center[1]),
            (center[0] - 4, center[1] + 4),
            (center[0] + 8, center[1] - 8)
        ]
        pygame.draw.lines(surface, self.colors['white'], False, points, 3)
        
        # Вирус (красный крестик)
        pygame.draw.rect(surface, (255, 0, 0), (center[0] + 10, center[1] + 10, 6, 6))
    
    def _draw_email(self, surface, size):
        color = self.colors['email']
        # Конверт
        pygame.draw.rect(surface, self.colors['white'], (8, 16, size-16, size-24))
        pygame.draw.rect(surface, color, (12, 20, size-24, size-32))
        
        # Клапан конверта
        points = [
            (12, 20),
            (size//2, 32),
            (size-12, 20)
        ]
        pygame.draw.polygon(surface, self.colors['white'], points)
        
        # Линии письма
        pygame.draw.rect(surface, self.colors['white'], (20, 32, size-40, 3))
        pygame.draw.rect(surface, self.colors['white'], (20, 40, size-48, 3))
        pygame.draw.rect(surface, self.colors['white'], (20, 48, size-44, 3))
    
    def _draw_documents(self, surface, size):
        color = self.colors['documents']
        # Папка
        pygame.draw.rect(surface, self.colors['white'], (8, 8, size-16, size-16))
        pygame.draw.rect(surface, color, (12, 12, size-24, size-20))
        
        # Листы бумаги
        for i in range(4):
            y_pos = 20 + i * 8
            pygame.draw.rect(surface, self.colors['white'], (16, y_pos, size-32, 4))
        
        # Вкладка папки
        pygame.draw.rect(surface, (255, 165, 0), (8, 8, size-16, 8))
    
    def _draw_recycle_bin(self, surface, size):
        color = self.colors['recycle']
        # Корзина
        pygame.draw.rect(surface, self.colors['white'], (12, 12, size-24, size-24))
        pygame.draw.rect(surface, color, (16, 16, size-32, size-32))
        
        # Отверстие
        pygame.draw.rect(surface, self.colors['black'], (20, 12, size-40, 6))
        
        # Бумажки
        pygame.draw.rect(surface, self.colors['white'], (8, 24, 8, 6))
        pygame.draw.rect(surface, self.colors['white'], (size-16, 28, 8, 6))
        pygame.draw.rect(surface, self.colors['white'], (12, 32, 10, 4))
    
    def _draw_settings(self, surface, size):
        color = self.colors['settings']
        center = (size//2, size//2)
        
        # Шестеренка
        pygame.draw.circle(surface, self.colors['white'], center, size//2 - 8)
        pygame.draw.circle(surface, color, center, size//2 - 12)
        pygame.draw.circle(surface, self.colors['white'], center, size//4)
        
        # Зубцы шестеренки
        for i in range(8):
            angle = i * 45
            rad = np.radians(angle)
            x1 = center[0] + (size//2 - 12) * np.cos(rad)
            y1 = center[1] + (size//2 - 12) * np.sin(rad)
            x2 = center[0] + (size//2 - 4) * np.cos(rad)
            y2 = center[1] + (size//2 - 4) * np.sin(rad)
            
            pygame.draw.line(surface, self.colors['white'], (x1, y1), (x2, y2), 4)
    
    def _draw_internet(self, surface, size):
        """Рисуем иконку интернета (глобус)"""
        color = self.colors['internet']
        center = (size//2, size//2)
        
        # Глобус
        pygame.draw.circle(surface, color, center, size//2 - 8)
        pygame.draw.circle(surface, self.colors['white'], center, size//2 - 10)
        
        # Меридианы
        for i in range(4):
            angle = i * 45
            rad = np.radians(angle)
            x1 = center[0] + (size//2 - 12) * np.cos(rad)
            y1 = center[1] + (size//2 - 12) * np.sin(rad)
            x2 = center[0] + (size//2 - 4) * np.cos(rad)
            y2 = center[1] + (size//2 - 4) * np.sin(rad)
            
            pygame.draw.line(surface, color, (x1, y1), (x2, y2), 2)
        
        # Параллели
        for i in range(2):
            y_offset = (i - 0.5) * 8
            pygame.draw.ellipse(surface, color, (center[0]-12, center[1]+y_offset-2, 24, 4), 2)
    
    def _draw_siem_system(self, surface, size):
        """Рисуем иконку SIEM системы"""
        color = self.colors['siem']
        
        # Основной прямоугольник (монитор)
        pygame.draw.rect(surface, self.colors['white'], (8, 8, size-16, size-16))
        pygame.draw.rect(surface, color, (12, 12, size-24, size-24))
        
        # График активности (волны)
        points = []
        for x in range(16, size-16, 3):
            y = size//2 + math.sin((x-16)/8) * 8
            points.append((x, y))
        
        if len(points) > 1:
            pygame.draw.lines(surface, (255, 255, 0), False, points, 2)
        
        # Точки данных
        for i in range(3):
            x = 20 + i * 15
            y = size - 20
            pygame.draw.circle(surface, (255, 100, 100), (x, y), 3)
        
        # Индикатор тревоги
        pygame.draw.circle(surface, (255, 0, 0), (size-12, 12), 4)

    def _draw_task_manager(self, surface, size):
        """Рисуем иконку диспетчера задач"""
        color = self.colors['task_manager']
        
        # Основной прямоугольник
        pygame.draw.rect(surface, self.colors['white'], (8, 8, size-16, size-16))
        pygame.draw.rect(surface, color, (12, 12, size-24, size-24))
        
        # Графики процессов
        for i in range(4):
            height = random.randint(10, 20)
            pygame.draw.rect(surface, self.colors['white'], 
                            (20 + i*12, size-20-height, 8, height))

    def _draw_traffic_analyzer(self, surface, size):
        """Рисуем иконку сетевого анализатора"""
        color = self.colors['traffic_analyzer']
        
        # Основной прямоугольник
        pygame.draw.rect(surface, self.colors['white'], (8, 8, size-16, size-16))
        pygame.draw.rect(surface, color, (12, 12, size-24, size-24))
        
        # Сетевые соединения
        for i in range(3):
            start_x = 16 + i * 8
            end_x = size - 16
            start_y = 20 + i * 12
            end_y = size - 20
            
            pygame.draw.line(surface, self.colors['white'], (start_x, start_y), (end_x, end_y), 2)
# [file content end]

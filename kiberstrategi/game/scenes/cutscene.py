import pygame
from ..ui.button import Button
from ..data.game_data import CUTSCENE_DATA

class Cutscene:
    def __init__(self, screen_width, screen_height, on_complete_callback, scene_id=0):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        self.scene_id = scene_id
        
        # Загрузка данных из CUTSCENE_DATA или значения по умолчанию
        data = CUTSCENE_DATA.get(scene_id, CUTSCENE_DATA.get(0, {}))
        self.title = data.get("title", "Киберзащитник")
        self.subtitle = data.get("subtitle", "Спокойное утро")
        self.description = data.get("description", [])
        button_text = data.get("button_text", "Начать рабочий день")
        self.instruction_text = data.get("instruction", "Нажмите кнопку чтобы начать рабочий день")
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        
        # Кнопка продолжения
        button_width, button_height = 220, 50
        button_x = (screen_width - button_width) // 2
        button_y = screen_height - 100
        self.continue_button = Button(
            button_x, button_y, button_width, button_height,
            button_text, (76, 175, 80), self.on_complete
        )
        
        # Таймер для анимации текста; текст и кнопка появляются по строкам
        self.text_timer = 0
        self.current_line = 0
        self.show_button = False
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.show_button:
            self.continue_button.handle_event(event)
    
    def update(self):
        # Анимация появления текста
        self.text_timer += 1
        if self.text_timer > 45:
            if self.current_line < len(self.description):
                self.current_line += 1
                self.text_timer = 0
            
            if self.current_line >= len(self.description):
                self.show_button = True
    
    def draw(self, screen):
        # Фон
        screen.fill((30, 60, 90))
        
        # Заголовок
        title_surface = self.font_large.render(self.title, True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(self.screen_width//2, 80))
        screen.blit(title_surface, title_rect)
        
        # Подзаголовок
        subtitle_surface = self.font_medium.render(self.subtitle, True, (200, 220, 255))
        subtitle_rect = subtitle_surface.get_rect(center=(self.screen_width//2, 140))
        screen.blit(subtitle_surface, subtitle_rect)
        
        # Описание (появляется постепенно)
        for i, line in enumerate(self.description[:self.current_line]):
            color = (255, 255, 255)
            text_surface = self.font_small.render(line, True, color)
            text_rect = text_surface.get_rect(center=(self.screen_width//2, 200 + i * 30))
            screen.blit(text_surface, text_rect)
        
        # Кнопка продолжения
        if self.show_button:
            self.continue_button.draw(screen)
            instruction_font = pygame.font.Font(None, 20)
            instruction = instruction_font.render(self.instruction_text, True, (200, 200, 255))
            instruction_rect = instruction.get_rect(center=(self.screen_width//2, self.screen_height - 40))
            screen.blit(instruction, instruction_rect)
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        button_width, button_height = 220, 50
        self.continue_button.rect.x = (w - button_width) // 2
        self.continue_button.rect.y = h - 100

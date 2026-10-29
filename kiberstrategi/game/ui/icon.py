import pygame

class DesktopIcon:
    def __init__(self, x, y, image, name, icon_type, click_callback):
        self.rect = pygame.Rect(x, y, 64, 80)
        self.image = image
        self.name = name
        self.icon_type = icon_type
        self.click_callback = click_callback
        self.font = pygame.font.Font(None, 16)
        self.selected = False
        self.click_timer = 0
        self.last_click_time = 0
        self.hovered = False
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                current_time = pygame.time.get_ticks()
                
                if current_time - self.last_click_time < 300:
                    self.click_callback(self.icon_type, self.name)
                    self.selected = False
                else:
                    self.selected = True
                
                self.last_click_time = current_time
                return True
        
        elif event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            
        return False
    
    def update(self):
        if self.selected:
            self.click_timer += 1
            if self.click_timer > 180:
                self.selected = False
                self.click_timer = 0
    
    def draw(self, screen):
        if self.selected or self.hovered:
            highlight_color = (255, 255, 100) if self.selected else (200, 200, 255, 100)
            highlight_rect = pygame.Rect(
                self.rect.x - 2, self.rect.y - 2,
                self.rect.width + 4, self.rect.height + 4
            )
            pygame.draw.rect(screen, highlight_color, highlight_rect, 2, border_radius=3)
        
        screen.blit(self.image, (self.rect.x, self.rect.y))
        
        words = self.name.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_surface = self.font.render(test_line, True, (255, 255, 255))
            if test_surface.get_width() <= 70:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        for i, line in enumerate(lines[:2]):
            text_surface = self.font.render(line, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(self.rect.x + 32, self.rect.y + 72 + i * 15))
            screen.blit(text_surface, text_rect)

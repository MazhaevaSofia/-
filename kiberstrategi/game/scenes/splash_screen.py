import pygame
import os
from ..ui import theme

class SplashScreen:
    def __init__(self, screen_width, screen_height, on_complete_callback):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        
        # Загрузка картинки
        self.image = None
        self._original_image = None
        try:
            # Пробуем разные пути к картинке
            possible_paths = [
                "main_image.jpg",
                "./main_image.jpg",
                os.path.join(os.path.dirname(__file__), "..", "..", "main_image.jpg")
            ]
            
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        self._original_image = pygame.image.load(path)
                        self.image = pygame.transform.scale(self._original_image, (screen_width, screen_height))
                        print(f"Картинка загружена: {path}")
                        break
                except:
                    continue
            else:
                self._original_image = None
                    
            if not self.image:
                print("Не удалось загрузить картинку заставки")
                self._original_image = None
                
        except Exception as e:
            print(f"Ошибка загрузки картинки: {e}")
            self.image = None
            self._original_image = None
        
        # Таймер
        self.start_time = pygame.time.get_ticks()
        self.display_time = 3000  # 3 секунды
        self.can_skip = False
        self.skip_timer = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            if self.can_skip:
                self.on_complete()
        return False

    def update(self):
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.start_time
        
        # Разрешаем пропуск через 1 секунду
        if elapsed_time > 1000:
            self.can_skip = True
        
        # Автоматический переход через 3 секунды
        if elapsed_time > self.display_time:
            self.on_complete()
        
        # Мигание подсказки
        self.skip_timer += 1
        if self.skip_timer > 60:
            self.skip_timer = 0

    def draw(self, screen):
        screen.fill(theme.BG)

        if self.image:
            screen.blit(self.image, (0, 0))
        else:
            title = theme.font(theme.FONT_TITLE, bold=True).render("КИБЕРСТРАТЕГИЯ", True, theme.TEXT_PRIMARY)
            screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, self.screen_height // 2 - 60))

            subtitle = theme.font(theme.FONT_LG).render("Битва за данные", True, theme.ACCENT)
            screen.blit(subtitle, (self.screen_width // 2 - subtitle.get_width() // 2, self.screen_height // 2 + 4))

        # Подсказка для пропуска — мягкая плашка внизу, плавно проявляется/гаснет
        if self.can_skip:
            phase = self.skip_timer / 60.0  # 0..1 за цикл мигания
            alpha = int(120 + 100 * abs(0.5 - phase) * 2)
            text_surf = theme.font(theme.FONT_SM).render("Нажмите любую клавишу, чтобы продолжить", True, theme.TEXT_PRIMARY)
            pill = pygame.Surface((text_surf.get_width() + 32, text_surf.get_height() + 16), pygame.SRCALPHA)
            pygame.draw.rect(pill, (*theme.SURFACE, min(200, alpha)), pill.get_rect(), border_radius=pill.get_height() // 2)
            pill.blit(text_surf, (16, 8))
            screen.blit(pill, (self.screen_width // 2 - pill.get_width() // 2, self.screen_height - 70))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if getattr(self, '_original_image', None):
            self.image = pygame.transform.scale(self._original_image, (w, h))


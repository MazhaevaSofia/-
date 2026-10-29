import pygame
import os

class ImageScene:
    def __init__(self, screen_width, screen_height, image_path, display_time, on_complete_callback):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.image_path = image_path
        self.display_time = display_time
        self.on_complete = on_complete_callback
        
        # Загрузка картинки
        self.image = None
        self._original_image = None
        try:
            # Пробуем разные пути к картинке
            possible_paths = [
                image_path,
                f"./{image_path}",
                os.path.join(os.path.dirname(__file__), "..", "..", image_path)
            ]
            
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        self._original_image = pygame.image.load(path)
                        img_width, img_height = self._original_image.get_size()
                        scale_ratio = min(screen_width / img_width, screen_height / img_height)
                        new_width = int(img_width * scale_ratio)
                        new_height = int(img_height * scale_ratio)
                        self.image = pygame.transform.scale(self._original_image, (new_width, new_height))
                        print(f"Картинка загружена: {path}")
                        break
                except:
                    continue
            else:
                self._original_image = None
                    
            if not self.image:
                print(f"Не удалось загрузить картинку: {image_path}")
                self._original_image = None
                
        except Exception as e:
            print(f"Ошибка загрузки картинки {image_path}: {e}")
            self.image = None
            self._original_image = None
        
        # Анимация
        self.alpha = 0
        self.fade_in = True
        self.fade_out = False
        self.fade_speed = 8
        
        # Таймеры
        self.start_time = pygame.time.get_ticks()
        self.display_start_time = 0
        self.can_skip = False
        self.skip_timer = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            if self.can_skip and self.on_complete:
                self.on_complete()
        return False

    def update(self):
        current_time = pygame.time.get_ticks()
        
        # Анимация появления
        if self.fade_in:
            self.alpha += self.fade_speed
            if self.alpha >= 255:
                self.alpha = 255
                self.fade_in = False
                self.display_start_time = current_time
                self.can_skip = True
        
        # Автоматическое исчезновение через указанное время после полного появления
        elif self.display_time > 0 and not self.fade_out and current_time - self.display_start_time > self.display_time:
            self.fade_out = True
        
        # Анимация исчезновения
        if self.fade_out:
            self.alpha -= self.fade_speed
            if self.alpha <= 0:
                self.alpha = 0
                if self.on_complete:
                    self.on_complete()
        
        # Мигание подсказки
        self.skip_timer += 1
        if self.skip_timer > 60:
            self.skip_timer = 0

    def draw(self, screen):
        # Черный фон
        screen.fill((0, 0, 0))
        
        if self.image:
            # Устанавливаем альфа-канал для изображения
            image_copy = self.image.copy()
            image_copy.set_alpha(self.alpha)
            
            # Центрируем изображение
            img_rect = image_copy.get_rect()
            img_rect.center = (self.screen_width // 2, self.screen_height // 2)
            screen.blit(image_copy, img_rect)
        else:
            # Если картинка не загрузилась, показываем сообщение
            font = pygame.font.Font(None, 36)
            error_text = font.render(f"Не удалось загрузить: {self.image_path}", True, (255, 255, 255))
            error_text.set_alpha(self.alpha)
            screen.blit(error_text, (self.screen_width//2 - error_text.get_width()//2, 
                                   self.screen_height//2 - error_text.get_height()//2))
        
        # Показываем подсказку для пропуска (мигает и тоже с прозрачностью)
        if self.can_skip and self.skip_timer < 30 and not self.fade_out:
            skip_font = pygame.font.Font(None, 24)
            skip_text = skip_font.render("Нажмите любую клавишу для продолжения...", True, (255, 255, 255))
            skip_text.set_alpha(self.alpha)
            screen.blit(skip_text, (self.screen_width//2 - skip_text.get_width()//2, 
                                  self.screen_height - 50))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        if getattr(self, '_original_image', None):
            img_width, img_height = self._original_image.get_size()
            scale_ratio = min(w / img_width, h / img_height)
            new_width = int(img_width * scale_ratio)
            new_height = int(img_height * scale_ratio)
            self.image = pygame.transform.scale(self._original_image, (new_width, new_height))

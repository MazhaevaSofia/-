import pygame
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.core.game_manager import GameManager

def main():
    # Инициализация Pygame
    pygame.init()
    
    # Настройки окна (масштабируемое)
    screen_width = 1280
    screen_height = 720
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
    pygame.display.set_caption("Serious game Information Security")
    
    # Создание игрового менеджера
    game_manager = GameManager(screen_width, screen_height)
    
    # Главный игровой цикл
    clock = pygame.time.Clock()
    running = True
    
    while running:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
                game_manager.set_screen_size(screen_width, screen_height)
            game_manager.handle_event(event)
        if game_manager.quit_requested:
            running = False
        
        # Обновление игры
        game_manager.update()
        
        # Отрисовка
        screen.fill((0, 0, 0))
        game_manager.draw(screen)
        pygame.display.flip()
        
        # Ограничение FPS
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

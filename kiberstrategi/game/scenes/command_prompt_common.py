# Общая логика для экранов с вводом команд: фон, кнопка «Назад»
import pygame
from ..ui.button import Button


def get_blurred_background(screen_width, screen_height):
    """Возвращает чёрный фон для окна ввода команд."""
    surface = pygame.Surface((screen_width, screen_height))
    surface.fill((0, 0, 0))
    return surface


def create_back_button(screen_width, screen_height, callback):
    """Кнопка «Назад» для закрытия окна ввода команд."""
    return Button(
        screen_width - 130, 20,
        110, 36,
        "Назад", (120, 120, 120), callback
    )

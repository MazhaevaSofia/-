import pygame

from . import theme
from ..core import sound_manager


def _shade(color, amount):
    """Осветляет (amount > 0) или затемняет (amount < 0) цвет, оставаясь в [0, 255]."""
    return tuple(max(0, min(255, c + amount)) for c in color)


class Button:
    def __init__(self, x, y, width, height, text, color, callback, font=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.callback = callback
        self.font = font if font is not None else theme.font(theme.FONT_MD)
        self.hovered = False
        self.pressed = False

    def handle_event(self, event, disabled=False):
        if disabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                sound_manager.play("click")
                self.callback()
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.pressed = False
        return False

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)
        if not pygame.mouse.get_pressed()[0]:
            self.pressed = False

    def draw(self, screen, disabled=False):
        if disabled:
            fill = theme.SURFACE_ALT
            border = theme.BORDER_SOFT
            text_color = theme.TEXT_MUTED
        else:
            fill = self.color
            if self.pressed:
                fill = _shade(fill, -25)
            elif self.hovered:
                fill = _shade(fill, 22)
            border = _shade(self.color, 45) if (self.hovered and not self.pressed) else _shade(self.color, -35)
            text_color = (255, 255, 255)

            if not self.pressed:
                shadow_rect = self.rect.move(0, 3 if not self.hovered else 4)
                shadow = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(shadow, (0, 0, 0, 60), shadow.get_rect(), border_radius=theme.RADIUS_MD)
                screen.blit(shadow, shadow_rect.topleft)

        draw_rect = self.rect.move(0, 1) if self.pressed else self.rect
        pygame.draw.rect(screen, fill, draw_rect, border_radius=theme.RADIUS_MD)
        pygame.draw.rect(screen, border, draw_rect, 1, border_radius=theme.RADIUS_MD)

        padding = 14
        max_w = max(1, draw_rect.width - padding)
        font = self.font
        text_surface = font.render(self.text, True, text_color)
        if text_surface.get_width() > max_w:
            for size in (theme.FONT_MD, theme.FONT_SM, theme.FONT_XS, 14):
                font = theme.font(size)
                text_surface = font.render(self.text, True, text_color)
                if text_surface.get_width() <= max_w:
                    break
        text_rect = text_surface.get_rect(center=draw_rect.center)
        screen.blit(text_surface, text_rect)

# Босс-уровень «Операция «Чёрный лёд»»: шесть подряд идущих фаз атаки без подсказок.
# В каждой фазе игрок отмечает улики в журнале, выбирает действие и получает разбор.
import functools
import math
import random

import pygame

from ..core import achievements, sound_manager
from ..core.boss_fight import (
    BossFight, PHASE_TIME_LIMIT, PHASE_MAX_POINTS, INTEGRITY_START,
)
from ..data import boss_incident as data
from ..ui import theme
from ..ui.button import Button
from ..ui.network_map import draw_network_map
from ..ui.widgets import draw_ring, draw_bar, draw_hexagon, wrap_lines

GUTTER = 16
HUD_HEIGHT = 84
BOTTOM_HEIGHT = 64
MAP_HEIGHT = 232
MIN_MAP_HEIGHT = 170
LOG_MIN_HEIGHT = 290
REVEAL_LOCK_MS = 300
FINAL_ANIM_FRAMES = 55
TYPE_SPEED = 0.8

QUALITY_COLOR = {2: theme.SUCCESS, 1: theme.WARNING, 0: theme.DANGER}
QUALITY_TITLE = {2: "Отличное решение", 1: "Решение неполное", 0: "Ошибка"}
TAG_COLOR = {"success": theme.SUCCESS, "warning": theme.WARNING, "danger": theme.DANGER}
RED_BUTTON = (150, 45, 55)
GREEN_BUTTON = (25, 120, 90)
SRC_COLORS = {
    "MAIL": (56, 189, 248), "PROXY": (56, 189, 248), "EDR": (251, 191, 36), "SYSMON": (251, 191, 36),
    "FW": (167, 139, 250), "FLOW": (167, 139, 250), "DNS": (52, 211, 153), "STAT": (52, 211, 153),
    "SSH": (244, 114, 182), "SUDO": (244, 114, 182),
}


@functools.lru_cache(maxsize=None)
def mono(size, bold=False):
    path = pygame.font.match_font("menlo,consolas,couriernew,dejavusansmono,monospace")
    f = pygame.font.Font(path, size)
    f.set_bold(bold)
    return f


def _wrap_chars(text, font, width):
    """Перенос по словам, а слишком длинное слово рубится по символам."""
    lines, current = [], ""
    for word in text.split(" "):
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = ""
        while font.size(word)[0] > width and len(word) > 1:
            cut = len(word)
            while cut > 1 and font.size(word[:cut])[0] > width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def _text_block(screen, text, font, color, x, y, width, gap=3):
    for line in wrap_lines(text, font, width):
        screen.blit(font.render(line, True, color), (x, y))
        y += font.get_linesize() + gap
    return y


def _measure(text, font, width, gap=3):
    return len(wrap_lines(text, font, width)) * (font.get_linesize() + gap)


def _glitch_text(screen, text, font, center, color, frame, duration=28):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center)
    if frame < duration:
        amp = int(4 * (1 - frame / duration)) + 1
        jitter = random.Random(frame).randint(-amp, amp)
        for dx, tint in ((-amp, (255, 60, 80)), (amp, (60, 220, 255))):
            layer = font.render(text, True, tint)
            layer.set_alpha(150)
            screen.blit(layer, rect.move(dx + jitter, 0))
    screen.blit(surf, rect)


class BossLevelScene:
    def __init__(self, screen_width, screen_height, save_manager, on_back,
                 completed_levels=None, rng=None, time_fn=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.save_manager = save_manager
        self.on_back = on_back
        self.completed_levels = completed_levels if completed_levels is not None else set()
        self._rng = rng or random.Random()
        self._now = time_fn or pygame.time.get_ticks

        self.state = "intro"
        self.fight = None
        self.result = None
        self.phase_started = 0
        self.reveal_since = 0
        self.type_frame = 0
        self.frame = 0
        self.shake = 0
        self.flash = None
        self._last_tick = None
        self.detail_index = 0
        self.new_best = False
        self.new_achievements = []
        self.final_frame = 0
        self._log_rows = []
        self.log_scroll = 0
        self._log_max_scroll = 0
        self.reveal_scroll = 0
        self._reveal_max_scroll = 0
        self._option_rects = []
        self._final_rows = []
        self._bg = None
        self._bg_size = None
        self._canvas = None

        big = theme.font(theme.FONT_MD, bold=True)
        self.confirm_button = Button(0, 0, 320, 46, "Подтвердить решение", GREEN_BUTTON, self.confirm, font=big)
        self.next_button = Button(0, 0, 320, 46, "Дальше", theme.ACCENT_DIM, self.next_step, font=big)
        self.exit_button = Button(0, 0, 110, 34, "Выйти", theme.SURFACE_ALT, self.to_intro)
        self.start_button = Button(0, 0, 340, 58, "Начать операцию", RED_BUTTON, self.start_fight,
                                   font=theme.font(theme.FONT_LG, bold=True))
        self.back_button = Button(0, 0, 120, 35, "Назад", theme.SURFACE_ALT, self.on_back)
        self.retry_button = Button(0, 0, 154, 46, "Ещё раз", RED_BUTTON, self.start_fight, font=big)
        self.menu_button = Button(0, 0, 154, 46, "В меню", theme.SURFACE_ALT, self.on_back, font=big)
        self._place_buttons()

    # ------------------------------------------------------------ раскладка
    def _layout(self):
        w, h = self.screen_width, self.screen_height
        main_top = HUD_HEIGHT + 12
        main_bottom = h - BOTTOM_HEIGHT - 8
        left_w = (w - 3 * GUTTER) // 2
        right_w = w - 3 * GUTTER - left_w
        left_x = GUTTER
        right_x = left_x + left_w + GUTTER
        map_h = max(MIN_MAP_HEIGHT, min(MAP_HEIGHT, main_bottom - main_top - LOG_MIN_HEIGHT - 12))
        log = pygame.Rect(left_x, main_top, left_w, main_bottom - main_top - map_h - 12)
        net = pygame.Rect(left_x, log.bottom + 12, left_w, map_h)
        right = pygame.Rect(right_x, main_top, right_w, main_bottom - main_top)
        return log, net, right

    def _final_panel(self):
        return pygame.Rect(30, 25, self.screen_width - 60, self.screen_height - 50)

    def _place_buttons(self):
        w, h = self.screen_width, self.screen_height
        self.confirm_button.rect.topleft = (w - GUTTER - 320, h - BOTTOM_HEIGHT + 9)
        self.next_button.rect.topleft = (w - GUTTER - 320, h - BOTTOM_HEIGHT + 9)
        self.exit_button.rect.topleft = (GUTTER, h - BOTTOM_HEIGHT + 15)
        self.start_button.rect.topleft = (w // 2 - 170, h - 130)
        self.back_button.rect.topleft = (30, h - 55)
        panel = self._final_panel()
        self.retry_button.rect.topleft = (panel.x + 24, panel.bottom - 70)
        self.menu_button.rect.topleft = (panel.x + 24 + 166, panel.bottom - 70)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self._bg = None
        self._canvas = None
        self._place_buttons()

    # ------------------------------------------------------------ переходы
    def to_intro(self):
        self.state = "intro"
        self.fight = None

    def start_fight(self):
        self.fight = BossFight(data.PHASES, data.NETWORK_NODES.keys(), rng=self._rng)
        self.new_best = False
        self.new_achievements = []
        self._begin_phase_intro()

    def _begin_phase_intro(self):
        self.state = "phase_intro"
        self.type_frame = 0
        self.frame = 0
        sound_manager.play("alert")

    def _begin_playing(self):
        self.log_scroll = 0
        self.state = "playing"
        self.phase_started = self._now()
        self._last_tick = None

    def remaining(self):
        return PHASE_TIME_LIMIT - (self._now() - self.phase_started) / 1000.0

    def confirm(self):
        if self.state == "playing" and self.fight.selected is not None:
            self._submit(timed_out=False)

    def _submit(self, timed_out):
        elapsed = (self._now() - self.phase_started) / 1000.0
        self.result = self.fight.submit(elapsed, timed_out=timed_out)
        self.state = "reveal"
        self.reveal_scroll = 0
        self.reveal_since = self._now()
        quality = self.result.quality
        sound_manager.play("correct" if quality == 2 else ("achievement" if quality == 1 else "wrong"))
        if quality == 0:
            self.shake = 16
            self.flash = ((255, 60, 70), 18, 18)
        elif quality == 2:
            self.flash = ((52, 211, 153), 14, 14)

    def next_step(self):
        if self.state != "reveal" or self._now() - self.reveal_since < REVEAL_LOCK_MS:
            return
        self.fight.advance()
        if self.fight.finished:
            self._finish()
        else:
            self._begin_phase_intro()

    def _finish(self):
        fight = self.fight
        grade, _ = fight.grade
        victory = fight.outcome == "victory"
        self.new_best = self.save_manager.record_boss_attempt(fight.score, grade, victory)
        new_ids = self.save_manager.unlock_achievements(achievements.evaluate_boss(fight))
        self.new_achievements = [achievements.ACHIEVEMENTS[a]["title"] for a in new_ids]
        weak = [i for i, r in enumerate(fight.results) if r.quality < 2]
        self.detail_index = weak[0] if weak else 0
        self.final_frame = 0
        self.state = "final"
        sound_manager.play("success" if victory else ("achievement" if fight.outcome == "partial" else "wrong"))

    # ------------------------------------------------------------ события
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event.key)
        if event.type == pygame.MOUSEWHEEL and self.state in ("playing", "reveal"):
            log_area, _, right_area = self._layout()
            mouse = pygame.mouse.get_pos()
            if log_area.collidepoint(mouse):
                self.log_scroll = max(0, min(self.log_scroll - event.y * 30, self._log_max_scroll))
                return True
            if self.state == "reveal" and right_area.collidepoint(mouse):
                self.reveal_scroll = max(0, min(self.reveal_scroll - event.y * 30, self._reveal_max_scroll))
                return True
        if self.state == "intro":
            return self.start_button.handle_event(event) or self.back_button.handle_event(event)
        if self.state == "phase_intro":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._advance_phase_intro()
                return True
        elif self.state == "playing":
            return self._handle_playing_mouse(event)
        elif self.state == "reveal":
            locked = self._now() - self.reveal_since < REVEAL_LOCK_MS
            return self.next_button.handle_event(event, disabled=locked) or self.exit_button.handle_event(event)
        elif self.state == "final":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, index in self._final_rows:
                    if rect.collidepoint(event.pos):
                        self.detail_index = index
                        sound_manager.play("click")
                        return True
            return self.retry_button.handle_event(event) or self.menu_button.handle_event(event)
        return False

    def _handle_playing_mouse(self, event):
        if self.confirm_button.handle_event(event, disabled=self.fight.selected is None):
            return True
        if self.exit_button.handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            log_area = self._layout()[0]
            for rect, index in self._log_rows:
                if rect.collidepoint(event.pos) and log_area.collidepoint(event.pos):
                    self.fight.toggle_mark(index)
                    sound_manager.play("click")
                    return True
            for rect, index in self._option_rects:
                if rect.collidepoint(event.pos):
                    self.fight.select(index)
                    sound_manager.play("click")
                    return True
        return False

    def _advance_phase_intro(self):
        taunt = self.fight.current["taunt"]
        if int(self.type_frame * TYPE_SPEED) < len(taunt):
            self.type_frame = len(taunt) / TYPE_SPEED
        else:
            self._begin_playing()

    def _handle_key(self, key):
        if self.state == "intro":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_fight()
                return True
            if key == pygame.K_ESCAPE:
                self.on_back()
                return True
        elif self.state == "phase_intro":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._advance_phase_intro()
                return True
        elif self.state == "playing":
            option_keys = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)
            if key in option_keys:
                self.fight.select(option_keys.index(key))
                return True
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.confirm()
                return True
        elif self.state == "reveal":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.next_step()
                return True
        elif self.state == "final":
            if key == pygame.K_RETURN:
                self.start_fight()
                return True
            if key == pygame.K_ESCAPE:
                self.on_back()
                return True
        return False

    def update(self):
        self.frame += 1
        for button in (self.confirm_button, self.next_button, self.exit_button, self.start_button,
                       self.back_button, self.retry_button, self.menu_button):
            button.update()
        if self.state == "phase_intro":
            self.type_frame += 1
        elif self.state == "playing":
            remaining = self.remaining()
            if remaining <= 0:
                self._submit(timed_out=True)
            elif remaining <= 10:
                second = int(math.ceil(remaining))
                if second != self._last_tick:
                    self._last_tick = second
                    sound_manager.play("noise")
        elif self.state == "final" and self.final_frame < FINAL_ANIM_FRAMES:
            self.final_frame += 1
        if self.shake > 0:
            self.shake -= 1
        if self.flash:
            color, frames, total = self.flash
            self.flash = (color, frames - 1, total) if frames > 1 else None

    # ------------------------------------------------------------ отрисовка
    def _ensure_buffers(self):
        size = (self.screen_width, self.screen_height)
        if self._bg_size != size or self._bg is None:
            bg = pygame.Surface(size)
            bg.fill(theme.BG)
            grid = pygame.Surface(size, pygame.SRCALPHA)
            for x in range(0, size[0], 44):
                pygame.draw.line(grid, (255, 255, 255, 7), (x, 0), (x, size[1]))
            for y in range(0, size[1], 44):
                pygame.draw.line(grid, (255, 255, 255, 7), (0, y), (size[0], y))
            for i in range(90):
                pygame.draw.rect(grid, (248, 113, 113, max(0, 20 - i // 4)), (0, i, size[0], 1))
            bg.blit(grid, (0, 0))
            self._bg, self._bg_size = bg, size
            self._canvas = pygame.Surface(size)

    def draw(self, screen):
        self._ensure_buffers()
        canvas = self._canvas
        canvas.blit(self._bg, (0, 0))
        if self.state == "intro":
            self._draw_intro(canvas)
        elif self.state == "final":
            self._draw_final(canvas)
        else:
            self._draw_hud(canvas)
            if self.state == "phase_intro":
                self._draw_phase_intro(canvas)
            else:
                self._draw_round(canvas)
        dx = dy = 0
        if self.shake > 0:
            amp = self.shake / 2.5
            dx = int(math.sin(self.frame * 2.7) * amp)
            dy = int(math.cos(self.frame * 3.1) * amp)
            screen.fill((0, 0, 0))
        screen.blit(canvas, (dx, dy))
        if self.flash:
            color, frames, total = self.flash
            veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            veil.fill((*color, int(70 * frames / total)))
            screen.blit(veil, (0, 0))

    # ---------- HUD
    def _draw_hud(self, screen):
        fight = self.fight
        w = self.screen_width
        pygame.draw.rect(screen, theme.SURFACE, (0, 0, w, HUD_HEIGHT))
        pygame.draw.line(screen, theme.BORDER, (0, HUD_HEIGHT - 1), (w, HUD_HEIGHT - 1))
        pygame.draw.line(screen, theme.DANGER_DIM, (0, HUD_HEIGHT), (w, HUD_HEIGHT), 2)

        # Босс и его мощь
        center = (46, 42)
        pulse = (math.sin(self.frame / 14.0) + 1) / 2
        draw_hexagon(screen, center, 28, theme.DANGER_DIM)
        draw_hexagon(screen, center, 28, theme.DANGER, 2)
        pygame.draw.circle(screen, theme.DANGER, center, int(5 + 2 * pulse))
        pygame.draw.line(screen, theme.DANGER, (center[0] - 14, center[1]), (center[0] + 14, center[1]), 1)
        pygame.draw.line(screen, theme.DANGER, (center[0], center[1] - 14), (center[0], center[1] + 14), 1)
        screen.blit(theme.font(theme.FONT_LG, bold=True).render(data.BOSS_NAME, True, theme.DANGER), (88, 12))
        screen.blit(theme.font(12).render("МОЩЬ АТАКИ", True, theme.TEXT_MUTED), (88, 46))
        draw_bar(screen, pygame.Rect(88, 62, 190, 10), fight.boss_hp / 100, theme.DANGER)

        # Дорожка фаз
        for i in range(fight.total):
            cx = w // 2 + int((i - (fight.total - 1) / 2) * 78)
            rect = pygame.Rect(0, 0, 66, 26)
            rect.center = (cx, 30)
            current = i == fight.index and not fight.finished
            if i < len(fight.results):
                color = QUALITY_COLOR[fight.results[i].quality]
                pygame.draw.rect(screen, theme.SURFACE_ALT, rect, border_radius=13)
                pygame.draw.rect(screen, color, rect, 2, border_radius=13)
                fg = color
            elif current:
                pygame.draw.rect(screen, theme.ACCENT_DIM, rect, border_radius=13)
                pygame.draw.rect(screen, theme.ACCENT, rect, 2, border_radius=13)
                fg = theme.TEXT_PRIMARY
            else:
                pygame.draw.rect(screen, theme.SURFACE, rect, border_radius=13)
                pygame.draw.rect(screen, theme.BORDER, rect, 1, border_radius=13)
                fg = theme.TEXT_MUTED
            num = theme.font(theme.FONT_XS, bold=True).render(str(i + 1), True, fg)
            screen.blit(num, num.get_rect(center=rect.center))
        if not fight.finished:
            phase = fight.current
            label = theme.font(theme.FONT_XS).render(
                f"Фаза {fight.index + 1} из {fight.total} · {phase['tactic']}", True, theme.TEXT_SECONDARY)
            screen.blit(label, label.get_rect(center=(w // 2, 62)))

        # Целостность и таймер
        bar_x = w - 400
        integrity = fight.integrity
        color = theme.SUCCESS if integrity > 60 else (theme.WARNING if integrity > 30 else theme.DANGER)
        screen.blit(theme.font(12).render("ЦЕЛОСТНОСТЬ СЕТИ", True, theme.TEXT_MUTED), (bar_x, 20))
        draw_bar(screen, pygame.Rect(bar_x, 42, 220, 12), integrity / INTEGRITY_START, color)
        value = theme.font(theme.FONT_MD, bold=True).render(str(integrity), True, color)
        screen.blit(value, (bar_x + 232, 38))

        ring_center = (w - 52, 42)
        if self.state == "playing":
            remaining = max(0.0, self.remaining())
            fraction = remaining / PHASE_TIME_LIMIT
            ring_color = theme.SUCCESS if fraction > 0.5 else (theme.WARNING if fraction > 0.2 else theme.DANGER)
            label = f"{int(remaining) // 60}:{int(math.ceil(remaining)) % 60:02d}" if remaining >= 1 else "0:00"
            if fraction <= 0.2 and int(self.frame / 15) % 2 == 0:
                ring_color = theme.TEXT_PRIMARY
            draw_ring(screen, ring_center, 30, 6, fraction, ring_color)
            txt = theme.font(theme.FONT_SM, bold=True).render(label, True, ring_color)
        else:
            draw_ring(screen, ring_center, 30, 6, 0, theme.BORDER)
            txt = theme.font(theme.FONT_SM, bold=True).render("--", True, theme.TEXT_MUTED)
        screen.blit(txt, txt.get_rect(center=ring_center))

    # ---------- заставка фазы
    def _draw_phase_intro(self, screen):
        fight = self.fight
        phase = fight.current
        w, h = self.screen_width, self.screen_height
        veil = pygame.Surface((w, h - HUD_HEIGHT), pygame.SRCALPHA)
        veil.fill((8, 11, 18, 235))
        screen.blit(veil, (0, HUD_HEIGHT))
        cx, cy = w // 2, h // 2 + 20

        small = theme.font(theme.FONT_SM, bold=True).render(
            f"ФАЗА {fight.index + 1} ИЗ {fight.total}   ·   {phase['clock']}", True, theme.DANGER)
        screen.blit(small, small.get_rect(center=(cx, cy - 110)))
        _glitch_text(screen, phase["tactic"].upper(), theme.font(52, bold=True), (cx, cy - 55), theme.TEXT_PRIMARY, self.frame)
        title = theme.font(theme.FONT_XL).render(phase["title"], True, theme.TEXT_SECONDARY)
        screen.blit(title, title.get_rect(center=(cx, cy + 5)))
        pygame.draw.line(screen, theme.DANGER_DIM, (cx - 160, cy + 38), (cx + 160, cy + 38), 2)

        typed = phase["taunt"][:int(self.type_frame * TYPE_SPEED)]
        cursor = "_" if int(self.frame / 20) % 2 == 0 else " "
        prefix = mono(16, bold=True).render(f"{data.BOSS_NAME}> ", True, theme.DANGER)
        line = mono(16).render(typed + cursor, True, theme.TEXT_PRIMARY)
        total_w = prefix.get_width() + mono(16).size(phase["taunt"] + "_")[0]
        x = cx - total_w // 2
        screen.blit(prefix, (x, cy + 62))
        screen.blit(line, (x + prefix.get_width(), cy + 62))

        done = int(self.type_frame * TYPE_SPEED) >= len(phase["taunt"])
        hint_text = "Пробел или клик: начать фазу" if done else "Пробел или клик: пропустить"
        hint = theme.font(theme.FONT_XS).render(hint_text, True, theme.TEXT_MUTED)
        screen.blit(hint, hint.get_rect(center=(cx, cy + 130)))

    # ---------- игровой экран
    def _draw_round(self, screen):
        fight = self.fight
        log, net, right = self._layout()
        reveal = self.state == "reveal"
        self._draw_log(screen, log, reveal)
        phase = fight.current
        draw_network_map(screen, net, data.NETWORK_NODES, data.NETWORK_EDGES, fight.node_state,
                         pygame.time.get_ticks(), path=phase["nodes"]["path"], animate=not reveal)
        if reveal:
            self._draw_reveal(screen, right)
        else:
            self._draw_decision(screen, right)

        pygame.draw.rect(screen, theme.SURFACE, (0, self.screen_height - BOTTOM_HEIGHT, self.screen_width, BOTTOM_HEIGHT))
        pygame.draw.line(screen, theme.BORDER, (0, self.screen_height - BOTTOM_HEIGHT), (self.screen_width, self.screen_height - BOTTOM_HEIGHT))
        self.exit_button.draw(screen)
        hint_font = theme.font(theme.FONT_XS)
        if reveal:
            last = fight.game_over or fight.index + 1 >= fight.total
            self.next_button.text = "К итогам операции" if last else f"Дальше: фаза {fight.index + 2}"
            locked = self._now() - self.reveal_since < REVEAL_LOCK_MS
            self.next_button.draw(screen, disabled=locked)
            hint = "Пробел или Enter: дальше"
        else:
            self.confirm_button.draw(screen, disabled=fight.selected is None)
            hint = "Клик по строке журнала отмечает улику. Клавиши 1-4 выбирают решение, Enter подтверждает."
        hint_surf = hint_font.render(hint, True, theme.TEXT_MUTED)
        screen.blit(hint_surf, (GUTTER + 130, self.screen_height - BOTTOM_HEIGHT // 2 - hint_surf.get_height() // 2))

    def _draw_log(self, screen, rect, reveal):
        fight = self.fight
        phase = fight.current
        theme.draw_panel(screen, rect, radius=theme.RADIUS_LG, fill=(15, 20, 30))
        prev_clip = screen.get_clip()
        screen.set_clip(rect)

        head = theme.font(theme.FONT_SM, bold=True).render("Журнал событий", True, theme.TEXT_PRIMARY)
        screen.blit(head, (rect.x + 16, rect.y + 10))
        marked = len(fight.marks) if not reveal else len(self.result.marks)
        counter = theme.font(theme.FONT_XS).render(f"Отмечено улик: {marked}", True, theme.ACCENT)
        screen.blit(counter, (rect.right - counter.get_width() - 16, rect.y + 12))
        pygame.draw.line(screen, theme.BORDER_SOFT, (rect.x + 12, rect.y + 38), (rect.right - 12, rect.y + 38))

        font = mono(13)
        tag_font = mono(12, bold=True)
        time_w, tag_w, flag_w = 74, 66, 30
        text_w = rect.width - 24 - time_w - tag_w - flag_w
        mouse = pygame.mouse.get_pos()
        self._log_rows = []
        y = rect.y + 46 - self.log_scroll
        marks = self.result.marks if reveal else fight.marks
        for index, line in enumerate(phase["log"]):
            lines = _wrap_chars(line["text"], font, text_w)
            row_h = len(lines) * (font.get_linesize() + 1) + 10
            row = pygame.Rect(rect.x + 8, y, rect.width - 16, row_h)
            hovered = row.collidepoint(mouse) and not reveal
            is_marked = index in marks
            is_sus = line["sus"]
            fill = None
            accent = None
            if reveal:
                if is_sus and is_marked:
                    fill, accent = (18, 70, 55), theme.SUCCESS
                elif is_sus:
                    fill, accent = (80, 62, 18), theme.WARNING
                elif is_marked:
                    fill, accent = (90, 30, 34), theme.DANGER
            elif is_marked:
                fill, accent = (90, 30, 34), theme.DANGER
            elif hovered:
                fill = theme.SURFACE_ALT
            if fill:
                pygame.draw.rect(screen, fill, row, border_radius=6)
            if accent:
                pygame.draw.rect(screen, accent, (row.x, row.y, 3, row.height), border_radius=2)
            screen.blit(font.render(line["t"], True, theme.TEXT_MUTED), (row.x + 10, y + 5))
            src_color = SRC_COLORS.get(line["src"], theme.TEXT_SECONDARY)
            screen.blit(tag_font.render(line["src"], True, src_color), (row.x + 10 + time_w, y + 5))
            for j, part in enumerate(lines):
                screen.blit(font.render(part, True, theme.TEXT_PRIMARY), (row.x + 10 + time_w + tag_w, y + 5 + j * (font.get_linesize() + 1)))
            icon = (row.right - 16, row.y + 14)
            if reveal:
                if is_sus and is_marked:
                    theme.draw_check(screen, icon, size=6, color=theme.SUCCESS, width=2)
                elif is_sus:
                    mark = tag_font.render("!", True, theme.WARNING)
                    screen.blit(mark, mark.get_rect(center=icon))
                elif is_marked:
                    theme.draw_cross(screen, icon, size=5, color=theme.DANGER, width=2)
            elif is_marked:
                pygame.draw.polygon(screen, theme.DANGER, [(icon[0] - 5, icon[1] - 7), (icon[0] + 6, icon[1] - 3), (icon[0] - 5, icon[1] + 1)])
                pygame.draw.line(screen, theme.DANGER, (icon[0] - 5, icon[1] - 7), (icon[0] - 5, icon[1] + 8), 2)
            self._log_rows.append((row, index))
            y += row_h + 2
        content_h = y + self.log_scroll - (rect.y + 46)
        self._log_max_scroll = max(0, content_h - (rect.height - 54))
        self.log_scroll = min(self.log_scroll, self._log_max_scroll)
        if self._log_max_scroll > 0:
            fade = pygame.Surface((rect.width - 2, 22), pygame.SRCALPHA)
            fade.fill((15, 20, 30, 235))
            screen.blit(fade, (rect.x + 1, rect.bottom - 23))
            hint = theme.font(12).render("прокрутите колесом мыши, чтобы увидеть все строки", True, theme.TEXT_MUTED)
            screen.blit(hint, hint.get_rect(center=(rect.centerx, rect.bottom - 12)))
        screen.set_clip(prev_clip)

    def _draw_decision(self, screen, rect):
        fight = self.fight
        phase = fight.current
        text_w = rect.width - 32
        body = theme.font(14)
        for size in (17, 16, 15, 14):
            candidate = theme.font(size)
            situation_h = 40 + _measure(phase["situation"], candidate, text_w) + 10
            avail = rect.height - situation_h - 12 - 30 - 8 * (len(phase["options"]) - 1)
            card_h = avail // len(phase["options"])
            need = max(len(wrap_lines(o["text"], candidate, rect.width - 74)) * (candidate.get_linesize() + 2)
                       for o in phase["options"])
            if need <= card_h - 8:
                body = candidate
                break
        # Ситуация
        situation_h = 40 + _measure(phase["situation"], body, text_w) + 10
        card = pygame.Rect(rect.x, rect.y, rect.width, situation_h)
        theme.draw_panel(screen, card, radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.DANGER, (card.x, card.y + 10, 4, card.height - 20), border_radius=2)
        screen.blit(theme.font(theme.FONT_SM, bold=True).render(f"Ситуация · {phase['clock']} · {phase['title']}", True, theme.DANGER), (card.x + 18, card.y + 10))
        _text_block(screen, phase["situation"], body, theme.TEXT_PRIMARY, card.x + 18, card.y + 38, text_w - 6)

        # Варианты решения
        y = card.bottom + 12
        head = theme.font(theme.FONT_SM, bold=True).render("Ваше решение", True, theme.TEXT_SECONDARY)
        screen.blit(head, (rect.x + 4, y))
        y += head.get_height() + 6
        options = phase["options"]
        gap = 8
        card_h = (rect.bottom - y - gap * (len(options) - 1)) // len(options)
        mouse = pygame.mouse.get_pos()
        self._option_rects = []
        for i, option in enumerate(options):
            box = pygame.Rect(rect.x, y + i * (card_h + gap), rect.width, card_h)
            selected = fight.selected == i
            hovered = box.collidepoint(mouse)
            fill = theme.ELEVATED if selected else (theme.SURFACE_ALT if hovered else theme.SURFACE)
            border = theme.ACCENT if selected else (theme.BORDER if hovered else theme.BORDER_SOFT)
            pygame.draw.rect(screen, fill, box, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, border, box, 2 if selected else 1, border_radius=theme.RADIUS_MD)
            badge = (box.x + 28, box.centery)
            pygame.draw.circle(screen, theme.ACCENT if selected else theme.SURFACE_ALT, badge, 15)
            pygame.draw.circle(screen, theme.ACCENT if selected else theme.BORDER, badge, 15, 2)
            letter = theme.font(theme.FONT_SM, bold=True).render("ABCD"[i], True, theme.TEXT_ON_ACCENT if selected else theme.TEXT_SECONDARY)
            screen.blit(letter, letter.get_rect(center=badge))
            lines = wrap_lines(option["text"], body, box.width - 74)
            ty = box.centery - len(lines) * (body.get_linesize() + 2) // 2
            for line in lines:
                screen.blit(body.render(line, True, theme.TEXT_PRIMARY), (box.x + 56, ty))
                ty += body.get_linesize() + 2
            self._option_rects.append((box, i))

    def _card(self, screen, rect, accent, title):
        theme.draw_panel(screen, rect, radius=theme.RADIUS_MD, shadow=False)
        pygame.draw.rect(screen, accent, (rect.x, rect.y + 8, 4, rect.height - 16), border_radius=2)
        screen.blit(theme.font(theme.FONT_SM, bold=True).render(title, True, accent), (rect.x + 16, rect.y + 8))

    def _draw_reveal(self, screen, rect):
        result = self.result
        fight = self.fight
        quality = result.quality
        color = QUALITY_COLOR[quality]
        title = "Время вышло" if result.timed_out else QUALITY_TITLE[quality]

        prev_clip = screen.get_clip()
        screen.set_clip(rect.inflate(0, 8))
        top = rect.y - self.reveal_scroll
        banner = pygame.Rect(rect.x, top, rect.width, 92)
        theme.draw_panel(screen, banner, radius=theme.RADIUS_LG, border=color)
        icon = (banner.x + 34, banner.y + 32)
        if quality == 2:
            theme.draw_check(screen, icon, size=11, color=color, width=4)
        elif quality == 1:
            mark = theme.font(theme.FONT_XL, bold=True).render("!", True, color)
            screen.blit(mark, mark.get_rect(center=icon))
        else:
            theme.draw_cross(screen, icon, size=10, color=color, width=4)
        screen.blit(theme.font(theme.FONT_LG, bold=True).render(title, True, theme.TEXT_PRIMARY), (banner.x + 64, banner.y + 14))
        points = theme.font(theme.FONT_LG, bold=True).render(f"+{result.points}", True, theme.WARNING)
        screen.blit(points, (banner.right - points.get_width() - 20, banner.y + 14))
        chips = [
            (f"Решение +{result.decision_points}", theme.ACCENT),
            (f"Улики +{result.evidence_points}", theme.SUCCESS),
            (f"Скорость +{result.speed_points}", theme.WARNING),
            (f"Целостность -{result.integrity_loss}" if result.integrity_loss else "Целостность без потерь",
             theme.DANGER if result.integrity_loss else theme.SUCCESS),
        ]
        x = banner.x + 18
        chip_font = theme.font(theme.FONT_XS, bold=True)
        for text, chip_color in chips:
            width = chip_font.size(text)[0] + 20
            theme.draw_badge(screen, (x + width // 2, banner.bottom - 22), text, fg=chip_color, bg=theme.SURFACE_ALT, font_size=theme.FONT_XS)
            x += width + 8

        body = theme.font(theme.FONT_XS)
        text_w = rect.width - 36
        y = banner.bottom + 10
        cards = [("Что произошло дальше", theme.ACCENT, [(result.phase["consequences"][quality], theme.TEXT_PRIMARY)])]
        if result.chosen is not None:
            cards.append(("Ваш ответ", color, [(result.chosen["text"], theme.TEXT_PRIMARY), (result.chosen["why"], theme.TEXT_SECONDARY)]))
        else:
            cards.append(("Решение не принято", theme.DANGER, [("Время вышло, а бездействие в SOC тоже решение, и атакующий его оценил.", theme.TEXT_SECONDARY)]))
        best = result.best_option
        if result.chosen is not best:
            cards.append(("Лучшее решение", theme.SUCCESS, [(best["text"], theme.TEXT_PRIMARY), (best["why"], theme.TEXT_SECONDARY)]))
        for title_text, accent, parts in cards:
            height = 34 + sum(_measure(text, body, text_w) + 4 for text, _ in parts) + 6
            card = pygame.Rect(rect.x, y, rect.width, height)
            self._card(screen, card, accent, title_text)
            ty = card.y + 32
            for text, part_color in parts:
                ty = _text_block(screen, text, body, part_color, card.x + 16, ty, text_w) + 4
            y += height + 8
        self._reveal_max_scroll = max(0, y - top - rect.height)
        self.reveal_scroll = min(self.reveal_scroll, self._reveal_max_scroll)
        screen.set_clip(prev_clip)
        if self._reveal_max_scroll > 0:
            hint = theme.font(12).render("колесо мыши: прокрутка", True, theme.TEXT_MUTED)
            screen.blit(hint, (rect.right - hint.get_width() - 8, rect.bottom - 16))

    # ---------- брифинг
    def _draw_intro(self, screen):
        w, h = self.screen_width, self.screen_height
        cx = w // 2
        pulse = (math.sin(self.frame / 16.0) + 1) / 2
        center = (cx, 96)
        draw_hexagon(screen, center, int(46 + 3 * pulse), theme.DANGER_DIM)
        draw_hexagon(screen, center, 46, theme.DANGER, 3)
        pygame.draw.circle(screen, theme.DANGER, center, int(8 + 3 * pulse))
        pygame.draw.line(screen, theme.DANGER, (center[0] - 26, center[1]), (center[0] + 26, center[1]), 2)
        pygame.draw.line(screen, theme.DANGER, (center[0], center[1] - 26), (center[0], center[1] + 26), 2)

        _glitch_text(screen, "ЧЁРНЫЙ ЛЁД", theme.font(60, bold=True), (cx, 190), theme.DANGER, self.frame % 240)
        sub = theme.font(theme.FONT_LG).render("Финальный инцидент  ·  Босс-уровень", True, theme.TEXT_SECONDARY)
        screen.blit(sub, sub.get_rect(center=(cx, 240)))

        panel_w = min(760, w - 60)
        panel = pygame.Rect(cx - panel_w // 2, 268, panel_w, 122)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.DANGER, (panel.x, panel.y + 12, 4, panel.height - 24), border_radius=2)
        _text_block(screen, data.BRIEFING, theme.font(theme.FONT_SM), theme.TEXT_PRIMARY, panel.x + 22, panel.y + 12, panel.width - 44, gap=4)

        tiles = [(str(len(data.PHASES)), "фаз атаки"), (f"{PHASE_TIME_LIMIT} с", "на каждую фазу"), ("0", "подсказок"), (str(PHASE_MAX_POINTS * len(data.PHASES)), "очков максимум")]
        gap = 12
        tile_w = (panel_w - 3 * gap) // 4
        for i, (big, caption) in enumerate(tiles):
            rect = pygame.Rect(panel.x + i * (tile_w + gap), panel.bottom + 14, tile_w, 82)
            pygame.draw.rect(screen, theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, theme.BORDER, rect, 1, border_radius=theme.RADIUS_MD)
            big_surf = theme.font(theme.FONT_XXL, bold=True).render(big, True, theme.DANGER)
            screen.blit(big_surf, big_surf.get_rect(center=(rect.centerx, rect.y + 32)))
            cap = theme.font(theme.FONT_XS).render(caption, True, theme.TEXT_SECONDARY)
            screen.blit(cap, cap.get_rect(center=(rect.centerx, rect.y + 62)))

        done = len(self.completed_levels)
        access = f"Допуск: пройдено {done} из 3 уровней"
        access_color = theme.SUCCESS if done >= 3 else theme.WARNING
        if done < 3:
            access += ". Рекомендуется сначала пройти кампанию"
        screen.blit(theme.font(theme.FONT_SM, bold=True).render(access, True, access_color),
                    theme.font(theme.FONT_SM, bold=True).render(access, True, access_color).get_rect(center=(cx, panel.bottom + 128)))
        sm = self.save_manager
        if sm.boss_attempts:
            record = f"Лучший результат: {sm.boss_best_grade} · {sm.boss_best_score} из {PHASE_MAX_POINTS * len(data.PHASES)}   ·   Попыток: {sm.boss_attempts}   ·   Побед: {sm.boss_victories}"
        else:
            record = "Вы ещё не встречались с BLACK ICE"
        rec = theme.font(theme.FONT_XS).render(record, True, theme.TEXT_MUTED)
        screen.blit(rec, rec.get_rect(center=(cx, panel.bottom + 152)))

        self.start_button.draw(screen)
        keys = theme.font(theme.FONT_XS).render("Пробел или Enter: начать", True, theme.TEXT_MUTED)
        screen.blit(keys, keys.get_rect(center=(cx, self.start_button.rect.bottom + 20)))
        self.back_button.draw(screen)

    # ---------- итоги
    def _draw_final(self, screen):
        fight = self.fight
        panel = self._final_panel()
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        tag, title, description = data.ENDINGS[fight.outcome]
        color = TAG_COLOR[tag]
        letter, rank = fight.grade
        progress = min(1.0, self.final_frame / FINAL_ANIM_FRAMES)
        eased = 1 - (1 - progress) ** 3

        left_w = 330
        x = panel.x + 24
        y = panel.y + 22
        screen.blit(theme.font(theme.FONT_SM).render("Операция завершена", True, theme.TEXT_SECONDARY), (x, y))
        y += 30
        for line in wrap_lines(title, theme.font(theme.FONT_XL, bold=True), left_w - 10):
            screen.blit(theme.font(theme.FONT_XL, bold=True).render(line, True, color), (x, y))
            y += 36
        y = _text_block(screen, description, theme.font(theme.FONT_XS), theme.TEXT_SECONDARY, x, y + 4, left_w - 10) + 8

        ring_center = (x + 66, y + 74)
        draw_ring(screen, ring_center, 62, 12, fight.percent / 100 * eased, color)
        big = theme.font(56, bold=True).render(letter, True, color)
        screen.blit(big, big.get_rect(center=(ring_center[0], ring_center[1] - 8)))
        pct = theme.font(theme.FONT_XS).render(f"{int(fight.percent * eased)}%", True, theme.TEXT_SECONDARY)
        screen.blit(pct, pct.get_rect(center=(ring_center[0], ring_center[1] + 28)))
        screen.blit(theme.font(theme.FONT_MD, bold=True).render(rank, True, theme.TEXT_PRIMARY), (x + 146, ring_center[1] - 30))
        if self.new_best and progress >= 1:
            theme.draw_badge(screen, (x + 210, ring_center[1] + 10), "Новый рекорд", fg=theme.TEXT_ON_ACCENT, bg=theme.WARNING)
        y = ring_center[1] + 82

        total_time = sum(r.elapsed for r in fight.results)
        stats = [
            ("Очки", f"{int(fight.score * eased)} из {fight.max_score}", theme.WARNING),
            ("Целостность сети", f"{fight.integrity} из {INTEGRITY_START}", theme.SUCCESS if fight.integrity > 30 else theme.DANGER),
            ("Мощь атаки осталась", f"{round(fight.boss_hp)} из 100", theme.DANGER if fight.boss_hp > 20 else theme.SUCCESS),
            ("Время на решения", f"{int(total_time) // 60}:{int(total_time) % 60:02d}", theme.ACCENT),
        ]
        for label, value, stat_color in stats:
            screen.blit(theme.font(theme.FONT_XS).render(label, True, theme.TEXT_SECONDARY), (x, y))
            val = theme.font(theme.FONT_SM, bold=True).render(value, True, stat_color)
            screen.blit(val, (x + left_w - val.get_width(), y))
            pygame.draw.line(screen, theme.BORDER_SOFT, (x, y + 24), (x + left_w, y + 24))
            y += 32
        if self.new_achievements:
            y += 6
            for name in self.new_achievements:
                screen.blit(theme.font(theme.FONT_XS, bold=True).render("Достижение: " + name, True, theme.WARNING), (x, y))
                y += 22

        # Правая часть: хронология и разбор
        rx = panel.x + 24 + left_w + 28
        rw = panel.right - 24 - rx
        pygame.draw.line(screen, theme.BORDER_SOFT, (rx - 14, panel.y + 20), (rx - 14, panel.bottom - 20))
        screen.blit(theme.font(theme.FONT_MD, bold=True).render("Хронология операции", True, theme.ACCENT), (rx, panel.y + 20))
        self._final_rows = []
        row_y = panel.y + 54
        row_h = 44
        mouse = pygame.mouse.get_pos()
        for i, phase in enumerate(fight.phases):
            row = pygame.Rect(rx, row_y, rw, row_h - 4)
            played = i < len(fight.results)
            selected = i == self.detail_index and played
            hovered = row.collidepoint(mouse) and played
            fill = theme.ELEVATED if selected else (theme.SURFACE_ALT if hovered else theme.SURFACE)
            pygame.draw.rect(screen, fill, row, border_radius=theme.RADIUS_SM)
            if selected:
                pygame.draw.rect(screen, theme.ACCENT, row, 1, border_radius=theme.RADIUS_SM)
            dot = (row.x + 22, row.centery)
            if played:
                q = fight.results[i].quality
                pygame.draw.circle(screen, QUALITY_COLOR[q], dot, 13)
                if q == 2:
                    theme.draw_check(screen, dot, size=5, color=theme.TEXT_ON_ACCENT, width=2)
                elif q == 1:
                    screen.blit(theme.font(theme.FONT_SM, bold=True).render("!", True, theme.TEXT_ON_ACCENT), theme.font(theme.FONT_SM, bold=True).render("!", True, theme.TEXT_ON_ACCENT).get_rect(center=dot))
                else:
                    theme.draw_cross(screen, dot, size=4, color=theme.TEXT_ON_ACCENT, width=2)
                self._final_rows.append((row, i))
            else:
                pygame.draw.circle(screen, theme.BORDER, dot, 13, 1)
            name_color = theme.TEXT_PRIMARY if played else theme.TEXT_MUTED
            screen.blit(theme.font(theme.FONT_SM, bold=True).render(f"{i + 1}. {phase['tactic']}", True, name_color), (row.x + 46, row.y + 4))
            screen.blit(theme.font(12).render(phase["title"], True, theme.TEXT_MUTED), (row.x + 46, row.y + 24))
            chip = phase["technique"]["id"]
            chip_font = mono(12, bold=True)
            chip_surf = chip_font.render(chip, True, theme.ACCENT if played else theme.TEXT_MUTED)
            chip_rect = pygame.Rect(0, 0, chip_surf.get_width() + 16, 22)
            chip_rect.midright = (row.right - 90, row.centery)
            pygame.draw.rect(screen, theme.SURFACE_ALT if not selected else theme.SURFACE, chip_rect, border_radius=11)
            screen.blit(chip_surf, chip_surf.get_rect(center=chip_rect.center))
            if played:
                pts = theme.font(theme.FONT_SM, bold=True).render(f"+{fight.results[i].points}", True, theme.WARNING)
                screen.blit(pts, pts.get_rect(midright=(row.right - 14, row.centery)))
            row_y += row_h

        detail_top = row_y + 8
        detail = pygame.Rect(rx, detail_top, rw, panel.bottom - 20 - detail_top)
        if self.detail_index < len(fight.results):
            self._draw_detail(screen, detail, fight.results[self.detail_index])

        self.retry_button.draw(screen)
        self.menu_button.draw(screen)

    def _draw_detail(self, screen, rect, result):
        technique = result.phase["technique"]
        prev_clip = screen.get_clip()
        screen.set_clip(rect)
        head = f"{technique['id']}  {technique['name']}"
        screen.blit(mono(14, bold=True).render(head, True, theme.ACCENT), (rect.x, rect.y))
        screen.blit(theme.font(theme.FONT_XS).render(technique["ru"], True, theme.TEXT_SECONDARY), (rect.x, rect.y + 22))

        body = theme.font(15)
        top = rect.y + 50
        best = result.best_option
        cols = []
        if result.chosen is None:
            cols.append(("Ответа не было", theme.DANGER, {"text": "Время вышло.", "why": "Бездействие оставило атакующему инициативу."}))
            cols.append(("Лучшее решение", theme.SUCCESS, best))
        elif result.chosen is best:
            cols.append(("Ваш ответ: лучшее решение", theme.SUCCESS, best))
        else:
            cols.append(("Ваш ответ", QUALITY_COLOR[result.quality], result.chosen))
            cols.append(("Лучшее решение", theme.SUCCESS, best))
        gap = 14
        col_w = (rect.width - gap * (len(cols) - 1)) // len(cols)
        need = max(32 + _measure(o["text"], body, col_w - 28, gap=2) + 6 + _measure(o["why"], body, col_w - 28, gap=2) + 14
                   for _, _, o in cols)
        box_h = min(rect.bottom - top - 28, need)
        for i, (title, color, option) in enumerate(cols):
            box = pygame.Rect(rect.x + i * (col_w + gap), top, col_w, box_h)
            pygame.draw.rect(screen, theme.SURFACE_ALT, box, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, color, (box.x, box.y + 8, 3, box.height - 16), border_radius=2)
            screen.blit(theme.font(theme.FONT_XS, bold=True).render(title, True, color), (box.x + 14, box.y + 8))
            ty = _text_block(screen, option["text"], body, theme.TEXT_PRIMARY, box.x + 14, box.y + 32, box.width - 28, gap=2)
            _text_block(screen, option["why"], body, theme.TEXT_SECONDARY, box.x + 14, ty + 6, box.width - 28, gap=2)
        note_font = theme.font(12)
        missed = sorted(result.missed_marks)
        if missed:
            line = "Пропущенные улики: " + "; ".join(result.phase["log"][i]["text"] for i in missed)
            color = theme.WARNING
        elif result.wrong_marks:
            line, color = "Все улики найдены, но были лишние отметки", theme.WARNING
        else:
            line, color = "Все улики найдены", theme.SUCCESS
        while note_font.size(line)[0] > rect.width and len(line) > 12:
            line = line[:-4].rstrip() + "..."
        screen.blit(note_font.render(line, True, color), (rect.x, top + box_h + 10))
        screen.set_clip(prev_clip)

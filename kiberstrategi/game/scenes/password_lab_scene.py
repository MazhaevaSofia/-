# Лаборатория паролей: анализатор стойкости, генератор парольных фраз и испытание.
# Пароль хранится только в памяти сцены: не сохраняется, не логируется, не отправляется.
import functools
import math
import random
import re

import pygame

from ..core import achievements, sound_manager
from ..core.password_lab import (
    analyze, generate_passphrase, crack_times, format_duration, random_password_bits,
    Challenge, MAX_PASSWORD_LENGTH, SCENARIOS, SCENARIO_RATE_TEXT, KIND_LABELS, SCORE_LABELS, ROUND_POINTS,
)
from ..data.password_challenges import ROUNDS
from ..data.password_lists import PHRASE_WORDS
from ..ui import theme
from ..ui.button import Button
from ..ui.widgets import draw_ring, draw_bar, wrap_lines

MARGIN = 30
TABS = [("analyzer", "Анализатор"), ("phrases", "Генератор фраз"), ("challenge", "Испытание")]
ORANGE = (249, 115, 22)
LIME = (132, 204, 22)
SCORE_COLORS = [theme.DANGER, ORANGE, theme.WARNING, LIME, theme.SUCCESS]
KIND_COLORS = {
    "common": theme.DANGER, "word": ORANGE, "layout": ORANGE, "date": ORANGE,
    "keyboard": theme.WARNING, "sequence": theme.WARNING, "repeat": theme.WARNING,
    "separator": theme.TEXT_MUTED, "random": theme.SUCCESS,
}
EXAMPLES = ["P@ssw0rd", "Sofia2007", "ghbdtn", "Xk9#mQ2$vL7!", "лес-река-лампа-ветер"]
SEPARATORS = [("-", "-"), (".", "."), ("_", "_"), (" ", "пробел")]
MIN_WORDS, MAX_WORDS = 3, 10
CHALLENGE_RANKS = [
    (8, "Гроссмейстер паролей", theme.SUCCESS),
    (6, "Знаток", theme.SUCCESS),
    (4, "Осведомлённый", theme.WARNING),
    (0, "Новичок", theme.DANGER),
]
COMPARE = [("8 случайных символов", random_password_bits(8)), ("12 случайных символов", random_password_bits(12)),
           ("16 случайных символов", random_password_bits(16))]
FONT_SEC = theme.FONT_SM


@functools.lru_cache(maxsize=None)
def mono(size, bold=False):
    path = pygame.font.match_font("menlo,consolas,couriernew,dejavusansmono,monospace")
    f = pygame.font.Font(path, size)
    f.set_bold(bold)
    return f


def _time_color(seconds):
    if seconds < 3600:
        return theme.DANGER
    if seconds < 86400 * 365:
        return ORANGE
    if seconds < 86400 * 365 * 100:
        return LIME
    return theme.SUCCESS


def _time_fraction(seconds):
    return max(0.02, min(1.0, math.log10(max(seconds, 1.0)) / 16.5))


def _bits_text(bits):
    n = int(round(bits))
    tail = n % 10
    if 11 <= n % 100 <= 19:
        word = "бит"
    elif tail == 1:
        word = "бит"
    elif 2 <= tail <= 4:
        word = "бита"
    else:
        word = "бит"
    return f"{n} {word}"


class PasswordLabScene:
    def __init__(self, screen_width, screen_height, save_manager, on_back, rng=None, time_fn=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.save_manager = save_manager
        self._on_back = on_back
        self._rng = rng or random.Random()
        self._passphrase_rng = rng
        self._now = time_fn or pygame.time.get_ticks

        self.tab = "analyzer"
        self.password = ""
        self.show_password = False
        self.analysis = analyze("")
        self.frame = 0
        self.toast = None

        self.word_count = 6
        self.separator = "-"
        self.capitalize = True
        self.add_digit = True
        self.phrase = ""
        self.phrase_bits = 0.0
        self.phrase_visible = True

        self.challenge = None
        self.challenge_state = "intro"
        self.challenge_result = None
        self.challenge_new_best = False
        self.challenge_new_achievements = []
        self.reveal_since = 0

        self._tab_rects = []
        self._chip_rects = []
        self._hit = {}
        self._card_rects = []

        big = theme.font(theme.FONT_MD, bold=True)
        self.back_button = Button(0, 0, 120, 35, "Назад", theme.SURFACE_ALT, self.leave)
        self.show_button = Button(0, 0, 118, 52, "Показать", theme.SURFACE_ALT, self.toggle_show, font=theme.font(theme.FONT_SM))
        self.clear_button = Button(0, 0, 100, 30, "Очистить", theme.SURFACE_ALT, self.clear_password, font=theme.font(theme.FONT_XS))
        self.generate_button = Button(0, 0, 260, 50, "Сгенерировать", (25, 120, 90), self.generate, font=big)
        self.minus_button = Button(0, 0, 42, 42, "-", theme.SURFACE_ALT, lambda: self.change_words(-1), font=big)
        self.plus_button = Button(0, 0, 42, 42, "+", theme.SURFACE_ALT, lambda: self.change_words(1), font=big)
        self.hide_phrase_button = Button(0, 0, 130, 32, "Скрыть", theme.SURFACE_ALT, self.toggle_phrase, font=theme.font(theme.FONT_XS))
        self.start_button = Button(0, 0, 300, 52, "Начать испытание", (25, 120, 90), self.start_challenge, font=big)
        self.next_button = Button(0, 0, 260, 46, "Дальше", theme.ACCENT_DIM, self.next_round, font=big)
        self.again_button = Button(0, 0, 220, 48, "Ещё раз", (25, 120, 90), self.start_challenge, font=big)
        self.to_analyzer_button = Button(0, 0, 240, 48, "К анализатору", theme.SURFACE_ALT, lambda: self.set_tab("analyzer"), font=big)
        self.generate()
        self._place_buttons()

    # ------------------------------------------------------------ раскладка
    def _content(self):
        w, h = self.screen_width, self.screen_height
        return pygame.Rect(MARGIN, 128, w - 2 * MARGIN, h - 128 - 64)

    def _columns(self, ratio=0.47):
        c = self._content()
        gap = 18
        left_w = int(c.width * ratio)
        return (pygame.Rect(c.x, c.y, left_w, c.height),
                pygame.Rect(c.x + left_w + gap, c.y, c.width - left_w - gap, c.height))

    def _place_buttons(self):
        w, h = self.screen_width, self.screen_height
        self.back_button.rect.topleft = (MARGIN, h - 52)
        left, right = self._columns()
        self.show_button.rect.topleft = (left.right - 20 - 118, left.y + 44)
        self.clear_button.rect.topleft = (left.right - 20 - 100, left.y + 8)
        self.generate_button.rect.topleft = (left.x + 20, left.bottom - 150)
        c = self._content()
        self.start_button.rect.midtop = (c.centerx, c.y + 330)
        self.next_button.rect.topleft = (c.right - 260, c.bottom - 50)
        self.again_button.rect.topleft = (c.centerx - 232, c.y + 400)
        self.to_analyzer_button.rect.topleft = (c.centerx + 12, c.y + 400)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self._place_buttons()

    # ------------------------------------------------------------ действия
    def leave(self):
        self.password = ""
        self.analysis = analyze("")
        self._on_back()

    def set_tab(self, tab):
        self.tab = tab
        sound_manager.play("click")

    def toggle_show(self):
        self.show_password = not self.show_password
        self.show_button.text = "Скрыть" if self.show_password else "Показать"

    def clear_password(self):
        self.set_password("")

    def set_password(self, value):
        self.password = value[:MAX_PASSWORD_LENGTH]
        self.analysis = analyze(self.password)

    def change_words(self, delta):
        self.word_count = max(MIN_WORDS, min(MAX_WORDS, self.word_count + delta))
        self.generate()

    def toggle_phrase(self):
        self.phrase_visible = not self.phrase_visible
        self.hide_phrase_button.text = "Скрыть" if self.phrase_visible else "Показать"

    def generate(self):
        self.phrase, self.phrase_bits = generate_passphrase(
            self.word_count, self.separator, self.capitalize, self.add_digit, rng=self._passphrase_rng)
        new_ids = self.save_manager.unlock_achievements(achievements.evaluate_passphrase(self.phrase_bits))
        if new_ids:
            self._show_toast("Достижение: " + achievements.ACHIEVEMENTS[new_ids[0]]["title"])
            sound_manager.play("achievement")

    def _show_toast(self, text):
        self.toast = (text, self._now())

    def start_challenge(self):
        self.tab = "challenge"
        self.challenge = Challenge(ROUNDS, rng=self._rng)
        self.challenge_state = "playing"
        self.challenge_result = None
        self.challenge_new_achievements = []

    def choose(self, index):
        if self.challenge_state != "playing":
            return
        self.challenge_result = self.challenge.answer(index)
        self.challenge_state = "reveal"
        self.reveal_since = self._now()
        sound_manager.play("correct" if self.challenge_result.correct else "wrong")

    def next_round(self):
        if self.challenge_state != "reveal" or self._now() - self.reveal_since < 300:
            return
        self.challenge.advance()
        if self.challenge.finished:
            self._finish_challenge()
        else:
            self.challenge_state = "playing"
            self.challenge_result = None

    def _finish_challenge(self):
        ch = self.challenge
        self.challenge_new_best = self.save_manager.record_password_challenge(ch.score)
        new_ids = self.save_manager.unlock_achievements(achievements.evaluate_password_challenge(ch.correct_count))
        self.challenge_new_achievements = [achievements.ACHIEVEMENTS[a]["title"] for a in new_ids]
        self.challenge_state = "final"
        sound_manager.play("success" if ch.correct_count >= 6 else "click")

    # ------------------------------------------------------------ события
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event)
        if self.back_button.handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab, rect in self._tab_rects:
                if rect.collidepoint(event.pos):
                    if tab != self.tab:
                        self.set_tab(tab)
                    return True
        if self.tab == "analyzer":
            return self._analyzer_event(event)
        if self.tab == "phrases":
            return self._phrases_event(event)
        return self._challenge_event(event)

    def _handle_key(self, event):
        key = event.key
        if self.tab == "analyzer":
            if key == pygame.K_BACKSPACE:
                self.set_password(self.password[:-1])
                return True
            if key == pygame.K_ESCAPE:
                self.set_password("")
                return True
            if key == pygame.K_v and event.mod & (pygame.KMOD_META | pygame.KMOD_CTRL):
                self._paste()
                return True
            char = getattr(event, "unicode", "")
            if char and char.isprintable() and not event.mod & (pygame.KMOD_META | pygame.KMOD_CTRL):
                self.set_password(self.password + char)
                return True
        elif self.tab == "phrases" and key in (pygame.K_RETURN, pygame.K_SPACE):
            self.generate()
            return True
        elif self.tab == "challenge":
            if self.challenge_state == "intro" and key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_challenge()
                return True
            if self.challenge_state == "playing" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.choose((pygame.K_1, pygame.K_2, pygame.K_3).index(key))
                return True
            if self.challenge_state == "reveal" and key in (pygame.K_RETURN, pygame.K_SPACE):
                self.next_round()
                return True
            if self.challenge_state == "final" and key == pygame.K_RETURN:
                self.start_challenge()
                return True
        return False

    def _paste(self):
        try:
            pygame.scrap.init()
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if raw:
                text = raw.decode("utf-8", errors="ignore").replace("\x00", "").splitlines()[0]
                self.set_password(self.password + text)
        except (pygame.error, AttributeError, IndexError, TypeError):
            pass

    def _analyzer_event(self, event):
        if self.show_button.handle_event(event) or self.clear_button.handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, text in self._chip_rects:
                if rect.collidepoint(event.pos):
                    self.set_password(text)
                    sound_manager.play("click")
                    return True
        return False

    def _phrases_event(self, event):
        for button in (self.generate_button, self.minus_button, self.plus_button, self.hide_phrase_button):
            if button.handle_event(event):
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self._hit.items():
                if not rect.collidepoint(event.pos):
                    continue
                if key.startswith("sep:"):
                    self.separator = key[4:]
                    self.generate()
                elif key == "capitalize":
                    self.capitalize = not self.capitalize
                    self.generate()
                elif key == "digit":
                    self.add_digit = not self.add_digit
                    self.generate()
                else:
                    continue
                sound_manager.play("click")
                return True
        return False

    def _challenge_event(self, event):
        if self.challenge_state == "intro":
            return self.start_button.handle_event(event)
        if self.challenge_state == "playing":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, index in self._card_rects:
                    if rect.collidepoint(event.pos):
                        self.choose(index)
                        return True
        elif self.challenge_state == "reveal":
            locked = self._now() - self.reveal_since < 300
            return self.next_button.handle_event(event, disabled=locked)
        elif self.challenge_state == "final":
            return self.again_button.handle_event(event) or self.to_analyzer_button.handle_event(event)
        return False

    def update(self):
        self.frame += 1
        for button in (self.back_button, self.show_button, self.clear_button, self.generate_button, self.minus_button,
                       self.plus_button, self.hide_phrase_button, self.start_button, self.next_button,
                       self.again_button, self.to_analyzer_button):
            button.update()
        if self.toast and self._now() - self.toast[1] > 3500:
            self.toast = None

    # ------------------------------------------------------------ отрисовка
    def draw(self, screen):
        screen.fill(theme.BG)
        self._hit = {}
        self._draw_header(screen)
        if self.tab == "analyzer":
            self._draw_analyzer(screen)
        elif self.tab == "phrases":
            self._draw_phrases(screen)
        else:
            self._draw_challenge(screen)
        self._draw_footer(screen)
        if self.toast:
            self._draw_toast(screen)

    def _draw_header(self, screen):
        w = self.screen_width
        screen.blit(theme.font(theme.FONT_XL, bold=True).render("Лаборатория паролей", True, theme.TEXT_PRIMARY), (MARGIN, 20))
        sub = theme.font(theme.FONT_XS).render("Проверьте, как атакующий видит ваш пароль, и научитесь делать надёжные", True, theme.TEXT_SECONDARY)
        screen.blit(sub, (MARGIN, 60))
        self._tab_rects = []
        x = MARGIN
        mouse = pygame.mouse.get_pos()
        font = theme.font(theme.FONT_SM, bold=True)
        for tab, label in TABS:
            width = font.size(label)[0] + 44
            rect = pygame.Rect(x, 84, width, 36)
            active = tab == self.tab
            hovered = rect.collidepoint(mouse)
            fill = theme.ACCENT_DIM if active else (theme.SURFACE_ALT if hovered else theme.SURFACE)
            pygame.draw.rect(screen, fill, rect, border_radius=18)
            pygame.draw.rect(screen, theme.ACCENT if active else theme.BORDER, rect, 2 if active else 1, border_radius=18)
            text = font.render(label, True, theme.TEXT_PRIMARY if active else theme.TEXT_SECONDARY)
            screen.blit(text, text.get_rect(center=rect.center))
            self._tab_rects.append((tab, rect))
            x += width + 10

    def _draw_footer(self, screen):
        w, h = self.screen_width, self.screen_height
        theme.draw_lock(screen, (MARGIN + 160, h - 34), color=theme.SUCCESS, scale=1.2)
        note = theme.font(theme.FONT_XS).render(
            "Пароль остаётся в памяти этого окна: он не сохраняется, не записывается в журнал и не отправляется в сеть. "
            "Всё равно вводите похожий пароль, а не настоящий.", True, theme.TEXT_MUTED)
        if note.get_width() > w - MARGIN * 2 - 200:
            for i, line in enumerate(wrap_lines(
                    "Пароль остаётся в памяти этого окна: не сохраняется, не пишется в журнал и не уходит в сеть. "
                    "Всё равно вводите похожий пароль, а не настоящий.", theme.font(theme.FONT_XS), w - MARGIN * 2 - 200)):
                screen.blit(theme.font(theme.FONT_XS).render(line, True, theme.TEXT_MUTED), (MARGIN + 180, h - 50 + i * 18))
        else:
            screen.blit(note, (MARGIN + 180, h - 42))
        self.back_button.draw(screen)

    def _draw_toast(self, screen):
        text = theme.font(theme.FONT_SM, bold=True).render(self.toast[0], True, theme.TEXT_ON_ACCENT)
        rect = pygame.Rect(0, 0, text.get_width() + 36, 40)
        rect.topright = (self.screen_width - MARGIN, 24)
        pygame.draw.rect(screen, theme.WARNING, rect, border_radius=20)
        screen.blit(text, text.get_rect(center=rect.center))

    def _card(self, screen, rect, title=None, accent=theme.ACCENT):
        theme.draw_panel(screen, rect, radius=theme.RADIUS_LG)
        if title:
            screen.blit(theme.font(theme.FONT_SM, bold=True).render(title, True, accent), (rect.x + 20, rect.y + 14))

    # ---------- анализатор
    def _draw_analyzer(self, screen):
        left, right = self._columns()
        analysis = self.analysis
        score = analysis["score"]
        color = SCORE_COLORS[score]

        # Ввод
        input_card = pygame.Rect(left.x, left.y, left.width, 132)
        self._card(screen, input_card, "Введите пароль для проверки")
        field = pygame.Rect(input_card.x + 20, input_card.y + 44, input_card.width - 40 - 130, 52)
        pygame.draw.rect(screen, theme.SURFACE_ALT, field, border_radius=theme.RADIUS_MD)
        pygame.draw.rect(screen, theme.ACCENT, field, 2, border_radius=theme.RADIUS_MD)
        self._draw_field_text(screen, field)
        self.show_button.rect.topleft = (field.right + 12, field.y)
        self.show_button.draw(screen)
        self.clear_button.rect.topleft = (input_card.right - 20 - 100, input_card.y + 8)
        if self.password:
            self.clear_button.draw(screen)
        self._chip_rects = []
        x, y = input_card.x + 20, input_card.y + 106
        screen.blit(theme.font(theme.FONT_XS).render("Примеры:", True, theme.TEXT_MUTED), (x, y + 3))
        x += 76
        mouse = pygame.mouse.get_pos()
        chip_font = mono(13)
        for example in EXAMPLES:
            width = chip_font.size(example)[0] + 20
            if x + width > input_card.right - 12:
                break
            rect = pygame.Rect(x, y - 2, width, 24)
            hovered = rect.collidepoint(mouse)
            pygame.draw.rect(screen, theme.ELEVATED if hovered else theme.SURFACE_ALT, rect, border_radius=12)
            pygame.draw.rect(screen, theme.BORDER, rect, 1, border_radius=12)
            screen.blit(chip_font.render(example, True, theme.TEXT_SECONDARY), (rect.x + 10, rect.y + 4))
            self._chip_rects.append((rect, example))
            x += width + 6

        # Оценка
        strength = pygame.Rect(left.x, input_card.bottom + 12, left.width, 104)
        self._card(screen, strength, "Оценка стойкости")
        seg_w = (strength.width - 40 - 4 * 6) // 5
        for i in range(5):
            rect = pygame.Rect(strength.x + 20 + i * (seg_w + 6), strength.y + 46, seg_w, 12)
            lit = self.password and i <= score
            pygame.draw.rect(screen, SCORE_COLORS[i] if lit else theme.SURFACE_ALT, rect, border_radius=6)
        label = SCORE_LABELS[score] if self.password else "Введите пароль"
        screen.blit(theme.font(theme.FONT_LG, bold=True).render(label, True, color if self.password else theme.TEXT_MUTED),
                    (strength.x + 20, strength.y + 66))
        if self.password:
            detail = f"{_bits_text(analysis['bits'])} энтропии, ≈ {self._format_guesses(analysis['guesses'])} попыток"
            surf = theme.font(theme.FONT_XS).render(detail, True, theme.TEXT_SECONDARY)
            screen.blit(surf, (strength.right - 20 - surf.get_width(), strength.y + 72))

        # Как это видит атакующий
        view = pygame.Rect(left.x, strength.bottom + 12, left.width, left.bottom - strength.bottom - 12)
        self._card(screen, view, "Как это видит атакующий")
        self._draw_breakdown(screen, view)

        # Время взлома
        self._draw_times(screen, right, analysis["times"], self.password != "")

    def _draw_field_text(self, screen, field):
        inner = field.inflate(-28, 0)
        prev_clip = screen.get_clip()
        screen.set_clip(inner)
        if not self.password:
            hint = theme.font(theme.FONT_SM).render("Например: Sofia2007", True, theme.TEXT_MUTED)
            screen.blit(hint, (inner.x, field.centery - hint.get_height() // 2))
            text_w = 0
        else:
            shown = self.password if self.show_password else "•" * len(self.password)
            font = mono(22) if self.show_password else theme.font(24)
            while font.size(shown)[0] > inner.width and len(shown) > 1:
                shown = shown[1:]
            surf = font.render(shown, True, theme.TEXT_PRIMARY)
            screen.blit(surf, (inner.x, field.centery - surf.get_height() // 2))
            text_w = surf.get_width()
        if (self.frame // 30) % 2 == 0:
            cx = inner.x + text_w + 2
            pygame.draw.line(screen, theme.ACCENT, (cx, field.y + 12), (cx, field.bottom - 12), 2)
        screen.set_clip(prev_clip)

    @staticmethod
    def _format_guesses(guesses):
        if guesses < 1000:
            return str(int(guesses))
        exponent = int(math.log10(guesses))
        if exponent < 6:
            return f"{int(guesses):,}".replace(",", " ")
        return f"10^{exponent}"

    def _draw_breakdown(self, screen, rect):
        analysis = self.analysis
        x0, y = rect.x + 20, rect.y + 46
        if not self.password:
            text = "Введите пароль, и здесь появится разбор: какие части атакующий угадает по словарю, а какие придётся перебирать."
            for line in wrap_lines(text, theme.font(theme.FONT_XS), rect.width - 40):
                screen.blit(theme.font(theme.FONT_XS).render(line, True, theme.TEXT_MUTED), (x0, y))
                y += 20
            return
        kind_at = {}
        for part in analysis["parts"]:
            for i in range(part.start, part.end):
                kind_at[i] = part.kind
        box_w, box_h, gap = 20, 26, 3
        per_row = max(1, (rect.width - 40) // (box_w + gap))
        font = mono(14, bold=True)
        for i, char in enumerate(self.password):
            col, row = i % per_row, i // per_row
            box = pygame.Rect(x0 + col * (box_w + gap), y + row * (box_h + gap), box_w, box_h)
            fill = KIND_COLORS[kind_at.get(i, "random")]
            pygame.draw.rect(screen, fill, box, border_radius=4)
            if self.show_password:
                glyph = font.render(char, True, theme.TEXT_ON_ACCENT)
                screen.blit(glyph, glyph.get_rect(center=box.center))
        rows = (len(self.password) - 1) // per_row + 1
        y += rows * (box_h + gap) + 8
        seen = []
        for part in analysis["parts"]:
            if part.kind not in seen:
                seen.append(part.kind)
        lx = x0
        for kind in seen:
            label = KIND_LABELS[kind]
            surf = theme.font(12).render(label, True, theme.TEXT_SECONDARY)
            if lx + surf.get_width() + 20 > rect.right - 16:
                lx = x0
                y += 18
            pygame.draw.rect(screen, KIND_COLORS[kind], (lx, y + 3, 10, 10), border_radius=3)
            screen.blit(surf, (lx + 16, y))
            lx += surf.get_width() + 34
        y += 26
        prev_clip = screen.get_clip()
        screen.set_clip(rect)
        for tip in analysis["tips"]:
            pygame.draw.circle(screen, theme.ACCENT, (x0 + 4, y + 9), 3)
            lines = wrap_lines(tip, theme.font(theme.FONT_XS), rect.width - 56)
            for line in lines:
                screen.blit(theme.font(theme.FONT_XS).render(line, True, theme.TEXT_PRIMARY), (x0 + 16, y))
                y += 19
            y += 5
        screen.set_clip(prev_clip)

    def _draw_times(self, screen, rect, times, active, heading="Сколько времени уйдёт на взлом"):
        self._card(screen, rect, heading)
        y = rect.y + 50
        row_h = (rect.height - 50 - 60) // len(times)
        for i, (name, seconds) in enumerate(times):
            top = y + i * row_h
            screen.blit(theme.font(theme.FONT_SM, bold=True).render(name, True, theme.TEXT_PRIMARY), (rect.x + 20, top))
            screen.blit(theme.font(12).render(SCENARIO_RATE_TEXT[i], True, theme.TEXT_MUTED), (rect.x + 20, top + 22))
            if active:
                color = _time_color(seconds)
                label = format_duration(seconds)
                surf = theme.font(theme.FONT_LG, bold=True).render(label, True, color)
                screen.blit(surf, (rect.right - 20 - surf.get_width(), top + 2))
                draw_bar(screen, pygame.Rect(rect.x + 20, top + 44, rect.width - 40, 10), _time_fraction(seconds), color)
            else:
                draw_bar(screen, pygame.Rect(rect.x + 20, top + 44, rect.width - 40, 10), 0, theme.BORDER)
        note = "Оценка учебная: словари небольшие, а реальные атакующие используют миллиарды записей. Считайте результат скорее оптимистичным."
        for j, line in enumerate(wrap_lines(note, theme.font(12), rect.width - 40)):
            screen.blit(theme.font(12).render(line, True, theme.TEXT_MUTED), (rect.x + 20, rect.bottom - 46 + j * 16))

    # ---------- генератор фраз
    def _draw_phrases(self, screen):
        left, right = self._columns(0.40)
        self._card(screen, left, "Параметры фразы")
        mouse = pygame.mouse.get_pos()
        y = left.y + 52
        screen.blit(theme.font(theme.FONT_SM).render("Количество слов", True, theme.TEXT_SECONDARY), (left.x + 20, y + 10))
        self.plus_button.rect.topleft = (left.right - 20 - 42, y)
        self.minus_button.rect.topleft = (left.right - 20 - 42 - 60 - 42, y)
        self.minus_button.draw(screen, disabled=self.word_count <= MIN_WORDS)
        self.plus_button.draw(screen, disabled=self.word_count >= MAX_WORDS)
        count = theme.font(theme.FONT_XL, bold=True).render(str(self.word_count), True, theme.TEXT_PRIMARY)
        screen.blit(count, count.get_rect(center=(left.right - 20 - 42 - 30, y + 21)))

        y += 62
        screen.blit(theme.font(theme.FONT_SM).render("Разделитель", True, theme.TEXT_SECONDARY), (left.x + 20, y + 4))
        x = left.right - 20
        for value, label in reversed(SEPARATORS):
            width = max(40, theme.font(theme.FONT_SM).size(label)[0] + 24)
            rect = pygame.Rect(x - width, y, width, 34)
            active = self.separator == value
            pygame.draw.rect(screen, theme.ACCENT_DIM if active else (theme.ELEVATED if rect.collidepoint(mouse) else theme.SURFACE_ALT), rect, border_radius=17)
            pygame.draw.rect(screen, theme.ACCENT if active else theme.BORDER, rect, 2 if active else 1, border_radius=17)
            surf = theme.font(theme.FONT_SM, bold=True).render(label, True, theme.TEXT_PRIMARY if active else theme.TEXT_SECONDARY)
            screen.blit(surf, surf.get_rect(center=rect.center))
            self._hit[f"sep:{value}"] = rect
            x -= width + 6

        y += 56
        for key, label, value in (("capitalize", "Слова с заглавной буквы", self.capitalize), ("digit", "Цифра в конце", self.add_digit)):
            rect = pygame.Rect(left.x + 20, y, left.width - 40, 36)
            pygame.draw.rect(screen, theme.ELEVATED if rect.collidepoint(mouse) else theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_MD)
            screen.blit(theme.font(theme.FONT_SM).render(label, True, theme.TEXT_PRIMARY), (rect.x + 14, rect.y + 8))
            switch = pygame.Rect(rect.right - 60, rect.y + 8, 44, 20)
            pygame.draw.rect(screen, theme.SUCCESS_DIM if value else theme.BORDER, switch, border_radius=10)
            pygame.draw.circle(screen, theme.SUCCESS if value else theme.TEXT_MUTED, (switch.right - 10 if value else switch.x + 10, switch.centery), 8)
            self._hit[key] = rect
            y += 44

        note = ("Считаем честно: атакующий знает и список из "
                f"{len(PHRASE_WORDS)} слов, и правила, поэтому каждое слово даёт ровно "
                f"{int(math.log2(len(PHRASE_WORDS)))} бит, а заглавные буквы и разделитель ничего не добавляют. "
                "Для настоящих паролей используйте менеджер паролей и список побольше.")
        ny = y + 6
        for line in wrap_lines(note, theme.font(12), left.width - 40):
            screen.blit(theme.font(12).render(line, True, theme.TEXT_MUTED), (left.x + 20, ny))
            ny += 16
        table_top = ny + 12
        if table_top + 26 + 4 * 21 <= left.bottom - 68 - 8:
            screen.blit(theme.font(theme.FONT_XS, bold=True).render("Ориентиры: сколько бит даёт число слов", True, theme.TEXT_SECONDARY), (left.x + 20, table_top))
            per_word = math.log2(len(PHRASE_WORDS))
            for i, count in enumerate(range(5, 9)):
                bits_value = count * per_word + (math.log2(10) if self.add_digit else 0)
                row_y = table_top + 26 + i * 21
                current = count == self.word_count
                color = SCORE_COLORS[min(4, int(bits_value // 16))]
                if current:
                    pygame.draw.rect(screen, theme.SURFACE_ALT, (left.x + 14, row_y - 3, left.width - 28, 22), border_radius=6)
                pygame.draw.circle(screen, color, (left.x + 30, row_y + 8), 5)
                screen.blit(theme.font(theme.FONT_XS, bold=current).render(f"{count} слов", True, theme.TEXT_PRIMARY if current else theme.TEXT_SECONDARY), (left.x + 46, row_y))
                value = theme.font(theme.FONT_XS, bold=current).render(_bits_text(bits_value), True, color)
                screen.blit(value, (left.right - 24 - value.get_width(), row_y))
        self.generate_button.rect.topleft = (left.x + 20, left.bottom - 68)
        self.generate_button.rect.width = left.width - 40
        self.generate_button.draw(screen)

        # Результат
        self._card(screen, right, "Ваша парольная фраза")
        box = pygame.Rect(right.x + 20, right.y + 46, right.width - 40, 96)
        pygame.draw.rect(screen, theme.SURFACE_ALT, box, border_radius=theme.RADIUS_MD)
        pygame.draw.rect(screen, theme.SUCCESS, box, 2, border_radius=theme.RADIUS_MD)
        shown = self.phrase if self.phrase_visible else "•" * len(self.phrase)
        for size in (30, 26, 22, 18):
            font = theme.font(size, bold=True)
            lines = self._wrap_phrase(shown, font, box.width - 32)
            if len(lines) * font.get_linesize() <= box.height - 12:
                break
        ty = box.centery - len(lines) * font.get_linesize() // 2
        for line in lines:
            surf = font.render(line, True, theme.TEXT_PRIMARY)
            screen.blit(surf, surf.get_rect(midtop=(box.centerx, ty)))
            ty += font.get_linesize()
        self.hide_phrase_button.rect.topright = (right.right - 20, right.y + 10)
        self.hide_phrase_button.draw(screen)

        # Энтропия и сравнение
        info_y = box.bottom + 16
        ring_center = (right.x + 20 + 56, info_y + 62)
        fraction = min(1.0, self.phrase_bits / 80)
        ring_color = SCORE_COLORS[min(4, int(self.phrase_bits // 16))]
        draw_ring(screen, ring_center, 52, 10, fraction, ring_color)
        bits = theme.font(theme.FONT_LG, bold=True).render(str(int(round(self.phrase_bits))), True, theme.TEXT_PRIMARY)
        screen.blit(bits, bits.get_rect(center=(ring_center[0], ring_center[1] - 6)))
        screen.blit(theme.font(12).render("бит", True, theme.TEXT_MUTED), theme.font(12).render("бит", True, theme.TEXT_MUTED).get_rect(center=(ring_center[0], ring_center[1] + 16)))

        compare_x = right.x + 20 + 128
        compare_w = right.right - 20 - compare_x
        screen.blit(theme.font(theme.FONT_XS, bold=True).render("Сравнение стойкости в битах", True, theme.TEXT_SECONDARY), (compare_x, info_y))
        rows = [("Ваша фраза", self.phrase_bits, theme.SUCCESS)] + [(n, b, theme.ACCENT) for n, b in COMPARE]
        for i, (name, bits_value, color) in enumerate(rows):
            top = info_y + 24 + i * 24
            screen.blit(theme.font(12).render(name, True, theme.TEXT_PRIMARY if i == 0 else theme.TEXT_SECONDARY), (compare_x, top))
            bar = pygame.Rect(compare_x + 160, top + 3, compare_w - 160 - 50, 10)
            draw_bar(screen, bar, bits_value / 110, color)
            screen.blit(theme.font(12).render(str(int(round(bits_value))), True, theme.TEXT_SECONDARY), (bar.right + 8, top))

        times_rect = pygame.Rect(right.x, info_y + 24 + 4 * 24 + 22, right.width, right.bottom - (info_y + 24 + 4 * 24 + 22))
        self._times_compact(screen, times_rect, crack_times(2.0 ** self.phrase_bits))

    def _times_compact(self, screen, rect, times):
        pygame.draw.line(screen, theme.BORDER_SOFT, (rect.x + 20, rect.y), (rect.right - 20, rect.y))
        screen.blit(theme.font(theme.FONT_XS, bold=True).render("Сколько времени уйдёт на взлом", True, theme.TEXT_SECONDARY), (rect.x + 20, rect.y + 10))
        row_h = max(26, (rect.height - 38) // len(times))
        for i, (name, seconds) in enumerate(times):
            top = rect.y + 34 + i * row_h
            color = _time_color(seconds)
            screen.blit(theme.font(12).render(name, True, theme.TEXT_SECONDARY), (rect.x + 20, top + 2))
            label = theme.font(theme.FONT_XS, bold=True).render(format_duration(seconds), True, color)
            screen.blit(label, (rect.right - 20 - label.get_width(), top))
            draw_bar(screen, pygame.Rect(rect.x + 20, top + 20, rect.width - 40, 5), _time_fraction(seconds), color)

    # ---------- испытание
    def _draw_challenge(self, screen):
        c = self._content()
        state = self.challenge_state
        if state == "intro":
            self._draw_challenge_intro(screen, c)
        elif state == "final":
            self._draw_challenge_final(screen, c)
        else:
            self._draw_challenge_round(screen, c)

    def _draw_challenge_intro(self, screen, c):
        panel = pygame.Rect(0, 0, min(760, c.width), 430)
        panel.midtop = (c.centerx, c.y + 10)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        title = theme.font(theme.FONT_XXL, bold=True).render("Испытание: кто крепче?", True, theme.TEXT_PRIMARY)
        screen.blit(title, title.get_rect(midtop=(panel.centerx, panel.y + 28)))
        text = ("В каждом из 8 раундов вам покажут три пароля. Выберите самый стойкий. "
                "Верный ответ определяет тот же оценщик, что и в анализаторе, а после выбора вы увидите цифры и короткий урок.")
        for i, line in enumerate(wrap_lines(text, theme.font(theme.FONT_MD), panel.width - 80)):
            screen.blit(theme.font(theme.FONT_MD).render(line, True, theme.TEXT_SECONDARY), (panel.x + 40, panel.y + 90 + i * 26))
        tiles = [(str(len(ROUNDS)), "раундов"), ("3", "пароля в каждом"), (f"+{ROUND_POINTS}", "очков за верный")]
        gap = 14
        tile_w = (panel.width - 80 - 2 * gap) // 3
        for i, (big, caption) in enumerate(tiles):
            rect = pygame.Rect(panel.x + 40 + i * (tile_w + gap), panel.y + 210, tile_w, 90)
            pygame.draw.rect(screen, theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, theme.BORDER, rect, 1, border_radius=theme.RADIUS_MD)
            b = theme.font(theme.FONT_XXL, bold=True).render(big, True, theme.ACCENT)
            screen.blit(b, b.get_rect(center=(rect.centerx, rect.y + 34)))
            cap = theme.font(theme.FONT_XS).render(caption, True, theme.TEXT_SECONDARY)
            screen.blit(cap, cap.get_rect(center=(rect.centerx, rect.y + 68)))
        best = self.save_manager.password_best
        runs = self.save_manager.password_runs
        stats = theme.font(theme.FONT_SM, bold=True).render(f"Лучший результат: {best} из {len(ROUNDS) * ROUND_POINTS}   ·   Пройдено раз: {runs}", True, theme.WARNING)
        screen.blit(stats, stats.get_rect(center=(panel.centerx, panel.y + 330)))
        self.start_button.rect.midtop = (panel.centerx, panel.y + 360)
        self.start_button.draw(screen)

    def _draw_challenge_round(self, screen, c):
        ch = self.challenge
        rnd = ch.current
        reveal = self.challenge_state == "reveal"
        head = theme.font(theme.FONT_LG, bold=True).render(f"Раунд {ch.index + 1} из {ch.total}", True, theme.TEXT_PRIMARY)
        screen.blit(head, (c.x, c.y))
        for i in range(ch.total):
            cx = c.x + 8 + i * 22
            if i < len(ch.results) and (i < ch.index or reveal):
                pygame.draw.circle(screen, theme.SUCCESS if ch.results[i].correct else theme.DANGER, (cx, c.y + 46), 7)
            elif i == ch.index:
                pygame.draw.circle(screen, theme.ACCENT, (cx, c.y + 46), 8)
            else:
                pygame.draw.circle(screen, theme.BORDER, (cx, c.y + 46), 7, 1)
        score = theme.font(theme.FONT_MD, bold=True).render(f"Очки: {ch.score}", True, theme.WARNING)
        screen.blit(score, (c.right - score.get_width(), c.y + 4))
        prompt = "Какой пароль самый стойкий?" if not reveal else ("Верно!" if self.challenge_result.correct else "Не угадали")
        prompt_color = theme.TEXT_SECONDARY if not reveal else (theme.SUCCESS if self.challenge_result.correct else theme.DANGER)
        screen.blit(theme.font(theme.FONT_MD, bold=True).render(prompt, True, prompt_color), (c.x, c.y + 70))

        gap = 18
        card_w = (c.width - 2 * gap) // 3
        card_h = max(190, min(270, c.bottom - (c.y + 106) - 190))
        mouse = pygame.mouse.get_pos()
        self._card_rects = []
        for i, password in enumerate(rnd["options"]):
            rect = pygame.Rect(c.x + i * (card_w + gap), c.y + 106, card_w, card_h)
            hovered = rect.collidepoint(mouse) and not reveal
            border = theme.ACCENT if hovered else theme.BORDER
            fill = theme.ELEVATED if hovered else theme.SURFACE
            if reveal:
                if i == rnd["best"]:
                    border = theme.SUCCESS
                elif i == self.challenge_result.chosen:
                    border = theme.DANGER
            pygame.draw.rect(screen, fill, rect, border_radius=theme.RADIUS_LG)
            pygame.draw.rect(screen, border, rect, 3 if reveal and border != theme.BORDER else 1, border_radius=theme.RADIUS_LG)
            badge = (rect.x + 26, rect.y + 26)
            pygame.draw.circle(screen, theme.SURFACE_ALT, badge, 15)
            pygame.draw.circle(screen, theme.BORDER, badge, 15, 1)
            num = theme.font(theme.FONT_SM, bold=True).render(str(i + 1), True, theme.TEXT_SECONDARY)
            screen.blit(num, num.get_rect(center=badge))
            font = mono(22, bold=True)
            lines = self._wrap_chars(password, font, rect.width - 40)
            ty = rect.y + (54 if reveal else rect.height // 2 - len(lines) * (font.get_linesize() + 2) // 2)
            for line in lines:
                surf = font.render(line, True, theme.TEXT_PRIMARY)
                screen.blit(surf, surf.get_rect(midtop=(rect.centerx, ty)))
                ty += font.get_linesize() + 2
            if reveal:
                self._draw_reveal_info(screen, rect, rnd, i)
            else:
                hint = theme.font(12).render("нажмите, чтобы выбрать", True, theme.ACCENT if hovered else theme.TEXT_MUTED)
                screen.blit(hint, hint.get_rect(midbottom=(rect.centerx, rect.bottom - 14)))
                self._card_rects.append((rect, i))
        if reveal:
            lesson = pygame.Rect(c.x, c.y + 106 + card_h + 14, c.width, c.bottom - (c.y + 106 + card_h + 14) - 58)
            theme.draw_panel(screen, lesson, radius=theme.RADIUS_MD, shadow=False)
            pygame.draw.rect(screen, theme.ACCENT, (lesson.x, lesson.y + 8, 4, lesson.height - 16), border_radius=2)
            screen.blit(theme.font(theme.FONT_SM, bold=True).render("Урок", True, theme.ACCENT), (lesson.x + 18, lesson.y + 8))
            for j, line in enumerate(wrap_lines(rnd["lesson"], theme.font(theme.FONT_SM), lesson.width - 40)):
                screen.blit(theme.font(theme.FONT_SM).render(line, True, theme.TEXT_PRIMARY), (lesson.x + 18, lesson.y + 34 + j * 22))
            self.next_button.text = "К итогам" if ch.index + 1 >= ch.total else "Дальше"
            locked = self._now() - self.reveal_since < 300
            self.next_button.draw(screen, disabled=locked)
        else:
            hint = theme.font(theme.FONT_XS).render("Кликните по паролю или нажмите 1, 2, 3", True, theme.TEXT_MUTED)
            screen.blit(hint, hint.get_rect(midtop=(c.centerx, c.y + 106 + card_h + 18)))
            tip = ("Смотрите на длину, на слова из словаря, на шаблоны и замены букв. "
                   "Верный ответ определяет тот же оценщик, что и в анализаторе.")
            for j, line in enumerate(wrap_lines(tip, theme.font(theme.FONT_XS), c.width - 60)):
                surf = theme.font(theme.FONT_XS).render(line, True, theme.TEXT_SECONDARY)
                screen.blit(surf, surf.get_rect(midtop=(c.centerx, c.y + 106 + card_h + 48 + j * 20)))

    @classmethod
    def _wrap_phrase(cls, text, font, width):
        """Перенос фразы по разделителям (дефис, точка, подчёркивание, пробел), а если не помещается, то по символам."""
        tokens = re.findall(r"[^-._ ]+[-._ ]?|[-._ ]", text)
        lines, current = [], ""
        for token in tokens:
            if font.size(current + token)[0] <= width:
                current += token
                continue
            if current:
                lines.append(current)
                current = ""
            if font.size(token)[0] > width:
                pieces = cls._wrap_chars(token, font, width)
                lines.extend(pieces[:-1])
                current = pieces[-1]
            else:
                current = token
        if current:
            lines.append(current)
        return lines or [""]

    @staticmethod
    def _wrap_chars(text, font, width):
        lines, current = [], ""
        for ch in text:
            if font.size(current + ch)[0] > width and current:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return lines

    def _draw_reveal_info(self, screen, rect, rnd, index):
        analysis = rnd["analyses"][index]
        y = rect.bottom - 92
        pygame.draw.line(screen, theme.BORDER_SOFT, (rect.x + 16, y - 8), (rect.right - 16, y - 8))
        bits = theme.font(theme.FONT_SM, bold=True).render(_bits_text(analysis["bits"]), True, SCORE_COLORS[analysis["score"]])
        screen.blit(bits, (rect.x + 20, y))
        seconds = analysis["times"][3][1]
        label = theme.font(theme.FONT_XS).render("MD5 на видеокартах:", True, theme.TEXT_MUTED)
        screen.blit(label, (rect.x + 20, y + 26))
        value = theme.font(theme.FONT_XS, bold=True).render(format_duration(seconds), True, _time_color(seconds))
        screen.blit(value, (rect.x + 24 + label.get_width(), y + 26))
        kinds = []
        for part in analysis["parts"]:
            if part.kind not in kinds:
                kinds.append(part.kind)
        text = ", ".join(KIND_LABELS[k] for k in kinds[:3])
        surf = theme.font(12).render(text if len(text) < 44 else text[:41] + "...", True, theme.TEXT_SECONDARY)
        screen.blit(surf, (rect.x + 20, y + 50))
        if index == rnd["best"]:
            theme.draw_badge(screen, (rect.right - 76, rect.y + 26), "Самый стойкий", fg=theme.TEXT_ON_ACCENT, bg=theme.SUCCESS, font_size=12)
        elif index == self.challenge_result.chosen:
            theme.draw_badge(screen, (rect.right - 60, rect.y + 26), "Ваш выбор", fg=theme.TEXT_ON_ACCENT, bg=theme.DANGER, font_size=12)

    def _draw_challenge_final(self, screen, c):
        ch = self.challenge
        panel = pygame.Rect(0, 0, min(760, c.width), 470)
        panel.midtop = (c.centerx, c.y + 6)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        rank, color = next((name, col) for threshold, name, col in CHALLENGE_RANKS if ch.correct_count >= threshold)
        screen.blit(theme.font(theme.FONT_MD).render("Испытание пройдено", True, theme.TEXT_SECONDARY), (panel.x + 40, panel.y + 26))
        title = theme.font(theme.FONT_XXL, bold=True).render(rank, True, color)
        screen.blit(title, (panel.x + 40, panel.y + 58))
        center = (panel.x + 40 + 72, panel.y + 190)
        draw_ring(screen, center, 62, 12, ch.correct_count / ch.total, color)
        n = theme.font(theme.FONT_XXL, bold=True).render(f"{ch.correct_count}/{ch.total}", True, theme.TEXT_PRIMARY)
        screen.blit(n, n.get_rect(center=center))
        x = panel.x + 40 + 170
        screen.blit(theme.font(theme.FONT_MD, bold=True).render(f"Очки: {ch.score} из {ch.max_score}", True, theme.WARNING), (x, panel.y + 140))
        if self.challenge_new_best:
            theme.draw_badge(screen, (x + 250, panel.y + 152), "Новый рекорд", fg=theme.TEXT_ON_ACCENT, bg=theme.WARNING)
        wrong = [i for i, r in enumerate(ch.results) if not r.correct]
        if wrong:
            screen.blit(theme.font(theme.FONT_SM, bold=True).render("Стоит повторить уроки:", True, theme.ACCENT), (x, panel.y + 178))
            for j, i in enumerate(wrong[:4]):
                lesson = ch.rounds[i]["lesson"].split(".")[0] + "."
                lesson = lesson if len(lesson) < 76 else lesson[:73] + "..."
                screen.blit(theme.font(theme.FONT_XS).render(f"Раунд {i + 1}: {lesson}", True, theme.TEXT_SECONDARY), (x, panel.y + 206 + j * 22))
        else:
            screen.blit(theme.font(theme.FONT_SM).render("Все ответы верны. Вы отлично чувствуете, что делает пароль стойким.", True, theme.SUCCESS), (x, panel.y + 184))
        if self.challenge_new_achievements:
            surf = theme.font(theme.FONT_SM, bold=True).render("Достижение: " + ", ".join(self.challenge_new_achievements), True, theme.WARNING)
            screen.blit(surf, surf.get_rect(center=(panel.centerx, panel.y + 330)))
        self.again_button.rect.topleft = (panel.centerx - 232, panel.y + 380)
        self.to_analyzer_button.rect.topleft = (panel.centerx + 12, panel.y + 380)
        self.again_button.draw(screen)
        self.to_analyzer_button.draw(screen)

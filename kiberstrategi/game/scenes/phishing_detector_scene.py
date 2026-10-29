# Режим «Фишинг-детектор»: настоящее сообщение или подделка? Вступление, раунд
# из 10 сообщений с таймером, разбор улик после каждого ответа и итоги.
import math
import random

import pygame

from ..core import achievements, sound_manager
from ..core.phishing_detector import (
    PhishingSession, ROUND_SIZE, TIME_LIMIT_SECONDS, POINTS_PER_CORRECT, rank_for_percent,
)
from ..data.phishing_messages import MESSAGES, CATEGORIES, CATEGORY_TIPS
from ..ui import theme
from ..ui.button import Button
from ..ui.widgets import draw_ring
from ..ui.message_mockup import draw_message, draw_clue_markers, wrap_text

MARGIN = 40
FEEDBACK_LOCK_MS = 350
RESULT_ANIM_FRAMES = 50

CHECKLIST = [
    ("Отправитель", "Совпадает ли домен с официальным?"),
    ("Ссылка", "Куда она ведёт на самом деле?"),
    ("Давление", "Нет ли срочности, угроз и дедлайнов?"),
    ("Запрос", "Не просят ли пароль, код или деньги?"),
    ("Вложение", "Какое у файла расширение целиком?"),
]

VERDICTS = {
    "correct_phishing": ("Верно! Это фишинг", "Вы заметили подделку. Ниже видно, по каким признакам."),
    "correct_safe": ("Верно! Сообщение безопасно", "Не каждое письмо с ссылкой опасно. Вот почему этому можно доверять."),
    "missed": ("Пропущен фишинг", "Вы решили, что сообщение безопасно, но это подделка. Вот что должно было насторожить."),
    "false_alarm": ("Ложная тревога", "Сообщение настоящее. Лишняя подозрительность тоже мешает работать. Вот признаки, что ему можно верить."),
    "timeout": ("Время вышло", "В реальной жизни спешка тоже работает на мошенника. Разбор ниже."),
}
MISTAKE_LABELS = {"missed": "пропущен фишинг", "false_alarm": "ложная тревога", "timeout": "не успели"}
TAG_COLORS = {"success": theme.SUCCESS, "warning": theme.WARNING, "danger": theme.DANGER}


def _short_title(message, limit=44):
    if message["channel"] == "email":
        text = f"Письмо: {message['subject']}"
    elif message["channel"] == "sms":
        text = f"SMS от {message['sender_name']}"
    else:
        text = f"Чат: {message['sender_name']}"
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _draw_envelope(screen, center, width=104, height=68):
    body = pygame.Rect(0, 0, width, height)
    body.center = center
    pygame.draw.rect(screen, theme.SURFACE_ALT, body, border_radius=theme.RADIUS_MD)
    pygame.draw.rect(screen, theme.ACCENT, body, 2, border_radius=theme.RADIUS_MD)
    pygame.draw.lines(screen, theme.ACCENT, False,
                      [(body.left + 4, body.top + 6), body.center, (body.right - 4, body.top + 6)], 2)
    tri_center = (body.right - 6, body.bottom - 4)
    tri = [(tri_center[0], tri_center[1] - 26), (tri_center[0] - 24, tri_center[1] + 14), (tri_center[0] + 24, tri_center[1] + 14)]
    pygame.draw.polygon(screen, theme.DANGER, tri)
    pygame.draw.polygon(screen, theme.BG, tri, 2)
    mark = theme.font(theme.FONT_MD, bold=True).render("!", True, theme.TEXT_ON_ACCENT)
    screen.blit(mark, mark.get_rect(center=(tri_center[0], tri_center[1] + 2)))


class PhishingDetectorScene:
    def __init__(self, screen_width, screen_height, save_manager, on_back, rng=None, time_fn=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.save_manager = save_manager
        self.on_back = on_back
        self._rng = rng or random.Random()
        self._now = time_fn or pygame.time.get_ticks

        self.state = "intro"
        self.session = None
        self.message_started = 0
        self.feedback_since = 0
        self.last_result = None
        self.hotspots = {}
        self.panel_scroll = 0
        self._panel_max_scroll = 0
        self.result_frame = 0
        self.result_new_best = False
        self.result_new_achievements = []

        self.f_title = theme.font(theme.FONT_TITLE, bold=True)
        self.f_xxl = theme.font(theme.FONT_XXL, bold=True)
        self.f_xl = theme.font(theme.FONT_XL, bold=True)
        self.f_lg = theme.font(theme.FONT_LG, bold=True)
        self.f_md = theme.font(theme.FONT_MD)
        self.f_md_b = theme.font(theme.FONT_MD, bold=True)
        self.f_sm = theme.font(theme.FONT_SM)
        self.f_sm_b = theme.font(theme.FONT_SM, bold=True)
        self.f_xs = theme.font(theme.FONT_XS)

        big = theme.font(theme.FONT_LG, bold=True)
        self.phish_button = Button(0, 0, 300, 58, "Это фишинг", (150, 55, 55), lambda: self.submit("phishing"), font=big)
        self.safe_button = Button(0, 0, 300, 58, "Безопасно", (25, 120, 90), lambda: self.submit("safe"), font=big)
        self.next_button = Button(0, 0, 300, 58, "Далее", theme.ACCENT_DIM, self.next_message, font=big)
        self.exit_button = Button(0, 0, 110, 32, "Выйти", theme.SURFACE_ALT, self.to_intro)
        self.start_button = Button(0, 0, 320, 58, "Начать раунд", (25, 120, 90), self.start_round, font=big)
        self.back_button = Button(0, 0, 120, 35, "Назад", theme.SURFACE_ALT, self.on_back)
        self.again_button = Button(0, 0, 250, 52, "Сыграть ещё", (25, 120, 90), self.start_round, font=big)
        self.menu_button = Button(0, 0, 200, 52, "В меню", theme.SURFACE_ALT, self.on_back, font=big)
        self._place_buttons()

    # ------------------------------------------------------------ раскладка
    def _layout(self):
        w, h = self.screen_width, self.screen_height
        right_w = 456 if w >= 1150 else max(300, int(w * 0.36))
        card = pygame.Rect(MARGIN, 100, w - 2 * MARGIN - right_w - 24, h - 100 - 130)
        panel = pygame.Rect(card.right + 24, card.y, right_w, card.height)
        return card, panel

    def _place_buttons(self):
        w, h = self.screen_width, self.screen_height
        card, _ = self._layout()
        row_y = h - 104
        self.phish_button.rect.topleft = (card.centerx - 310, row_y)
        self.safe_button.rect.topleft = (card.centerx + 10, row_y)
        self.next_button.rect.topleft = (card.centerx - 150, row_y)
        self.exit_button.rect.topleft = (w - MARGIN - 110, 14)
        self.back_button.rect.topleft = (30, h - 55)
        panel_w, panel_h = self._intro_panel_size()
        px, py = (w - panel_w) // 2, (h - panel_h) // 2
        self.start_button.rect.topleft = (w // 2 - 160, py + panel_h - 92)
        rp = self._result_panel()
        self.again_button.rect.topleft = (rp.centerx - 262, rp.bottom - 72)
        self.menu_button.rect.topleft = (rp.centerx + 12, rp.bottom - 72)

    def _intro_panel_size(self):
        return min(820, self.screen_width - 60), min(580, self.screen_height - 60)

    def _result_panel(self):
        w, h = self.screen_width, self.screen_height
        pw, ph = min(880, w - 60), min(650, h - 50)
        return pygame.Rect((w - pw) // 2, (h - ph) // 2, pw, ph)

    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h
        self._place_buttons()

    # ------------------------------------------------------------ переходы
    def to_intro(self):
        self.state = "intro"
        self.session = None

    def start_round(self):
        self.session = PhishingSession(MESSAGES, rng=self._rng)
        self.result_new_achievements = []
        self._begin_message()

    def _begin_message(self):
        self.state = "playing"
        self.message_started = self._now()
        self.last_result = None
        self.hotspots = {}
        self.panel_scroll = 0

    def elapsed(self):
        return (self._now() - self.message_started) / 1000.0

    def submit(self, choice):
        if self.state != "playing":
            return
        elapsed = self.elapsed()
        self.last_result = self.session.answer(choice, min(elapsed, TIME_LIMIT_SECONDS))
        sound_manager.play("correct" if self.last_result.correct else "wrong")
        self.state = "feedback"
        self.feedback_since = self._now()
        self.panel_scroll = 0

    def next_message(self):
        if self.state != "feedback" or self._now() - self.feedback_since < FEEDBACK_LOCK_MS:
            return
        self.session.advance()
        if self.session.finished:
            self._finish_round()
        else:
            self._begin_message()

    def _finish_round(self):
        session = self.session
        self.result_new_best = self.save_manager.record_phishing_round(session.score)
        ids = achievements.evaluate_phishing_round(session, self.save_manager.phishing_rounds)
        new_ids = self.save_manager.unlock_achievements(ids)
        self.result_new_achievements = [achievements.ACHIEVEMENTS[a]["title"] for a in new_ids]
        self.result_frame = 0
        self.state = "result"
        sound_manager.play("success" if session.percent >= 80 else ("correct" if session.percent >= 50 else "wrong"))

    # ------------------------------------------------------------ события
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event.key)
        if event.type == pygame.MOUSEWHEEL and self.state == "feedback":
            self.panel_scroll = max(0, min(self.panel_scroll - event.y * 30, self._panel_max_scroll))
            return True
        if self.state == "intro":
            return self.start_button.handle_event(event) or self.back_button.handle_event(event)
        if self.state == "playing":
            return (self.phish_button.handle_event(event) or self.safe_button.handle_event(event)
                    or self.exit_button.handle_event(event))
        if self.state == "feedback":
            locked = self._now() - self.feedback_since < FEEDBACK_LOCK_MS
            return self.next_button.handle_event(event, disabled=locked) or self.exit_button.handle_event(event)
        if self.state == "result":
            return self.again_button.handle_event(event) or self.menu_button.handle_event(event)
        return False

    def _handle_key(self, key):
        if self.state == "intro":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_round()
                return True
            if key == pygame.K_ESCAPE:
                self.on_back()
                return True
        elif self.state == "playing":
            if key in (pygame.K_LEFT, pygame.K_a):
                self.submit("phishing")
                return True
            if key in (pygame.K_RIGHT, pygame.K_d):
                self.submit("safe")
                return True
        elif self.state == "feedback":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.next_message()
                return True
        elif self.state == "result":
            if key == pygame.K_RETURN:
                self.start_round()
                return True
            if key == pygame.K_ESCAPE:
                self.on_back()
                return True
        return False

    def update(self):
        for button in (self.phish_button, self.safe_button, self.next_button, self.exit_button,
                       self.start_button, self.back_button, self.again_button, self.menu_button):
            button.update()
        if self.state == "playing" and self.elapsed() >= TIME_LIMIT_SECONDS:
            self.submit(None)
        if self.state == "result" and self.result_frame < RESULT_ANIM_FRAMES:
            self.result_frame += 1

    # ------------------------------------------------------------ отрисовка
    def draw(self, screen):
        screen.fill(theme.BG)
        if self.state == "intro":
            self._draw_intro(screen)
        elif self.state == "result":
            self._draw_result(screen)
        else:
            self._draw_round(screen)

    def _draw_intro(self, screen):
        w, h = self.screen_width, self.screen_height
        pw, ph = self._intro_panel_size()
        panel = pygame.Rect((w - pw) // 2, (h - ph) // 2, pw, ph)
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)

        _draw_envelope(screen, (panel.centerx, panel.y + 62))
        title = self.f_title.render("Фишинг-детектор", True, theme.TEXT_PRIMARY)
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 114))
        sub = self.f_md.render("Настоящее сообщение или подделка? Решайте быстро и по фактам.", True, theme.TEXT_SECONDARY)
        screen.blit(sub, (panel.centerx - sub.get_width() // 2, panel.y + 168))

        rules = [
            (str(ROUND_SIZE), "сообщений в раунде: письма, SMS и чаты"),
            (f"{TIME_LIMIT_SECONDS} с", "на решение по каждому сообщению"),
            (f"+{POINTS_PER_CORRECT}", "очков за верный ответ, ошибка сбрасывает серию"),
        ]
        gap = 14
        card_w = (panel.width - 80 - 2 * gap) // 3
        for i, (big, caption) in enumerate(rules):
            rect = pygame.Rect(panel.x + 40 + i * (card_w + gap), panel.y + 212, card_w, 122)
            pygame.draw.rect(screen, theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, theme.BORDER, rect, 1, border_radius=theme.RADIUS_MD)
            big_surf = self.f_xxl.render(big, True, theme.ACCENT)
            screen.blit(big_surf, (rect.centerx - big_surf.get_width() // 2, rect.y + 12))
            for j, line in enumerate(wrap_text(caption, self.f_xs, rect.width - 24)):
                surf = self.f_xs.render(line, True, theme.TEXT_SECONDARY)
                screen.blit(surf, (rect.centerx - surf.get_width() // 2, rect.y + 62 + j * 20))

        tip = self.f_sm.render("Наводите курсор на отправителя и ссылку: настоящий адрес виден только так.", True, theme.TEXT_SECONDARY)
        screen.blit(tip, (panel.centerx - tip.get_width() // 2, panel.y + 352))

        best = self.save_manager.phishing_best
        rounds = self.save_manager.phishing_rounds
        stats = self.f_sm_b.render(f"Лучший результат: {best} из 100   ·   Сыграно раундов: {rounds}", True, theme.WARNING)
        screen.blit(stats, (panel.centerx - stats.get_width() // 2, panel.y + 392))

        self.start_button.draw(screen)
        keys = self.f_xs.render("Клавиши: Пробел или Enter, чтобы начать", True, theme.TEXT_MUTED)
        screen.blit(keys, (panel.centerx - keys.get_width() // 2, panel.bottom - 24))
        self.back_button.draw(screen)

    def _draw_round(self, screen):
        session = self.session
        w, h = self.screen_width, self.screen_height
        card, panel = self._layout()
        message = session.current
        feedback = self.state == "feedback"

        # Шапка: название, серия, очки и выход
        title = self.f_lg.render("Фишинг-детектор", True, theme.TEXT_PRIMARY)
        screen.blit(title, (MARGIN, 16))
        badge_x = self.exit_button.rect.x - 16
        for text, color in ((f"Очки: {session.score}", theme.WARNING), (f"Серия: {session.streak}", theme.ACCENT)):
            badge_w = theme.font(theme.FONT_SM, bold=True).size(text)[0] + 20
            rect = theme.draw_badge(screen, (badge_x - badge_w // 2, 30), text, fg=color, bg=theme.SURFACE_ALT, font_size=theme.FONT_SM)
            badge_x = rect.left - 12
        self.exit_button.draw(screen)

        # Таймер
        bar = pygame.Rect(MARGIN, 58, w - 2 * MARGIN - 70, 8)
        pygame.draw.rect(screen, theme.SURFACE_ALT, bar, border_radius=4)
        if feedback:
            spent = min(self.last_result.elapsed, TIME_LIMIT_SECONDS)
            fraction = 1 - spent / TIME_LIMIT_SECONDS
            color = theme.BORDER
            label = "время" if self.last_result.kind == "timeout" else f"{spent:.1f} с".replace(".", ",")
        else:
            remaining = max(0.0, TIME_LIMIT_SECONDS - self.elapsed())
            fraction = remaining / TIME_LIMIT_SECONDS
            color = theme.SUCCESS if fraction > 0.5 else (theme.WARNING if fraction > 0.25 else theme.DANGER)
            label = f"0:{int(math.ceil(remaining)):02d}"
        fill = bar.copy()
        fill.width = int(bar.width * max(0.0, fraction))
        if fill.width > 0:
            pygame.draw.rect(screen, color, fill, border_radius=4)
        label_surf = self.f_sm_b.render(label, True, theme.TEXT_SECONDARY if feedback else color)
        screen.blit(label_surf, (bar.right + 12, bar.centery - label_surf.get_height() // 2))

        # Точки прогресса
        for i in range(session.total):
            cx = MARGIN + 6 + i * 20
            if i < len(session.results) and (i < session.index or feedback):
                ok = session.results[i].correct
                pygame.draw.circle(screen, theme.SUCCESS if ok else theme.DANGER, (cx, 82), 6)
            elif i == session.index:
                pygame.draw.circle(screen, theme.ACCENT, (cx, 82), 7)
            else:
                pygame.draw.circle(screen, theme.BORDER, (cx, 82), 6, 1)
        counter = self.f_xs.render(f"Сообщение {session.index + 1} из {session.total}", True, theme.TEXT_MUTED)
        screen.blit(counter, (MARGIN + session.total * 20 + 8, 74))

        # Сообщение
        mouse = pygame.mouse.get_pos()
        self.hotspots, _ = draw_message(screen, card, message, mouse_pos=mouse, reveal=feedback)
        if feedback:
            draw_clue_markers(screen, self.hotspots, message["clues"], message["is_phishing"])
            self._draw_feedback_panel(screen, panel)
            self.next_button.text = "Итоги раунда" if session.is_last else "Далее"
            locked = self._now() - self.feedback_since < FEEDBACK_LOCK_MS
            self.next_button.draw(screen, disabled=locked)
            keys = "Пробел или Enter: дальше"
        else:
            self._draw_checklist(screen, panel)
            self.phish_button.draw(screen)
            self.safe_button.draw(screen)
            keys = "Клавиши: стрелка влево или A: фишинг, стрелка вправо или D: безопасно"
        keys_surf = self.f_xs.render(keys, True, theme.TEXT_MUTED)
        screen.blit(keys_surf, (card.centerx - keys_surf.get_width() // 2, h - 34))

    def _draw_checklist(self, screen, panel):
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        heading = self.f_md_b.render("Памятка детектива", True, theme.ACCENT)
        screen.blit(heading, (panel.x + 24, panel.y + 20))
        theme.draw_divider(screen, panel.x + 24, panel.y + 54, panel.width - 48)
        y = panel.y + 70
        for title, text in CHECKLIST:
            pygame.draw.circle(screen, theme.ACCENT, (panel.x + 32, y + 11), 5)
            screen.blit(self.f_sm_b.render(title, True, theme.TEXT_PRIMARY), (panel.x + 50, y))
            for j, line in enumerate(wrap_text(text, self.f_sm, panel.width - 80)):
                screen.blit(self.f_sm.render(line, True, theme.TEXT_SECONDARY), (panel.x + 50, y + 24 + j * 20))
            y += 74
        note = "Иногда всё выглядит безопасно. Тогда верное решение: пропустить."
        for j, line in enumerate(wrap_text(note, self.f_xs, panel.width - 48)):
            screen.blit(self.f_xs.render(line, True, theme.TEXT_MUTED), (panel.x + 24, panel.bottom - 56 + j * 18))

    def _draw_feedback_panel(self, screen, panel):
        result = self.last_result
        message = result.message
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)

        if result.kind == "correct":
            key = "correct_phishing" if message["is_phishing"] else "correct_safe"
        else:
            key = result.kind
        head, sub = VERDICTS[key]
        good = result.correct
        banner_h = 96
        banner = pygame.Rect(panel.x + 14, panel.y + 14, panel.width - 28, banner_h)
        pygame.draw.rect(screen, theme.SUCCESS_DIM if good else theme.DANGER_DIM, banner, border_radius=theme.RADIUS_MD)
        pygame.draw.rect(screen, theme.SUCCESS if good else theme.DANGER, banner, 1, border_radius=theme.RADIUS_MD)
        icon_center = (banner.x + 30, banner.y + 30)
        if good:
            theme.draw_check(screen, icon_center, size=10, color=theme.SUCCESS, width=4)
        else:
            theme.draw_cross(screen, icon_center, size=9, color=theme.DANGER, width=4)
        screen.blit(self.f_md_b.render(head, True, theme.TEXT_PRIMARY), (banner.x + 56, banner.y + 16))
        for j, line in enumerate(wrap_text(sub, self.f_xs, banner.width - 32)[:3]):
            screen.blit(self.f_xs.render(line, True, theme.TEXT_SECONDARY), (banner.x + 16, banner.y + 50 + j * 17))

        heading_text = "Красные флаги" if message["is_phishing"] else "Почему это безопасно"
        heading = self.f_sm_b.render(heading_text, True, theme.DANGER if message["is_phishing"] else theme.SUCCESS)
        screen.blit(heading, (panel.x + 24, banner.bottom + 12))

        viewport = pygame.Rect(panel.x + 8, banner.bottom + 40, panel.width - 16, panel.bottom - banner.bottom - 48)
        prev_clip = screen.get_clip()
        screen.set_clip(viewport)
        marker_color = theme.DANGER if message["is_phishing"] else theme.SUCCESS
        y = viewport.y - self.panel_scroll
        text_w = panel.width - 78
        for number, clue in enumerate(message["clues"], start=1):
            pygame.draw.circle(screen, marker_color, (panel.x + 34, y + 12), 11)
            num = self.f_xs.render(str(number), True, theme.TEXT_ON_ACCENT)
            screen.blit(num, num.get_rect(center=(panel.x + 34, y + 12)))
            screen.blit(self.f_sm_b.render(clue["title"], True, theme.TEXT_PRIMARY), (panel.x + 56, y + 2))
            lines = wrap_text(clue["explain"], self.f_xs, text_w)
            for j, line in enumerate(lines):
                screen.blit(self.f_xs.render(line, True, theme.TEXT_SECONDARY), (panel.x + 56, y + 28 + j * 18))
            y += 28 + len(lines) * 18 + 14
        screen.set_clip(prev_clip)
        content_h = y + self.panel_scroll - viewport.y
        self._panel_max_scroll = max(0, content_h - viewport.height)
        if self._panel_max_scroll > 0:
            hint = self.f_xs.render("прокрутите колесом мыши", True, theme.TEXT_MUTED)
            screen.blit(hint, (panel.right - hint.get_width() - 20, panel.bottom - 22))

    def _draw_result(self, screen):
        session = self.session
        panel = self._result_panel()
        theme.draw_panel(screen, panel, radius=theme.RADIUS_LG)
        tag, rank_title, rank_desc = rank_for_percent(session.percent)
        color = TAG_COLORS[tag]
        progress = min(1.0, self.result_frame / RESULT_ANIM_FRAMES)
        eased = 1 - (1 - progress) ** 3

        head = self.f_md.render("Раунд завершён", True, theme.TEXT_SECONDARY)
        screen.blit(head, (panel.x + 30, panel.y + 20))

        center = (panel.x + 30 + 84, panel.y + 132)
        draw_ring(screen, center, 68, 13, session.percent / 100 * eased, color)
        pct = self.f_xl.render(f"{int(session.percent * eased)}%", True, theme.TEXT_PRIMARY)
        screen.blit(pct, pct.get_rect(center=(center[0], center[1] - 6)))
        small = self.f_xs.render("точность", True, theme.TEXT_MUTED)
        screen.blit(small, small.get_rect(center=(center[0], center[1] + 20)))

        tx = panel.x + 30 + 84 * 2 + 36
        screen.blit(self.f_xxl.render(rank_title, True, color), (tx, panel.y + 60))
        for j, line in enumerate(wrap_text(rank_desc, self.f_sm, panel.right - tx - 30)):
            screen.blit(self.f_sm.render(line, True, theme.TEXT_SECONDARY), (tx, panel.y + 108 + j * 22))
        score_text = self.f_md_b.render(f"Очки: {int(session.score * eased)} из {session.max_score}", True, theme.WARNING)
        screen.blit(score_text, (tx, panel.y + 178))
        if self.result_new_best and progress >= 1:
            theme.draw_badge(screen, (tx + score_text.get_width() + 84, panel.y + 190), "Новый рекорд", fg=theme.TEXT_ON_ACCENT, bg=theme.WARNING)

        tiles = [
            ("Верно", f"{session.correct_count} из {session.total}", theme.SUCCESS),
            ("Пропущено фишингов", str(session.missed_count), theme.DANGER),
            ("Ложных тревог", str(session.false_alarm_count), theme.WARNING),
            ("Лучшая серия", str(session.best_streak), theme.ACCENT),
        ]
        gap = 12
        tile_w = (panel.width - 60 - 3 * gap) // 4
        tile_y = panel.y + 224
        for i, (label, value, tile_color) in enumerate(tiles):
            rect = pygame.Rect(panel.x + 30 + i * (tile_w + gap), tile_y, tile_w, 72)
            pygame.draw.rect(screen, theme.SURFACE_ALT, rect, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, tile_color, (rect.x, rect.y, 4, rect.height),
                             border_top_left_radius=theme.RADIUS_MD, border_bottom_left_radius=theme.RADIUS_MD)
            screen.blit(self.f_xl.render(value, True, theme.TEXT_PRIMARY), (rect.x + 18, rect.y + 8))
            screen.blit(self.f_xs.render(label, True, theme.TEXT_SECONDARY), (rect.x + 18, rect.y + 46))

        y = tile_y + 72 + 14
        avg = session.average_time
        if avg is not None:
            avg_text = f"Среднее время ответа: {avg:.1f} с".replace(".", ",")
            if session.timeout_count:
                avg_text += f"   ·   Не успели: {session.timeout_count}"
            screen.blit(self.f_xs.render(avg_text, True, theme.TEXT_MUTED), (panel.x + 30, y))
            y += 26

        weak = session.weakest_category()
        if weak:
            box = pygame.Rect(panel.x + 30, y, panel.width - 60, 74)
            pygame.draw.rect(screen, theme.WARNING_DIM, box, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, theme.WARNING, box, 1, border_radius=theme.RADIUS_MD)
            screen.blit(self.f_sm_b.render(f"Слабое место: {CATEGORIES[weak]}", True, theme.WARNING), (box.x + 16, box.y + 10))
            for j, line in enumerate(wrap_text(CATEGORY_TIPS[weak], self.f_xs, box.width - 32)[:2]):
                screen.blit(self.f_xs.render(line, True, theme.TEXT_PRIMARY), (box.x + 16, box.y + 36 + j * 18))
            y = box.bottom + 14

        buttons_y = self.again_button.rect.y
        screen.blit(self.f_sm_b.render("Разбор ошибок", True, theme.ACCENT), (panel.x + 30, y))
        y += 28
        ach_space = 26 if self.result_new_achievements else 0
        max_rows = max(1, (buttons_y - 12 - ach_space - y) // 24)
        mistakes = session.mistakes
        if not mistakes:
            screen.blit(self.f_sm.render("Ошибок нет. Ни одна подделка не прошла.", True, theme.SUCCESS), (panel.x + 30, y))
        else:
            for result in mistakes[:max_rows]:
                dot = theme.DANGER if result.kind == "missed" else theme.WARNING
                pygame.draw.circle(screen, dot, (panel.x + 38, y + 10), 5)
                text = f"{_short_title(result.message)}: {MISTAKE_LABELS[result.kind]}"
                screen.blit(self.f_sm.render(text, True, theme.TEXT_SECONDARY), (panel.x + 54, y))
                y += 24
            hidden = len(mistakes) - max_rows
            if hidden > 0:
                screen.blit(self.f_xs.render(f"и ещё {hidden}", True, theme.TEXT_MUTED), (panel.x + 54, y))

        if self.result_new_achievements:
            text = "Новые достижения: " + ", ".join(self.result_new_achievements)
            surf = self.f_sm_b.render(text, True, theme.WARNING)
            screen.blit(surf, (panel.centerx - surf.get_width() // 2, buttons_y - 30))

        self.again_button.draw(screen)
        self.menu_button.draw(screen)

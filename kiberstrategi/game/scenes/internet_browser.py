# [file name]: internet_browser.py
# [file content begin]
import re
import pygame
from ..ui.button import Button


def _normalize_query(s: str) -> str:
    """Убирает спецсимволы (/, \\, -, и т.д.), оставляет буквы, цифры и пробелы."""
    s = s.strip().lower()
    s = re.sub(r"[\s/\\.,_;:!?*#\-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Транслитерация кириллица → латиница: сначала двухбуквенные, потом однобуквенные
_TRANSLIT_PAIRS = [
    ("щ", "sch"), ("ч", "ch"), ("ш", "sh"), ("ж", "zh"), ("ю", "yu"), ("я", "ya"),
    ("ц", "ts"), ("ы", "y"), ("э", "e"), ("й", "y"), ("ъ", ""), ("ь", ""),
]
_cyr = "абвгдеёзиклмнопрстуфхиії"
_lat = "abvgdeeziyklmnoprstufhii"  # 24 символа (и, і, ї -> i, i, i по позициям)
_CYRILLIC_TO_LATIN = str.maketrans(_cyr, _lat)


def _transliterate_cyrillic_to_latin(word: str) -> str:
    """Переводит слово из кириллицы в латиницу (сием→siem, митре→mitre)."""
    if not word:
        return word
    w = word.lower()
    for cyr, lat in _TRANSLIT_PAIRS:
        w = w.replace(cyr, lat)
    w = w.translate(_CYRILLIC_TO_LATIN)
    return w


def _has_cyrillic(s: str) -> bool:
    return bool(s) and any("\u0400" <= c <= "\u04ff" for c in s)


def _levenshtein(a: str, b: str) -> int:
    """Расстояние Левенштейна между строками (допуск опечаток)."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    n, m = len(a), len(b)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[m]


def _fuzzy_match(query: str, keyword: str, max_edits: int = 2, ratio_threshold: float = 0.75) -> bool:
    """True, если запрос совпадает с ключом с учётом небольших опечаток."""
    if not query or not keyword:
        return False
    if query in keyword or keyword in query:
        return True
    dist = _levenshtein(query, keyword)
    max_len = max(len(query), len(keyword))
    if max_len <= 4:
        return dist <= 1
    if dist <= max_edits:
        return True
    return (1 - dist / max_len) >= ratio_threshold


# Синонимы только там, где транслитерация не даёт совпадения: падежи и loanwords (аккаунты→accounts)
_WORD_ALIASES = {
    "учетные": "учетных", "записи": "записей", "защиты": "защита", "защ": "защита",
    "мониторинга": "мониторинг", "компрометации": "компрометация",
    "кибербезопасности": "кибербезопасность", "кибер": "кибербезопасность",
    "akkaunty": "accounts", "akkaunt": "accounts", "akkaunts": "accounts",
}


def _normalize_word_for_match(w: str) -> str:
    """Единый вид для сравнения: убираем &, ё→е, кириллицу переводим в латиницу, затем синонимы."""
    if not w:
        return w
    w = w.lower().replace("&", "").replace("ё", "е")
    if _has_cyrillic(w):
        w = _transliterate_cyrillic_to_latin(w)
    return _WORD_ALIASES.get(w, w)


def _word_matches(q: str, k: str) -> bool:
    """Одно слово запроса совпадает с словом ключа (вхождение или опечатка)."""
    if not q or not k:
        return False
    q = _normalize_word_for_match(q)
    k = _normalize_word_for_match(k)
    if q in k or k in q:
        return True
    if len(q) >= 2 and k.startswith(q):
        return True
    if len(k) >= 2 and q.startswith(k):
        return True
    return _fuzzy_match(q, k)


def _query_matches_keyword(query: str, keyword: str) -> bool:
    """True, если запрос совпадает с ключом: целиком или по словам (фиш/защ -> фишинг защита)."""
    query = _normalize_query(query)
    keyword = keyword.strip().lower()
    if not query:
        return False
    if query in keyword or keyword in query:
        return True
    if _fuzzy_match(query, keyword):
        return True
    qwords = [w for w in query.split() if w]
    kwords = [w for w in keyword.split() if w]
    if not qwords:
        return False
    for qw in qwords:
        if any(_word_matches(qw, kw) for kw in kwords):
            continue
        return False
    return True


class InternetBrowser:
    def __init__(self, screen_width, screen_height, on_complete_callback):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_complete = on_complete_callback
        
        # Состояние браузера
        self.current_page = "search"
        self.search_query = ""
        self.search_results = []
        self.history = []
        
        # База знаний о кибербезопасности
        self.knowledge_base = {
            "фишинг анализ": [
                "Как анализировать фишинг письма:",
                "- Проверьте заголовки письма (From, Reply-To)",
                "- Изучите домен отправителя через WHOIS",
                "- Проверьте SPF, DKIM, DMARC записи",
                "- Анализируйте ссылки и вложения",
                "- Ищите грамматические ошибки и спешку"
            ],
            "фишинг защита": [
                "Защита от фишинга:",
                "- Включите двухфакторную аутентификацию (MFA)",
                "- Обучайте сотрудников распознаванию угроз",
                "- Настройте фильтрацию почты",
                "- Блокируйте подозрительные домены",
                "- Внедрите системы мониторинга"
            ],
            "mitre att&ck фишинг": [
                "MITRE ATT&CK T1566 - Фишинг:",
                "- Тактика: Initial Access",
                "- Техника: Spearphishing Link/Attachment",
                "- Процедура: Отправка поддельных писем",
                "- Обнаружение: Анализ почтовых заголовков",
                "- Защита: DMARC, обучение сотрудников"
            ],
            "mitre att&ck valid accounts": [
                "MITRE ATT&CK T1078 - Valid Accounts:",
                "- Тактика: Defense Evasion, Persistence, Privilege Escalation",
                "- Техника: Использование легитимных учетных записей",
                "- Процедура: Компрометация существующих учетных записей",
                "- Обнаружение: Мониторинг аномальной активности",
                "- Защита: MFA, строгие политики паролей, аудит"
            ],
            "компрометация учетных записей": [
                "Компрометация учетных записей:",
                "- Признаки: Активность в нерабочее время",
                "- Признаки: Доступ к нехарактерным ресурсам",
                "- Признаки: Попытки эскалации привилегий",
                "- Защита: Многофакторная аутентификация",
                "- Защита: Политики условного доступа"
            ],
            "nist кибербезопасность": [
                "NIST Cybersecurity Framework:",
                "- Identify: Идентификация активов и угроз",
                "- Protect: Внедрение защитных мер",
                "- Detect: Обнаружение киберинцидентов",
                "- Respond: Реагирование на инциденты",
                "- Recover: Восстановление после атак"
            ],
            "siem мониторинг": [
                "SIEM мониторинг:",
                "- Сбор и анализ логов безопасности",
                "- Обнаружение аномальной активности",
                "- Корреляция событий безопасности",
                "- Оперативное реагирование на инциденты",
                "- Отчетность и аудит"
            ]
        }
        
        # Кнопки
        self.buttons = []
        self._create_buttons()
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_mono = pygame.font.Font(None, 16)
        
        # Поле ввода
        self.input_active = False
        self.cursor_timer = 0
        self.show_cursor = True
    
    def _create_buttons(self):
        """Создание кнопок браузера (равномерно, без наложения)"""
        # Высота шапки и отступ как у окон приложений
        nav_y = 70
        btn_w = 140
        btn_h = 28
        gap = 16
        start_x = 50
        nav_buttons = [
            ("Поиск", self.show_search),
            ("База знаний", self.show_knowledge_base),
            ("Домой", self.go_home),
        ]
        for i, (text, callback) in enumerate(nav_buttons):
            x = start_x + i * (btn_w + gap)
            button = Button(x, nav_y, btn_w, btn_h, text, (80, 80, 120), callback)
            self.buttons.append(button)
    
    def show_search(self):
        self.current_page = "search"
    
    def show_knowledge_base(self):
        self.current_page = "knowledge_base"
    
    def go_home(self):
        self.current_page = "search"
        self.search_query = ""
        self.search_results = []
    
    def perform_search(self):
        """Выполнение поиска в базе знаний (с допуском небольших опечаток)."""
        query = self.search_query.lower().strip()
        self.search_results = []
        
        for keyword, content in self.knowledge_base.items():
            if _query_matches_keyword(query, keyword):
                self.search_results.extend(content)
                self.search_results.append("---")
        
        if not self.search_results:
            self.search_results = [
                "По вашему запросу ничего не найдено.",
                "Попробуйте следующие запросы:",
                "- фишинг анализ",
                "- фишинг защита",
                "- mitre att&ck фишинг",
                "- mitre att&ck valid accounts",
                "- компрометация учетных записей",
                "- siem мониторинг",
                "- nist кибербезопасность"
            ]
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            close_size = 16
            close_btn = pygame.Rect(self.screen_width - close_size - 6, 8, close_size, close_size)
            if close_btn.collidepoint(event.pos):
                self.on_complete(True)
                return True
            
            search_y, search_h = 106, 28
            search_w = min(500, self.screen_width - 200)
            input_rect = pygame.Rect(50, search_y, search_w, search_h)
            if input_rect.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False
            
            search_btn = pygame.Rect(50 + search_w + 10, search_y, 80, search_h)
            if search_btn.collidepoint(event.pos):
                self.perform_search()
            
            # Проверка кнопок навигации
            for button in self.buttons:
                button.handle_event(event)
        
        elif event.type == pygame.KEYDOWN and self.input_active:
            if event.key == pygame.K_RETURN:
                self.perform_search()
            elif event.key == pygame.K_BACKSPACE:
                self.search_query = self.search_query[:-1]
            else:
                self.search_query += event.unicode
        
        return False
    
    def update(self):
        # Мигание курсора
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.show_cursor = not self.show_cursor
        
        for button in self.buttons:
            button.update()
    
    def draw(self, screen):
        # Стиль как у окон приложений (Почта, Мой компьютер): шапка и тело
        header_h = 32
        header_color = (10, 36, 106)
        body_color = (240, 240, 240)
        border_color = (128, 128, 128)
        
        screen.fill(body_color)
        
        # Шапка как у Window
        title_bg = pygame.Rect(0, 0, self.screen_width, header_h)
        pygame.draw.rect(screen, header_color, title_bg)
        pygame.draw.line(screen, (255, 255, 255), (0, header_h - 1), (self.screen_width, header_h - 1), 1)
        
        title = self.font_medium.render("Интернет - Поиск информации", True, (255, 255, 255))
        screen.blit(title, (10, 6))
        
        # Кнопка закрытия как в окнах (справа в шапке)
        close_size = 16
        close_btn = pygame.Rect(self.screen_width - close_size - 6, 8, close_size, close_size)
        pygame.draw.rect(screen, (220, 60, 60), close_btn)
        pygame.draw.rect(screen, (0, 0, 0), close_btn, 1)
        close_text = self.font_small.render("x", True, (255, 255, 255))
        screen.blit(close_text, (close_btn.x + (close_size - close_text.get_width()) // 2, close_btn.y + 1))
        
        # Кнопки навигации (уже без наложения)
        for button in self.buttons:
            button.draw(screen)
        
        # Строка поиска под кнопками (nav_y + btn_h + отступ)
        search_y = 106
        search_h = 28
        search_w = min(500, self.screen_width - 200)
        search_x = 50
        search_bg = pygame.Rect(search_x, search_y, search_w, search_h)
        pygame.draw.rect(screen, (255, 255, 255), search_bg)
        pygame.draw.rect(screen, border_color, search_bg, 1)
        
        search_text = self.font_small.render(self.search_query, True, (0, 0, 0))
        screen.blit(search_text, (search_x + 8, search_y + 5))
        
        if self.input_active and self.show_cursor:
            cursor_x = search_x + 8 + search_text.get_width()
            pygame.draw.line(screen, (0, 0, 0), (cursor_x, search_y + 4), (cursor_x, search_y + search_h - 4), 2)
        
        # Кнопка "Искать" справа от поля
        search_btn_x = search_x + search_w + 10
        search_btn = pygame.Rect(search_btn_x, search_y, 80, search_h)
        pygame.draw.rect(screen, (76, 175, 80), search_btn)
        pygame.draw.rect(screen, border_color, search_btn, 1)
        btn_text = self.font_small.render("Искать", True, (255, 255, 255))
        screen.blit(btn_text, (search_btn_x + (80 - btn_text.get_width()) // 2, search_y + 5))
        
        # Область контента как тело окна
        content_top = search_y + search_h + 12
        results_bg = pygame.Rect(20, content_top, self.screen_width - 40, self.screen_height - content_top - 20)
        pygame.draw.rect(screen, (255, 255, 255), results_bg)
        pygame.draw.rect(screen, border_color, results_bg, 1)
        
        if self.current_page == "search":
            self.draw_search_results(screen, content_top, results_bg)
        elif self.current_page == "knowledge_base":
            self.draw_knowledge_base(screen, content_top, results_bg)
    
    def draw_search_results(self, screen, content_top, results_bg):
        """Отрисовка результатов поиска (стиль окна приложения)"""
        pad = 15
        x, y = results_bg.x + pad, content_top + pad
        title = self.font_medium.render("Результаты поиска:", True, (0, 0, 128))
        screen.blit(title, (x, y))
        y += 28
        results_right = results_bg.right - pad
        results_bottom = results_bg.bottom - pad
        for result in self.search_results:
            if y > results_bottom:
                break
            if result == "---":
                pygame.draw.line(screen, (180, 180, 180), (x, y), (results_right, y), 1)
                y += 12
                continue
            color = (0, 0, 0) if not result.startswith("-") else (0, 100, 0)
            result_text = self.font_small.render(result, True, color)
            screen.blit(result_text, (x, y))
            y += 22
    
    def draw_knowledge_base(self, screen, content_top, results_bg):
        """Отрисовка базы знаний (стиль окна приложения)"""
        pad = 15
        x, y = results_bg.x + pad, content_top + pad
        title = self.font_medium.render("База знаний по кибербезопасности:", True, (0, 0, 128))
        screen.blit(title, (x, y))
        y += 28
        topics = [
            "фишинг анализ - как анализировать фишинг-письма",
            "фишинг защита - методы защиты от фишинга",
            "mitre att&ck фишинг - тактики и техники фишинга",
            "mitre att&ck valid accounts - компрометация учётных записей",
            "компрометация учётных записей - признаки и защита",
            "siem мониторинг - системы мониторинга безопасности",
            "nist кибербезопасность - фреймворк безопасности"
        ]
        for topic in topics:
            topic_text = self.font_small.render("- " + topic, True, (0, 0, 0))
            screen.blit(topic_text, (x, y))
            y += 26
        y += 12
        info_text = self.font_small.render("Введите запрос в поле поиска для получения информации.", True, (100, 100, 100))
        screen.blit(info_text, (x, y))
    
    def on_resize(self, w, h):
        self.screen_width, self.screen_height = w, h

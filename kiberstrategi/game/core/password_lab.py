"""Оценка стойкости пароля для «Лаборатории паролей» (без pygame, без сети).

Пароль разбирается на части, которые проще угадать, чем перебирать: частый
пароль, слово (в том числе с заменами вроде @ вместо a и в русской
раскладке), клавиатурная последовательность, повтор, дата. Остальное
считается перебором. Из лучшего разбора получается число попыток, а из него
время взлома в четырёх сценариях. Это учебная модель по мотивам zxcvbn:
словари маленькие, поэтому реальные атакующие справятся быстрее.

Пароль нигде не сохраняется и не логируется: функции чистые.
"""
import math
import re
import secrets
from dataclasses import dataclass

from ..data.password_lists import (
    COMMON_PASSWORDS, WORDS, KEYBOARD_ROWS, LEET, LAYOUT_EN_RU, PHRASE_WORDS,
)

MAX_PASSWORD_LENGTH = 64

_COMMON_RANK = {}
for _rank, _word in enumerate(COMMON_PASSWORDS, start=1):
    _COMMON_RANK.setdefault(_word, _rank)
_WORD_RANK = {}
for _rank, _word in enumerate(WORDS, start=1):
    _WORD_RANK.setdefault(_word, _rank)

# Один запрос в секунду на словарь из ~12 тысяч слов: так оценивается «обычное слово»
_WORD_BASE_GUESSES = 500
_WORD_RANK_SCALE = 40
_LEET_MULTIPLIER = 3

# Сценарии атаки: название, попыток в секунду
SCENARIOS = [
    ("Вход на сайт с защитой от перебора", 100 / 3600),
    ("Вход на сайт без ограничений", 10),
    ("Взлом утёкшей базы (bcrypt)", 1e4),
    ("Взлом утёкшей базы (MD5, видеокарты)", 1e10),
]

SCENARIO_RATE_TEXT = ["100 попыток в час", "10 попыток в секунду", "10 тысяч в секунду", "10 миллиардов в секунду"]

# Пороги числа попыток для оценок 1..4
SCORE_THRESHOLDS = [1e5, 1e8, 1e11, 1e14]
SCORE_LABELS = ["Очень слабый", "Слабый", "Средний", "Хороший", "Отличный"]

# Незнакомое, но обычное слово атакующий ищет по словарю частых слов: не больше ~8 тысяч вариантов
_UNKNOWN_WORD_MAX_GUESSES = 2 ** 13
_VOWELS = set("aeiouyаеёиоуыэюя")
_SEPARATORS = " -_.,;:/+="

KIND_LABELS = {
    "separator": "разделитель",
    "common": "популярный пароль",
    "word": "обычное слово",
    "layout": "слово в другой раскладке",
    "keyboard": "клавиатурный шаблон",
    "sequence": "последовательность",
    "repeat": "повтор",
    "date": "дата или год",
    "random": "случайные символы",
}


@dataclass
class Match:
    start: int
    end: int
    kind: str
    guesses: float
    detail: str = ""

    @property
    def bits(self):
        return math.log2(max(self.guesses, 1.0))


def _pool_size(password):
    pool = 0
    if re.search(r"[a-z]", password):
        pool += 26
    if re.search(r"[A-Z]", password):
        pool += 26
    if re.search(r"\d", password):
        pool += 10
    if re.search(r"[а-яё]", password):
        pool += 33
    if re.search(r"[А-ЯЁ]", password):
        pool += 33
    if re.search(r"[^\w\s]", password) or "_" in password:
        pool += 33
    if re.search(r"[^\x00-\x7fЀ-ӿ]", password):
        pool += 100
    if " " in password:
        pool += 1
    return max(pool, 10)


def _case_multiplier(token):
    letters = [c for c in token if c.isalpha()]
    upper = sum(1 for c in letters if c.isupper())
    lower = len(letters) - upper
    if upper == 0 or lower == 0 and upper == len(letters):
        return 1 if upper == 0 else 2
    if token[0].isupper() and upper == 1:
        return 2
    total = 0
    for i in range(1, min(upper, lower) + 1):
        total += math.comb(upper + lower, i)
    return max(2, total)


def _deleet(token):
    return "".join(LEET.get(c, c) for c in token)


def _to_russian_layout(token):
    converted = "".join(LAYOUT_EN_RU.get(c, c) for c in token)
    return converted if converted != token else None


def _dictionary_matches(password):
    lowered = password.lower()
    found = []
    n = len(password)
    for i in range(n):
        for j in range(i + 3, min(n, i + 24) + 1):
            raw = lowered[i:j]
            token = password[i:j]
            case_mult = _case_multiplier(token)
            # 1. Прямое совпадение с частым паролем или словом
            if raw in _COMMON_RANK:
                found.append(Match(i, j, "common", _COMMON_RANK[raw] * case_mult, raw))
            if raw in _WORD_RANK:
                guesses = (_WORD_BASE_GUESSES + _WORD_RANK[raw] * _WORD_RANK_SCALE) * case_mult
                found.append(Match(i, j, "word", guesses, raw))
            # 2. С заменами символов
            plain = _deleet(raw)
            if plain != raw:
                if plain in _COMMON_RANK:
                    found.append(Match(i, j, "common", _COMMON_RANK[plain] * case_mult * _LEET_MULTIPLIER, plain))
                if plain in _WORD_RANK:
                    guesses = (_WORD_BASE_GUESSES + _WORD_RANK[plain] * _WORD_RANK_SCALE) * case_mult * _LEET_MULTIPLIER
                    found.append(Match(i, j, "word", guesses, plain))
            # 3. Русские слова, набранные в английской раскладке
            russian = _to_russian_layout(raw)
            if russian:
                if russian in _COMMON_RANK:
                    found.append(Match(i, j, "layout", _COMMON_RANK[russian] * case_mult * 2, russian))
                if russian in _WORD_RANK:
                    guesses = (_WORD_BASE_GUESSES + _WORD_RANK[russian] * _WORD_RANK_SCALE) * case_mult * 2
                    found.append(Match(i, j, "layout", guesses, russian))
    return found


def _looks_like_word(plain):
    """Правдоподобное слово: буквы, разумная доля гласных, нет длинных россыпей согласных."""
    if len(plain) < 3 or not plain.isalpha():
        return False
    vowels = sum(1 for c in plain if c in _VOWELS)
    if not 0.25 <= vowels / len(plain) <= 0.65:
        return False
    run = 0
    for c in plain:
        run = 0 if c in _VOWELS else run + 1
        if run > 4:
            return False
    return not re.search(r"(.)\1\1", plain)


def _natural_word_matches(password):
    """Слова, которых нет в нашем словаре, но которые похожи на слова (в том числе с заменами букв)."""
    found = []
    n = len(password)
    letter_like = [c.isalpha() or c in LEET for c in password]
    i = 0
    while i < n:
        if not letter_like[i]:
            i += 1
            continue
        end = i
        while end < n and letter_like[end]:
            end += 1
        for start in range(i, end):
            for stop in range(start + 3, min(end, start + 16) + 1):
                token = password[start:stop]
                if not (token[0].isalpha() and token[-1].isalpha()):
                    continue
                if sum(1 for c in token if not c.isalpha()) > len(token) // 3:
                    continue
                plain = _deleet(token.lower())
                if not _looks_like_word(plain):
                    continue
                alphabet = 33 if re.search(r"[а-яё]", plain) else 26
                guesses = min(alphabet ** len(plain), _UNKNOWN_WORD_MAX_GUESSES) * _case_multiplier(token)
                if plain != token.lower():
                    guesses *= _LEET_MULTIPLIER
                found.append(Match(start, stop, "word", guesses, plain))
        i = end
    return found


def _separator_matches(password):
    return [Match(i, i + 1, "separator", 8.0, c) for i, c in enumerate(password) if c in _SEPARATORS]


def _keyboard_matches(password):
    lowered = password.lower()
    found = []
    n = len(password)
    for row in KEYBOARD_ROWS:
        for source in (row, row[::-1]):
            for i in range(n):
                for j in range(i + 4, n + 1):
                    if lowered[i:j] in source:
                        found.append(Match(i, j, "keyboard", 40.0 * (j - i), lowered[i:j]))
                    else:
                        break
    return found


def _sequence_matches(password):
    found = []
    n = len(password)
    i = 0
    while i < n - 2:
        step = ord(password[i + 1]) - ord(password[i])
        if step in (1, -1):
            j = i + 1
            while j + 1 < n and ord(password[j + 1]) - ord(password[j]) == step:
                j += 1
            if j - i + 1 >= 3:
                start_char = password[i]
                base = 4.0 if start_char in "aAzZ01959" else (10.0 if start_char.isdigit() else 26.0)
                guesses = base * (j - i + 1) * (2 if step < 0 else 1)
                found.append(Match(i, j + 1, "sequence", guesses, password[i:j + 1]))
            i = j
        else:
            i += 1
    return found


def _repeat_matches(password):
    found = []
    n = len(password)
    for size in range(1, n // 2 + 1):
        for i in range(0, n - size * 2 + 1):
            unit = password[i:i + size]
            count = 1
            while password.startswith(unit, i + size * count):
                count += 1
            if count >= 2 and size * count >= 3:
                unit_guesses = _pool_size(unit) ** size
                found.append(Match(i, i + size * count, "repeat", unit_guesses * count, unit))
    return found


def _date_matches(password):
    found = []
    for m in re.finditer(r"(?<!\d)(19\d\d|20[0-3]\d)(?!\d)", password):
        found.append(Match(m.start(), m.end(), "date", 130.0, m.group()))
    for m in re.finditer(r"(?<!\d)(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])(\d\d|19\d\d|20\d\d)(?!\d)", password):
        found.append(Match(m.start(), m.end(), "date", 365.0 * 100, m.group()))
    for m in re.finditer(r"(?<!\d)\d{4}(?!\d)", password):
        found.append(Match(m.start(), m.end(), "date", 10000.0, m.group()))
    return found


def _best_decomposition(password, matches):
    """Оптимальная разбивка: минимум бит с небольшой платой за число частей."""
    n = len(password)
    pool_bits = math.log2(_pool_size(password))
    by_start = {}
    for match in matches:
        by_start.setdefault(match.start, []).append(match)
    INF = float("inf")
    best = [[INF] * (n + 2) for _ in range(n + 1)]
    back = {}
    best[0][0] = 0.0
    for i in range(n):
        for k in range(n + 1):
            base = best[i][k]
            if base == INF:
                continue
            for match in by_start.get(i, []):
                cost = base + match.bits
                if cost < best[match.end][k + 1]:
                    best[match.end][k + 1] = cost
                    back[(match.end, k + 1)] = (i, k, match)
            for j in range(i + 1, n + 1):
                cost = base + (j - i) * pool_bits
                if cost < best[j][k + 1]:
                    best[j][k + 1] = cost
                    back[(j, k + 1)] = (i, k, Match(i, j, "random", 2 ** ((j - i) * pool_bits)))
    choice, total = None, INF
    for k in range(1, n + 1):
        if best[n][k] == INF:
            continue
        cost = best[n][k] + math.log2(math.factorial(k))
        if cost < total:
            choice, total = k, cost
    parts = []
    i, k = n, choice
    while i > 0:
        start, prev_k, match = back[(i, k)]
        parts.append(match)
        i, k = start, prev_k
    parts.reverse()
    return parts, total


def format_duration(seconds):
    """Время в человеческом виде по-русски: «3 минуты», «12 лет», «века»."""
    if seconds < 1:
        return "мгновенно"
    units = [
        (60, ("секунда", "секунды", "секунд")),
        (3600, ("минута", "минуты", "минут")),
        (86400, ("час", "часа", "часов")),
        (86400 * 31, ("день", "дня", "дней")),
        (86400 * 365, ("месяц", "месяца", "месяцев")),
    ]
    divisors = [1, 60, 3600, 86400, 86400 * 30]
    for (limit, forms), divisor in zip(units, divisors):
        if seconds < limit:
            return f"{int(seconds // divisor)} {_plural(int(seconds // divisor), forms)}"
    years = seconds / (86400 * 365)
    if years < 100:
        return f"{int(years)} {_plural(int(years), ('год', 'года', 'лет'))}"
    if years < 1000:
        return f"{int(years // 100)} {_plural(int(years // 100), ('век', 'века', 'веков'))}"
    if years < 1e6:
        thousands = int(years // 1000)
        return f"{thousands} {_plural(thousands, ('тысяча лет', 'тысячи лет', 'тысяч лет'))}"
    if years < 1e9:
        millions = int(years // 1e6)
        return f"{millions} {_plural(millions, ('миллион лет', 'миллиона лет', 'миллионов лет'))}"
    return "миллиарды лет"


def _plural(n, forms):
    n = abs(n) % 100
    if 11 <= n <= 19:
        return forms[2]
    n %= 10
    if n == 1:
        return forms[0]
    if 2 <= n <= 4:
        return forms[1]
    return forms[2]


def crack_times(guesses):
    """Среднее время взлома (половина пространства) в каждом сценарии: список (название, секунды)."""
    return [(name, guesses / 2 / rate) for name, rate in SCENARIOS]


def score_for_guesses(guesses):
    score = 0
    for threshold in SCORE_THRESHOLDS:
        if guesses >= threshold:
            score += 1
    return score


def _feedback(password, parts):
    tips = []
    kinds = {p.kind for p in parts}
    if "common" in kinds:
        tips.append("Такой пароль есть в списках утёкших: его проверят первым же делом.")
    if "layout" in kinds:
        tips.append("Русское слово в английской раскладке (ghbdtn) злоумышленники тоже подбирают.")
    if "word" in kinds and "common" not in kinds:
        tips.append("Обычные слова и имена угадываются словарём, даже с заглавной буквой или цифрой в конце.")
    if re.search(r"[@$!0-9]", password) and kinds & {"common", "word"}:
        tips.append("Замены вроде @ вместо a и 0 вместо o давно известны и почти не добавляют стойкости.")
    if "keyboard" in kinds or "sequence" in kinds:
        tips.append("Соседние клавиши и цепочки вроде 1234 или abc проверяются в самом начале.")
    if "repeat" in kinds:
        tips.append("Повторы (aaaa, abcabc) добавляют длину, но не добавляют неожиданности.")
    if "date" in kinds:
        tips.append("Годы и даты рождения угадываются за минуты. Не используйте их.")
    if len(password) < 12:
        tips.append("Длина важнее сложности: возьмите 12 символов и больше или парольную фразу из нескольких слов.")
    if not tips:
        tips.append("Хороший результат. Главное: не использовать этот пароль больше чем на одном сайте.")
    return tips[:4]


def analyze(password):
    """Возвращает словарь с оценкой. Пустой пароль даёт нулевую оценку."""
    password = password[:MAX_PASSWORD_LENGTH]
    if not password:
        return {"length": 0, "parts": [], "guesses": 1.0, "bits": 0.0, "score": 0,
                "label": SCORE_LABELS[0], "times": crack_times(1.0), "tips": [], "pool": 0}
    matches = []
    matches += _dictionary_matches(password)
    matches += _keyboard_matches(password)
    matches += _sequence_matches(password)
    matches += _repeat_matches(password)
    matches += _date_matches(password)
    matches += _natural_word_matches(password)
    matches += _separator_matches(password)
    parts, total_bits = _best_decomposition(password, matches)
    guesses = 2 ** total_bits
    score = score_for_guesses(guesses)
    return {
        "length": len(password),
        "parts": parts,
        "guesses": guesses,
        "bits": total_bits,
        "score": score,
        "label": SCORE_LABELS[score],
        "times": crack_times(guesses),
        "tips": _feedback(password, parts),
        "pool": _pool_size(password),
    }


def random_password_bits(length):
    """Стойкость случайного пароля из всех печатных символов (94 варианта на знак)."""
    return length * math.log2(94)


def generate_passphrase(word_count, separator="-", capitalize=False, add_digit=False, rng=None):
    """Парольная фраза из случайных слов; возвращает (фраза, бит стойкости).

    Стойкость считается честно: атакующий знает список слов, а порядок,
    заглавные буквы и разделитель ему известны, поэтому в бит идут только выбор слов и цифра.
    """
    rng = rng or secrets.SystemRandom()
    words = [rng.choice(PHRASE_WORDS) for _ in range(word_count)]
    if capitalize:
        words = [w.capitalize() for w in words]
    phrase = separator.join(words)
    bits = word_count * math.log2(len(PHRASE_WORDS))
    if add_digit:
        phrase += f"{separator}{rng.randrange(10)}"
        bits += math.log2(10)
    return phrase, bits


ROUND_POINTS = 10


class RoundResult:
    def __init__(self, chosen, best, analyses):
        self.chosen = chosen
        self.best = best
        self.analyses = analyses

    @property
    def correct(self):
        return self.chosen == self.best


class Challenge:
    """«Испытание»: в каждом раунде выбрать самый стойкий из трёх паролей.

    Верный ответ определяет тот же оценщик, что и в анализаторе, поэтому
    игра и разбор никогда не расходятся.
    """

    def __init__(self, rounds, rng=None):
        import random
        rng = rng or random.Random()
        self.rounds = []
        for source in rounds:
            options = list(source["options"])
            rng.shuffle(options)
            analyses = [analyze(pw) for pw in options]
            best = max(range(len(options)), key=lambda i: analyses[i]["bits"])
            self.rounds.append({"options": options, "analyses": analyses, "best": best, "lesson": source["lesson"]})
        self.index = 0
        self.results = []

    @property
    def total(self):
        return len(self.rounds)

    @property
    def current(self):
        return self.rounds[self.index] if self.index < self.total else None

    @property
    def finished(self):
        return self.index >= self.total

    @property
    def answered_current(self):
        return len(self.results) > self.index

    @property
    def correct_count(self):
        return sum(1 for r in self.results if r.correct)

    @property
    def score(self):
        return self.correct_count * ROUND_POINTS

    @property
    def max_score(self):
        return self.total * ROUND_POINTS

    def answer(self, index):
        if self.finished or self.answered_current:
            return self.results[-1]
        rnd = self.current
        result = RoundResult(index, rnd["best"], rnd["analyses"])
        self.results.append(result)
        return result

    def advance(self):
        if self.answered_current:
            self.index += 1

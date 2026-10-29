"""Логика раунда режима «Фишинг-детектор»: отбор сообщений, очки, серии,
статистика и слабое место игрока. Здесь нет ни pygame, ни отрисовки:
сцена только показывает то, что считает сессия.
"""
import random
from collections import Counter

ROUND_SIZE = 10
PHISH_PER_ROUND = 6
TIME_LIMIT_SECONDS = 20
POINTS_PER_CORRECT = 10

# Порог процента, тег цвета, звание, описание. Проверяются по убыванию порога.
RANKS = [
    (100, "success", "Охотник за фишингом",
     "Ни одна подделка не прошла, и ни одного настоящего письма вы не потеряли. Так держать."),
    (80, "success", "Бдительный аналитик",
     "Вы уверенно отличаете подделки от настоящих сообщений. Осталось отточить пару деталей."),
    (50, "warning", "Стажёр по фишингу",
     "Часть подделок вас всё ещё обманывает. Разбор улик ниже поможет заметить их в следующий раз."),
    (0, "danger", "Лёгкая добыча",
     "Мошенники справились бы с вами без труда. Пройдите раунд ещё раз, читая разбор после каждого ответа."),
]


def rank_for_percent(percent):
    for threshold, tag, title, description in RANKS:
        if percent >= threshold:
            return tag, title, description
    _, tag, title, description = RANKS[-1]
    return tag, title, description


class AnswerResult:
    """Итог одного ответа. kind: correct, missed, false_alarm или timeout."""

    def __init__(self, message, choice, kind, elapsed):
        self.message = message
        self.choice = choice
        self.kind = kind
        self.elapsed = elapsed

    @property
    def correct(self):
        return self.kind == "correct"


class PhishingSession:
    def __init__(self, messages, rng=None, round_size=ROUND_SIZE, phish_count=PHISH_PER_ROUND):
        rng = rng or random.Random()
        phishing = [m for m in messages if m["is_phishing"]]
        legit = [m for m in messages if not m["is_phishing"]]
        phish_take = min(phish_count, len(phishing), round_size)
        legit_take = min(round_size - phish_take, len(legit))
        picked = rng.sample(phishing, phish_take) + rng.sample(legit, legit_take)
        rng.shuffle(picked)
        self.messages = picked
        self.index = 0
        self.results = []
        self.streak = 0
        self.best_streak = 0

    @property
    def total(self):
        return len(self.messages)

    @property
    def current(self):
        return self.messages[self.index] if self.index < self.total else None

    @property
    def finished(self):
        return self.index >= self.total

    @property
    def is_last(self):
        return self.index == self.total - 1

    @property
    def answered_current(self):
        return len(self.results) > self.index

    @property
    def score(self):
        return sum(POINTS_PER_CORRECT for r in self.results if r.correct)

    @property
    def max_score(self):
        return self.total * POINTS_PER_CORRECT

    @property
    def percent(self):
        return round(self.score / self.max_score * 100) if self.max_score else 0

    def answer(self, choice, elapsed):
        """choice: "phishing", "safe" или None (время вышло). Возвращает AnswerResult."""
        if self.finished or self.answered_current:
            return self.results[-1]
        message = self.current
        if choice is None:
            kind = "timeout"
        elif (choice == "phishing") == message["is_phishing"]:
            kind = "correct"
        elif message["is_phishing"]:
            kind = "missed"
        else:
            kind = "false_alarm"
        result = AnswerResult(message, choice, kind, elapsed)
        self.results.append(result)
        if result.correct:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.streak = 0
        return result

    def advance(self):
        if self.answered_current:
            self.index += 1

    @property
    def correct_count(self):
        return sum(1 for r in self.results if r.correct)

    @property
    def missed_count(self):
        return sum(1 for r in self.results if r.kind == "missed")

    @property
    def false_alarm_count(self):
        return sum(1 for r in self.results if r.kind == "false_alarm")

    @property
    def timeout_count(self):
        return sum(1 for r in self.results if r.kind == "timeout")

    @property
    def average_time(self):
        times = [r.elapsed for r in self.results if r.kind != "timeout"]
        return sum(times) / len(times) if times else None

    @property
    def mistakes(self):
        return [r for r in self.results if not r.correct]

    def weakest_category(self):
        """Категория красных флагов, которую игрок пропускал чаще всего (или None)."""
        counter = Counter()
        for r in self.results:
            if r.correct or not r.message["is_phishing"]:
                continue
            for clue in r.message["clues"]:
                counter[clue["category"]] += 1
        if not counter:
            return None
        return counter.most_common(1)[0][0]

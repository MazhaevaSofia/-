"""Копит неверные ответы викторин за текущую сессию — «разбор ошибок» игрока.

Каждый сценарий-расследование передаёт свои game/ui/quiz_engine.py
QuizEngine.mistakes через колбэк on_complete; MistakeTracker просто
складывает их в один список с привязкой к технике, чтобы в конце
прохождения показать, какие темы вызвали больше всего затруднений.
"""


class MistakeTracker:
    def __init__(self):
        self.entries = []  # [{"technique": str, "question": str, "chosen": str, "correct": str, "explanation": str}]

    def record(self, technique, mistakes):
        if not mistakes:
            return
        for m in mistakes:
            self.entries.append({"technique": technique, **m})

    def clear(self):
        self.entries = []

    @property
    def has_mistakes(self):
        return len(self.entries) > 0

    def techniques_to_review(self):
        """Уникальные техники, отсортированные по числу ошибок (больше — раньше)."""
        counts = {}
        for entry in self.entries:
            counts[entry["technique"]] = counts.get(entry["technique"], 0) + 1
        return sorted(counts.keys(), key=lambda t: -counts[t])

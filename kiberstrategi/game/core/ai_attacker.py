"""Локальный адаптивный ИИ-атакующий для режима «Игрок против ИИ».

Полностью офлайн и бесплатный: без обращения к внешним LLM-сервисам, что
сохраняет заявленное конкурентное преимущество тренажёра (не требует
подключения к интернету). Тактика меняется по простому, объяснимому
правилу — эскалация сложности, если защитник справляется хорошо, и
продолжение давления на тот же класс уязвимостей, если защитник ошибается.
"""
import random

from .versus_match import TECHNIQUES, MAX_SCORE_PER_ROUND

STRONG_PERFORMANCE_RATIO = 0.7


class AIAttacker:
    def __init__(self, technique_pool=None):
        self.pool = list(technique_pool or TECHNIQUES.keys())
        self.history = []  # [(technique_key, defender_score)]

    def choose(self, available_techniques):
        """Выбрать технику для следующего раунда из ещё не использованных."""
        available = [t for t in available_techniques if t in self.pool]
        if not available:
            return None
        if not self.history:
            return random.choice(available)

        _, last_score = self.history[-1]
        performance = last_score / MAX_SCORE_PER_ROUND

        if performance >= STRONG_PERFORMANCE_RATIO:
            # Защитник хорошо справился — эскалируем к более сложным техникам
            candidates = [t for t in available if TECHNIQUES[t]["tier"] == "hard"]
        else:
            # Защитник ошибался — атакующий продолжает давить похожим вектором
            candidates = [t for t in available if TECHNIQUES[t]["tier"] == "easy"]

        return random.choice(candidates or available)

    def record_result(self, technique_key, defender_score):
        self.history.append((technique_key, defender_score or 0))

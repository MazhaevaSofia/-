"""Логика босс-уровня: очки, целостность сети, «здоровье» атакующего, состояние
узлов карты и итог операции. Без pygame и без отрисовки.
"""
import random

PHASE_TIME_LIMIT = 60
INTEGRITY_START = 100
INTEGRITY_LOSS = {2: 0, 1: 10, 0: 30}
DECISION_POINTS = {2: 60, 1: 30, 0: 0}
EVIDENCE_MAX = 30
SPEED_MAX = 10
PHASE_MAX_POINTS = max(DECISION_POINTS.values()) + EVIDENCE_MAX + SPEED_MAX
BOSS_DAMAGE_FACTOR = {2: 1.0, 1: 0.5, 0: 0.0}
VICTORY_HP_THRESHOLD = 20

# Порог процента, буква, звание
GRADES = [
    (90, "S", "Легенда SOC"),
    (75, "A", "Старший аналитик"),
    (55, "B", "Опытный аналитик"),
    (35, "C", "Младший аналитик"),
    (0, "D", "Нужна практика"),
]


def grade_for_percent(percent):
    for threshold, letter, title in GRADES:
        if percent >= threshold:
            return letter, title
    return GRADES[-1][1], GRADES[-1][2]


class PhaseResult:
    def __init__(self, phase, chosen, quality, marks, elapsed, timed_out):
        self.phase = phase
        self.chosen = chosen
        self.quality = quality
        self.marks = set(marks)
        self.elapsed = elapsed
        self.timed_out = timed_out

        suspicious = {i for i, line in enumerate(phase["log"]) if line["sus"]}
        self.correct_marks = self.marks & suspicious
        self.wrong_marks = self.marks - suspicious
        self.missed_marks = suspicious - self.marks

        self.decision_points = DECISION_POINTS[quality]
        raw = len(self.correct_marks) - 0.5 * len(self.wrong_marks)
        self.evidence_points = round(EVIDENCE_MAX * max(0.0, raw) / len(suspicious)) if suspicious else 0
        speed_share = max(0.0, 1 - elapsed / PHASE_TIME_LIMIT)
        self.speed_points = round(SPEED_MAX * speed_share * (1.0 if quality == 2 else 0.5)) if quality > 0 else 0
        self.integrity_loss = INTEGRITY_LOSS[quality]

    @property
    def points(self):
        return self.decision_points + self.evidence_points + self.speed_points

    @property
    def best_option(self):
        return max(self.phase["options"], key=lambda o: o["quality"])


class BossFight:
    def __init__(self, phases, node_ids, rng=None):
        rng = rng or random.Random()
        self.phases = []
        for phase in phases:
            copy = dict(phase)
            options = list(phase["options"])
            rng.shuffle(options)
            copy["options"] = options
            self.phases.append(copy)
        self.node_state = {node: "ok" for node in node_ids}
        self.index = 0
        self.integrity = INTEGRITY_START
        self.boss_hp = 100.0
        self.results = []
        self.marks = set()
        self.selected = None
        self._enter_phase()

    @property
    def total(self):
        return len(self.phases)

    @property
    def current(self):
        return self.phases[self.index] if self.index < self.total else None

    @property
    def answered_current(self):
        return len(self.results) > self.index

    @property
    def game_over(self):
        return self.integrity <= 0

    @property
    def finished(self):
        return self.game_over or self.index >= self.total

    @property
    def score(self):
        return sum(r.points for r in self.results)

    @property
    def max_score(self):
        return self.total * PHASE_MAX_POINTS

    @property
    def percent(self):
        return round(self.score / self.max_score * 100) if self.max_score else 0

    @property
    def grade(self):
        return grade_for_percent(self.percent)

    @property
    def outcome(self):
        if self.game_over:
            return "defeat"
        if self.boss_hp <= VICTORY_HP_THRESHOLD:
            return "victory"
        return "partial"

    @property
    def flawless(self):
        return self.outcome == "victory" and self.integrity == INTEGRITY_START

    def _enter_phase(self):
        phase = self.current
        if phase:
            for node in phase["nodes"]["attack"]:
                self.node_state[node] = "compromised"

    def toggle_mark(self, line_index):
        if self.answered_current:
            return
        if line_index in self.marks:
            self.marks.discard(line_index)
        else:
            self.marks.add(line_index)

    def select(self, option_index):
        if self.answered_current:
            return
        if 0 <= option_index < len(self.current["options"]):
            self.selected = option_index

    def submit(self, elapsed, timed_out=False):
        """Фиксирует решение. По таймауту решение считается плохим, отметки улик сохраняются."""
        if self.finished or self.answered_current:
            return self.results[-1]
        phase = self.current
        if timed_out or self.selected is None:
            chosen, quality, timed_out = None, 0, True
        else:
            chosen = phase["options"][self.selected]
            quality = chosen["quality"]
        result = PhaseResult(phase, chosen, quality, self.marks, min(elapsed, PHASE_TIME_LIMIT), timed_out)
        self.results.append(result)
        self.integrity = max(0, self.integrity - result.integrity_loss)
        self.boss_hp = max(0.0, self.boss_hp - 100.0 / self.total * BOSS_DAMAGE_FACTOR[quality])
        self._apply_nodes(phase, quality)
        return result

    def _apply_nodes(self, phase, quality):
        nodes = phase["nodes"]
        if quality >= 1:
            for node in nodes["attack"]:
                self.node_state[node] = "contained"
        if quality == 1:
            for node in nodes["spread"]:
                if self.node_state[node] != "compromised":
                    self.node_state[node] = "suspicious"
        elif quality == 0:
            for node in nodes["spread"]:
                self.node_state[node] = "compromised"

    def advance(self):
        if not self.answered_current:
            return
        self.index += 1
        self.marks = set()
        self.selected = None
        if not self.finished:
            self._enter_phase()

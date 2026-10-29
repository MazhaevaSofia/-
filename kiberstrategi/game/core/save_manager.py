"""Сохранение прогресса между запусками игры (пройденные уровни, рекорд).

Раньше прогресс жил только в памяти GameManager и полностью обнулялся
при перезапуске. Файл сохранения лежит рядом с исполняемым файлом/main.py,
чтобы работать как при запуске из исходников, так и из собранного .exe.
"""
import json
import os
import sys

SAVE_FILE_NAME = "savegame.json"
MAX_CASE_LOG_ENTRIES = 60  # доска расследований хранит только последние N дел


def _default_save_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # game/core/save_manager.py -> корень проекта на два уровня выше
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SaveManager:
    def __init__(self, path=None):
        self.path = path or os.path.join(_default_save_dir(), SAVE_FILE_NAME)
        self.completed_levels = set()
        self.best_score = 0
        self.unlocked_achievements = set()
        self.case_log = []
        self.phishing_best = 0
        self.phishing_rounds = 0
        self.boss_best_score = 0
        self.boss_best_grade = ""
        self.boss_attempts = 0
        self.boss_victories = 0
        self.password_best = 0
        self.password_runs = 0
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.completed_levels = {int(x) for x in data.get("completed_levels", [])}
            self.best_score = int(data.get("best_score", 0))
            self.unlocked_achievements = {str(x) for x in data.get("unlocked_achievements", [])}
            self.case_log = list(data.get("case_log", []))
            self.phishing_best = int(data.get("phishing_best", 0))
            self.phishing_rounds = int(data.get("phishing_rounds", 0))
            self.boss_best_score = int(data.get("boss_best_score", 0))
            self.boss_best_grade = str(data.get("boss_best_grade", ""))
            self.boss_attempts = int(data.get("boss_attempts", 0))
            self.boss_victories = int(data.get("boss_victories", 0))
            self.password_best = int(data.get("password_best", 0))
            self.password_runs = int(data.get("password_runs", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Повреждённый или недоступный файл сохранения не должен ронять игру
            self.completed_levels = set()
            self.best_score = 0
            self.unlocked_achievements = set()
            self.case_log = []
            self.phishing_best = 0
            self.phishing_rounds = 0
            self.boss_best_score = 0
            self.boss_best_grade = ""
            self.boss_attempts = 0
            self.boss_victories = 0
            self.password_best = 0
            self.password_runs = 0

    def save(self):
        data = {
            "completed_levels": sorted(self.completed_levels),
            "best_score": self.best_score,
            "unlocked_achievements": sorted(self.unlocked_achievements),
            "case_log": self.case_log,
            "phishing_best": self.phishing_best,
            "phishing_rounds": self.phishing_rounds,
            "boss_best_score": self.boss_best_score,
            "boss_best_grade": self.boss_best_grade,
            "boss_attempts": self.boss_attempts,
            "boss_victories": self.boss_victories,
            "password_best": self.password_best,
            "password_runs": self.password_runs,
        }
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def mark_level_completed(self, level_id):
        if level_id not in self.completed_levels:
            self.completed_levels.add(level_id)
            self.save()

    def record_score(self, score):
        if score > self.best_score:
            self.best_score = score
            self.save()

    def unlock_achievements(self, achievement_ids):
        """Отмечает достижения разблокированными. Возвращает только новые id (для тоста/уведомления)."""
        newly = [a for a in achievement_ids if a not in self.unlocked_achievements]
        if newly:
            self.unlocked_achievements.update(newly)
            self.save()
        return newly

    def record_case(self, entry):
        """Добавляет запись на доску расследований (см. game/scenes/case_board_scene.py)."""
        self.case_log.append(entry)
        if len(self.case_log) > MAX_CASE_LOG_ENTRIES:
            self.case_log = self.case_log[-MAX_CASE_LOG_ENTRIES:]
        self.save()

    def record_phishing_round(self, score):
        """Учитывает сыгранный раунд «Фишинг-детектора». Возвращает True, если это новый рекорд."""
        self.phishing_rounds += 1
        is_new_best = score > self.phishing_best
        if is_new_best:
            self.phishing_best = score
        self.save()
        return is_new_best

    def record_boss_attempt(self, score, grade, victory):
        """Учитывает попытку босс-уровня. Возвращает True, если это новый рекорд по очкам."""
        self.boss_attempts += 1
        if victory:
            self.boss_victories += 1
        is_new_best = score > self.boss_best_score
        if is_new_best:
            self.boss_best_score = score
            self.boss_best_grade = grade
        self.save()
        return is_new_best

    def record_password_challenge(self, score):
        """Учитывает прохождение «Испытания» лаборатории паролей. Возвращает True при новом рекорде."""
        self.password_runs += 1
        is_new_best = score > self.password_best
        if is_new_best:
            self.password_best = score
        self.save()
        return is_new_best

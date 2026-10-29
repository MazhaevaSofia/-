"""Загрузка пользовательских сценариев-расследований из JSON.

Формат описан и задокументирован в SCENARIO_FORMAT.md — он позволяет
преподавателям и специалистам добавлять новые уровни, не трогая код
Python: кладёте .json в папку scenarios/, и он появляется в списке
«Пользовательские сценарии».
"""
import json
import os
import sys

SCENARIOS_DIR_NAME = "scenarios"

REQUIRED_TOP_LEVEL_KEYS = ("id", "title", "technique", "description_lines", "analysis_steps", "unlock_action", "quiz")
REQUIRED_STEP_KEYS = ("id", "button_label", "title", "content")
REQUIRED_UNLOCK_KEYS = ("button_label", "prompt_title", "instruction", "command_hint", "success_command", "success_message")


class ScenarioValidationError(ValueError):
    pass


def _scenarios_dir():
    if getattr(sys, "frozen", False):
        # В собранном .exe __file__ указывает во временную распакованную
        # копию (sys._MEIPASS), а не рядом с исполняемым файлом — папку
        # scenarios/ нужно искать там же, где savegame.json (см. save_manager.py)
        root = os.path.dirname(sys.executable)
    else:
        # game/core/scenario_loader.py -> корень проекта на три уровня выше
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, SCENARIOS_DIR_NAME)


def validate_scenario(data):
    """Бросает ScenarioValidationError с понятным сообщением, если схема нарушена."""
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            raise ScenarioValidationError(f"отсутствует обязательное поле '{key}'")

    if not isinstance(data["analysis_steps"], list) or not data["analysis_steps"]:
        raise ScenarioValidationError("'analysis_steps' должен быть непустым списком")
    for i, step in enumerate(data["analysis_steps"]):
        for key in REQUIRED_STEP_KEYS:
            if key not in step:
                raise ScenarioValidationError(f"analysis_steps[{i}]: отсутствует поле '{key}'")

    unlock = data["unlock_action"]
    for key in REQUIRED_UNLOCK_KEYS:
        if key not in unlock:
            raise ScenarioValidationError(f"unlock_action: отсутствует поле '{key}'")

    quiz = data["quiz"]
    questions = quiz.get("questions")
    if not questions or not isinstance(questions, list):
        raise ScenarioValidationError("quiz.questions должен быть непустым списком вопросов")
    for i, q in enumerate(questions):
        if "question" not in q or "options" not in q or "correct" not in q:
            raise ScenarioValidationError(f"quiz.questions[{i}]: нужны поля question/options/correct")
        if not (0 <= q["correct"] < len(q["options"])):
            raise ScenarioValidationError(f"quiz.questions[{i}]: 'correct' вне диапазона options")


def load_scenario(path):
    """Загружает и валидирует один файл сценария. Бросает исключение при ошибке."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate_scenario(data)
    return data


def list_custom_scenarios(directory=None):
    """Возвращает список (path, scenario_dict) для всех валидных .json в scenarios/.

    Повреждённые или не проходящие валидацию файлы пропускаются (с выводом
    предупреждения в консоль), а не роняют игру.
    """
    directory = directory or _scenarios_dir()
    results = []
    if not os.path.isdir(directory):
        return results
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        try:
            results.append((path, load_scenario(path)))
        except (OSError, ValueError, ScenarioValidationError) as e:
            print(f"Пропущен сценарий {name}: {e}")
    return results

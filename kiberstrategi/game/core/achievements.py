"""Определения ачивок и правила их разблокировки.

Сам факт разблокировки хранится в SaveManager (savegame.json) —
здесь только список достижений и функции, решающие, что нового
разблокировано по итогам конкретного события: расследования,
матча режима ПРОТИВ или пользовательского сценария.
"""

SPEED_THRESHOLD_SECONDS = 90

# Порядок в словаре — порядок показа на экране «Достижения».
ACHIEVEMENTS = {
    "perfect_run": {
        "title": "Без единой ошибки",
        "description": "Пройти расследование, ни разу не ошибившись в финальном тесте",
    },
    "speed_runner": {
        "title": "Молниеносно",
        "description": f"Завершить расследование быстрее чем за {SPEED_THRESHOLD_SECONDS} секунд",
    },
    "campaign_complete": {
        "title": "Киберзащитник",
        "description": "Пройти кампанию целиком — с 1 по 7 день",
    },
    "flawless_campaign": {
        "title": "Идеальное прохождение",
        "description": "Пройти всю кампанию без единой ошибки в тестах",
    },
    "versus_winner": {
        "title": "Победитель",
        "description": "Выиграть матч в режиме «Атакующий vs Защитник» на стороне Защитника",
    },
    "ai_slayer": {
        "title": "Сильнее машины",
        "description": "Обыграть ИИ-атакующего в режиме «Игрок против ИИ»",
    },
    "explorer": {
        "title": "Первопроходец",
        "description": "Пройти пользовательский сценарий",
    },
    "phish_perfect": {
        "title": "Ни один фишинг не прошёл",
        "description": "Верно определить все сообщения раунда в режиме «Фишинг-детектор»",
    },
    "phish_veteran": {
        "title": "Бдительный сотрудник",
        "description": "Сыграть 5 раундов в режиме «Фишинг-детектор»",
    },
    "pw_expert": {
        "title": "Знаток паролей",
        "description": "Набрать 7 очков из 8 в «Испытании» лаборатории паролей",
    },
    "pw_phrase": {
        "title": "Парольная фраза",
        "description": "Сгенерировать в лаборатории паролей фразу стойкостью от 56 бит",
    },
    "boss_victory": {
        "title": "Чёрный лёд растаял",
        "description": "Победить группировку BLACK ICE на босс-уровне",
    },
    "boss_flawless": {
        "title": "Ни одной царапины",
        "description": "Победить босса, не потеряв ни единицы целостности сети",
    },
}

PHISH_VETERAN_ROUNDS = 5


def evaluate_investigation(mistakes, score, elapsed_seconds):
    """Достижения по итогам одного расследования (любого — кампания, ПРОТИВ, своё)."""
    unlocked = []
    if score and score > 0 and not mistakes:
        unlocked.append("perfect_run")
    if elapsed_seconds is not None and elapsed_seconds < SPEED_THRESHOLD_SECONDS:
        unlocked.append("speed_runner")
    return unlocked


def evaluate_campaign(num_levels_played, mistake_tracker):
    """Достижения по итогам полного прохождения кампании (экран титров)."""
    unlocked = []
    if num_levels_played >= 7:
        unlocked.append("campaign_complete")
        if not mistake_tracker.has_mistakes:
            unlocked.append("flawless_campaign")
    return unlocked


def evaluate_versus_result(mode, winner):
    """Достижения по итогам матча режима «Атакующий vs Защитник»."""
    unlocked = []
    if winner == "defender":
        unlocked.append("versus_winner")
        if mode == "pve":
            unlocked.append("ai_slayer")
    return unlocked


def evaluate_phishing_round(session, rounds_played):
    """Достижения по итогам раунда «Фишинг-детектора»; rounds_played включает только что сыгранный."""
    unlocked = []
    if session.total and session.correct_count == session.total:
        unlocked.append("phish_perfect")
    if rounds_played >= PHISH_VETERAN_ROUNDS:
        unlocked.append("phish_veteran")
    return unlocked


def evaluate_boss(fight):
    """Достижения по итогам босс-уровня."""
    unlocked = []
    if fight.outcome == "victory":
        unlocked.append("boss_victory")
        if fight.flawless:
            unlocked.append("boss_flawless")
    return unlocked


PASSWORD_EXPERT_CORRECT = 7
PASSPHRASE_BITS = 56


def evaluate_password_challenge(correct_count):
    return ["pw_expert"] if correct_count >= PASSWORD_EXPERT_CORRECT else []


def evaluate_passphrase(bits):
    return ["pw_phrase"] if bits >= PASSPHRASE_BITS else []

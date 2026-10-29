"""Реестр техник и состояние матча «Атакующий vs Защитник».

Каждый раунд переиспользует существующий сценарий-расследование как есть
(PhishingMinigame и т.д.) — они уже самодостаточны и вызывают
on_complete(success, score, mistakes), поэтому режим ПРОТИВ построен поверх
них без единой правки их кода.
"""

MAX_SCORE_PER_ROUND = 30  # 3 вопроса финального квиза x 10 очков


def _load_phishing(w, h, on_complete):
    from ..scenes.phishing_minigame import PhishingMinigame
    return PhishingMinigame(w, h, on_complete, None)


def _load_valid_accounts(w, h, on_complete):
    from ..scenes.valid_account_minigame import ValidAccountsMinigame
    return ValidAccountsMinigame(w, h, on_complete, None)


def _load_process_injection(w, h, on_complete):
    from ..scenes.process_injection_minigame import ProcessInjectionMinigame
    return ProcessInjectionMinigame(w, h, on_complete, None)


def _load_dns_c2(w, h, on_complete):
    from ..scenes.dns_c2_minigame import DNSC2Minigame
    return DNSC2Minigame(w, h, on_complete)


def _load_dos(w, h, on_complete):
    from ..scenes.dos_analysis import DoSAnalysis
    return DoSAnalysis(w, h, on_complete, None)


def _load_meterpreter(w, h, on_complete):
    from ..scenes.meterpreter_analysis import MeterpreterAnalysis
    return MeterpreterAnalysis(w, h, on_complete, None)


def _load_ssh_bruteforce(w, h, on_complete):
    from ..scenes.ssh_bruteforce_analysis import SSHBruteforceAnalysis
    return SSHBruteforceAnalysis(w, h, on_complete)


# Ключ -> (человекочитаемое название, "лёгкая"/"сложная" сложность для ИИ, загрузчик сцены)
TECHNIQUES = {
    "phishing": {"label": "Фишинг (T1566)", "tier": "easy", "loader": _load_phishing},
    "valid_accounts": {"label": "Valid Accounts (T1078)", "tier": "easy", "loader": _load_valid_accounts},
    "process_injection": {"label": "Process Injection (T1055)", "tier": "hard", "loader": _load_process_injection},
    "dns_c2": {"label": "DNS C2 (T1071.004)", "tier": "hard", "loader": _load_dns_c2},
    "dos": {"label": "DoS (T1498)", "tier": "hard", "loader": _load_dos},
    "meterpreter": {"label": "Meterpreter", "tier": "hard", "loader": _load_meterpreter},
    "ssh_bruteforce": {"label": "Брутфорс SSH (T1110)", "tier": "hard", "loader": _load_ssh_bruteforce},
}

ROUNDS_PER_MATCH = 4


class VersusMatch:
    """Состояние одного матча: mode = 'pvp' (hotseat) или 'pve' (против ИИ)."""

    def __init__(self, mode, attacker_name="Атакующий", defender_name="Защитник"):
        self.mode = mode
        self.attacker_name = attacker_name
        self.defender_name = defender_name
        self.round_number = 0
        self.attacker_score = 0
        self.defender_score = 0
        self.used_techniques = []
        self.rounds_log = []  # [{"technique": key, "label": str, "defender_score": int}]
        self.finished = False

    def available_techniques(self):
        return [key for key in TECHNIQUES if key not in self.used_techniques]

    def has_next_round(self):
        return self.round_number < ROUNDS_PER_MATCH and bool(self.available_techniques())

    def record_round(self, technique_key, defender_score):
        defender_score = defender_score or 0
        self.used_techniques.append(technique_key)
        self.round_number += 1
        self.defender_score += defender_score
        self.attacker_score += max(0, MAX_SCORE_PER_ROUND - defender_score)
        self.rounds_log.append({
            "technique": technique_key,
            "label": TECHNIQUES[technique_key]["label"],
            "defender_score": defender_score,
        })
        if not self.has_next_round():
            self.finished = True

    def winner(self):
        if self.attacker_score > self.defender_score:
            return "attacker"
        if self.defender_score > self.attacker_score:
            return "defender"
        return "draw"

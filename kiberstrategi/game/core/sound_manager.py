"""Звуковые эффекты, синтезированные на лету через numpy — без внешних
аудиофайлов (лицензионно чисто, ничего не нужно ни скачивать, ни
записывать). Раньше в игре не было звука вообще.

Если звуковое устройство недоступно (headless-тесты, CI, машина без
колонок), SoundManager тихо отключает себя, и play() становится
безопасным no-op — отсутствие звука не должно ронять игру.
"""
import numpy as np
import pygame

SAMPLE_RATE = 44100


def _tone(freq, duration, volume=0.5, fade=0.015):
    """Один синусоидальный тон с коротким fade in/out, чтобы не щёлкал на стыках."""
    n = max(1, int(SAMPLE_RATE * duration))
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.sin(2 * np.pi * freq * t)
    fade_n = min(n // 2, max(1, int(SAMPLE_RATE * fade)))
    envelope = np.ones(n)
    envelope[:fade_n] = np.linspace(0, 1, fade_n)
    envelope[-fade_n:] = np.linspace(1, 0, fade_n)
    return wave * envelope * volume


def _sequence(*notes):
    """Склеивает несколько нот (freq, duration, volume) в одну короткую мелодию."""
    return np.concatenate([_tone(*note) for note in notes])


def _to_sound(samples):
    audio = np.clip(samples, -1.0, 1.0)
    audio_i16 = (audio * 32767).astype(np.int16)
    stereo = np.repeat(audio_i16.reshape(-1, 1), 2, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


class SoundManager:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self._init_mixer()

    def _init_mixer(self):
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
            self._build_sounds()
            self.enabled = True
        except (pygame.error, Exception):
            self.enabled = False

    def _build_sounds(self):
        # Короткий нейтральный щелчок — используется буквально везде (см. game/ui/button.py)
        self.sounds["click"] = _to_sound(_tone(880, 0.03, volume=0.2))
        # Верный/неверный ответ в квизе
        self.sounds["correct"] = _to_sound(_sequence((659, 0.09, 0.35), (988, 0.15, 0.35)))
        self.sounds["wrong"] = _to_sound(_sequence((220, 0.16, 0.35), (165, 0.2, 0.3)))
        # Настоящий алерт угрозы — привлекает внимание сильнее, чем шум
        self.sounds["alert"] = _to_sound(_sequence((740, 0.11, 0.4), (0.1, 0.03, 0), (740, 0.11, 0.4)))
        # Фоновый шум — тише и мягче, чтобы отличаться на слух, а не только по цвету
        self.sounds["noise"] = _to_sound(_tone(500, 0.07, volume=0.12))
        # Разблокирована ачивка
        self.sounds["achievement"] = _to_sound(_sequence((523, 0.09, 0.32), (659, 0.09, 0.32), (784, 0.18, 0.38)))
        # Успешное завершение дня/уровня
        self.sounds["success"] = _to_sound(_sequence((523, 0.1, 0.32), (659, 0.1, 0.32), (784, 0.1, 0.32), (1047, 0.24, 0.4)))

    def play(self, name):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def set_enabled(self, value):
        """Глобальный мьют/анмьют (задел под будущий переключатель в настройках)."""
        self.enabled = bool(value) and bool(self.sounds)


_manager = None


def get_manager():
    global _manager
    if _manager is None:
        _manager = SoundManager()
    return _manager


def play(name):
    get_manager().play(name)

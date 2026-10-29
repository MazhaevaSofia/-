# [file name]: game_manager.py
# [file content begin]
import pygame
import os
import datetime
from .scene_manager import SceneManager
from .save_manager import SaveManager
from .mistake_tracker import MistakeTracker
from .versus_match import VersusMatch, TECHNIQUES as VERSUS_TECHNIQUES, ROUNDS_PER_MATCH
from .ai_attacker import AIAttacker
from . import achievements
from .case_log import grade_for_score
from ..scenes.image_scene import ImageScene

# Название техники для каждого дня — используется в разборе ошибок
DAY_TECHNIQUE_LABELS = {
    1: "Фишинг (T1566)",
    2: "Valid Accounts (T1078)",
    3: "Process Injection (T1055)",
    4: "DNS C2 (T1071.004)",
    5: "DoS (T1498)",
    6: "Meterpreter",
    7: "Брутфорс SSH (T1110)",
}

class GameManager:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scene_manager = SceneManager()
        
        # Инициализация сцен
        from ..scenes.splash_screen import SplashScreen
        from ..scenes.image_scene import ImageScene
        from ..scenes.cutscene import Cutscene
        from ..scenes.desktop import DesktopScene
        
        # После заставки — вступительная катсцена «Киберзащитник», затем выбор уровня
        self.splash_screen = SplashScreen(screen_width, screen_height, self.show_intro_cutscene)
        self.intro_cutscene = Cutscene(screen_width, screen_height, self.show_level_select, scene_id=0)
        # Картинки 1–4 и катсцена показываются после выбора уровня (в intro для уровня)
        self.main_image = ImageScene(screen_width, screen_height, "main.jpg", 3000, self.show_level_select)
        self.first_image = ImageScene(screen_width, screen_height, "1.jpg", 3000, self.show_second_image)
        self.second_image = ImageScene(screen_width, screen_height, "2.jpg", 3000, self.show_third_image)
        self.third_image = ImageScene(screen_width, screen_height, "3.jpg", 3000, self.show_cutscene)
        self.cutscene = Cutscene(screen_width, screen_height, self._after_intro_cutscene, scene_id=1)
        
        self.desktop = DesktopScene(screen_width, screen_height, self)
        
        from ..scenes.level_select import LevelSelectScene
        from ..scenes.level_complete import LevelCompleteScene
        self.level_select = LevelSelectScene(screen_width, screen_height, self)
        self.LevelCompleteScene = LevelCompleteScene
        
        # Начинаем с заставки, после неё — сразу выбор уровня (до картинок дня 1)
        self.scene_manager.push_scene(self.splash_screen)
        
        # Состояние игры
        self.current_day = 1
        self.current_level = None  # 1, 2 или 3 — выбранный уровень; None при полном прохождении
        self.completed_objectives = []
        self.current_image_index = 0
        self.pending_level_id = None
        self.pending_start_day = None
        self._intro_index = 0
        # Накопление очков за игру (викторины по 30 за уровень)
        self.total_game_score = 0
        self.initial_start_day = 1  # день текущего уровня (1/3/6)
        self.min_start_day = 1  # самый ранний день за сессию — для расчёта макс. баллов в титрах
        self.quit_requested = False
        # Прогресс, сохраняемый между запусками игры (game/data/savegame.json)
        self.save_manager = SaveManager()
        # Уже пройденные уровни (при выходе в главное меню с экрана «Уровень пройден»)
        self.completed_levels = set(self.save_manager.completed_levels)
        # Разбор ошибок викторин за текущую сессию (обнуляется при начале уровня)
        self.mistake_tracker = MistakeTracker()
        # Режим «Атакующий vs Защитник» (хотсит/против ИИ) — см. show_versus_menu()
        self.versus_match = None
        self.versus_ai = None
        self._versus_newly_unlocked = []
        # Момент запуска текущего расследования (для ачивки «Молниеносно»)
        self.investigation_started_at = None

    def _mark_investigation_start(self):
        """Засечь момент запуска расследования — для ачивки «Молниеносно»."""
        self.investigation_started_at = pygame.time.get_ticks()

    def _investigation_elapsed_seconds(self):
        if self.investigation_started_at is None:
            return None
        return (pygame.time.get_ticks() - self.investigation_started_at) / 1000.0

    def _record_case(self, score, max_score=30):
        """Добавить запись о завершённом расследовании на доску дел."""
        tag, grade_text = grade_for_score(score, max_score)
        self.save_manager.record_case({
            "technique": DAY_TECHNIQUE_LABELS.get(self.current_day, f"День {self.current_day}"),
            "score": score,
            "max_score": max_score,
            "grade_tag": tag,
            "grade_text": grade_text,
            "date": datetime.date.today().isoformat(),
        })

    def _unlock_achievements(self, achievement_ids):
        """Разблокировать ачивки и показать тост на рабочем столе для новых."""
        newly = self.save_manager.unlock_achievements(achievement_ids)
        if newly and hasattr(self.desktop, "show_achievement_toast"):
            titles = ", ".join(achievements.ACHIEVEMENTS[a]["title"] for a in newly)
            self.desktop.show_achievement_toast(titles)
        return newly

    def mark_level_completed(self, level_id):
        """Отметить уровень пройденным — в текущей сессии и в сохранении на диске."""
        self.completed_levels.add(level_id)
        self.save_manager.mark_level_completed(level_id)

    def request_quit(self):
        """Вызов из титров по кнопке «Закрыть игру»."""
        self.quit_requested = True
    
    def set_screen_size(self, w, h):
        """Изменить размер окна (вызов при VIDEORESIZE)."""
        self.screen_width = w
        self.screen_height = h
        self.scene_manager.notify_resize(w, h)
    
    def handle_event(self, event):
        self.scene_manager.handle_event(event)
    
    def update(self):
        self.scene_manager.update()
    
    def draw(self, screen):
        self.scene_manager.draw(screen)
    
    def show_main_image(self):
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.main_image)
    
    def show_first_image(self):
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.first_image)
    
    def show_second_image(self):
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.second_image)
    
    def show_third_image(self):
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.third_image)
    
    def show_intro_cutscene(self):
        """Показать вступительную катсцену «Киберзащитник» перед выбором уровня."""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.intro_cutscene)
    
    def show_cutscene(self):
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.cutscene)
    
    def _after_intro_cutscene(self):
        """После катсцены вводной (без 4.jpg) — сразу запуск уровня."""
        self.scene_manager.pop_scene()
        self.start_level(self.pending_level_id, self.pending_start_day)
    
    def show_level_select(self):
        """Показать экран выбора уровня (дни 1–2, 3–5, 6–7). Картинки 1–4 показываются после выбора уровня."""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.level_select)
        self.min_start_day = 7  # сброс: следующий start_level задаст начало новой сессии
    
    def show_intro_for_level(self, level_id, start_day):
        """После выбора уровня показать вводную последовательность (1.jpg → 2 → 3 → катсцена), затем запустить уровень."""
        self.pending_level_id = level_id
        self.pending_start_day = start_day
        self._intro_index = 0
        self.scene_manager.pop_scene()
        self._push_next_intro_scene()
    
    def _on_intro_step(self):
        """Переход к следующей картинке/катсцене вводной последовательности."""
        self.scene_manager.pop_scene()
        self._intro_index += 1
        self._push_next_intro_scene()
    
    def _on_intro_step_final(self):
        """Конец вводной последовательности — запуск выбранного уровня."""
        self.scene_manager.pop_scene()
        self.start_level(self.pending_level_id, self.pending_start_day)
    
    def _push_next_intro_scene(self):
        """Показать следующую сцену вводной последовательности (1.jpg, 2.jpg, 3.jpg, катсцена). Без 4.jpg."""
        from ..scenes.image_scene import ImageScene
        from ..scenes.cutscene import Cutscene
        if self._intro_index == 0:
            scene = ImageScene(self.screen_width, self.screen_height, "1.jpg", 3000, self._on_intro_step)
        elif self._intro_index == 1:
            scene = ImageScene(self.screen_width, self.screen_height, "2.jpg", 3000, self._on_intro_step)
        elif self._intro_index == 2:
            scene = ImageScene(self.screen_width, self.screen_height, "3.jpg", 3000, self._on_intro_step)
        elif self._intro_index == 3:
            scene = Cutscene(self.screen_width, self.screen_height, self._on_intro_step_final, scene_id=1)
        else:
            return
        self.scene_manager.push_scene(scene)
    
    def show_level_complete(self):
        """Показать экран «Уровень пройден»: следующий уровень или выбор уровня."""
        if self.current_level is None or self.current_level >= 3:
            self.show_level_select()
            return
        self.scene_manager.pop_scene()
        scene = self.LevelCompleteScene(self.screen_width, self.screen_height, self, self.current_level)
        self.scene_manager.push_scene(scene)
    
    def start_level(self, level_id, start_day):
        """Начать выбранный уровень с указанного дня."""
        self.current_level = level_id
        self.current_day = start_day
        self.initial_start_day = start_day
        self.min_start_day = min(self.min_start_day, start_day)  # для макс. баллов в титрах при прохождении 1→2→3
        self.total_game_score = 0
        self.completed_objectives = []
        self.mistake_tracker.clear()
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)

    def start_day_one_desktop(self):
        """Запуск рабочего стола дня 1"""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)
    
    def complete_day_one(self):
        """Завершение дня 1 с показом картинок (5.jpg, 6.jpg)"""
        self.current_day = 2
        self.current_image_index = 0
        self.scene_manager.pop_scene()
        self.show_day_images("day1_complete")
    
    def complete_day_two(self):
        """Завершение дня 2 с показом картинок (8.jpg, 9.jpg)"""
        self.current_day = 3
        self.current_image_index = 0
        self.scene_manager.pop_scene()
        self.show_day_images("day2_complete")
    
    def complete_day_three(self):
        """Завершение дня 3 с показом картинок (11.jpg, 12.jpg)"""
        self.current_day = 4
        self.current_image_index = 0
        self.scene_manager.pop_scene()
        self.show_day_images("day3_complete")

    def complete_day_four(self):
        """Завершение дня 4 с показом картинок (14.jpg, 15.jpg) и переходом к дню 5"""
        self.current_day = 5
        self.current_image_index = 0
        self.scene_manager.pop_scene()
        self.show_day_images("day4_complete")

    def complete_day_five(self):
        """Завершение дня 5 с показом 3 картинок (17.jpg, 18.jpg, 19.jpg) и переходом к дню 6"""
        self.current_day = 6
        self.current_image_index = 0
        self.scene_manager.pop_scene()
        self.show_day_images("day5_complete")

    def complete_day_six(self):
        """Завершение дня 6 с показом 3 картинок (20.jpg, 21.jpg, 22.jpg) и переходом к дню 7"""
        self.current_day = 7
        self.current_image_index = 0
        self.scene_manager.pop_scene()
        self.show_day_images("day6_complete")

    def complete_day_seven(self):
        """Завершение дня 7 с показом финальных картинок и титров"""
        self.current_day = 8
        self.current_image_index = 0
        self.scene_manager.pop_scene()
        self.show_final_sequence()
    
    def show_day_images(self, day_type):
        """Показ картинок после завершения дня"""
        image_sequences = {
            "day1_complete": [
                {"image": "5.jpg", "duration": 3000},
                {"image": "6.jpg", "duration": 3000}
            ],
            "day2_complete": [
                {"image": "8.jpg", "duration": 3000},
                {"image": "9.jpg", "duration": 3000}
            ],
            "day3_complete": [
                {"image": "11.jpg", "duration": 3000},
                {"image": "12.jpg", "duration": 3000}
            ],
            "day4_complete": [
                {"image": "14.jpg", "duration": 3000},
                {"image": "15.jpg", "duration": 3000}
            ],
            "day5_complete": [],
            "day6_complete": [],
        }
        
        # Пустая последовательность (картинки убраны) — сразу переход
        if len(image_sequences[day_type]) == 0:
            if day_type == "day5_complete":
                if self.current_level == 2:
                    self.show_level_complete()
                else:
                    self.start_day_six_desktop()
            elif day_type == "day6_complete":
                self.start_day_seven_desktop()
            return
        
        if self.current_image_index < len(image_sequences[day_type]):
            image_info = image_sequences[day_type][self.current_image_index]
            
            # Определяем колбэк для последней картинки в последовательности
            if self.current_image_index == len(image_sequences[day_type]) - 1:
                if day_type == "day1_complete":
                    callback = self.start_day_two_desktop
                elif day_type == "day2_complete":
                    # Уровень 1: экран «Уровень пройден» (следующий уровень или выбор)
                    callback = self.show_level_complete if self.current_level == 1 else self.start_day_three_desktop
                elif day_type == "day3_complete":
                    callback = self.start_day_four_desktop
                elif day_type == "day4_complete":
                    callback = self.start_day_five_desktop
                elif day_type == "day5_complete":
                    # Уровень 2: экран «Уровень пройден» (следующий уровень или выбор)
                    callback = self.show_level_complete if self.current_level == 2 else self.start_day_six_desktop
                elif day_type == "day6_complete":
                    callback = self.start_day_seven_desktop
                else:
                    callback = self.show_next_day_image
            else:
                callback = self.show_next_day_image
            
            # Создаем сцену с картинкой
            scene = ImageScene(
                self.screen_width, 
                self.screen_height, 
                image_info["image"], 
                image_info["duration"], 
                callback
            )
            
            # Сохраняем текущий тип дня для использования в колбэке
            self.current_day_type = day_type
            self.scene_manager.push_scene(scene)
    
    def show_next_day_image(self):
        """Переход к следующей картинке в последовательности дня"""
        self.current_image_index += 1
        self.scene_manager.pop_scene()
        self.show_day_images(self.current_day_type)
    
    def show_final_sequence(self):
        """Показ финальной последовательности, затем титры"""
        self.show_credits()
    
    def show_next_final_image(self):
        """Переход к следующей финальной картинке"""
        self.current_image_index += 1
        self.scene_manager.pop_scene()
        self.show_final_sequence()
    
    def show_credits(self):
        """Показ титров с общим баллом и полем для имени"""
        from ..scenes.credits_scene import CreditsScene
        self.scene_manager.pop_scene()
        # Прохождение дня 7 не проходит через show_level_complete (это последний уровень),
        # поэтому уровень 3 отмечается пройденным здесь.
        if self.current_level is not None:
            self.mark_level_completed(self.current_level)
        self.save_manager.record_score(self.total_game_score)
        # Макс. баллов по самому раннему дню сессии: 1→7 уровней (210), 3→5 (150), 6→2 (60)
        num_levels = 7 - self.min_start_day + 1
        max_score = num_levels * 30
        newly = self.save_manager.unlock_achievements(achievements.evaluate_campaign(num_levels, self.mistake_tracker))
        new_titles = [achievements.ACHIEVEMENTS[a]["title"] for a in newly]
        credits_scene = CreditsScene(
            self.screen_width, self.screen_height,
            self.show_final_image,
            on_quit_callback=self.request_quit,
            total_score=self.total_game_score,
            max_score=max_score,
            best_score=self.save_manager.best_score,
            on_review_mistakes_callback=self.show_mistake_review if self.mistake_tracker.has_mistakes else None,
            new_achievements=new_titles,
            unlocked_achievement_ids=self.save_manager.unlocked_achievements,
            new_achievement_ids=newly
        )
        self.scene_manager.push_scene(credits_scene)

    def show_mistake_review(self):
        """Показать разбор неверных ответов викторин за сессию."""
        from ..scenes.mistake_review_scene import MistakeReviewScene
        scene = MistakeReviewScene(
            self.screen_width, self.screen_height,
            self.mistake_tracker.entries,
            self._close_mistake_review
        )
        self.scene_manager.push_scene(scene)

    def _close_mistake_review(self):
        self.scene_manager.pop_scene()

    def show_achievements(self):
        """Показать экран «Достижения» со списком всех ачивок и их статусом."""
        from ..scenes.achievements_scene import AchievementsScene
        self.scene_manager.pop_scene()
        scene = AchievementsScene(
            self.screen_width, self.screen_height,
            self.save_manager.unlocked_achievements,
            self.show_level_select
        )
        self.scene_manager.push_scene(scene)

    def show_case_board(self):
        """Показать доску расследований — историю пройденных дел кампании."""
        from ..scenes.case_board_scene import CaseBoardScene
        self.scene_manager.pop_scene()
        scene = CaseBoardScene(
            self.screen_width, self.screen_height,
            self.save_manager.case_log,
            self.show_level_select
        )
        self.scene_manager.push_scene(scene)

    def show_phishing_detector(self):
        """Открыть отдельный режим «Фишинг-детектор» из выбора уровня."""
        from ..scenes.phishing_detector_scene import PhishingDetectorScene
        self.scene_manager.pop_scene()
        scene = PhishingDetectorScene(
            self.screen_width, self.screen_height,
            self.save_manager,
            self.show_level_select
        )
        self.scene_manager.push_scene(scene)

    def show_password_lab(self):
        """Открыть «Лабораторию паролей» из выбора уровня."""
        from ..scenes.password_lab_scene import PasswordLabScene
        self.scene_manager.pop_scene()
        scene = PasswordLabScene(
            self.screen_width, self.screen_height,
            self.save_manager,
            self.show_level_select
        )
        self.scene_manager.push_scene(scene)

    def show_boss_level(self):
        """Открыть босс-уровень «Операция «Чёрный лёд»» из выбора уровня."""
        from ..scenes.boss_level_scene import BossLevelScene
        self.scene_manager.pop_scene()
        scene = BossLevelScene(
            self.screen_width, self.screen_height,
            self.save_manager,
            self.show_level_select,
            completed_levels=self.completed_levels
        )
        self.scene_manager.push_scene(scene)

    def show_credits_from_shutdown(self):
        """Показ титров с текущим баллом при выборе «Выключить» в меню Пуск (без смены сцены под десктопом)."""
        from ..scenes.credits_scene import CreditsScene
        num_levels = 7 - self.min_start_day + 1
        max_score = num_levels * 30
        credits_scene = CreditsScene(
            self.screen_width, self.screen_height,
            lambda: None,
            on_quit_callback=self.request_quit,
            total_score=self.total_game_score,
            max_score=max_score,
            on_review_mistakes_callback=self.show_mistake_review if self.mistake_tracker.has_mistakes else None,
            unlocked_achievement_ids=self.save_manager.unlocked_achievements
        )
        self.scene_manager.push_scene(credits_scene)

    def show_final_image(self):
        """Показ финальной картинки 25.jpeg"""
        self.scene_manager.pop_scene()
        final_image = ImageScene(self.screen_width, self.screen_height, "25.jpg", 0, None)  # 0 - бесконечная длительность
        self.scene_manager.push_scene(final_image)
    
    def start_day_two_desktop(self):
        """Запуск рабочего стола для дня 2"""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)
    
    def start_day_three_desktop(self):
        """Запуск рабочего стола для дня 3"""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)
    
    def start_day_four_desktop(self):
        """Запуск рабочего стола для дня 4 (DNS C-2)"""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)

    def start_day_five_desktop(self):
        """Запуск рабочего стола для дня 5 (DoS)"""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)

    def start_day_six_desktop(self):
        """Запуск рабочего стола для дня 6 (Meterpreter)"""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)

    def start_day_seven_desktop(self):
        """Запуск рабочего стола для дня 7 (SSH Bruteforce)"""
        self.scene_manager.pop_scene()
        self.scene_manager.push_scene(self.desktop)
        self.desktop.initialize_day(self.current_day)
    
    # Старые методы для обратной совместимости с desktop.py
    def start_day_two(self):
        """Совместимость со старым кодом - вызывает complete_day_one"""
        self.complete_day_one()
    
    def start_day_three(self):
        """Совместимость со старым кодом - вызывает complete_day_two"""
        self.complete_day_two()
    
    def start_day_four(self):
        """Совместимость со старым кодом - вызывает complete_day_three"""
        self.complete_day_three()
    
    def start_day_five(self):
        """Совместимость со старым кодом - вызывает complete_day_four"""
        self.complete_day_four()
    
    def start_phishing_investigation(self):
        from ..scenes.phishing_minigame import PhishingMinigame
        self._mark_investigation_start()
        phishing_minigame = PhishingMinigame(self.screen_width, self.screen_height, self.return_to_desktop, self)
        self.scene_manager.push_scene(phishing_minigame)

    def start_valid_accounts_investigation(self):
        from ..scenes.valid_account_minigame import ValidAccountsMinigame
        self._mark_investigation_start()
        valid_accounts_minigame = ValidAccountsMinigame(self.screen_width, self.screen_height, self.return_to_desktop, self)
        self.scene_manager.push_scene(valid_accounts_minigame)
    
    def open_internet_browser(self):
        from ..scenes.internet_browser import InternetBrowser
        internet_browser = InternetBrowser(self.screen_width, self.screen_height, self._close_browser)
        self.scene_manager.push_scene(internet_browser)

    def _close_browser(self, _success=True):
        """Закрыть браузер без засчитывания выполнения уровня (браузер — только справка)."""
        self.scene_manager.pop_scene()
    
    def try_show_next_day_button(self):
        """Показать кнопку «Следующий день», если все обязательные действия дня выполнены."""
        if hasattr(self.desktop, 'try_show_next_day_button'):
            self.desktop.try_show_next_day_button()

    def return_to_desktop(self, success, score=None, mistakes=None):
        self.scene_manager.pop_scene()
        if success:
            if score is not None:
                self.total_game_score += score
            if mistakes:
                technique = DAY_TECHNIQUE_LABELS.get(self.current_day, f"День {self.current_day}")
                self.mistake_tracker.record(technique, mistakes)
            if score is not None:
                elapsed = self._investigation_elapsed_seconds()
                self._unlock_achievements(achievements.evaluate_investigation(mistakes, score, elapsed))
                self._record_case(score)
            self.investigation_started_at = None
            if self.current_day == 1:
                self.complete_objective("Расследовать фишинг атаку")
                if hasattr(self.desktop, 'clear_threat_message'):
                    self.desktop.clear_threat_message()
                if hasattr(self.desktop, 'remove_phishing_email_from_windows'):
                    self.desktop.remove_phishing_email_from_windows()
            elif self.current_day == 2:
                self.complete_objective("Расследовать инцидент компрометации учетных записей")
                if hasattr(self.desktop, 'clear_threat_message'):
                    self.desktop.clear_threat_message()
            elif self.current_day == 3:
                self.complete_objective("Расследовать Process Injection атаку")
                if hasattr(self.desktop, 'clear_threat_message'):
                    self.desktop.clear_threat_message()
            elif self.current_day == 4:
                self.complete_objective("Расследовать DNS C2 атаку")
                if hasattr(self.desktop, 'clear_threat_message'):
                    self.desktop.clear_threat_message()
            elif self.current_day == 5:
                self.complete_objective("Расследовать DoS атаку")
                if hasattr(self.desktop, 'clear_threat_message'):
                    self.desktop.clear_threat_message()
            elif self.current_day == 6:
                self.complete_objective("Расследовать атаку с Meterpreter")
                if hasattr(self.desktop, 'clear_threat_message'):
                    self.desktop.clear_threat_message()
            elif self.current_day == 7:
                self.complete_objective("Расследовать брутфорс SSH атаку")
                if hasattr(self.desktop, 'clear_threat_message'):
                    self.desktop.clear_threat_message()
            # Кнопка «Следующий день» только когда все обязательные действия дня выполнены
            self.try_show_next_day_button()
    
    def complete_objective(self, objective_name):
        if objective_name not in self.completed_objectives:
            self.completed_objectives.append(objective_name)

    def start_process_injection_investigation(self):
        """Запуск расследования Process Injection"""
        from ..scenes.process_injection_minigame import ProcessInjectionMinigame
        self._mark_investigation_start()
        process_injection_minigame = ProcessInjectionMinigame(
            self.screen_width, self.screen_height,
            self.return_to_desktop,
            self
        )
        self.scene_manager.push_scene(process_injection_minigame)
    
    def start_dns_c2_investigation(self):
        """Запуск расследования DNS C-2"""
        from ..scenes.dns_c2_minigame import DNSC2Minigame
        self._mark_investigation_start()
        dns_c2_minigame = DNSC2Minigame(
            self.screen_width, self.screen_height, 
            self.return_to_desktop
        )
        self.scene_manager.push_scene(dns_c2_minigame)

    # --- НОВЫЕ МЕТОДЫ ДЛЯ ДНЕЙ 5, 6, 7 ---
    def start_dos_investigation(self):
        """Запуск расследования DoS атаки (День 5)"""
        from ..scenes.dos_analysis import DoSAnalysis
        self._mark_investigation_start()
        dos_analysis = DoSAnalysis(
            self.screen_width, self.screen_height,
            self.return_to_desktop,
            self
        )
        self.scene_manager.push_scene(dos_analysis)

    def start_meterpreter_investigation(self):
        """Запуск расследования атаки с Meterpreter (День 6)"""
        from ..scenes.meterpreter_analysis import MeterpreterAnalysis
        self._mark_investigation_start()
        meterpreter_analysis = MeterpreterAnalysis(
            self.screen_width, self.screen_height,
            self.return_to_desktop,
            self
        )
        self.scene_manager.push_scene(meterpreter_analysis)

    def start_ssh_bruteforce_investigation(self):
        """Запуск расследования брутфорс SSH атаки (День 7)"""
        from ..scenes.ssh_bruteforce_analysis import SSHBruteforceAnalysis
        self._mark_investigation_start()
        ssh_analysis = SSHBruteforceAnalysis(
            self.screen_width, self.screen_height,
            self.return_to_desktop
        )
        self.scene_manager.push_scene(ssh_analysis)
    # --- КОНЕЦ НОВЫХ МЕТОДОВ ---

    # --- РЕЖИМ «АТАКУЮЩИЙ VS ЗАЩИТНИК» (хотсит и против ИИ) ---
    def show_versus_menu(self):
        """Показать экран выбора режима ПРОТИВ (хотсит/ИИ) поверх текущей сцены."""
        from ..scenes.versus_menu_scene import VersusMenuScene
        self.scene_manager.pop_scene()
        scene = VersusMenuScene(
            self.screen_width, self.screen_height,
            on_start_pvp=lambda: self.start_versus_mode("pvp"),
            on_start_pve=lambda: self.start_versus_mode("pve"),
            on_back=self.show_level_select
        )
        self.scene_manager.push_scene(scene)

    def start_versus_mode(self, mode):
        """Начать новый матч режима ПРОТИВ. mode: 'pvp' (хотсит) или 'pve' (против ИИ)."""
        self.versus_match = VersusMatch(mode)
        self.versus_ai = AIAttacker(list(VERSUS_TECHNIQUES.keys())) if mode == "pve" else None
        self._versus_newly_unlocked = []
        self.scene_manager.pop_scene()
        self._versus_next_round()

    def _versus_next_round(self):
        from ..scenes.versus_round_intro_scene import VersusRoundIntroScene
        match = self.versus_match
        available = match.available_techniques()
        ai_pick = self.versus_ai.choose(available) if match.mode == "pve" else None
        scene = VersusRoundIntroScene(
            self.screen_width, self.screen_height,
            match.round_number + 1, ROUNDS_PER_MATCH, available,
            self._versus_technique_ready, ai_pick=ai_pick
        )
        self.scene_manager.push_scene(scene)

    def _versus_technique_ready(self, technique_key):
        self.scene_manager.pop_scene()
        self._mark_investigation_start()
        loader = VERSUS_TECHNIQUES[technique_key]["loader"]
        scene = loader(
            self.screen_width, self.screen_height,
            lambda success, score=None, mistakes=None: self._versus_round_complete(technique_key, success, score, mistakes)
        )
        self.scene_manager.push_scene(scene)

    def _versus_round_complete(self, technique_key, success, score=None, mistakes=None):
        self.scene_manager.pop_scene()
        match = self.versus_match
        defender_score = score if success and score is not None else 0
        elapsed = self._investigation_elapsed_seconds()
        self.investigation_started_at = None
        round_unlocks = self.save_manager.unlock_achievements(
            achievements.evaluate_investigation(mistakes, defender_score, elapsed)
        )
        self._versus_newly_unlocked.extend(round_unlocks)
        match.record_round(technique_key, defender_score)
        if match.mode == "pve":
            self.versus_ai.record_result(technique_key, defender_score)
        if match.finished:
            match_unlocks = self.save_manager.unlock_achievements(
                achievements.evaluate_versus_result(match.mode, match.winner())
            )
            self._versus_newly_unlocked.extend(match_unlocks)
            titles = [achievements.ACHIEVEMENTS[a]["title"] for a in self._versus_newly_unlocked]
            from ..scenes.versus_result_scene import VersusResultScene
            scene = VersusResultScene(self.screen_width, self.screen_height, match, self.show_versus_menu, new_achievements=titles)
            self.scene_manager.push_scene(scene)
        else:
            self._versus_next_round()
    # --- КОНЕЦ РЕЖИМА «АТАКУЮЩИЙ VS ЗАЩИТНИК» ---

    # --- ПОЛЬЗОВАТЕЛЬСКИЕ СЦЕНАРИИ (открытый JSON-формат, см. SCENARIO_FORMAT.md) ---
    def show_custom_scenarios(self):
        from ..scenes.custom_scenarios_scene import CustomScenariosScene
        self.scene_manager.pop_scene()
        scene = CustomScenariosScene(
            self.screen_width, self.screen_height,
            on_select=self._launch_custom_scenario,
            on_back=self.show_level_select
        )
        self.scene_manager.push_scene(scene)

    def _launch_custom_scenario(self, scenario_data):
        from ..scenes.data_driven_investigation_scene import DataDrivenInvestigationScene
        self.scene_manager.pop_scene()
        on_complete = lambda success, score=None, mistakes=None: self._custom_scenario_complete(scenario_data, success, score, mistakes)
        scene = DataDrivenInvestigationScene(self.screen_width, self.screen_height, scenario_data, on_complete)
        self.scene_manager.push_scene(scene)

    def _custom_scenario_complete(self, scenario_data, success, score=None, mistakes=None):
        if success and mistakes:
            self.mistake_tracker.record(scenario_data.get("title", "Пользовательский сценарий"), mistakes)
        if success and score:
            self.save_manager.unlock_achievements(["explorer"] + achievements.evaluate_investigation(mistakes, score, None))
        self.show_custom_scenarios()
    # --- КОНЕЦ ПОЛЬЗОВАТЕЛЬСКИХ СЦЕНАРИЕВ ---
# [file content end]
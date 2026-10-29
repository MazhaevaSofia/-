class SceneManager:
    def __init__(self):
        self.scenes = []
    
    def push_scene(self, scene):
        """Добавить сцену поверх текущей"""
        self.scenes.append(scene)
    
    def pop_scene(self):
        """Убрать верхнюю сцену"""
        if self.scenes:
            return self.scenes.pop()
        return None
    
    def get_current_scene(self):
        """Получить текущую активную сцену"""
        if self.scenes:
            return self.scenes[-1]
        return None
    
    def handle_event(self, event):
        """Передать событие активной сцене"""
        current_scene = self.get_current_scene()
        if current_scene:
            result = current_scene.handle_event(event)
            if result:
                return True
        return False
    
    def update(self):
        """Обновить активную сцену"""
        current_scene = self.get_current_scene()
        if current_scene:
            current_scene.update()
    
    def draw(self, screen):
        """Отрисовать все сцены (от нижней к верхней)"""
        for scene in self.scenes:
            scene.draw(screen)
    
    def notify_resize(self, w, h):
        """Уведомить все сцены об изменении размера окна"""
        for scene in self.scenes:
            if hasattr(scene, 'on_resize'):
                scene.on_resize(w, h)

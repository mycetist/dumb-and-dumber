import pyray as pr
from abc import ABC, abstractmethod

pr.init_window(800, 600, "demo")
pr.set_target_fps(60)

class Entity(ABC):
    @abstractmethod
    def draw(self):
        ...

    @abstractmethod
    def update(self, dt: float):
        ...
    

class Block(Entity):
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def update(self, dt: float):
        pass

    def draw(self):
        pr.draw_rectangle(self.x, self.y, self.w, self.h, pr.GREEN)

level_map = [
    (0, 300, 200, 200),
    (500, 400, 500, 200),
    (1100, 500, 600, 100),
    (1300, 600, 600, 100),
]

class Level(Entity):
    def __init__(self, level_map: list[tuple[int, int]]):
        self.layout: list[Block] = []
        for pos in level_map:
            self.layout.append(Block(*pos))

    def update(self, dt: float):
        pass

    def draw(self):
        for obj in self.layout:
            obj.draw()


class Player(Entity):
    def __init__(self):
        self.x: float = 50
        self.y: float = 50
        self.w: float = 50
        self.h: float = 100

        self.gravity: float = 36
        self.jump_strength: float = 1000
        self.walk_speed: float = 600
        self.y_speed: float = 0
        self.x_speed: float = 0

        self.grounded: bool = False

    def update(self, dt: float, level: Level):
        key_left = pr.is_key_down(pr.KeyboardKey.KEY_A) or pr.is_key_down(pr.KeyboardKey.KEY_LEFT)
        key_right = pr.is_key_down(pr.KeyboardKey.KEY_D) or pr.is_key_down(pr.KeyboardKey.KEY_RIGHT)
        key_up = pr.is_key_pressed(pr.KeyboardKey.KEY_W) or pr.is_key_pressed(pr.KeyboardKey.KEY_UP) or pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE)

        def _overlap(obj: Block, x: float, y: float):
            return x < obj.x + obj.w and x + self.w > obj.x and \
                y < obj.y + obj.h and y + self.h > obj.y
        
        if key_right and not key_left:
            self.x_speed = self.walk_speed * dt
        elif key_left and not key_right:
            self.x_speed = -self.walk_speed * dt
        else:
            self.x_speed = 0

        if key_up and self.grounded:
            self.y_speed = -self.jump_strength * dt
        
        overlapped_objs: list[Block]
        
        x_new = self.x + self.x_speed
        overlapped_objs = [obj for obj in level.layout if _overlap(obj, x_new, self.y)]
        for obj in overlapped_objs:
            if x_new < obj.x < x_new + self.w > obj.x: x_new = min(x_new, obj.x - self.w)
            if x_new < obj.x + obj.w < x_new + self.w: x_new = max(x_new, obj.x + obj.w)
        self.x = x_new

        self.y_speed += self.gravity * dt
        y_new = self.y + self.y_speed
        overlapped_objs = [obj for obj in level.layout if _overlap(obj, self.x, y_new)]
        self.grounded = False
        for obj in overlapped_objs:
            if y_new < obj.y < y_new + self.h:
                self.y_speed = 0
                y_new = min(y_new, obj.y - self.h)
                self.grounded = True
            if y_new < obj.y + obj.h < y_new + self.h:
                self.y_speed = 0
                y_new = max(y_new, obj.y + obj.h)
        self.y = y_new
        
    def draw(self):
        pr.draw_rectangle(int(self.x), int(self.y), int(self.w), int(self.h), pr.RED)




level = Level(level_map)
player = Player()
cam = pr.Camera2D()
cam.target = pr.Vector2(player.x, player.y)
cam.offset = pr.Vector2(800 / 2, 600 / 2)
cam.zoom = 0.5

while not pr.window_should_close():
    dt = pr.get_frame_time()

    pr.begin_drawing()
    pr.clear_background(pr.RAYWHITE)

    player.update(dt, level)

    cam.target = pr.Vector2(player.x, player.y)

    pr.begin_mode_2d(cam)
    level.draw()
    player.draw()
    pr.end_mode_2d()

    pr.draw_fps(10, 10)
    pr.end_drawing()

pr.close_window()

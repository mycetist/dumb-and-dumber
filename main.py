from __future__ import annotations

import pyray as pr
from abc import ABC, abstractmethod

pr.init_window(1500, 1000, "demo")
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
        self.carried: bool = False

        self.partner: Player = None

    def set_partner(self, partner: Player):
        self.partner = partner

    def update(self):
        pass

    def _overlap_x(self, obj: Entity, x: float):
        return x < obj.x + obj.w and x + self.w > obj.x
    
    def _overlap_y(self, obj: Entity, y: float):
        return y < obj.y + obj.h and y + self.h > obj.y
    
    def _overlap(self, obj: Entity, x: float, y: float):
        return self._overlap_x(obj, x) and self._overlap_y(obj, y)

    

    def travel(self, level: Level, delta_x: float, delta_y: float):
        x_new = self.x + delta_x
        y_new = self.y + delta_y

        overlapped_objs: list[Block]
        overlapped_objs = [obj for obj in level.layout if self._overlap(obj, x_new, self.y)]
        for obj in overlapped_objs:
            if x_new < obj.x < x_new + self.w > obj.x:
                x_new = min(x_new, obj.x - self.w)
            if x_new < obj.x + obj.w < x_new + self.w:
                x_new = max(x_new, obj.x + obj.w)
        travel_x = x_new - self.x
        self.x = x_new
        
        overlapped_objs = [obj for obj in level.layout if self._overlap(obj, self.x, y_new)]
        self.grounded = False
        for obj in overlapped_objs:
            if y_new < obj.y < y_new + self.h:
                self.y_speed = 0
                y_new = min(y_new, obj.y - self.h)
                self.grounded = True
            if y_new < obj.y + obj.h < y_new + self.h:
                self.y_speed = 0
                y_new = max(y_new, obj.y + obj.h)

        if self.partner and self._overlap_x(self.partner, self.x) and self.y + self.h <= self.partner.y and y_new + self.h >= self.partner.y:
            self.carried = True
            self.y_speed = 0
            y_new = min(y_new, self.partner.y - self.h)
            self.grounded = True
        else:
            self.carried = False

        
        travel_y = y_new - self.y
        self.y = y_new
        return travel_x, travel_y



    def _move(self, dt: float, level: Level, keys: dict[str, bool], partner: Player = None):
        if keys['right'] and not keys['left']:
            self.x_speed = self.walk_speed * dt
        elif keys['left'] and not keys['right']:
            self.x_speed = -self.walk_speed * dt
        else:
            self.x_speed = 0

        if keys['up'] and self.grounded:
            self.y_speed = -self.jump_strength * dt
        self.y_speed += self.gravity * dt
    
        return self.travel(level, self.x_speed, self.y_speed)
        
    def draw(self):
        # default: draw rectangle
        pr.draw_rectangle(int(self.x), int(self.y), int(self.w), int(self.h), pr.RED)


class User(Player):
    def __init__(self):
        super().__init__()

    def update(self, dt: float, level: Level, partner: Player):
        # key_left = pr.is_key_down(pr.KeyboardKey.KEY_A) or pr.is_key_down(pr.KeyboardKey.KEY_LEFT)
        # key_right = pr.is_key_down(pr.KeyboardKey.KEY_D) or pr.is_key_down(pr.KeyboardKey.KEY_RIGHT)
        # key_up = pr.is_key_pressed(pr.KeyboardKey.KEY_W) or pr.is_key_pressed(pr.KeyboardKey.KEY_UP) or pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE)
        key_left = pr.is_key_down(pr.KeyboardKey.KEY_A)
        key_right = pr.is_key_down(pr.KeyboardKey.KEY_D)
        key_up = pr.is_key_pressed(pr.KeyboardKey.KEY_W)
        keys = {'right': key_right, 'left': key_left, 'up': key_up}

        return self._move(dt, level, keys, partner)

    def draw(self):
        pr.draw_rectangle(int(self.x), int(self.y), int(self.w), int(self.h), pr.RED)


class Bot(Player):
    def __init__(self):
        super().__init__()

    def update(self, dt: float, level: Level, partner: Player):
        key_left = pr.is_key_down(pr.KeyboardKey.KEY_LEFT)
        key_right = pr.is_key_down(pr.KeyboardKey.KEY_RIGHT)
        key_up = pr.is_key_pressed(pr.KeyboardKey.KEY_UP)
        keys = {'right': key_right, 'left': key_left, 'up': key_up}
        return self._move(dt, level, keys, partner)

    def draw(self):
        pr.draw_rectangle(int(self.x), int(self.y), int(self.w), int(self.h), pr.BLUE)


level = Level(level_map)

user = User()
bot = Bot()
user.set_partner(bot)
bot.set_partner(user)

cam = pr.Camera2D()
cam.target = pr.Vector2(user.x, user.y)
cam.offset = pr.Vector2(800 / 2, 600 / 2)
cam.zoom = 0.5

while not pr.window_should_close():
    dt = pr.get_frame_time()

    pr.begin_drawing()
    pr.clear_background(pr.RAYWHITE)

    user_x, user_y = user.update(dt, level, bot)
    bot_x, bot_y = bot.update(dt, level, user)

    if bot.carried:
        bot.travel(level, user_x, user_y)
    elif user.carried:
        user.travel(level, bot_x, bot_y)

    cam.target = pr.Vector2(user.x, user.y)

    pr.begin_mode_2d(cam)
    level.draw()
    user.draw()
    bot.draw()
    pr.end_mode_2d()

    pr.draw_fps(10, 10)
    pr.end_drawing()

pr.close_window()

from __future__ import annotations

import pyray as pr
from abc import ABC, abstractmethod
from enum import Enum
import json
import os

VOICE = True

import random
from concurrent.futures import ThreadPoolExecutor
if VOICE:
    from voice.final_pipeline import run_pipeline, get_whisper, get_llm_instance, LLM_PATH
    from voice.recorder import Recorder, SAMPLE_RATE
    from voice.LLM import close_llm

random.seed(0)



pr.set_config_flags(pr.ConfigFlags.FLAG_WINDOW_RESIZABLE)
pr.init_window(1500, 1000, "demo")
pr.set_target_fps(60)

pr.init_audio_device()

death_sfx = pr.load_sound("sfx/vine-boom.mp3")

blood_texture = pr.load_texture("textures/blood.png")
blood_frames = 10
blood_w = blood_texture.width / blood_frames
blood_h = blood_texture.height
blood_frame_time = 0.05

class Explosion:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.timer = 0.0
        self.frame = 0
        self.done = True

    def start(self, cx, cy):
        self.x = cx - self.w / 2
        self.y = cy - self.w / 2
        self.timer = 0
        self.frame = 0
        self.done = False

    def update(self, dt: float):
        if self.done:
            return
        self.timer += dt
        while self.timer >= blood_frame_time:
            self.timer -= blood_frame_time
            self.frame += 1
            if self.frame >= blood_frames:
                self.done = True
                break

    def draw(self):
        if self.done:
            return
        pr.draw_texture_pro(
            blood_texture,
            pr.Rectangle(self.frame * blood_w, 0, blood_w, blood_h),
            pr.Rectangle(self.x, self.y, self.w, self.h),
            pr.Vector2(0, 0),
            0,
            pr.RAYWHITE    
        )


player_still = pr.load_texture("textures/player/still.png")
player_run1 = pr.load_texture("textures/player/run1.png")
player_run2 = pr.load_texture("textures/player/run2.png")
player_jump = pr.load_texture("textures/player/jump.png")
bot_still = pr.load_texture("textures/bot/still.png")
bot_run1 = pr.load_texture("textures/bot/run1.png")
bot_run2 = pr.load_texture("textures/bot/run2.png")
bot_jump = pr.load_texture("textures/bot/jump.png")
bot_texture = pr.load_texture("textures/bot.png")

block_texture = pr.load_texture("textures/block.png")
finish_texture = pr.load_texture("textures/fin.png")
grass_texture = pr.load_texture("textures/grass.png")
spikes_texture = pr.load_texture("textures/spikes.png")
bg_texture = pr.load_texture("textures/bg.png")

sign_restart = pr.load_texture("textures/signs/restart.png")
sign_q = pr.load_texture("textures/signs/q.png")
sign_q_green = pr.load_texture("textures/signs/q_green.png")
sign_zoom = pr.load_texture("textures/signs/zoom.png")
sign_gg = pr.load_texture("textures/signs/gg.png")

mic_texture = pr.load_texture("textures/mic.png")

def fast_render(texture: pr.Texture, x: int, y: int, w: int, h: int, opacity: float = 1):
    col = pr.Color(255, 255, 255, int(opacity * 255))
    pr.draw_texture_pro(
        texture,
        pr.Rectangle(0, 0, texture.width, texture.height),
        pr.Rectangle(x, y, w, h),
        pr.Vector2(0, 0),
        0,
        col
    )

class Entity(ABC):
    @abstractmethod
    def draw(self):
        ...

    @abstractmethod
    def update(self, dt: float):
        ...


grass_edge = 15
grass_height = 2

spike_edge = 40
spike_height = 50

class Block(Entity):
    def __init__(self, x: int, y: int, w: int, h: int, flags: list[str] = None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.flags = flags

        if "nograss" in self.flags:
            return
        elif "spikes" in self.flags:
            self.spike_w = int((max(self.w, self.h) + spike_edge * 2) / 1.1)
            if spikes_texture.width <= self.spike_w:
                self.spike_w = spikes_texture.width
                self.spike_x = 0
            else:
                self.spike_x = random.randint(0, spikes_texture.width - self.spike_w)
            return

        if not "nograss" in self.flags:
            self.grass_w = (self.w + grass_edge * 2) // 3
            if grass_texture.width <= self.grass_w:
                # cap grass width to texture size
                self.grass_w = grass_texture.width
                self.grass_x = 0
            else:
                self.grass_x = random.randint(0, grass_texture.width - self.grass_w)
            

    def update(self, dt: float):
        pass

    def draw(self):
        if "finish" in self.flags:
            fast_render(finish_texture, self.x, self.y, self.w, self.h)
        elif "signrestart" in self.flags:
            fast_render(sign_restart, self.x, self.y, self.w, self.h)
        elif "signq" in self.flags:
            if user.grounded:
                fast_render(sign_q_green, self.x, self.y, self.w, self.h)
            else:
                fast_render(sign_q, self.x, self.y, self.w, self.h)
        elif "signzoom" in self.flags:
            fast_render(sign_zoom, self.x, self.y, self.w, self.h)
        elif "signgg" in self.flags:
            fast_render(sign_gg, self.x, self.y, self.w, self.h)
        elif "spikes" in self.flags:
            rot = self.h > self.w
            se = spike_edge if not rot else spike_height
            sh = spike_height if not rot else spike_edge
            
            dw = (self.h if rot else self.w) + 2 * se
            dh = (self.w if rot else self.h) + 2 * sh
            cx = self.x + self.w / 2 + (sh / 2 if rot else 0)
            cy = self.y + self.h / 2 - (0 if rot else sh / 2)
            pr.draw_texture_pro(
                spikes_texture,
                pr.Rectangle(self.spike_x, 0, self.spike_w, spikes_texture.height),
                pr.Rectangle(cx, cy, dw, dh),
                pr.Vector2(dw / 2, dh / 2),
                90 if rot else 0,
                pr.RAYWHITE
            )
        else:
            opacity = 0.4 if "bg" in self.flags else 1
            fast_render(block_texture, self.x, self.y, self.w, self.h, opacity)
            if not "nograss" in self.flags:
                pr.draw_texture_pro(
                    grass_texture,
                    pr.Rectangle(self.grass_x, 0, self.grass_w, grass_texture.height),
                    pr.Rectangle(self.x - grass_edge, self.y - grass_height, self.w + 2 * grass_edge, self.h // 1.6),
                    pr.Vector2(0, 0),
                    0,
                    pr.Color(255, 255, 255, int(opacity*255))
                )


class Level(Entity):
    def __init__(self):
        self.layout: list[Block] = []

    def update(self, dt: float):
        pass

    def load(self, id: int):
        self.layout = []

        with open(f"levels/{id}.json") as f:
            level_data = json.load(f)
        
        for pos in level_data['map']:
            x, y, w, h, *flags = pos
            self.layout.append(Block(x, y, w, h, flags))

        return level_data

    def draw(self, bg: bool = False):
        for obj in self.layout:
            if "bg" in obj.flags and bg:
                obj.draw()
            elif not "bg" in obj.flags and not bg:
                obj.draw()


class Player(Entity):
    def __init__(self):
        self.x: float = 50
        self.y: float = 50
        self.w: float = 100
        self.h: float = 100

        self.animation_dt: float = 0
        self.animation_duration: float = 0.15
        self.animation_frame = 0

        self.gravity: float = 36
        self.jump_strength: float = 1000
        self.walk_speed: float = 600

        self.dead = False

        self.y_speed: float = 0
        self.x_speed: float = 0

        self.grounded: bool = False
        self.carried: bool = False

        self.finish: bool = False

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

    def respawn(self, x: int, y: int):
        self.x = x
        self.y = y

        self.x_speed = 0
        self.y_speed = 0
        self.grounded = False
        self.carried = False
        self.finish = False
        self.dead = False

    def travel(self, level: Level, delta_x: float, delta_y: float, pushed: bool = False):
        x_new = self.x + delta_x
        y_new = self.y + delta_y

        overlapped_objs: list[Block]
        overlapped_objs = [obj for obj in level.layout if self._overlap(obj, x_new, self.y)]
        for obj in overlapped_objs:
            if 'finish' in obj.flags:
                self.finish = True
            elif 'notouch' in obj.flags:
                continue
            elif 'spikes' in obj.flags:
                self.dead = True
            if x_new < obj.x < x_new + self.w > obj.x:
                x_new = min(x_new, obj.x - self.w)
            if x_new < obj.x + obj.w < x_new + self.w:
                x_new = max(x_new, obj.x + obj.w)
        travel_x = x_new - self.x
        self.x = x_new
        
        overlapped_objs = [obj for obj in level.layout if self._overlap(obj, self.x, y_new)]
        if not pushed:
            self.grounded = False
        for obj in overlapped_objs:
            if 'finish' in obj.flags:
                self.finish = True
            elif 'notouch' in obj.flags:
                continue
            elif 'spikes' in obj.flags:
                self.dead = True
            if y_new < obj.y < y_new + self.h:
                self.y_speed = 0
                y_new = min(y_new, obj.y - self.h)
                self.grounded = True
            if y_new < obj.y + obj.h < y_new + self.h:
                self.y_speed = 0
                y_new = max(y_new, obj.y + obj.h)
            

        if not pushed:
            if self.partner and self._overlap_x(self.partner, self.x) and self.y + self.h - 1 <= self.partner.y and y_new + self.h >= self.partner.y:
                self.carried = True
                self.y_speed = 0
                y_new = min(y_new, self.partner.y - self.h)
                self.grounded = True
            else:
                self.carried = False

        
        travel_y = y_new - self.y
        self.y = y_new
        return travel_x, travel_y



    def _move(self, dt: float, level: Level, keys: dict[str, bool]):
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

    def _animate(self, dt: float):
        if self.x_speed == 0:
            self.animation_dt = 0
        else:
            self.animation_dt += dt
            if self.animation_dt >= self.animation_duration:
                self.animation_dt = 0
                self.animation_frame += 1
                self.animation_frame %= 2

        
    def draw(self):
        # default: draw rectangle
        pr.draw_rectangle(int(self.x), int(self.y), int(self.w), int(self.h), pr.RED)


class User(Player):
    def __init__(self):
        super().__init__()

    def update(self, dt: float, level: Level):
        # key_left = pr.is_key_down(pr.KeyboardKey.KEY_A) or pr.is_key_down(pr.KeyboardKey.KEY_LEFT)
        # key_right = pr.is_key_down(pr.KeyboardKey.KEY_D) or pr.is_key_down(pr.KeyboardKey.KEY_RIGHT)
        # key_up = pr.is_key_pressed(pr.KeyboardKey.KEY_W) or pr.is_key_pressed(pr.KeyboardKey.KEY_UP) or pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE)
        key_left = pr.is_key_down(pr.KeyboardKey.KEY_A)
        key_right = pr.is_key_down(pr.KeyboardKey.KEY_D)
        key_up = pr.is_key_pressed(pr.KeyboardKey.KEY_W)
        keys = {'right': key_right, 'left': key_left, 'up': key_up}
        self._animate(dt)
        return self._move(dt, level, keys)

    def draw(self):
        if not self.grounded:
            fast_render(player_jump, self.x, self.y, self.w, self.h)
        elif self.x_speed != 0:
            if self.animation_frame == 0:
                fast_render(player_run1, self.x, self.y, self.w, self.h)
            else:
                fast_render(player_run2, self.x, self.y, self.w, self.h)
        else:
            fast_render(player_still, self.x, self.y, self.w, self.h)


class Bot(Player):
    def __init__(self):
        super().__init__()
        self.executing = False
        self.timer = 0
        self.instruction: list = []

    def _update_manual(self, dt: float, level: Level):
        key_left = pr.is_key_down(pr.KeyboardKey.KEY_LEFT)
        key_right = pr.is_key_down(pr.KeyboardKey.KEY_RIGHT)
        key_up = pr.is_key_pressed(pr.KeyboardKey.KEY_UP)
        keys = {'right': key_right, 'left': key_left, 'up': key_up}
        self._animate(dt)
        return self._move(dt, level, keys)

    def update(self, dt: float, level: Level):
        if not VOICE:
            return self._update_manual(dt, level)
        keys = {'right': False, 'left': False, 'up': False}
        def _add_action(action: str):
            if action.lower() == "jump":
                keys['up'] = True
            else:
                keys[action.lower()] = True
        
        if self.executing and self.timer > max(cmd['duration'][1] for cmd in self.instruction):
            self.executing = False
            self.timer = 0
        
        if self.executing:
            self.timer += dt
            for i in range(len(self.instruction)):
                cmd = self.instruction[i]
                if self.timer > cmd['duration'][0] and \
                        (self.timer <= cmd['duration'][1] or not cmd.get('ran', False)):
                    _add_action(cmd['type'])
                    self.instruction[i]['ran'] = True

        self._animate(dt)
        return self._move(dt, level, keys)
            

    def execute(self, instruction: list):
        self.instruction = instruction
        self.executing = True
        self.timer = 0

    def respawn(self, x: int, y: int):
        super().respawn(x, y)
        self.executing = False
        self.timer = 0

    def draw(self):
        if not self.grounded:
            fast_render(bot_jump, self.x, self.y, self.w, self.h)
        elif self.x_speed != 0:
            if self.animation_frame == 0:
                fast_render(bot_run1, self.x, self.y, self.w, self.h)
            else:
                fast_render(bot_run2, self.x, self.y, self.w, self.h)
        else:
            fast_render(bot_still, self.x, self.y, self.w, self.h)

def sign(x):
    return (x > 0) - (x < 0)

class Rope:
    def __init__(self):
        self.active = False

        self.dur_alpha = 0
        self.dur = 3

        self.cooldown = 0.3
        self.cooldown_alpha: float = 0

        self.travel_x = 1
        self.travel_y = 1

    def reset(self):
        self.active = False
        self.cooldown_alpha = 0
        self.dur_alpha = 0
        self.travel_x = 1
        self.travel_y = 1

    def use(self):
        if self.cooldown_alpha < self.cooldown:
            # sfx here????
            return
        self.reset()
        self.active = True


    def update(self, dt: float):
        if self.active:
            self.dur_alpha += dt
            if self.dur_alpha >= self.dur:
                bot.y_speed = 0
                self.reset()
                return

            delta_x = user.x - bot.x
            delta_y = user.y - bot.y
            dist = (delta_x**2 + delta_y**2)**0.5

            if dist < 5 or (self.travel_x == 0 and self.travel_y == 0):
                self.reset()
                bot.y_speed = 0
                return

            if dist > 0:
                step = min(800 * dt, dist)
                move_x = delta_x / dist * step
                move_y = delta_y / dist * step

                if self.travel_x == 0 and move_y != 0:
                    remaining_y = user.y - bot.y
                    move_y = sign(remaining_y) * min(abs(remaining_y), step / 1.5)
                if self.travel_y == 0 and move_x != 0:
                    remaining_x = user.x - bot.x
                    move_x = sign(remaining_x) * min(abs(remaining_x), step / 1.5)

                self.travel_x, self.travel_y = bot.travel(level, move_x, move_y, True)

        else:
            self.cooldown_alpha += dt
        

    def draw(self):
        pr.draw_line_ex(
            pr.Vector2(user.x + user.w // 2, user.y + user.h // 2),
            pr.Vector2(bot.x + bot.w // 2, bot.y + bot.h // 2),
            7, pr.Color(255, 255, 255, 100)
        )


level = Level()
level_id = 1
level_data = level.load(level_id)

user = User()
bot = Bot()
rope = Rope()
rope.cooldown_alpha = rope.cooldown
user.set_partner(bot)
bot.set_partner(user)
user.respawn(*level_data['spawn']['user'])
bot.respawn(*level_data['spawn']['bot'])

cam = pr.Camera2D()



def update_characters():
    carried = 'bot' if bot.carried else 'user' if user.carried else None
    
    if carried == 'bot':
        bot_x, bot_y = bot.update(dt, level)
        user_x, user_y = user.update(dt, level)
    else:
        user_x, user_y = user.update(dt, level)
        bot_x, bot_y = bot.update(dt, level)

    if carried == 'bot' and bot.carried:
        bot.travel(level, user_x, user_y, True)
    elif carried == 'user' and user.carried:
        user.travel(level, bot_x, bot_y, True)

def update_camera(dt: float):
    mid_x = (user.x + user.w / 2 + bot.x + bot.w / 2) / 2
    mid_y = (user.y + user.h / 2 + bot.y + bot.h / 2) / 2

    padding = 1_000
    if game_status == Status.DEAD:
        padding /= 5
    elif pr.is_key_down(pr.KeyboardKey.KEY_Z):
        padding *= 5
    cam_w = abs(user.x - bot.x) + user.w + padding
    cam_h = abs(user.y - bot.y) + user.h + padding

    zoom = min(pr.get_screen_width() / cam_w, pr.get_screen_height() / cam_h)
    zoom = max(0.15, min(1, zoom))

    t = 1 - 0.001 ** dt
    cam.target.x += (mid_x - cam.target.x) * t
    cam.target.y += (mid_y - cam.target.y) * t
    cam.zoom += (zoom - cam.zoom) * t

def reset_camera():
    cam.target = pr.Vector2((user.x + bot.x) / 2, (user.y + bot.y) / 2)
    cam.offset = pr.Vector2(pr.get_screen_width() / 2, pr.get_screen_height() / 2)
    cam.zoom = 0.5

reset_camera()

class Status(Enum):
    DEAD = 0
    PLAYING = 1
    TRANSITIONING = 2
    INTRO = 3

game_status = Status.PLAYING

def restart():
    level_data = level.load(level_id)
    user.respawn(*level_data['spawn']['user'])
    bot.respawn(*level_data['spawn']['bot'])
    rope.reset()
    rope.cooldown_alpha = rope.cooldown
    explosion.done = True
    reset_camera()

explosion = Explosion(0, 0, 250, 250)

voice_job = None

if VOICE:
    voice_pool = ThreadPoolExecutor(max_workers=1)
    recorder = Recorder()

    def warm_up():
        get_whisper()
        get_llm_instance(LLM_PATH)

    voice_pool.submit(warm_up)

while not pr.window_should_close():
    dt = pr.get_frame_time()

    if VOICE:
        if pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE) and voice_job is None:
            recorder.start()
        elif pr.is_key_released(pr.KeyboardKey.KEY_SPACE) and recorder.stream is not None:
            audio = recorder.stop()
            if len(audio) > 0.3 * SAMPLE_RATE:
                voice_job = voice_pool.submit(run_pipeline, audio)

        if voice_job is not None and voice_job.done():
            try:
                result, took = voice_job.result()
                print(result)
                bot.execute(result['commands'])
            except Exception as e:
                print(f"pipeline fail: {e}")
            voice_job = None

    if game_status == Status.PLAYING:
        if (user.finish or bot.finish):
            if level_id >= len(os.listdir("levels")):
                level_id = 1
            else:
                level_id += 1
            level_data = level.load(level_id)
            user.respawn(*level_data['spawn']['user'])
            bot.respawn(*level_data['spawn']['bot'])
            rope.reset()
            rope.cooldown_alpha = rope.cooldown
        elif pr.is_key_pressed(pr.KeyboardKey.KEY_R):
            restart()
        elif user.dead or bot.dead:
            game_status = Status.DEAD
            pr.play_sound(death_sfx)
            victim = user if user.dead else bot
            explosion.start(victim.x + victim.w / 2, victim.y + victim.h / 2)
        
        else:
            if pr.is_key_pressed(pr.KeyboardKey.KEY_Q) and user.grounded:
                rope.use()
            if not rope.active:
                update_characters()
            rope.update(dt)


    elif game_status == Status.DEAD:
        explosion.update(dt)
        if pr.is_key_pressed(pr.KeyboardKey.KEY_R):
            restart()
            game_status = Status.PLAYING
    
    update_camera(dt)



    pr.begin_drawing()
    pr.clear_background(pr.RAYWHITE)

    fast_render(bg_texture, 0, 0, pr.get_screen_width(), pr.get_screen_height())
    pr.begin_mode_2d(cam)

    level.draw(bg=True)
    if rope.active and game_status == Status.PLAYING:
        rope.draw()

    if not user.dead: user.draw()
    if not bot.dead: bot.draw()
    level.draw()
    explosion.draw()
    pr.end_mode_2d()

    if VOICE and recorder.stream is not None:
        mic_w = mic_texture.width * 3
        mic_h = mic_texture.height * 3
        fast_render(
            mic_texture,
            pr.get_screen_width() / 2 - mic_w / 2,
            pr.get_screen_height() / 2 - mic_h / 2,
            mic_w,
            mic_h
        )


    pr.draw_fps(10, 10)
        
    pr.end_drawing()

pr.close_window()

voice_pool.shutdown(wait=True, cancel_futures=True)
close_llm()
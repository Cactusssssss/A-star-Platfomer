import pygame
from pygame.locals import *
import sys
import random
import time
import math
import os
import matplotlib.pyplot as plt

# global variables
pygame.init()
vec = pygame.math.Vector2  # 2 for two dimensional
## colours
background_colour = (0, 0, 0)
white_rgb = (255, 255, 255)
red_rgb = (255, 0, 0)
green_rgb = (0, 255, 0)
blue_rgb = (0, 0, 255)
yellow_rgb = (255, 255, 0)
## game window settings
window_height = 800
window_width = 400
font_size = 16
font_type = "free sans"
display_window = pygame.display.set_mode((window_width, window_height))
pygame.display.set_caption("platformer")
## movement settings
speed = 4
friction = -0.13
FPS = (60)*5
## control settings
jump_keys = [pygame.K_w, pygame.K_SPACE]
escape_keys = [pygame.K_ESCAPE]
left_key = pygame.K_a
right_key = pygame.K_d
## player variables
player_size = 30
player_spawn_pos = (window_width/2, window_height-player_size)
jump_height = 13
player_vision = (window_width/2, round(window_height/15))
## platform dimensions
platform_height = 20
platform_width = 60
platform_dim = (platform_width, platform_height)
# key platform positions
floor_pos = (window_width/2, window_height)
goal_pos = (window_width/2, player_size+(platform_height/2))
# all sprite objects
all_platforms = pygame.sprite.Group()
all_players = pygame.sprite.Group()
all_sprites = pygame.sprite.Group()


# player class
class Player(pygame.sprite.Sprite):
    def __init__(self, pos = player_spawn_pos, use_greedy = False, use_astar = False):
        super().__init__()
        # self.image = pygame.image.load("character.png")
        self.surf = pygame.Surface(vec(player_size, player_size))
        self.surf.fill(yellow_rgb)
        self.rect = self.surf.get_rect()
        self.pos = vec(pos)
        self.vel = vec(0, 0)
        self.acc = vec(0, 0)
        # general booleans
        self.jumping = False

        # general variables for all search algos
        self.target_platform = (-1, -1) # (x, y)
        self.vision = player_vision
        # greedy search variables
        self.use_greedy = use_greedy
        self.distance_to_goal = sys.maxsize
        self.reachedGoal = False
        # astar search variables
        self.use_astar = use_astar
        self.all_target_platforms = []


    def move(self, left = False, right = False):
        self.acc = vec(0, 0.5)

        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[left_key] or left:
            self.move_left()
        if pressed_keys[right_key] or right:
            self.move_right()

        self.acc.x += self.vel.x * friction
        self.vel += self.acc  
        # self.pos += self.vel + ((speed/2) * self.acc)
        self.pos += self.vel + 0.5 * self.acc

        if self.pos.x > window_width:
            self.pos.x = 0
        if self.pos.x < 0:
            self.pos.x = window_width

        self.rect.midbottom = self.pos

    # movement
    def move_left(self):
        self.acc.x = -speed

    def move_right(self):
        self.acc.x = speed

    def jump(self):
        hits = pygame.sprite.spritecollide(self, all_platforms, False)
        if hits and not self.jumping:
            self.jumping = True
            self.vel.y = -jump_height

    def cancel_jump(self):
        neg_val = -2
        if self.jumping:
            if self.vel.y < neg_val:
                self.vel.y = neg_val

    # update sprite if it hit a platform
    def update(self):
        hits = pygame.sprite.spritecollide(self, all_platforms, False)
        if self.vel.y > 0:
            if hits:
                if self.pos.y < hits[0].rect.bottom:
                    # if hits[0].point == True:
                    #     hits[0].point = False
                    #     self.score += 1
                    self.pos.y = hits[0].rect.top + 1
                    self.vel.y = 0
                    self.jumping = False
        # update distance to goal
        if self.use_greedy and self.reachedGoal == False:
            self.move_toward_target()
            self.distance_to_goal = calculate_distance((goal_pos[0], goal_pos[1]-platform_height/2), self.get_pos())
            self.reachedGoal = True if self.get_y_pos() < goal_pos[1] else False
        elif self.use_astar and self.reachedGoal == False:
            if (self.target_platform == (-1, -1) or self.check_target_platform_proximity()) and len(self.all_target_platforms) > 0:
                self.target_platform = self.all_target_platforms[0]
                del self.all_target_platforms[0]
                # print( self.all_target_platforms )
            self.move_toward_target()
            self.distance_to_goal = calculate_distance((goal_pos[0], goal_pos[1]-platform_height/2), self.get_pos())
            self.reachedGoal = True if self.get_y_pos() < goal_pos[1] else False

    def move_toward_target(self):
        target_platform_pos = self.get_target_platform_pos()
        if self.get_y_pos() > target_platform_pos[1]:
            self.jump()
        elif self.get_y_pos()-(player_size*2) < target_platform_pos[1]:
            self.cancel_jump()
        if self.get_x_pos() < target_platform_pos[0]:
            self.move(right = True)
        if self.get_x_pos() > target_platform_pos[0]:
            self.move(left = True)

    # checkers
    def check_platform_proximity(self, target_pos):
        return True if calculate_distance(target_pos, self.get_pos()) < 7 else False

    def check_target_platform_proximity(self):
        return True if self.get_target_platform_distance() < 7 else False

    def check_has_target_platform(self):
        return False if self.target_platform == (-1, -1) else True

    def check_within_vision(self, target_pos):
        # check if target is within field of vision
        vision = self.get_field_of_vision()
        upper_left_field = (self.get_x_pos()-vision[0], self.get_y_pos()-vision[1])
        bottom_right_field = (self.get_x_pos()+vision[0], self.get_y_pos()+vision[1])
        return True if (upper_left_field[0] < target_pos[0] and target_pos[0] < bottom_right_field[0] and upper_left_field[1] < target_pos[1] and target_pos[1] < bottom_right_field[1]) else False

    def check_player_on_platform(self):
        player_pos = self.get_pos()
        left_top = (self.target_platform[0]-platform_width/2, self.target_platform[1]-player_size)
        right_bottom = (self.target_platform[0]-platform_width/2, self.target_platform[1])
        return True if (left_top[0] < player_pos[0] and player_pos[0] < right_bottom[0] and left_top[1] < player_pos[1] and player_pos[1] < right_bottom[1]) else False

    # setters
    def set_pos(self, pos_tuple):
        self.pos.x = pos_tuple[0]
        self.pos.y = pos_tuple[1]

    def set_target_platform(self, pos):
        self.target_platform = pos

    def set_all_target_platforms(self, all_targets):
        self.all_target_platforms = all_targets

    # getters
    def get_x_pos(self):
        return self.pos.x

    def get_y_pos(self):
        return self.pos.y

    def get_pos(self):
        return (self.get_x_pos(), self.get_y_pos())

    def get_field_of_vision(self):
        return self.vision

    def get_distance_to_goal(self):
        return self.distance_to_goal

    def get_target_platform_pos(self, roundoff = -1):
        return self.target_platform if roundoff == -1 else (round(self.target_platform[0], roundoff), round(self.target_platform[1], roundoff))

    def get_target_platform_distance(self):
        target_pos = self.get_target_platform_pos()
        return calculate_distance( (target_pos[0], target_pos[1]-(platform_height/2)), self.get_pos())


# platforms class
class platform(pygame.sprite.Sprite):
    def __init__(self, pos = (-1, -1), dimensions = vec(platform_dim), moving = False, point = False, isGoal = False, isFloor = False, isTrap = False):
        super().__init__()
        self.dim = dimensions
        self.surf = pygame.Surface(self.dim)
        self.surf.fill(blue_rgb)
        self.pos = vec(pos[0], pos[1])
        if self.pos == (-1, -1):
            self.rect = self.surf.get_rect(center=(random.randint(0, window_width - 10), random.randint(0, window_height - 30)))
        else:
            self.rect = self.surf.get_rect(center=pos)
        self.speed = random.randint(-1, 1)
        # booleans
        self.point = point
        self.moving = moving
        self.isGoal = isGoal
        self.isFloor = isFloor
        self.isTrap = isTrap
        self.hasReached = True if self.isFloor else False

    def move(self):
        if self.moving == True:
            self.rect.move_ip(self.speed, 0)
            if self.speed > 0 and self.rect.left > window_width:
                self.rect.right = 0
            if self.speed < 0 and self.rect.right < 0:
                self.rect.left = window_width

    # togglers
    def toggle_hasReached(self):
        self.hasReached = True if not self.hasReached else False

    # checkers
    def check_within_range(self, target_pos):
        vision = platform_vision
        upper_left_field = (self.get_x_pos() - vision[0], self.get_y_pos() - vision[1])
        bottom_right_field = (self.get_x_pos() + vision[0], self.get_y_pos() + vision[1])
        return True if (upper_left_field[0] < target_pos[0] and
                        target_pos[0] < bottom_right_field[0] and
                        upper_left_field[1] < target_pos[1] and
                        target_pos[1] < bottom_right_field[1]
                        ) else False

    # setters

    # getters
    def get_x_pos(self):
        return self.pos.x

    def get_y_pos(self):
        return self.pos.y

    def get_pos(self):
        return (self.get_x_pos(), self.get_y_pos())


# check collision class
def check(platform, groupies):
    if pygame.sprite.spritecollideany(platform, groupies):
        return True
    else:
        for entity in groupies:
            if entity == platform:
                continue
            if (abs(platform.rect.top - entity.rect.bottom) < 40) and (
                    abs(platform.rect.bottom - entity.rect.top) < 40):
                return True
        C = False


# # generate several platform class
# def plat_gen():
#     while len(all_platforms) < 6:
#         width = random.randrange(50, 100)
#         # width = window_width
#         p = platform()
#         C = True
#
#         while C:
#             p = platform()
#             p.rect.center = (random.randrange(0, window_width - width),
#                              random.randrange(-50, 0))
#             C = check(p, all_platforms)
#         all_platforms.add(p)
#         all_sprites.add(p)


# generate platforms randomly
def generate_platforms(seed = 0):
    random.seed(seed)
    # curr_x_pos = random.randint(round(platform_width/2), round(window_width-(platform_width/2)))
    curr_y_pos = (player_size*2)+platform_height*2
    while curr_y_pos < (window_height-(platform_height)-player_size):
        for i in range(random.randint(1, 4)):
            random_x_pos = random.randint(round(platform_width/2), round(window_width-(platform_width/2)))
            pltfrm = platform(pos=( random_x_pos, curr_y_pos), dimensions = platform_dim)
            all_platforms.add(pltfrm)
            all_sprites.add(pltfrm)
        curr_y_pos += (player_size*2) + (platform_height/2)


# calculate euclidean distance between two points
def calculate_distance(pos_a, pos_b):
    return math.sqrt(pow((pos_a[0]-pos_b[0]), 2) + pow((pos_a[1]-pos_b[1]), 2))


# start a round of game simulation
def start_greedy_sim(seed = 0, platform = platform):
    touched_platforms = 0

    # create player object
    for i in range(0, 1):
        player_obj = Player(use_greedy=True)
        all_players.add(player_obj)
        all_sprites.add(player_obj)

    # floor platform
    floor_obj = platform(pos=floor_pos, dimensions=(window_width, platform_height), moving = False, point = False, isFloor = True) # create platform object
    floor_obj.surf.fill(green_rgb)
    all_platforms.add(floor_obj)
    all_sprites.add(floor_obj)

    # goal platform
    goal_obj = platform(pos=goal_pos, dimensions=(platform_width, platform_height), moving = False, point = True, isGoal = True)
    goal_obj.surf.fill(red_rgb)
    all_platforms.add(goal_obj)
    all_sprites.add(goal_obj)

    generate_platforms(seed = seed)

    # gameplay loop
    start_time = time.time()
    while True:
        # update player
        for player_obj in all_players:
            player_obj.update()
        # check for player inputs
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in escape_keys:
                    pygame.quit()
                    sys.exit()
                elif event.key in jump_keys:
                    for player_obj in all_players:
                        player_obj.jump()
            if event.type == pygame.KEYUP and event.key in jump_keys:
                for player_obj in all_players:
                    player_obj.cancel_jump()

        display_window.fill(background_colour)
        for player_obj in all_players:
            # reset player if fell below map
            if player_obj.get_y_pos() > window_height:
                player_obj.set_pos(player_spawn_pos)
            # checking if player has reached target platform
            if player_obj.use_greedy and not player_obj.reachedGoal:
                if player_obj.check_target_platform_proximity():
                    reached_platform_pos = player_obj.get_target_platform_pos()
                    # highlight all traversed platforms
                    for platform in all_platforms:
                        if platform.get_pos() == reached_platform_pos and platform.point == False:
                            platform.surf.fill(yellow_rgb)
                            touched_platforms += 1
                            platform.point = True
                    player_obj.set_target_platform((-1, -1))
                    for platform in all_platforms:
                        if reached_platform_pos == platform.get_pos():
                            # platform.surf.fill(blue_rgb)
                            platform.toggle_hasReached()
                            break
                elif player_obj.check_has_target_platform() == False:
                    best_platform_distance = sys.maxsize
                    best_goal_distance = sys.maxsize
                    for platform in all_platforms:
                        # print(f"{platform.get_pos()} within FOV: {player_obj.check_within_vision(platform.get_pos())}")
                        if platform.hasReached == False and platform.isFloor == False and player_obj.check_within_vision(platform.get_pos()):
                            distance_player_to_platform = calculate_distance(player_obj.get_pos(), platform.get_pos())
                            # distance_platform_to_goal = calculate_distance(platform.get_pos(), goal_pos)
                            # if distance_player_to_platform < best_platform_distance and distance_platform_to_goal < best_goal_distance:
                            if distance_player_to_platform < best_platform_distance:
                                best_platform_distance = distance_player_to_platform
                                # best_goal_distance = distance_platform_to_goal
                                player_obj.set_target_platform( platform.get_pos() )
                                # platform.surf.fill(yellow_rgb)


            # display info on top left corner
            all_msg = [
                # f"x: {round(player_obj.get_x_pos(), 1)}",
                # f"y: {round(player_obj.get_y_pos(), 1)}",
                # f"goal distance: {round(player_obj.get_distance_to_goal(), 2)}",
                # f"platform count: {len(all_platforms)}",
                # f"target platform: {player_obj.get_target_platform_pos(roundoff=0)}",
                # f"next plat distance: {round(player_obj.get_target_platform_distance(), 2)}",
                # f"time elapsed: {round(time.time() - start_time, 2)}",
                f"Platforms Traversed: {touched_platforms}",
                f"Total Platforms: {len(all_platforms)}",
            ]
            system_font = pygame.font.SysFont(font_type, font_size)
            msg_pos = (0, 0)
            for msg in all_msg:
                displayed_text = system_font.render(msg, True, white_rgb)
                display_window.blit(displayed_text, msg_pos)
                msg_pos = (msg_pos[0], msg_pos[1] + font_size)


        # update all sprite positions (move all sprites)
        for entity in all_sprites:
            display_window.blit(entity.surf, entity.rect)
            entity.move()

        pygame.display.update()
        pygame.time.Clock().tick(FPS)

        # checking if players reached goal
        for player_obj in all_players:
            if player_obj.reachedGoal:
                file_path = os.path.join(os.getcwd(), f"greedy\{seed}.png")
                pygame.image.save(display_window, file_path)
                return (len(all_platforms), touched_platforms), (time.time() - start_time)
        # exceeded time limit
        if (time.time() - start_time) > 10:
            file_path = os.path.join(os.getcwd(), f"greedy\{seed}.png")
            pygame.image.save(display_window, file_path)
            return (len(all_platforms), touched_platforms), (time.time() - start_time)


def start_astar_sim(seed = 0, platform=platform):
    # create player object
    for i in range(0, 1):
        player_obj = Player(use_astar=True)
        all_players.add(player_obj)
        all_sprites.add(player_obj)

    # floor platform
    floor_obj = platform(pos=floor_pos, dimensions=(window_width, platform_height), moving=False, point=False, isFloor=True)  # create platform object
    floor_obj.surf.fill(green_rgb)
    all_platforms.add(floor_obj)
    all_sprites.add(floor_obj)

    # goal platform
    goal_obj = platform(pos=goal_pos, dimensions=(platform_width, platform_height), moving=False, point=True, isGoal=True)
    goal_obj.surf.fill(red_rgb)
    all_platforms.add(goal_obj)
    all_sprites.add(goal_obj)

    # generate Astar path
    generate_platforms(seed=seed)
    platforms_traversed = []
    search_queue_dict = {}
    search_queue = []
    current_search_pos = floor_pos
    while current_search_pos != goal_pos:
        # getting platform in range
        curr_closest_y_pos = -1
        for pltfrm in all_platforms:
            if current_search_pos[1] > pltfrm.get_y_pos() > curr_closest_y_pos:
                curr_closest_y_pos = pltfrm.get_y_pos()
        platforms_in_range = [i.get_pos() for i in all_platforms if i.get_y_pos() == curr_closest_y_pos]
        # find the next stop
        for curr_pos in platforms_in_range:
            curr_pos_to_platform = calculate_distance(current_search_pos, curr_pos)
            curr_platform_to_goal = calculate_distance(curr_pos, goal_pos)
            curr_total_pos_to_goal = curr_pos_to_platform + curr_platform_to_goal
            if (curr_pos not in search_queue_dict):
                search_queue_dict[curr_pos] = curr_total_pos_to_goal
                search_queue.append( curr_total_pos_to_goal )
                search_queue.sort()
            elif (curr_pos in search_queue_dict):
                if search_queue_dict[curr_pos] > curr_total_pos_to_goal:
                    to_remove = search_queue_dict[curr_pos]
                    search_queue_dict[curr_pos] = curr_total_pos_to_goal
                    search_queue.remove(to_remove)
                    search_queue.append(curr_total_pos_to_goal)
                    search_queue.sort()
        # change current search position
        search_queue.sort()
        platforms_traversed.append( current_search_pos )
        current_search_pos = list(search_queue_dict.keys())[list(search_queue_dict.values()).index(search_queue[0])]
        del search_queue_dict[current_search_pos]
        del search_queue[0]
    if platforms_traversed[-1] != goal_pos:
        platforms_traversed.append(goal_pos)
    platforms_traversed_len = len(platforms_traversed)
    # set path for player
    for player_obj in all_players:
        player_obj.set_all_target_platforms(platforms_traversed)

    # gameplay loop
    start_time = time.time()
    while True:
        # update player
        for player_obj in all_players:
            for platform in all_platforms:
                if platform.get_pos() == player_obj.get_target_platform_pos() and platform.isFloor == False:
                    platform.surf.fill(yellow_rgb)
            player_obj.update()
        # check for player inputs
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in escape_keys:
                    pygame.quit()
                    sys.exit()
                elif event.key in jump_keys:
                    for player_obj in all_players:
                        player_obj.jump()
            if event.type == pygame.KEYUP and event.key in jump_keys:
                for player_obj in all_players:
                    player_obj.cancel_jump()

        display_window.fill(background_colour)

        # update all sprite positions (move all sprites)
        for entity in all_sprites:
            display_window.blit(entity.surf, entity.rect)
            entity.move()

        for player_obj in all_players:
            if player_obj.get_y_pos() > window_height:
                player_obj.set_pos( (window_width/2, window_height-platform_height) )
            # display message updates
            all_msg = [
                # f"x: {round(player_obj.get_x_pos(), 1)}",
                # f"y: {round(player_obj.get_y_pos(), 1)}",
                # f"goal distance: {round(player_obj.get_distance_to_goal(), 2)}",
                # f"platform count: {len(all_platforms)}",
                # f"target platform: {player_obj.get_target_platform_pos(roundoff=0)}",
                # f"next plat distance: {round(player_obj.get_target_platform_distance(), 2)}",
                # f"time elapsed: {round(time.time() - start_time, 2)}",
                f"Platforms Traversed: {platforms_traversed_len}",
                f"Total Platforms: {len(all_platforms)}",
            ]
            system_font = pygame.font.SysFont(font_type, font_size)
            msg_pos = (0, 0)
            for msg in all_msg:
                displayed_text = system_font.render(msg, True, white_rgb)
                display_window.blit(displayed_text, msg_pos)
                msg_pos = (msg_pos[0], msg_pos[1] + font_size)

        pygame.display.update()
        pygame.time.Clock().tick(FPS)

        # checking if players reached goal
        for player_obj in all_players:
            if player_obj.reachedGoal:
                file_path = os.path.join(os.getcwd(), f"astar\{seed}.png")
                pygame.image.save(display_window, file_path)
                return (len(all_platforms), platforms_traversed_len), (time.time() - start_time)
        # exceeded time limit
        if (time.time() - start_time) > 10:
            file_path = os.path.join(os.getcwd(), f"astar\{seed}.png")
            pygame.image.save(display_window, file_path)
            return (len(all_platforms), platforms_traversed_len), (time.time() - start_time)


def generate_and_save(seed = 0, platform=platform):
    # create player object
    # for i in range(0, 1):
    #     player_obj = Player()
    #     all_players.add(player_obj)
    #     all_sprites.add(player_obj)

    # floor platform
    floor_obj = platform(pos=floor_pos, dimensions=(window_width, platform_height), moving=False, point=False,
                         isFloor=True)  # create platform object
    floor_obj.surf.fill(green_rgb)
    all_platforms.add(floor_obj)
    all_sprites.add(floor_obj)

    # goal platform
    goal_obj = platform(pos=goal_pos, dimensions=(platform_width, platform_height), moving=False, point=True,
                        isGoal=True)
    goal_obj.surf.fill(red_rgb)
    all_platforms.add(goal_obj)
    all_sprites.add(goal_obj)

    generate_platforms(seed=seed)
    # update screen
    display_window.fill(background_colour)
    for entity in all_sprites:
        entity.move()
        entity.update()
        pygame.display.update()
        display_window.blit(entity.surf, entity.rect)
        # display seed on top of window
        system_font = pygame.font.SysFont(font_type, font_size)
        displayed_text = system_font.render(f"seed: {seed}", True, white_rgb)
        display_window.blit(displayed_text, (window_width/2, 0))
    # save to file
    file_path = os.path.join(os.getcwd(), f"stages\{seed}.png")
    pygame.image.save(display_window, file_path)

##################################################################################################################
random.seed( 0 )
for i in range(0, 100):
    generate_and_save(seed=random.randint(0, 10000))
    # reset everything
    all_sprites = pygame.sprite.Group()
    all_platforms = pygame.sprite.Group()
    all_players = pygame.sprite.Group()
sys.exit()


random.seed( 0 )
time_dict = []
touched_list = []
for i in range(0, 100):
    platforms_touched, time_taken = start_greedy_sim( seed = random.randint(0, 10000) )
    time_dict.append( time_taken )
    touched_list.append( platforms_touched )
    # reset everything
    all_sprites = pygame.sprite.Group()
    all_platforms = pygame.sprite.Group()
    all_players = pygame.sprite.Group()
print( touched_list )
print( time_dict )
# plot
touched_list_pct = [(i[1]/i[0])*100 for i in touched_list]
plt.plot(range(0, len(touched_list)), touched_list_pct)
plt.plot(range(0, len(touched_list)), [sum(touched_list_pct)/len(touched_list_pct) for i in range(0, len(touched_list))], color='red')
plt.title(f'Platforms Used vs. Iterations')
plt.xlabel('Iteration')
plt.ylabel('Percentage of Platforms Used, %')
plt.show()
sys.exit()

random.seed( 0 )
time_dict = []
touched_list = []
for i in range(0, 100):
    seed = random.randint(0, 10000)
    print(f"seed: {seed}")
    platforms_touched, time_taken = start_astar_sim( seed = seed )
    time_dict.append(time_taken)
    touched_list.append(platforms_touched)
    # reset everything
    all_platforms = pygame.sprite.Group()
    all_players = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group()
print( touched_list )
print( time_dict )
# plot
touched_list_pct = [(i[1]/i[0])*100 for i in touched_list]
plt.plot(range(0, len(touched_list)), touched_list_pct)
plt.plot(range(0, len(touched_list)), [sum(touched_list_pct)/len(touched_list_pct) for i in range(0, len(touched_list))], color='red')
plt.title(f'Platforms Used vs. Iterations')
plt.xlabel('Iteration')
plt.ylabel('Percentage of Platforms Used, %')
plt.show()
sys.exit()

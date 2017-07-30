# coding: utf8

from bearlibterminal import terminal as blt
import libtcodpy as libtcod

import constants

# Needed for map
class struct_Tile:
    def __init__(self, block_path):
        self.block_path = block_path
        self.explored = False

# Storing our stuff in one place
# Most importantly this stores the entities on map and the messages to be displayed
class obj_Game:
    def __init__(self):
        self.current_map, self.current_rooms = map_create()
        self.current_entities = []
        self.message_history = []

    def add_entity(self, entity):
        if entity is not None:
            self.current_entities.append(entity)
    
    def game_message(self, msg, msg_color):
        self.message_history.append((msg, msg_color))

class Rect:
    # a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        # returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)


# Entity
class obj_Entity:
    def __init__(self, x, y, char, creature=None, ai=None):
        self.x = x
        self.y = y
        self.char = char

        # both creature and AI are optional
        self.creature = creature

        if self.creature:
            creature.owner = self

        self.ai = ai
        if self.ai:
            ai.owner = self

    def draw(self):
        is_visible = libtcod.map_is_in_fov(FOV_MAP, self.x, self.y)

        if is_visible:
            tile_x, tile_y = draw_iso(self.x, self.y)
            # draw our entity's ASCII symbol at an offset
            # blt.put_ext(tile_x, tile_y, 0, blt.state(blt.TK_CELL_HEIGHT), self.char)

            # draw the tile at different offset because size of a tile is much different than the size of an ASCII letter
            blt.put_ext(tile_x, tile_y, 0, 2, self.char)


# Something that can move and fight
class com_Creature:
    ''' Name_instance is the name of an individual, e.g. "Agrk"'''
    def __init__(self, name_instance,
                 num_dice = 1, damage_dice = 6, base_def = 0, hp=10,
                 death_function=None):
        self.name_instance = name_instance
        self.max_hp = hp
        self.hp = hp
        self.num_dice = num_dice
        self.damage_dice = damage_dice
        self.base_def = base_def
        self.death_function = death_function

    @property
    def attack_mod(self):
        total_attack = roll(self.num_dice, self.damage_dice)

        return total_attack

    def move(self, dx, dy):
        if self.owner.y + dy >= len(GAME.current_map) or self.owner.y < 0:
            print("Tried to move out of map")
            return

        if self.owner.x + dx >= len(GAME.current_map) or self.owner.x < 0:
            print("Tried to move out of map")
            return

        target = None

        target = map_check_for_creature(self.owner.x + dx, self.owner.y + dy, self.owner)

        if target:
            damage_dealt = self.attack_mod
            self.attack(target, damage_dealt)

        tile_is_wall = (GAME.current_map[self.owner.x + dx][self.owner.y + dy].block_path == True)

        if not tile_is_wall and target is None:
            self.owner.x += dx
            self.owner.y += dy

    def attack(self, target, damage):

        GAME.game_message(self.name_instance + " attacks " + target.creature.name_instance + " for " +
                     str(damage) +
                     " damage!", "red")
        target.creature.take_damage(damage)

    def take_damage(self, damage):
        self.hp -= damage
        GAME.game_message(self.name_instance + "'s hp is " + str(self.hp) + "/" + str(self.max_hp), "white")

        if self.hp <= 0:
            if self.death_function is not None:
                self.death_function(self.owner)

class AI_test:
    def take_turn(self):
        self.owner.creature.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1, 1))

def roll(dice, sides):
    result = 0
    for i in range(0, dice, 1):
        roll = libtcod.random_get_int(0, 1, sides)
        result += roll

    print 'Rolling ' + str(dice) + "d" + str(sides) + " result: " + str(result)
    return result

def death_monster(monster):
    GAME.game_message(monster.creature.name_instance + " is dead!", "gray")
    # clean up components
    monster.creature = None
    monster.ai = None
    # remove from map
    GAME.current_entities.remove(monster)



# dungeon generation functions
def create_room(room, new_map):
    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            new_map[x][y].block_path = False


def create_h_tunnel(x1, x2, y, new_map):
    # horizontal tunnel. min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        new_map[x][y].block_path = False


def create_v_tunnel(y1, y2, x, new_map):
    # vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        new_map[x][y].block_path = False


def map_create():
    new_map = [[struct_Tile(True) for y in range(0, constants.MAP_HEIGHT)] for x in range(0, constants.MAP_WIDTH)]

    rooms = []
    num_rooms = 0

    for r in range(constants.MAX_ROOMS):
        # random width and height
        w = libtcod.random_get_int(0, constants.ROOM_MIN_SIZE, constants.ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, constants.ROOM_MIN_SIZE, constants.ROOM_MAX_SIZE)
        # random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, constants.MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, constants.MAP_HEIGHT - h - 1)

        # "Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        # run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            # this means there are no intersections, so this room is valid

            # "paint" it to the map's tiles
            create_room(new_room, new_map)

            # center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                # this is the first room, where the player starts at
                player_x = new_x
                player_y = new_y
            else:
                # all rooms after the first:
                # connect it to the previous room with a tunnel

                # center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                # draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    # first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y, new_map)
                    create_v_tunnel(prev_y, new_y, new_x, new_map)
                else:
                    # first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x, new_map)
                    create_h_tunnel(prev_x, new_x, new_y, new_map)

            # finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

    # some walls just to test
    #new_map[10][10].block_path = True
    #new_map[12][12].block_path = True

    # walls around the map
    # for x in range(constants.MAP_WIDTH):
    #     new_map[x][0].block_path = True
    #     new_map[x][constants.MAP_WIDTH-1].block_path = True
    #
    # for y in range(constants.MAP_HEIGHT):
    #     new_map[0][y].block_path = True
    #     new_map[constants.MAP_HEIGHT-1][y].block_path = True

    map_make_fov(new_map)

    return new_map, rooms


def map_make_fov(incoming_map):
    global FOV_MAP

    FOV_MAP = libtcod.map_new(constants.MAP_WIDTH, constants.MAP_HEIGHT)

    for y in range(constants.MAP_HEIGHT):
        for x in range(constants.MAP_WIDTH):
            libtcod.map_set_properties(FOV_MAP, x,y,
                                       not incoming_map[x][y].block_path, not incoming_map[x][y].block_path)

def map_calculate_fov():
    global FOV_CALCULATE

    if FOV_CALCULATE:
        FOV_CALCULATE = False
        libtcod.map_compute_fov(FOV_MAP, PLAYER.x, PLAYER.y, constants.LIGHT_RADIUS, constants.FOV_LIGHT_WALLS,
                                constants.FOV_ALGO)

def map_check_for_creature(x, y, exclude_entity=None):

    target = None

    # find entity that isn't excluded
    if exclude_entity:
        for ent in GAME.current_entities:
            if (ent is not exclude_entity
                and ent.x == x
                and ent.y == y):
                target = ent

            if target:
                return target

    # find any entity if no exclusions
    else:
        for ent in GAME.current_entities:
            if (ent.x == x
                and ent.y == y):
                target = ent


# based on STI library for LOVE2D
# this places 0,0 at the top of the screen in the middle
# as opposed to other isometric calculations which might place 0,0 in lower left
def draw_iso(x,y):
    # we're offsetting so that we can see the lower-left corner of the map, otherwise it only shows the right half of it
    offset_x = constants.MAP_WIDTH * 4
    # isometric
    tile_x = (x - y) * constants.TILE_WIDTH / 2 + offset_x
    tile_y = (x + y) * constants.TILE_HEIGHT / 2
    return tile_x, tile_y

def draw_map(map_draw):
    for x in range(0, constants.MAP_WIDTH):
        for y in range(0, constants.MAP_HEIGHT):

            is_visible = libtcod.map_is_in_fov(FOV_MAP, x, y)

            if is_visible:
                tile_x, tile_y = draw_iso(x, y)
                blt.color("white")
                map_draw[x][y].explored = True

                if map_draw[x][y].block_path == True:
                    # draw wall
                    blt.put(tile_x, tile_y, "#")

                else:
                    # draw floor
                    blt.put(tile_x, tile_y, 0x3002)
                    #we draw the dot for reference so that we know what on-screen position the tile_x, tile_y refers to
                    blt.put(tile_x, tile_y, ".")

            elif map_draw[x][y].explored:
                tile_x, tile_y = draw_iso(x, y)
                # shade the explored tiles
                blt.color("gray")
                if map_draw[x][y].block_path == True:
                    # draw wall
                    blt.put(tile_x, tile_y, "#")

                else:
                    # draw floor
                    blt.put(tile_x, tile_y, 0x3002)
                    #we draw the dot for reference so that we know what on-screen position the tile_x, tile_y refers to
                    blt.put(tile_x, tile_y, ".")


def draw_messages(msg_history):
    if len(msg_history) <= constants.NUM_MESSAGES:
        to_draw = msg_history
    else:
        to_draw = msg_history[-constants.NUM_MESSAGES:]

    start_y = 45 - (constants.NUM_MESSAGES)

    i = 0
    for message, color in to_draw:
        string = "[color=" + str(color) + "] " + message
        blt.puts(2, start_y+i, string)

        i += 1

def draw_game():
    # draw map
    draw_map(GAME.current_map)

    # because the map might have been drawn in another color
    blt.color("white")
    # draw our entities
    for ent in GAME.current_entities:
        ent.draw()

    # draw messages
    draw_messages(GAME.message_history)

# Get free tiles of our map
def get_free_tiles(inc_map):
    free_tiles = []
    for y in range(len(inc_map)):
        for x in range(len(inc_map[0])):
            if not inc_map[x][y].block_path:
                free_tiles.append((x, y))
    return free_tiles

# The traditional way of picking a random spot seems to be iterating over all tiles, if it's blocked, retry
# ... if reached a certain number of tries, abort...
# This way, we only need to pick a random index of a list, we don't have to retry at all
def random_free_tile(inc_map):
    free_tiles = get_free_tiles(inc_map)
    index = libtcod.random_get_int(0, 0, len(free_tiles) - 1)
    # print("Index is " + str(index))
    x = free_tiles[index][0]
    y = free_tiles[index][1]
    print("Coordinates are " + str(x) + " " + str(y))
    return x, y

# This function makes sure every NPC has the creature and AI components
# X,Y need to come last because we're using tuple unwrapping
def NPC_wrapper(char, name, x,y):
    creature_comp = com_Creature(name, death_function=death_monster)
    ai_comp = AI_test()
    NPC = obj_Entity(x,y, char, creature=creature_comp, ai=ai_comp)
    return NPC

# Core game stuff
def game_main_loop():
    game_quit = False

    while not game_quit:

        # clear
        blt.clear()

        # draw game
        draw_game()

        # refresh term
        blt.refresh()

        # avoid blocking the game with blt.read
        while not game_quit and blt.has_input():
            player_action = game_handle_keys()

            map_calculate_fov()

            if player_action == "QUIT":
                game_quit = True

            # let the AIs take action
            if player_action != "no-action" and player_action != "mouse_click":
                for ent in GAME.current_entities:
                    if ent.ai:
                        ent.ai.take_turn()

    # quit the game
    blt.close()


def game_handle_keys():
    global FOV_CALCULATE

    key = blt.read()

    if key in (blt.TK_ESCAPE, blt.TK_CLOSE):
        return "QUIT"

    # Player movement
    if key == blt.TK_UP:
        PLAYER.creature.move(0, -1)
        FOV_CALCULATE = True
    if key == blt.TK_DOWN:
        PLAYER.creature.move(0, 1)
        FOV_CALCULATE = True
    if key == blt.TK_LEFT:
        PLAYER.creature.move(-1, 0)
        FOV_CALCULATE = True
    if key == blt.TK_RIGHT:
        PLAYER.creature.move(1, 0)
        FOV_CALCULATE = True


def game_initialize():
    global GAME, PLAYER, FOV_CALCULATE

    blt.open()
    # default terminal size is 80x25
    # we need nonstandard size to fit the test map
    blt.set("window: size=160x45, cellsize=auto, title='roguelike dev does the tutorial'; font: default")

    # we need composition to be able to draw tiles on top of other tiles
    blt.composition(True)

    # needed to avoid insta-close
    blt.refresh()

    # tiles
    # we use Unicode code point 3002 instead of a normal dot because the dot will be necessary for message log
    blt.set("0x3002: gfx/floor_sand.png, align=center")
    # no such problems with @ and #
    blt.set("0x23: gfx/wall_stone.png, align=center")  # "#"
    blt.set("0x40: gfx/human_m.png, align=center")  # "@"
    # NPCs (we use Unicode private area here)
    blt.set("0xE000: gfx/kobold.png,  align=center")  # ""
    blt.set("0xE001: gfx/goblin.png, align=center")

    GAME = obj_Game()

    FOV_CALCULATE = True

    player_x, player_y = GAME.current_rooms[0].center()
    creature_com1 = com_Creature("Player")
    PLAYER = obj_Entity(player_x, player_y, "@", creature=creature_com1)
    #PLAYER = obj_Entity(1, 1, "@")

    # two test enemies
    # * means we're unwrapping the tuple (Python 2.7 only allows it as the last parameter)
    # the GAME.add_entity function wraps the current_entities.append and checks if we're not trying to add a None
    GAME.add_entity(NPC_wrapper(0xE000, "kobold", *random_free_tile(GAME.current_map)))
    GAME.add_entity(NPC_wrapper(0xE001, "goblin", *random_free_tile(GAME.current_map)))

    # put player last
    GAME.current_entities.append(PLAYER)

# Execute
if __name__ == '__main__':
    game_initialize()
    game_main_loop()

# coding: utf8

from bearlibterminal import terminal as blt
import libtcodpy as libtcod
import math

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
    ''' Name is the name of the whole class, e.g. "goblin"'''
    def __init__(self, x, y, char, name, creature=None, ai=None, container=None, item=None, equipment=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name

        # both creature and AI are optional
        self.creature = creature

        if self.creature:
            creature.owner = self

        self.ai = ai
        if self.ai:
            ai.owner = self

        # container allows the player to pick up items
        self.container = container
        if self.container:
            container.owner = self

        # these optional components make the entity an pickable and/or wearable item
        self.item = item
        if self.item:
            item.owner = self

        self.equipment = equipment
        if self.equipment:
            equipment.owner = self

    def display_name(self):
        if self.creature:
            return (self.creature.name_instance + " the " + self.name)

        if self.item:
            if self.equipment and self.equipment.equipped:
                return self.name + " (equipped in slot: " + self.equipment.slot + ")"
            else:
                return self.name

    def draw(self):
        is_visible = libtcod.map_is_in_fov(FOV_MAP, self.x, self.y)

        if is_visible:
            tile_x, tile_y = draw_iso(self.x, self.y)
            # draw our entity's ASCII symbol at an offset
            # blt.put_ext(tile_x, tile_y, 0, blt.state(blt.TK_CELL_HEIGHT), self.char)

            # draw the tile at different offset because size of a tile is much different than the size of an ASCII letter
            blt.put_ext(tile_x, tile_y, 0, 2, self.char)


    def distance_to(self, other):
        # return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

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

# Inventory and items
class com_Container:
    def __init__(self, inventory = None):
        if inventory is None:
            inventory = []
        self.inventory = inventory

    @property
    def equipped_items(self):
        list_equipped = [obj for obj in self.inventory
                         if obj.equipment and obj.equipment.equipped]

        return list_equipped

class com_Item:
    def __init__(self, weight=0.0, use_function=None):
        self.weight = weight
        self.use_function = use_function

    def pick_up(self, actor):
        if actor.container:
            GAME.game_message("Picking up", "white")
            actor.container.inventory.append(self.owner)
            self.current_container = actor.container
            GAME.current_entities.remove(self.owner)

    def drop(self, new_x, new_y):
        GAME.game_message("Item dropped", "white")
        self.current_container.inventory.remove(self.owner)
        GAME.current_entities.append(self.owner)
        self.owner.x = new_x
        self.owner.y = new_y

    def use(self, actor):
        # equip it if it's a piece of equipment
        if self.owner.equipment:
            self.owner.equipment.toggle_equip(actor)
            return
        # use it if it has a function defined
        if self.use_function:
            # destroy after use, unless it was cancelled for some reason
            if self.use_function() != 'cancelled':
                self.current_container.inventory.remove(self.owner)


class com_Equipment:
    def __init__(self, slot, num_dice = 1, damage_dice = 4, attack_bonus = 0, defense_bonus = 0):
        self.slot = slot
        self.equipped = False
        self.num_dice = num_dice
        self.damage_dice = damage_dice
        self.attack_bonus = attack_bonus
        self.defense_bonus = defense_bonus

    def toggle_equip(self, actor):
        if self.equipped:
            self.unequip(actor)
        else:
            self.equip(actor)

    def equip(self, actor):
        old_equipment = get_equipped_in_slot(actor, self.slot)
        if old_equipment is not None:
            #print "Unequipping " + old_equipment.owner.name
            old_equipment.unequip(actor)

        self.equipped = True
        GAME.game_message("Item equipped", "white")

    def unequip(self, actor):
        self.equipped = False
        GAME.game_message("Took off item", "white")



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

# returns the equipment in a slot, or None if it's empty
def get_equipped_in_slot(actor, slot):
    for obj in actor.container.inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.equipped:
            return obj.equipment
    return None

# spells
def closest_monster(max_range):
    # find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  # start with (slightly more than) maximum range

    for object in GAME.current_entities:
        if object.creature and not object == PLAYER and libtcod.map_is_in_fov(FOV_MAP, object.x, object.y):
            # calculate distance between this object and the player
            dist = PLAYER.distance_to(object)
            if dist < closest_dist:  # it's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy


def cast_lightning():
    # find closest enemy (inside a maximum range) and damage it
    monster = closest_monster(constants.LIGHTNING_RANGE)
    if monster is None:  # no enemy found within maximum range
        GAME.game_message('No enemy is close enough to strike.', "red")
        return 'cancelled'

    # zap it!
    GAME.game_message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! It deals '
            + str(constants.LIGHTNING_DAMAGE) + ' damage.', "light blue")
    monster.creature.take_damage(constants.LIGHTNING_DAMAGE)

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
                and ent.y == y
                and ent.creature):
                target = ent

            if target:
                return target

    # find any entity if no exclusions
    else:
        for ent in GAME.current_entities:
            if (ent.x == x
                and ent.y == y):
                target = ent

def map_check_for_item(x, y):
    target = None

    for ent in GAME.current_entities:
        if (ent.x == x
            and ent.y == y
            and ent.item):
            target = ent

        if target:
            return target


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

# GUI
# based on https://github.com/FirstAidKitten/Roguelike-Sandbox
def create_window(x, y, w, h, title=None):
    #test
    blt.composition(False)

    last_bg = blt.state(blt.TK_BKCOLOR)
    blt.bkcolor(blt.color_from_argb(200, 0, 0, 0))
    blt.clear_area(x - 2, y - 2, w + 2, h + 2)
    blt.bkcolor(last_bg)

    # upper border
    border = '┌' + '─' * (w) + '┐'
    blt.puts(x - 1, y - 1, border)
    # sides
    for i in range(h):
        blt.puts(x - 1, y + i, '│')
        blt.puts(x + w, y + i, '│')
    # lower border
    border = '└' + '─' * (w) + '┘'
    blt.puts(x - 1, y + h, border)

    if title is not None:
        leng = len(title)
        offset = (w + 2 - leng) // 2
        blt.puts(x + offset, y - 1, title)


def menu(header, options, width, title=None):
    global FOV_CALCULATE

    FOV_CALCULATE = True

    menu_x = int((120 - width) / 2)

    if len(options) > 26:
        raise ValueError('Cannot have a menu with more than 26 options.')

    header_height = 2

    menu_h = int(header_height + 1 + 26)
    menu_y = int((50 - menu_h) / 2)

    # create a window

    create_window(menu_x, menu_y, width, menu_h, title)


    blt.puts(menu_x, menu_y, header)

    # print all the options
    y = menu_y + header_height + 1
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        blt.puts(menu_x, y, text)
        y += 1
        letter_index += 1

    blt.refresh()
    # present the root console to the player and wait for a key-press
    blt.set('input: filter = [keyboard]')
    while True:
        key = blt.read()
        if blt.check(blt.TK_CHAR):
            # convert the ASCII code to an index; if it corresponds to an option, return it
            key = blt.state(blt.TK_CHAR)
            index = key - ord('a')
            if 0 <= index < len(options):
                blt.set('input: filter = [keyboard, mouse+]')
                blt.composition(True)
                return index
        else:
            blt.set('input: filter = [keyboard, mouse+]')
            blt.composition(True)
            return None


def inventory_menu(header, player):
    # show a menu with each item of the inventory as an option
    if len(player.container.inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = [item.display_name() for item in player.container.inventory]

    index = menu(header, options, 50, 'INVENTORY')

    # if an item was chosen, return it
    if index is None or len(player.container.inventory) == 0:
        return None
    return player.container.inventory[index]


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
    NPC = obj_Entity(x,y, char, name, creature=creature_comp, ai=ai_comp)
    return NPC


def eq_wrapper(char, name, item_slot, x,y):
    eq_com = com_Equipment(item_slot)
    item_com = com_Item()
    item = obj_Entity(x, y, char, name, item=item_com, equipment=eq_com)
    return item


# this assumes a random spawn location
# we duplicate some code, sorry
def usable_item_wrapper(char, name, use):
    x, y = random_free_tile(GAME.current_map)
    item_com = com_Item(use_function=use)
    item = obj_Entity(x, y, char, name, item=item_com)
    return item


def item_wrapper(char, name, x,y):
    item_com = com_Item()
    item = obj_Entity(x, y, char, name, item=item_com)
    return item


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

    # items
    if key == blt.TK_G:
        ent = map_check_for_item(PLAYER.x, PLAYER.y)
        #for ent in objects:
        ent.item.pick_up(PLAYER)

    if key == blt.TK_D:
        if len(PLAYER.container.inventory) > 0:
            #drop the last item
            PLAYER.container.inventory[-1].item.drop(PLAYER.x, PLAYER.y)

    if key == blt.TK_I:
        chosen_item = inventory_menu("Inventory", PLAYER)
        if chosen_item is not None:
            if chosen_item.item:
                chosen_item.item.use(PLAYER)

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
    # items
    blt.set("0x2215: gfx/longsword.png, align=center")  # "∕"
    blt.set("0x203D: gfx/scroll.png, align=center") # "‽"
    # NPCs (we use Unicode private area here)
    blt.set("0xE000: gfx/kobold.png,  align=center")  # ""
    blt.set("0xE001: gfx/goblin.png, align=center")

    GAME = obj_Game()

    FOV_CALCULATE = True

    player_x, player_y = GAME.current_rooms[0].center()
    container_com1 = com_Container()
    creature_com1 = com_Creature("Player")
    PLAYER = obj_Entity(player_x, player_y, "@", "Player", creature=creature_com1, container=container_com1)
    #PLAYER = obj_Entity(1, 1, "@")

    #test item
    GAME.add_entity(eq_wrapper(0x2215, "sword", "main_hand", *random_free_tile(GAME.current_map)))
    GAME.add_entity(usable_item_wrapper(0x203D, "scroll", cast_lightning))

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

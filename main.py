from bearlibterminal import terminal as blt

import constants

# Needed for map
class struct_Tile:
    def __init__(self, block_path):
        self.block_path = block_path

# Storing our stuff in one place
class obj_Game:
    def __init__(self):
        self.current_map = map_create()
        self.current_entities = []

# Entity
class obj_Entity:
    def __init__(self, x, y, char):
        self.x = x
        self.y = y
        self.char = char

    def move(self, dx, dy):
        if self.y + dy >= len(GAME.current_map) or self.y < 0:
            print("Tried to move out of map")
            return

        if self.x + dx >= len(GAME.current_map) or self.x < 0:
            print("Tried to move out of map")
            return

        tile_is_wall = (GAME.current_map[self.x + dx][self.y + dy].block_path == True)

        if not tile_is_wall:
            self.x += dx
            self.y += dy


    def draw(self):
        tile_x, tile_y = draw_iso(self.x, self.y)
        # draw our entity's ASCII symbol at an offset
        # blt.put_ext(tile_x, tile_y, 0, blt.state(blt.TK_CELL_HEIGHT), self.char)

        # draw the tile at different offset because size of a tile is much different than the size of an ASCII letter
        blt.put_ext(tile_x, tile_y, 0, 2, self.char)

def map_create():
    new_map = [[struct_Tile(False) for y in range(0, constants.MAP_HEIGHT)] for x in range(0, constants.MAP_WIDTH)]

    # some walls just to test
    new_map[10][10].block_path = True
    new_map[12][12].block_path = True

    # walls around the map
    for x in range(constants.MAP_WIDTH):
        new_map[x][0].block_path = True
        new_map[x][constants.MAP_WIDTH-1].block_path = True

    for y in range(constants.MAP_HEIGHT):
        new_map[0][y].block_path = True
        new_map[constants.MAP_HEIGHT-1][y].block_path = True

    return new_map

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
            tile_x, tile_y = draw_iso(x, y)

            if map_draw[x][y].block_path == True:
                # draw wall
                blt.put(tile_x, tile_y, "#")

            else:
                # draw floor
                blt.put(tile_x, tile_y, 0x3002)
                #we draw the dot for reference so that we know what on-screen position the tile_x, tile_y refers to
                blt.put(tile_x, tile_y, ".")



def draw_game():
    # draw map
    draw_map(GAME.current_map)

    # draw our entities
    for ent in GAME.current_entities:
        ent.draw()


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

            if player_action == "QUIT":
                game_quit = True

    # quit the game
    blt.close()


def game_handle_keys():
    key = blt.read()

    if key in (blt.TK_ESCAPE, blt.TK_CLOSE):
        return "QUIT"

    # Player movement
    if key == blt.TK_UP:
        PLAYER.move(0, -1)
    if key == blt.TK_DOWN:
        PLAYER.move(0, 1)
    if key == blt.TK_LEFT:
        PLAYER.move(-1, 0)
    if key == blt.TK_RIGHT:
        PLAYER.move(1, 0)


def game_initialize():
    global GAME, PLAYER

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

    GAME = obj_Game()

    PLAYER = obj_Entity(1, 1, "@")

    GAME.current_entities = [PLAYER]

# Execute
if __name__ == '__main__':
    game_initialize()
    game_main_loop()
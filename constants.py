import libtcodpy as libtcod

# Map size
MAP_HEIGHT = 20
MAP_WIDTH = 20

# in number of cells
# default BearLibTerminal cell size is 8 px wide 16 px high
TILE_HEIGHT = 2
TILE_WIDTH = 8

#parameters for dungeon generator
ROOM_MAX_SIZE = 6
ROOM_MIN_SIZE = 4
MAX_ROOMS = 4

#FOV
FOV_ALGO = libtcod.FOV_BASIC
FOV_LIGHT_WALLS = True
LIGHT_RADIUS = 4
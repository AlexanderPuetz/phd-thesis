import argparse
import os
import sys
import re
import random
import numpy as np
import pandas as pd
import collections
import shutil
from PIL import Image,ImageFont,ImageDraw
# from time import sleep
# from fish import ProgressFish

# When this script is executed, some input is required:
parser = argparse.ArgumentParser()
parser.add_argument("mode",type=str,choices=['inf','pbc'],help="choose between an infinite lattice or periodic boundary conditions")
parser.add_argument("size",type=str,help="lattice size, format as '100x100'")
parser.add_argument("-hex","--hexagonal",action="store_true",help="switch square to a hexagonal lattice")
parser.add_argument("-g","--generations",type=int,default=500,action="store",help="number of generations, default = 500")
parser.add_argument("-f","--file",type=str,default="seed.cnw",action="store",help="name of the seed input file, default = '.O'")
parser.add_argument("-i","--input",type=str,default=".O",action="store",help="definition of dead/alive cells in seed input file, default = '.O'")
parser.add_argument("-r","--randomize",action="store_true",help="randomize the seed")
# parser.add_argument("-c","--colored",action="store_true",help="change colormap to rainbow instead of grey scale") # maybe color them according to the number of neighbors around them
parser.add_argument("-v","--video",action="store_false",help="disable video generation")
args = parser.parse_args()

# # Sorting the args into global variables and establishing arrays:
mode        = args.mode
size        = list(map(int, re.findall('\d+', args.size)))
hexagonal   = args.hexagonal
generations = args.generations
gen_number  = 0
seedfile    = args.file
input_style = list(args.input)
randomize   = args.randomize
# colored     = args.colored
video       = args.video

# Defining variable, arrays, ...

if hexagonal:
    bsc             = [2,3,4] # birth/survive conditions (B2/S34)
    vec_neigh       = np.array([[1,-1],[1,0],[0,1],[-1,1],[-1,0],[0,-1]])    
    width           = ((size[0]) * 12 + size[1] * 6) + 20
    height          = ((size[1]) * 10) + 70
    neighbor_number = 6
else:
    bsc             = [3,2,3] # birth/survive conditions (B3/S23)
    vec_neigh       = np.array([[-1,-1],[0,-1],[1,-1],[1,0],[1,1],[0,1],[-1,1],[-1,0]])
    width           = ((size[0]) * 12) + 20
    height          = (size[1]) * 12 + 70
    neighbor_number = 8

min_x, min_y  = 0, 0
max_x, max_y  = size
color         = [(55,55,55),(255,255,255)]
seed          = np.zeros((size[1],size[0]), dtype=np.int16)
cells         = dict()
changes       = []
gen_info      = [0,0,0,0,0] # size x, size y, number of births/deaths and total population
gen_info_list = np.zeros((generations+1, 6),dtype=np.int16) # list of generation number and generation info with column names: Generation, Size X, Size Y, Births, Deaths, Total Population

# =======================================================================

class Cell:

    def __init__(self, x, y, state):
        self.x = x
        self.y = y
        self.state = state

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def adjust_neighbors(self,change):
        self.neighbors += change

    def how_many_neighbors(self):
        neighbors = []
        global min_x
        global max_x
        global min_y
        global max_y
        for i in range(0,neighbor_number):
            neigh_x = self.x + vec_neigh[i,0]
            neigh_y = self.y + vec_neigh[i,1]
            if mode == "pbc": # loop at borders of the lattice
                if neigh_x < 0: neigh_x = size[0] + neigh_x
                if neigh_y < 0: neigh_y = size[1] + neigh_y
                if neigh_x >= size[0]: neigh_x = neigh_x - size[0]
                if neigh_y >= size[1]: neigh_y = neigh_y - size[1]
            elif mode == "inf": # extend lattice if necessary
                if neigh_x < min_x or neigh_x > max_x:
                    for y in range(min(min_y,neigh_y), max(max_y,neigh_y) + 1):
                        cell = str(f"{neigh_x}|{y}")
                        cells[cell] = Cell(neigh_x, y, 0)
                if neigh_y < min_y or neigh_y > max_y:
                    for x in range(min(min_x,neigh_x), max(max_x,neigh_x) + 1):
                        cell = str(f"{x}|{neigh_y}")
                        cells[cell] = Cell(x, neigh_y, 0)
            neighbor = str(f"{neigh_x}|{neigh_y}")
            neighbors.append(cells[neighbor].get_state())
        return sum(neighbors)


# =======================================================================

def create_visible_cells():
    for x,y in ((x,y) for x in range(0, size[0]+1) for y in range(0, size[1]+1)):
        cell = str(f"{x}|{y}")
        cells[cell] = Cell(x, y, 0)


def read_seed_input():
    global changes
    """Read the input file and place it in the middle of the lattice"""
    with open(seedfile) as seed_input:
        seed_str = seed_input.read()
    rows = seed_str.split("\n")
    indent_y = int((size[1] - len(rows)) / 2)
    for y in range(0,len(rows)): # walk over rows ...
        columns = list(rows[y])
        indent_x = int((size[0] - len(columns)) / 2)
        for x in range(0,len(columns)): # ... and columns
            if columns[x] == input_style[0]:
                seed[y + indent_y, x + indent_x] = 0 # parse the string input into ones and zeros
                changes.append([x + indent_x, y + indent_y, 0])
            elif columns[x] == input_style[1]:
                seed[y + indent_y, x + indent_x] = 1
                changes.append([x + indent_x, y + indent_y, 1])
            else: raise ValueError(f"Input lattice must only consist of '{input_style[0]}' and '{input_style[1]}'")
    apply_changes()
    # print(seed)


def randomize_seed():
    global changes
    for y,x in ((y,x) for x in range(0,size[0]) for y in range(0,size[1])):
        changes.append([x, y, round(random.random())])
    apply_changes()
    # print(seed)

def apply_changes():
    global changes
    for change in changes:
        cell = str(f"{change[0]}|{change[1]}")
        cells[cell].set_state(change[2])
    changes = []

def advance_generation():
    apply_changes()
    for x,y in ((x,y) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)):
        decide_fate(x,y)

def decide_fate(x,y):
    global changes
    global gen_info
    global min_x
    global max_x
    global min_y
    global max_y
    cell = str(f"{x}|{y}")
    n = cells[cell].how_many_neighbors()
    if n == bsc[0]:
        changes.append([x, y, 1])
        gen_info[2] += 1
    elif cells[cell].get_state() == 1 and (n < bsc[1] or n > bsc[2]): 
        changes.append([x, y, 0])
        gen_info[3] += 1
    if x < min_x: min_x = x
    elif x > max_x: max_x = x
    if x < min_y: min_y = y
    elif x > max_y: max_y = y


def print_lattice():
    """Print a given lattice as an image consisting of circles, where living cells are white.
       Some information about the simulation is also provided."""
    img  = Image.new('RGB',(width,height),color=0)
    draw = ImageDraw.Draw(img)

    menlo_regular    = ImageFont.truetype("../fonts/Menlo.ttf",15)
    menlo_italic     = ImageFont.truetype("../fonts/MenloItalic.ttf",15)
    menlo_bold       = ImageFont.truetype("../fonts/MenloBold.ttf",15)
    menlo_bolditalic = ImageFont.truetype("../fonts/MenloBoldItalic.ttf",15)
    white = 255,255,255

    draw.text((10,10),"J.H. Conway's Game of Life",white,font=menlo_bold)
    draw.text((10,height-25),f"Generation {gen_number}",white,font=menlo_bold)

    for y in range(0,size[1]):
        for x in range(0,size[0]):
            if hexagonal:
                pos_x = (x * 12 + y * 6) + 10
                pos_y = (x * 0 + y * 10) + 35
            else:
                pos_x = (x * 12) + 10
                pos_y = (y * 12) + 35
            cell = str(f"{x}|{y}")
            draw.ellipse((pos_x,pos_y,pos_x+10,pos_y+10), fill=color[cells[cell].get_state()], outline=color[cells[cell].get_state()])
    del draw
    img.save('Gen%04d' % gen_number + '.png',"PNG")
    # img.show() # open image in default viewer


# ================================================================================

def main():
    global gen_number
    shutil.copy(__file__, "_current_script_version.py") # save a backup of the executed PY script
    create_visible_cells()
    if randomize: randomize_seed()
    else: read_seed_input()
    print("The seeds are sown. Let Conway's Game of Life begin!")
    for gen in range(0,generations+1):
        gen_info = [0,0,0,0,0]
        population = 0
        print_lattice()
        advance_generation()
        gen_number += 1
        sys.stdout.write('\r') # print a progress bar
        sys.stdout.write("[%-50s] %d%%" % ('='*int(gen_number*50/generations), int(2*gen_number*50/generations)))
        sys.stdout.flush()
        for x,y in ((x,y) for x in range(min_x + 1, max_x) for y in range(min_y + 1, max_y)):
            if cells[str(f"{x}|{y}")].get_state() == 1: population += 1
        gen_info[0] = (max_x-min_x) 
        gen_info[1] = (max_y-min_y)
        gen_info[4] = population
        gen_info_list[gen_number-1,0] = gen_number # index the list of generational information with generation number, ...
        for i in range(0,5): gen_info_list[gen_number-1,i+1] = gen_info[i]
    print('') # include a line break after the progress bar
    df = pd.DataFrame(gen_info_list,columns=['Generation','Size X','Size Y','Births','Deaths','Total Population'])
    df.to_csv('./_generations.csv',index=False) # save table of transitions in a CSV file
    print(f"Conway's Game of Life finished successfully after {generations} generations!")
    if video: os.system(f"ffmpeg -r 6 -f image2 -i Gen%04d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p -s {width}x{height} _animation.mp4")


if __name__ == "__main__":
    main()









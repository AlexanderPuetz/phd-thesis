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
parser.add_argument("-v","--video",action="store_true",help="generate video of simulation")
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
    width           = ((size[0]-1) * 12 + size[1] * 6) + 490
    height          = ((size[1]-1) * 10)
    neighbor_number = 6
else:
    bsc             = [3,2,3] # birth/survive conditions (B3/S23)
    vec_neigh       = np.array([[-1,-1],[0,-1],[1,-1],[1,0],[1,1],[0,1],[-1,1],[-1,0]])
    width           = ((size[0]-1) * 12) + 490
    height          = (size[1]-1) * 12
    neighbor_number = 8

if mode == "inf":
    current_gen_tl   = np.zeros((1000000,1000000), dtype=np.int16) # top left (--)
    previous_gen_tl  = np.zeros((1000000,1000000), dtype=np.int16)
    current_gen_tr   = np.zeros((1000000,1000000), dtype=np.int16) # top right (+-)
    previous_gen_tr  = np.zeros((1000000,1000000), dtype=np.int16)
    current_gen      = np.zeros((1000000,1000000), dtype=np.int16) # bottom right (++)
    previous_gen     = np.zeros((1000000,1000000), dtype=np.int16)
    current_gen_bl   = np.zeros((1000000,1000000), dtype=np.int16) # bottom left (-+)
    previous_gen_bl  = np.zeros((1000000,1000000), dtype=np.int16)
elif mode == "pbc":
    current_gen   = np.zeros((size[0],size[1]), dtype=np.int16)
    previous_gen  = np.zeros((size[0],size[1]), dtype=np.int16)

color         = [(55,55,55),(255,255,255)]
seed          = np.zeros((size[0],size[1]), dtype=np.int16)
gen_info      = [0,0,0] # number of births/deaths and total population
gen_info_list = np.zeros((generations+1, 4),dtype=np.int16) # list of generation number and generation info with column names: Generation, Births, Deaths, Total Population

# =======================================================================
def read_seed_input():
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
                current_gen[y + indent_y, x + indent_x] = 0
            elif columns[x] == input_style[1]: 
                seed[y + indent_y, x + indent_x] = 1
                current_gen[y + indent_y, x + indent_x] = 1
            else: raise ValueError(f"Input lattice must only consist of '{input_style[0]}' and '{input_style[1]}'")
    # print(seed)

def randomize_seed():
    for y,x in ((y,x) for x in range(0,size[0]) for y in range(0,size[1])):
        seed[y,x] = round(random.random())
    # print(seed)


def advance_generation():
    global previous_gen
    global current_gen
    previous_gen = current_gen
    if mode == "inf":
        global previous_gen_tl
        global current_gen_tl
        previous_gen_tl = current_gen_tl
        global previous_gen_tr
        global current_gen_tr
        previous_gen_tr = current_gen_tr
        global previous_gen_bl
        global current_gen_bl
        previous_gen_bl = current_gen_bl
        for y,x in ((x,y) for x in range(0,999995) for y in range(0,999995)):
            current_gen_tl[y,x] = decide_fate(-y-1,-x-1)
            current_gen_tr[y,x] = decide_fate(-y-1,x)
            current_gen[y,x] = decide_fate(y,x)
            current_gen_bl[y,x] = decide_fate(y,-x-1)
        #     current_gen_tr[0,x] = decide_fate(-1,x)
        #     current_gen_bl[y,0] = decide_fate(y,-1)
        # current_gen_tl[0,0] = decide_fate(-1,-1)
    else:
        for y,x in ((y,x) for x in range(0,size[0]) for y in range(0,size[1])):
            current_gen[y,x] = decide_fate(y,x)


def decide_fate(y,x):
    n = how_many_neighbors(y,x)
    if n == bsc[0]: return 1
    elif n < bsc[1] or n > bsc[2]: return 0


def how_many_neighbors(y,x):
    global previous_gen
    neighbors = []
    for i in range(0,neighbor_number):
        if mode == "inf":
            neigh_y = y + vec_neigh[i,1]
            neigh_x = x + vec_neigh[i,0]
            if neigh_y < 0 and neigh_x < 0: neighbors.append(previous_gen_tl[-neigh_y + 1, -neigh_x + 1])
            elif neigh_y < 0 and neigh_x >= 0: neighbors.append(previous_gen_tr[-neigh_y + 1, neigh_x])
            elif neigh_y >= 0 and neigh_x >= 0: neighbors.append(previous_gen[neigh_y, neigh_x])
            elif neigh_y >= 0 and neigh_x < 0: neighbors.append(previous_gen_bl[neigh_y, -neigh_x + 1])
        else:
            neigh_y = y + vec_neigh[i,1]
            neigh_x = x + vec_neigh[i,0]
            # if neigh_y < 0: neigh_y =    # should work since it adresses the first, second to last
            if neigh_y >= size[1]: neigh_y = neigh_y - size[1]
            if neigh_x >= size[0]: neigh_x = neigh_x - size[0]
            neighbors.append(previous_gen[neigh_y, neigh_x]) 
    return sum(neighbors)



def print_lattice():
    """Print a given lattice as an image consisting of circles, where living cells are white.
       Some information about the simulation is also provided."""
    img  = Image.new('RGB',(width,height),color=0)
    draw = ImageDraw.Draw(img)

    menlo_normal     = ImageFont.truetype("../fonts/Menlo.ttf",30)
    menlo_italic     = ImageFont.truetype("../fonts/MenloItalic.ttf",30)
    menlo_bold       = ImageFont.truetype("../fonts/MenloBold.ttf",30)
    menlo_bolditalic = ImageFont.truetype("../fonts/MenloBoldItalic.ttf",30)
    white = 255,255,255

    # if model == 'lennard_jones': draw.text((width-460,20),"Lennard Jones Model",white,font=menlo_italic)
    # elif model == 'exponential': draw.text((width-460,20),"Exponential Model",white,font=menlo_italic)
    # elif model == 'squared': draw.text((width-460,20),"Squared Model",white,font=menlo_italic)
    # draw.text((width-460,75),"%s x %s Pores" % (size[0],size[1]),white,font=menlo_normal)
    # if annealing != 'static':
    #     draw.text((width-460,110),"With simulated annealing",white,font=menlo_normal)
    #     if annealing == 'dynamic': draw.text((width-460,145),"Dynamic",white,font=menlo_italic)
    #     elif annealing == 'linear': draw.text((width-460,145),"Linear",white,font=menlo_italic)
    #     offset = 35
    # else: draw.text((width-460,110),"W/out simulated annealing",white,font=menlo_normal)
    # draw.text((width-460,165+offset),"Temperature:     %s" % (abs(round(temp,2))),white,font=menlo_normal)
    # draw.text((width-460,200+offset),"Simulation runs: %s" % (add_sfx(sim)),white,font=menlo_normal)
    # draw.text((width-460,height-110-wall_number*35),"Fill levels:",white,font=menlo_italic)
    # for i in range(0,wall_number+1):
    #     draw.rectangle((width-460,height-55-(wall_number-i)*35,width-370,height-20-(wall_number-i)*35),fill=color[i], outline=color[i])
    #     draw.text((width-360,height-55-(wall_number-i)*35),"%s" % (i),white,font=menlo_normal)

    for y in range(0,size[1]-1):
        for x in range(0,size[0]-1):
            if hexagonal:
                pos_x = x * 12 + y * 6
                pos_y = x * 0 + y * 10
            else:
                pos_x = x * 12
                pos_y = y * 12
            draw.ellipse((pos_x,pos_y,pos_x+10,pos_y+10), fill=color[current_gen[y,x]], outline=color[current_gen[y,x]])
    del draw
    img.save('Gen%04d' % gen_number + '.png',"PNG")
    # img.show() # open image in default viewer


# ================================================================================

def main():
    if randomize: randomize_seed()
    else: read_seed_input()
    for gen in range(0,generations):
        print_lattice()
        advance_generation()
        gen_number += 1
    if video: os.system(f"ffmpeg -r 2 -f image2 -i Gen%04d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p -s {width}x{height} animation.mp4")


if __name__ == "__main__":
    main()









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
parser.add_argument("net_symbol",type=str,choices=['hxl','sql'],help="hexagonal or tetragonal lattice")
parser.add_argument("sim_model",type=str,choices=['lennard_jones','reciprocal','squared'],help="simulation model used to compare frustration of two neighboring pores") # ----- maybe implement a standard model at some point (lennard_jones?)
parser.add_argument("annealing",type=str,choices=['simulated_annealing','dynamic','linear','static'],help="implement dynamic or linear simulated annealing or a static error") # :::::::::::::::::::::::ADAPT THIS
parser.add_argument("-s","--size",dest='size',type=str,default='100x100',action="store",help="lattice size, default = '100x100'")
parser.add_argument("-i","--init",dest='init',type=int,default=500000,action="store",help="number of random flips at initialization, default = 500k")
parser.add_argument("-r","--runs",dest='runs',type=int,default=1000000,action="store",help="number of simulation runs, default = 1E6")
parser.add_argument("-f","--frames",dest='frames',type=int,default=20,action="store",help="number of image outputs, default = 20")
parser.add_argument("-t","--temperature",dest='temperature',type=float,default=1,action="store",help="temperature from which acceptance probablity is calculated, default = 1")
parser.add_argument("-l","--levels",action="store_true",help="print final result seperatly for each fill level")
parser.add_argument("-c","--colored",action="store_true",help="change colormap to rainbow instead of grey scale")
parser.add_argument("-v","--video",action="store_true",help="generate video of simulation")
args = parser.parse_args()

# Sorting the args into global variables and establishing arrays:
net         = args.net_symbol                        # ----- add descriptions for each
init_grade  = args.init
model       = args.sim_model
annealing   = args.annealing
size        = list(map(int, re.findall('\d+', args.size)))
runs        = args.runs
sim         = 0
frames      = args.frames
temp,temp_i = args.temperature,args.temperature
levels      = args.levels
colored     = args.colored
video       = args.video

if net == 'hxl':
    vec_walls = np.array([[1,-1],[1,0],[0,1],[-1,1],[-1,0],[0,-1]])
    width               = ((size[0]-1) * 12 + size[1] * 6) + 490
    height              = ((size[1]-1) * 10)
    lennard_jones_max   = 5.52 # empirical value for which frustration is 1, thus frustration(6) = 0.47
    reciprocal_shift    = 7
    wall_number         = 6
    if colored: color = [(0,0,255),(0,153,255),(0,255,255),(0,255,51),(255,255,0),(255,153,0),(255,0,0)]

    else: color = [(55,55,55),(84,84,84),(113,113,113),(142,142,142),(171,171,171),(200,200,200),(255,255,255)]
elif net == 'sql':
    vec_walls = np.array([[0,-1],[1,0],[0,1],[-1,0]])
    width               = ((size[0]-1) * 12) + 490
    height              = (size[1]-1) * 12
    lennard_jones_max = 3.68 # empirical value for which frustration is 1, thus frustration(4) = 0.47
    reciprocal_shift    = 5
    wall_number         = 4
    if colored: color = [(0,0,255),(0,255,255),(0,255,51),(255,255,0),(255,0,0)]
    else: color = [(55,55,55),(105,105,105),(155,155,155),(205,205,205),(255,255,255)]

fills = np.ones((size[0],size[1]), dtype=np.int16)
walls = np.ones((size[0],size[1],wall_number), dtype=np.int16)
operations = [0,0,0] # number of downhill/uphill transitions or none
operations_list = np.zeros((frames+1,4),dtype=np.int16) # list of frame number and excecuted transitions with column names: Frame, Downhill Transitions, Uphill Transitions, None

# =======================================================================

def fill(a,b):
    """Calculates the fill value of a given pore (a,b)"""
    return len([v for v in walls[a,b] if v == 1]) # make a list from all values in the walls array that == 1 and return the length
    # old clunky code:
    # fill = 0
    # for i in walls[a,b]:
    #     if i == 1: fill += 1
    # return fill

def random_xy():
    """Return random coordinates on the lattice"""
    x = int(round(random.random()*(size[0]-1),0))
    y = int(round(random.random()*(size[1]-1),0))
    return [x,y]

    # return [int(round(random.random()*(size[0]-1),0)),int(round(random.random()*(size[1]-1),0))]

def initial_energy(index_list):
    """Take a transition index list and calculate the combined energy of the affected pores before the transition"""
    n,a,b,m,c,d = index_list # split index list back into individual variables
    return energy(fill(a,b)) + energy(fill(c,d))


def final_energy(index_list):
    """Take a transition index list and calculate the combined energy of the affected pores after the transition.
       If the first pore is already completly filled, or the second pore is completly empty, the transition cannot take place and the inital combined energy is returned."""
    n,a,b,m,c,d = index_list # split index list back into individual variables
    if fill(a,b) == wall_number or fill(c,d) == 0: return energy(fill(a,b)) + energy(fill(c,d))
    else: return energy(fill(a,b)+1) + energy(fill(c,d)-1)


def energy(fill):
    """    Return the energy value of a pore with respect to fill level based on different models in a.u."""
    if model == 'lennard_jones': # https://www.google.de/search?dcr=0&q=-(1*(5.52%2F(x-(2*5.52)))^6*((5.52%2F(x-(2*5.52)))^6-2))&oq=-(1*(5.52%2F(x-(2*5.52)))^6*((5.52%2F(x-(2*5.52)))^6-2))
        epsilon = -1 # define the maximum of the Lennard Jones function (rather arbitary, since values are not compared inbetween different models)
        energy = epsilon*(lennard_jones_max/(fill-(2*lennard_jones_max)))**6 * ((lennard_jones_max/(fill-(2*lennard_jones_max)))**6 - 2)

    elif model == 'reciprocal': # https://www.google.de/search?dcr=0&q=1%2F(x-7)
        energy = 1/(fill-reciprocal_shift)

    # elif model == 'exponential': # https://www.google.de/search?dcr=0&q=e^x
    #     energy = np.exp(fill)

    elif model == 'squared': # https://www.wolframalpha.com/input/?i=1+-+(1%2F((6%2F2)%5E2))+*+(x-(6%2F2))%5E2+from+0+to+6
        energy = 1 -(1/((wall_number/2)**2)) * (fill-(wall_number/2))**2 # normalized to 0 as lowest, 1 as highest value

    return float(energy)

# ================================================================================

def add_suffix(n): # add suffix
    """Convert long integer to more readable 10 k, 1 m, etc."""
    suffix = ['',' k',' m',' b']
    n = float(n)
    millidx = max(0,min(len(suffix)-1,int(np.floor(0 if n == 0 else np.log10(abs(n))/3))))
    if millidx == 2: return '{:.3f}{}'.format(n / 10**(3 * millidx), suffix[millidx]) # include three decimals for values over 1 m
    else: return '{:.0f}{}'.format(n / 10**(3 * millidx), suffix[millidx])


def print_image():
    """Print a given board as an image consisting of circles, where the fill is encoded in the color.
       Some information about the simulation is also provided."""
    img  = Image.new('RGB',(width,height),color=0)
    draw = ImageDraw.Draw(img)

    menlo_normal     = ImageFont.truetype("../fonts/Menlo.ttf",30)
    menlo_italic     = ImageFont.truetype("../fonts/MenloItalic.ttf",30)
    menlo_bold       = ImageFont.truetype("../fonts/MenloBold.ttf",30)
    menlo_bolditalic = ImageFont.truetype("../fonts/MenloBoldItalic.ttf",30)
    white = 255,255,255
    offset = 0

    if model == 'lennard_jones': draw.text((width-460,20),"Lennard Jones Model",white,font=menlo_italic)
    elif model == 'exponential': draw.text((width-460,20),"Exponential Model",white,font=menlo_italic)
    elif model == 'squared': draw.text((width-460,20),"Squared Model",white,font=menlo_italic)
    draw.text((width-460,75),"%s x %s Pores" % (size[0],size[1]),white,font=menlo_normal)
    if annealing != 'static':
        draw.text((width-460,110),"With simulated annealing",white,font=menlo_normal)
        if annealing == 'dynamic': draw.text((width-460,145),"Dynamic",white,font=menlo_italic)
        elif annealing == 'linear': draw.text((width-460,145),"Linear",white,font=menlo_italic)
        offset = 35
    else: draw.text((width-460,110),"W/out simulated annealing",white,font=menlo_normal)
    draw.text((width-460,165+offset),"Temperature:     %s" % (abs(round(temp,2))),white,font=menlo_normal)
    draw.text((width-460,200+offset),"Simulation runs: %s" % (add_suffix(sim)),white,font=menlo_normal)
    draw.text((width-460,height-110-wall_number*35),"Fill levels:",white,font=menlo_italic)
    for i in range(0,wall_number+1):
        draw.rectangle((width-460,height-55-(wall_number-i)*35,width-370,height-20-(wall_number-i)*35),fill=color[i], outline=color[i])
        draw.text((width-360,height-55-(wall_number-i)*35),"%s" % (i),white,font=menlo_normal)

    for b in range(0,size[1]-1):
        for a in range(0,size[0]-1):
            if net == 'hxl':
                pos_x = a * 12 + b * 6
                pos_y = a * 0 + b * 10
            elif net == 'sql':
                pos_x = a * 12
                pos_y = b * 12
            draw.ellipse((pos_x,pos_y,pos_x+10,pos_y+10), fill=color[int(fills[a,b])], outline=color[int(fills[a,b])])
    del draw
    img.save('Frame%04d' % (sim*frames/runs) + '.png',"PNG")
    # img.show() # open image in default viewer

def print_levels():
    """Prints the final board seperatly for each fill level"""
    print('Printing final result for each fill level...') # give a status update in the console
    for n in range(0,wall_number+1):
        img   = Image.new('RGB',(width,height),color=0)
        draw = ImageDraw.Draw(img)

        menlo_normal     = ImageFont.truetype("../fonts/Menlo.ttf",30)
        menlo_italic     = ImageFont.truetype("../fonts/MenloItalic.ttf",30)
        menlo_bold       = ImageFont.truetype("../fonts/MenloBold.ttf",30)
        menlo_bolditalic = ImageFont.truetype("../fonts/MenloBoldItalic.ttf",30)
        white = 255,255,255
        offset = 0

        if model == 'lennard_jones': draw.text((width-460,20),"Lennard Jones Model",white,font=menlo_italic)
        elif model == 'exponential': draw.text((width-460,20),"Exponential Model",white,font=menlo_italic)
        elif model == 'squared': draw.text((width-460,20),"Squared Model",white,font=menlo_italic)
        draw.text((width-460,75),"%s x %s Pores" % (size[0],size[1]),white,font=menlo_normal)
        if annealing != 'static':
            draw.text((width-460,110),"With simulated annealing",white,font=menlo_normal)
            if annealing == 'dynamic': draw.text((width-460,145),"Dynamic",white,font=menlo_italic)
            elif annealing == 'linear': draw.text((width-460,145),"Linear",white,font=menlo_italic)
            offset = 35
        else: draw.text((width-460,110),"W/out simulated annealing",white,font=menlo_normal)
        draw.text((width-460,165+offset),"Simulation runs: %s" % (add_suffix(sim)),white,font=menlo_normal)
        draw.text((width-460,height-110-wall_number*35),"Fill levels:",white,font=menlo_italic)
        for i in range(0,wall_number+1):
            if i == n:
                draw.rectangle((width-440,height-55-(wall_number-i)*35,width-350,height-20-(wall_number-i)*35),fill=color[i], outline=color[i])
                draw.text((width-340,height-55-(wall_number-i)*35),"%s" % (i),white,font=menlo_bold)
            else:
                draw.rectangle((width-460,height-55-(wall_number-i)*35,width-370,height-20-(wall_number-i)*35),fill=color[i], outline=color[i])
                draw.text((width-360,height-55-(wall_number-i)*35),"%s" % (i),white,font=menlo_normal)

            for a, b in ((a,b) for a in range(0,size[0]-1) for b in range(0,size[1]-1)):
                if net == 'hxl':
                    pos_x = a * 12 + b * 6
                    pos_y = a * 0 + b * 10
                elif net == 'sql':
                    pos_x = a * 12
                    pos_y = b * 12
                if fills[a,b] == n: draw.ellipse((pos_x,pos_y,pos_x+10,pos_y+10), fill=color[n], outline=color[n])
        del draw
        img.save('FillLevel%s' % (n) + '.png',"PNG")
        # img.show() # Open image in default viewer
        sys.stdout.write('\r')
        sys.stdout.write("[%-50s] %d%%" % ('='*int(n*50/wall_number), int(2*n*50/wall_number)))
        sys.stdout.flush()
    print('') # include a line break after the progress bar
    print('Done!')  # give a status update in the console


def print_array():
    """Print the current pore fill array as a CSV file (a values in first row, b values in first column)"""
    df = pd.DataFrame(fills)
    df.to_csv('./Array%04d.csv' % (int(sim*frames/runs)))


def demon():
    """Select a random pore and wall and transition to new state (i.e. flipped wall) according to acceptance probability function"""
    index_list = get_random_transition()
    if not (index_list[4] >= size[0] or index_list[5] >= size[1]): # make sure that no pores outside of the boundary are affected
        e_i = initial_energy(index_list)
        e_f = final_energy(index_list)
        if acceptance_probability(e_i,e_f): execute_trans(index_list) # make sure the acceptance probability function is true


def acceptance_probability(e_i,e_f): # acceptance probablity function P(dE)
    """Calculate acceptance probability from initial and final energy states and return boolean value accordingly"""
    if annealing == 'simulated_annealing': # check if simulated annealing is desired
        if e_f <= e_i: # if the final energy is lower, proceed with transition immediately, thus P(dE) = 1
            operations[0] += 1 # add 1 to the counter of downhill transitions
            return True
        elif bool(np.exp(-1 * (e_f - e_i) / temp) >= random.random()): # if the final energy is higher, proceed with transition according to probability function P(dE) = exp(-dE / temperature)
            operations[1] += 1 # add 1 to the counter of uphill transitions
            return True
        else:
            operations[2] += 1 # add 1 to the counter of no transitions
            return False

    # elif annealing == 'fixed_temp' or annealing == 'linear_acc': return bool(random.random() >= acceptance) # ---remove eventually


def lower_temperature(): # adjust the temperature
    """Start with the predefined temperature and drop it to zero in 20 steps over 4/5th of the length of the simulation"""
    global temp # use global value for temperature
    if sim >= (runs/25) and (sim)%(runs/25) == 0: # is the simulation run number divisible by 25 (and have at least a 1/25th of simulations been excecuted)?
        temp -= temp_i/20
        if temp <= 0: temp = 0.001 # avoid negative values

def run_sim():
    """Evoke the demon and simulated annealing functions for the number of chosen runs and regularly print images"""
    frame_rate = runs/frames # calculate frame rate from total simulation runs and frames
    print('Running simulation...')  # give a status update in the console
    with open("_parameters.txt","w") as file: # save a TXT file containing a list of the simulation parameters
        file.write(f"net = {net}\ninit_grade = {init_grade}\nmodel = {model}\nannealing = {annealing}\nsize = {size}\nruns = {runs}\nframes = {frames}\ntemp = {temp_i}\nlevels = {levels}\ncolored = {colored}\nvideo = {video}")
    shutil.copy(__file__, "_current_script_version.py") # save a backup of the executed PY script

    global sim # use global variables
    global operations
    global operations_list
    for sim in range(0,runs+1): #execute the given number of simulations
        demon() # evoke the demon
        if annealing != 'fixed_temp': lower_temperature() # lower the temperature if appropriate
        if sim%frame_rate == 0: # actions that are performed once per frame
            print_image()
            # print_array()

            sys.stdout.write('\r') # print a progress bar
            sys.stdout.write("[%-50s] %d%%" % ('='*int(sim*50/runs), int(2*sim*50/runs)))
            sys.stdout.flush()

            operations_list[int(sim*frames/runs),0] = int(sim*frames/runs) # append the list of operations with frame number, ...
            operations_list[int(sim*frames/runs),1] = operations[0] # ... number of downhill transitions, ...
            operations_list[int(sim*frames/runs),2] = operations[1] # ... number of uphill transitions, ...
            operations_list[int(sim*frames/runs),3] = operations[2] # ... and number of no transitions
            operations = [0,0,0] # reset list of operations for the next frame

    print('') # include a line break after the progress bar
    if run_check(): print('Simulation finished w/out error!') # give a status update in the console
    df = pd.DataFrame(operations_list,columns=['Frame','Downhill Transitions','Uphill Transitions','None'])
    df.to_csv('./_operations.csv',index=False) # save table of transitions in a CSV file
    if levels: print_levels() # print final lattice for each individual fill value
    if video: os.system(f"ffmpeg -r 25 -f image2 -i Frame%04d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p -s {width}x{height} animation.mp4")

def calculate_all_fills():
    """(Re-)Calculate all fill values"""
    for a, b in ((a,b) for a in range(0,size[0]) for b in range(0,size[1])):
        fills[a,b] = fill(a,b)

def run_check():
    """Check if all walls are defined as inside by one and outside by the neighboring pore and give a statement to the result"""
    for a, b, n in ((a,b,n) for a in range(0,size[0]-1) for b in range(0,size[1]-1) for n in range(0,wall_number)):
        if walls[a,b,n] + walls[a+vec_walls[n,0],b+vec_walls[n,1],int((n+(wall_number/2))%wall_number)] == 0: # check if both instances of the wall agree on the flip state
            return True
        else: 
            sys.exit("Oops! Flip states didn't match for {}|{} {} and {}|{} {}.".format(a,b,walls[a,b,1],a+vec_walls[n,0],b+vec_walls[n,1],walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+(wall_number/2))%wall_number]))

# ================================================================================

def initiate_uniform_lattice():
    """Create a lattice of a given size and populate it with pores and walls where all moieties uniformly point up and/or right"""
    for a, b in ((a,b) for a in range(0,size[0]) for b in range(0,size[1])): # cycle through all points on the lattice
        if   net == 'hxl': walls[a,b] = [1,1,1,-1,-1,-1] # assign wall flip states
        elif net == 'sql': walls[a,b] = [1,1,-1,-1]
        fills[a,b] = fill(a,b) # calculate and set fill value

def initiate_random_lattice(n):
    """Initiate a random lattice with n random transitions"""

    initiate_uniform_lattice()
    print('Initialising...') # give a status update in the console

    for i in range(0,n+1):
        index_list = get_random_transition()
        if not (index_list[4] >= size[0] or index_list[5] >= size[1]):
            execute_trans(index_list)
        sys.stdout.write('\r') # print progress bar
        sys.stdout.write("[%-50s] %d%%" % ('='*int(i*50/n), int(2*i*50/n)))
        sys.stdout.flush()

    print('')
    calculate_all_fills()
    if run_check(): print('Random lattice generated successfully!') # give a status update in the console


def execute_trans(index_list): # excecute transition to new state
    """Flip wall n towards pore (a|b)"""

    n,a,b,m,c,d = index_list # split index list back into individual variables
    walls[a,b,n] = 1 # flip towards
    walls[c,d,m] = -1 # flip away from
    fills[a,b] = fill(a,b)
    fills[c,d] = fill(c,d)


def get_random_transition():
    """Generate the index list [n,a,b,m,c,d] for a random transition"""

    if net == 'hxl': # choose random wall ...
        n = random.choice([0,1,2,3,4,5])
        m = (n+3)%6
    elif net == 'sql':
        n = random.choice([0,1,2,3])
        m = (n+2)%4

    xy  = random_xy() # ... and pore
    a,b = xy[0],xy[1]
    c,d = a+vec_walls[n,0],b+vec_walls[n,1]

    return [n,a,b,m,c,d]

# ================================================================================

initiate_random_lattice(init_grade)
run_sim()

# if sys.platform == 'win32' or sys.platform == 'win64': os.system("")
# elif sys.platform == 'darwin' or sys.platform == 'linux' or sys.platform == 'linux2': os.system("")

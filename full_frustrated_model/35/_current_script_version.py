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

def calc_fill(a,b):
    """Calculates the fill value of a given pore (a,b)"""

    fill = 0
    for i in walls[a,b]:
        if i == 1: fill += 1
    return fill


def get_rnd_xy():
    """Return random coordinates on the lattice"""

    x = int(round(random.random()*(size[0]-1),0))
    y = int(round(random.random()*(size[1]-1),0))
    return [x,y]

def get_int_energy(transition):
    """DESCRIPTION"""

    n,a,b,m,c,d = transition
    return get_energy(calc_fill(a,b)) + get_energy(calc_fill(c,d))


def get_fin_energy(transition):
    """DESCRIPTION"""

    n,a,b,m,c,d = transition
    if calc_fill(a,b) == 6 or calc_fill(c,d) == 0: return get_energy(calc_fill(a,b)) + get_energy(calc_fill(c,d))
    else: return get_energy(calc_fill(a,b)+1) + get_energy(calc_fill(c,d)-1)


def get_energy(fill):
    """
    Return the energy value of a pore with respect to fill level based on different models (a.u.)
    """

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

def add_sfx(n): # add suffix
    """Convert integer to more readable 10 k, 1 m, etc."""
    suffix = ['',' k',' m',' b']
    n = float(n)
    millidx = max(0,min(len(suffix)-1,int(np.floor(0 if n == 0 else np.log10(abs(n))/3))))
    if millidx == 2: return '{:.3f}{}'.format(n / 10**(3 * millidx), suffix[millidx]) # include three decimals for values over 1 m
    else: return '{:.0f}{}'.format(n / 10**(3 * millidx), suffix[millidx])


def print_image():
    """Prints a given board as an image consisting of monocrome circles"""
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
    draw.text((width-460,165+offset),"Temperature:     %s" % (abs(round(temp,2))),white,font=menlo_normal)
    draw.text((width-460,200+offset),"Simulation runs: %s" % (add_sfx(sim)),white,font=menlo_normal)
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
    # img.show() # Open image in default viewer

    # Frames were converted to video using ffmpeg and the following commands:
    # ffmpeg -r 25 -f image2 -i Frame%04d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p -s 2108x740 animation.mp4


def print_levels():
    """Prints a given board seperatly for each fill level"""
    print('Printing final result for each fill level...')
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
        draw.text((width-460,165+offset),"Simulation runs: %s" % (add_sfx(sim)),white,font=menlo_normal)
        draw.text((width-460,height-110-wall_number*35),"Fill levels:",white,font=menlo_italic)
        for i in range(0,wall_number+1):
            if i == n:
                draw.rectangle((width-440,height-55-(wall_number-i)*35,width-350,height-20-(wall_number-i)*35),fill=color[i], outline=color[i])
                draw.text((width-340,height-55-(wall_number-i)*35),"%s" % (i),white,font=menlo_bold)
            else:
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
                if fills[a,b] == n: draw.ellipse((pos_x,pos_y,pos_x+10,pos_y+10), fill=color[n], outline=color[n])
        del draw
        img.save('FillLevel%s' % (n) + '.png',"PNG")
        # img.show() # Open image in default viewer
        sys.stdout.write('\r')
        sys.stdout.write("[%-50s] %d%%" % ('='*int(n*50/wall_number), int(2*n*50/wall_number)))
        sys.stdout.flush()
    print('')
    print('Done!')


def print_array():
    """Print the current pore fill array as CSV file (a in first row, b in first column)"""
    df = pd.DataFrame(fills)
    df.to_csv('./Array%04d.csv' % (int(sim*frames/runs)))


def demon():
    """Select a random pore and wall and transition to new state (i.e. flipped wall) according to acceptance probability function"""

    transition = get_rnd_trans()
    if not (transition[4] >= size[0] or transition[5] >= size[1]): # make sure that no pores outside of the boundary are affected
        e_i = get_int_energy(transition)
        e_f = get_fin_energy(transition)
        if acc_prob_fn(e_i,e_f): exec_trans(transition) # make sure the acceptance probability function is true


def acc_prob_fn(e_i,e_f): # acceptance probablity function
    """Calculate acceptance probability from initial and final energy states and return boolean value accordingly"""

    if annealing == 'simulated_annealing':
        if e_f <= e_i:
            operations[0] += 1
            return True
        elif bool(np.exp(-1 * (e_f - e_i) / temp) >= random.random()):
            operations[1] += 1
            return True
        else: 
            operations[2] += 1
            return False

    # elif annealing == 'fixed_acc' or annealing == 'linear_acc': return bool(random.random() >= acceptance) # ---remove eventually


def lwr_temp(): # adjust the temperature
    """Start with the predefined temperature and drop it to zero in 20 steps over the length of the simulation"""
    global temp
    if sim >= (runs/25) and (sim)%(runs/25) == 0:
            temp -= temp_i/20
            if temp <= 0: temp = 0.001

def run_sim():
    """Evoke the demon and simulated annealing functions for the number of chosen runs and regularly print images"""
    frame_rate = runs/frames # calculate frame rate from total simulation runs and frames
    print('Running simulation...')
    with open("_parameters.txt","w") as file:
        file.write(f"net = {net}\ninit_grade = {init_grade}\nmodel = {model}\nannealing = {annealing}\nsize = {size}\nruns = {runs}\nframes = {frames}\ntemp = {temp_i}\nlevels = {levels}\ncolored = {colored}\nvideo = {video}")
    shutil.copy(__file__, "_current_script_version.py") # save a backup of the executed PY script

    global sim
    global operations
    global operations_list
    for sim in range(0,runs+1):
        demon()
        if annealing != 'fixed_acc': lwr_temp()
        if sim%frame_rate == 0:
            print_image()
            # print_array()

            sys.stdout.write('\r')
            sys.stdout.write("[%-50s] %d%%" % ('='*int(sim*50/runs), int(2*sim*50/runs)))
            sys.stdout.flush()

            operations_list[int(sim*frames/runs),0] = int(sim*frames/runs)
            operations_list[int(sim*frames/runs),1] = operations[0]
            operations_list[int(sim*frames/runs),2] = operations[1]
            operations_list[int(sim*frames/runs),3] = operations[2]
            operations = [0,0,0]

    print('')
    if check_all(): print('Simulation finished w/out error!')
    df = pd.DataFrame(operations_list,columns=['Frame','Downhill Transitions','Uphill Transitions','None'])
    df.to_csv('./_operations.csv',index=False)
    if levels: print_levels()
    if video: os.system(f"ffmpeg -r 25 -f image2 -i Frame%04d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p -s {width}x{height} animation.mp4")

def calc_all_fills():
    """(Re-)Calculate all fill values"""
    for a in range(0,size[0]):
        for b in range(0,size[1]):
            fills[a,b] = calc_fill(a,b)

def check_all():
    """Check if all walls are defined as inside by one and outside by the neighboring pore and give a statement to the result"""
    for a in range(0,size[0]-1):
        for b in range(0,size[1]-1):
            if net == 'hxl':
                for n in range(-1,6):
                    if walls[a,b,n] + walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+3)%6] != 0: # check if both instances of the wall agree on the flip state
                        sys.exit("Oops! Flip states didn't match for {}|{} {} and {}|{} {}.".format(a,b,walls[a,b,1],a+vec_walls[n,0],b+vec_walls[n,1],walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+3)%6]))
            elif net == 'sql':
                for n in range(-1,4):
                    if walls[a,b,n] + walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+2)%4] != 0: # check if both instances of the wall agree on the flip state
                        sys.exit("Oops! Flip states didn't match for {}|{} {} and {}|{} {}.".format(a,b,walls[a,b,1],a+vec_walls[n,0],b+vec_walls[n,1],walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+2)%4]))
    return True

# ================================================================================

def init_unif():
    """Create a lattice of a given size and populate it with pores and walls where all moieties uniformly point up and/or right"""
    for x in range(0,size[0]): # create all pores and assign wall flip states
        for y in range(0,size[1]):
            fills[x,y] = 0
            if   net == 'hxl': walls[x,y] = [1,1,1,-1,-1,-1]
            elif net == 'sql': walls[x,y] = [1,1,-1,-1]

    for a in range(0,size[0]): # calculate and set all fill values
        for b in range(0,size[1]):
            fills[a,b] = calc_fill(a,b)


def init_rnd_lattice(n):
    """Initiate a random lattice with n random transitions"""

    init_unif()
    print('Initialising...')

    for i in range(0,n+1):
        transition = get_rnd_trans()
        if not (transition[4] >= size[0] or transition[5] >= size[1]):
            exec_trans(transition)
        sys.stdout.write('\r') # print progress bar
        sys.stdout.write("[%-50s] %d%%" % ('='*int(i*50/n), int(2*i*50/n)))
        sys.stdout.flush()

    print('')
    calc_all_fills()
    if check_all(): print('Random lattice generated successfully!')


def exec_trans(transition): # excecute transition to new state
    """Flip wall n towards pore (a|b)"""

    n,a,b,m,c,d = transition
    walls[a,b,n] = 1 # flip towards
    walls[c,d,m] = -1 # flip away from
    fills[a,b] = calc_fill(a,b)
    fills[c,d] = calc_fill(c,d)


def get_rnd_trans():
    """Generate n,a,b,m,c,d for a random wall on the lattice"""

    if net == 'hxl': # choose random wall ...
        n = random.choice([0,1,2,3,4,5])
        m = (n+3)%6
    elif net == 'sql':
        n = random.choice([0,1,2,3])
        m = (n+2)%4

    xy  = get_rnd_xy() # ... and pore
    a,b = xy[0],xy[1]
    c,d = a+vec_walls[n,0],b+vec_walls[n,1]

    return [n,a,b,m,c,d]

# ================================================================================

init_rnd_lattice(init_grade)
run_sim()

# if sys.platform == 'win32' or sys.platform == 'win64': os.system("")
# elif sys.platform == 'darwin' or sys.platform == 'linux' or sys.platform == 'linux2': os.system("")

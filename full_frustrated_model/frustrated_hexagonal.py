import sys
import random
import numpy as np
import scipy.misc as smp
from PIL import Image,ImageDraw

'''Let's define some global variables and arrays'''
global vec_walls
vec_walls = np.array([[1,-1],[1,0],[0,1],[-1,1],[-1,0],[0,-1]])

global mode
global comparison
global error_probability
global size_x,size_y
global sim_runs
global frames
global epsilon
global width
global height
global img
mode                = 'hexagonal'
# comparison          = 'lennard_jones'
# comparison          = 'reciprocal'
comparison          = 'exponential'
error_probability   = 0.10
size_x,size_y       = 200,150
sim_runs            = 1000000
frames              = 200
epsilon             = 1.0
width               = size_x * 12 + size_y * 6
height              = size_y * 10
img                 = Image.new('RGB',(width,height),color=0)

pores = np.ones((size_x,size_y,1), dtype=np.int16)
walls = np.ones((size_x,size_y,6), dtype=np.int16)

# =======================================================================

def calculate_fill(a,b):
    """Calculates the fill value of a given pore (a,b)"""
    fill = 0
    for i in walls[a,b]:
        if i == 1: fill += 1
    return fill

def set_fill(a,b,new_fill):
    """Set the fill of a pore to a new value"""
    pores[a,b] = new_fill

def get_random_xy():
    """Returns random coordinates on the board"""
    x = int(round(random.random()*(size_x-1),0))
    y = int(round(random.random()*(size_y-1),0))
    return [x,y]

def get_frustration(a,b):
    """
    Returns the 'frustration' (1-happiness) of a pore with respect to fill level based on the Lennard Jones (12,6) potential:
    V(r) = epsilon * (r_m/r)^6 * [(r_m/r)^6 - 2],
    with the potential V, the potential well epsilon > 0, the radius r, V(sigma) = 0 and the minimum V(r_m) with r_m ~= 1.12 * sigma.
    """
    frustration = 0
    r = int(pores[a,b])
    sigma = float(6)
    # rm = 5.4098 # empirical value for which frustration(6)~=0 from positive values
    # rm = 5.46 # empirical value for which frustration(6) = 0.25
    rm = 5.52 # empirical value for which frustration(6) = 0.47

    if comparison == 'lennard_jones':
        frustration = -(epsilon*(rm/(r-(2*rm)))**6 * ((rm/(r-(2*rm)))**6 - 2))
    # frustration(r) for r = 0,1,2,3,4,5,6
    # i = 0: 0.03101
    # i = 1: 0.05514
    # i = 2: 0.10369
    # i = 3: 0.20726
    # i = 4: 0.43629
    # i = 5: 0.87415
    # i = 6: 5.46
    elif comparison == 'reciprocal':
        frustration = 1/(r-7)
    elif comparison == 'exponential':
        frustration = np.exp(r)
    return float(frustration)

def get_sigmoidal_value(x,k):
    out = (x - x * k)/(k - abs(x) * 2 * k + 1)
    return out

# ================================================================================

def print_image(name):
    """Prints a given board as an image consisting of monocrome circles"""
    draw = ImageDraw.Draw(img)
    for b in range(0,size_y-1):
        for a in range(0,size_x-1):
            pos_x = a * 12 + b * 6
            pos_y = a * 0 + b * 10
            if pores[a,b] == 0: color = (60,60,60)
            elif pores[a,b] == 1: color = (60,60,60)
            elif pores[a,b] == 2: color = (64,64,64)
            elif pores[a,b] == 3: color = (70,70,70)
            elif pores[a,b] == 4: color = (86,86,86)
            elif pores[a,b] == 5: color = (131,131,131)
            elif pores[a,b] == 6: color = (255,255,255)
            else: color = (255,0,0)
            draw.ellipse((pos_x,pos_y,pos_x+10,pos_y+10), fill=color, outline=color)
    del draw
    img.save(name + '.png',"PNG")
    # img.show() # View in default viewer
    # convert to video with:
    # ffmpeg -r 25 -f image2 -s 3300x1500 -i Frame%04d.png -vcodec libx264 -crf 25  -pix_fmt yuv420p 200x150exponential0.1error1000000rns.mp4

def demon(sim):
    """
    Select a random pore and wall and compare fill values.
    The least happy pore will get the flip.
    """
    n   = random.choice([0,1,2,3,4,5])
    m   = (n+3)%6
    xy  = get_random_xy()
    a,b = xy[0],xy[1]
    c,d = a+vec_walls[n,0],b+vec_walls[n,1]
    if not (c >= size_x or d >= size_y): # make sure that no pores outside of the boundary are affected
        if comparison == 'lennard_jones': # follows a Lennard Jones function, where 5 wins every time and 6 wins over 1,2,3,4 and bigger numbers win over smaller ones for 1,2,3,4
            compare_frustration_and_flip(n,a,b,m,c,d)
        elif (comparison == 'reciprocal') or (comparison == 'exponential'):
            compare_frustration_and_flip(n,a,b,m,c,d)
            # if sim%3 == 0:
            #     flip_random()

def compare_frustration_and_flip(n,a,b,m,c,d):
    if get_frustration(a,b) >= get_frustration(c,d):
        flip_wall_towards(n,a,b,m,c,d)
    elif get_frustration(a,b) == get_frustration(c,d): # if both are the same, fate choses
        if random.random >= 0.5: flip_wall_towards(n,a,b,m,c,d)
        else: flip_wall_towards(m,c,d,n,a,b)
    else: flip_wall_towards(m,c,d,n,a,b)

def simulate():
    frame_length = sim_runs/frames
    for sim in range(0,sim_runs+1):
        demon(sim)
        simulated_annealing(sim)
        if sim%frame_length == 0: print_image('hex%sx%s%s%serror%srns' % (size_x,size_y,comparison,error_probability,sim))

def recalculate_fills():
    """Recalculates all fill values"""
    for a in range(0,size_x):
        for b in range(0,size_y):
            set_fill(a,b,calculate_fill(a,b))

def check_all_walls():
    for a in range(0,size_x-1):
        for b in range(0,size_y-1):
            for n in range(-1,6):
                if walls[a,b,n] + walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+3)%6] != 0: # check if both instances of the wall agree on the flip state
                    sys.exit("Oops! Flip states didn't match for {}|{} {} and {}|{} {}.".format(a,b,walls[a,b,1],a+vec_walls[n,0],b+vec_walls[n,1],walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+3)%6]))
    else: print ('All flip states are looking good!')

# ================================================================================

def initiate_all_right():
    """Creates a board of a given size and populates it with pores and walls, whose moieties all point right."""
    for x in range(0,size_x):
        for y in range(0,size_y):
            pores[x,y] = [0]
            walls[x,y] = [1,1,1,-1,-1,-1]
    for a in range(0,size_x): # calculate and set all fill values
        for b in range(0,size_y):
            set_fill(a,b,calculate_fill(a,b))

def initiate_random(n):
    """Initiate a random board"""
    initiate_all_right()
    for i in range(0,n):
        flip_random()
    recalculate_fills()
    print_image('hex%sx%srndminit%s' % (size_x,size_y,n))

def flip_wall(n,a,b):
    """Flips both instances of a wall n for a given pore (a,b) and (n+3)%6 for the adjacent pore"""
    m   = (n+3)%6
    c,d = a+vec_walls[n,0],b+vec_walls[n,1]
    if not (c >= size_x or d >= size_y): # make sure that no pores outside of the boundary are affected
        walls[a,b,n] = -1 * walls[a,b,n] # flip first wall
        walls[c,d,m] = -1 * walls[c,d,m]
        set_fill(a,b,calculate_fill(a,b))
        set_fill(c,d,calculate_fill(c,d))

def switch_pores(n,a,b,m,c,d):
    '''Switches two pores and respective walls with each other'''
    switched = [m,c,d,n,a,b]
    return switched

def flip_wall_towards(n,a,b,m,c,d):
    """Flips a wall n towards a given pore (a,b) and away for (n+3)%6 of the adjacent pore"""
    if random.random() <= error_probability:
        sw = switch_pores(n,a,b,m,c,d)
        n,a,b,m,c,d = sw[0],sw[1],sw[2],sw[3],sw[4],sw[5]
    walls[a,b,n] = 1 # flip towards
    walls[c,d,m] = -1 # flip away from
    set_fill(a,b,calculate_fill(a,b))
    set_fill(c,d,calculate_fill(c,d))

def flip_random():
    """Flip a random wall on the board"""
    n = random.choice([0,1,2,3,4,5])
    xy = get_random_xy()
    a,b = xy[0],xy[1]
    flip_wall(n,xy[0],xy[1])
    # print ("Wall {} at {} was flipped randomly.".format(n,xy))

# ================================================================================

initiate_random(500000)
check_all_walls()
simulate()
check_all_walls()

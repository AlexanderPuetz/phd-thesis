import sys
import random
import numpy as np
from PIL import Image,ImageDraw

'''Let's define some global variables and arrays'''
vec_walls = np.array([[0,-1],[1,0],[0,1],[-1,0]])

mode                = 'tetragonal'
comparison          = 'lennard_jones'
## comparison          = 'reciprocal'
# comparison          = 'exponential'
simulated_annealing = 1
error_probability   = 0.20
initial_error_prop  = error_probability
size_x,size_y       = 10,10
sim_runs            = 100000
frames              = 10
width               = (size_x-1) * 12
height              = (size_y-1) * 12
img                 = Image.new('RGB',(width,height),color=0)

pores = np.ones((size_x,size_y,1), dtype=np.int16)
walls = np.ones((size_x,size_y,4), dtype=np.int16)

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
    epsilon = 1
    frustration = 0
    r = int(pores[a,b])
    sigma = float(4)

    rm = 3.68 # empirical value for which frustration(4) = 0.47

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
        frustration = 1/(r-5)
    elif comparison == 'exponential':
        frustration = np.exp(r)
    return float(frustration)

# def get_sigmoidal_value(x,k):
#     out = (x - x * k)/(k - abs(x) * 2 * k + 1)
#     return out

# ================================================================================

def print_image(name):
    """Prints a given board as an image consisting of monocrome circles"""
    draw = ImageDraw.Draw(img)
    for b in range(0,size_y-1):
        for a in range(0,size_x-1):
            pos_x = a * 12
            pos_y = b * 12
            if   pores[a,b] == 0: color = (64,64,64)                # ---------- make rainbow color scheme (origin, freddies last stacking paper)
            elif pores[a,b] == 1: color = (70,70,70)
            elif pores[a,b] == 2: color = (86,86,86)
            elif pores[a,b] == 3: color = (131,131,131)
            elif pores[a,b] == 4: color = (255,255,255)
            else: color = (255,0,0)
            draw.ellipse((pos_x,pos_y,pos_x+10,pos_y+10), fill=color, outline=color)
    del draw
    img.save(name + '.png',"PNG")
    # img.show() # View in default viewer

    # Frames were converted to video with:
    # ffmpeg -r 25 -f image2 -s 3300x1500 -i Frame%04d.png -vcodec libx264 -crf 25  -pix_fmt yuv420p 200x150exponential0.1error1000000rns.mp4

def demon(sim):
    """Select a random pore and wall and compare fill values. The least happy pore will get the flip."""
    n   = random.choice([0,1,2,3])
    m   = (n+2)%4
    xy  = get_random_xy()
    a,b = xy[0],xy[1]
    c,d = a+vec_walls[n,0],b+vec_walls[n,1]
    if not (c >= size_x or d >= size_y): # make sure that no pores outside of the boundary are affected
        if comparison == 'lennard_jones': # follows a Lennard Jones function, where 3 wins every time and 4 wins over 1,2 and 2 wins over 1
            compare_frustration_and_flip(n,a,b,m,c,d)
        elif (comparison == 'reciprocal') or (comparison == 'exponential'):
            compare_frustration_and_flip(n,a,b,m,c,d)
            # if sim%3 == 0:
            #     flip_random()

def simulated_annealing(sim):
    """Starts with the predefined error_probability and drops it to zero in 20 steps over the length of the simulation"""
    if sim >= (sim_runs/20):
        if (sim)%(sim_runs/20) == 0:
            global error_probability
            error_probability -= initial_error_prop/20

def compare_frustration_and_flip(n,a,b,m,c,d):
    """COULD ACTUALLY BE BACK IN demon(sim), SINCE THERE IS NO DIFFERENCE BETWEEN THE COMPARISON MODES"""
    if get_frustration(a,b) >= get_frustration(c,d):
        flip_wall_towards(n,a,b,m,c,d)
    elif get_frustration(a,b) == get_frustration(c,d): # if both are the same, fate choses
        if random.random >= 0.5: flip_wall_towards(n,a,b,m,c,d)
        else: flip_wall_towards(m,c,d,n,a,b)
    else: flip_wall_towards(m,c,d,n,a,b)

def simulate():
    """Evokes the demon and simulated annealing functions for the number of chosen runs and regularly prints images"""
    frame_length = sim_runs/frames
    for sim in range(0,sim_runs+1):
        demon(sim)
        simulated_annealing(sim)
        if sim%frame_length == 0: print_image('tet%sx%s%ssimann%srns%serrors' % (size_x,size_y,comparison,sim,abs(round(error_probability,2))))

def recalculate_fills():
    """Recalculates all fill values"""
    for a in range(0,size_x):
        for b in range(0,size_y):
            set_fill(a,b,calculate_fill(a,b))

def check_all_walls():
    """Checks if all walls are defined as inside by one and outside by the neighboring pore and gives a statement to the result"""
    for a in range(0,size_x-1):
        for b in range(0,size_y-1):
            for n in range(-1,4):
                if walls[a,b,n] + walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+2)%4] != 0: # check if both instances of the wall agree on the flip state
                    sys.exit("Oops! Flip states didn't match for {}|{} {} and {}|{} {}.".format(a,b,walls[a,b,1],a+vec_walls[n,0],b+vec_walls[n,1],walls[a+vec_walls[n,0],b+vec_walls[n,1],(n+2)%4]))
    else: print ('All flip states are looking good!')

# ================================================================================

def initiate_all_upright():
    """Creates a board of a given size and populates it with pores and walls, whose moieties all point right."""
    for x in range(0,size_x):
        for y in range(0,size_y):
            pores[x,y] = [0]
            walls[x,y] = [1,1,-1,-1]
    for a in range(0,size_x): # calculate and set all fill values
        for b in range(0,size_y):
            set_fill(a,b,calculate_fill(a,b))

def initiate_random(n):
    """Initiate a random board"""
    initiate_all_upright()
    for i in range(0,n):
        flip_random()
    recalculate_fills()
    print_image('tet%sx%srndminit%s' % (size_x,size_y,n))

def flip_wall(n,a,b):
    """Flips both instances of a wall n for a given pore (a,b) and (n+2)%4 for the adjacent pore"""
    m   = (n+2)%4
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
    n = random.choice([0,1,2,3])
    xy = get_random_xy()
    a,b = xy[0],xy[1]
    flip_wall(n,xy[0],xy[1])

# ================================================================================

# initiate_random(500000)
# check_all_walls()
# comparison = 'lennard_jones'
# simulate()
# check_all_walls()
initiate_random(500000)
check_all_walls()
simulate()
check_all_walls()

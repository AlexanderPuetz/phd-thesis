import numpy as np

dimensions = [200,60]
cells = np.zeros(dimensions)
dimensions_as_seed = False


def read_input(seed):
	global dimensions
	global cells

	with open(seed) as seed_txt:
		seed = seed_txt.read()
	rows = seed.split("\n")
	if dimensions_as_seed:
		dimensions[0] = len(rows[0])
		dimensions[1] = len(rows)
		cells = np.zeros(dimensions)
		shift_x,shift_y = 0,0		
	else: 
		shift_x = int((dimensions[0]-len(rows[0]))/2)
		shift_y = int((dimensions[1]-len(rows))/2)
		print(shift_x,shift_y)
	for x in range (0,dimensions[0]-shift_x): #expand read range for negative shift (seed bigger then dimension), 
		for y in range (0,dimensions[1]-shift_y): #reduce read range for positive shift (dimension bigger)
			try: 
				if rows[y][x] == 'o': cells[x+shift_x][y+shift_y] = 1
			except: pass
	return cells

def generate_output():
	global dimensions
	global cells
	output = ""
	for y in range (0,dimensions[1]):
		row = ""
		for x in range (0,dimensions[0]):
			if cells[x][y] == 1: row = row + ("o")
			else: row = row + (".")
		row = row + ("\n")
		output = output + row
	return output

def get_neighbors(x,y):
	neighbors = 0
	for rel_x in range (-1,2):
		for rel_y in range (-1,2):
			if (rel_x == 0 and rel_y == 0) or x+rel_x < 0 or y+rel_y < 0: pass #skip check if cell itself or either cell coordinate is -1
			else: 
				try: 
					if cells[x+rel_x][y+rel_y] == 1: neighbors = neighbors+1
				except: pass
	return neighbors

def next_generation():
	global dimensions
	global cells
	cells_new = np.zeros(dimensions)
	for y in range (0,dimensions[1]):
		for x in range (0,dimensions[0]):
			neighbors = get_neighbors(x,y)
			if cells[x][y] == 1:
				if neighbors == 2 or neighbors == 3: cells_new[x][y] = 1 #rule 2
				else: cells_new[x][y] = 0 #rules 1, 3
			else:
				if neighbors == 3: cells_new[x][y] = 1 #rule 4
	cells = cells_new

def main(seed):
	read_input(seed)
	print(generate_output())

	for i in range (0,400):
		next_generation()
		print(generate_output())

main("./seed_acorn.txt")
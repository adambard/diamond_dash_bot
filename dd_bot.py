"""
A Diamond Dash bot.

Copyright (c) 2011 Adam Bard (adambard.com)

Licensed under the MIT License: http://www.opensource.org/licenses/mit-license
"""

import gtk
import numpy
import math
import png
import os
import time

current_side = True
diamond_present = False

# The screen index of the play area is stored, so
# no moving after the game starts.
TOP_LEFT_INDEX = None

DELAY = 0.7

# Color of each block at 10, 10
COLORS = (
		(158, 221, 255), # Diamond
		(247, 183, 0), #Yellow
		(1, 185, 1), # Green
		(186, 115, 255), # Purple
		(242, 0, 16), # Red
		(6, 104, 253)) # Blue

class NotDiamondDashException(Exception):
	pass

def crop_dd_screenshot(pixarray):
	"""
	If there is no stored index, load the reference .png,
	find it in the current screen, and get the coordinates.

	If the reference is not found, raise a
	NotDiamondDashException so we know we're not looking
	at a Diamond Dash screen

	If the index has already been stored, just slice the
	array to the right parameters.
	"""
	global TOP_LEFT_INDEX

	if not TOP_LEFT_INDEX:
        # Load it up
		ref_pixarray = read_png_to_pixarray('topleft_ref.png')
	
		ind = search_for_subarray(pixarray, ref_pixarray)

		if not ind:
			raise NotDiamondDashException("This isn't diamond dash.")


		ref_row, ref_col, _ = ref_pixarray.shape

		# Add the size of the reference
		row = ind[0] + ref_row
		col = ind[1] + ref_col

		TOP_LEFT_INDEX = (row, col)
	else:
		row, col = TOP_LEFT_INDEX

	# Diamond dash board runs 400x360 px.
	return pixarray[row:row + 360, col:col + 400], (row, col)


def search_for_subarray(A, A_sub):
	"""
	Search for A_sub in A

	>>> A = numpy.array([[1,2,3,4],[5,6,7,8]])
	>>> search_for_subarray(A, numpy.array([[2,3],[6,7]]))
	(0, 1)
	"""

	if len(A.shape) == 3:
		sub_rows, sub_cols, _ = A_sub.shape
		rows, cols, _ = A.shape
	elif len(A.shape) == 2:
		sub_rows, sub_cols = A_sub.shape
		rows, cols = A.shape

	for i in range(rows):
		for j in range(cols):
			if numpy.all(A[i][j] == A_sub[0][0]):
				if numpy.all(A[i:i+sub_rows, j:j+sub_cols] == A_sub):
					return (i, j)
	return None

def read_png_to_pixarray(filename):
	"""
	Read a .png image into an (x,y,3) full-color pixarray
	"""
	with open(filename, 'rb') as f:
		r = png.Reader(file=f)
		out = r.asDirect()

		pixarray = numpy.reshape(list(out[2]), (out[1], out[0], 3))

	return pixarray

def write_png_from_pixarray(filename, pixarray):
	"""
	Write a .png image from an (x, y, 3) fill-color pixarray
	"""

	rows = len(pixarray)
	cols = len(pixarray[0])

	with open(filename, 'wb') as f:
		w = png.Writer(cols, rows)
		img = numpy.around(pixarray).reshape(rows, cols*3)
		w.write(f, img)


def downsample_pixarray(pixarray, factor=40.):
	"""
	Get the nearest color index match from the COLORS tuple
	from every square.

	Diamond dash squares are 40x40.
	"""
	factor = float(factor)

	rows, cols, _ = pixarray.shape

	new_rows = int(math.ceil(rows / factor))
	new_cols = int(math.ceil(cols / factor))

	counts = numpy.zeros((new_rows, new_cols))
	out_pixarray = numpy.zeros((new_rows, new_cols, 3))

	# Downsample instead of averaging
	for i in range(new_rows):
		for j in range(new_cols):
            # Get a point from 10,10 in a 40px square, which should be the right color
			i_ind = int(i * factor + factor/4) 
			j_ind = int(j * factor + factor/4)

			pixel = pixarray[i_ind][j_ind]

			c = nearest_index_to_color(pixel)
			counts[i][j] = c

	return counts

def get_best_dd_point(countsarray):
	"""
	A wrapper for find_contiguous_regions with a 
	shortcut for diamonds.
	"""
	global diamond_present
	if 0 in countsarray:
# Only go every second time.
		if diamond_present:
			global DELAY
			DELAY = 2 # Double delay for meteor action
			rows, cols = numpy.where(countsarray == 0.)
			diamond_present = False
			return (rows[0], cols[0])
		diamond_present = True

	return find_contiguous_regions(countsarray)

def find_contiguous_regions(countsarray):
	"""
	Find the contiguous regions in countsarray using the modified
	flood count algorithm described in get_flood_count
	"""
	global current_side

	Q = countsarray.copy()
	points_checked = []
	rows, cols = Q.shape

	cols = cols / 2 - 1

	best_score = 0
	best_ind = -1
	best_point = (0, 0)

	for i in range(rows):
		for j in range(cols):
			if current_side:
				j = j + cols + 2

			if Q[i][j] >= 0:
				score = get_flood_count(Q, i, j, Q[i][j])
				if score > best_score:
					best_score = score
					best_ind = countsarray[i][j]
					best_point = (i, j)

	current_side = not current_side

	# Generate a nice little display
	print countsarray
	print "Best score: {0:d} ({1:d}, {2:d})".format(best_score, best_point[0], best_point[1])

	if best_score < 3:
		return find_contiguous_regions(countsarray)

	return best_point

def get_flood_count(Q, i, j, target, replacement=-1):
	"""
	A modified flood count algorithm.
	
	Makes some assumptions about the input, namely:

	1. Input array is small enough not to overflow the stack
	2. Input array is numeric, and
	3. Input array is wholly positive (or at least, has no -1's)
	
	>>> Q = numpy.array([[1,1,2,4], [1, 3, 5, 7]])
	>>> get_flood_count(Q, 0, 0, Q[0][0])
	3
	"""
	s = Q.shape
	if i < 0 or j < 0 or i >= s[0] or j >= s[1] or Q[i][j] != target:
		 return 0

	# Q[i][j] == target_ind
	Q[i][j] = replacement
	
	return 1 + (get_flood_count(Q, i+1, j, target, replacement) + 
			get_flood_count(Q, i, j+1, target, replacement) +
			get_flood_count(Q, i-1, j, target, replacement) +
			get_flood_count(Q, i, j-1, target, replacement))



def nearest_index_to_color(color_tuple):
	"Get the index in COLORS closest to color_tuple"
	distances = [color_distance(c, color_tuple) for c in COLORS]
	return distances.index(min(distances))

def normalize_color(color_tuple):
	"Get the color closest to color_tuple"
	return COLORS[nearest_index_to_color(color_tuple)]

def color_distance(c1, c2):
	"""Get the sum of squares of the difference between two colors"""
	return (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2

def take_screenshot():
	"""
	Use GTK to get a screengrab of the current screen.

	Returns an (x, y, 3) full-color pixel array
	"""
	w = gtk.gdk.get_default_root_window()
	sz = w.get_size()

	pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,False,8,sz[0],sz[1])
	pb = pb.get_from_drawable(w,w.get_colormap(),0,0,0,0,sz[0],sz[1])

	return pb.get_pixels_array()

if __name__ == "__main__":

	import doctest
	doctest.testmod()


	time.sleep(5)
	orig_delay = DELAY

	pixarray = take_screenshot()
	write_png_from_pixarray('test.png', pixarray)
	while 1:

		# reset delay
		DELAY = orig_delay

		pixarray = take_screenshot()
		print "Screenshot read"

		try:
			pixarray, offset = crop_dd_screenshot(pixarray)
		except NotDiamondDashException as e:
			print "Not Diamond Dash"
			continue

		print "Screenshot searched"
		countsarray = downsample_pixarray(pixarray, 40)
		best_point = get_best_dd_point(countsarray)

		# Figure out where to click
		x_offset = offset[1] + 20 + best_point[1]*40
		y_offset = offset[0] + 20 + best_point[0]*40

		os.system('xdotool mousemove {0} {1}'.format(x_offset, y_offset))
		os.system('xdotool click 1')
		time.sleep(DELAY)





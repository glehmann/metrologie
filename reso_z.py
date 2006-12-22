#!/usr/bin/env python

import itk, sys
itk.auto_progress(2)
itk.MultiThreader.SetGlobalDefaultNumberOfThreads(1)


def med(numbers):
   "Return the median of the list of numbers."
   # Sort the list and take the middle element.
   n = len(numbers)
   copy = numbers[:] # So that "numbers" keeps its original order
   copy.sort()
   if n & 1:         # There is an odd number of elements
      return copy[n // 2]
   else:
      return (copy[n // 2 - 1] + copy[n // 2]) / 2

reader = itk.lsm(ImageType=itk.Image.US3)

# use a median to remove some noise
median = itk.MedianImageFilter.IUS3IUS3.New(reader)

# first find the beads, to process them one by one
# That's done by projecting the image on the z axis, splitting the 2D image in several
# regions (one per bead) and unprojecting the regions in the original 3d image
projz = itk.MaximumProjectionImageFilter.IUS3IUS2.New(median)
invert = itk.InvertIntensityImageFilter.IUS2IUS2.New(projz)
watershed = itk.MorphologicalWatershedImageFilter.IUS2IUS2.New(invert, MarkWatershedLine=False)
wrelabel = itk.RelabelComponentImageFilter.IUS2IUS2.New(watershed)
upperdim = itk.UpperDimensionImageFilter.IUS2IUS3.New(wrelabel, NewDimension=2)

# mask the image to select only one bead
selectedLabel = itk.BinaryThresholdImageFilter.IUS3IUS3.New(upperdim)
mask = itk.MaskImageFilter.IUS3IUS3IUS3.New(median, selectedLabel)

# and project the image on axis x and y to keep only the max pixel of the slice
# for all the z values
proj2D = itk.MaximumProjectionImageFilter.IUS3IUS2.New(mask, ProjectionDimension=1)
proj1D = itk.MaximumProjectionImageFilter.IUS2IUS2.New(proj2D, ProjectionDimension=0)
# binarize the image
th = itk.BinaryThresholdImageFilter.IUS2IUS2.New(proj1D, InsideValue=1)
# and count the pixels to get the resolution on the z axis
labelShape = itk.LabelShapeImageFilter.IUS2.New(th)
# count the object to display a warning
label = itk.ConnectedComponentImageFilter.IUS2IUS2.New(th)
relabel = itk.RelabelComponentImageFilter.IUS2IUS2.New(label)


for f in sys.argv[1:] :
	reader.SetFileName( f )
	projz.UpdateLargestPossibleRegion()
	m, M = itk.range(projz)
	watershed.SetLevel( m+(M-m)/2 )
	upperdim.SetNewDimensionSapcing( itk.spacing(reader)[2] )
	upperdim.SetNewDimensionSize( itk.size(reader)[2] )
	upperdim.UpdateLargestPossibleRegion() # to get a valid number of labels
	
	# store the results so we can compute the mean and the meadian for 
	# all the beads in the image
	results = []
	
	for l in range(1, wrelabel.GetNumberOfObjects()+1):
		selectedLabel.SetUpperThreshold( l )
		selectedLabel.SetLowerThreshold( l)
		proj1D.UpdateLargestPossibleRegion()
		m, M = itk.range(proj1D)
		th.SetLowerThreshold( (M-m)/2 )
		
		labelShape.UpdateLargestPossibleRegion()
		relabel.UpdateLargestPossibleRegion()
		
		res = labelShape.GetVolume(1) * itk.spacing(reader)[2]
		results.append( res )
		print "%s:\t%i\t%f" % (f, l, res),
		
		# there not enough pixels in the objects - display a warning about resolution
		if labelShape.GetVolume(1) < 10 :
			print "\t!reso!",
		
		# there is more than on object in the image - a problem in the shape of the psf ?
		if relabel.GetNumberOfObjects() != 1:
			print "\t!nb of objects!",
		
		print # end of line
	
	print "%s:\t%s\t%f" % (f, "mean", sum(results)/len(results))
	print "%s:\t%s\t%f" % (f, "median", med(results))
	print

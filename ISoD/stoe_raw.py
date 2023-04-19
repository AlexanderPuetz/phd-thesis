#! /usr/bin/python
# -*- coding: UTF-8 -*-

__author__ = "fr"
__date__ = "$02.08.2014 23:11:52$"

from analytics import SeqData
from analytics import Multiple
from entity import AnaXyData

def procRawData():
	global rawData, desiredImgWidth
	
	fileRaw = rawData.findFolderFile("", "*.raw")

	if fileRaw == None:
		return None
	
	# identify magic bytes
	if not fileRaw.hasBytesAt(0, "RAW_"):
		return None
	
	rawContent = fileRaw.getContent()
	rawSize = len(rawContent)
	
	if rawSize <= 2560:
		# truncated?
		return None
	
	retval = Multiple()
	# read graph sizes at 496ff
	blocks = struct.unpack("<BxBxBxBxBxBxBxB",rawContent[496:511])
	base = 2048
	for blockSize in blocks:
		if blockSize <= 0:
			continue
		
		# prepare graph
		xMin = getFloat(rawContent, base + 44)
		xMax = getFloat(rawContent, base + 52)
		xStep = getFloat(rawContent, base + 60)
		binStart = base + 512
		
		spectrum = SeqData(desiredImgWidth, int(desiredImgWidth / 1.41))
		spectrum.setNoXTicks(6)
		spectrum.setxMin(xMin)
		spectrum.setxMax(xMax)
		spectrum.setxUnit(u'2 ϴ in °')

		spectrum.setNoYTicks(11)
		spectrum.setyUnit("rel. int. %")
		spectrum.setxMarginLeft(40)

		# auto peak-picking
		spectrum.setAverExc(1.15)
		spectrum.setAverCells(50)
		spectrum.setMaxPeaks(50)
		spectrum.setMinRelPeak(0.04)
		spectrum.setMinPeakRelRange(0.003)

		# get graph at 2560
		#blocks = struct.unpack("<h",rawContent[495:497])[0]
		blocks = int((xMax - xMin) / xStep)

		bytePerPoint = 4
		numberFormat = "i"
		maxBlocks = int((blockSize * 512) / bytePerPoint)
		if blocks > maxBlocks: # file is too small for int
			bytePerPoint = 2
			numberFormat = "h"

		binEnd = binStart + blocks * bytePerPoint
		
		if binEnd > rawSize:
			break
		
		fmt = "<" + str(blocks) + numberFormat
		spectrum.addDataRow(list(struct.unpack(fmt, rawContent[binStart:binEnd])))

		# ignore negative values, artefacts
		if spectrum.getyMin() < 0.0:
			spectrum.setyMin(0.0)

		peakList = spectrum.getIntPeakListForActiveDataRow()
		yMax = spectrum.getyMax()
		deltaY = spectrum.getDeltaY()

		if deltaY > 0.0:
			yFactor = 100.0 / yMax
			spectrum.setyLabelFactor(yFactor)
			spectrum.setyLabelDecimals(0)
			# make percent values
			peaksInterpretations = []
			for peak in peakList:
				anaXyData = AnaXyData(peak.x, peak.y)
				spectrum.addToAnaXyDataCollection(anaXyData)
				peaksInterpretations.append(str(int(round(peak.x))) + " (" + str(int(peak.y * yFactor)) + ")")
			spectrum.normalizeAnaXyData()
			if len(peaksInterpretations) > 0:
				interpretation = u'2ϴ=' + ", ".join(peaksInterpretations) + u' °'
				spectrum.setTextReport(interpretation)
		retval.add(spectrum)
		base = base + (blockSize + 1) * 512
	
	sz = retval.size()
	if sz == 0:
		return None
	if sz == 1:
		return retval.get(0)
	
	return retval

def getFloat(rawContent, offset):
	return struct.unpack("<f",rawContent[offset:offset + 4])[0]
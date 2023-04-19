#! /usr/bin/python
# -*- coding: UTF-8 -*-

__author__ = "fr"
__date__ = "$02.08.2014 23:11:52$"

from analytics import SeqData
from entity import AnaXyData

bytePerPoint = 4
def procRawData():
	global rawData, desiredImgWidth, bytePerPoint
	
	fileRaw = rawData.findFolderFile("", "*.raw")

	if fileRaw == None:
		return None
	
	# identify magic bytes
	if not (fileRaw.hasBytesAt(0, "RAW") and fileRaw.hasBytesAt(7, "\0")):
		return None
	
	rawContent = fileRaw.getContent()
	rawSize = len(rawContent)
	binStart = 1016
	
	if rawSize <= binStart:
		# truncated?
		return None
	
	# prepare graph
	xMin = getFloat(rawContent, 728)
	xStep = getFloat(rawContent, 888)
	blocks = getInt(rawContent, 716)
	xMax = xMin + xStep * blocks
	# print str(blocks)+"/"+str(xMax)
	retval = SeqData(desiredImgWidth, int(desiredImgWidth / 1.41))
	retval.setNoXTicks(6)
	retval.setxMin(xMin)
	retval.setxMax(xMax)
	retval.setxUnit(u'2 ϴ in °')
	
	retval.setNoYTicks(11)
	retval.setyUnit("rel. int. %")
	retval.setxMarginLeft(40)
	
	# auto peak-picking
	retval.setAverExc(1.15)
	retval.setAverCells(50)
	retval.setMaxPeaks(50)
	retval.setMinRelPeak(0.04)
	retval.setMinPeakRelRange(0.003)
	
	properties = retval.getAnaDataProperty()
	properties.put("xray_source", struct.unpack("2s", rawContent[608:610])[0])
	
	# get graph at 1016
	fmt = "<" + str(blocks) + "f"
	retval.addDataRow(list(struct.unpack(fmt, rawContent[binStart:binStart + blocks * bytePerPoint])))
	
	# ignore negative values, artefacts
	if retval.getyMin() < 0.0:
		retval.setyMin(0.0)
	
	peakList = retval.getIntPeakListForActiveDataRow()
	yMax = retval.getyMax()
	deltaY = retval.getDeltaY()
	
	if deltaY > 0.0:
		yFactor = 100.0 / yMax
		retval.setyLabelFactor(yFactor)
		retval.setyLabelDecimals(0)
		# make percent values
		peaksInterpretations = []
		for peak in peakList:
			anaXyData = AnaXyData(peak.x, peak.y)
			retval.addToAnaXyDataCollection(anaXyData)
			peaksInterpretations.append(str(int(round(peak.x))) + " (" + str(int(peak.y * yFactor)) + ")")
		retval.normalizeAnaXyData()
		interpretation = u'2ϴ=' + ", ".join(peaksInterpretations) + u' °'
		retval.setTextReport(interpretation)
	
	return retval

def getFloat(rawContent, offset):
	return struct.unpack("<d",rawContent[offset:offset + 8])[0]

def getInt(rawContent, offset):
	return struct.unpack("<i",rawContent[offset:offset + 4])[0]
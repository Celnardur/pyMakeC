#!/usr/bin/env python3

import os
import json
import re


# Functions

def listFiles(sSearchDir="."):
	"""Recursively list all the files contained in the passed directory."""
	for root, dirs, files in os.walk(sSearchDir):
		for file in files:
			yield os.path.join(root, file)


def listDirs(sSearchDir="."):
	"""Recursively list the sub-directories of the one passed to it."""
	for root, dirs, files in os.walk(sSearchDir):
		for dir in dirs:
			yield os.path.join(root, dir)


class CFile(object):
	def __init__(self, sFilePath,  oFileDepen = None):
		if oFileDepen is None:
			self.sPath = sFilePath
			self.unixModTime = os.path.getmtime(sFilePath)
			# do this latter for potential concurrency
			self.lDepens = None
		else:
			regex = r'\.c(pp)?$'
			sName = re.sub(regex, '.o', os.path.basename(oFileDepen.sPath))
			self.sPath = sFilePath + '/' + sName
			self.unixModTime = 0
			self.oFileDepen = oFileDepen
			# do this latter for potential concurrency
			self.lDepens = None

	def __str__(self):
		sPrintStr = 'Path:   {}'.format(self.sPath)
		sPrintStr += '\nDepens:'
		for oSrc in self.lDepens:
			sPrintStr += '\n' + oSrc.sPath
		return sPrintStr

	def addDepens(self, loSrcObjs):
		self.lDepens = set()
		regex = r'[<"](.+)[">]'

		with open(self.sPath) as fsSrc:
			for line in fsSrc:
				line = line.rstrip()
				# if '{' in line:
				# 	break

				if line.startswith('#include'):
					for oSrc in loSrcObjs:
						if oSrc.matches(re.findall(regex, line)[0]):
							self.lDepens.add(oSrc)

	def getDepens(self, loSrcOjbs):
		for oSrc in self.lDepens:
			if oSrc in loSrcObjs:
				loSrcObjs.remove(oSrc)
				yield oSrc
				yield from oSrc.getDepens(loSrcObjs)

	def matches(self, sPath):
		return self.sPath.endswith(sPath)

	def getPath(self):
		return self.sPath

	def getModTime(self):
		return self.unixModTime


# default settings
settings = {
	"CC": "g++",
	"Flags": "",
	"LinkerFlags": "",
	"SrcRootDir": ".",
	"OtherSrcDirs": [],
	"IncludeDirs": [],
	"LibDirs": [],
	"Bin": ".",
	"ObjDir": "."
}

# read settings from cset file if it exists
if os.path.isfile('./cset.json'):
	with open('cset.json') as cset:
		settings = json.load(cset)

# find all the sources files
lSources = {
	file for file in listFiles(settings['SrcRootDir'])
	if file.endswith('.cpp') or file.endswith('.h') or file.endswith('.c')
}

lSources |= {
	file for dirs in settings['OtherSrcDirs'] for file in os.listdir(dirs)
	if file.endswith('.cpp') or file.endswith('.h') or file.endswith('.c')
}

lSources |= {
	file for dirs in settings['IncludeDirs'] for file in listFiles(dirs)
	if file.endswith('.cpp') or file.endswith('.h') or file.endswith('.c')
}

loSrcObjs = set()
for file in lSources:
	loSrcObjs.add(CFile(file))

for oSrc in loSrcObjs:
	oSrc.addDepens(loSrcObjs)
	print(oSrc)

loObjFiles = {
	CFile(settings['ObjDir'], oSrc)
	for oSrc in loSrcObjs
	if oSrc.sPath.endswith('.cpp') or oSrc.sPath.endswith('.c')
}

print('\nObjectFiles')

# need to loop through obj Depens multiple times
for oObj in loObjFiles:
	oObj.lDepens = set(oObj.oFileDepen.getDepens(loSrcObjs[:]))
	print(oObj)

print('\nSource Objs\n')

for oSrc in loSrcObjs:
	print(oSrc)

for oObj in loObjFiles:
	if os.path.isfile(oObj.sPath):
		oObj.unixModTime = os.path.getmtime(oObj.sPath)


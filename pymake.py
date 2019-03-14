#!/usr/bin/env python3

import os
import json
import re
import sys


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


def findSourceFiles(sSearchDir='.', lsFileEndings=None):
	"""Return the source files in the passed directory and sub directories."""
	if lsFileEndings is None:
		return (file for file in listFiles(sSearchDir))
	else:
		return (
			file for file in listFiles(sSearchDir)
			for sEnding in lsFileEndings
			if file.endswith(sEnding)
		)


def getIncludes(sFile):
	"""Returns the includes that are used in this file."""
	regex = r'#include ?[<"](.+)[">]'
	with open(sFile) as fsFileStream:
		return re.findall(regex, fsFileStream.read())


def getProjIncludes(sFile, lsSrcs):
	"""Returns a list of includes that are in the project"""
	return {
		sSrc for sInc in getIncludes(sFile)
		for sSrc in lsSrcs
		if sSrc.endswith(sInc)
	}


def getEndingRegex(lsSrcEndings):
	"""Returns a compiled regex that searches for the given endings"""
	regex = "("
	for sEnd in lsSrcEndings:
		regex += '\\' + sEnd + '$|'
	regex = regex[:-1] + ')'
	return re.compile(regex)


def getDepens(sFile, dSrcData, setsDepens):
	"""Returns a set of all the dependencies of a file"""
	setsDepens.add(sFile)
	for sDepen in dSrcData[sFile]:
		if sDepen not in setsDepens:
			getDepens(sDepen, dSrcData, setsDepens)
	return setsDepens


def getObjFiles(dSrcData, lsSrcEndings, sObjEnding, sObjDir):
	"""Returns a dict of needed object files to compile project mapped to their .cpp/.c."""
	regex = getEndingRegex(lsSrcEndings)
	return {
		sObjDir + '/' + os.path.basename(regex.sub(sObjEnding, sSrc)): sSrc
		for sSrc in dSrcData.keys()
		if regex.search(sSrc)
	}


def getObjData(dSrcData, dObjFiles):
	"""Returns a dict of needed object files with their dependencies."""
	return {
		sObj: getDepens(dObjFiles[sObj], dSrcData, set())
		for sObj in dObjFiles.keys()
	}


def needsCompilation(sObj, dObjData):
	"""Returns true if an Obj file needs to be compiled."""
	if not os.path.exists(sObj):
		return True

	fLastCmp = os.path.getmtime(sObj)
	for sDepen in dObjData[sObj]:
		if fLastCmp < os.path.getmtime(sDepen):
			return True


def getObjsToCmp(dObjFiles, dObjData):
	"""Returns a dictionary of the Objects that need to be Compiled."""
	return {
		sObj: sSrc
		for sObj, sSrc in dObjFiles.items()
		if needsCompilation(sObj, dObjData)
	}


def compileObjs(settings, dObjFiles):
	"""Compiles the Object files from their data."""
	sBaseCmd = settings['Compiler'] + ' ' + settings['Flags'] + ' -c -o '
	sEndCmd = ''
	for sInc in settings['Include Dirs']:
		sEndCmd += ' -I' + sInc
	for sInc in settings["3rd Party Include Dirs"]:
		sEndCmd += ' -I' + sInc

	for sObj, sDepen in dObjFiles.items():
		sMid = sObj + ' ' + sDepen
		print(sBaseCmd + sMid + sEndCmd)
		os.system(sBaseCmd + sMid + sEndCmd)


def compileExe(settings, dObjFiles):
	"""Compiles an executable from the Object files."""
	sBaseCmd = settings['Compiler'] + ' ' + settings['Flags'] + ' -o ' + \
	           settings['Bin'] + '/' + settings['Project Name'] + '.exe '

	sEndCmd = ''
	for sLib in settings['Libs']:
		sEndCmd += '-l' + sLib + ' '
	for sLib in settings['Lib Dirs']:
		sEndCmd += '-L' + sLib + ' '

	sMid = ''
	for sObj in dObjFiles.keys():
		sMid += sObj + ' '

	sCmd = sBaseCmd + sMid + sEndCmd
	print(sCmd)
	os.system(sCmd)


def clean(settings):
	"""Cleans a project based on the source files."""
	sExeClean = 'rm ' + settings['Bin'] + '/' + settings['Project Name'] + '.exe'
	sObjClean = 'rm ' + settings['Obj Dir'] + '/*.o'
	print(sExeClean)
	os.system(sExeClean)
	print(sObjClean)
	os.system(sObjClean)
	sys.exit(0)


def run(settings):
	"""Runs a project from an executable given."""
	sRun = settings['Bin'] + '/' + settings['Project Name'] + '.exe'
	if os.path.exists(sRun):
		print(sRun + ' &')
		os.system(sRun + ' &')
		sys.exit(0)
	else:
		print('No executable file')
		sys.exit(1)


def genProjectFile(settings):
	if not os.path.exists('./project.json'):
		sProject = '''{
	"Project Name": "project",
	"Compiler": "g++",
	"Flags": "-g -Wall",
	"Src Root Dir": ".",
	"Other Src Dirs": [],
	"Include Dirs": [],
	"3rd Party Include Dirs": [],
	"Lib Dirs": [],
	"Libs": [],
	"Bin": ".",
	"Obj Dir": ".",
	"Executable": true
}'''
		with open('project.json', 'w') as fp:
			fp.write(sProject)
	sys.exit(0)


if __name__ == '__main__':

	# default settings
	settings = {
		"Project Name": "project",
		"Compiler": "g++",
		"Flags": "-g -Wall",
		"Src Root Dir": ".",
		"Other Src Dirs": [],
		"Include Dirs": [],
		"3rd Party Include Dirs": [],
		"Lib Dirs": [],
		"Libs": [],
		"Bin": ".",
		"Obj Dir": ".",
		"Executable": True
	}
	bRun = False

	# read settings from cset file if it exists
	if os.path.isfile('./project.json'):
		with open('project.json') as cset:
			settings = json.load(cset)

	# Command line options
	args = sys.argv[1:]
	if len(args) and not args[0].startswith('-'):
		arg = args.pop(0)
		if arg == 'clean':
			clean(settings)
		elif arg == 'test':
			bRun = True
		elif arg == 'project':
			genProjectFile(settings)

	setsSrcDirs = set(settings['Other Src Dirs'] + settings['Include Dirs'])
	setsSrcDirs.add(settings['Src Root Dir'])
	setsSources = {
		sFile for sDir in setsSrcDirs
		for sFile in findSourceFiles(sDir, ['.c', '.cpp', '.h'])
	}

	dSrcData = {sSrc: getProjIncludes(sSrc, setsSources) for sSrc in setsSources}

	dObjFiles = getObjFiles(dSrcData, ['.c', '.cpp'], '.o', settings['Obj Dir'])
	dObjData = getObjData(dSrcData, dObjFiles)
	dObjToCmp = getObjsToCmp(dObjFiles, dObjData)
	compileObjs(settings, dObjToCmp)
	if settings['Executable']:
		compileExe(settings, dObjFiles)

	if bRun and not settings['Executable']:
		print('No Executable to run')
		sys.exit(2)

	if bRun:
		run(settings)


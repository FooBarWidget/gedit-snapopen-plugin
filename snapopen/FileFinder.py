import os
import os.path
import fnmatch

try:
	import psyco
	from psyco.classes import __metaclass__
except:
	pass

from IgnoreFile import IgnoreFile

if 'relpath' in dir(os.path):
	relpath = os.path.relpath
else:
	def relpath(path, start):
		if not start.endswith(os.sep):
			start += os.sep
		if path.startswith(start):
			return path[len(start):]
		else:
			return path

class FileFinder:
	def __init__(self, directory, pattern = None):
		self.directory = os.path.normcase(os.path.normpath(directory))
		if pattern:
			self.pattern = pattern.lower()
		else:
			self.pattern = None
	
	def start(self, callback):
		self._traverse(self.directory, set(), None, callback)
	
	def _traverse(self, directory, dirs_seen, ignore_file, callback):
		try:
			entries = os.listdir(directory)
		except (OSError):
			entries = None
		if entries:
			try:
				f = open(os.path.join(directory, '.snapopen_ignore'), 'r')
				lines = f.readlines()
				f.close()
				ignore_file = IgnoreFile(directory, lines, ignore_file)
			except (IOError):
				pass
			for entry in sorted(entries):
				if entry.startswith('.'):
					# Ignore hidden files.
					continue
				path      = os.path.join(directory, entry)
				real_path = os.path.realpath(path)
				norm_path = os.path.normcase(os.path.normpath(path))
				if ignore_file and ignore_file.match(norm_path):
					continue
				if os.path.isdir(norm_path):
					if real_path in dirs_seen:
						# Make sure we don't follow cyclic symlinks.
						continue
					else:
						dirs_seen.add(real_path)
						self._traverse(norm_path, dirs_seen, ignore_file, callback)
				else:
					rel_path = relpath(norm_path, self.directory)
					if not self.pattern or fnmatch.fnmatch(rel_path.lower(), self.pattern):
						callback(rel_path)

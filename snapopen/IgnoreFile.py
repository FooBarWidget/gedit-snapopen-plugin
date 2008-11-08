import os.path
from fnmatch import fnmatch

try:
	import psyco
	from psyco.classes import __metaclass__
except:
	pass

# Patterns in ignore files are supposed to work similar to .gitignore:
#
# - If the pattern does not contain a slash /, it will be treated as a
#   shell glob pattern and checks for a match against the pathname
#   without leading directories.
# - Otherwise, the pattern will be treated as a shell glob suitable for
#   consumption by fnmatch.
class IgnoreFile:
	class Rule:
		def __init__(self, pattern, is_dir_rule, match_subdirs):
			self.pattern       = pattern
			self.is_dir_rule   = is_dir_rule
			self.match_subdirs = match_subdirs
	
	def __init__(self, directory, lines, chain = None):
		self.directory = directory
		self.rules     = self._compile_to_rules(lines)
		self.chain     = chain
	
	def match(self, relative_filename):
		for rule in self.rules:
			if self._matches_rule(relative_filename, rule):
				return True
		return False
	
	def _compile_to_rules(self, lines):
		rules = []
		if isinstance(lines, str):
			lines = lines.replace("\r\n", "\n").split("\n")
		for line in lines:
			line = line.strip()
			if len(line) > 0 and not line.startswith('#'):
				full_path = os.path.join(self.directory, line.rstrip('/'))
				if line.startswith('/'):
					if line.endswith('/') or os.path.isdir(full_path):
						rule = self.Rule(line.strip('/'), True, False)
					else:
						rule = self.Rule(line.lstrip('/'), False, False)
				else:
					if line.endswith('/') or os.path.isdir(full_path):
						rule = self.Rule(line.rstrip('/'), True, True)
					else:
						rule = self.Rule(line, False, True)
				rules.append(rule)
		return rules
	
	def _matches_rule(self, relative_filename, rule):
		if rule.match_subdirs:
			result = False
			if self.directory == '.':
				rule_prefix = ''
			else:
				rule_prefix = self.directory + os.sep
			if rule.is_dir_rule:
				result = fnmatch(relative_filename, rule_prefix + rule.pattern + '/*')
			#print [relative_filename, os.path.join(rule_prefix, '*', rule.pattern)]
			result = result or fnmatch(relative_filename, os.path.join(rule_prefix, rule.pattern))
			return result
		else:
			if rule.is_dir_rule:
				ref_dir = (self.directory + os.sep + rule.pattern).rstrip(os.sep)
			else:
				ref_dir = (self.directory + os.sep + os.path.dirname(rule.pattern)).rstrip(os.sep)
			file_dir = os.path.dirname(relative_filename)
			if len(file_dir) == 0:
				file_dir = '.'
			#print [self.directory, relative_filename, rule.pattern, ref_dir, file_dir]
			if ref_dir == file_dir:
				result = False
				if rule.is_dir_rule:
					result = fnmatch(
						os.path.basename(relative_filename),
						os.path.basename(rule.pattern + os.sep + '/*'))
				result = result or \
					fnmatch(
						os.path.basename(relative_filename),
						os.path.basename(rule.pattern))
				return result
			else:
				return False

import unittest
import tempfile
import shutil
import os
import os.path
import stat

from FileFinder import FileFinder
from IgnoreFile import IgnoreFile

class FileFinderTest(unittest.TestCase):
	def setUp(self):
		self.tempdir = tempfile.mkdtemp()
		self.filelist = set()
	
	def tearDown(self):
		shutil.rmtree(self.tempdir)
	
	def callback(self, filename):
		self.filelist.add(filename.replace(os.sep, '/'))
	
	def touch(self, subfilename):
		filename = os.path.join(self.tempdir, subfilename.replace('/', os.sep))
		directory = os.path.dirname(filename)
		if not os.path.exists(directory):
			os.makedirs(directory)
		open(filename, 'w').close()
	
	def test_listing_empty_directory(self):
		FileFinder(self.tempdir).start(self.callback)
		self.assertEqual(self.filelist, set())
	
	def test_listing_directory_with_only_files(self):
		self.touch("file1")
		self.touch("file2")
		FileFinder(self.tempdir).start(self.callback)
		self.assertEqual(self.filelist, set(['file1', 'file2']))
	
	def test_listing_directory_with_only_files_and_with_filter(self):
		self.touch("file1")
		self.touch("file2.txt")
		self.touch("file3.txt")
		self.touch("file4")
		FileFinder(self.tempdir, '*.txt').start(self.callback)
		self.assertEqual(self.filelist, set(['file2.txt', 'file3.txt']))

	def test_listing_files_in_subdirectories_and_with_filter(self):
		self.touch("hello/world.txt")
		self.touch("foo/bar.txt")
		self.touch("foo/baz.txt")
		self.touch("foo/banana.jpg")
		FileFinder(self.tempdir, '*.txt').start(self.callback)
		self.assertEqual(self.filelist, set(['hello/world.txt', 'foo/bar.txt', 'foo/baz.txt']))
	
	def test_filter_matches_full_relative_path(self):
		self.touch("foo/bar.txt")
		self.touch("unrelated/hmpf.txt")
		FileFinder(self.tempdir, 'foo/*.txt').start(self.callback)
		self.assertEqual(self.filelist, set(['foo/bar.txt']))
	
	def test_cyclic_symlinks_are_not_followed(self):
		self.touch("subdir/file.txt")
		self.touch("foo/test.py")
		os.symlink("../subdir", os.path.join(self.tempdir, "subdir", "subdir"))
		FileFinder(self.tempdir).start(self.callback)
		self.assertEqual(self.filelist, set(['subdir/file.txt', 'foo/test.py']))
	
	def test_listing_file_symlinks(self):
		self.touch("subdir/file1.txt")
		os.symlink("file1.txt", os.path.join(self.tempdir, "subdir", "file2.txt"))
		FileFinder(self.tempdir).start(self.callback)
		self.assertEqual(self.filelist, set(['subdir/file1.txt', 'subdir/file2.txt']))
	
	def test_correct_relative_paths_are_passed_to_callbacks(self):
		tempdir2 = tempfile.mkdtemp()
		try:
			filename = os.path.join(tempdir2, "file.txt")
			open(filename, 'w').close()
			os.symlink(filename, os.path.join(self.tempdir, "symlink.txt"))
			FileFinder(self.tempdir).start(self.callback)
			self.assertEqual(self.filelist, set(['symlink.txt']))  # instead of file.txt
		finally:
			shutil.rmtree(tempdir2)
	
	def test_read_permissions_are_ignored(self):
		self.touch("subdir/file.txt")
		subdir = os.path.join(self.tempdir, "subdir")
		os.chmod(subdir, 0000)
		try:
			FileFinder(self.tempdir).start(self.callback)
			self.assertEqual(self.filelist, set())
		finally:
			os.chmod(subdir, stat.S_IRWXU)
	
	def test_ignore_file(self):
		self.touch("README.TXT")
		self.touch("ruby/gc.c")
		self.touch("ruby/rdoc/index.html")
		self.touch("ruby/rdoc/methods.html")
		self.touch("ruby/rdoc/classes/String.html")
		self.touch("ruby/rdoc/classes/Array.html")
		self.touch("ruby/rdoc/classes/File/Stat.html")
		f = open(os.path.join(self.tempdir, "ruby", "rdoc", ".snapopen_ignore"), 'w')
		f.write("index.html\n")
		f.write("classes\n")
		f.close()
		FileFinder(self.tempdir).start(self.callback)
		self.assertEqual(self.filelist, set(['README.TXT', 'ruby/gc.c', 'ruby/rdoc/methods.html']))

class IgnoreFileTest(unittest.TestCase):
	def test_empty_ignore_file_matches_nothing(self):
		self.assert_(not IgnoreFile(".", "").match("foo.txt"))
		
	def test_pattern_without_slash(self):
		self.assert_(IgnoreFile(".", "*.txt").match("tmp/foo.txt"))
		self.assert_(not IgnoreFile(".", "*.txt").match("tmp/foo.jpg"))
	
	def test_pattern_with_slash(self):
		self.assert_(IgnoreFile(".", "/*.txt").match("foo.txt"))
		self.assert_(not IgnoreFile(".", "/*.txt").match("tmp/foo.txt"))
	
	def test_entry_for_directory_matches_subfiles_and_subdirectories(self):
		self.assert_(IgnoreFile(".", "folder/").match("folder"))
		self.assert_(IgnoreFile(".", "folder/").match("folder/file1.txt"))
		self.assert_(IgnoreFile(".", "folder/").match("folder/file2.txt"))
		self.assert_(IgnoreFile(".", "folder/").match("folder/subfolder/banana.jpg"))
		self.assert_(not IgnoreFile(".", "folder/").match("another_folder"))
		# TODO: the following is not implemented yet. Not very important
		# but would be nice to have.
		self.assert_(IgnoreFile(".", "folder/").match("foo/folder/banana.jpg"))
	
	def test_matches_only_files_and_directories_in_its_own_directory(self):
		self.assert_(not IgnoreFile("ruby/rdoc", "*.html").match("index.html"))
		self.assert_(IgnoreFile("ruby/rdoc", "*.html").match("ruby/rdoc/index.html"))
		self.assert_(IgnoreFile("ruby/rdoc", "*.html").match("ruby/rdoc/classes/String.html"))
		self.assert_(IgnoreFile("ruby/rdoc", "/*.html").match("ruby/rdoc/index.html"))
		self.assert_(not IgnoreFile("ruby/rdoc", "/*.html").match("ruby/rdoc/classes/String.html"))
		self.assert_(IgnoreFile("ruby", "/rdoc/").match("ruby/rdoc/index.html"))
		self.assert_(not IgnoreFile("ruby/rdoc", "/ruby/rdoc/").match("ruby/rdoc/classes/index.html"))
	
	def test_autodetection_of_dir_rules(self):
		tempdir = tempfile.mkdtemp()
		old_cwd = os.getcwd()
		try:
			os.makedirs(os.path.join(tempdir, "ruby", "rdoc"))
			os.chdir(tempdir)
			self.assert_(IgnoreFile("ruby", "rdoc").match("ruby/rdoc"))
			self.assert_(IgnoreFile("ruby", "rdoc").match("ruby/rdoc/index.html"))
			self.assert_(IgnoreFile("ruby", "rdoc").match("ruby/rdoc/classes/index.html"))
			self.assert_(not IgnoreFile("ruby", "rdoc").match("foo/rdoc/index.html"))
		finally:
			shutil.rmtree(tempdir)
			os.chdir(old_cwd)

if __name__ == '__main__':
	unittest.main()


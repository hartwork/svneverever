#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later
#
from __future__ import print_function
import pysvn
import sys
import math
import os
import time
import fcntl
import termios
import struct

try:
	import argparse
except ImportError:
	print("ERROR: You need Python 2.7+ unless you have module argparse "
		"(package dev-python/argparse on Gentoo) installed independently.", file=sys.stderr)
	sys.exit(1)


def get_terminal_width():
	try:
		return int(os.environ['COLUMNS'])
	except:
		pass

	def query_fd(fd):
		rows, cols, ph, pw = struct.unpack('HHHH', (fcntl.ioctl(fd, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0))))
		return cols

	for fd in (0, 1, 2):
		try:
			return query_fd(fd)
		except:
			pass

	try:
		fd = os.open(os.ctermid(), os.O_RDONLY)
		try:
			return query_fd(fd)
		except:
			pass
		finally:
			os.close(fd)
	except:
		pass

	return 80


def dump_tree(t, revision_digits, latest_revision, config, level=0, branch_level=-3, tag_level=-3):
	def indent_print(line_start, text):
		if config.show_numbers:
			print('%s  %s%s' % (line_start, ' '*(4*level), text))
		else:
			print('%s%s' % (' '*(4*level), text))

	items = ((k, v) for k, v in t.items() if k)

	if ((branch_level + 2 == level) and not config.show_branches) \
			or ((tag_level + 2 == level) and not config.show_tags) \
			or level >= config.max_depth:
		if items and config.show_dots:
			line_start = ' '*(1 + revision_digits + 2 + revision_digits + 1)
			indent_print(line_start, '[..]')
		return

	for k, (added_on_rev, last_deleted_on_rev, children) in sorted(items):
		format = '[%%%dd; %%%dd]' % (revision_digits, revision_digits)
		if last_deleted_on_rev is not None:
			last_seen_rev = last_deleted_on_rev - 1
		else:
			last_seen_rev = latest_revision
		visual_rev = format % (added_on_rev, last_seen_rev)

		indent_print(visual_rev, '/%s' % k)

		bl = branch_level
		tl = tag_level
		if k == 'branches':
			bl = level
		elif k == 'tags':
			tl = level

		dump_tree(children, revision_digits, latest_revision, config, level=level + 1, branch_level=bl, tag_level=tl)


def dump_nick_stats(nick_stats, revision_digits, config):
	if config.show_numbers:
		format = "%%%dd [%%%dd; %%%dd]  %%s" % (revision_digits, revision_digits, revision_digits)
		for nick, (first_commit_rev, last_commit_rev, commit_count) in sorted(nick_stats.items()):
			print(format % (commit_count, first_commit_rev, last_commit_rev, nick))
	else:
		for nick, (first_commit_rev, last_commit_rev, commit_count) in sorted(nick_stats.items()):
			print(nick)


def ensure_uri(text):
	import re
	svn_uri_detector = re.compile('^[A-Za-z+]+://')
	if svn_uri_detector.search(text):
		return text
	else:
		import os
		import urllib
		abspath = os.path.abspath(text)
		return 'file://%s' % urllib.quote(abspath)


def digit_count(n):
	if n == 0:
		return 1
	assert(n > 0)
	return int(math.floor(math.log10(n)) + 1)


def hms(seconds):
	seconds = math.ceil(seconds)
	h = int(seconds / 3600)
	seconds = seconds - h*3600
	m = int(seconds / 60)
	seconds = seconds - m*60
	return h, m, seconds


def make_progress_bar(percent, width, seconds_taken, seconds_expected):
	other_len = (6 + 1) + 2 + (1 + 8 + 1 + 9 + 1) + 3 + 1
	assert(width > 0)
	bar_content_len = width - other_len
	assert(bar_content_len >= 0)
	fill_len = int(percent * bar_content_len / 100)
	open_len = bar_content_len - fill_len
	seconds_remaining = seconds_expected - seconds_taken
	hr, mr, sr = hms(seconds_remaining)
	if hr > 99:
		hr = 99
	return '%6.2f%%  (%02d:%02d:%02d remaining)  [%s%s]' % (percent, hr, mr, sr, '#'*fill_len, ' '*open_len)


def command_line():
	from svneverever.version import VERSION_STR
	parser = argparse.ArgumentParser(description='Collects path entries across SVN history')
	parser.add_argument(
		'--version',
		action='version', version='%(prog)s ' + VERSION_STR)
	parser.add_argument('repo_uri',
		metavar='REPOSITORY', action='store',
		help='Path or URI to SVN repository')
	parser.add_argument(
		'--tags',
		dest='show_tags', action='store_true', default=False,
		help='Show content of tag folders (default: disabled)')
	parser.add_argument(
		'--branches',
		dest='show_branches', action='store_true', default=False,
		help='Show content of branch folders (default: disabled)')
	parser.add_argument(
		'--no-dots',
		dest='show_dots', action='store_false', default=True,
		help='Hide "[..]" omission marker (default: disabled)')
	parser.add_argument(
		'--no-numbers',
		dest='show_numbers', action='store_false', default=True,
		help='Hide numbers, e.g. revision ranges (default: disabled)')
	parser.add_argument(
		'--no-progress',
		dest='show_progress', action='store_false', default=True,
		help='Hide progress bar (default: disabled)')
	parser.add_argument(
		'--depth',
		dest='max_depth', metavar='DEPTH', action='store', type=int, default=-1,
		help='Maximum depth to print (starting at 1)')
	parser.add_argument(
		'--authors',
		dest='authors_mode', action='store_true', default=False,
		help='Collect author names instead of path information (default: disabled)')

	args = parser.parse_args()

	args.repo_uri = ensure_uri(args.repo_uri)
	if args.max_depth < 1:
		args.max_depth = sys.maxint

	return args


def main():
	args = command_line()

	# Build tree from repo
	client = pysvn.Client()
	tree = dict()
	try:
		latest_revision = client.info2(args.repo_uri, recurse=False)[0][1]['last_changed_rev'].number
	except (pysvn.ClientError) as e:
		sys.stderr.write('ERROR: %s\n' % str(e))
		sys.exit(1)
	prev_percent = 0

	start_time = time.time()
	sys.stderr.write('Analyzing %d revisions...\n' % latest_revision)
	width = get_terminal_width()
	
	def indicate_progress(rev, before_work=False):
		percent = rev * 100.0 / latest_revision
		seconds_taken = time.time() - start_time
		seconds_expected = seconds_taken / float(rev) * latest_revision
		if (rev == latest_revision) and not before_work:
			percent = 100
			seconds_expected = seconds_taken
		sys.stderr.write('\r' + make_progress_bar(percent, width, seconds_taken, seconds_expected))
		sys.stderr.flush()

	nick_stats = dict()
	
	for rev in xrange(1, latest_revision + 1):
		if rev == 1 and args.show_progress:
			indicate_progress(rev, before_work=True)

		if args.authors_mode:
			author_name = client.revpropget('svn:author', args.repo_uri, pysvn.Revision(pysvn.opt_revision_kind.number, rev))[1]
			(first_commit_rev, last_commit_rev, commit_count) = nick_stats.get(author_name, (None, None, 0))

			if first_commit_rev is None:
				first_commit_rev = rev
			last_commit_rev = rev
			commit_count = commit_count + 1

			nick_stats[author_name] = (first_commit_rev, last_commit_rev, commit_count)

			if args.show_progress:
				indicate_progress(rev)
			continue

		summary = client.diff_summarize(
			args.repo_uri,
			revision1=pysvn.Revision(pysvn.opt_revision_kind.number, rev - 1),
			url_or_path2=args.repo_uri,
			revision2=pysvn.Revision(pysvn.opt_revision_kind.number, rev),
			recurse=True,
			ignore_ancestry=True)

		def is_directory_addition(summary_entry):
			return summary_entry.summarize_kind == pysvn.diff_summarize_kind.added \
				and summary_entry.node_kind == pysvn.node_kind.dir

		def is_directory_deletion(summary_entry):
			return summary_entry.summarize_kind == pysvn.diff_summarize_kind.delete \
				and summary_entry.node_kind == pysvn.node_kind.dir

		dirs_added = [e.path for e in summary if is_directory_addition(e)]
		for d in dirs_added:
			sub_tree = tree
			for name in d.split('/'):
				if name not in sub_tree:
					added_on_rev, last_deleted_on_rev, children = rev, None, dict()
					sub_tree[name] = (added_on_rev, last_deleted_on_rev, children)
				else:
					added_on_rev, last_deleted_on_rev, children = sub_tree[name]
				sub_tree = children

		def mark_deleted_recursively(sub_tree, name, rev):
			added_on_rev, last_deleted_on_rev, children = sub_tree[name]
			sub_tree[name] = (added_on_rev, rev, children)
			for child_name in children.keys():
				mark_deleted_recursively(children, child_name, rev)

		dirs_deleted = [e.path for e in summary if is_directory_deletion(e)]
		for d in dirs_deleted:
			sub_tree = tree
			comps = d.split('/')
			comps_len = len(comps)
			for i, name in enumerate(comps):
				if i == comps_len - 1:
					mark_deleted_recursively(sub_tree, name, rev)
				else:
					added_on_rev, last_deleted_on_rev, children = sub_tree[name]
					sub_tree = children

		if args.show_progress:
			indicate_progress(rev)

	if args.show_progress:
		sys.stderr.write('\n\n')
	else:
		sys.stderr.write('\n')
	sys.stderr.flush()

	# NOTE: Leaves are files and empty directories
	if args.authors_mode:
		dump_nick_stats(nick_stats, digit_count(latest_revision), config=args)
	else:
		dump_tree(tree, digit_count(latest_revision), latest_revision, config=args)


if __name__ == '__main__':
	main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later
#
from __future__ import print_function
import pysvn
import sys
import math

USAGE = """
  %prog  REPOSITORY"""


def dump(t, revision_digits, latest_revision, level=0, branch_tag_level=-3):
	def indent_print(line_start, text):
		print(line_start, '%s%s' % (' '*(4*level), text))

	if branch_tag_level + 2 == level:
		indent_print('[..]')
		return

	for k, (added_on_rev, last_deleted_on_rev, children) in sorted(t.items()):
		if not k:
			continue

		format = '[%%%dd; %%%dd]' % (revision_digits, revision_digits)
		if last_deleted_on_rev is not None:
			last_seen_rev = last_deleted_on_rev - 1
		else:
			last_seen_rev = latest_revision
		visual_rev = format % (added_on_rev, last_seen_rev)

		indent_print(visual_rev, ' /%s' % k)
		if k in ('branches', 'tags'):
			btl = level
		else:
			btl = branch_tag_level
		dump(children, revision_digits, latest_revision, level=level + 1, branch_tag_level=btl)


def hide_branch_and_tag_content(t, level=0, branch_tag_level=-2):
	for k, (added_on_rev, last_deleted_on_rev, children) in list(t.items()):
		if branch_tag_level + 1 == level:
			continue
		if k in ('branches', 'tags'):
			btl = level
		else:
			btl = branch_tag_level
		hide_branch_and_tag_content(children, level=level + 1, branch_tag_level=btl)


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


def main():
	# Command line interface
	from optparse import OptionParser
	from svneverever.version import VERSION_STR
	parser = OptionParser(usage=USAGE, version=VERSION_STR)
	(opts, args) = parser.parse_args()
	if len(args) != 1:
		parser.print_usage()
		sys.exit(1)
	REPO_URI = ensure_uri(args[0])


	# Build tree from repo
	client = pysvn.Client()
	tree = dict()
	try:
		latest_revision = client.info2(REPO_URI, recurse=False)[0][1]['last_changed_rev'].number
	except (pysvn.ClientError) as e:
		sys.stderr.write('ERROR: %s\n' % str(e))
		sys.exit(1)
	prev_percent = 0

	sys.stderr.write('Analyzing %d revisions...' % latest_revision)
	for rev in xrange(1, latest_revision + 1):
		# Indicate progress
		sys.stderr.write('.')
		sys.stderr.flush()
		percent = rev * 100 / latest_revision
		if (percent - prev_percent >= 5):
			prev_percent = percent
			text = ' %d%% (r%d)%s' % (percent, rev, (percent != 100) and '..' or '.')
			sys.stderr.write(text)

		summary = client.diff_summarize(
			REPO_URI,
			revision1=pysvn.Revision(pysvn.opt_revision_kind.number, rev - 1),
			url_or_path2=REPO_URI,
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

	sys.stderr.write('\n\n')
	sys.stderr.flush()

	# NOTE: Leaves are files and empty directories
	hide_branch_and_tag_content(tree)
	dump(tree, digit_count(latest_revision), latest_revision)


if __name__ == '__main__':
	main()

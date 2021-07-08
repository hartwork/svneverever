#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2021 Sebastian Pipping <sebastian@pipping.org>
# Copyright (C) 2011      Wouter Haffmans <wouter@boxplosive.nl>
# Copyright (C) 2019      Kevin Lane <kevin.lane84@outlook.com>
# Licensed under GPL v3 or later
#
from __future__ import print_function

import argparse
import getpass
import math
import os
import re
import signal
import sys
import time
from collections import namedtuple
from textwrap import dedent
from urllib.parse import quote as urllib_parse_quote

import pysvn

from .version import VERSION_STR

_EPILOG = """\
Please report bugs at https://github.com/hartwork/svneverever.  Thank you!
"""


_OsTerminalSize = namedtuple('_OsTerminalSize', ['columns', 'lines'])


class _SvnCheckoutDetected(ValueError):
    def __init__(self, repo_location):
        self._repo_location = repo_location

    def __str__(self):
        return (f'Directory {self._repo_location!r}'
                ' does not contain an SVN repository'
                ' but an SVN checkout.')


def _get_terminal_size_or_default():
    try:
        return int(os.environ['COLUMNS'])
    except (KeyError, ValueError):
        pass

    query_fd = os.get_terminal_size
    for fd in (0, 1, 2):
        try:
            return query_fd(fd)
        except Exception:
            pass

    try:
        fd = os.open(os.ctermid(), os.O_RDONLY)
        try:
            return query_fd(fd)
        finally:
            os.close(fd)
    except Exception:
        pass

    return _OsTerminalSize(columns=80, lines=24)


def _for_print(text):
    if sys.version_info >= (3, ):
        return text

    return text.encode(sys.stdout.encoding or 'UTF-8', 'replace')


def dump_tree(t, revision_digits, latest_revision, config,
              level=0, branch_level=-3, tag_level=-3, parent_dir=''):
    def indent_print(line_start, text):
        if config.flat_tree:
            level_text = parent_dir
        else:
            level_text = ' '*(4*level)
        if config.show_numbers:
            print('{}  {}{}'.format(line_start, level_text, _for_print(text)))
        else:
            print('{}{}'.format(level_text, _for_print(text)))

    items = ((k, v) for k, v in t.items() if k)

    if ((branch_level + 2 == level) and not config.show_branches) \
            or ((tag_level + 2 == level) and not config.show_tags) \
            or level >= config.max_depth:
        if items and config.show_dots:
            line_start = ' '*(1 + revision_digits + 2 + revision_digits + 1)
            if config.flat_tree:
                indent_print(line_start, '/[..]')
            else:
                indent_print(line_start, '[..]')
        return

    for k, (added_on_rev, last_deleted_on_rev, children) in sorted(items):
        format = '(%%%dd; %%%dd)' % (revision_digits, revision_digits)
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
        dump_tree(children, revision_digits, latest_revision, config,
                  level=level + 1, branch_level=bl, tag_level=tl,
                  parent_dir='{}/{}'.format(parent_dir, k))


def dump_nick_stats(nick_stats, revision_digits, config):
    if config.show_numbers:
        format = "%%%dd (%%%dd; %%%dd)  %%s" % (revision_digits,
                                                revision_digits,
                                                revision_digits)
        for nick, (first_commit_rev, last_commit_rev, commit_count) \
                in sorted(nick_stats.items()):
            print(format % (commit_count, first_commit_rev, last_commit_rev,
                            _for_print(nick)))
    else:
        for nick, (first_commit_rev, last_commit_rev, commit_count) \
                in sorted(nick_stats.items()):
            print(_for_print(nick))


def ensure_uri(text):
    svn_uri_detector = re.compile('^[A-Za-z+]+://')
    if svn_uri_detector.search(text):
        return text
    else:
        abspath = os.path.abspath(text)
        if os.path.exists(os.path.join(abspath, '.svn')):
            raise _SvnCheckoutDetected(abspath)
        return 'file://%s' % urllib_parse_quote(abspath)


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
    return ('%6.2f%%  (%02d:%02d:%02d remaining)  [%s%s]'
            % (percent, hr, mr, sr, '#'*fill_len, ' '*open_len))


def command_line():
    parser = argparse.ArgumentParser(
            prog='svneverever',
            description='Collects path entries across SVN history',
            epilog=_EPILOG,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            )
    parser.add_argument(
        '--version',
        action='version', version='%(prog)s ' + VERSION_STR)
    parser.add_argument(
        'repo_uri',
        metavar='REPOSITORY', action='store',
        help='Path or URI to SVN repository')

    modes = parser.add_argument_group('mode selection arguments')
    modes.add_argument(
        '--committers',
        dest='nick_stat_mode', action='store_true', default=False,
        help='Collect committer names instead of path information '
             '(default: disabled)')

    common = parser.add_argument_group('common arguments')
    common.add_argument(
        '--no-numbers',
        dest='show_numbers', action='store_false', default=True,
        help='Hide numbers, e.g. revision ranges (default: disabled)')
    common.add_argument(
        '--no-progress',
        dest='show_progress', action='store_false', default=True,
        help='Hide progress bar (default: disabled)')
    common.add_argument(
        '--non-interactive',
        dest='interactive', action='store_false', default=True,
        help='Will not ask for input (e.g. login credentials) if required'
             ' (default: ask if required)')

    path_tree_mode = parser.add_argument_group('path tree mode arguments')
    path_tree_mode.add_argument(
        '--tags',
        dest='show_tags', action='store_true', default=False,
        help='Show content of tag folders (default: disabled)')
    path_tree_mode.add_argument(
        '--branches',
        dest='show_branches', action='store_true', default=False,
        help='Show content of branch folders (default: disabled)')
    path_tree_mode.add_argument(
        '--no-dots',
        dest='show_dots', action='store_false', default=True,
        help='Hide "[..]" omission marker (default: disabled)')
    path_tree_mode.add_argument(
        '--depth',
        dest='max_depth', metavar='DEPTH', action='store',
        type=int, default=-1,
        help='Maximum depth to print (starting at 1)')
    path_tree_mode.add_argument(
        '--flatten',
        dest='flat_tree', action='store_true', default=False,
        help='Flatten tree (default: disabled)')

    committer_mode = parser.add_argument_group('committer mode arguments')
    committer_mode.add_argument(
        '--unknown-committer',
        dest='unknown_committer_name', metavar='NAME', default='<unknown>',
        help='Committer name to use for commits'
             ' without a proper svn:author property (default: "%(default)s")')

    args = parser.parse_args()

    if args.max_depth < 1:
        args.max_depth = sys.maxsize

    return args


def _login(realm, username, may_save, _tries):
    if _tries > 0:
        print('ERROR: Credentials not accepted by SVN, please try again.',
              file=sys.stderr)

    try:
        if username:
            print('Username: {}  (as requested by SVN)'.format(username),
                  file=sys.stderr)
        else:
            print('Username: ', end='', file=sys.stderr)
            username = input('')
        password = getpass.getpass('Password: ')
        print(file=sys.stderr)
        return True, username, password, False
    except (KeyboardInterrupt, EOFError):
        print(file=sys.stderr)
        print('Operation cancelled.', file=sys.stderr)
        sys.exit(128 + signal.SIGINT)


def _create_login_callback():
    tries = 0

    def login_with_try_counter(*args, **kvargs):
        nonlocal tries

        kvargs['_tries'] = tries
        try:
            return _login(*args, **kvargs)
        finally:
            tries += 1

    return login_with_try_counter


def _check_for_suitable_pysvn():
    if not hasattr(pysvn, 'ClientError'):
        print(dedent("""\
            ERROR: You need PySVN 1.x.x off SourceForge (https://pysvn.sourceforge.io/).
                   Package "pysvn" on PyPI is something else, unfortunately.
        """), file=sys.stderr)  # noqa: E501
        sys.exit(2)


def main():
    args = command_line()

    _check_for_suitable_pysvn()

    try:
        args.repo_uri = ensure_uri(args.repo_uri)
    except _SvnCheckoutDetected as e:
        print('ERROR: %s' % str(e), file=sys.stderr)
        sys.exit(3)

    # Build tree from repo
    client = pysvn.Client()
    if args.interactive:
        client.callback_get_login = _create_login_callback()
    tree = dict()
    try:
        latest_revision = client.info2(
            args.repo_uri, recurse=False)[0][1]['last_changed_rev'].number
    except (pysvn.ClientError) as e:
        if str(e) == 'callback_get_login required':
            print('ERROR: SVN Repository requires login credentials'
                  '. Please run without --non-interactive switch.',
                  file=sys.stderr)
        else:
            print('ERROR: %s' % str(e), file=sys.stderr)
        sys.exit(1)

    start_time = time.time()
    print('Analyzing %d revisions...' % latest_revision, file=sys.stderr)
    width = _get_terminal_size_or_default().columns

    def indicate_progress(rev, before_work=False):
        percent = rev * 100.0 / latest_revision
        seconds_taken = time.time() - start_time
        seconds_expected = seconds_taken / float(rev) * latest_revision
        if (rev == latest_revision) and not before_work:
            percent = 100
            seconds_expected = seconds_taken
        print('\r' + make_progress_bar(percent, width,
                                       seconds_taken, seconds_expected),
              end='', file=sys.stderr)
        sys.stderr.flush()

    nick_stats = dict()

    for rev in range(1, latest_revision + 1):
        if rev == 1 and args.show_progress:
            indicate_progress(rev, before_work=True)

        if args.nick_stat_mode:
            committer_name = client.revpropget(
                'svn:author', args.repo_uri,
                pysvn.Revision(pysvn.opt_revision_kind.number, rev))[1]
            if not committer_name:
                committer_name = args.unknown_committer_name
            (first_commit_rev, last_commit_rev, commit_count) \
                = nick_stats.get(committer_name, (None, None, 0))

            if first_commit_rev is None:
                first_commit_rev = rev
            last_commit_rev = rev
            commit_count = commit_count + 1

            nick_stats[committer_name] = (first_commit_rev, last_commit_rev,
                                          commit_count)

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
            return (summary_entry.summarize_kind
                    == pysvn.diff_summarize_kind.added
                    and summary_entry.node_kind == pysvn.node_kind.dir)

        def is_directory_deletion(summary_entry):
            return (summary_entry.summarize_kind
                    == pysvn.diff_summarize_kind.delete
                    and summary_entry.node_kind == pysvn.node_kind.dir)

        dirs_added = [e.path for e in summary if is_directory_addition(e)]
        for d in dirs_added:
            sub_tree = tree
            for name in d.split('/'):
                if name not in sub_tree:
                    added_on_rev, last_deleted_on_rev, children \
                        = rev, None, dict()
                    sub_tree[name] = (added_on_rev, last_deleted_on_rev,
                                      children)
                else:
                    added_on_rev, last_deleted_on_rev, children \
                        = sub_tree[name]
                    if last_deleted_on_rev is not None:
                        sub_tree[name] = (added_on_rev, None, children)
                sub_tree = children

        def mark_deleted_recursively(sub_tree, name, rev):
            added_on_rev, last_deleted_on_rev, children = sub_tree[name]
            if last_deleted_on_rev is None:
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
                    added_on_rev, last_deleted_on_rev, children \
                        = sub_tree[name]
                    sub_tree = children

        if args.show_progress:
            indicate_progress(rev)

    if args.show_progress:
        print(file=sys.stderr)
    print(file=sys.stderr)
    sys.stderr.flush()

    # NOTE: Leaves are files and empty directories
    if args.nick_stat_mode:
        dump_nick_stats(nick_stats, digit_count(latest_revision), config=args)
    else:
        dump_tree(tree, digit_count(latest_revision), latest_revision,
                  config=args)


if __name__ == '__main__':
    main()

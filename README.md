[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)


# About
**svneverever** helps you inspect the structure of a SVN repository and the changes made to it over time. Its most common use is in combination with [svn-all-fast-export](https://github.com/svn-all-fast-export/svn2git) (or "KDE's svn2git" if you wish).


# Installation

## Dependencies
**svneverever** requires Python 3.7 or higher
and [PySVN](https://pysvn.sourceforge.io/)
(the one on SourceForge, not the one on PyPI).
If you want to install **svneverever** with **pip** you need a few additional packages.
For Debian/Ubuntu the following should work:

```console
# sudo apt install python3-svn python3-pip
```

## System package manager
[Some distributions](https://repology.org/projects/?search=svneverever) offer a native package for **svneverever**:
- [Arch AUR](https://aur.archlinux.org/packages/python-svneverever/)
- [Funtoo](https://github.com/funtoo/dev-kit/tree/1.4-release/dev-vcs/svneverever)
- [Gentoo](https://packages.gentoo.org/packages/dev-vcs/svneverever)
- [openSUSE](https://software.opensuse.org/package/python-svneverever)

## pip
Install with pip as user to avoid messes with Python system files.
```console
# pip install --user svneverever
```

## From source
```console
# git clone https://github.com/hartwork/svneverever.git
# cd svneverever
# python3 setup.py install --user
# echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> ~/.bashrc
```

# Usage
**svneverever** needs the "server-side" of the repository with full history. There are two ways to obtain this. Let's take the SVN history of [headphone effect library bs2b](http://bs2b.sourceforge.net/) as an example.

The first way is to directly point **svneverever** to the server `svneverever svn://svn.code.sf.net/p/bs2b/code/`. However this is slow and it puts a lot of stress on the server, and will be little fun to run multiple times.

The second and recommended method is first downloading the history with
`svnrdump dump` (that comes with Subversion >=1.7) or [`rsvndump`](https://github.com/jgehring/rsvndump) (with a slightly [different feature set](https://rsvndump.sourceforge.io/) and supporting older versions of Subversion).
For this method we first need to use `svnadmin` to create an empty repository and then load the output of svnrdump/rsvndump into it. This can be done in the following way:

## With `svnrdump dump`

```console
# svnadmin create bs2b_svn_store

# time sh -c 'svnrdump dump svn://svn.code.sf.net/p/bs2b/code/ | svnadmin load bs2b_svn_store/'
[..]
real    0m3.008s
user    0m0.309s
sys     0m0.235s
```

## With `rsvndump`

```console
# svnadmin create bs2b_svn_store

# time sh -c 'rsvndump svn://svn.code.sf.net/p/bs2b/code/ | svnadmin load bs2b_svn_store/'
[..]
real    2m54.403s
user    0m1.003s
sys     0m1.300s
```

The output can now be obtained by pointing **svneverver** to the svn store directory `bs2b_svn_store`.

```console
# svneverever --no-progress bs2b_svn_store/
```

## Analyzing the output
The output of the direct method or the **rsvndump** method will be the same and looks like this:

```console
Analyzing 175 revisions...

(  1; 175)  /branches
( 66;  76)      /libbs2b-config-header
                    [..]
(  1; 175)  /tags
(109; 175)      /description
                    [..]
( 46; 175)      /libbs2b
                    [..]
( 28;  46)      /libbs2b-2.2.1
                    [..]
( 31; 175)      /plugins
                    [..]
(  1; 175)  /trunk
( 80; 175)      /description
( 80; 175)          /img
(  2; 175)      /libbs2b
(  2; 175)          /doc
(  2;  80)              /img
(  2;   6)              /src
(  4; 175)          /m4
(  2; 175)          /src
(  2; 175)          /win32
(  2; 175)              /bs2bconvert
(  2; 175)              /bs2bstream
(  2; 175)              /examples
(  2; 175)              /sndfile
(  2; 175)      /plugins
( 38; 175)          /audacious
( 38; 175)              /m4
( 38; 175)              /src
( 24; 175)          /foobar2000
(143; 175)          /ladspa
(144; 175)              /m4
(143; 175)              /src
( 39; 175)          /qmmp
(  2; 175)          /vst
(  2; 175)              /src
(  2; 175)                  /resources
(  2; 175)              /win32
(117; 175)          /winamp
(  2; 175)          /xmms
( 12; 175)              /m4
( 12; 175)              /src
```

The ranges on the left indicate at what revision folders appeared first and got deleted latest.

You can see a few things in this output:
* That a branch called `libbs2b-config-header` got deleted at revision 76.
* In which order plug-ins in `plugins` appeared over time.
* That tag `libbs2b-2.2.1` was deleted at the same revision that a tag folder `libbs2b` appeared.

The last item we can verify to see if it was _actually_ moved into that tag subfolder.

```console
# svneverever --no-progress --tags --flatten bs2b_svn_store/ | grep '2.2.1$'
Analyzing 175 revisions...

(110; 175)  /tags/description/2.2.1
( 47; 175)  /tags/libbs2b/2.2.1
( 28;  46)  /tags/libbs2b-2.2.1
```

Next I have a look at who the committers where, when they joined or left and how many commits the did (though that last number is of limited value). This can help to write an identity map for svn2git.

```console
# svneverever --no-progress --committers bs2b_svn_store/
Analyzing 175 revisions...

 81 (  1; 174)  boris_mikhaylov
 94 (  4; 175)  hartwork
```

# `--help` output
```console
# svneverever --help
usage: svneverever [-h] [--version] [--committers] [--no-numbers]
                   [--no-progress] [--non-interactive] [--tags] [--branches]
                   [--no-dots] [--depth DEPTH] [--flatten]
                   [--unknown-committer NAME]
                   REPOSITORY

Collects path entries across SVN history

positional arguments:
  REPOSITORY            Path or URI to SVN repository

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

mode selection arguments:
  --committers          Collect committer names instead of path information
                        (default: disabled)

common arguments:
  --no-numbers          Hide numbers, e.g. revision ranges (default: disabled)
  --no-progress         Hide progress bar (default: disabled)
  --non-interactive     Will not ask for input (e.g. login credentials) if
                        required (default: ask if required)

path tree mode arguments:
  --tags                Show content of tag folders (default: disabled)
  --branches            Show content of branch folders (default: disabled)
  --no-dots             Hide "[..]" omission marker (default: disabled)
  --depth DEPTH         Maximum depth to print (starting at 1)
  --flatten             Flatten tree (default: disabled)

committer mode arguments:
  --unknown-committer NAME
                        Committer name to use for commits without a proper
                        svn:author property (default: "<unknown>")

Please report bugs at https://github.com/hartwork/svneverever.  Thank you!
```

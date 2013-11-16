python-smartypants
------------------

SmartyPants is a tool for converting plain ASCII punctuation characters into
"smart" HTML entities, such as "straight" quotes into "curly" quotes and
"---" into em-dashes.

SmartyPants was originally written in Perl by John Gruber. See
http://daringfireball.net/projects/smartypants/.

Chad Miller then ported it to Python 
(http://web.chad.org/projects/smartypants.py/), and Hao Lian packaged it and
put it on PyPI (http://pypi.python.org/pypi/smartypants).

This version makes just one small tweak to the PyPI version. It adds the
``<tt>`` tag to the list of skipped tags. Since reStructuredText renders
inline literals as ``<tt>`` tags, this is important so as not to introduce
curly quotes into inline code snippets.

Jeff Schenck <http://jeffschenck.com/>

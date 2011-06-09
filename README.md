Dartmouth Last Chances
====================

A great tradition for seniors...?

Written by Ian Webster '11, [Hacker Club] project, for '11 Class Council.

Setup
-----

Everything in `/app` is written for Google App Engine.  The scripts in the `remote/` directory should be hosted off Google App Engine, probably on some machine that can be universally used for DND lookup because it is such a common need.

To perform matching as admin, go to the following URLs:

  - `/match`
  - `/mail`

Alternatively, just run `/match`, toggle the `RELEASE_MATCHES` flag, and tell everyone to go to the site.  Ideally, do both.


Resetting
---------

To reset everything, go to `/clearall` as admin.


TODO
----

  - remove/translate unicode chars in DND lookups
  - better way to add superseniors


  [Hacker Club]: http://hacktown.cs.dartmouth.edu/

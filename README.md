# tag
Organize, tag and search my library. Every once in a while, I export my own library (with a small number of omissions) [here](https://github.com/jadnohra/tag_export).

<img src="tag.png" width="450">

# Basic Usage Examples
 * A database is used to store the information, and a repository folder is used to hold the library's files.
 * The database can be set by the user, but if it not set, it is assumed to be the file 'tag.db' within the set repository.
 * ./tag.py -repo /foo/bar -add /Downloads/paper.pdf -tags "math,geom,[euclid]"
  * /Downloads/paper.pdf is copied to /foo/bar/paper.pdf and tagged with the three supplied tags
 * ./tag.py -repo /foo/bar -find geom
  * Prints a list of all files tagged 'geom'
 * ./tag.py -repo /foo/bar -name linear
  * Prints a list of all files whose name contains 'linear' (case insensitive)
 * ./tag.py -repo /foo/bar

  * Enters interactive mode which supports the following commands (requires a VT100 terminal for editing operations)
   * cd foo: Filters the library to files tagged with foo.
   * cd .. : Moves one filter back up the filter stack.
   * ls: Lists all files that pass the whole filter stack.
   * e i (where i is an integer from ls's output): edit the entry's name and/or tags.
   * + i foo,bar: adds 'foo' and 'bar' as tags to the i'th entry.
   * - i foo, bar: removes 'foo' and 'bar' from the i'th entry's tags.

* ./tag.py -repo /foo/bar -import /foo/bar2"
  * Imports (a batch -add) all files (of certain types) to the repository. It also preprocesses the file names into titles (although the name of the actual file is preserved in the file system):
    * Turning them into Title Case if they are all caps.
    * Separating them by spaces if they are camel-cased.
    * Detects tags and strips them if they are enclosed in parentheses, per example the file "(geom,[euclid]) TheElements.pdf" will get the name 'The Elements', with the tags 'geom', '[euclid]' and '.pdf'



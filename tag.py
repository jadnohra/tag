#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import sqlite3
import shutil
import json
import sys
import datetime
import os
import re
import time
import termios
import fcntl
import copy

# synonym: (lin-alg, l-lag)
# search: lin-alg:lvl-0 will match l-alg:(eigen, lvl-0)
# add, remove

Classif = { 'math' : { 'lin-alg' : { 'eigen' }, 'opt' : {} } }
Tags = { 'title' : 'test1', 'eigen' : {'lvl0':'', 'impl':''}, 'lvl1' : { 'lin-alg':'', 'opt':'' } }

def getch():
	fd = sys.stdin.fileno()

	oldterm = termios.tcgetattr(fd)
	newattr = termios.tcgetattr(fd)
	newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
	termios.tcsetattr(fd, termios.TCSANOW, newattr)

	oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
	fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

	c = []
	try:
		while len(c) == 0:
			try:
				while 1:
					c.append(sys.stdin.read(1))
				break
			except IOError: pass
	finally:
		termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
		fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
	return c

SMALL = 'a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v\.?|via|vs\.?'
PUNCT = "!\"#$%&'‘()*+,\\-./:;?@[\\\\\]_`{|}~"
SMALL_WORDS = re.compile(r'^(%s)$' % SMALL, re.I)
INLINE_PERIOD = re.compile(r'[a-z][.][a-z]', re.I)
UC_ELSEWHERE = re.compile(r'[%s]*?[a-zA-Z]+[A-Z]+?' % PUNCT)
CAPFIRST = re.compile(r"^[%s]*?([A-Za-z])" % PUNCT)
SMALL_FIRST = re.compile(r'^([%s]*)(%s)\b' % (PUNCT, SMALL), re.I)
SMALL_LAST = re.compile(r'\b(%s)[%s]?$' % (SMALL, PUNCT), re.I)
SUBPHRASE = re.compile(r'([:.;?!][ ])(%s)' % SMALL)
APOS_SECOND = re.compile(r"^[dol]{1}['‘]{1}[a-z]+$", re.I)
ALL_CAPS = re.compile(r'^[A-Z\s\d%s]+$' % PUNCT)
UC_INITIALS = re.compile(r"^(?:[A-Z]{1}\.{1}|[A-Z]{1}\.{1}[A-Z]{1})+$")
MAC_MC = re.compile(r"^([Mm]c)(\w.+)")
def titlecase(text, callback=None):
    """
    Titlecases input text
    This filter changes all words to Title Caps, and attempts to be clever
    about *un*capitalizing SMALL words like a/an/the in the input.
    The list of "SMALL words" which are not capped comes from
    the New York Times Manual of Style, plus 'vs' and 'v'.
    """
    lines = re.split('[\r\n]+', text);
    processed = []
    for line in lines:
        all_caps = ALL_CAPS.match(line)
        words = re.split('[\t ]', line)
        tc_line = []
        for word in words:
            if callback:
                new_word = callback(word, all_caps=all_caps)
                if new_word:
                    tc_line.append(new_word)
                    continue
            if all_caps:
                if UC_INITIALS.match(word):
                    tc_line.append(word)
                    continue
                else:
                    word = word.lower()
            if APOS_SECOND.match(word):
                if len(word[0]) == 1 and word[0] not in 'aeiouAEIOU':
                    word = word[0].lower() + word[1] + word[2].upper() + word[3:]
                else:
                    word = word[0].upper() + word[1] + word[2].upper() + word[3:]
                tc_line.append(word)
                continue
            if INLINE_PERIOD.search(word) or UC_ELSEWHERE.match(word):
                tc_line.append(word)
                continue
            if SMALL_WORDS.match(word):
                tc_line.append(word.lower())
                continue
            match = MAC_MC.match(word)
            if match:
                tc_line.append("%s%s" % (match.group(1).capitalize(),
                                         match.group(2).capitalize()))
                continue
            if "/" in word and "//" not in word:
                slashed = map(lambda t: titlecase(t,callback), word.split('/'))
                tc_line.append("/".join(slashed))
                continue
            if '-' in word:
                hyphenated = map(lambda t: titlecase(t,callback), word.split('-'))
                tc_line.append("-".join(hyphenated))
                continue
            # Just a normal word that needs to be capitalized
            tc_line.append(CAPFIRST.sub(lambda m: m.group(0).upper(), word))
        result = " ".join(tc_line)
        result = SMALL_FIRST.sub(lambda m: '%s%s' % (
            m.group(1),
            m.group(2).capitalize()
        ), result)
        result = SMALL_LAST.sub(lambda m: m.group(0).capitalize(), result)
        result = SUBPHRASE.sub(lambda m: '%s%s' % (
            m.group(1),
            m.group(2).capitalize()
        ), result)
        processed.append(result)
    return "\n".join(processed)

largv = []

def largv_has(keys):
	for i in range(len(keys)):
		 if (keys[i] in largv):
			return True
	return False

def largv_has_key(keys):
	for key in keys:
		ki = largv.index(key) if key in largv else -1
		if (ki >= 0 and ki+1 < len(largv)):
			return True
	return False

def largv_get(keys, dflt):
	if ( hasattr(sys, 'argv')):
		for key in keys:
			ki = largv.index(key) if key in largv else -1
			if (ki >= 0 and ki+1 < len(largv)):
				return largv[ki+1]
	return dflt

def largv_geti(i, dflt):
	if (i >= len(largv)):
		return dflt
	return largv[i]

gPrintCol = [ 'default', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'  ]
gPrintColCode = [ "\x1B[0m", "\x1B[31m", "\x1B[32m", "\x1B[33m", "\x1B[34m", "\x1B[35m", "\x1B[36m", "\x1B[37m"  ]
gAltCols = [ gPrintCol.index(x) for x in ['default', 'yellow'] ]
gPrintColI = 0

def print_coli(coli):
	global gPrintColI
	coli = coli % len(gPrintCol)
	gPrintColI = coli
	print gPrintColCode[coli],

def print_col(col):
	print_coli(gPrintCol.index(col))

g_repo = None
g_dbpath = None
g_dry = False

def unistr(str):
	if not isinstance(str, unicode):
		return unicode(str, "utf-8")
	return str

def matchTags(pat, tags):
	if (isinstance(pat, str)):
		for t in tags.keys():
			if (t == pat):
				return True
	return False

def matchName(pat, name):
	if (pat.lower() in name.lower()):
		return True
	return False

def genFileMD5Str(fpath, name):
	if (os.path.getsize(fpath) > 0):
		return str(hashlib.sha256(open(fpath, 'rb').read()).hexdigest())
	else:
		return '_' + str(hashlib.sha256(name).hexdigest())

def setDbLocation(location):
	global g_repo
	g_repo = location

def tagCleanFromName(name):
	p1, p2 = tagRe()
	cname = re.sub(p1, '', name)
	comps = [x.strip() for x in cname.split()]
	cname = ' '.join(comps)
	return cname

def camelCaseToSpace(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)

def stripFileName(name):
	if ('.' in name):
		f,e = os.path.splitext(name)
		f = f.strip()
		return f+e
	return name.strip()

def normalizeName(name):
	name = name.replace("_", " ")
	comps = [x.strip() for x in name.split()]
	name = ' '.join(comps)
	name = stripFileName(name)
	name = camelCaseToSpace(name)
	comps = [x.strip() for x in name.split()]
	name = ' '.join(comps)
	if (name.isupper()):
		name = titlecase(name)
	return name

def cleanFilename(name):
	return normalizeName(tagCleanFromName(name))

def makeCleanFilename(fpath):
	head, tail = os.path.split(fpath)
	return cleanFilename(tail)

def createEntry(fpath, tags):
	fname = makeCleanFilename(fpath)
	name,ext = os.path.splitext(fname)
	hashid = genFileMD5Str(fpath, fname)
	return { 'hashid':hashid, 'fname':fname, 'name':name, 'tags':tags, 'ts':datetime.datetime.now() }

def dbBootstrap(conn):
	conn.execute('CREATE TABLE file_entries(hashid TEXT PRIMARY KEY, fname TEXT, name TEXT, tags TEXT, ts TIMESTAMP)')
	conn.commit()

def dbStartSession(dbPath):
	conn = None
	if (dbPath is not None):
		tail, head = os.path.split(dbPath)
		if (not os.path.isdir(tail)):
			os.makedirs(tail)
		conn = sqlite3.connect(dbPath)
		if 1:
			tableListQuery = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY Name"
			cursor = conn.execute(tableListQuery)
			tables = map(lambda t: t[0], cursor.fetchall())
			cursor.close()
			if (len(tables) == 0):
				dbBootstrap(conn)
	else:
		conn = sqlite3.connect(":memory:")
		dbBootstrap(conn)
	return conn

def dbEndSession(conn):
	if conn is None:
		return 0
 	conn.close()

def dbUpgrade(conn):
	#conn.execute("alter table file_entries add column 'extra' 'TEXT'")
	#conn.commit()
	return 0

def dbAddEntry(conn, entry):
	tag_str = json.dumps( entry['tags'] )
	conn.execute("INSERT INTO file_entries VALUES (?,?,?,?,?,?)", (entry['hashid'], unistr(entry['fname']), unistr(entry['name']), tag_str, entry['ts'], ','.join(entry['extra']) ) )
	conn.commit()

def dbRemoveEntry(conn, entry):
	conn.execute("DELETE FROM file_entries WHERE hashid=?", (entry['hashid'], ) )
	conn.commit()

def dbExistsEntry(conn, entry):
	ret = []
	recs = conn.execute('SELECT * FROM file_entries WHERE hashid=?', (entry['hashid'], ) )
	rec = recs.fetchone()
	recs.close()
	return (rec != None)

def dbUpdateEntryFName(conn, entry):
	conn.execute('UPDATE file_entries SET fname=? WHERE hashid=?', (entry['fname'], entry['hashid'], ) )
	conn.commit()

def dbUpdateEntryName(conn, entry):
	conn.execute('UPDATE file_entries SET name=? WHERE hashid=?', (entry['name'], entry['hashid'], ) )
	conn.commit()

def dbUpdateEntry(conn, entry):
	dbRemoveEntry(conn, entry)
	dbAddEntry(conn, entry)

def dbRecToEntryIndexed(rec):
	rec_extra = rec[5] if rec[5] is not None else ''
	entry = { 'hashid':rec[0], 'fname':unistr(rec[1]), 'name':unistr(rec[2]), 'tags':json.loads(rec[3]), 'ts':rec[4], 'extra':rec_extra.split(',') }
	return entry

def dbGetEntries(conn):
	ret = []
	recs = conn.execute('SELECT * FROM file_entries')
	rec = recs.fetchone()
	while (rec != None):
		entry = dbRecToEntryIndexed(rec)
		ret.append(entry)
		rec = recs.fetchone()
	recs.close()
	return ret

def dbGetEntryByHash(conn, hashid):
	ret = []
	recs = conn.execute('SELECT * FROM file_entries WHERE hashid=?', (hashid, ) )
	rec = recs.fetchone()
	entry = None
	if (rec != None):
		entry = dbRecToEntryIndexed(rec)
	recs.close()
	return entry

def flattags(tags):
	return tags.keys()

def printEntry(entry, nice = True):
	if nice:
		print entry['name'],
		print_col('yellow'); print ','.join(flattags(entry['tags'])); print_col('default');
	else:
		print entry['hashid'], entry['fname'], entry['ts'], entry['name'], entry['tags']

def editEntry(entry, ename = True, etags = True):
	def finalizeName(entry, name):
		if (name != entry['name']):
			print name
			entry['name'] = name
			return True
		return False
	def finalizeTags(entry, tag_str):
		tagsa = [x.strip() for x in tag_str.split(',')]
		tags = {}
		for tag in tagsa:
			tags[tag] = ''
		if (entry['tags'] != tags):
			print flattags(tags)
			entry['tags'] = tags
			return True
		return False
	try:
		if (ename and etags):
			entry_str = '{{{}}}{{{}}}'.format(entry['name'], ','.join(flattags(entry['tags'])))
		elif (ename):
			entry_str = entry['name']
		elif (etags):
			entry_str = ','.join(flattags(entry['tags']))
		else:
			return False

		cpos = 0
		it = 0
		print ' - {}'.format(entry_str)
		prefix = ' : '
		print_col('yellow')
		while 1:
			# http://www.termsys.demon.co.uk/vtansi.htm
			print '\x1B[2K', # Erase line
			print '\r{}{}\r'.format(prefix, entry_str),
			print '\r\x1B[{}C'.format(cpos + len(prefix)),
			it = it+1
			inp = getch()

			if ('\n' in inp):
				break

			if (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'A']):
				app = 'up'
			elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'B']):
				app = 'down'
			elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'C']):
				cpos = min(cpos + 1, len(entry_str))
			elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'D']):
				cpos = max(cpos - 1, 0)
			elif (len(inp) >= 1 and inp[0] == '\x7F'):
				if (cpos > 0):
					entry_str = entry_str[0:cpos-1] + entry_str[cpos:]
					cpos = cpos-1
			elif (len(inp)==1):
				entry_str = entry_str[0:cpos] + ''.join(inp) + entry_str[cpos:]
				cpos = cpos + 1
			else:
				print inp
	except:
		e = sys.exc_info()[0]
		raise e
		return False
	finally:
		print_col('default')
		print ''

	if (ename and etags):
		re_pat = re.compile(ur'\{([^\}]*)\}')
		re_mat = re.findall(re_pat, entry_str)
		if (len(re_mat) == 2):
			modn = finalizeName(entry, re_mat[0])
			modt = finalizeTags(entry, re_mat[1])
			return (modn or modt)
		return False
	elif (ename):
		return finalizeName(entry, entry_str)
	elif (etags):
		return finalizeTags(entry, entry_str)
	return False


def editUpdateEntry(conn, entry, ename, etags):
	modded = editEntry(entry, ename, etags)
	if (modded):
		dbUpdateEntry(conn, entry)
		entry = dbGetEntryByHash(conn, entry['hashid'])
		print_col('green'); printEntry(entry); print_col('default');


def addFile(sess, conn, fpath, tags, copy):
	entry = createEntry(fpath, tags)
	return addEntry(sess, conn, fpath, entry, copy)

def addEntry(sess, conn, fpath, entry, copy):
	def addIgnored(sess, key, fpath):
		if (key not in sess):
			sess[key] = []
		sess[key].append(fpath)

	if (g_repo is not None):
		if (not os.path.isdir(g_repo)):
			os.makedirs(g_repo)
		if (copy == True):
			tpath = os.path.join(g_repo, entry['fname'])
			if (os.path.isfile(tpath)):
				thashid = genFileMD5Str(tpath, makeCleanFilename(tpath))
				if (thashid == entry['hashid']):
					addIgnored(sess, 'ignored', fpath)
					return None
				print 'File name clash [{}], edit? [ y(es), n(o) ]:'.format(entry['fname']),
				inp = raw_input()

				if (inp.lower() in ['y', 'yes']):
					if (editEntry(entry, True, False)):
						return addEntry(sess, conn, fpath, entry, copy)
				addIgnored(sess, 'clashed', fpath)
				return None
			#print_col('green'); print 'Copy [{}]->[{}]'.format(fpath, tpath); print_col('default');
			shutil.copyfile(fpath, tpath)
	if True:
		if (dbExistsEntry(conn, entry)):
			addIgnored(sess, 'ignored', fpath)
			return None
		dbAddEntry(conn, entry)
	return entry

def listAll(conn):
	entries = dbGetEntries(conn)
	for e in entries:
		printEntry(e)


def enter_assisted_input():

	def filterEntries(entries, filters):
		filtered = []
		for e in entries:
			fpass = True
			for f in filters:
				if (fpass):
					if (f['type'] == 'name'):
						fpass = fpass and matchName(f['pat'], e['name'])
					elif (f['type'] == 'tag'):
						fpass = fpass and matchTags(f['pat'], e['tags'])
				else:
					break
			if (fpass):
				filtered.append(e)
		return filtered

	def sortEntries(entries):
		return sorted(entries, key = lambda x : (x['name']))

	conn = dbStartSession(g_dbpath)
	filters = []; entries = [sortEntries(dbGetEntries(conn))];

	while True:
		pats = [x['pat'] for x in filters]
		print '/{} ({})>'.format('/'.join(pats), len(entries[-1])),
		inp = raw_input()
		input_splt = inp.split(' ')
		cmd = input_splt[0]

		if (cmd == 'q'):
			break
		elif (cmd == 'r' or cmd == 'reset'):
			filters = []; entries = [sortEntries(dbGetEntries(conn))];
		elif (cmd == 'ls' or cmd == 'l'):
			for ie in range(len(entries[-1])):
				print '{}. '.format(ie),
				printEntry(entries[-1][ie]);
		elif (cmd == 'tags' or cmd == 't'):
			tags = {}
			for e in entries[-1]:
				etags = flattags(e['tags'])
				for etag in etags:
					tags[etag] = ''
			tkeys = tags.keys()
			for it in range(len(tkeys)):
				print '{}, '.format(tkeys[it]),
				if (it % 10 == 0 and it != 0):
					print ''
			print '\n{} tags\n'.format(len(tkeys))
		elif ((cmd == 'cd' and len(input_splt) == 1)
				or (cmd == 'cd' and input_splt[1] == '..')
				or cmd == '..'
				or cmd == 'cd..'):
			if (len(filters)):
				filters.pop(); entries.pop();
		elif (cmd == 'cd'):
			if (len(input_splt) == 2):
				tag = input_splt[1]
				filter = {'type':'tag', 'pat':tag}
				filters.append(filter)
				entries.append( sortEntries( filterEntries(entries[-1], [filter]) ) )
		elif (cmd == 'e' or cmd == 'en' or cmd == 'et'):
			if (len(input_splt) == 2):
				ei = int(input_splt[1])
				entry = entries[-1][ei]
				editUpdateEntry(conn, entry, cmd == 'e' or cmd == 'en', cmd == 'e' or cmd == 'et')
		elif (cmd == 'cleanup'):
			centries = [x for x in entries[-1] if ('c' not in x['extra']) ]
			print 'There are {} entries to clean.'.format(len(centries))
			for ie in range(len(centries)):
				print '{}. '.format(ie),
				entry = centries[ie]
				editUpdateEntry(conn, entry, True, True)
				entry['extra'].append('c')
				dbUpdateEntry(conn, entry)
		elif (cmd == '+' or cmd == '-'):
			if (len(input_splt) == 3):
				ei = int(input_splt[1])
				entry = entries[-1][ei]
				ntags = input_splt[2].split(',')
				etags = copy.deepcopy(entry['tags'])
				for ntag in ntags:
					if (cmd == '+'):
						entry['tags'][ntag] = ''
					else:
						if ntag in entry['tags']:
							del entry['tags'][ntag]
				modded = (etags != entry['tags'])
				if (modded):
					print_col('green'); printEntry(entry); print_col('default');

	dbEndSession(conn)
	return 0

def tagAdd(conn, fpath, ltags, jtags = None):
	if (len(fpath) == 0):
		return
	tags = {}
	if (ltags is not None):
		ltags = [x.strip() for x in ltags]
		for ltag in ltags:
			tags[ltag] = ''
	elif (jtags is not None):
		tags = json.loads( jtags )
	tags[os.path.splitext(fpath)[1]] = ''
	entry = addFile(None, conn, fpath, tags, True)
	if (entry is not None):
		editUpdateEntry(conn, entry, True, True)
	return entry

def tagFind(conn, pat):
	entries = dbGetEntries(conn)
	for e in entries:
		if matchTags(pat, e['tags']):
			printEntry(e)

def nameFind(conn, pat):
	entries = dbGetEntries(conn)
	for e in entries:
		if matchName(pat, e['name']):
			printEntry(e)
	print ''

def tagList(conn):
	entries = dbGetEntries(conn)
	for e in entries:
		printEntry(e)
	print ''

def tagRe():
	p1 = re.compile(ur'\(([\w|,|\s|\-|\]|\[)]*)\)')
	p2 = re.compile(ur'\[([\w|,|\s|\-)]*)\]')
	return p1, p2

def matchesRe(name, rec):
	matches1 = []
	for y in re.findall(rec, name):
		matches1 = matches1 + [ x.strip() for x in y.split(',') ]
	return matches1

def tagImport(conn, ipath, updating):
	if (len(ipath) == 0):
		return
	addFileSess = {}
	p1, p2 = tagRe()
	for dirName, subdirList, fileList in os.walk(ipath):
		dirNameTail, dirNameHead = os.path.split(dirName)
		if (dirNameHead.startswith('.') == False and dirNameHead.startswith('_') == False):
			for fname in fileList:
				fname_, fext = os.path.splitext(fname)
				if (fname.startswith('.') == False and fext.lower() in ['.pdf', '.djvu', '.txt', '.md', '.jpg', '.jpeg', '.png', '.missing']):
					fpath = os.path.join(os.path.join(ipath, dirName), fname)
					ltags1 = matchesRe(fpath, p1); ltags2 = matchesRe(fpath, p2);
					tags = {}
					for ltag in ltags1:
						tags[ltag] = ''
					for ltag in ltags2:
						tags['[{}]'.format(ltag).lower()] = ''
					tags[fext] = ''
					if (os.path.getsize(fpath) == 0 and fext != '.missing'):
						if (updating == False):
							print_col('cyan'); print fname; print_col('default');
					else:
						entry = addFile(addFileSess, conn, fpath, tags, True)
						if (entry):
							printEntry(entry)
						elif (updating == False):
							print_col('red'); print fname; print_col('default');
							entry = dbGetEntryByHash(conn, genFileMD5Str(fpath, makeCleanFilename(fpath)))
							if (entry):
								print ' > ',
								printEntry(entry)
				else:
					if (updating == False):
						print_col('cyan'); print fname; print_col('default');
		else:
			if (updating == False):
				print_col('cyan'); print '{}/*'.format(dirName); print_col('default');


def tagCleanFromNames(conn):
	def tagCleanFromString(entry, key):
		cname = tagCleanFromName(entry[key])
		if (cname != entry[key]):
			print u'[{}] -> [{}]'.format(entry[key], cname)
			if (g_dry == False):
				entry[key] = cname
				if (key == 'fname'):
					dbUpdateEntryFName(conn, entry)
				else:
					dbUpdateEntryName(conn, entry)

	entries = dbGetEntries(conn)
	for e in entries:
		tagCleanFromString(e, 'fname')
		tagCleanFromString(e, 'name')
	print ''

def normalizeNames(conn):
	def normalizeString(entry, key):
		cname = normalizeName(entry[key])
		if (cname != entry[key]):
			print u'[{}] -> [{}]'.format(entry[key], cname)
			if (g_dry == False):
				entry[key] = cname
				if (key == 'fname'):
					dbUpdateEntryFName(conn, entry)
				else:
					dbUpdateEntryName(conn, entry)

	entries = dbGetEntries(conn)
	for e in entries:
		normalizeString(e, 'fname')
		normalizeString(e, 'name')
	print ''


def main():
	global largv
	global g_dbpath
	global g_dry
	global g_repo

	largv = sys.argv

	#print sys.stdout.encoding
	print_col('default'); print '';

	if largv_has(['-db']):
		g_dbpath = largv_get(['-db'], None)
	if largv_has(['-repo']):
		g_repo = largv_get(['-repo'], None)
	if (g_repo is not None and g_dbpath is None):
		g_dbpath = os.path.join(g_repo, 'tag.db')
	if largv_has(['-dry']):
		g_dry = True

	if largv_has(['-add']):
		fpath = largv_get(['-add'], '')
		ltags = largv_get(['-tags'], None)
		if (ltags is not None):
			ltags = [x.strip() for x in ltags.split(',')]
		jtags = json.loads( largv_get(['-jtags'], None))
		entry = None
		conn = dbStartSession(g_dbpath); entry = tagAdd(conn, fpath, ltags, jtags); dbEndSession(conn);
		if (entry is not None):
			if (largv_has(['-x'])):
				os.remove(fpath)
	elif largv_has(['-find', '-tag']):
		pat = largv_get(['-find', '-tag'], 'n/a')
		conn = dbStartSession(g_dbpath); tagFind(conn, pat); dbEndSession(conn);
	elif largv_has(['-name']):
			pat = largv_get(['-name'], 'n/a')
			conn = dbStartSession(g_dbpath); nameFind(conn, pat); dbEndSession(conn);
	elif largv_has(['-list']):
		conn = dbStartSession(g_dbpath); tagList(conn); dbEndSession(conn);
	elif largv_has(['-import']):
		ipath = largv_get(['-import'], '')
		updating = largv_has(['-u', '-update'])
		conn = dbStartSession(g_dbpath); tagImport(conn, ipath, updating); dbEndSession(conn);
	elif largv_has(['-test_normalize']):
		print normalizeName(largv_get(['-test_normalize'], ''))
	elif largv_has(['-test_clean']):
		print cleanFilename(largv_get(['-test_clean'], ''))
	elif largv_has(['-db_upgrade']):
			conn = dbStartSession(g_dbpath); dbUpgrade(conn); dbEndSession(conn);
	else:
		enter_assisted_input()

main()

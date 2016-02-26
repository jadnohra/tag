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
import subprocess
import traceback
import threading
import multiprocessing
import math

#https://docs.python.org/2/library/plistlib.html
#http://apple.stackexchange.com/questions/194503/where-is-preview-storing-the-data-to-reopen-a-pdf-at-the-last-page-os-x-lion
# synonym: (lin-alg, l-lag)
# search: lin-alg:lvl-0 will match l-alg:(eigen, lvl-0)
# add, remove

Classif = { 'math' : { 'lin-alg' : { 'eigen' }, 'opt' : {} } }
Tags = { 'title' : 'test1', 'eigen' : {'lvl0':'', 'impl':''}, 'lvl1' : { 'lin-alg':'', 'opt':'' } }


def init_getch():
	def init_getch_win():
		from msvcrt import getch as win_getch
		return win_getch
	def init_getch_posix():
		import tty,sys,termios
		def posix_getch():
			fd = sys.stdin.fileno(); old_settings = termios.tcgetattr(fd);
			try:
				tty.setraw(sys.stdin.fileno());	ch = sys.stdin.read(1);
			finally:
				termios.tcsetattr(fd, termios.TCSADRAIN, old_settings);
				if ord(ch) == 13:
					return '\n'
				elif ch == '\x1B':
					return [ch, posix_getch(), posix_getch()]
				else:
					return ch
		return posix_getch
	impls = [init_getch_win, init_getch_posix]
	for impl in impls:
		try:
			return impl()
		except:
			#traceback.print_exc()
			pass
	return None
getch = init_getch()

def vt_hist_create():
	return { 'list':[], 'max':30, 'index':0  }

def vt_hist_add(hist, item, max = 30):
	if item not in hist:
		hist.append(item)
	if len(hist) > max:
		hist.remove(0)

def vt_edit(prefix, initial, hist = None):
	inpchars = [x for x in initial]
	while True:
		print '\x1B[2K', '\r{} {}'.format(prefix, ''.join(inpchars)),
		pre_inp = getch()
		#print '[{}]'.format(pre_inp[0] == '\x1B')
		if (len(pre_inp) >= 3 and pre_inp[0:3] == ['\x1B', '[', 'A'] and hist):
			if (hist['index'] >= -len(hist['list'])):
				hist['index'] = hist['index']-1
			if (hist['index'] >= -len(hist['list'])):
				inpchars = [x for x in hist['list'][hist['index']]]
			else:
				inpchars = []
		elif (len(pre_inp) >= 3 and pre_inp[0:3] == ['\x1B', '[', 'B']):
			if (hist['index'] <= -1):
				hist['index'] = hist['index']+1
			if (hist['index'] < 0):
				inpchars = [x for x in hist['list'][hist['index']]]
			else:
				inpchars = []
		if len(pre_inp) == 1:
			if ('\n' in pre_inp):
				sys.stdout.write('\n')
				break
			else:
				for x in pre_inp:
					if x == '\x7F':
						if len(inpchars):
							inpchars.pop()
					else:
						inpchars.append(x)
	return ''.join(inpchars)

def vt_edit2(prefix, items, sep_back = 'bwhite', type_back = {}, sel_back = 'bblue', edit_back = 'bred'):
	def cprint(str, lpos):
		print str,;	return lpos + len(str);
	def bcol(item, type_back):
		return type_back.get( item.get('type', ''), 'bcyan')
	try:
		ipos = 0
		lipos = -1
		epos = -1
		while 1:
			lpos = 0
			sys.stdout.write('\x1B[2K'); sys.stdout.write('\r');
			lpos = cprint('{}'.format(prefix), lpos)
			for iti in range(len(items)):
				print_col(sep_back); lpos = cprint(' ', lpos);
				print_col( bcol(items[iti], type_back) if (iti != ipos) else sel_back if (epos == -1) else edit_back)
				items[iti]['lpos'] = lpos+1
				lpos = cprint(u' {} '.format(items[iti]['str']), lpos)
			print_col('bdefault')
			sys.stdout.write('\r')
			if (epos != -1):
				sys.stdout.write('\r\x1B[{}C'.format(items[ipos]['lpos'] + epos))
			inp = getch()
			if (epos == -1):
				if (len(inp) == 1 and ord(inp[0]) == 27):
					break
				elif ('\n' in inp):
					if (lipos == ipos):
						break
					else:
						epos = 0
				elif ('q' in inp):
					break
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'C']):
					ipos = min(ipos + 1, len(items)-1)
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'D']):
					ipos = max(ipos - 1, 0)
				elif (len(inp)==1):
					char = inp[0]
					if (True and (ord(char) >= 32 and ord(char) <= 126)):
						ipos = ipos
					elif (ord(char) == 9):
						ipos = min(ipos + 1, len(items)-1)
					#else:
					#	print 'xxx'; print 'xxx'
			else:
				edit_str = items[ipos]['str']
				if (len(inp) == 1 and ord(inp[0]) == 27):
					epos = -1
					lipos = ipos
				elif ('\n' in inp):
					epos = -1
					lipos = ipos
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'C']):
					epos = min(epos + 1, len(edit_str))
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'D']):
					epos = max(epos - 1, 0)
				elif (len(inp) >= 1 and inp[0] == '\x7F'):
					if (epos > 0):
						edit_str = edit_str[0:epos-1] + edit_str[epos:]
						epos = epos-1
				elif (len(inp)==1):
					char = inp[0]
					if ((ord(char) >= 32 and ord(char) <= 126)):
						edit_str = edit_str[0:epos] + ''.join(inp) + edit_str[epos:]
						epos = epos + 1
				items[ipos]['str'] = edit_str
	except:
		traceback.print_exc()
		e = sys.exc_info()[0]
		raise e
		return False
	finally:
		print_col('default')
		print ''
	return True

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

def is_int(str):
	try:
		i = int(str); return True;
	except ValueError:
		return False

def runUnpiped(args):
	subprocess.Popen(args)

def runPiped(args):
	proc = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	return proc.communicate()

def runPipedShell(args):
	proc = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
	return proc.communicate()

gPrintCol = [ 'default', 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', 'bdefault', 'bblack', 'bred', 'bgreen', 'byellow', 'bblue', 'bmagenta', 'bcyan', 'bwhite'  ]
gPrintColCode = [ "\x1B[0m", "\x1B[30m", "\x1B[31m", "\x1B[32m", "\x1B[33m", "\x1B[34m", "\x1B[35m", "\x1B[36m", "\x1B[37m",
"\x1B[49m", "\x1B[40m", "\x1B[41m", "\x1B[42m", "\x1B[43m", "\x1B[44m", "\x1B[45m", "\x1B[46m", "\x1B[47m", ]
gAltCols = [ gPrintCol.index(x) for x in ['default', 'yellow'] ]

def print_coli(coli):
	coli = coli % len(gPrintCol)
	code = gPrintColCode[coli]
	sys.stdout.write(code)
	#sys.stdout.write('\x1B[{}D'.format(len(code)-3))

def print_col(col):
	print_coli(gPrintCol.index(col))


g_repo = None
g_dbpath = None
g_dry = False
g_lastscan = None

def unistr(str):
	if not isinstance(str, unicode):
		return unicode(str, "utf-8")
	return str

def matchTags(pat, tags):
	#if (isinstance(pat, str)):
	if (True):
		for t in tags.keys():
			if (t == pat):
				return True
	return False

def matchName(pat, name):
	if (pat.lower() in name.lower()):
		return True
	return False

def dmy_as_date(d,m,y):
	try:
		return datetime.datetime(int(y), time.strptime(m,'%b').tm_mon, int(d)).date()
	except:
		return datetime.datetime(int(y), int(m), int(d)).date()

def fixupTimePat(pat):
	pat = pat.strip()
	if len(pat) == 0:
		return 'today'
	if (pat in ['today']):
		return pat
	if (True or '-' in pat or ' ' in pat):
		pat_splt = pat.split('-') if '-' in pat else pat.split()
		if len(pat_splt) == 1:
			pat_splt.append(str(datetime.datetime.today().month))
		if len(pat_splt) == 2:
			pat_splt.append(str(datetime.datetime.today().year))
		try:
			if (len(pat_splt) == 3):
				dmy_as_date(*pat_splt)
			elif (len(pat_splt) == 6):
				dmy_as_date(*pat_splt[:3]); dmy_as_date(*pat_splt[3:]);
			else:
				return ''
			return '-'.join(pat_splt)
		except:
			return ''
	return ''

def matchTime(pat, ts):
	pat_splt = pat.split('-')
	if (len(pat_splt) == 3):
		return ts.date() == dmy_as_date(*pat_splt)
	elif (len(pat_splt) == 6):
		return ts.date() >= dmy_as_date(*pat_splt[:3]) and ts.date() <= dmy_as_date(*pat_splt[3:])
	elif pat == 'today':
		return ts.date() == datetime.datetime.today().date()
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

def createFileHash(fpath):
	fname = makeCleanFilename(fpath)
	name,ext = os.path.splitext(fname)
	hashid = genFileMD5Str(fpath, fname)
	return hashid

def createEntry(fpath, tags):
	fname = makeCleanFilename(fpath)
	name,ext = os.path.splitext(fname)
	hashid = genFileMD5Str(fpath, fname)
	return { 'hashid':hashid, 'fname':fname, 'name':name, 'tags':tags, 'ts':datetime.datetime.now(), 'extra':'', 'link_id':'' }

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
	#conn.execute("alter table file_links add column 'link_type' 'TEXT'")
	#conn.execute('DROP TABLE file_notes')
	#conn.execute('CREATE TABLE file_notes(note_id INTEGER PRIMARY KEY AUTOINCREMENT, link_id TEXT, loc TEXT, descr TEXT, ts TIMESTAMP)')
	#conn.execute('CREATE INDEX manual_index_file_links_1 on file_links (link_from, link_to)')
	#conn.execute("alter table file_entries add column 'link_id' 'TEXT'")
	conn.commit()
	return 0

def dbAddLink(conn, frm, to, tp, descr):
	conn.execute("INSERT INTO file_links VALUES (?,?,?,?,?,?)", (None, frm, to, tp, descr, datetime.datetime.now() ) )
	conn.commit()

def dbUpdateLink(conn, link):
	conn.execute('UPDATE file_links SET link_from=?, link_to=?, link_type=?, descr=?, ts=? WHERE link_id=?', (link[1], link[2], link[3], link[4], link[5], link[0],) )
	conn.commit()

def dbAddNote(conn, link_id, loc, descr):
	conn.execute("INSERT INTO file_notes VALUES (?,?,?,?,?)", (None, link_id, loc, descr, datetime.datetime.now() ) )
	conn.commit()

def dbUpdateNote(conn, note):
	conn.execute('UPDATE file_notes SET link_id=?, loc=?, descr=?, ts=? WHERE note_id=?', (note[1], note[2], note[3], note[4], note[0],) )
	conn.commit()

def dbAddEntry(conn, entry):
	entry['tags'] = listToTags(entry['tags'])
	tag_str = json.dumps( entry['tags'] )
	conn.execute("INSERT INTO file_entries VALUES (?,?,?,?,?,?,?)", (entry['hashid'], unistr(entry['fname']), unistr(entry['name']), tag_str, entry['ts'], ','.join(entry['extra']), entry['link_id'] ) )
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

def dbUpdateEntryLinkId(conn, entry):
	conn.execute('UPDATE file_entries SET link_id=? WHERE hashid=?', (entry['link_id'], entry['hashid'], ) )
	conn.commit()

def dbUpdateEntry(conn, entry):
	dbRemoveEntry(conn, entry)
	dbAddEntry(conn, entry)

def dbRecToEntryIndexed(rec):
	rec_extra = rec[5] if rec[5] is not None else ''
	rec_link_id = rec[6] if rec[6] is not None else ''
	entry = { 'hashid':rec[0], 'fname':unistr(rec[1]), 'name':unistr(rec[2]),
				'tags':listToTags(json.loads(rec[3])), 'ts':datetime.datetime.strptime(rec[4], "%Y-%m-%d %H:%M:%S.%f"),
				'extra':rec_extra.split(','),
				'link_id':rec_link_id }
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

def dbGetLinkFull(conn, link_id):
	recs = conn.execute('SELECT link_id, link_from, link_to, link_type, descr, ts FROM file_links WHERE link_id=?', (link_id, ) )
	rec = recs.fetchone()
	recs.close()
	return rec

def dbGetNoteFull(conn, note_id):
	recs = conn.execute('SELECT note_id, link_id, loc, descr, ts FROM file_notes WHERE note_id=?', (note_id, ) )
	rec = recs.fetchone()
	recs.close()
	return rec

def dbGetLinkPartners(conn, from_link_id, show_link_descr = False):
	rets = ([], []); conds = ('link_from', 'link_to');
	for i in range(len(conds)):
		cond = conds[i]
		recs = conn.execute('SELECT link_id, link_from, link_to, link_type {} FROM file_links WHERE {}=?'.format(', descr' if show_link_descr else '', cond), (from_link_id, ) )
		rec = recs.fetchone()
		while (rec != None):
			rets[i].append(rec)
			rec = recs.fetchone()
		recs.close()
	return rets

def dbHasLinks(conn, link_id):
	ret = False; conds = ('link_from', 'link_to');
	for i in range(len(conds)):
		cond = conds[i]
		recs = conn.execute('SELECT link_id FROM file_links WHERE {}=?'.format(cond), (link_id, ))
		rec = recs.fetchone(); ret = ret or rec != None; recs.close();
	return ret

def dbHasNotes(conn, link_id):
	ret = []
	recs = conn.execute('SELECT note_id FROM file_notes WHERE link_id=?', (link_id, ) )
	rec = recs.fetchone(); recs.close(); return rec != None;

def dbGetNotes(conn, link_id, show_note_descr = False):
	ret = []
	recs = conn.execute('SELECT note_id, loc{} FROM file_notes WHERE link_id=?'.format(', descr' if show_note_descr else ''), (link_id, ) )
	rec = recs.fetchone()
	while (rec != None):
		ret.append(rec)
		rec = recs.fetchone()
	recs.close()
	return ret

def dbGetLinkPartnerStrings(conn, link_id, show_link_descr = False):
	def format_descr_has(x, show_link_descr):
		return ' ({})'.format(x[4]) if len(x[4]) else ''
	def format_descr(x, show_link_descr):
		return format_descr_has(x, show_link_descr) if show_link_descr else ''
	ret1, ret2 = dbGetLinkPartners(conn, link_id, show_link_descr)
	ret = []
	ret.extend(['{} {}{}'.format(x[3], x[2], format_descr(x, show_link_descr)) for x in ret1])
	ret.extend(['{} {}{}'.format(x[1], x[3], format_descr(x, show_link_descr)) for x in ret2])
	return ret

def dbGetNoteStrings(conn, link_id, show_note_descr = False):
	notes = dbGetNotes(conn, link_id, show_note_descr)
	return ['{} : {}'.format(x[1], x[2]) for x in notes] if show_note_descr else [x[1] for x in notes]

def flattags(tags):
	flat = [k if (len(v)==0) else '{}:{}'.format(k,v) for k,v in tags.items()]
	return sorted(flat)

def listToTags(ltags):
	if isinstance(ltags, list):
		dtags = {}
		for t in ltags:
			dtags[t] = ''
		return dtags
	elif isinstance(ltags, dict):
		return ltags
	else:
		return listToTags([ltags])

def printList(lst, sep, col1, col2):
	for i in range(len(lst)):
		print_col(col2 if i%2 else col1)
		print '{}{}'.format(lst[i], sep if i+1<len(lst) else ''),
	print_col('default')
	print ''

def printTagList(lst, sep, col1, col2, coldeep):
	for i in range(len(lst)):
		print_col(coldeep if (':' in lst[i]) else (col2 if i%2 else col1))
		print '{}{}'.format(lst[i], sep if i+1<len(lst) else ''),
	print_col('default')
	print ''

def printEntry(entry, mode = 2, show_ts = False, show_links = False, conn_db = None, len_prefix = 0, show_link_descr = False, show_notes = False, show_note_descr = False):
	def printList(lst, len_prefix, bcol = 'bblue', fcol = 'default', lbreak = False):
		if len(lst) == 0:
			return
		print ''.join([' ']*(len_prefix+2)),
		for iti in range(len(lst)):
			print_col('bwhite'); print '{}'.format(iti+1),; print_col(fcol); print_col(bcol);
			print u' {} {}'.format(lst[iti], '\n' if lbreak else ''),
		print_col('bwhite'); print ' ',
		print_col('bdefault'); print_col('default'); print '';
	if mode > 0:
		if (show_ts):
			print '<{}>'.format(entry['ts'].strftime('%d-%b-%Y')),
		if mode == 1:
			print unistr('[{}]{}').format(entry['name'], '/{}'.format(entry['link_id']) if len(entry['link_id']) else '' ),
			printTagList(flattags(entry['tags']), ',', 'yellow', 'yellow', 'magenta')
			#print_col('yellow'); print ','.join(flattags(entry['tags'])); print_col('default');
		else:
			print unistr('[{}] ').format(entry['name']),
			if len(entry['link_id']):
				print_col('bblue');  print unistr('({})').format(entry['link_id']),; print_col('bdefault'); sys.stdout.write(' ');
			items = flattags(entry['tags'])
		 	for iti in range(len(items)):
				print_col('bwhite'); print ' ',; print_col('bmagenta' if (':' in items[iti]) else 'bgreen');
				print u' {} '.format(items[iti]),
			print_col('bwhite'); print ' ',
			print_col('bdefault'); print '';
			if show_links and len(entry['link_id']):
				partners = dbGetLinkPartnerStrings(conn_db, entry['link_id'], show_link_descr)
				printList(partners, len_prefix, 'bblue')
			if show_notes and len(entry['link_id']):
				notes = dbGetNoteStrings(conn_db, entry['link_id'], show_note_descr)
				printList(notes, len_prefix, 'bdefault', 'yellow', show_note_descr)
	else:
		print entry['hashid'], entry['fname'], entry['ts'], entry['name'], entry['tags']

def editFinalizeName(entry, name):
	if (name != entry['name']):
		print name
		entry['name'] = name
		return True
	return False
def editFinalizeTags(entry, tag_str):
	tagsa = [x.strip() for x in tag_str.split(',')]
	tags = {}
	for tag in tagsa:
		if (':' not in tag):
			tags[tag] = ''
		else:
			tags[tag.split(':')[0]] = tag.split(':')[1]
	if (entry['tags'] != tags):
		print flattags(tags)
		entry['tags'] = tags
		return True
	return False

def editEntry(entry, ename = True, etags = True, nameFirst = True):
	try:
		if (ename and etags):
			print entry['name']
			print flattags(entry['tags'])
			fmt_str = u'<{}><{}>'
			if (nameFirst):
				entry_str = fmt_str.format(entry['name'], ','.join(flattags(entry['tags'])))
			else:
				entry_str = fmt_str.format(','.join(flattags(entry['tags'])), entry['name'])
		elif (ename):
			entry_str = entry['name']
		elif (etags):
			entry_str = ','.join(flattags(entry['tags']))
		else:
			return False

		cpos = 0
		it = 0
		print u' - {}'.format(entry_str)
		prefix = ' : '
		print_col('yellow')
		while 1:
			# http://www.termsys.demon.co.uk/vtansi.htm
			print '\x1B[2K', # Erase line
			print u'\r{}{}\r'.format(prefix, entry_str),
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
				char = inp[0]
				if (True and (ord(char) >= 32 and ord(char) <= 126)):
					entry_str = entry_str[0:cpos] + ''.join(inp) + entry_str[cpos:]
					cpos = cpos + 1
			else:
				print inp
	except:
		traceback.print_exc()
		e = sys.exc_info()[0]
		raise e
		return False
	finally:
		print_col('default')
		print ''

	if (ename and etags):
		re_pat = re.compile(ur'\<([^\>]*)\>')
		re_mat = re.findall(re_pat, entry_str)
		if (len(re_mat) == 2):
			modn = editFinalizeName(entry, re_mat[0 if nameFirst else 1])
			modt = editFinalizeTags(entry, re_mat[1 if nameFirst else 0])
			return (modn or modt)
		return False
	elif (ename):
		return editFinalizeName(entry, entry_str)
	elif (etags):
		return editFinalizeTags(entry, entry_str)
	return False

def editEntry2(entry, ename = True, etags = True, nameFirst = True):
	def cprint(str, lpos):
		print str,;	return lpos + len(str);
	if largv_has(['-simple_edit']):
		return editEntry(entry, ename, etags, nameFirst)
	try:
		ipos = 0
		lipos = -1
		epos = -1
		items = []
		if ename and nameFirst:
			items.extend([ {'str':u'{}'.format(entry['name']), 'src':'name'} ])
		if etags:
			items.extend([{'str':x, 'src':'tag'} for x in flattags(entry['tags']) ] )
		if ename and (not nameFirst):
			items.extend([ {'str':u'{}'.format(entry['name']), 'src':'name'} ])
		prefix = ' : '
		while 1:
			lpos = 0
			# http://www.termsys.demon.co.uk/vtansi.htm
			sys.stdout.write('\x1B[2K') # Erase line
			sys.stdout.write('\r')
			lpos = cprint('{}'.format(prefix), lpos)
			for iti in range(len(items)):
				print_col('bwhite'); lpos = cprint(' ', lpos);
				if (iti == ipos):
					if (epos == -1):
						print_col('bblue' if iti>0 else 'bblue')
					else:
						print_col(('bred' if (':' in items[iti]['str']) else 'bred')  if iti>0 else 'bred')
				else:
					print_col( ('bmagenta' if (':' in items[iti]['str']) else 'bgreen')  if iti>0 else 'bcyan')
				items[iti]['lpos'] = lpos+1
				lpos = cprint(u' {} '.format(items[iti]['str']), lpos)

			print_col('bdefault')
			sys.stdout.write('\r')
			if (epos != -1):
				sys.stdout.write('\r\x1B[{}C'.format(items[ipos]['lpos'] + epos))
			inp = getch()

			if (epos == -1):
				if (len(inp) == 1 and ord(inp[0]) == 27):
					break
				elif ('\n' in inp):
					if (lipos == ipos):
						break
					else:
						epos = 0
				elif ('q' in inp):
					break
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'C']):
					ipos = min(ipos + 1, len(items)-1)
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'D']):
					ipos = max(ipos - 1, 0)
				elif (len(inp)==1):
					char = inp[0]
					if (True and (ord(char) >= 32 and ord(char) <= 126)):
						ipos = ipos
					elif (ord(char) == 9):
						ipos = min(ipos + 1, len(items)-1)
					#else:
					#	print 'xxx'; print 'xxx'
			else:
				edit_str = items[ipos]['str']
				if (len(inp) == 1 and ord(inp[0]) == 27):
					epos = -1
					lipos = ipos
				elif ('\n' in inp):
					epos = -1
					lipos = ipos
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'C']):
					epos = min(epos + 1, len(edit_str))
				elif (len(inp) >= 3 and inp[0:3] == ['\x1B', '[', 'D']):
					epos = max(epos - 1, 0)
				elif (len(inp) >= 1 and inp[0] == '\x7F'):
					if (epos > 0):
						edit_str = edit_str[0:epos-1] + edit_str[epos:]
						epos = epos-1
				elif (len(inp)==1):
					char = inp[0]
					if ((ord(char) >= 32 and ord(char) <= 126)):
						edit_str = edit_str[0:epos] + ''.join(inp) + edit_str[epos:]
						epos = epos + 1
				items[ipos]['str'] = edit_str
			#else:
			#	print inp,

		newflattags = []
		for it in items:
			if it['src'] == 'name' and it['str'] != entry['name']:
				editFinalizeName(entry, it['str'])
			elif it['src'] == 'tag':
				newflattags.append(it['str'])
		if etags:
			editFinalizeTags(entry, ','.join(newflattags))
		return True
	except:
		traceback.print_exc()
		e = sys.exc_info()[0]
		raise e
		return False
	finally:
		print_col('default')
		print ''
	return False

def editUpdateEntry(conn, entry, ename, etags, nameFirst = True):
	modded = editEntry2(entry, ename, etags, nameFirst)
	if (modded):
		dbUpdateEntry(conn, entry)
		entry = dbGetEntryByHash(conn, entry['hashid'])
		print_col('green'); printEntry(entry, 1); print_col('default');

def editUpdateLinkPartner(conn, entry, li):
	ret1,ret2 = dbGetLinkPartners(conn, entry['link_id'])
	link_rec = ret1[li] if (li < len(ret1)) else ret2[li-len(ret1)]
	full_rec = dbGetLinkFull(conn, link_rec[0])
	edit_inds = [1,3,2,4]
	edit_items = [{'str':full_rec[x]} for x in edit_inds]
	vt_edit2(' ', edit_items)
	new_rec = [full_rec[x] if (x not in edit_inds) else edit_items[edit_inds.index(x)]['str'] for x in range(len(full_rec))]
	if (new_rec != full_rec):
		dbUpdateLink(conn, new_rec)
	return 0

def addFile(sess, conn, fpath, tags, copy):
	entry = createEntry(fpath, tags)
	return addEntry(sess, conn, fpath, entry, copy)

def addEntry(sess, conn, fpath, entry, copy):
	def addIgnored(sess, key, fpath, extra_info = None):
		if (sess is not None):
			if (key not in sess):
				sess[key] = []
			sess[key].append(fpath if (extra_info is None) else (fpath, extra_info))

	if (g_repo is not None):
		if (not os.path.isdir(g_repo)):
			os.makedirs(g_repo)
		if (copy == True):
			tpath = os.path.join(g_repo, entry['fname'])
			if (os.path.isfile(tpath)):
				thashid = genFileMD5Str(tpath, makeCleanFilename(tpath))
				if (thashid == entry['hashid']):
					addIgnored(sess, 'ignored', fpath, entry)
					return None
				print 'File name clash [{}], edit? [ y(es), n(o) ]:'.format(entry['fname']),
				inp = raw_input()

				if (inp.lower() in ['y', 'yes']):
					if (editEntry(entry, True, False)):
						return addEntry(sess, conn, fpath, entry, copy)
				addIgnored(sess, 'clashed', fpath, entry)
				return None
			#print_col('green'); print 'Copy [{}]->[{}]'.format(fpath, tpath); print_col('default');
			shutil.copyfile(fpath, tpath)
	if True:
		if (dbExistsEntry(conn, entry)):
			addIgnored(sess, 'exists', fpath, entry)
			return None
		dbAddEntry(conn, entry)
	return entry

def listAll(conn):
	entries = dbGetEntries(conn)
	for e in entries:
		printEntry(e)


def enter_assisted_input():

	def checkPlatMac():
		if os.name != 'posix':
			print_col('red'); print 'Not supported on windows yet'; print_col('default');
			return False
		return True

	def viewEntry(entry):
		if (not checkPlatMac()):
			return
		if (entry['fname'].endswith('.pdf')):
			runUnpiped(['open', '-a', 'Preview', os.path.join(g_repo, entry['fname'])])
		else:
			runUnpiped(['open', os.path.join(g_repo, entry['fname'])])

	def closeViewEntry(entry):
		if (not checkPlatMac()):
			return
		# http://superuser.com/questions/526624/how-do-i-close-a-window-from-an-application-passing-the-file-name
		script = "tell application \"Preview\" to close (every window whose name begins with \"{}\")".format(entry['fname'])
		runUnpiped(['osascript', '-e', "{}".format(script)])

	def filterEntries(entries, filters, conn):
		filtered = []
		for e in entries:
			fpass = True
			for f in filters:
				if (fpass):
					if (f['type'] == 'name'):
						fpass = fpass and matchName(f['pat'], e['name'])
					elif (f['type'] == 'tag'):
						fpass = fpass and matchTags(f['pat'], e['tags'])
					elif (f['type'] == 'time'):
						fpass = fpass and matchTime(f['pat'], e['ts'])
					elif (f['type'] == 'linked'):
						fpass = fpass and len(e['link_id']) > 0 and dbHasLinks(conn, e['link_id'])
					elif (f['type'] == 'noted'):
						fpass = fpass and len(e['link_id']) > 0 and dbHasNotes(conn, e['link_id'])
				else:
					break
			if (fpass):
				filtered.append(e)
		return filtered

	def matchAllTags(pat, entries):
		tags = {}
		for e in entries:
			etags = flattags(e['tags'])
			for etag in etags:
				tags[etag] = ''
		matches = []
		tkeys = sorted(tags.keys())
		for it in range(len(tkeys)):
			if matchName(pat, tkeys[it]):
				matches.append(tkeys[it])
		return matches

	def sortEntries(entries, time_based = False):
		if time_based:
			return sorted(entries, key = lambda x : (x['ts'], x['name']))
		else:
			return sorted(entries, key = lambda x : (x['name']))

	def reset(conn, time_based = False):
		filters = []; entries = [sortEntries(dbGetEntries(conn), time_based)];
		return (filters, entries, [time_based])

	def textSearchEntry(ei, e, phrase):
		if (not checkPlatMac()):
			return
		tpath = os.path.join(unistr(g_repo), unistr(e['fname']))
		fname_, fext = os.path.splitext(e['fname']); fext = fext.lower();
		if (fext.lower() == '.pdf'):
			args = [unistr('pdftotext'), unistr('\"{}\"').format(tpath), '-', '|', 'grep', '-i', unistr('\"{}\"').format(unistr(phrase))]
		elif (fext.lower() == '.djvu'):
			args = [unistr('djvutxt'), unistr('\"{}\"').format(tpath), '|', 'grep', '-i', unistr('\"{}\"').format(unistr(phrase))]
		else:
			return ([],[])
		#print unistr(' '.join(args))
		(out, err) = runPipedShell(unistr(' '.join(args)))
		elines = []; lines = [];
		if (len(err)):
			elines = [' ' + x.strip() for x in err.split('\n') if (len(x.strip()))]
		lines = [x.strip() for x in out.split('\n') if (len(x.strip()))]
		return (elines, lines)

	def textLengthEntry(e):
		if (not checkPlatMac()):
			return
		tpath = os.path.join(unistr(g_repo), unistr(e['fname']))
		fname_, fext = os.path.splitext(e['fname']); fext = fext.lower();
		if (fext.lower() == '.pdf'):
			args = [unistr('pdftotext'), unistr('\"{}\"').format(tpath), '-', '|', 'wc', '-w']
		elif (fext.lower() == '.djvu'):
			args = [unistr('djvutxt'), unistr('\"{}\"').format(tpath), '|', 'wc', '-w']
		else:
			return ([], 0)
		#print unistr(' '.join(args))
		(out, err) = runPipedShell(unistr(' '.join(args)))
		elines = []; lines = [];
		if (len(err)):
			elines = [' ' + x.strip() for x in err.split('\n') if (len(x.strip()))]
		count = int(out.strip())
		return (elines, count)

	def textCountEntry(e,word):
		if (not checkPlatMac()):
			return
		tpath = os.path.join(unistr(g_repo), unistr(e['fname']))
		fname_, fext = os.path.splitext(e['fname']); fext = fext.lower();
		if (fext.lower() == '.pdf'):
			args = [unistr('pdftotext'), unistr('\"{}\"').format(tpath), '-', '|', 'grep', '-c', '-i', unistr('\"{}\"').format(unistr(word))]
		elif (fext.lower() == '.djvu'):
			args = [unistr('djvutxt'), unistr('\"{}\"').format(tpath), '|', 'grep', '-c', '-i', unistr('\"{}\"').format(unistr(word))]
		else:
			return ([], 0)
		#print unistr(' '.join(args))
		(out, err) = runPipedShell(unistr(' '.join(args)))
		elines = []; lines = [];
		if (len(err)):
			elines = [' ' + x.strip() for x in err.split('\n') if (len(x.strip()))]
		count = int(out.strip())
		return (elines, count)

	def showEntry(ei, e):
		prefix = '\n{}. '.format(ei+1)
		print(prefix),
		printEntry(e, len_prefix=len(prefix))

	def printErrLines(ei, e, elines):
		if (len(elines) == 0):
			return
		showEntry(ei, e)
		ulines = []
		for el in elines:
			if el not in ulines:
				ulines.append(el)
		print_col('red'); print '\n'.join(ulines); print_col('default');

	def textSearchPrint(ei, e, elines, lines):
		printErrLines(ei, e, elines)
		if (len(lines)):
			if (len(elines) == 0):
				showEntry(ei, e)
			for li in range(len(lines)):
				print_col('cyan' if li%2 else 'magenta')
				print ' {}. {}'.format(li+1, lines[li])
			print_col('default')

	def textSearchEntries(entries, phrase, nthreads = 1):
		if (not checkPlatMac()):
			return
		if (nthreads == 1):
			for ei in range(len(entries)):
				(elines, lines) = textSearchEntry(ei, entries[ei], phrase)
				textSearchPrint(ei, entries[ei], elines, lines)
		else:
			def textSearchThread(eis, entries, entry_list, entry_errs, entry_lines):
				for ei in eis:
					(elines, lines) = textSearchEntry(ei, entries[ei], phrase)
					if (len(elines) or len(lines)):
						entry_list.append(ei); entry_errs.append(elines); entry_lines.append(lines)

			def chunks(l, n):
				n = max(1, n)
				return [l[i:i + n] for i in range(0, len(l), n)]
			print ' Using {} threads...'.format(nthreads)
			eis = range(len(entries))
			teis = chunks(eis, int(math.ceil(float(len(eis))/float(nthreads))))
			tinfos = []
			for ti in range(len(teis)):
				tinfo = {'entry_list':[], 'entry_errs':[], 'entry_lines':[], 'thread':None }
				if len(teis[ti]):
					#print threading.active_count()
					t = threading.Thread(target=textSearchThread, args=(teis[ti],entries,tinfo['entry_list'],tinfo['entry_errs'],tinfo['entry_lines']))
					tinfo['thread'] = t
					tinfos.append(tinfo)
					t.setDaemon(True)
					t.start()
					#print threading.active_count()
			for tinfo in tinfos:
				tinfo['thread'].join()
			for tinfo in tinfos:
				for i in range(len(tinfo['entry_list'])):
					ei = tinfo['entry_list'][i]
					textSearchPrint(ei, entries[ei], tinfo['entry_errs'][i], tinfo['entry_lines'][i])

	def listEntries(entries, show_ts=False, show_links = False, conn_db = None, show_notes = False):
		for ie in range(len(entries)):
			prefix = '{}. '.format(ie+1)
			print prefix,
			printEntry(entries[ie], show_ts=show_ts, show_links=show_links, conn_db = conn_db, len_prefix = len(prefix), show_notes = show_notes);

	def handle_cd(filters, entries, time_based, newentries, filt, cd_time_based, show_links, conn_db, show_notes):
		newentries = sortEntries( filterEntries(entries[-1], [filt], conn_db), cd_time_based )
		if (len(newentries)):
			filters.append(filt); entries.append( newentries ); time_based.append(cd_time_based);
			if (len( newentries ) <= 24):
				listEntries( entries[-1], show_ts=cd_time_based, show_links = show_links, conn_db = conn_db, show_notes = show_notes )
		else:
			print ' empty...'

	cur_time_based = False; cur_show_links = True;
	cur_show_notes = True;
	conn = dbStartSession(g_dbpath)
	filters, entries, time_based = reset(conn, cur_time_based)
	viewEntryHist = []
	cmd_hist = vt_hist_create()
	user_exit = False
	while user_exit == False:
		try:
			while True:
				pats = [x['pat'] for x in filters]; prefix = '/{} ({})>'.format('/'.join(pats), len(entries[-1]))
				inp = vt_edit(prefix, '', cmd_hist)
				#inp = raw_input(); print inp;
				input_splt = inp.split(' ')
				cmd = input_splt[0]

				if (cmd == 'q'):
					user_exit = True
					break
				elif (cmd in ['time', '+time']):
					cur_time_based = True
					entries[-1] = sortEntries(entries[-1], time_based = cur_time_based)
					time_based[-1] = cur_time_based
				elif (cmd in ['-time', 'notime']):
					cur_time_based = False
					entries[-1] = sortEntries(entries[-1], time_based = cur_time_based)
					time_based[-1] = cur_time_based
				elif (inp in ['links', '+links']):
					cur_show_links = True
				elif (cmd in ['nolinks', '-links']):
					cur_show_links = False
				elif (inp in ['notes', '+notes']):
					cur_show_notes = True
				elif (cmd in ['nonotes', '-notes']):
					cur_show_notes = False
				elif (cmd == 'r' or cmd == 'reset'):
					filters, entries = reset(conn, cur_time_based)
				elif (cmd == 'ls' or cmd == 'l' or cmd == 'tls'):
					listEntries( entries[-1], show_ts=(cmd == 'tls') or ('-t' in input_splt) or (time_based[-1]), show_links = cur_show_links, conn_db = conn, show_notes = cur_show_notes )
				elif (cmd == 'tags' or cmd == 't'):
					tags = {}
					for e in entries[-1]:
						etags = flattags(e['tags'])
						for etag in etags:
							tags[etag] = ''
					tkeys = sorted(tags.keys())
					for it in range(len(tkeys)):
						print '{}, '.format(tkeys[it]),
						if (it % 10 == 0 and it != 0):
							print ''
					print '\n{} tags\n'.format(len(tkeys))
				elif ((cmd == 'cd' and len(input_splt) == 1)
						or (cmd == 'cd' and input_splt[1] == '..')
						or cmd == '..'
						or cmd == '.'
						or cmd == 'cd..'):
					if (len(filters)):
						filters.pop(); entries.pop(); time_based.pop();
				elif (cmd == 'cd' or cmd == 'fcd'):
					filter2 = [None]
					repeat_count = 0; repeat = True;
					while repeat:
						repeat = False
						if (cmd == 'cd' and repeat_count == 0):
							if (len(input_splt) == 2):
								tag = input_splt[1]
								filter2[0] = {'type':'tag', 'pat':tag}
						elif (cmd == 'fcd' or repeat_count > 0):
							phrase = ' '.join(input_splt[1:])
							matches = matchAllTags(phrase, entries[-1])
							choices = printAndChoose(matches)
							if (len(choices)):
								filter2[0] = {'type':'tag', 'pat':matches[choices[0]]}
						print filter2
						if (filter2[0] is not None):
							cd_time_based = True if ('t' in input_splt) else False if ('-t' in input_splt) else cur_time_based
							newentries = sortEntries( filterEntries(entries[-1], filter2, conn), cd_time_based )
							handle_cd(filters, entries, time_based, newentries, filter2[0], cd_time_based, cur_show_links, conn, cur_show_notes)
							if (len(newentries) == 0 and cmd == 'cd' and repeat_count == 0):
								print ' trying a search instead...'
								repeat_count = 1; repeat = True;
							else:
								vt_hist_add(cmd_hist['list'], inp)
						else:
							print ' empty...'
							if (cmd == 'cd' and repeat_count == 0):
								repeat_count = 1; repeat = True;
				elif (cmd == 'cn' and len(input_splt) >= 2):
					tag = input_splt[1]
					filter = {'type':'name', 'pat':tag}
					cd_time_based = True if ('t' in input_splt) else False if ('-t' in input_splt) else cur_time_based
					newentries = sortEntries( filterEntries(entries[-1], [filter], conn), cd_time_based )
					handle_cd(filters, entries, time_based, newentries, filter, cd_time_based, cur_show_links, conn, cur_show_notes)
				elif (cmd == 'ct'):
					pat = fixupTimePat(' '.join([x for x in input_splt[1:] if x != '-t']))
					if (len(pat)):
						filter = {'type':'time', 'pat':pat}
						cd_time_based = True if ('-t' not in input_splt) else False
						newentries = sortEntries( filterEntries(entries[-1], [filter], conn), cd_time_based )
						handle_cd(filters, entries, time_based, newentries, filter, cd_time_based, cur_show_links, conn, cur_show_notes)
					else:
						print ' invalid pattern...'
				elif (cmd == 'cl'):
					filter = {'type':'linked', 'pat':'linked'}
					cd_time_based = True if ('t' in input_splt) else False if ('-t' in input_splt) else cur_time_based
					newentries = sortEntries( filterEntries(entries[-1], [filter], conn), cd_time_based )
					handle_cd(filters, entries, time_based, newentries, filter, cd_time_based, True, conn, False)
				elif (inp == 'cn'):
					filter = {'type':'noted', 'pat':'noted'}
					cd_time_based = True if ('t' in input_splt) else False if ('-t' in input_splt) else cur_time_based
					newentries = sortEntries( filterEntries(entries[-1], [filter], conn), cd_time_based )
					handle_cd(filters, entries, time_based, newentries, filter, cd_time_based, False, conn, True)
				elif (cmd in ['lid', 'nid']):
					if (len(input_splt) == 3):
						ei = int(input_splt[1])-1; entry = entries[-1][ei]; lid = input_splt[2];
						if (entry['link_id'] != lid):
							old_lid = entry['link_id']; entry['link_id'] = lid;
							dbUpdateEntryLinkId(conn, entry)
							print ' {} (was {})'.format(lid, old_lid)
				elif (cmd == 'link'):
					if (len(input_splt) >= 4):
						link_from = input_splt[1]; link_type = input_splt[2]; link_to = input_splt[3]; link_desc = ' '.join(input_splt[4:]);
						dbAddLink(conn, link_from, link_to, link_type, link_desc)
				elif (cmd == 'note'):
					if (len(input_splt) >= 3):
						link_id = input_splt[1]; note_loc = input_splt[2]; note_desc = ' '.join(input_splt[3:]);
						if is_int(link_id):
							link_id = entry = entries[-1][int(link_id)]['link_id']
						dbAddNote(conn, link_id, note_loc, note_desc)
				elif (cmd == 'links'):
					if (len(input_splt) == 2):
							ei = int(input_splt[1])-1; entry = entries[-1][ei];
							prefix = ' '; print prefix;
							printEntry(entry, show_ts=cur_time_based, show_links=True, conn_db = conn, len_prefix = len(prefix), show_link_descr = True)
				elif (cmd == 'notes'):
					if (len(input_splt) == 2):
							ei = int(input_splt[1])-1; entry = entries[-1][ei];
							prefix = ' '; print prefix;
							printEntry(entry, show_ts=cur_time_based, conn_db = conn, len_prefix = len(prefix), show_notes = True, show_note_descr = True)
				elif (cmd == 'e' or cmd == 'en' or cmd == 'et'):
					if (len(input_splt) == 2):
						ei = int(input_splt[1])-1
						entry = entries[-1][ei]
						editUpdateEntry( conn, entry, cmd == 'e' or cmd == 'en', cmd == 'e' or cmd == 'et')
				elif (cmd == 'el'):
					if (len(input_splt) == 3):
						try:
							ei = int(input_splt[1])-1; li = int(input_splt[2])-1; entry = entries[-1][ei];
							editUpdateLinkPartner( conn, entry, li)
						except:
							traceback.print_exc()
				elif (cmd == 'o' or cmd == 'read' or cmd == 'view'):
					if (len(input_splt) == 2):
						ei = int(input_splt[1])-1
						entry = entries[-1][ei]
						viewEntryHist.append(entry)
						viewEntry(entry)
					else:
						for e in viewEntryHist:
							printEntry(entry)
				elif (cmd == 'x' or cmd == 'close'):
					entry = None
					if (len(input_splt) == 2):
						ei = int(input_splt[1])-1
						entry = entries[-1][ei]
					else:
						if (len(viewEntryHist)):
							entry = viewEntryHist.pop()
					if (entry is not None):
						closeViewEntry(entry)
				elif (cmd == 'cleanup'):
					centries = [x for x in entries[-1] if ('c' not in x['extra']) ]
					print 'There are {} entries to clean.'.format(len(centries))
					for ie in range(len(centries)):
						print '{}. '.format(ie),
						entry = centries[ie]
						editUpdateEntry(conn, entry, True, True)
						entry['extra'].append('c')
						dbUpdateEntry(conn, entry)
				elif (cmd == 'scan'):
					spath = None if (g_lastscan is None) else g_lastscan[0]
					time =  None if (g_lastscan is None) else g_lastscan[1]
					if (len(input_splt) >= 2):
						spath = input_splt[1]
					if (len(input_splt) >= 3):
						time = input_splt[2]
					if (spath is not None):
						scanImport(conn, spath, '1h' if time is None else time)
					filters, entries, time_based = reset(conn, cur_time_based)
				elif (cmd == '+' or cmd == '-'):
					if (len(input_splt) == 3):
						ei = int(input_splt[1])-1
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
							dbUpdateEntry(conn, entry)
							print_col('green'); printEntry(entry, 1); print_col('default');
				elif (cmd == '#'):
					if (len(input_splt) == 2):
						ei = int(input_splt[1])-1
						entry = entries[-1][ei]
						(elines, count) = textLengthEntry(entry)
						printErrLines(ei, entry, elines)
						print_col('green'); print ' {} words'.format(count); print_col('default');
				elif (cmd == 'figs'):
					if (len(input_splt) == 2):
						ei = int(input_splt[1])-1
						entry = entries[-1][ei]
						(elines, count) = textCountEntry(entry, 'figure')
						printErrLines(ei, entry, elines)
						print_col('green'); print ' ~{} figures'.format(count/2); print_col('default');
				elif (cmd == 'f' or cmd == 'find'):
					phrase = ' '.join(input_splt[1:])
					nthreads = max(1, multiprocessing.cpu_count()-1)
					textSearchEntries(entries[-1], phrase, nthreads)
				elif (cmd == 'ft'):
					phrase = ' '.join(input_splt[1:])
					matches = matchAllTags(phrase, entries[-1])
					for it in range(len(matches)):
							print '{}. {}, '.format(it+1, matches[it]),
							if (it % 10 == 0 and it != 0):
								print ''
					print '\n{} tags\n'.format(len(matches))
				elif (cmd == 'remove' or cmd == 'delete'):
					ei = int(input_splt[1])-1
					entry = entries[-1][ei]
					print_col('red'); printEntry(entry, 1); print_col('default');
					dbRemoveEntry(conn, entry)
					tpath = os.path.join(unistr(g_repo), unistr(entry['fname']))
					os.remove(tpath)
		except:
			#dbEndSession(conn)
			print_col('red'); print ''; traceback.print_exc(); print_col('default');
			e = sys.exc_info()[0]
			#raise e
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

def extractTagsFromFileName(fname):
	p1, p2 = tagRe()
	ltags1 = matchesRe(fname, p1); ltags2 = matchesRe(fname, p2);
	tags = {}
	for ltag in ltags1:
		tags[ltag] = ''
	for ltag in ltags2:
		tags['[{}]'.format(ltag).lower()] = ''
	fname_, fext = os.path.splitext(fname)
	tags[fext] = ''
	return tags

def tagImport(conn, ipath, updating):
	if (len(ipath) == 0):
		return
	addFileSess = {}
	for dirName, subdirList, fileList in os.walk(ipath):
		dirNameTail, dirNameHead = os.path.split(dirName)
		if (dirNameHead.startswith('.') == False and dirNameHead.startswith('_') == False):
			for fname in fileList:
				fname_, fext = os.path.splitext(fname)
				if (fname.startswith('.') == False and fext.lower() in ['.pdf', '.djvu', '.epub', '.txt', '.md', '.jpg', '.jpeg', '.png', '.missing']):
					fpath = os.path.join(os.path.join(ipath, dirName), fname)
					tags = extractTagsFromFileName(fpath)
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

def printAndChoose(list, postindex = False, forceChoose = False):
	if (len(list) == 0): return []
	if (len(list) == 1 and forceChoose == False): return list
	for i in range(len(list)):
		print_coli(gAltCols[i % len(gAltCols)])
		if postindex:
			print '. {} ({})'.format(list[i], i+1)
		else:
			print '{}. {}'.format(i+1, list[i])
	print_col('default')
	print '>',
	input_str = raw_input()
	choices = []
	if ('-' in input_str):
		list = input_str.split('-')
		choices = range(int(list[0]), int(list[1])+1)
	elif (',' in input_str):
		choices = [int(x) for x in input_str.split(',')]
	else:
		if len(input_str):
			choices.append(int(input_str))
	choices = [i-1 for i in choices]
	return choices

def scanImport(conn, spath, time):
	global g_lastscan
	g_lastscan = (spath, time)
	if os.name == 'nt':
		# http://blogs.technet.com/b/heyscriptingguy/archive/2014/02/07/use-powershell-to-find-files-that-have-not-been-accessed.aspx
		print_col('red'); print 'Not supported on windows yet'; print_col('default');
		return
	exts = ['.pdf','.djvu','.epub']
	args = ['find', '{}'.format(spath), '(']
	for e in exts:
		args.extend(['-name', '*{}'.format(e), '-o'])
	args.pop()
	args.extend([')', '-ctime', '-{}'.format(time)])
	#print args
	(out, err) = runPiped(args)
	if (len(err)):
		print_col('red'); print err; print_col('default');
		return
	lines = [x.strip() for x in out.split('\n') if (len(x.strip()))]
	chosen = printAndChoose(lines, False, True)
	for c in chosen:
		fpath = lines[c]
		tags = extractTagsFromFileName(fpath)
		if (len(tags) == 0):
			tags['scan'] = ''
		sess = 	{}
		entry = addFile(sess, conn, fpath, tags, True)
		if (len(sess)):
			print sess
		if (entry is not None):
			editUpdateEntry(conn, entry, True, True, False)
		else:
			entry = dbGetEntryByHash(conn, createFileHash(fpath))
			print_col('yellow'); printEntry(entry); print_col('default');


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
		jtags = None
		if (largv_get(['-jtags'], '') != ''):
			json.loads( largv_get(['-jtags'], ''))
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
	elif (largv_get(['-scan'], None) is not None):
		spath = largv_get(['-scan'], None)
		time = largv_get(['-time'], '1h')
		conn = dbStartSession(g_dbpath); scanImport(conn, spath, time); dbEndSession(conn);
	elif largv_has(['-test_normalize']):
		print normalizeName(largv_get(['-test_normalize'], ''))
	elif largv_has(['-test_clean']):
		print cleanFilename(largv_get(['-test_clean'], ''))
	elif largv_has(['-db_upgrade']):
			conn = dbStartSession(g_dbpath); dbUpgrade(conn); dbEndSession(conn);
	else:
		enter_assisted_input()

main()

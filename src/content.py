# -*- coding: utf-8 -*-

""" MediaPlat Content Manager """

import os, time, datetime
from psycopg2 import *
import subprocess
import unittest
import tempfile, random, difflib, shutil, string
from pattern import singleton
from log import log, clog
from util import *
from config import settings
from glob import glob

@singleton
class Content(object):
    DATABASE = 'mediaplat'
    PGUSER = 'postgres'
    PGHOST = '/var/run/postgresql'
    ROOT = 'ROOT'
    FOLDER = 'folder'
    AUDIO = 'audio'
    VIDEO = 'video'
    IMAGE = 'image'

    CUT = "__CUT__"
    TABLES = {
        'tree': "CREATE TABLE tree (_id serial PRIMARY KEY, uid varchar, pid varchar, type varchar, name varchar, sortname varchar)",
        'data': "CREATE TABLE data (_id serial PRIMARY KEY, uid varchar, module varchar, key varchar, value varchar)"
    }
    VIEWS = {
        'tree_pid_index': "CREATE INDEX tree_pid_index ON tree (pid)",
        'tree_uid_index': "CREATE INDEX tree_uid_index ON tree (uid)",
        'data_uid_index': "CREATE INDEX data_uid_index ON data (uid)",
        'data_key_value_index': "CREATE INDEX data_key_value_index ON data (key, lower(value))"
    }
    TREE = {
        ROOT: [ROOT, "0", {
            FOLDER: ["Folder", "1", {
                '2': ["root", "1", {}]
            }],
            AUDIO: ["Audio", "2", {
                'audio_all': ["All Audio", "1", {}],
                'audio_album': ["Album", "2", {}],
                'audio_artist': ["Artist", "3", {}],
                'audio_genre': ["Genre", "4", {}]
            }],
            VIDEO: ["Video", "3", {
                'video_all': ["All Video", "1", {}]
            }],
            IMAGE: ["Image", "4", {
                'image_all' : ["All Image", "1", {}],
                'image_date' : ["Date", "2", {}]
            }]
        }]
    }

    def __init__(self):
        self.fnull = open(os.devnull, 'w')
        self._create_database(self.DATABASE)
        self.conn = connect("dbname={} host={} user={}".format(self.DATABASE, self.PGHOST, self.PGUSER))
        self.STOPWATCH = False
        self.push_func = None

    def __del__(self):
        self.conn.close()
        self.fnull.close()

    def _create_database(self, database):
        try:
            subprocess.check_output(["createdb", database, "-U", self.PGUSER], stderr=self.fnull)
        except subprocess.CalledProcessError as ex:
            pass

    def _execute_commit(self, query):
        cursor = self.conn.cursor()
        cursor.execute(query);
        self.conn.commit()
        cursor.close()

    def _execute_fetchone(self, query):
        cursor = self.conn.cursor()
        cursor.execute(query)
        if cursor.rowcount <= 0:
            return None
        result = cursor.fetchone()
        cursor.close()
        return result

    def database(self, dbname):
        self._create_database(database)
        self.conn = connect("dbname={} host={} user={}".format(self.DATABASE, self.PGHOST, self.PGUSER))

    def buildup(self):
        """Create database tables and views"""
        self.cleanup()

        cursor = self.conn.cursor()
        for table in self.TABLES.iterkeys():
            cursor.execute(self.TABLES[table])
        for table in self.VIEWS.iterkeys():
            cursor.execute(self.VIEWS[table])
        self.conn.commit()
        cursor.close()

        self.buildup_tree()

    def cleanup(self):
        """Remove all tables in database"""
        cursor = self.conn.cursor()
        for table in self.TABLES.iterkeys():
            query = "DROP TABLE IF EXISTS {}".format(table)
            cursor.execute(query)
        self.conn.commit()
        cursor.close()

    def buildup_tree(self):
        self._buildup_tree(self.TREE, '0')

    def _buildup_tree(self, items, parent):
        for item in items.iterkeys():
            node = { 'uid':item, 'pid':parent, 'type':'container',
                     'name':items[item][0], 'sortname':items[item][1] }
            self.add_tree(node)
            self._buildup_tree(items[item][2], item)

    def rebuild(self):
        log.info("Rebuild database and thumbnails")
        cursor = self.conn.cursor()
        for table in self.TABLES.iterkeys():
            query = "DELETE FROM {}".format(table)
            cursor.execute(query)
        self.conn.commit()
        cursor.close()

        thumb_dir = settings.get("thumbnail", "path")
        for base, dirs, files, in os.walk(thumb_dir):
            for file in files:
                os.remove(os.path.join(base, file))

        self.buildup_tree()

    def add_tree(self, node):
        """
        :param node: data must have 'uid', 'pid', 'type', 'name'
        """
        required = [ 'uid', 'pid', 'type', 'name' ]
        if not self._has_keys(required, node):
            return None
        if 'sortname' not in node:
            node['sortname'] = node['name']

        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO tree (uid, pid, type, name, sortname) VALUES (%(uid)s, %(pid)s, %(type)s, %(name)s, %(sortname)s)", node)
        self.conn.commit()
        cursor.close()
        return node

    def get_tree(self, id):
        if not self._check_valid_id(id):
            return None
        cursor = self.conn.cursor()
        cursor.execute("SELECT uid, name, pid, type FROM tree WHERE uid=%(uid)s", {'uid':id})
        if cursor.rowcount <= 0:
            return None
        data = {}
        data['uid'], data['name'], data['pid'], data['type'] = cursor.fetchone()
        cursor.close()
        return data

    def del_tree(self, id):
        query = "DELETE FROM tree WHERE uid='{}'".format(id)
        self._execute_commit(query)

    def cut_tree(self, id):
        query = "UPDATE tree SET pid='{}' WHERE uid='{}'".format(self.CUT, id)
        self._execute_commit(query)

    def mod_tree(self, id, data):
        query = "UPDATE tree SET "
        column_to_update = ['uid', 'pid', 'type', 'name', 'sortname']

        for key in data.keys():
            if key in column_to_update:
                query += "{}='{}',".format(key, data[key])

        query = query.rstrip(",")
        query += " WHERE uid='{}'".format(id)
        self._execute_commit(query)

    def add_data(self, node):
        """
        :param node: data dictionary (must have 'uid', 'module')
        """
        required = [ 'uid', 'module' ]
        if not self._has_keys(required, node):
            return None

        uid = node.pop('uid')
        module = node.pop('module')
        cursor = self.conn.cursor()

        exist_check = ['category']
        for key in node.iterkeys():
            if key in exist_check:
                query = "DELETE FROM data WHERE uid='{}' AND key='{}'".format(uid, key)
                cursor.execute(query)
            cursor.execute("INSERT INTO data (uid, module, key, value) VALUES (%(uid)s, %(module)s, %(key)s, %(value)s)", 
                           {'uid':uid, 'module':module, 'key':key, 'value':node[key]})
        self.conn.commit()
        cursor.close()

        # virtual folder
        if module == 'media_info' and 'category' in node:
            node['uid'] = uid
            self._add_category(node)

    def _add_category(self, node):
        required = [ 'uid', 'category' ]
        if not self._has_keys(required, node):
            return

        tnode = self.get_tree(node['uid'])
        default_name = tnode['name']

        parents = []
        if node['category'] == 'video':
            parents.append(('video_all', default_name))
        elif node['category'] == 'audio':

            music_name = ''
            music_name += node.get('album', '')
            music_name += "%05s" % node.get('track_number', '0')

            parents.append(('audio_all', music_name))
            if 'artist' in node:
                parent = self._get_category(node['uid'], 'audio_artist', node['artist'])
                parents.append((parent, music_name))
            if 'album' in node:
                parent = self._get_category(node['uid'], 'audio_album', node['album'])
                parents.append((parent, music_name))
            if 'genre' in node:
                parent = self._get_category(node['uid'], 'audio_genre', node['genre'])
                parents.append((parent, music_name))
        elif node['category'] == 'image':
            parents.append(('image_all', default_name))

            dnode = self.get_data(node['uid'])
            parent = self._get_category(node['uid'], 'image_date', dnode['date'][:7])
            parents.append((parent, default_name))

        for parent, sortname in parents:
            uid = parent + "_" + node['uid']
            tnode = {'uid':uid, 'pid':parent, 'type':'item', 'name':default_name, 'sortname':sortname}
            self.add_tree(tnode)

    def _get_category(self, uid, parent, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT uid FROM tree WHERE pid=%(pid)s AND name=%(name)s", 
            {'pid':parent, 'name':name})
        if cursor.rowcount <= 0:
            result = parent + '_v' + uid
            node = {'uid': result, 'pid':parent, 'type':'container', 'name':name}
            self.add_tree(node)
        else:
            result, = cursor.fetchone()
        cursor.close()
        return result

    def _del_category(self, uid):
        cursor = self.conn.cursor()
        query = "SELECT pid FROM tree WHERE uid like '%{}' AND type='item'".format(uid)
        cursor.execute(query)
        result = cursor.fetchall()

        query = "DELETE FROM tree WHERE uid LIKE '%{}' AND type='item'".format(uid)
        self._execute_commit(query)

        for pid, in result:
            if pid.find('_v') < 0:
                continue
            query = "SELECT COUNT(*) FROM tree WHERE pid='{}'".format(pid)
            count, = self._execute_fetchone(query)
            if count == 0:
                query = "DELETE FROM tree WHERE uid='{}'".format(pid)
                self._execute_commit(query)
        cursor.close()

    def get_data(self, id):
        data = {}
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM data WHERE uid=%(uid)s", {'uid':id})
        result = cursor.fetchall()
        for key, value in result:
            data[key] = value
        cursor.close()
        return data

    def del_data(self, id):
        query = "DELETE FROM data WHERE uid='{}'".format(id)
        self._execute_commit(query)

    def exist(self, id, size, date):
        cursor = self.conn.cursor()
        cursor.execute("SELECT uid FROM tree WHERE uid=%(uid)s", {'uid':id})

        if cursor.rowcount <= 0:
            cursor.close()
            return 'NEW_FILE'
        else:
            cursor.execute("SELECT value FROM data WHERE uid=%(uid)s AND key='size'", {'uid':id})
            if cursor.rowcount <= 0:
                cursor.close()
                return 'MODIFIED'
            else:
                size_fetched = cursor.fetchone()

            cursor.execute("SELECT value FROM data WHERE uid=%(uid)s AND key='date'", {'uid':id})
            if cursor.rowcount <= 0:
                cursor.close()
                return 'MODIFIED'
            else:
                date_fetched = cursor.fetchone()

            if size == size_fetched and date == date_fetched:
                cursor.close()
                return 'SAME_FILE'


    def original_uid(self, id):
        if not id.isdigit():
            id = id[id.rfind('_') + 1:]
        return id

    def fullpath(self, id):
        lpath = []

        id = self.original_uid(id)

        cursor = self.conn.cursor()
        while True:
            if id == '2' or id == self.ROOT:
                break
            cursor.execute("SELECT pid, name FROM tree WHERE uid=%s", (id, ))
            if cursor.rowcount <= 0:
                return None
            id, name = cursor.fetchone()
            lpath.insert(0, name)
        cursor.close()
        return '/' + '/'.join(lpath)

    def uid(self, fullpath):
        fullpath = os.path.realpath(fullpath) 
        path = fullpath.split('/')
        path = [p for p in path if p != '']
        cursor = self.conn.cursor()
        pid = '2'
        for name in path:
            cursor.execute("SELECT uid FROM tree WHERE pid=%(pid)s AND name=%(name)s", 
                {'pid':pid, 'name':name})
            pid = cursor.fetchone()

        cursor.close()

        if pid:
            str_pid = ''.join(pid)
            return str_pid
        else:
            log.debug("uid of \'%s\' was not found in DB." % fullpath)
            return

    def category(self, uid):
        if uid.find('audio') >= 0:
            return 'audio'
        elif uid.find('video') >= 0:
            return 'video'
        elif uid.find('image') >= 0:
            return 'image'
        else:
            return 'folder'

    def parents(self, id):
        result = []

        pid = id
        cursor = self.conn.cursor()
        while True:
            if pid == self.ROOT:
                break
            cursor.execute("SELECT pid, uid, name FROM tree WHERE uid=%s", (pid, ))
            if cursor.rowcount <= 0:
                return result
            pid, id, name = cursor.fetchone()
            result.insert(0, (id, name))
        cursor.close()
        return result

    def total(self):
        query = "SELECT COUNT(DISTINCT uid) FROM data WHERE key='category' AND value='folder'"
        dirs, = self._execute_fetchone(query)
        query = "SELECT COUNT(DISTINCT uid) FROM data"
        total, = self._execute_fetchone(query)
        return total, dirs, total - dirs

    def browse_metadata(self, id=ROOT):
        data = self.get_tree(id)
        if data == None:
            return None

        original_id = self.original_uid(id)
        data.update(self.get_data(original_id))

        if "type" in data and data["type"] == "container":
            # process category
            data['category'] = self.category(id)

            # process child count
            data['child_count'], = \
                self._execute_fetchone("SELECT COUNT(*) FROM tree WHERE pid='{}'".format(id))
            data['child_container_count'], = \
                self._execute_fetchone("SELECT COUNT(*) FROM tree WHERE pid='{}' AND type='container'".format(id))
            data['child_item_count'] = \
                data['child_count'] - data['child_container_count']

            # process thumbnail
            if data['pid'] in ['audio_artist', 'audio_album', 'image_date']:
                if original_id[0] == 'v' and original_id[1:].isdigit():
                    child = self.browse_metadata(original_id[1:])
                    if child:
                        if 'has_thumbnail' in child:
                            data['has_thumbnail'] = child['has_thumbnail']
                        if 'artist' in child:
                            data['artist'] = child['artist']
                        if 'album' in child:
                            data['album'] = child['album']

        return data

    def browse_children(self, id=ROOT, start_index=0, request_count=0, sort="type,sortname"):
        if not self._check_valid_id(id):
            return None

        if self.STOPWATCH:
            starttime = time.time()

        cursor = self.conn.cursor()
        query = "SELECT uid, name FROM tree WHERE pid='{}' ORDER BY {}".format(id, sort)
        if request_count != 0:
            query += " LIMIT " + str(request_count)
        if start_index != 0:
            query += " OFFSET " + str(start_index)

        cursor.execute(query)
        result = cursor.fetchall()
        row_list = []
        for uid, name in result:
            row_list.append(self.browse_metadata(uid))
        cursor.close()

        if self.STOPWATCH:
            print "Elapsed Time : {}".format(time.time() - starttime)
        return row_list

    def sort(self, row_list, key):
        row_list.sort(lambda a, b: cmp(a.get(key, ''), b.get(key, '')))
        return row_list

    def _search_merge(self, query, uid_set, max_count):
        cursor = self.conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        for uid, in result:
            if len(uid_set) < max_count:
                uid_set.add(uid)
            else:
                break
        cursor.close()

    def search_keyword(self, keyword, id = FOLDER, fields = ['name', 'artist', 'album'], categorize = True):
        """ TODO """

        max_count = 100

        if self.STOPWATCH:
            starttime = time.time()

        keyword = keyword.lower()
        field_set = set(fields)
        uid_set = set()

        if 'name' in field_set:
            field_set.remove('name')
            query = "SELECT uid FROM tree WHERE uid SIMILAR TO '[0-9]+' AND lower(name) LIKE '%{}%' LIMIT {}".format(keyword, max_count) 
            self._search_merge(query, uid_set, max_count)
            query = "SELECT uid FROM tree WHERE type='container' AND lower(name) LIKE '%{}%' LIMIT {}".format(keyword, max_count) 
            self._search_merge(query, uid_set, max_count)

        if len(field_set) > 0:
            query = "" 
            for field in field_set:
               query += "(key='{}' and value=lower('{}')) or ".format(field, keyword)
            query = "SELECT uid from data WHERE " + query[:-3] + " LIMIT {}".format(max_count)
            self._search_merge(query, uid_set, max_count)

        if len(uid_set) == 0:
            return {}

        row_list = []
        for uid in uid_set:
            row_list.append(self.browse_metadata(uid))

        row_dict = {}
        if categorize:
            category = ['container', 'video', 'audio', 'image', 'document']
            for c in category:
                row_dict[c] = []

            for row in row_list:
                if 'type' in row and row['type'] == 'container':
                    row_dict['container'].append(row)
                elif 'category' in row and row['category'] in row_dict:
                    row_dict[row['category']].append(row)

            for c in category:
                if not row_dict[c]:
                    del row_dict[c]
        else:
            row_dict['file'] = row_list

        if self.STOPWATCH:
            print "Elapsed Time : {}".format(time.time() - starttime)

        return row_dict

    def search_query(self, id, query):
        """ TODO """
        pass

    def last(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT max(_id) FROM tree")
        result, = cursor.fetchone()
        cursor.execute("SELECT uid FROM tree WHERE _id=%s", (result, ))
        result, = cursor.fetchone()
        cursor.close()
        return self.browse_metadata(result)

    def tree(self, id=ROOT, depth=0, mode='view'):
        if self.STOPWATCH:
            starttime = time.time()
        buffer = []
        top = self.browse_metadata(id)
        list = [(id, top['name'])]
        dcount, fcount = self._tree(list, 0, [], depth, buffer, mode)
        if self.STOPWATCH:
            print "Elapsed Time : {}".format(time.time() - starttime)

        dstr = {'1': "directory"}.get(str(dcount), "directories")
        fstr = {'1': "file"}.get(str(fcount), "files")
 
        if mode == "compare":
            buffer.pop(0)
            buffer.insert(0, self.fullpath(id) + "\n")
            buffer.append("\n%d %s, %d %s\n" % (dcount, dstr, fcount, fstr))
        else:
            print "\n%d containers, %d items\n" % (dcount, fcount)

        return ''.join(buffer)

    def _tree(self, list, depth, map, maxdepth, buffer, mode):
        if maxdepth != 0 and depth > maxdepth:
            return

        fcount, dcount = 0, 0
        for index in xrange(len(list)):
            space = ""
            for i in map:
                if i:
                    space += "    "
                else:
                    space += "|   "
            if index == len(list) - 1:
                space += "`-- "
                is_last = True
            else:
                space += "|-- "
                is_last = False
            if mode == "compare":
                output = space + "[%7s]  " % list[index][0] + list[index][1]
                output = output[4:]
            else:
                output = space + " " + list[index][1] + " [%s]" % list[index][0]
                print output

            buffer.append(output + "\n")

            rows = self.browse_children(list[index][0])
            child_list = []
            for i in xrange(len(rows)):
                child_list.append((rows[i]["uid"], rows[i]["name"]))
                if rows[i]['type'] == 'container':
                    dcount += 1
                else:
                    fcount += 1

            d, f = self._tree(child_list, depth + 1, map + [is_last], maxdepth, buffer, mode)
            dcount += d
            fcount += f
        return dcount, fcount

    def _get_uid(self, fullpath):
        fullpath = os.path.realpath(fullpath)
        st = os.stat(fullpath)
        uid = str(st.st_ino)
        if uid == '2':
            if os.path.ismount(fullpath) and fullpath != '/':
                uid = os.path.basename(fullpath)
        return uid

    def get_file_info(self, fullpath):
        node = {}
        fullpath = os.path.realpath(fullpath)
        if not os.path.exists(fullpath):
            return

        st = os.stat(fullpath)

        node['uid'] = self._get_uid(fullpath)
        node['name'] = os.path.basename(fullpath)

        if os.path.isdir(fullpath):
            node['type'] = 'container'
            node['category'] = 'folder'
        else:
            node['type'] = 'item'
            node['category'] = 'document'

        node['pid'] = self._get_uid(os.path.dirname(fullpath))
        node['size'] = str(st.st_size)
        node['date'] = str(datetime.datetime.fromtimestamp(st.st_mtime).replace(microsecond=0))
        node['sortname'] = node['name']

        return node

    def _strip_tree_info(self, node):
        node['module'] = "file"
        if node['type'] == 'container':
            del node['size']

        for key in ['name', 'pid', 'type', 'sortname']:
            del node[key]

    def add_file(self, fullpath, verify=True, info=None):
        fullpath = os.path.realpath(fullpath)
        if info == None:
            node = self.get_file_info(fullpath)
        else:
            node = info

        if verify:
            tnode = self.get_tree(node['uid'])
            if tnode:
                if tnode['name'] != node['name'] or tnode['pid'] != node['pid'] \
                    or tnode['type'] != node['type']:
                    self.del_tree(tnode['uid'])
                    self.del_data(tnode['uid'])
                else:
                    return

        log.debug("[ADD] " + fullpath)
        atype = node['type']
        uid = node['uid']

        self.add_tree(node)
        self._strip_tree_info(node)
        self.add_data(node)

        if atype == 'item':
            self.push(uid, fullpath)

    def modify_file(self, fullpath):
        fullpath = os.path.realpath(fullpath)
        log.debug("[MOD] " + fullpath) 
        node = self.get_file_info(fullpath)

        self.del_data(node['uid'])
        self.delete_thumbnail(node['uid'])
        atype = node['type']
        uid = node['uid']

        self._strip_tree_info(node)
        self.add_data(node)

        if atype == 'item':
            self.push(uid, fullpath)

    def delete_file(self, fullpath):
        fullpath = os.path.realpath(fullpath)
        log.debug("[DEL] " + fullpath)
        uid = self.uid(fullpath)
        if uid:
            self.del_tree(uid)
            self.del_data(uid)
            self.delete_thumbnail(uid)
            self._del_category(uid)
        else:
            log.error('UID is none. Cannot continue the operation.')

    def move_file(self, srcpath, dstpath):
        srcpath = os.path.realpath(srcpath)
        dstpath = os.path.realpath(dstpath)
        log.debug("[MOV] " + srcpath + "->" + dstpath)
        snode_uid = self.uid(srcpath)
        dnode = self.get_file_info(dstpath)
        if snode_uid:
            self.mod_tree(snode_uid, dnode)
        else:
            log.error('UID is none. Cannot continue the operation.')

    def delete_thumbnail(self, uid):
        name = os.path.join(settings.get("thumbnail", "path"), uid) + ".*"
        for file in glob(name):
            os.remove(file)

    def add_fullpath(self, fullpath):
        fullpath = os.path.realpath(fullpath)
        lpath = fullpath.split("/")
        if lpath[-1] == "":
            del lpath[-1]
        path = "/"
        for name in lpath:
            if name == "":
                continue
            path = os.path.join(path, name)
            self.add_file(path, True)

    def scan(self, topdir, verify=True):

        topdir = os.path.realpath(topdir)
        log.info("Scan directory (verify={}) : {}".format(str(verify), topdir))
        if self.STOPWATCH:
            starttime = time.time()

        self.add_fullpath(topdir)

        if verify:
            result = self.verify(topdir)
        else:
            result = {'add':0, 'move':0, 'delete':0}
            for base, dirs, files in os.walk(topdir):
                for dir in dirs:
                    if not check_deny_file(dir):
                        self.add_file(os.path.join(base, dir), verify)
                        result['add'] += 1
                for file in files:
                    if not check_deny_file(file):
                        self.add_file(os.path.join(base, file), verify)
                        result['add'] += 1

        if self.STOPWATCH:
            print "Elapsed Time : {}".format(time.time() - starttime)

        log.info("Scan Finished : {}".format(str(verify), topdir))
        return result

    def verify(self, topdir):
        result = {'add':0, 'move':0, 'delete':0}
        cursor = self.conn.cursor()
        todo = [topdir]
        while len(todo) > 0:
            dir = todo.pop(0)
            id = self._get_uid(dir)
            cursor.execute("SELECT name, uid FROM tree WHERE pid=%(uid)s", {'uid':id})
            db_list = cursor.fetchall()
            db_list.sort()
            miss = []
            flist = os.listdir(dir)
            flist.sort()

            for f in flist:
                fpath = os.path.join(dir, f)
                if not check_deny_file(fpath):
                    uid = self._get_uid(fpath)

                    missed = True
                    for db_name, db_uid in db_list:
                        if db_name == f and db_uid == uid:
                            clog.debug("[1-1] PASS: " + db_name)
                            db_list.remove((f, uid))
                            missed = False
                            break
                        elif db_name == f:
                            self.cut_tree(db_uid)
                            break
                    if missed:
                        miss.append(f)

                    if os.path.isdir(fpath):
                        todo.append(fpath)

            for only_in_db, uid in db_list:
                self.cut_tree(uid)
                clog.debug("[2] Remaining item: " + str(only_in_db))
            for only_in_fs in miss:
                only_in_fs = os.path.join(dir, only_in_fs)
                file_node = self.get_file_info(only_in_fs)
                db_node = self.get_tree(file_node['uid'])

                if db_node == None:
                    self.add_file(only_in_fs, verify=False, info=file_node)
                    result['add'] += 1
                    clog.debug("[3-1] Missing item: " + str(only_in_fs))
                else:
                    db_node.update(self.get_data(file_node['uid']))

                    if db_node['type'] == file_node['type'] and db_node['size'] == file_node['size'] and db_node['date'] == file_node['date']:
                        self.mod_tree(file_node['uid'], 
                            {'name': os.path.basename(only_in_fs), 'pid': file_node['pid']})
                        result['move'] += 1
                        clog.debug("[3-3] Missing item :" + str(only_in_fs))
                    else:
                        self.del_tree(file_node['uid'])
                        self.del_data(file_node['uid'])
                        result['delete'] += 1
                        self.add_file(only_in_fs, verify=False, info=file_node)
                        result['add'] += 1
                        clog.debug("[3-2] Missing item: " + str(only_in_fs))


        cursor.close()
        return result

    def set_push_func(self, func):
        log.debug("push queue function is set: " + str(func))
        self.push_func = func

    def push(self, uid, filename):
        if self.push_func:
            self.push_func((uid, filename))

    """ Utility function for Contents """

    def _has_keys(self, keys, data):
        for key in keys:
           if key not in data:
               return False
        return True
    def _check_valid_id(self, id):
        if type("") != type(id):
            return False
        return True

""" End of Class """

""" Move to util module """

def random_str(length):
    return ''.join(random.choice(string.letters) for i in xrange(length))

def _make_random_tree(dir, count, curcount, maxcount, curdepth, maxdepth):
    dir_count = random.randrange(1, max(count, 2))
    file_count = count - dir_count

    for i in range(dir_count):
        name = os.path.join(dir, "%07d_" % curcount + random_str(8))
        os.mkdir(name)
        curcount += 1
        if curcount > maxcount:
            raise Exception
    for i in range(file_count):
        name = os.path.join(dir, "%07d_" % curcount + random_str(8))
        file = open(name, 'w')
        file.write("hi")
        file.close()
        curcount += 1
        if curcount > maxcount:
            raise Exception

    if curdepth >= maxdepth:
        return
    for d in os.listdir(dir):
        if not os.path.isdir(os.path.join(dir, d)):
            continue
        _make_random_tree(os.path.join(dir, d), 
                               max(2, random.randrange(1, max(2, count / 2))), 
                               curcount + 1, maxcount, curdepth + 1, maxdepth)

def make_random_tree(topdir, count=100, depth=5):
    if count < depth * 2:
        count = depth * 2

    onelevel_count = count / depth
    _make_random_tree(topdir, onelevel_count, 0, count, 1, depth)
    return topdir

""" Move to util module """

content = Content()

if __name__ == "__main__":
    #content.STOPWATCH = True
    #content.rebuild()
    #content.scan("/root/mediaplat/test/linux-3.0.8", False)
    #content.scan("/root/mediaplat/test/linux-3.0.8")
    #content.scan("/media", False)
    #os.rename("/media/root", "/media/root2")
    #result = content.scan("/media", False)
    #result = content.scan("/media")
    #result = content.scan("/mnt/disk/default/Multimedia")
    #content.tree()
    #print content.browse_metadata("image_all_28201208")

    #print content.fullpath('199820')
    print content.uid('/media/root////')

    #print result
    #os.rename("/media/root2", "/media/root")
    ##content.STOPWATCH = False

    #content.search_keyword("mp")
    #print content.tree("66", mode="compare")
    #print content.fullpath("66")

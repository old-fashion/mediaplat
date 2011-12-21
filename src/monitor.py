import os, sys
import pyinotify
import time
import pdb
from util import *
from log import log
from log import clog
from content import content
from threading import Timer

INITIAL_TIMER_INTERVAL = 10
TIMER_INTERVAL = 5

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self):
        self._moved_from_cookie_prev = 0
        self._moved_from_file = ''
        self.up_to_date = True
        self.event_dir_list = []

    def process_IN_CREATE(self, event):
        self.check_delete_file(event)
        filename = event.pathname

        if not check_deny_file(filename):
            clog.debug('[CREATE] filename: %s' % filename)

    def process_IN_CLOSE_WRITE(self, event):
        self.check_delete_file(event)
        filename = event.pathname

        if not check_deny_file(filename):
            if not os.path.exists(filename):
                return
            node = content.get_file_info(filename)
            if not node:
                return

            # Modify existing record
            ret = content.exist(node['uid'], node['size'], node['date'])
            if ret == 'MODIFIED':
                clog.debug('[WRITE] MODIFIED: %s' % filename)
                content.modify_file(filename)
                self.update_event_dir_list(filename)
                self.up_to_date = False
            # Insert New Record
            elif ret == 'NEW_FILE':
                clog.debug('[WRITE] CREATED: %s' % filename)
                content.add_file(filename, True, node)
                self.update_event_dir_list(filename)
                self.up_to_date = False
            # Already in the DB.(For Samba event)
            elif ret == 'SAME_FILE':
                pass

    def process_IN_DELETE(self, event):
        self.check_delete_file(event)
        filename = event.pathname

        if not check_deny_file(filename):
            clog.debug('[DELETE] filename: %s' % filename)
            content.delete_file(filename)
            self.update_event_dir_list(filename)
            self.up_to_date = False

    def process_IN_MOVED_FROM(self, event):
        self.check_delete_file(event)
        filename = event.pathname

        clog.debug('UID existence check..')
        if not content.uid(filename):
            return

        if self._moved_from_cookie_prev == 0:
            self._moved_from_cookie_prev = event.cookie
            self._moved_from_file = event.pathname

        clog.debug('[MV_FROM] filename: %s' % event.pathname)
        self.update_event_dir_list(filename)
        self.up_to_date = False

    def process_IN_MOVED_TO(self, event):
        dst_path = event.pathname
        node = content.get_file_info(dst_path)

        # New Contents came in.
        if event.src_exist == False:
            if not check_deny_file(dst_path):
                clog.debug('[MOVED_TO] Created: %s' % dst_path)
                content.add_file(dst_path, True, node)
                self.update_event_dir_list(dst_path)
                self.up_to_date = False
        else:
            clog.debug('UID existence check..')
            uid = content.uid(event.src_pathname)
            # New contents came in.(This should be a dir creation on Samba.)
            if not uid:
                log.debug('UID doesn\'t exists in DB. Adding file...')
                if not check_deny_file(dst_path):
                    clog.debug('[MOVED_TO] Created: %s' % dst_path)
                    content.add_file(dst_path, True, node)
                    self.update_event_dir_list(dst_path)
                    self.up_to_date = False
            # Moved inside the content directory
            else:
                clog.debug('========= Before updating watches=========')
                for w in event.wm.watches.values():
                    clog.debug('wd: %d, path: %s' % (w.wd, w.path))
                clog.debug('==========================================')

                # Update Watch
                if (event.mask & pyinotify.IN_ISDIR) :
                    src_path = event.src_pathname

                    for w in event.wm.watches.values():
                        if w.path == src_path:
                            w.path = dst_path

                    clog.debug('========== After updating watches =============')
                    for w in event.wm.watches.values():
                        clog.debug('wd: %d, path: %s' % (w.wd, w.path))
                    clog.debug('===============================================')

                    src_path_len = len(src_path)
                    sep_len = len(os.path.sep)

                    for w in event.wm.watches.values():
                        if w.path.startswith(src_path):
                            # Note that dest_path is a normalized path.
                            w.path = os.path.join(dst_path, w.path[src_path_len + sep_len:])
                            #log.debug('[MOVED_TO] updated watch path: %s' % w.path)

                    clog.debug('======== After updating watch dependencies ==========')
                    for w in event.wm.watches.values():
                        clog.debug('wd: %d, path: %s' % (w.wd, w.path))
                    clog.debug('=====================================================')

                clog.debug('[MOVED_TO] Moved: %s' % dst_path)
                content.move_file(event.src_pathname, dst_path)
                self.update_event_dir_list(dst_path)
                self.up_to_date = False

                self._moved_from_cookie_prev = 0
                self._moved_from_file = ''

    def check_delete_file(self, event):
            # No previous MOVED_FROM event.
            if self._moved_from_cookie_prev == 0:
                return

            # One of the other events except MOVED_FROM came in.
            elif event.mask != pyinotify.IN_MOVED_TO and event.mask != pyinotify.IN_MOVED_FROM:
                clog.debug('[1] No MOVED_* Event. Removing previous MOVED_FROM file.')
                content.delete_file(self._moved_from_file)
                self.up_to_date = False
                self._moved_from_cookie_prev = 0
                self._moved_from_file = ''

            # Another MOVED_FROM event came in. Delete previous MOVED_FROM file.
            elif event.mask == pyinotify.IN_MOVED_FROM:
                clog.debug('[2] Another MOVED_FROM event. Removing previous MOVED_FROM file.')
                content.delete_file(self._moved_from_file)
                self.up_to_date = False
                self._moved_from_cookie_prev = event.cookie
                self._moved_from_file = event.pathname
            else:
                log.exception('[ERROR] Unexpected case!')

    def update_event_dir_list(self, filename):
        dirname = os.path.dirname(filename)

        if len(self.event_dir_list) == 0:
            self.event_dir_list.append(dirname)
        else:
            for dir in self.event_dir_list:
                if dirname == dir:
                    #log.debug('Already in the list. Returning..')
                    return
                elif dirname.startswith(dir):
                    #log.debug('Parent is in the list. Returning..')
                    return
                elif dir.startswith(dirname):
                    #log.debug('Replace children with a parent.')
                    for dir_ in self.event_dir_list:
                        self.event_dir_list.remove(dir_)
                    self.event_dir_list.append(dirname)
                    return

            #log.debug('New event dir! Appending to the list..')
            self.event_dir_list.append(dirname)

class Monitor(object):
    def __init__(self, paths):
        self.wm = pyinotify.WatchManager()
        mask = pyinotify.IN_CREATE | pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO | pyinotify.IN_DELETE | pyinotify.IN_CLOSE_WRITE # watched events

        self.notifier = pyinotify.ThreadedNotifier(self.wm, default_proc_fun=EventHandler())
        #self.notifier = pyinotify.ThreadedNotifier(self.wm)
        self.running = False
        self.paths = paths
        self.timer = Timer(INITIAL_TIMER_INTERVAL, self.partial_scan_for_recent_events)

        # Add watches with 'auto-add' option enabled..
        for path in paths:
            self.wm.add_watch(path, mask, rec=False, auto_add=True)
            for base, dirs, files in os.walk(path):
                for dir in dirs:
                    if not dir.startswith('.'):
                        self.wm.add_watch(os.path.join(base, dir), mask, rec=False, auto_add=True)

        # each wdd is of dict format (path: wd)
        for path in paths:
            clog.debug('Monitored Paths: %s', path)

    def get_status(self):
        return self.running

    def get_scan_status(self):
        return self.notifier._rescan_required

    def start(self):

        #content.cleanup()
        #content.buildup()

        for path in self.paths:
            result = content.scan(path)

        self.notifier.start()
        self.running = True
        log.info('Monitor started.')

        self.timer.start()

    def stop(self):
        self.notifier.stop()
        self.timer.cancel()
        log.info('Monitor stopped.')

    def partial_scan_for_recent_events(self):
        status = self.get_scan_status()

        # Monitor is idle.
        if status == True:
            # Some events happened after previous scanning.
            if not self.notifier._default_proc_fun.up_to_date:
                clog.debug('Some events occurred. Start scanning the below directories...')
                for dir in self.notifier._default_proc_fun.event_dir_list:
                    clog.debug('| %s |' % dir)

                clog.debug('=============== End of Event Dirs ===============')

                for dir in self.notifier._default_proc_fun.event_dir_list:
                    content.scan(dir)

                self.notifier._default_proc_fun.event_dir_list = []
                self.notifier._default_proc_fun.up_to_date = True

                clog.debug('Finished Partial Scanning...')

        self.timer = Timer(TIMER_INTERVAL, self.partial_scan_for_recent_events)
        self.timer.start()

if __name__ == '__main__':
    try:
        paths = []
        num_args = len(sys.argv)
        for i in range(1, num_args):
            paths.append(sys.argv[i])
    except IndexError:
        print 'use: %s path' % sys.argv[0]
    else:
        monitor = Monitor(paths)
        monitor.start()

        time.sleep(20)

        if monitor.get_scan_status():
            print 'You may scan now!'
        else:
            print 'Monitor is busy!'

        if monitor.get_status():
            monitor.stop()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Daemonize Module """

import os
import sys
import json
import signal
import socket
import SocketServer
from struct import pack, unpack, calcsize
import setproctitle

from log import log 
from monitor import Monitor
from config  import settings
from plugin_manager import plugin_manager
from content import content
from bonjour import Bonjour

SOCKET_FILE = "/var/run/mediaplat/mediaplat_sock"
SOCKET_HEADER_FMT = "@hq"
CHUNK_SIZE = 4096

class CommunicateError(Exception):
    """ Communicate error between platform daemon """

class ThreadedUnixSocketServer(SocketServer.ThreadingUnixStreamServer):
    """ multi-thread unix socket server class """
    pass

class ThreadedUnixSocketRequestHandler(SocketServer.StreamRequestHandler):
    """ request handler class

        main methos are setup, handle, finish
        execution sequence is setup, handle and finish
    """

    def setup(self):
        """ handler entry point

            Called before the handle() method to perform any initialization
            actions required.
        """
        pass


    def do_action(self, request):
        """ method call entry point

            Called method of requested module 
        """
        module = request.get('module')
        action = request.get('action')
        params = request.get('params')

        if params:
            return getattr(eval(module), action)(*params)
        else:
            return getattr(eval(module), action)()

    def send_response(self, response):
        response = json.dumps(response)
        total_response_len = len(response)
        sended_len = self.request.send(response)
        if total_response_len != sended_len:
            log.error('comm response data missmatch send_req {} != sended {}'.format(total_response_len, sended_len))

    def handle(self):
        """ main request handle method

        This function will be executed as a seperated thread.
        1. receive input message
        2. do action
        3. send result message
        """
        header_size = calcsize(SOCKET_HEADER_FMT)
        header = self.request.recv(header_size)
        mode, data_len = unpack(SOCKET_HEADER_FMT, header)

        data = ''
        remain_data_len = int(data_len)
        while True:
            if remain_data_len < CHUNK_SIZE:
                cur_recv_data_len = remain_data_len
            else:
                cur_recv_data_len = CHUNK_SIZE
            cur_data = self.request.recv(cur_recv_data_len)

            if cur_recv_data_len != len(cur_data):
                log.error('ERROR: daemon data get length error send(%d) != recv(%d)' % (cur_recv_data_len, len(cur_data)))
                self.send_response({'result': False, 'data': 'Error occured during communicate with Daemon'})
                return

            data += cur_data

            remain_data_len -= cur_recv_data_len
            if remain_data_len == 0:
                break

        req_param = {}
        req_param = json.loads(data)

        # call service manager
        try:
            response_data = self.do_action(req_param)
            response = {'result': True, 'data': response_data}
        except:
            log.exception('Failed to request mediaplat')
            response = {'result': False, 'data': 'Unknown error occured'}

        self.send_response(response)


    def finish(self):
        """ handler exit point

            Called after the handle() method to perform any clean-up actions
            required.
        """
        pass

class Mediaplat(object):
    """ Daemonize Class """

    def __init__(self):
        """ 
        Constructor of Daemon Class
        """
        # register signal handlers
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        signal.signal(signal.SIGTTIN, signal.SIG_IGN)
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        signal.signal(signal.SIGINT,  self.__signal_handler_terminate)
        signal.signal(signal.SIGTERM, self.__signal_handler_terminate)

        try:
            self.server = ThreadedUnixSocketServer(SOCKET_FILE, 
                ThreadedUnixSocketRequestHandler)
        except:
            log.error('address already in use')
            sys.exit(1)

    def __signal_handler_terminate(self, signalnum, frame):
        """ 
        Signal handler for terminate signals.

        Signal handler for the "signal.SIGTERM" signal. Raise a "SystemExit"
        exception to do something for that signal
        """
        log.warning("Terminating on signal %(signalnum)r" % locals())
        raise KeyboardInterrupt


    def run(self, options):
        """ 
        Beginning monitor thread. 
        Sleep and wait for interrupt. 
        """
        # Start plugin manager
        plugin_manager.load_all_plugins()
        # Start monitor thread
        paths = settings.get('core', 'base').split(',')

        content.set_push_func(plugin_manager.push_queue)
        if options.rebuild:
            content.rebuild()

        self.monitor = Monitor(paths)
        #self.monitor.set_push_queue_func(plugin_manager.push_queue)
        self.monitor.start()

        # Register bonjour
        if settings.get('core', 'aggregation') == 'True':
            self.bonjour = Bonjour()
            self.bonjour.register(socket.gethostname(), '_mediaplat._tcp', 9020)

        self.server.serve_forever()

    def stop(self):
        """ 
        stop the server and remove socket file.
        Terminate all children threads and wait until terminate. 
        """
        try:
            os.unlink(SOCKET_FILE)
        except:
            pass

        if getattr(self, 'bonjour', None):
            self.bonjour.unregister()

        self.server.shutdown()

        self.monitor.stop()
        plugin_manager.stop() 

    def __enter__(self):
        """ 
        Entry point of Daemon Class for python 'with' statement
        """
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        """ 
        Clean up function of Daemon Class for python 'with' statement
        """
        self.stop()

    @classmethod
    def request(self, send_data, mode = 0):
        """ request daemon function

            @type  send_data: dict
            @param send_data: parameters related with service and action
            @type  mode: int 
            @param mode: request & response type
            @rtype: dict
            @return: {"error": int, "return_date": dict} dictionary
        """
        try:
            if not os.path.exists(SOCKET_FILE):
                raise CommunicateError

            encoded_send_data = json.dumps(send_data)
            total_send_len = len(encoded_send_data)
            send_header = pack(SOCKET_HEADER_FMT, mode, total_send_len)

            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(SOCKET_FILE)

            sock.send(send_header)
            if total_send_len <= CHUNK_SIZE:
                sended_len = sock.send(encoded_send_data)
                if total_send_len != sended_len:
                    log.error('comm send data missmatch send_req {0} != sended {1}'.format(total_send_len, sended_len))
                    raise CommunicateError
            else:
                remain_send_len = total_send_len
                current_send_len = 0
                current_sended_len = 0
                current_send_index = 0

                while True:
                    if remain_send_len < CHUNK_SIZE:
                        current_send_len = remain_send_len
                    else:
                        current_send_len = CHUNK_SIZE

                    current_send_data = encoded_send_data[current_send_index:
                        current_send_index + current_send_len]

                    current_sended_len = sock.send(current_send_data)
                    if current_send_len != current_sended_len:
                        log.error('comm send data missmatch send_req {0} != sended {1}'.format(current_send_len, current_send_data))
                        raise CommunicateError

                    remain_send_len -= current_send_len
                    current_send_index += current_send_len
                    if remain_send_len == 0:
                        break

            all_response = ""
            while True:
                response = sock.recv(CHUNK_SIZE)
                if not response:
                    break
                all_response += response

            sock.close()

            return json.loads(all_response)

        except (CommunicateError, socket.error):
            log.exception('request daemon comunication error')
            return {'result': False, 'data': 'request comunication error'}

if __name__ == '__main__':
    import argparse

    class options(object):
        rebuild = False

    setproctitle.setproctitle("mediaplatd") 
    parser = argparse.ArgumentParser(description = 'mediaplat main process')
    parser.add_argument('-r', '--rebuild', action = 'store_true',
            help = 'Rebuild database')
    parser.parse_args(namespace = options)

    try:
        daemoned_process = Mediaplat()
        daemoned_process.run(options)
    except KeyboardInterrupt:
        daemoned_process.stop()
    except NameError:
        pass

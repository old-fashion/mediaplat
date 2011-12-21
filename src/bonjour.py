# -*- coding: utf-8 -*-

import select
import pybonjour
from log import log

class Bonjour(object):

    def __init__(self):
        self.devices = []
        self.timeout = 1
        self.is_timeout = False

    def discovery(self, regtype):
        def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                             hosttarget, port, txtRecord):
            if errorCode == pybonjour.kDNSServiceErr_NoError:
                self.devices.append(hosttarget)

        def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                            regtype, replyDomain):
            if errorCode != pybonjour.kDNSServiceErr_NoError:
                return

            if not (flags & pybonjour.kDNSServiceFlagsAdd):
                log.debug('Bonjour service removed')
                return

            resolve_sdRef = pybonjour.DNSServiceResolve(0,
                                                        interfaceIndex,
                                                        serviceName,
                                                        regtype,
                                                        replyDomain,
                                                        resolve_callback)

            while True:
                ready = select.select([resolve_sdRef], [], [], self.timeout)
                if resolve_sdRef not in ready[0]:
                    log.debug('Bonjour discovery timeout reached')
                    self.is_timeout = True
                    break
                pybonjour.DNSServiceProcessResult(resolve_sdRef)
            resolve_sdRef.close()

        browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype,
                                                  callBack = browse_callback)
        try:
            while not self.devices and not self.is_timeout:
                ready = select.select([browse_sdRef], [], [])
                if browse_sdRef in ready[0]:
                    pybonjour.DNSServiceProcessResult(browse_sdRef)
        finally:
            browse_sdRef.close()
            return self.devices

    def register(self, name, regtype, port):
        def register_callback(sdRef, flags, errorCode, name, regtype, domain):
            if errorCode == pybonjour.kDNSServiceErr_NoError:
                log.debug('Registered service : name = {}, regtype = {}, domain = {}'.format(name, regtype, domain))

        self.sdRef = pybonjour.DNSServiceRegister(name = name,
                                             regtype = regtype,
                                             port = port,
                                             callBack = register_callback)

        while True:
            ready = select.select([self.sdRef], [], [])
            if self.sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(self.sdRef)
                break;

    def unregister(self):
        self.sdRef.close()

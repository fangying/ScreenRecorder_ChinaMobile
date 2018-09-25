# -*- coding: utf-8 -*-
import sys

import win32api
import win32con
import win32event
import win32service
import win32serviceutil
import servicemanager
import logging
import os
import configparser
from http.server import HTTPServer, CGIHTTPRequestHandler


class HTTPFilerServer(win32serviceutil.ServiceFramework):
    _svc_name_ = "HTTPFileServer"
    _svc_display_name_ = "HTTP File Server"
    _svc_description_ = "HTTP File Server"
    _listen_port = 8080

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._svc_runtime_dir = os.path.dirname(sys.argv[0])
        self.logger = self._getLogger()
        self._videos_dir = self._getVideoDir()
        self.config = configparser.ConfigParser(allow_no_value=True)
        self._readConfig()

    def _readConfig(self):
        cfg_path = os.path.join(os.path.dirname(sys.argv[0]), 'HTTPFileServer.ini')

        if os.path.exists(cfg_path):
            try:
                self.config.read(cfg_path)
                if self.config.has_section('listen_port'):
                    if self.config.has_option('listen_port', 'port'):
                        self._video_keep_period = self.config.getint('listen_port', 'port')
                        self.logger.info('read from cfg listen_port port=%d'
                                         % self._video_keep_period)
                    else:
                        self.logger.warn('''no config option 'port' found''')
                else:
                    self.logger.warn('no config section [listen_port] found')
            except configparser.Error as e:
                self.logger.warn('error parse config file, use default cfg port = %d'
                                 % self._listen_port)
                self.logger.warn(str(e))
        else:
            self.config.remove_section('listen_port')
            self.config.add_section('listen_port')
            self.config.set('listen_port', 'port', str(self._listen_port))

            with open(cfg_path, 'w') as cfg:
                self.config.write(cfg)
            self.logger.info('use default listen_port port=%d' % self._listen_port)

    def _getVideoDir(self):
        pwd = os.path.dirname(sys.argv[0])
        if os.path.exists(os.path.join(pwd, 'videos')):
            pass
        else:
            os.mkdir(os.path.join(pwd, 'videos'))

        return os.path.join(os.path.join(pwd, 'videos'))

    def _getLogger(self):

        logger = logging.getLogger('[HTTPFileServer]')
        dirpath = os.path.dirname(sys.argv[0])
        handler = logging.FileHandler(os.path.join(dirpath, self._svc_name_ + ".log"))

        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        return logger

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            self.logger.info('HTTP File Server is Starting')
            self.start()
            import time
            time.sleep(3)

            os.chdir(self._videos_dir)
            self.logger.info('HTTP File Server runs at local dir %s ' % self._videos_dir)
            httpd = HTTPServer(('', self._listen_port), CGIHTTPRequestHandler)
            httpd.serve_forever()

            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            self.logger.info('HTTP File Server Shutdown')
        except BaseException as e:
            self.logger.warn('Exception : %s' % e)
            self.SvcStop()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.logger.info('HTTP File Server is Stopping ...')
        self.stop()
        self.logger.info('HTTP File Server Service Stopped')
        win32event.SetEvent(self.stop_event)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def start(self):
        if not os.path.exists(self._svc_runtime_dir):
            os.mkdir(self._svc_runtime_dir)
            win32api.SetFileAttributes(self._svc_runtime_dir, win32con.FILE_ATTRIBUTE_HIDDEN)
        else:
            pass

    def stop(self):
        pass

    def log(self, msg):
        servicemanager.LogInfoMsg(str(msg))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(HTTPFilerServer)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(HTTPFilerServer)

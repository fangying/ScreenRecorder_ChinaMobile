# -*- coding: utf-8 -*-
import subprocess
import datetime
import logging
import socket
import time
import os
import re
import ctypes
import configparser
from datetime import datetime, timedelta


class ScreenRecorder():
    _video_keep_period = 8  # keep video for 8 days by default

    def __init__(self):
        # video_dir comes first
        self._prepareVideoDir()
        self.runtimeDir = os.path.dirname(os.path.realpath(__file__))
        self._video_dir = os.path.join(self.runtimeDir, 'videos')
        self._ffmpeg_exe = os.path.join(self.runtimeDir, 'ffmpeg.exe')
        self.logger = self._getLogger()
        self._ffmpeg_info = os.path.join(self.runtimeDir, 'ffmpeg_info.log')
        self.default_audio_dev = "virtual-audio-capturer"
        self.config = configparser.ConfigParser(allow_no_value=True)
        # call _readConfig here
        self._readConfig()

    def _readConfig(self):
        if os.path.exists('ScreenRecorder.ini'):
            try:
                self.config.read('ScreenRecorder.ini')
                if self.config.has_section('video_keep_period'):
                    if self.config.has_option('video_keep_period', 'period'):
                        self._video_keep_period = self.config.getint('video_keep_period', 'period')
                        self.logger.info('read from cfg video_keep_period period = %d'
                                         % self._video_keep_period)
                    else:
                        self.logger.warn('''no config option 'period' found''')
                else:
                    self.logger.warn('no config section [video_keep_period] found')
            except configparser.Error as e:
                self.logger.warn('error parse config file, use default cfg video_keep_period = %d'
                                 % self._video_keep_period)
                self.logger.warn(str(e))
        else:
            self.config.remove_section('video_keep_period')
            self.config.add_section('video_keep_period')
            self.config.set('video_keep_period', 'period', str(self._video_keep_period))
            with open('ScreenRecorder.ini', 'w') as cfg:
                self.config.write(cfg)
            self.logger.info('use default video_keep_period period = 8 days')

    def _prepareVideoDir(self):
        pwd = os.path.dirname(os.path.realpath(__file__))
        if os.path.exists(os.path.join(pwd, 'videos')):
            pass
        else:
            os.mkdir(os.path.join(pwd, 'videos'))

    def _getLogger(self):
        logger = logging.getLogger('[ScreenRecorder]')
        handler = logging.FileHandler(os.path.join(self.runtimeDir, "ScreenRecorder.log"))
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def killFFMpeg(self):
        if "ffmpeg" in os.popen('tasklist /FI "IMAGENAME eq "ffmpeg.exe"').read():
            os.system('TASKKILL /F /IM ffmpeg.exe')
            self.logger.info('Terminate previous ffmpeg')

    def rmOldVideo(self):
        if not os.path.exists(self._video_dir):
            return

        videos = list()
        for f in os.listdir(self._video_dir):
            if ".mkv" in f:
                videos.append(f)

        yestorday = datetime.now() - timedelta(days=self._video_keep_period)
        yestorday_str = str(yestorday.strftime('%Y-%m-%d-23-59-59'))
        for f in videos:
            ret = re.search('_.*.mkv', f)
            if ret:
                date = ret.group(0).strip("_|.mkv")
                if date < yestorday_str:
                    self.logger.info('Video %s is outdated and removed' % f)
                    os.remove(os.path.join(self._video_dir, f))

    def getAudioDevAlias(self):
        # find audio device alias using ffmpeg cmdline
        cmd = 'ffmpeg -list_devices true -f dshow -i dummy 2> %s' % self._ffmpeg_info
        sp = subprocess.Popen(list(cmd.split(' ')), shell=True)
        sp.communicate()

        # read result from file
        audio_device_alias = list()
        f = open(self._ffmpeg_info, encoding='utf-8')
        for line in f.readlines():
            if self.default_audio_dev in line:
                audio_device_alias.append(self.default_audio_dev)

            if 'Alternative name' in line and 'wave' in line:
                m = re.search('".*"', line)
                audio_device_alias.append(m.group(0))

        return audio_device_alias

    def doRecording(self):

        # using ip-dateinfo in output file name
        hostname = socket.getfqdn(socket.gethostname())
        ip_addr = socket.gethostbyname(hostname)

        date_info = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))

        video_name = ip_addr + "_" + date_info + ".mkv"
        video_path = os.path.join(self._video_dir, video_name)

        self.logger.info("hostname=%s ip=%s video_path=%s, ScreenRecorder started" % (hostname, ip_addr, video_path))

        audio_devs = self.getAudioDevAlias()
        if self.default_audio_dev not in audio_devs:
            self.logger.warn('no %s audio device found on host' % self.default_audio_dev)
            cmd = r'%s -f gdigrab -i desktop -framerate 10 -y %s' % (self._ffmpeg_exe, video_path)
        else:
            # user Screen Capturer Recorder Audio Device Here
            self.logger.info('audio device %s found on host' % self.default_audio_dev)
            cmd = r'%s -f dshow -i audio=%s -framerate 10 -f gdigrab -i desktop -y %s' % \
                  (self._ffmpeg_exe, self.default_audio_dev, video_path)

        cmd_list = list(cmd.split(' '))
        self.logger.info(cmd)

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            process = subprocess.Popen(cmd_list, startupinfo=startupinfo,
                                       stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                       shell=True)
            # hide windows console here
            whnd = ctypes.windll.kernel32.GetConsoleWindow()
            if whnd != 0:
                ctypes.windll.user32.ShowWindow(whnd, 0)
                ctypes.windll.kernel32.CloseHandle(whnd)

            sout, serr = process.communicate()
            if serr != None:
                self.logger.error(serr)
            if sout != None:
                self.logger.info(sout)

        except BaseException as e:
            self.logger.warn('Exception : %s' % e)


if __name__ == "__main__":
    sr = ScreenRecorder()
    sr.killFFMpeg()
    sr.rmOldVideo()
    sr.doRecording()

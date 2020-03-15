#!/usr/bin/env python

import dbus, subprocess, os, signal
from time import sleep

#### FUNCTIONS ####

def record_track(track_id):
    r = Recorder()
    s = SpotifyInterface()

    s.pause()

    playing = False

    r.start_recording()

    s.open(track_id)

    print("[RECORDER] PID: {}".format(r.pid))

    while not playing:
        playing = s.is_playing()

    while playing:
        playing = s.is_playing()
        sleep(1)

    print("[RECORDER] Stopping recording")

    r.stop_recording()

#### CLASSES ####

class Recorder:
    def __init__(self):
        self.pid = None

    def start_recording(self):
        cmd = "parec -d 0 | sox -S -t raw -b 16 -e signed -c 2 -r 44100 - recorded.wav"
        process = subprocess.Popen(
                cmd, 
                shell=True,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
                )
        self.pid = process.pid

    def stop_recording(self):
        pgid = os.getpgid(self.pid)
        os.killpg(pgid, signal.SIGINT)
        self.pid = None

class SpotifyInterface:
    def __init__(self):
        self.dbus_session = dbus.SessionBus()
        self.dbus_spotify_object = self.dbus_session.get_object("org.mpris.MediaPlayer2.spotify", "/org/mpris/MediaPlayer2")
        self.spotify_iface = dbus.Interface(self.dbus_spotify_object, dbus_interface="org.mpris.MediaPlayer2.Player")
        self.properties_iface = dbus.Interface(self.dbus_spotify_object, dbus_interface="org.freedesktop.DBus.Properties")

    def play(self):
        self.spotify_iface.Play()

    def pause(self):
        self.spotify_iface.Pause()

    def trigger(self):
        self.spotify_iface.PlayPause()

    def open(self, spotify_uri):
        self.spotify_iface.OpenUri(spotify_uri)

    def get_property(self, prop):
        return self.properties_iface.Get("org.mpris.MediaPlayer2.Player", prop)

    def is_playing(self):
        d = {"Playing":True, "Paused":False}
        prop = self.get_property("PlaybackStatus")
        return d[str(prop)]


#### MAIN ####



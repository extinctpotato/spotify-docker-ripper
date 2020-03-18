#!/usr/bin/env python3

import dbus, subprocess, os, signal, stat
from time import sleep

#### GLOBAL VARS ####
MUSIC_DIR = "/root/Music"

#### FUNCTIONS ####

def record_track(track_id):
    print("Starting record_track.")

    try:
        print("Changing dir to {}".format(MUSIC_DIR))
        os.chdir(MUSIC_DIR)

        s = SpotifyInterface()

        r = Recorder()

        s.pause()

        playing = False

        r.start_recording()

        s.open(track_id)

        print("parec and sox PID: {}".format(r.pid))

        while not playing:
            playing = s.is_playing()
        print("The music started playing.")

        sleep(1)

        m = s.get_meta()

        print("Artist:\t {}".format(m['artist']))
        print("Album:\t {}".format(m['album']))
        print("Title:\t {}".format(m['title']))

        r.set_meta(
                artist = m['artist'],
                album = m['album'],
                title = m['title'],
                )

        while playing:
            playing = s.is_playing()
            sleep(1)

        print("Stopping recording.")

        r.stop_recording()

        print("Removing silence.")

        r.remove_silence()

        print("Encoding to ogg.")

        r.oggenc()
    finally:
        to_delete = ["raw.wav", "nosilence.wav"]

        for f in to_delete:
            if os.path.isfile(f):
                print("Removing {}".format(f))
                os.remove(f)

def record_test():
    record_track("spotify:track:5treNJZ0gCdEO3EcWp9aDu")

def spotify_start(user=None, password=None):
    if user is None and password is None:
        print("Using credentials from environment.")
        user = os.environ["SPOTIFY_USER"]
        password = os.environ["SPOTIFY_PASS"]
    else:
        print("Using credentials provided as arguments.")

    user_prefs = '''
    audio.sync_bitrate_enumeration=4
    audio.play_bitrate_enumeration=4
    app.player.autoplay=false
    '''

    launcher_path = "/usr/bin/spotify-launcher"

    user_path = "/root/.config/spotify/Users/{}-user".format(user)

    spotify_creds = "spotify --username={} --password={}".format(user, password)

    with open(launcher_path, "w") as f:
        f.write("#!/bin/sh\n")
        f.write("spotify --username={} --password={}".format(user, password))

    os.chmod(launcher_path, stat.S_IRWXU)

    os.makedirs(user_path, exist_ok=True)

    with open(os.path.join(user_path, "prefs"), "w") as f:
        f.write(user_prefs)

    s1 = subprocess.Popen(
            spotify_creds,
            shell=True,
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            )

def spotify_stop():
    subprocess.Popen("killall spotify", shell=True)

#### CLASSES ####

class Recorder:
    def __init__(self, artist="u", album="u", title="u"):
        u = "Unknown"
        self.pid = None
        self.filename = "{} - {}".format(artist, title)
        self.artist = u
        self.album = u
        self.title = u

    def set_meta(self, artist, album, title):
        self.filename = "{} - {}".format(artist, title)
        self.artist = artist
        self.album = album
        self.title = title

    def start_recording(self):
        cmd = "parec -d 0 | sox -q -t raw -b 16 -e signed -c 2 -r 44100 - raw.wav"
        process = subprocess.Popen(
                cmd, 
                shell=True,
                preexec_fn=os.setsid
                )
        self.pid = process.pid

    def stop_recording(self):
        pgid = os.getpgid(self.pid)
        os.killpg(pgid, signal.SIGINT)
        self.pid = None

    def remove_silence(self):
        cmd = "sox -q raw.wav nosilence.wav --norm=-0.1 silence -l 1 0.1 0% reverse silence -l 1 0.1 0% reverse"
        process = subprocess.run(
                cmd,
                shell=True,
                )

    def oggenc(self):
        cmd = 'oggenc nosilence.wav -Q -q 9 -o "final.ogg" -t "{}" -a "{}" -l "{}"'.format(
                self.title,
                self.artist,
                self.album
                )
        process = subprocess.run(cmd, shell=True)
        os.rename("final.ogg", "{}.ogg".format(self.filename))


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
        d = {"Playing":True, "Paused":False, "Stopped":False}
        prop = self.get_property("PlaybackStatus")
        return d[str(prop)]

    def get_meta(self):
        meta = self.get_property("Metadata")
        d = {"artist":"","album":"","title":""}
        d['artist'] = str(meta['xesam:artist'][0])
        d['album'] = str(meta['xesam:album'])
        d['title'] = str(meta['xesam:title'])
        return d


#### MAIN ####

if __name__ == '__main__':
    print("test")

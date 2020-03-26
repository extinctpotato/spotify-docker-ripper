#!/usr/bin/env python3

import dbus, subprocess, os, signal, stat, logging, psutil
from time import sleep
from sparrow.spotifyapi import Track
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import Picture
from base64 import b64encode

#### GLOBAL VARS ####
MUSIC_DIR = "/root/Music"
DBUS_ENV = "/tmp/dbus.env"

#### FUNCTIONS ####
def dbus_env():
    with open(DBUS_ENV, "r") as f:
        env = f.read().split("\n")
    e1 = env[0].split("=", 1)
    e2 = env[1].split("=")
    logging.debug(e1[0])
    logging.debug(e1[1])
    logging.debug(e2[0])
    logging.debug(e2[1])
    os.environ[e1[0]] = e1[1]
    os.environ[e2[0]] = e1[1]

def write_ogg_coverart(ogg_file_path, cover_bytes, dimensions):
    ogg_file = OggVorbis(ogg_file_path)

    picture = Picture()
    picture.data = cover_bytes
    picture.type = 3
    picture.mime = u"image/jpeg"
    picture.width = dimensions[0]
    picture.height = dimensions[1]
    picture.depth = 24

    picture_data = picture.write()
    encoded_data = b64encode(picture_data)
    comment = encoded_data.decode("ascii")

    ogg_file["metadata_block_picture"] = [comment]
    ogg_file.save()

def uri_split(uri):
    return uri.split(":")

def is_track_uri(uri):
    s = uri_split(uri)
    if not s[0] == "spotify":
        return False
    if not s[1] == "track":
        return False
    return True

def is_spotify_running():
    if "spotify" in (p.name() for p in psutil.process_iter()):
        return True
    return False

def job_desc_to_tid(desc):
    splt = desc.split("(")
    if splt[0] == "sparrow.record_track":
        tid = splt[1].split("'")[1]
    else:
        tid = ""
    return tid

def record_track(track_id, logfile=False):
    track_id_literal = uri_split(track_id)[2]

    if logfile:
        os.makedirs("/var/log/sparrow", exist_ok=True)
        print("Logging to file.")
        logging.basicConfig(
                filename='/var/log/sparrow/{}.log'.format(track_id_literal), 
                filemode='w',
                format="%(asctime)s %(levelname)s %(message)s"
                )
        logging.root.setLevel(logging.NOTSET)
    else:
        logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
        logging.root.setLevel(logging.NOTSET)
    dbus_env()
    logging.info("Starting record_track.")

    try:
        logging.info("Changing dir to {}".format(MUSIC_DIR))
        os.chdir(MUSIC_DIR)

        s = SpotifyInterface()

        r = Recorder()

        s.pause()

        playing = False

        r.start_recording()

        s.open(track_id)

        logging.info("parec and sox PID: {}".format(r.pid))

        while not playing:
            playing = s.is_playing()
        logging.info("The music started playing.")

        sleep(1)

        m = s.get_meta()

        logging.info("Artist:\t {}".format(m['artist']))
        logging.info("Album:\t {}".format(m['album']))
        logging.info("Title:\t {}".format(m['title']))

        r.set_meta(
                artist = m['artist'],
                album = m['album'],
                title = m['title'],
                )

        while playing:
            playing = s.is_playing()
            sleep(1)

        logging.info("Stopping recording.")

        r.stop_recording()

        logging.info("Removing silence.")

        r.remove_silence()

        logging.info("Encoding to ogg.")

        r.oggenc(track_id_literal)

        logging.info("Connecting to Spotify API.")

        t = Track(track_id)
        t.download_cover()
        
        logging.info("Writing cover art to ogg file.")
        write_ogg_coverart("{}.ogg".format(track_id_literal), t.cover_bytes, t.cover_dimensions)
    finally:
        to_delete = ["raw.wav", "nosilence.wav"]

        for f in to_delete:
            if os.path.isfile(f):
                logging.info("Removing {}".format(f))
                os.remove(f)

def record_test(logfile=False):
    record_track("spotify:track:5treNJZ0gCdEO3EcWp9aDu", logfile=logfile)

def spotify_start(user=None, password=None):
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
    logging.root.setLevel(logging.NOTSET)
    dbus_env()
    if user is None and password is None:
        logging.info("Using credentials from environment.")
        user = os.environ["SPOTIFY_USER"]
        password = os.environ["SPOTIFY_PASS"]
    else:
        logging.info("Using credentials provided as arguments.")

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

    def oggenc(self, filename=None):
        if filename is not None:
            self.filename = filename
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
        try:
            d['artist'] = str(meta['xesam:artist'][0])
            d['album'] = str(meta['xesam:album'])
            d['title'] = str(meta['xesam:title'])
        except IndexError:
            pass
        return d


#### MAIN ####

if __name__ == '__main__':
    logging.info("test")
    testing()

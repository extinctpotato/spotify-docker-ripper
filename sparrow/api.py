import os, glob, shutil
from math import ceil
from mutagen.oggvorbis import OggVorbis
from flask import request, Response, Flask, jsonify, make_response, send_from_directory
from redis import Redis
import pickle
pickle.HIGHEST_PROTOCOL = 4
from threading import Lock
from rq import Queue
from rq.job import Job
from sparrow import spotifyapi as sapi
from sparrow import is_track_uri, dbus_env, is_spotify_running, job_desc_to_tid
from sparrow import SpotifyInterface

sparrow_api = Flask(__name__)
redis_con = Redis()
q = Queue(connection=redis_con)
lock = Lock()

T = 9600

MUSIC_DIR = "/root/Music"
LOG_DIR = "/var/log/sparrow"
EXPORT_DIR = "/mnt/library"

def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return ceil(n * multiplier) / multiplier

@sparrow_api.route("/")
def index():
    return make_response("Argh!", 200)

@sparrow_api.route("/status", methods=["GET"])
def test_route():
    dbus_env()
    s_running = is_spotify_running()
    j = {}
    j['pending_jobs'] = len(q.jobs)
    j['spotify_running'] = is_spotify_running()
    if s_running:
        s = SpotifyInterface()
        j['playback_status'] = s.get_property('PlaybackStatus')
        j.update(s.get_meta())

    return make_response(jsonify(j), 200)

@sparrow_api.route("/sapi/search", methods=["GET"])
def sapi_search():
    q = request.args.get('q')
    full = request.args.get('full')

    sr = sapi.search(q)

    if full == 'true':
        return make_response(jsonify(sr), 200)
    else:
        j = {"results":[]}
        
        for result in sr['tracks']['items']:
            filtered = {}
            filtered['album'] = result['album']['name']
            filtered['artists'] = []
            for artist in result['artists']:
                filtered['artists'].append(artist['name'])
            filtered['title'] = result['name']
            filtered['track_id'] = result['uri']
            j['results'].append(filtered)

        return make_response(jsonify(j), 200)

@sparrow_api.route("/list/jobs", methods=["GET"])
def joblist():
    j = {"running_job":{},"pending_jobs":[]}

    current_job_test = q.started_job_registry.get_job_ids()

    if current_job_test:
        current_job_id = current_job_test[0]
        current_job = Job.fetch(current_job_id, connection=redis_con)
        current_job_dict = current_job.to_dict()
        del current_job_dict['data']
        del current_job_dict['origin']
        current_job_dict['track_id'] = job_desc_to_tid(current_job_dict['description'])
        j['running_job'] = current_job_dict

    if q.jobs:
        for pending in q.jobs:
            pending_copy = pending.to_dict()
            del pending_copy['data']
            del pending_copy['origin']
            pending_copy['track_id'] = job_desc_to_tid(pending_copy['description'])
            j['pending_jobs'].append(pending_copy)

    return make_response(jsonify(j), 200)

@sparrow_api.route("/log", methods=["GET", "DELETE"])
def loglist():
    if request.method == "GET":
        j = {"count":int(), "logs":[]}
        log_list = os.listdir(LOG_DIR)

        for l in log_list:
            ogg = os.path.join(MUSIC_DIR, l.replace(".log", ".ogg"))
            track_exists = os.path.isfile(ogg)
            log = {
                    "file":l,
                    "track":track_exists,
                    }
            j['logs'].append(log)

        j['count'] = len(log_list)

        return make_response(jsonify(j), 200)

    if request.method == "DELETE":
        files_to_remove = glob.glob(os.path.join(LOG_DIR, "*"))
        j = {"removed":files_to_remove}

        for f in files_to_remove:
            os.remove(f)

        return make_response(jsonify(j), 200)


@sparrow_api.route("/track", methods=["GET", "DELETE"])
def tracklist():
    if request.method == "GET":
        j = {"count":int(),"tracks":[]}
        file_list = os.listdir(MUSIC_DIR)

        non_ogg = []

        for i in range(len(file_list)):
            if not file_list[i].endswith(".ogg"):
                non_ogg.append(i)

        for non in non_ogg:
            del file_list[non]

        j['count'] = len(file_list)

        for f in file_list:
            abs_path = os.path.join(MUSIC_DIR, f)
            tags = OggVorbis(abs_path)
            track = {
                    "file":f,
                    "size_mb":round_up(os.path.getsize(abs_path)/(1024*1024), 1),
                    "artist":tags["artist"][0],
                    "album":tags["album"][0],
                    "title":tags["title"][0],
                    "track_id":"spotify:track:{}".format(f.split(".")[0]),
                    }
            j['tracks'].append(track)

        return make_response(jsonify(j), 200)
    
    if request.method == "DELETE":
        files_to_remove = glob.glob(os.path.join(MUSIC_DIR, "*"))
        j = {"removed":files_to_remove}

        for f in files_to_remove:
            os.remove(f)

        return make_response(jsonify(j), 200)

@sparrow_api.route("/spotify/<string:action>", methods=["POST"])
def s(action):
    if action == "start":
        if not is_spotify_running():
            q.enqueue_call(func='sparrow.spotify_start', timeout=5)
            msg = "OK"
        else:
            msg = "RUNNING"
    elif action == "stop":
        if is_spotify_running():
            q.enqueue_call(func='sparrow.spotify_stop', timeout=5)
            msg = "OK"
        else:
            msg = "STOPPED"
    else:
        j = jsonify({"msg":"No such action!"})
        return make_response(j, 404)
    j = jsonify({"msg":msg})
    return make_response(j, 200)
    
@sparrow_api.route("/log/<string:logname>", methods=["GET", "DELETE"])
def log(logname):
    if request.method == "GET":
        return send_from_directory(LOG_DIR, logname, as_attachment=True)
    if request.method == "DELETE":
        p = os.path.join(LOG_DIR, logname)
        if os.path.isfile(p):
            os.remove(p)
            j = {"msg":"REMOVED"}
        else:
            j = {"msg":"NO SUCH FILE"}
        return make_response(jsonify(j), 200)

@sparrow_api.route("/track/<string:track_id>", methods=["POST", "DELETE"])
def track(track_id):
    if request.method == "POST":
        if not is_spotify_running():
            error_json = {"msg":"Spotify is not running!"}
            return make_response(jsonify(error_json), 400)

        if track_id == "test":
            job = q.enqueue_call(func='sparrow.record_test', args=(True,), timeout=T)
            test_json = {"msg":"Testing!", "job":job.id}
            return make_response(jsonify(test_json), 200)

        if not is_track_uri(track_id):
            error_json = {"msg":"{} is not a valid track_id!".format(track_id)}
            return make_response(jsonify(error_json), 400)

        job = q.enqueue_call(func='sparrow.record_track', args=(track_id, True,), timeout=T)
        test_json = {"msg":track_id, "job":job.id}
        return make_response(jsonify(test_json), 200)

    if request.method == "DELETE":
        if not is_track_uri(track_id):
            error_json = {"msg":"{} is not a valid track_id!".format(track_id)}
            return make_response(jsonify(error_json), 400)

        music_file = "{}.ogg".format(sapi.strip_tid(track_id))
        p = os.path.join(MUSIC_DIR, music_file)
        if os.path.isfile(p):
            os.remove(p)
            j = {"msg":"REMOVED: {}".format(p)}
        else:
            j = {"msg":"NO SUCH FILE: {}".format(p)}
        return make_response(jsonify(j), 200)

@sparrow_api.route("/export/<string:track_id>", methods=["POST"])
def export(track_id):
    if request.method == "POST":
        if not is_track_uri(track_id):
            j = {"msg":"{} is not a valid track_id!".format(track_id),
                    "oldpath":"","newpath":"","uid":""}
            return make_response(jsonify(j), 404)

        old_music_file = "{}.ogg".format(sapi.strip_tid(track_id))
        oldpath = os.path.join(MUSIC_DIR, old_music_file)
        
        if not os.path.isfile(oldpath):
            j = {"msg":"No such file!","oldpath":"","newpath":"","uid":""}
            return make_response(jsonify(j), 404)

        tags = OggVorbis(oldpath)
        new_music_file = "{} - {}.ogg".format(tags['artist'][0], tags['title'][0])
        newpath = os.path.join(EXPORT_DIR, new_music_file)

        shutil.move(oldpath, newpath)
        new_uid = int(os.environ['LIBRARY_UID'])
        os.chown(newpath, new_uid, new_uid)

        j = {"msg":"OK", "oldpath":oldpath, "newpath":newpath, "uid":new_uid}
        return make_response(jsonify(j), 200)

@sparrow_api.route("/export", methods=["POST"])
def export_all():
    if request.method == "POST":
        music_files = glob.glob(os.path.join(MUSIC_DIR, "*.ogg"))
        new_uid = int(os.environ['LIBRARY_UID'])

        j = {"uid":new_uid, "moved":[]}
        
        for f in music_files:
            tags = OggVorbis(f)
            new_music_file = "{} - {}.ogg".format(tags['artist'][0], tags['title'][0])
            newpath = os.path.join(EXPORT_DIR, new_music_file)

            shutil.move(f, newpath)
            os.chown(newpath, new_uid, new_uid)

            file_dict = {"oldpath":f, "newpath":newpath}
            j['moved'].append(file_dict)

        return make_response(jsonify(j), 200)


def main():
    sparrow_api.run(host='0.0.0.0', debug=False, port=9000)

if __name__ == '__main__':
    main()

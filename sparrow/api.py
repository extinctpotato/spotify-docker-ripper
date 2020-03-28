import os
from math import ceil
from mutagen.oggvorbis import OggVorbis
from flask import request, Response, Flask, jsonify, make_response
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

@sparrow_api.route("/list/tracks")
def tracklist():
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
    

@sparrow_api.route("/track/<string:track_id>", methods=["POST"])
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

def main():
    sparrow_api.run(host='0.0.0.0', debug=False, port=9000)

if __name__ == '__main__':
    main()

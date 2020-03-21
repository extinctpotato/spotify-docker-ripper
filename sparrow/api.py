from flask import request, Response, Flask, jsonify, make_response
from redis import Redis
import pickle
pickle.HIGHEST_PROTOCOL = 4
from threading import Lock
from rq import Queue
from rq.job import Job
from sparrow import is_track_uri, spotify_start, spotify_stop, dbus_env, is_spotify_running
from sparrow import SpotifyInterface

sparrow_api = Flask(__name__)
redis_con = Redis()
q = Queue(connection=redis_con)
lock = Lock()

T = 9600

@sparrow_api.route("/")
def index():
    return make_response("Argh!", 200)

@sparrow_api.route("/status", methods=["GET"])
def test_route():
    dbus_env()
    s = SpotifyInterface()
    j = {}
    j.update(s.get_meta())
    j['playback_status'] = s.get_property('PlaybackStatus')
    j['pending_jobs'] = len(q.jobs)
    j['spotify_running'] = is_spotify_running()
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

        if track_id == "test":
            job = q.enqueue_call(func='sparrow.record_test', args=(True,), timeout=T)
            test_json = {"msg":"Testing!", "job":job.id}
            return make_response(jsonify(test_json), 200)

        if not is_track_uri(track_id):
            error_json = {"error":"{} is not a valid track_id!".format(track_id)}
            return make_response(jsonify(error_json), 400)

        job = q.enqueue_call(func='sparrow.record_track', args=(track_id, True,), timeout=T)
        test_json = {"msg":track_id, "job":job.id}
        return make_response(jsonify(test_json), 200)

def main():
    sparrow_api.run(host='0.0.0.0', debug=False, port=9000)

if __name__ == '__main__':
    main()

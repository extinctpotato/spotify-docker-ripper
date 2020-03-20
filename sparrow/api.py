from flask import request, Response, Flask, jsonify, make_response
from redis import Redis
import pickle
pickle.HIGHEST_PROTOCOL = 4
from rq import Queue
from rq.job import Job
from sparrow import is_track_uri, spotify_start, spotify_stop

sparrow_api = Flask(__name__)
redis_con = Redis()
q = Queue(connection=redis_con)

@sparrow_api.route("/")
def index():
    return make_response("Argh!", 200)

@sparrow_api.route("/track/<string:track_id>", methods=["POST"])
def track(track_id):
    if request.method == "POST":
        if not is_track_uri(track_id):
            error_json = {"error":"{} is not a valid track_id!".format(track_id)}
            return make_response(jsonify(error_json), 400)

def main():
    sparrow_api.run(host='0.0.0.0', debug=False, port=9000)

if __name__ == '__main__':
    main()

import requests, os
from base64 import b64encode

CID = os.environ['SPOTIFY_API_CLIENT_ID']
CS = os.environ['SPOTIFY_API_CLIENT_SECRET']

def get_token():
    url = "https://accounts.spotify.com/api/token"
    params = {"grant_type":"client_credentials"}
    auth_string = "{}:{}".format(CID, CS)
    auth_string_b64 = b64encode(auth_string.encode()).decode()
    auth_header = {"Authorization":"Basic {}".format(auth_string_b64)}
    r = requests.post(url, data=params, headers=auth_header)
    return r.json()['access_token']

def strip_tid(track_id):
    return track_id.split(":")[2]

class Track:
    def __init__(self, track_id):
        self.tid = strip_tid(track_id)
        self.token = get_token()
        self.headers = {"Authorization":"Bearer {}".format(self.token)}
        self.metadata = self.__get_meta()
        self.cover_url = self.__get_cover()

    def __get_meta(self):
        url = "https://api.spotify.com/v1/tracks/{}".format(self.tid)
        r = requests.get(url, headers=self.headers)
        j = r.json()
        del j['available_markets']
        del j['album']['available_markets']
        return j

    def __get_cover(self):
        for cover in self.metadata['album']['images']:
            if cover['height'] > 600 and cover['width'] > 600:
                return cover['url']

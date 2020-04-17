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

def search(query, content_type="track"):
    url = "https://api.spotify.com/v1/search"
    params = {"q":query, "type":content_type}
    headers = {"Authorization":"Bearer {}".format(get_token())}
    r = requests.get(url, params=params, headers=headers)
    search_result = r.json()

    for index in range(len(search_result['tracks']['items'])):
        del search_result['tracks']['items'][index]['available_markets']
        del search_result['tracks']['items'][index]['album']['available_markets']

    return search_result

class Track:
    def __init__(self, track_id="spotify:track:5treNJZ0gCdEO3EcWp9aDu"):
        self.tid = strip_tid(track_id)
        self.token = get_token()
        self.headers = {"Authorization":"Bearer {}".format(self.token)}
        self.metadata = self.__get_meta()
        self.cover_url = self.__get_cover()[0]
        self.cover_bytes = None 
        self.cover_dimensions = self.__get_cover()[1:]

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
                return cover['url'], cover['height'], cover['width']

    def download_cover(self):
        r = requests.get(self.cover_url)
        self.cover_bytes = r.content

class Episode:
    def __init__(self, eid="spotify:episode:5lUORBC9mw9vroABUJj5A9", market="US"):
        self.eid = strip_tid(eid)
        self.market = market
        self.token = get_token()
        self.headers = {"Authorization":"Bearer {}".format(self.token)}
        self.metadata = self.__get_meta()
        self.cover_url = self.__get_cover()[0]
        self.cover_bytes = None 
        self.cover_dimensions = self.__get_cover()[1:]

    def __get_meta(self):
        url = "https://api.spotify.com/v1/episodes/{}".format(self.eid)
        r = requests.get(url, headers=self.headers, params={'market':self.market})
        j = r.json()
        del j['show']['available_markets']
        return j

    def __get_cover(self):
        for cover in self.metadata['images']:
            if cover['height'] > 600 and cover['width'] > 600:
                return cover['url'], cover['height'], cover['width']

    def download_cover(self):
        r = requests.get(self.cover_url)
        self.cover_bytes = r.content

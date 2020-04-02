# spotify-docker-ripper

This repository contains the code of my duct tape application for ripping which, as the name suggests, records tracks from Spotify and encodes them as ogg files.

__DISCLAIMER: This software is for educational/testing purposes only. If you're using it, you're probably in the violation of Spotify's ToS. The author is not responsible for its use.__

Having said that, it's practically impossible to detect.
While running, it's nearly indistinguishable from a normal, minding-its-own-business Linux machine running the official client.

Hey ho, let's go setup this thingy.

## Prerequisites

Like I mentioned before, this is a duct tape application so it made sense to pack it all in a Docker image.
It also helps to isolate Spotify.

* `Docker`
* `docker-compose`
* Spotify Premium Account (unless you want to record songs with baked-in ads)

## Setup

Everything is configured by means of a `docker-compose.override.yml`.
You can find the template in `docker-compose.override.yml.example`.
Simply copy it and change the values to your liking.

Especially important are the environment variables.
They are used to log in to Spotify and to fetch the data using the Spotify API.

To obtain the API key, please go to the [Spotify for Developers](https://developer.spotify.com/dashboard/applications) website and create a new client ID.
Then, copy it to the override file and you're good to go.

The REST API server allowing you to control this recording tandem is running on the port 9000, so feel free to remap it to whatever port you want.

After performing the configuration process, start the tandem by running `docker-compose up -d`.

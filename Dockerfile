FROM debian:buster

ENV DEBIAN_FRONTEND noninteractive
RUN apt update

# Set up tzdata
RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
RUN apt-get install -qqy --no-install-recommends tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata

# Install X window system and supervisor
RUN apt -y upgrade
RUN apt -qqy --no-install-recommends install \
	xvfb x11vnc curl gnupg vorbis-tools \
	ca-certificates pulseaudio sox supervisor \
	htop python3-dbus dbus-x11 psmisc xdg-user-dirs \
	redis python3-redis python3-click python3-setuptools \
	python3-flask python3-psutil python3-requests python3-mutagen \
	uwsgi uwsgi-plugin-python3 nginx
RUN apt -y autoremove

RUN curl http://ftp.ca.debian.org/debian/pool/main/p/python-rq/python3-rq_1.2.2-1_all.deb -o /tmp/rq.deb && \
	dpkg -i /tmp/rq.deb && rm -rf /tmp/rq.deb

RUN curl -sS https://download.spotify.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb http://repository.spotify.com stable non-free" | tee /etc/apt/sources.list.d/spotify.list

RUN apt update && apt -qqy --no-install-recommends install spotify-client

ENV HOME /root/
RUN xdg-user-dirs-update

ENV DISPLAY :1

COPY supervisord.conf /etc/supervisord.conf
COPY sparrow.ini /etc/sparrow.ini
COPY nginx.conf /etc/nginx.conf

RUN ln -s /code/sparrow /usr/lib/python3/dist-packages/sparrow

ENTRYPOINT ["supervisord"]

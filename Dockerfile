FROM debian:buster

ENV DEBIAN_FRONTEND noninteractive
RUN apt update

# Set up tzdata
RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata

# Install X window system and supervisor
RUN apt -y upgrade
RUN apt -qqy install \
	xvfb xfce4-terminal xfce4-panel \
	xfdesktop4 xfwm4 xfce4-settings \
	xfce4-session x11vnc curl gnupg \
	pavucontrol pulseaudio sox supervisor \
	htop
RUN apt -y remove xscreensaver
RUN apt -y autoremove

RUN curl -sS https://download.spotify.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb http://repository.spotify.com stable non-free" | tee /etc/apt/sources.list.d/spotify.list

RUN apt update && apt -qqy install spotify-client

RUN apt -qqy remove tumbler && apt -qqy autoremove
RUN rm -rf \
	/etc/xdg/autostart/at-spi-dbus-bus.desktop \
	/etc/xdg/autostart/light-locker.desktop \
	/etc/xdg/autostart/xscreensaver.desktop \
	/etc/xdg/autostart/xdg-user-dirs.desktop

ENV HOME /root/
RUN xdg-user-dirs-update

ENV DISPLAY :1

COPY supervisord.conf /etc/supervisord.conf

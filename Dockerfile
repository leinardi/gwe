# TODO does not work yet
FROM x11docker/kde-plasma

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y\
  && apt-get install -y \
    gedit pkg-config python3-dev libgirepository1.0-dev meson ninja-build appstream-util \
    python3 python3-pip libgirepository1.0-dev gir1.2-ayatanaappindicator3-0.1 \
    gnome-shell-extension-appindicator libdazzle-1.0-dev git libxml2-utils \
    desktop-file-utils python3-rx python3-gi-cairo
#ubuntu: gir1.2-appindicator3-0.1 \
WORKDIR /app

# in order to use this Dockerfile to build and run gwe do the following commands:
# docker build . -t gwe
# install x11 docker: https://github.com/mviereck/x11docker
# x11docker -it --share "$(pwd)" --gpu gwe
# now in the docker shell:
# remove the fixed version for PyGObject in requirements.txt then:
# pip install -r requirements.txt --break-system-packages
# ./run.sh

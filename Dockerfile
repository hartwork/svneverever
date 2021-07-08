FROM debian:9

RUN apt update && apt install -y \
    git subversion \
    python3 python3-svn python3-pip

RUN pip3 install --user svneverever

WORKDIR /workdir

ENV PATH="/root/.local/bin:${PATH}"

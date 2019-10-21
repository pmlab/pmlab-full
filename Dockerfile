FROM ubuntu:xenial
LABEL maintainer "DataMade <info@datamade.us>"

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get -y install curl \
    && echo "deb http://downloads.skewed.de/apt/xenial xenial universe" >> /etc/apt/sources.list \
    && echo "deb-src http://downloads.skewed.de/apt/xenial xenial universe" >> /etc/apt/sources.list \
    && curl https://keys.openpgp.org/vks/v1/by-fingerprint/793CEFE14DBC851A2BFB1222612DEFB798507F25 -L --output graph-tool.key \
    && apt-key add graph-tool.key \
    && apt-get update
RUN apt-get -y install equivs \
    && equivs-control python-scipy.control \
    && sed -i 's/<package name; defaults to equivs-dummy>/python-scipy/g' python-scipy.control \
    && equivs-build --arch=i386 python-scipy.control \
    && dpkg -i python-scipy_1.0_i386.deb \
    && equivs-control python-matplotlib.control \
    && sed -i 's/<package name; defaults to equivs-dummy>/python-matplotlib/g' python-matplotlib.control \
    && equivs-build --arch=i386 python-matplotlib.control \
    && dpkg -i python-matplotlib_1.0_i386.deb \
    && apt-get purge -y equivs \
    && apt-get autoremove -y \
    && apt-get -y install python-graph-tool:i386
    
COPY . /app
WORKDIR /app

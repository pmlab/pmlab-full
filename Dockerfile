FROM ubuntu:trusty

LABEL maintainer "DataMade <info@datamade.us>"

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get -y install curl software-properties-common \
    && add-apt-repository ppa:ubuntu-toolchain-r/test -y \
    && echo "deb http://downloads.skewed.de/apt/trusty trusty universe" >> /etc/apt/sources.list \
    && echo "deb-src http://downloads.skewed.de/apt/trusty trusty universe" >> /etc/apt/sources.list \
    && curl https://keys.openpgp.org/vks/v1/by-fingerprint/793CEFE14DBC851A2BFB1222612DEFB798507F25 -L --output graph-tool.key \
    && apt-key add graph-tool.key \
    && rm graph-tool.key \
    && apt-get update \
    && apt-get -y install libc6:i386 lp-solve:i386 gcc:i386 g++:i386  \
    && curl "http://downloads.sourceforge.net/project/boost/boost/1.40.0/boost_1_40_0.tar.gz" -L --output boost.tar.gz \
    && tar xzf boost.tar.gz \
    && cd boost_1_40_0 \
    && ./bootstrap.sh \
    && ./bjam address-model=32 --with-program_options \
    && mv stage/lib/libboost_program_options.* /usr/lib/i386-linux-gnu/ \
    && cd .. \
    && rm -rf boost.tar.gz boost_1_40_0 \
    && ln -s /usr/lib/i386-linux-gnu/libboost_program_options.so.1.40.0 /usr/lib/i386-linux-gnu/libboost_program_options-mt.so.1.38.0 \
    && ln -s /usr/lib/lp_solve/liblpsolve55.so /usr/lib/i386-linux-gnu \
    && ln -s /usr/lib/i386-linux-gnu/libcolamd.so.2.8.0 /usr/lib/i386-linux-gnu/libcolamd.so.2.7.1 \
    && curl "http://personals.ac.upc.edu/msole/homepage/rbminer/rbminer.tar.gz" -L --output rbminer.tar.gz \
    && tar xvf rbminer.tar.gz \
    && mv Release/bin/rbminer /usr/local/bin \
    && mv Release/bin/log2ts /usr/local/bin \
    && rm rbminer.tar.gz \
    && rm -rf Release \
    && apt-get -y install cmake3 bison flex libboost-program-options-dev libboost-dev python perl minisat zlib1g-dev build-essential \
    && curl "https://github.com/stp/stp/archive/master.tar.gz" -L --output stp.tar.gz \
    && tar xvf stp.tar.gz \
    && cd stp-master \
    && mkdir build \
    && cd build \
    && cmake .. -DCMAKE_INSTALL_PREFIX=/usr \
    && make \
    && make install \
    && cd ../.. \
    && rm -rf stp* \
    && apt-get -y install python-graph-tool \
    && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py \
    && rm get-pip.py \
    && apt-get remove -y cmake3 bison flex build-essential \
    && apt-get autoremove -y \
    && apt-get -y install libstdc++6:i386

    
COPY . /app
WORKDIR /app
RUN pip install .
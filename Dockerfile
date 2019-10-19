FROM centos:6
LABEL maintainer "DataMade <info@datamade.us>"

RUN yum install -y libglibc.i686 glibc-devel.i686 libstdc++-devel.i686 libstdc++-devel.x86_64 glibc-devel.x86_64 gcc gcc-c++ suitesparse.i686 scl-utils centos-release-scl-rh && yum install -y python27 python-setuptools
RUN curl "http://downloads.sourceforge.net/project/boost/boost/1.40.0/boost_1_40_0.tar.gz" -L --output boost.tar.gz \
	&& tar xzf boost.tar.gz \
        && cd boost_1_40_0 \
	&& ./bootstrap.sh --prefix=/usr \
	&& ./bjam address-model=32 --with-program_options install \
	&& cd .. \
	&& rm -rf boost.tar.gz boost_1_40_0 \
	&& ln /usr/lib/libboost_program_options.so.1.40.0 /usr/lib/libboost_program_options-mt.so.1.38.0 \
	&& mkdir lp_solve \
	&& cd lp_solve \
	&& curl "http://downloads.sourceforge.net/project/lpsolve/lpsolve/5.5.2.5/lp_solve_5.5.2.5_dev_ux32.tar.gz" -L --output lp_solve.tar.gz \
	&& tar xvf lp_solve.tar.gz \
	&& mv liblpsolve55.* /usr/lib \
	&& cd .. \
	&& rm -rf lp_solve

COPY . /app
WORKDIR /app
RUN scl enable python27 "python setup.py install"

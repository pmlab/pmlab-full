FROM centos:6
LABEL maintainer "DataMade <info@datamade.us>"

RUN yum install -y libglibc.i686 suitesparse.i686 boost-program-options.i686 scl-utils centos-release-scl-rh && yum install -y python27-python python27-python-setuptools
RUN ln -s /usr/lib/libboost_program_options.so.5 /usr/lib/libboost_program_options.so.1.40.0 \
        && ln -s /usr/lib/libboost_program_options-mt.so.5 /usr/lib/libboost_program_options-mt.so.1.38.0 \
	&& mkdir lp_solve \
	&& cd lp_solve \
	&& curl "http://downloads.sourceforge.net/project/lpsolve/lpsolve/5.5.2.5/lp_solve_5.5.2.5_dev_ux32.tar.gz" -L --output lp_solve.tar.gz \
	&& tar xvf lp_solve.tar.gz \
	&& mv liblpsolve55.* /usr/lib \
	&& cd .. \
	&& rm -rf lp_solve \
	&& curl "http://personals.ac.upc.edu/msole/homepage/rbminer/rbminer.tar.gz" -L --output rbminer.tar.gz \
	&& tar xvf rbminer.tar.gz \
	&& mv Release/bin/rbminer /usr/local/bin \
	&& mv Release/bin/log2ts /usr/local/bin \
	&& rm rbminer.tar.gz \
	&& rm -rf Release


COPY . /app
WORKDIR /app
RUN scl enable python27 "python setup.py install"

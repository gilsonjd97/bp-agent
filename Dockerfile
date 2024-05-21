# Use an official base image, e.g., Ubuntu

FROM i386/ubuntu:14.04

RUN apt-get update  && apt-get install -y \
	software-properties-common

RUN add-apt-repository ppa:openjdk-r/ppa && \
	apt-get update && \
	apt-get install -y openjdk-8-jdk

# Set JAVA_HOME environment variable

ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-i386

# Set environment variables to avoid any interactive dialogue from the OS

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies (if any) and tools necessary for your installation

RUN apt-get update && apt-get install -y \
	build-essential \
	make \
	gcc \
	autoconf \
	libtool \
	libc6-dev \
	libssl-dev \
	libxml2-dev \
	clang \
	libcunit1 \
	libcunit1-dev \
	ant \
	openssl \
	x11-apps \
	libx11-dev \
	xauth \
	wget \
	unzip \
	python \
	python-pip \
	python-dev \
	gcc-msp430 \
	msp430-libc \
	mspdebug \
	&& rm -rf /var/lib/apt/lists/*

# Set the DISPLAY environment variable

#ENV DISPLAY host.docker.internal:0

# Copy the coap-controller directory from your host to the Docker image

COPY coap-eap-controller /home/contiki/coap-eap-controller

# Copy the Contiki directory from your host to the Docker image

COPY contiki-2.7 /home/contiki/contiki-2.7

# Copy the observer and scripts

COPY observer /home/contiki/observer
COPY scripts /home/contiki/scripts

# Set the working directory to where your Cooja simulation is

WORKDIR /home/contiki/contiki-2.7/tools/cooja

# Build Cooja

RUN ant jar

#### CoAP controller ###
# Create the required directory structure

RUN mkdir -p /home/contiki/coap-eap-tfg

# Copy the freeradius-2.0.2-psk directory into the correct place in the Docker image

COPY freeradius-2.0.2-psk /home/contiki/coap-eap-tfg/freeradius-2.0.2-psk/

# Change WORKDIR to the eap_example directory

WORKDIR /home/contiki/coap-eap-tfg/freeradius-2.0.2-psk/hostapd/eap_example

RUN make CONFIG_SOLIB=yes

# Change WORKDIR to freeradius-2.0.2-psk

WORKDIR /home/contiki/coap-eap-tfg/freeradius-2.0.2-psk

RUN cp ./freeradius_mod_files/modules.c ./freeradius-server-2.0.2/src/main/ && \
	cp ./freeradius_mod_files/Makefile ./freeradius-server-2.0.2/src/modules/rlm_eap2/

# Change WORKDIR to the freeradius-server-2.0.2 directory

WORKDIR /home/contiki/coap-eap-tfg/freeradius-2.0.2-psk/freeradius-server-2.0.2

# Add this step to give execute permissions to the configure script
RUN chmod +x ./configure ./install-sh

# Run the configure script
RUN ./configure --prefix=/home/contiki/freeradius-psk --with-modules=rlm_eap2 && \
	make && \
	make install

# Change WORKDIR back to freeradius-2.0.2-psk

WORKDIR /home/contiki/coap-eap-tfg/freeradius-2.0.2-psk

RUN cp ./freeradius_mod_files/eap.conf /home/contiki/freeradius-psk/etc/raddb && \
	cp ./freeradius_mod_files/users /home/contiki/freeradius-psk/etc/raddb && \
	cp ./freeradius_mod_files/default /home/contiki/freeradius-psk/etc/raddb/sites-enabled/

# Set environment variables for FreeRADIUS

ENV LD_PRELOAD=/home/contiki/coap-eap-tfg/freeradius-2.0.2-psk/hostapd/eap_example/libeap.so

# Expose port

EXPOSE 5000

# Set the working directory in the container

WORKDIR /home/contiki/scripts

CMD ["bash"]


#!/bin/bash

#
# Predepend : python2.7
#

NAME=pylib
TOPDIR=$(pwd)/$(dirname $0)/
INSTDIR=$TOPDIR/inst
MISCDIR=$TOPDIR/misc
cd $TOPDIR

PACKAGES=(psycopg2 uwsgi pymediainfo pybonjour)

# STEP 0: prepare
rm -rf $INSTDIR
mkdir -p $INSTDIR

ARCH=$(dpkg --print-architecture)
if [ ! -d /usr/include/python2.7 ]; then
  dpkg -x $TOPDIR/debian/python2.7-dev_2.7.1-6_$ARCH.deb /
fi

# package for pybonjour
dpkg -i $TOPDIR/debian/avahi-daemon_0.6.27-2+squeeze1_$ARCH.deb
dpkg -i $TOPDIR/debian/libavahi-compat-libdnssd1_0.6.27-2+squeeze1_$ARCH.deb
dpkg -i $TOPDIR/debian/libavahi-core7_0.6.27-2+squeeze1_$ARCH.deb
dpkg -i $TOPDIR/debian/libnss-mdns_0.10-3.1_$ARCH.deb

for PKG in ${PACKAGES[@]}; do
  SRC=$(echo ${TOPDIR}/${PKG}-*.tar.gz)
  SRC_DIR=$(basename $SRC | sed "s/.tar.gz$//")

  # STEP 1: unpack
  tar xf $SRC -C $TOPDIR 

  # STEP 2: make binary dist
  cd $TOPDIR/$SRC_DIR
  rm -rf ./dist >/dev/null 2>&1
  python ./setup.py bdist
  wait $!

  # STEP 3: untar dist file 
  tar xf ./dist/* -C $INSTDIR
done

# STEP 4 : Finalize
cd $INSTDIR
mv ./usr/local/* ./usr/
rm -rf ./usr/local
cp -rfp $MISCDIR/* $INSTDIR/

find ./usr/bin -exec strip {} \;

[ $? != 0 ] && ARCH=unknown
tar jcvf $TOPDIR/${NAME}_${ARCH}.tar.bz2 .

[ $? = "0" ] || exit 1 

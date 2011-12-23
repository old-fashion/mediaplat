#!/bin/sh

#
# Predepend : libexpat1-dev libxml2-dev libpcre3-dev
#

NAME=nginx
TOPDIR=$(pwd)/$(dirname $0)/
SOURCEFILE=$TOPDIR/nginx-1.0.9.tar.gz
SOURCEDIR=$TOPDIR/nginx-1.0.9
PKGDIR=$TOPDIR/pkg
INSTDIR=$TOPDIR/inst
MISCDIR=$TOPDIR/misc
ARCH=$(dpkg --print-architecture)
[ $? != 0 ] && ARCH=unknown

cd $TOPDIR

# STEP 0 : install pre-required packages
dpkg -i $PKGDIR/python2.7-dev_2.7.1-6_$ARCH.deb
#sh $PKGDIR/setuptools-0.6c11-py2.7.egg

easy_install uwsgi 
mkdir -p $INSTDIR/usr/bin
mv /usr/bin/uwsgi $INSTDIR/usr/bin


# STEP 1 : unpack
if [ ! -e "$SOURCEDIR" ] || [ "$1" = "init" ]; then
  rm -rf $SOURCEDIR
  tar xvf $SOURCEFILE
fi

# STEP 2 : configure
cd $SOURCEDIR
if [ "$1" != "passconf" ]; then
  ./configure \
    --sbin-path=/usr/sbin/nginx \
    --conf-path=/etc/nginx/nginx.conf \
    --error-log-path=/var/log/nginx/error.log \
    --pid-path=/var/run/nginx.pid \
    --lock-path=/var/lock/nginx.lock \
    --http-log-path=/var/log/nginx/access.log \
    --with-http_dav_module \
    --http-client-body-temp-path=/var/lib/nginx/body \
    --with-http_ssl_module \
    --http-proxy-temp-path=/var/lib/nginx/proxy \
    --with-http_stub_status_module \
    --http-fastcgi-temp-path=/var/lib/nginx/fastcgi \
    --with-debug \
    --with-http_flv_module 

  [ $? = "0" ] || exit 1 
fi

# STEP 3 : make
make
[ $? = "0" ] || exit 1 

# STEP 4 : make install
rm -rf $INSTDIR
mkdir -p $INSTDIR
mkdir -p $INSTDIR/etc

make DESTDIR=$TOPDIR/inst install

# STEP 5 : Finalize
cp -rfp $MISCDIR/* $INSTDIR/
cd $INSTDIR

rm -rf `find . -name .git`
mkdir -p ./var/lib/nginx

# strip
strip ./usr/bin/*
strip ./usr/lib/*
strip ./usr/sbin/*

tar jcvf $TOPDIR/${NAME}_${ARCH}.tar.bz2 .

[ $? = "0" ] || exit 1 

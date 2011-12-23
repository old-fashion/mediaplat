#!/bin/sh

#
# Predepend : libreadline-dev libpam0g-dev libxslt1-dev libossp-uuid-dev
#

NAME=postgresql
TOPDIR=$(pwd)/$(dirname $0)/
SOURCEFILE=$TOPDIR/postgresql-9.1.1.tar.bz2
SOURCEDIR=$TOPDIR/postgresql-9.1.1
INSTDIR=$TOPDIR/inst
MISCDIR=$TOPDIR/misc
VERSION=9.1

cd $TOPDIR

# STEP 1 : unpack
if [ ! -e "$SOURCEDIR" ] || [ "$1" = "init" ]; then
  rm -rf $SOURCEDIR
  tar xvf $SOURCEFILE
fi

# STEP 2 : configure
cd $SOURCEDIR
if [ "$1" != "passconf" ]; then
  ./configure \
  	--prefix=/usr \
	--sysconfdir=/etc/postgresql-common \
	--datadir=/usr/share/postgresql/$VERSION \
	--bindir=/usr/lib/postgresql/$VERSION/bin \
	--includedir=/usr/include/postgresql/ \
	--enable-integer-datetimes \
	--enable-thread-safety \
	--enable-debug \
	--disable-rpath \
	--with-python \
	--with-pam \
	--with-libxml \
	--with-libxslt \
	--with-ossp-uuid \
	--with-gnu-ld \
	--with-system-tzdata=/usr/share/zoneinfo \
	--with-pgport=5432 

  [ $? = "0" ] || exit 1 
fi

# STEP 3 : make
make
[ $? = "0" ] || exit 1 

# STEP 4 : make install
rm -rf $INSTDIR
mkdir -p $INSTDIR
make DESTDIR=$TOPDIR/inst install

# STEP 4.1: install addtional package
dpkg -x $TOPDIR/pkg/postgresql-common_125_all.deb $INSTDIR
dpkg -x $TOPDIR/pkg/postgresql-client-common_125_all.deb $INSTDIR

# STEP 5 : Finalize
cp -rfp $MISCDIR/* $INSTDIR/
cd $INSTDIR

rm -rf `find . -name .svn`
rm -f ./usr/lib/*.la

find ./usr/lib -exec strip {} \;
mkdir -p ./var/run/postgresql

ARCH=$(dpkg --print-architecture)
[ $? != 0 ] && ARCH=unknown
tar jcvf $TOPDIR/${NAME}_${ARCH}.tar.bz2 .

[ $? = "0" ] || exit 1 

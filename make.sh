#!/bin/bash


PROJECT=mediaplat
DEPEND=(libncurses5-dev libssl-dev libreadline-dev libpam0g-dev libxslt1-dev libossp-uuid-dev libpcre3-dev)

USE_PASSCONF=off

HOME_DIR=$(pwd)/$(dirname $0)
INST_DIR=${HOME_DIR}/inst

get_tempfile() {
  TEMP=$(mktemp)
  TEMPFILES=("${TEMPFILES[@]}" "$TEMP")
  echo $TEMP
}

cleanup() {
  rm -f "${TEMPFILES[@]}" >/dev/null
  exit
}

init() {
  # check arch
  ARCH=$(dpkg --print-architecture)

  # check dialog
  DIALOG=$(which dialog)
  [ -z "$DIALOG" ] && USE_DIALOG=no || USE_DIALOG=yes

  # check dependency
  for PKG in ${DEPEND[@]}; do
    dpkg -s $PKG >/dev/null 2>&1
	if [ "$?" != "0" ]; then
	  echo "[ERROR] Package $PKG is not installed"
	fi
  done

  # check python version
  if [ ! -e /usr/include/python2.7/Python.h ]; then
    dpkg -x $TOPDIR/pylib/debian/python2.7-dev_2.7.1-6_$ARCH.deb /
    echo "[ERROR] Python 2.7 is required"
  fi

  # check package version
  POSTGRESQL_SRC=$(basename $(grep "^SOURCEFILE" $HOME_DIR/postgresql/make.sh))
  NGINX_SRC=$(basename $(grep "^SOURCEFILE" $HOME_DIR/nginx/make.sh))
  echo $ERLANG_VERSION $COUCHDB_VERSION

  # make initial dir
  rm -rf $HOME_DIR/inst >/dev/null 2>&1
  mkdir $HOME_DIR/inst
}

# $1: module name
build_package() {
  [ -z "$1" ] && return 1
  [ "$WITH_PASSCONF" = "yes" ] && PASSCONF=passconf

  PACKAGE_HOME=$HOME_DIR/$1
  cd $PACKAGE_HOME
  ./make.sh $PASSCONF
  if [ "$?" != 0 ]; then
    echo "[ERROR] $1 package build fail"
	exit 1
  fi
}

build() {
  [ "$WITH_POSTGRESQL" = "yes" ] && build_package postgresql
  [ "$WITH_NGINX" = "yes" ] && build_package nginx
  [ "$WITH_PYLIB" = "yes" ] && build_package pylib
}

dist() {
  # extract packages
  for PKG in postgresql nginx pylib; do
    PACKAGE_HOME="$HOME_DIR/$PKG"
    PACKAGE="$PACKAGE_HOME/${PKG}_$ARCH.tar.bz2"
    if [ -e "$PACKAGE" ]; then
      tar xvf $PACKAGE -C $HOME_DIR/inst
    else
      echo "[ERROR] Package $PKG does not exist"
	  exit 1
    fi
  done

  # copy source
  mkdir -p $INST_DIR/usr/lib/mediaplat
  mkdir -p $INST_DIR/var/lib/mediaplat
  cp -a $HOME_DIR/src/* $HOME_DIR/inst/usr/lib/mediaplat/
  cp -a $HOME_DIR/src/plugins $HOME_DIR/inst/var/lib/mediaplat/

  # copy misc
  cp -a $HOME_DIR/rootfs/* $INST_DIR

  # make version

  # make directories
  mkdir -p $INST_DIR/usr/bin >/dev/null 2>&1
  mkdir -p $INST_DIR/var/lib/mediaplat >/dev/null 2>&1
  mkdir -p $INST_DIR/var/run/mediaplat >/dev/null 2>&1
  mkdir -p $INST_DIR/var/log/mediaplat >/dev/null 2>&1
  mkdir -m 777 -p $INST_DIR/var/lib/mediaplat/www/conf >/dev/null 2>&1

  ln -s /usr/lib/mediaplat/mediaplat $HOME_DIR/inst/usr/bin/mediaplat

  cd $HOME_DIR/inst
  tar jcvf $HOME_DIR/${PROJECT}_${ARCH}.tar.bz2 .

 
}

parse_args() {
  ARGS_ALL="$@"
  while [ "$1" != "" ]; do
    case "$1" in
	  "passconf") 	WITH_PASSCONF=yes ;;
	  "postgresql")	WITH_POSTGRESQL=yes ;;
	  "nginx") 		WITH_NGINX=yes ;;
	  "pylib") 		WITH_PYLIB=yes ;;
	  "compile") 	WITH_COMPILE=yes ;;
	esac
	shift
  done
}

make_dialog() {
  [ "$USE_DIALOG" = "no" ] && return

  SELECT_FILE=$(get_tempfile)
  dialog --colors --ascii-lines \
    --checklist "$PROJECT Build" 16 70 16 \
	"passconf"		"Skip ./configure" "$USE_PASSCONF" \
	"postgresql"	"Build PostgreSQL \Z1$POSTGRESQL_SRC" "on" \
	"nginx"			"Build NGiNX \Z1$NGINX_SRC" "on" \
	"pylib"			"Build Python Libraries" "on" \
	"compile"		"Compile MediaPlat code" "on" \
	2> $SELECT_FILE
  RESULT=$?
  if [ "$RESULT" = 0 ]; then
    parse_args $(cat $SELECT_FILE | sed 's/"//g')
  elif [ "RESULT" = 1 ]; then
    exit 1
  fi
  echo
}

auto() {
  WITH_PASSCONF=no
  WITH_POSTGRESQL=yes
  WITH_NGINX=yes
  WITH_PYLIB=yes

  echo $@ | grep "passconf"
  [ "$?" = "0" ] && WITH_PASSCONF=yes

  echo $@ | grep "min"
  if [ "$?" = "0" ]; then
    WITH_PASSCONF=yes
    WITH_POSTGRESQL=no
    WITH_NGINX=no
    WITH_PYLIB=no
  fi

}

main() {

  init
  if [ ! -z "$1" ]; then
    auto $@
  else 
    make_dialog
  fi
  build
  dist
}

trap cleanup INT TERM EXIT
main $@

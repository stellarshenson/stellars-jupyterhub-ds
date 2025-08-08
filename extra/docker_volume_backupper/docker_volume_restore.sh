#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup-file1.tar.gz|.tgz|.tar> [backup-file2 ...]"
  exit 1
fi

extract_volume_name() {
  local f="$1"
  local b
  b="$(basename "$f")"
  # strip known extensions
  b="${b%.tar.gz}"
  b="${b%.tgz}"
  b="${b%.tar}"
  # strip trailing _YYYY-MM-DD or -YYYY-MM-DD (optionally followed by anything)
  b="$(echo "$b" | sed -E 's/([_-][0-9]{4}-[0-9]{2}-[0-9]{2})([_-].*)?$//')"
  printf '%s' "$b"
}

volume_exists() {
  docker volume inspect "$1" >/dev/null 2>&1
}

tar_flag_for() {
  case "$1" in
    *.tar.gz|*.tgz) echo "xzf" ;;
    *.tar)          echo "xf"  ;;
    *)              echo "xzf" ;; # default assume gzip
  esac
}

for backup in "$@"; do
  if [ ! -f "$backup" ]; then
    echo "SKIP: file not found: $backup"
    continue
  fi

  vol="$(extract_volume_name "$backup")"
  if [ -z "$vol" ]; then
    echo "SKIP: could not infer volume name from $backup"
    continue
  fi

  if ! volume_exists "$vol"; then
    echo "SKIP: docker volume does not exist: $vol  (from $backup)"
    continue
  fi

  absdir="$(realpath "$(dirname "$backup")")"
  base="$(basename "$backup")"
  tarflags="$(tar_flag_for "$backup")"
  cname="restore_${vol}_$(date +%s)_$$"

  echo "RESTORE: $base -> volume $vol"

  # restore into volume: wipe existing contents then extract
  docker run --rm \
    --name "$cname" \
    -v "$vol":/data \
    -v "$absdir":/backup \
    alpine sh -c "
      set -e
      cd /data
      rm -rf ./* .??* 2>/dev/null || true
      tar ${tarflags} \"/backup/${base}\" -C /data
    "

  echo "OK: restored $vol"
done


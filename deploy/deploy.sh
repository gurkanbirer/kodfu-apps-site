#!/usr/bin/env bash
# Publish the Kodfu app sites to kodfu-box. Runbook: docs/deployment.md.
#   deploy/deploy.sh [app ...]        new release of each app folder from the committed HEAD (default: all five)
#   deploy/deploy.sh nginx            install/refresh the five vhosts (nginx -t && reload; restores on failure)
#   deploy/deploy.sh rollback <app>   point that app's `current` at its previous release
#   deploy/deploy.sh check            curl every host (status + TLS)
# Build first (python3 tools/build.py) and commit: a release is what is committed, never the working tree.
set -euo pipefail
cd "$(dirname "$0")/.."
TARGET="${TARGET:-kodfu-box}"
BASE=/srv/kodfu-apps-site
APPS=(sparkwise bluebell hivis tickover fareback)
host() { if [ "$1" = sparkwise ]; then echo sparkwiseapp.co.uk; else echo "$1.kodfu.com"; fi; }

release() {
  local app="$1" rel
  [ -d "$app" ] || { echo "no folder $app"; exit 2; }
  if ! git diff --quiet HEAD -- "$app" src tools || [ -n "$(git ls-files --others --exclude-standard -- "$app" src tools)" ]; then
    echo "warning: uncommitted changes in $app/, src/ or tools/ are NOT shipped (release = committed HEAD)"
  fi
  rel="$(date -u +%Y%m%d-%H%M%S)-$(git rev-parse --short=12 HEAD)"
  git archive HEAD "$app" | ssh "$TARGET" "set -e; d=$BASE/$app; mkdir -p \$d/releases/$rel; tar -x -C \$d/releases/$rel --strip-components=1; \
    rm -f \$d/releases/$rel/README.md; chown -R root:root \$d/releases/$rel; chmod -R a+rX $BASE; \
    ln -sfn \$d/releases/$rel \$d/current.new; mv -Tf \$d/current.new \$d/current; \
    ls -1dt \$d/releases/* | tail -n +6 | xargs -r rm -rf; echo \"$app: released $rel\""
}

case "${1:-all}" in
  all) for a in "${APPS[@]}"; do release "$a"; done ;;
  sparkwise|bluebell|hivis|tickover|fareback) for a in "$@"; do release "$a"; done ;;
  nginx)
    for a in "${APPS[@]}"; do
      h="$(host "$a")"
      ssh "$TARGET" "set -e; f=/etc/nginx/sites-available/$h; [ -f \$f ] && cp \$f /root/kodfu-apps-$h.vhost.bak || rm -f /root/kodfu-apps-$h.vhost.bak; cat > \$f.new" < "deploy/nginx/$h.conf"
    done
    ssh "$TARGET" "set -e; for h in $(for a in "${APPS[@]}"; do host "$a"; done | tr '\n' ' '); do f=/etc/nginx/sites-available/\$h; mv \$f.new \$f; ln -sfn \$f /etc/nginx/sites-enabled/\$h; done; \
      if nginx -t 2>/tmp/kodfu-apps-nginx-t.log; then nginx -s reload; echo 'nginx ok, reloaded'; \
      else cat /tmp/kodfu-apps-nginx-t.log; for h in $(for a in "${APPS[@]}"; do host "$a"; done | tr '\n' ' '); do f=/etc/nginx/sites-available/\$h; \
        if [ -f /root/kodfu-apps-\$h.vhost.bak ]; then cp /root/kodfu-apps-\$h.vhost.bak \$f; else rm -f /etc/nginx/sites-enabled/\$h \$f; fi; done; nginx -t && echo restored; exit 1; fi"
    ;;
  rollback)
    a="${2:?usage: $0 rollback <app>}"
    ssh "$TARGET" "set -e; d=$BASE/$a; prev=\$(ls -1dt \$d/releases/* | sed -n 2p); ln -sfn \$prev \$d/current.new; mv -Tf \$d/current.new \$d/current; echo now \$prev"
    ;;
  check)
    for a in "${APPS[@]}"; do h="$(host "$a")"
      for p in / /privacy/ /terms/ /sitemap.xml /robots.txt; do
        curl -sS -o /dev/null -w "%{http_code} ssl_verify=%{ssl_verify_result} https://$h$p\n" "https://$h$p"
      done
    done
    curl -sS -o /dev/null -w "%{http_code} -> %{redirect_url}  https://www.sparkwiseapp.co.uk/\n" https://www.sparkwiseapp.co.uk/
    ;;
  *) echo "usage: $0 [all|<app> ...|nginx|rollback <app>|check]"; exit 2 ;;
esac

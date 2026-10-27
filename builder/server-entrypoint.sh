#!/usr/bin/env bash
#
# trailcam-server entrypoint — project-plan §9 / §17 (house pattern, lugtrax
# lineage). Idempotent: safe to run on every container start.
#
#   1. php-fpm pool identity (house image runs as `ubuntu`, pool as www-data)
#   2. self-signed dev TLS in /etc/wapiti (production terminates at the edge)
#   3. site config (baked by Dockerfile.server) syntax check
#   4. php artisan migrate --force   (auth collections now; WI-102 the rest)
#   5. php-fpm + nginx in the foreground
set -euo pipefail

POOL=/etc/php/8.5/fpm/pool.d/www.conf
sudo sed -i "s/^user = www-data/user = ubuntu/; s/^group = www-data/group = ubuntu/; s/^listen.owner = www-data/listen.owner = ubuntu/; s/^listen.group = www-data/listen.group = ubuntu/" "$POOL"
grep -q "^listen.mode" "$POOL" || echo "listen.mode = 0666" | sudo tee -a "$POOL" >/dev/null

if [ ! -f /etc/wapiti/server.key ]; then
    sudo mkdir -p /etc/wapiti
    sudo openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout /etc/wapiti/server.key -out /etc/wapiti/server.crt \
        -days 3650 -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,DNS:default.wapiti.cam,IP:127.0.0.1,IP:172.17.0.1" \
        2>/dev/null
fi

sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t

cd /var/www/html
php artisan migrate --force

sudo service php8.5-fpm start
exec sudo nginx -g "daemon off;"

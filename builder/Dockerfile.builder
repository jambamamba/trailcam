# trailcam-builder:v1 — one-shot builder (project-plan §3.1, tests BLD-01..04).
#
# Base is the server image itself (trailcam-server:v1 = nginx:v5 + ext-mongodb
# 2.5.5) because the house image already carries PHP 8.5 + Composer + Node 22 +
# npm, and composer install must see a CVE-current ext-mongodb (WI-101 notes).
#
# Run against the mounted server/ (no EXPOSE — BLD-03 one-shot):
#   docker run --rm -v $REPO/server:/var/www/html trailcam-builder:v1
FROM trailcam-server:v1

WORKDIR /var/www/html

# composer install (idempotent). npm/vite joins here with the PWA (WI-305);
# the Yocto/Zephyr image builds are separate one-shots under device/ (WI-201+).
CMD ["bash", "-lc", "composer install --no-interaction --prefer-dist --no-progress && echo BUILDER_OK"]

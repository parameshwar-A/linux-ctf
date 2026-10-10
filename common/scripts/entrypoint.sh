#!/bin/bash
# Linux CTF - In-Container Hardened Entrypoint
set -e

# If CTF_FLAG is provided, execute compiled room initializer
if [ -n "${CTF_FLAG:-}" ] && [ -x /usr/local/bin/init-room ]; then
    /usr/local/bin/init-room "$CTF_FLAG" "$CTF_SALT" "$CTF_HASH"
fi

# Ensure /home/learner is properly owned and clean
if [ -d /home/learner ]; then
    chown -R learner:learner /home/learner
fi

# Wipe sensitive session secrets from environment
unset CTF_FLAG
unset CTF_SALT
unset CTF_HASH

cd /home/learner

# If command passed (e.g. non-interactive test), execute it under learner
if [ $# -gt 0 ]; then
    exec su - learner -c "$*"
else
    # Interactive login shell
    exec su - learner
fi

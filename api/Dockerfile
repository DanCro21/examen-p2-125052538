FROM python:3.12-slim

# openssh-client: para demostrar  ssh hadoop@hadoop  desde este contenedor
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

# Script de arranque embebido (requiere Docker 23+ / BuildKit).
# Copia la llave privada del volumen ssh_keys (solo lectura) a ~/.ssh con
# permisos correctos para poder hacer:  ssh hadoop@hadoop
COPY <<'EOF' /entrypoint.sh
#!/bin/sh
set -e
mkdir -p /root/.ssh && chmod 700 /root/.ssh
i=0
while [ ! -f /ssh-keys/id_ed25519 ] && [ $i -lt 60 ]; do i=$((i+1)); sleep 1; done
if [ -f /ssh-keys/id_ed25519 ]; then
  cp /ssh-keys/id_ed25519 /root/.ssh/id_ed25519
  chmod 600 /root/.ssh/id_ed25519
  printf 'Host hadoop\n    StrictHostKeyChecking accept-new\n' > /root/.ssh/config
fi
exec "$@"
EOF
RUN chmod +x /entrypoint.sh

EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]

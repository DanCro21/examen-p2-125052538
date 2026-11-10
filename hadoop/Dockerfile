# Hadoop standalone sobre Debian.
# Hadoop 3.3.x solo soporta Java 8/11 (Java 17 no es oficial), por eso se copia
# un OpenJDK 11 (Temurin) desde una etapa previa y se mantiene Debian como base.
FROM eclipse-temurin:11-jre AS jre

FROM debian:bookworm-slim

ARG HADOOP_VERSION=3.3.6
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 openssh-server openssh-client curl ca-certificates procps \
 && rm -rf /var/lib/apt/lists/*

# Java (OpenJDK 11)
COPY --from=jre /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV HADOOP_HOME=/opt/hadoop
ENV PATH=${PATH}:${JAVA_HOME}/bin:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin

# Hadoop (modo standalone: sin configuracion extra, usa el FS local)
RUN curl -fsSL https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz \
    | tar -xz -C /opt \
 && mv /opt/hadoop-${HADOOP_VERSION} ${HADOOP_HOME} \
 && echo "export JAVA_HOME=${JAVA_HOME}" >> ${HADOOP_HOME}/etc/hadoop/hadoop-env.sh

# Variables tambien para sesiones SSH no interactivas (ssh hadoop@hadoop <cmd>)
RUN printf 'JAVA_HOME=%s\nHADOOP_HOME=%s\nPATH=%s\n' \
      "${JAVA_HOME}" "${HADOOP_HOME}" \
      "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${JAVA_HOME}/bin:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin" \
      > /etc/environment

# Usuario sin contrasena (el acceso es solo por llave)
RUN useradd -m -s /bin/bash hadoop \
 && usermod -p '*' hadoop \
 && mkdir -p /home/hadoop/.ssh /data/input /data/output /run/sshd \
 && chmod 700 /home/hadoop/.ssh \
 && chown -R hadoop:hadoop /home/hadoop /data

# sshd: solo llaves, sin root
RUN printf 'PasswordAuthentication no\nPermitRootLogin no\nPubkeyAuthentication yes\n' \
      > /etc/ssh/sshd_config.d/10-hardening.conf

# Script de arranque embebido (requiere Docker 23+ / BuildKit).
# Genera llaves SSH sin contrasena (una sola vez, en el volumen ssh_keys).
COPY <<'EOF' /entrypoint.sh
#!/bin/bash
set -e
SSH_DIR=/home/hadoop/.ssh
ssh-keygen -A
if [ ! -f "$SSH_DIR/id_ed25519" ]; then
  runuser -u hadoop -- ssh-keygen -t ed25519 -N "" -q -f "$SSH_DIR/id_ed25519"
  cat "$SSH_DIR/id_ed25519.pub" > "$SSH_DIR/authorized_keys"
fi
printf 'Host localhost hadoop\n    StrictHostKeyChecking accept-new\n' > "$SSH_DIR/config"
chown -R hadoop:hadoop "$SSH_DIR"
chmod 700 "$SSH_DIR"
chmod 600 "$SSH_DIR/id_ed25519" "$SSH_DIR/authorized_keys" "$SSH_DIR/config"
exec "$@"
EOF
RUN chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/sbin/sshd", "-D", "-e"]

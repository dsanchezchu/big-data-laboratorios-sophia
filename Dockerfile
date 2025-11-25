FROM debian:12-slim

# Evitar preguntas interactivas durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias adicionales
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    wget \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    ssh \
    sudo \
    vim \
    net-tools \
    iputils-ping \
    gosu \
    netcat-traditional \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV HADOOP_HOME=/opt/hadoop
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin

# Crear usuario para servicios
RUN useradd -m -s /bin/bash hadoop && \
    echo "hadoop:hadoop" | chpasswd && \
    adduser hadoop sudo

# Descargar e instalar Hadoop
# Prefer local installers under 'installer/', otherwise download
COPY installer/ /tmp/installer/

RUN set -eux; \
    # Hadoop: prefer tarball, then directory, otherwise download tarball
    if [ -f /tmp/installer/hadoop-3.3.6.tar.gz ]; then \
        echo "Using local Hadoop tarball"; cp /tmp/installer/hadoop-3.3.6.tar.gz /tmp/hadoop.tar.gz; \
    elif [ -d /tmp/installer/hadoop-3.3.6 ]; then \
        echo "Using local Hadoop directory"; mv /tmp/installer/hadoop-3.3.6 $HADOOP_HOME; \
    else \
        echo "Downloading Hadoop"; wget https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz -O /tmp/hadoop.tar.gz; \
    fi; \
    if [ -f /tmp/hadoop.tar.gz ]; then \
        tar -xzf /tmp/hadoop.tar.gz -C /opt && mv /opt/hadoop-3.3.6 $HADOOP_HOME && rm /tmp/hadoop.tar.gz; \
    fi; \
    # Spark: prefer tarball, then directory, otherwise download tarball
    if [ -f /tmp/installer/spark-3.4.1-bin-hadoop3.tgz ]; then \
        echo "Using local Spark tarball"; cp /tmp/installer/spark-3.4.1-bin-hadoop3.tgz /tmp/spark.tar.gz; \
    elif [ -d /tmp/installer/spark-3.4.1-bin-hadoop3 ]; then \
        echo "Using local Spark directory"; mv /tmp/installer/spark-3.4.1-bin-hadoop3 $SPARK_HOME; \
    else \
        echo "Downloading Spark"; wget https://archive.apache.org/dist/spark/spark-3.4.1/spark-3.4.1-bin-hadoop3.tgz -O /tmp/spark.tar.gz; \
    fi; \
    if [ -f /tmp/spark.tar.gz ]; then \
        tar -xzf /tmp/spark.tar.gz -C /opt && mv /opt/spark-3.4.1-bin-hadoop3 $SPARK_HOME && rm /tmp/spark.tar.gz; \
    fi; \
    rm -rf /tmp/installer

# Configurar permisos
RUN chown -R hadoop:hadoop $HADOOP_HOME && \
    chown -R hadoop:hadoop $SPARK_HOME

# Configurar SSH sin contraseña
RUN mkdir -p /home/hadoop/.ssh && \
    ssh-keygen -t rsa -P '' -f /home/hadoop/.ssh/id_rsa && \
    cat /home/hadoop/.ssh/id_rsa.pub >> /home/hadoop/.ssh/authorized_keys && \
    chown -R hadoop:hadoop /home/hadoop/.ssh

# Crear entorno virtual y instalar dependencias de Python
RUN python3 -m venv /opt/python-env && \
    /opt/python-env/bin/pip install --upgrade pip && \
    /opt/python-env/bin/pip install --no-cache-dir \
        jupyterlab \
        pyspark==3.4.1 \
        pandas \
        numpy \
        findspark \
        matplotlib \
        seaborn \
        pyarrow \
        fastparquet \
        streamlit

# Agregar entorno virtual al PATH
ENV PATH="/opt/python-env/bin:$PATH"

# Crear directorios necesarios
RUN mkdir -p /data/hdfs/namenode && \
    mkdir -p /data/hdfs/datanode && \
    mkdir -p /home/jupyter/notebooks && \
    mkdir -p /scripts && \
    chown -R hadoop:hadoop /data /home/jupyter /scripts

# Copiar scripts y asegurar permisos correctos
COPY scripts/ /scripts/
RUN dos2unix /scripts/*.sh && \
    chmod +x /scripts/*.sh && \
    chown -R hadoop:hadoop /scripts

# Cambiar al usuario hadoop
USER hadoop

# Exponer puertos
EXPOSE 8020 9870 8088 8042 8888 8080 7077 4040

WORKDIR /home/hadoop
FROM debian:12-slim

# Evitar preguntas interactivas durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
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
RUN wget https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz -O /tmp/hadoop.tar.gz && \
    tar -xzf /tmp/hadoop.tar.gz -C /opt && \
    mv /opt/hadoop-3.3.6 $HADOOP_HOME && \
    rm /tmp/hadoop.tar.gz

# Descargar e instalar Spark
RUN wget https://archive.apache.org/dist/spark/spark-3.4.1/spark-3.4.1-bin-hadoop3.tgz -O /tmp/spark.tar.gz && \
    tar -xzf /tmp/spark.tar.gz -C /opt && \
    mv /opt/spark-3.4.1-bin-hadoop3 $SPARK_HOME && \
    rm /tmp/spark.tar.gz

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
        seaborn

# Agregar entorno virtual al PATH
ENV PATH="/opt/python-env/bin:$PATH"

# Crear directorios necesarios
RUN mkdir -p /data/hdfs/namenode && \
    mkdir -p /data/hdfs/datanode && \
    mkdir -p /home/jupyter/notebooks && \
    mkdir -p /scripts && \
    chown -R hadoop:hadoop /data /home/jupyter /scripts

# Copiar scripts
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

# Cambiar al usuario hadoop
USER hadoop

# Exponer puertos
EXPOSE 8020 9870 8088 8042 8888 8080 7077 4040

WORKDIR /home/hadoop
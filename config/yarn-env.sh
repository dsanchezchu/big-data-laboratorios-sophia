#!/bin/bash

# Java options for YARN ResourceManager
export YARN_RESOURCEMANAGER_OPTS="${YARN_RESOURCEMANAGER_OPTS} -Djava.net.preferIPv4Stack=true --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/java.lang.reflect=ALL-UNNAMED"

# Java options for YARN NodeManager
export YARN_NODEMANAGER_OPTS="${YARN_NODEMANAGER_OPTS} -Djava.net.preferIPv4Stack=true --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/java.lang.reflect=ALL-UNNAMED"

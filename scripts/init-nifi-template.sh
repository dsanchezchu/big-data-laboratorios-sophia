#!/bin/sh
# filepath: ./scripts/init-nifi-template.sh

NIFI_USER=admin
NIFI_PASS=ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB
NIFI_URL=http://nifi:8080/nifi-api
TEMPLATE_FILE=/conexion_nifi_a_hdfs.xml

# 1️⃣ Espera a que NiFi esté listo
echo "⏳ Esperando a que NiFi esté listo..."
until curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/status > /dev/null; do
  sleep 5
done
echo "✅ NiFi está listo"

# 2️⃣ Sube la plantilla
echo "📤 Subiendo plantilla..."
curl -s -u $NIFI_USER:$NIFI_PASS \
  -F template=@$TEMPLATE_FILE \
  $NIFI_URL/process-groups/root/templates/upload

# 3️⃣ Espera unos segundos a que NiFi registre la plantilla
sleep 5

# 4️⃣ Obtén el ID de la plantilla
TEMPLATE_ID=""
i=0
while [ -z "$TEMPLATE_ID" ] && [ $i -lt 10 ]; do
  TEMPLATE_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/templates \
    | grep -o '"id"[ ]*:[ ]*"[^"]*"' \
    | tail -n1 \
    | cut -d'"' -f4)

  if [ -n "$TEMPLATE_ID" ]; then
    echo "✅ Plantilla registrada con ID: $TEMPLATE_ID"
    break
  fi

  i=$((i+1))
  echo "⏳ Aún no aparece la plantilla, reintentando ($i)..."
  sleep 5
done

if [ -z "$TEMPLATE_ID" ]; then
  echo "❌ No se pudo obtener el ID de la plantilla"
  exit 1
fi

# 5️⃣ Instancia la plantilla en el root group con coordenadas
echo "📦 Instanciando plantilla en el root group..."
HTTP_CODE=$(curl -s -o /tmp/nifi_response.json -w "%{http_code}" -u $NIFI_USER:$NIFI_PASS \
  -H "Content-Type: application/json" \
  -X POST \
  -d "{\"templateId\":\"$TEMPLATE_ID\",\"originX\":0.0,\"originY\":0.0}" \
  $NIFI_URL/process-groups/root/template-instance)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
  echo "✅ Plantilla instanciada correctamente"
else
  echo "❌ Error instanciando plantilla, revisa /tmp/nifi_response.json"
  exit 1
fi

# 6️⃣ Obtén el ID del process group root
PROCESS_GROUP_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/process-groups/root \
  | grep -o '"id"[ ]*:[ ]*"[^"]*"' \
  | head -n1 \
  | cut -d'"' -f4)

# 7️⃣ Activa todos los procesadores
echo "▶️ Activando todos los procesadores..."
curl -s -u $NIFI_USER:$NIFI_PASS \
  -H "Content-Type: application/json" \
  -X PUT \
  -d '{"id":"'$PROCESS_GROUP_ID'","state":"RUNNING"}' \
  $NIFI_URL/flow/process-groups/$PROCESS_GROUP_ID

# 8️⃣ Mensaje de éxito
echo "✅ Plantilla cargada e instanciada correctamente"
echo "✅ Todos los procesadores están activos"
echo "🔍 El driver PostgreSQL está disponible en /opt/nifi/nifi-current/drivers/"
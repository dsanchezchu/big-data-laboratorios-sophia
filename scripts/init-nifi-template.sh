#!/bin/sh
# filepath: ./scripts/init-nifi-template.sh

NIFI_USER=admin
NIFI_PASS=ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB
NIFI_URL=http://nifi:8080/nifi-api
TEMPLATE_DIR=/template

# 1️⃣ Espera a que NiFi esté listo
echo "⏳ Esperando a que NiFi esté listo..."
until curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/status > /dev/null; do
  sleep 5
done
echo "✅ NiFi está listo"

# 2️⃣ Obtener el primer archivo xml del directorio
TEMPLATE_FILE=$(ls $TEMPLATE_DIR/*.xml 2>/dev/null | head -n1)

if [ -z "$TEMPLATE_FILE" ]; then
  echo "❌ No se encontró ningún XML en $TEMPLATE_DIR"
  exit 1
fi

# 3️⃣ Extraer el nombre del template del XML
TEMPLATE_NAME=$(sed -n 's:.*<name>\(.*\)</name>.*:\1:p' "$TEMPLATE_FILE" | head -n1)

if [ -z "$TEMPLATE_NAME" ]; then
  echo "❌ No se pudo obtener el nombre del template de $TEMPLATE_FILE"
  exit 1
fi
echo "🔍 Nombre del template: $TEMPLATE_NAME"

# 4️⃣ Revisar si ya existe un template con ese nombre en NiFi
EXISTING_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/templates \
  | grep -A5 "\"name\"[ ]*:[ ]*\"$TEMPLATE_NAME\"" \
  | grep '"id"' \
  | head -n1 \
  | cut -d'"' -f4)

if [ -n "$EXISTING_ID" ]; then
  echo "⚠️  El template '$TEMPLATE_NAME' ya existe con ID $EXISTING_ID. No se subirá de nuevo."
  exit 0
fi

# 5️⃣ Subir la plantilla
echo "📤 Subiendo plantilla: $TEMPLATE_FILE ..."
curl -s -u $NIFI_USER:$NIFI_PASS \
  -F template=@$TEMPLATE_FILE \
  $NIFI_URL/process-groups/root/templates/upload

# 6️⃣ Esperar a que NiFi registre la plantilla
sleep 5

# 7️⃣ Obtener el ID de la nueva plantilla
TEMPLATE_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/templates \
  | sed -n "s/.*\"id\"[ ]*:[ ]*\"\([a-f0-9-]\+\)\".*/\1/p" \
  | head -n1)

if [ -z "$TEMPLATE_ID" ]; then
  echo "❌ No se pudo obtener el ID del template recién subido"
  exit 1
fi
echo "✅ Plantilla registrada con ID: $TEMPLATE_ID"

# 8️⃣ Instanciar la plantilla en el root group
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

# 9️⃣ Activar todos los procesadores en el root
PROCESS_GROUP_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/process-groups/root \
  | grep -o '"id"[ ]*:[ ]*"[^"]*"' \
  | head -n1 \
  | cut -d'"' -f4)

echo "▶️ Activando todos los procesadores..."
curl -s -u $NIFI_USER:$NIFI_PASS \
  -H "Content-Type: application/json" \
  -X PUT \
  -d '{"id":"'$PROCESS_GROUP_ID'","state":"RUNNING"}' \
  $NIFI_URL/flow/process-groups/$PROCESS_GROUP_ID

echo "✅ Plantilla '$TEMPLATE_NAME' cargada e instanciada correctamente"
echo "✅ Todos los procesadores están activos"
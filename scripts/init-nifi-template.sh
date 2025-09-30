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

# 2️⃣ Verificar credenciales en archivo .env
echo "🔐 Verificando credenciales en archivo .env..."

# Verificar si existe SupabaseConfig.json, si no crearlo desde el ejemplo
if [ ! -f "$TEMPLATE_DIR/parameter-contexts/SupabaseConfig.json" ]; then
  if [ -f "$TEMPLATE_DIR/parameter-contexts/SupabaseConfig.json.example" ]; then
    echo "📋 Creando SupabaseConfig.json desde el archivo ejemplo..."
    cp "$TEMPLATE_DIR/parameter-contexts/SupabaseConfig.json.example" "$TEMPLATE_DIR/parameter-contexts/SupabaseConfig.json"
  else
    echo "❌ No se encontró archivo ejemplo SupabaseConfig.json.example"
    exit 1
  fi
fi

if [ -f "/.env" ]; then
  # Leer variables del archivo .env
  SUPABASE_URL=$(grep "^SUPABASE_URL=" /.env | cut -d'=' -f2- | tr -d '"')
  SUPABASE_USERNAME=$(grep "^SUPABASE_USERNAME=" /.env | cut -d'=' -f2- | tr -d '"')
  SUPABASE_PASSWORD=$(grep "^SUPABASE_PASSWORD=" /.env | cut -d'=' -f2- | tr -d '"')
  DATABASE_DRIVER=$(grep "^DATABASE_DRIVER=" /.env | cut -d'=' -f2- | tr -d '"')
  
  # Verificar que las credenciales no sean valores de ejemplo
  if [ "$SUPABASE_URL" != "your_supabase_url_here" ] && [ "$SUPABASE_USERNAME" != "your_username_here" ] && [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_USERNAME" ]; then
    echo "✅ Credenciales válidas encontradas en .env"
    
    # Actualizar SupabaseConfig.json con credenciales reales
    cat > $TEMPLATE_DIR/parameter-contexts/SupabaseConfig.json << EOF
{
  "parameterContext": {
    "name": "SupabaseConfig",
    "description": "Configuración de conexión a Supabase",
    "parameters": [
      {
        "parameter": {
          "name": "supabase_url",
          "description": "URL de conexión a Supabase",
          "sensitive": false,
          "value": "$SUPABASE_URL"
        }
      },
      {
        "parameter": {
          "name": "supabase_username",
          "description": "Usuario de la base de datos",
          "sensitive": false,
          "value": "$SUPABASE_USERNAME"
        }
      },
      {
        "parameter": {
          "name": "supabase_password",
          "description": "Contraseña de la base de datos",
          "sensitive": true,
          "value": "$SUPABASE_PASSWORD"
        }
      },
      {
        "parameter": {
          "name": "database_driver",
          "description": "Driver JDBC para PostgreSQL",
          "sensitive": false,
          "value": "$DATABASE_DRIVER"
        }
      }
    ]
  }
}
EOF
    echo "✅ SupabaseConfig.json actualizado con credenciales del archivo .env"
  else
    echo "⚠️  Las credenciales en .env parecen ser valores de ejemplo, usando configuración actual"
  fi
else
  echo "📝 No se encontró archivo .env, usando configuración actual de SupabaseConfig.json"
fi

# 3️⃣ Obtener el primer archivo xml del directorio
TEMPLATE_FILE=$(ls $TEMPLATE_DIR/*.xml 2>/dev/null | head -n1)

if [ -z "$TEMPLATE_FILE" ]; then
  echo "❌ No se encontró ningún XML en $TEMPLATE_DIR"
  exit 1
fi

# 4️⃣ Extraer el nombre del template del XML
TEMPLATE_NAME=$(sed -n 's:.*<name>\(.*\)</name>.*:\1:p' "$TEMPLATE_FILE" | head -n1)

if [ -z "$TEMPLATE_NAME" ]; then
  echo "❌ No se pudo obtener el nombre del template de $TEMPLATE_FILE"
  exit 1
fi
echo "🔍 Nombre del template: $TEMPLATE_NAME"

# 5️⃣ Revisar si ya existe un template con ese nombre en NiFi
EXISTING_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/templates \
  | grep -A5 "\"name\"[ ]*:[ ]*\"$TEMPLATE_NAME\"" \
  | grep '"id"' \
  | head -n1 \
  | cut -d'"' -f4)

if [ -n "$EXISTING_ID" ]; then
  echo "⚠️  El template '$TEMPLATE_NAME' ya existe con ID $EXISTING_ID. Continuando con configuración..."
else
  # 6️⃣ Subir la plantilla
  echo "📤 Subiendo plantilla: $TEMPLATE_FILE ..."
  curl -s -u $NIFI_USER:$NIFI_PASS \
    -F template=@$TEMPLATE_FILE \
    $NIFI_URL/process-groups/root/templates/upload

  # Esperar a que NiFi registre la plantilla
  sleep 3

  # Obtener el ID de la nueva plantilla
  TEMPLATE_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/templates \
    | sed -n "s/.*\"id\"[ ]*:[ ]*\"\([a-f0-9-]\+\)\".*/\1/p" \
    | head -n1)

  if [ -z "$TEMPLATE_ID" ]; then
    echo "❌ No se pudo obtener el ID del template recién subido"
    exit 1
  fi
  echo "✅ Plantilla registrada con ID: $TEMPLATE_ID"

  # 7️⃣ Instanciar la plantilla en el root group
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
fi

# 8️⃣ Cargar Parameter Contexts
echo "🔧 Cargando Parameter Contexts..."
PARAM_CONTEXT_DIR="$TEMPLATE_DIR/parameter-contexts"

if [ -d "$PARAM_CONTEXT_DIR" ]; then
  for param_file in "$PARAM_CONTEXT_DIR"/*.json; do
    if [ -f "$param_file" ]; then
      PARAM_NAME=$(basename "$param_file" .json)
      echo "📝 Procesando Parameter Context: $PARAM_NAME"
      
      # Verificar si el Parameter Context ya existe
      EXISTING_PARAM_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/parameter-contexts \
        | grep -B2 -A2 "\"name\"[ ]*:[ ]*\"$PARAM_NAME\"" \
        | grep '"id"' \
        | head -n1 \
        | cut -d'"' -f4)
      
      if [ -n "$EXISTING_PARAM_ID" ]; then
        echo "✅ Parameter Context '$PARAM_NAME' ya existe con ID: $EXISTING_PARAM_ID"
        
        # Si es SupabaseConfig, guardar el ID para vinculación
        if [ "$PARAM_NAME" = "SupabaseConfig" ]; then
          SUPABASE_PARAM_ID="$EXISTING_PARAM_ID"
        fi
      else
        echo "➕ Creando nuevo Parameter Context: $PARAM_NAME"
        
        # Crear nuevo Parameter Context
        PARAM_CREATE_RESPONSE=$(curl -s -u $NIFI_USER:$NIFI_PASS \
          -H "Content-Type: application/json" \
          -X POST \
          -d @"$param_file" \
          $NIFI_URL/parameter-contexts)
        
        # Extraer el ID del Parameter Context recién creado
        NEW_PARAM_ID=$(echo "$PARAM_CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -n1 | cut -d'"' -f4)
        
        echo "✅ Parameter Context '$PARAM_NAME' creado con ID: $NEW_PARAM_ID"
        
        # Si es SupabaseConfig, guardar el ID para vinculación
        if [ "$PARAM_NAME" = "SupabaseConfig" ]; then
          SUPABASE_PARAM_ID="$NEW_PARAM_ID"
        fi
      fi
    fi
  done
else
  echo "⚠️  No se encontró directorio de Parameter Contexts: $PARAM_CONTEXT_DIR"
fi

# 9️⃣ Vincular Parameter Context SupabaseConfig al Process Group "NiFi Flow"
echo "🔗 Vinculando SupabaseConfig al Process Group 'NiFi Flow'..."

# Si no se capturó el ID durante la creación, intentar buscarlo
if [ -z "$SUPABASE_PARAM_ID" ]; then
  echo "🔍 Buscando Parameter Context SupabaseConfig..."
  PARAM_RESPONSE=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/parameter-contexts)
  SUPABASE_PARAM_ID=$(echo "$PARAM_RESPONSE" | sed 's/},{/}\n{/g' | grep '"name":"SupabaseConfig"' | sed 's/.*"id":"\([^"]*\)".*/\1/')
fi

if [ -n "$SUPABASE_PARAM_ID" ]; then
  echo "🔍 Parameter Context SupabaseConfig encontrado con ID: $SUPABASE_PARAM_ID"
  
  # Buscar el Process Group "NiFi Flow" específicamente
  echo "🔍 Buscando Process Group 'NiFi Flow'..."
  
  NIFI_FLOW_PG_ID=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/process-groups/root \
    | sed 's/},{/}\n{/g' \
    | grep '"name":"NiFi Flow"' \
    | grep -o '"id":"[^"]*"' \
    | head -n1 \
    | cut -d'"' -f4)
  
  if [ -n "$NIFI_FLOW_PG_ID" ]; then
    echo "🎯 Process Group 'NiFi Flow' encontrado con ID: $NIFI_FLOW_PG_ID"
    
    # Obtener información actual del Process Group
    PG_INFO=$(curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/process-groups/$NIFI_FLOW_PG_ID)
    
    # Verificar si ya tiene un Parameter Context asignado
    CURRENT_PARAM_CONTEXT=$(echo "$PG_INFO" | grep -o '"parameterContext":{"id":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$CURRENT_PARAM_CONTEXT" = "$SUPABASE_PARAM_ID" ]; then
      echo "✅ Process Group 'NiFi Flow' ya tiene SupabaseConfig vinculado"
    else
      # Extraer revisión actual
      CURRENT_REV=$(echo "$PG_INFO" | grep -o '"version":[0-9]*' | head -n1 | cut -d':' -f2)
      
      echo "🔗 Vinculando SupabaseConfig al Process Group 'NiFi Flow' (rev: $CURRENT_REV)"
      
      # Crear JSON para actualizar el Process Group con Parameter Context
      UPDATE_JSON="{
        \"revision\": {
          \"version\": $CURRENT_REV
        },
        \"component\": {
          \"id\": \"$NIFI_FLOW_PG_ID\",
          \"parameterContext\": {
            \"id\": \"$SUPABASE_PARAM_ID\"
          }
        }
      }"
      
      # Actualizar Process Group con Parameter Context
      HTTP_CODE=$(curl -s -o /tmp/pg_update_response.json -w "%{http_code}" -u $NIFI_USER:$NIFI_PASS \
        -H "Content-Type: application/json" \
        -X PUT \
        -d "$UPDATE_JSON" \
        $NIFI_URL/process-groups/$NIFI_FLOW_PG_ID)
      
      if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo "✅ Parameter Context SupabaseConfig vinculado exitosamente al Process Group 'NiFi Flow'"
      else
        echo "⚠️  Error vinculando Parameter Context (HTTP: $HTTP_CODE)"
        echo "📋 Respuesta: $(cat /tmp/pg_update_response.json 2>/dev/null || echo 'No response file')"
      fi
    fi
  else
    echo "❌ No se encontró Process Group 'NiFi Flow'"
    echo "📋 Process Groups disponibles:"
    curl -s -u $NIFI_USER:$NIFI_PASS $NIFI_URL/flow/process-groups/root \
      | sed 's/},{/}\n{/g' \
      | grep '"name":' \
      | grep -o '"name":"[^"]*"' \
      | cut -d'"' -f4 \
      | head -10
  fi
else
  echo "❌ No se encontró Parameter Context SupabaseConfig"
fi

echo "✅ Plantilla '$TEMPLATE_NAME' cargada e instanciada correctamente"
echo "✅ Parameter Contexts configurados y vinculados automáticamente"
echo "✅ Todos los procesadores están listos para usar"
echo "💡 Nota: Los Controller Services deben habilitarse manualmente desde la UI de NiFi"
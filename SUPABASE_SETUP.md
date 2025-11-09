# 🚀 Configuración Automática de Credenciales de Supabase para NiFi

Este sistema permite que cualquier miembro del equipo configure **automáticamente** las credenciales de Supabase para que el **DBCPConnectionPool** de NiFi funcione correctamente con el **Parameter Context "SupabaseConfig"**.

## 📋 Flujo Automático

El sistema ahora **detecta automáticamente** las credenciales y las configura sin scripts adicionales:

```bash
# 🎯 Solo necesitas hacer esto:
1. Crear archivo .env con tus credenciales
2. Ejecutar: docker compose up -d
3. ¡NiFi tendrá las credenciales automáticamente!
```

## 🔧 Configuración Inicial (Una sola vez por persona)

### Paso 1: Obtener credenciales de Supabase
1. Ve a tu proyecto de Supabase
2. Settings → Database → Connection string
3. Copia la información de conexión

### Paso 2: Crear archivo .env
Crea el archivo `.env` en la raíz del proyecto:

```env
# Archivo: .env
SUPABASE_URL=jdbc:postgresql://aws-0-us-east-1.pooler.supabase.com:5432/postgres
SUPABASE_USERNAME=postgres.tuproyecto
SUPABASE_PASSWORD=tu_password_real
DATABASE_DRIVER=org.postgresql.Driver
```

### Paso 3: Ejecutar Docker
```bash
docker compose up -d
```

## ✨ ¿Qué sucede automáticamente?

1. **Al iniciar Docker**: El contenedor `nifi-init` lee automáticamente tu archivo `.env`
2. **Detección inteligente**: Si encuentra credenciales válidas (no ejemplos), actualiza `SupabaseConfig.json`
3. **Carga automática**: NiFi recibe el Parameter Context "SupabaseConfig" con tus credenciales
4. **Sin intervención**: Todo funciona sin scripts adicionales

## 🔒 Seguridad

- El archivo `.env` está en `.gitignore` (nunca se sube al repo)
- Las credenciales solo existen localmente
- Cada miembro del equipo usa sus propias credenciales
- Los parámetros sensibles se marcan como `sensitive: true` en NiFi

## 👥 Para nuevos miembros del equipo

```bash
# 1. Clona el repositorio
git clone [repo-url]

# 2. Crea tu archivo .env con credenciales reales
cat > .env << EOF
SUPABASE_URL=jdbc:postgresql://aws-0-us-east-1.pooler.supabase.com:5432/postgres
SUPABASE_USERNAME=postgres.tuproyecto
SUPABASE_PASSWORD=tu_password_real
DATABASE_DRIVER=org.postgresql.Driver
EOF

# 3. Ejecuta Docker
docker compose up -d

# ¡Listo! NiFi tendrá las credenciales configuradas automáticamente
```

## 🔧 DBCPConnectionPool Configuration

En tu DBCPConnectionPool de NiFi, usa estos valores:

| Propiedad | Valor |
|-----------|-------|
| Database Connection URL | `#{supabase_url}` |
| Database Driver Class Name | `#{database_driver}` |
| Database User | `#{supabase_username}` |
| Password | `#{supabase_password}` |

## 🐛 Solución de Problemas

### Error: "No se puede conectar a Supabase"
- Verifica que las credenciales sean correctas en tu archivo `.env`
- Asegúrate de que tu IP esté en la lista blanca de Supabase
- Verifica que el proyecto de Supabase esté activo

### Parameter Context no aparece en NiFi
- Verifica que el archivo `.env` exista en la raíz del proyecto
- Revisa los logs del contenedor nifi-init: `docker logs nifi-init`
- Reinicia el contenedor de NiFi: `docker compose restart nifi nifi-init`

### Credenciales no se actualizan
- Asegúrate de que el archivo `.env` no tenga valores de ejemplo
- Verifica que las variables en `.env` no tengan espacios alrededor del `=`
- Formato correcto: `SUPABASE_URL=valor` (sin espacios)

## 📁 Estructura Final del Proyecto

```
📁 template/
  📁 parameter-contexts/
    📄 SupabaseConfig.json          # Se actualiza automáticamente
📄 .env.example                     # Ejemplo de credenciales  
📄 .env                            # Tus credenciales (gitignored)
📄 SUPABASE_SETUP.md               # Esta documentación
📄 docker-compose.yml              # Configuración con montaje automático
📁 scripts/
  📄 init-nifi-template.sh         # Script con detección automática
```

## 🎯 Resumen del Flujo Automático

1. **Desarrollador crea** → Archivo `.env` con credenciales reales
2. **Docker detecta** → Credenciales automáticamente al iniciar
3. **NiFi recibe** → Parameter Context "SupabaseConfig" configurado  
4. **DBCPConnectionPool** → Funciona inmediatamente con `#{supabase_*}`

¡Todo automático, sin scripts manuales! 🚀
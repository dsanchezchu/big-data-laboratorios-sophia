# 🚀 Despliegue en GitHub Codespaces

## ⚡ Inicio Ultra Rápido (1 clic)

1. **Abrir en Codespaces:**
   
   [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dsanchezchu/big-data-laboratorios-sophia)

2. **Esperar a que se configure** (2-3 minutos)

3. **Ejecutar el setup:**
   ```bash
   ./setup.sh
   ```

4. **¡Listo!** Las interfaces estarán disponibles en los puertos:
   - 🌐 Hadoop UI: Puerto 9870
   - ⚡ Spark UI: Puerto 8080  
   - 📓 Jupyter: Puerto 8888

## 🔧 Configuración Automática

El proyecto incluye configuración de **Dev Container** que automáticamente:

✅ Instala Docker y Docker Compose
✅ Configura Java 17
✅ Instala Python 3.11
✅ Expone los puertos necesarios
✅ Configura VS Code con extensiones útiles

## 💡 Tips para Codespaces

- **Tiempo gratuito**: 120 horas/mes
- **Máquina recomendada**: 4-core (8GB RAM)
- **Auto-save**: Los cambios se guardan automáticamente
- **Compartir**: Puedes hacer público el Codespace

## 🌐 Acceso a las Interfaces

Codespaces automáticamente detecta los puertos y los hace accesibles:

1. **Panel de Puertos**: Ve a la pestaña "PORTS" en VS Code
2. **Click en el puerto**: Para abrir en nueva pestaña
3. **URLs públicas**: Disponibles para compartir

## 🔗 Enlaces Directos

Una vez iniciado el cluster, las URLs serán algo como:

```
https://scaling-space-disco-abc123.github.dev/  # Tu workspace
├── :8888  # Jupyter Lab
├── :9870  # Hadoop UI  
├── :8080  # Spark Master
└── :8081  # Spark Worker
```

## 🎯 Perfecta para:

- ✅ **Estudiantes**: Sin instalación local
- ✅ **Profesores**: Demostrar en clase
- ✅ **Colaboración**: Compartir workspace
- ✅ **Desarrollo**: Ambiente consistente

---

**¡Con Codespaces tu cluster Big Data estará listo en menos de 5 minutos! 🚀**
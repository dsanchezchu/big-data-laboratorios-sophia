# 🚀 Guía Rápida - Big Data Laboratorios Sophia

## ⚡ Inicio Ultra Rápido (Para Compañeros)

### 🎯 Solo 3 pasos:

1. **Clonar y entrar al directorio**:
   ```bash
   git clone https://github.com/dsanchezchu/big-data-laboratorios-sophia.git
   cd big-data-laboratorios-sophia
   ```

2. **Ejecutar setup automático**:
   
   **Linux/Mac**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   
   **Windows PowerShell** (como Administrador):
   ```powershell
   .\setup.ps1
   ```

3. **¡Listo! Acceder a las interfaces**:
   - 🌐 Hadoop: http://localhost:9870
   - ⚡ Spark: http://localhost:8080  
   - 📓 Jupyter: http://localhost:8888 (usar token del log)

---

## 🎓 Para el Examen/Laboratorio

### Comandos Básicos HDFS:
```bash
# Crear directorio
docker exec namenode hdfs dfs -mkdir /datos

# Subir archivo
echo "Hola Sophia!" | docker exec -i namenode hdfs dfs -put - /datos/test.txt

# Listar archivos  
docker exec namenode hdfs dfs -ls /

# Leer archivo
docker exec namenode hdfs dfs -cat /datos/test.txt
```

### Token Jupyter:
```bash
# Windows
docker-compose logs jupyter | Select-String "token"

# Linux/Mac  
docker-compose logs jupyter | grep token
```

### Verificar Cluster:
```bash
docker-compose ps
docker exec namenode hdfs dfsadmin -report
```

---

## 🆘 Problemas Comunes

❌ **"Port already in use"** → `docker-compose down && docker-compose up -d`

❌ **"No se conecta"** → Esperar 2-3 minutos después del `docker-compose up -d`

❌ **Docker no funciona** → Reiniciar Docker Desktop

❌ **Token no aparece** → `docker-compose restart jupyter`

---

## 📞 Ayuda

- Ver logs: `docker-compose logs [servicio]`
- Reiniciar: `docker-compose restart [servicio]`  
- Limpiar todo: `docker-compose down --volumes`

**¡Cualquier duda, pregunta a Diego! 👨‍💻**
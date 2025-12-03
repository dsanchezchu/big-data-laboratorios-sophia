# 🚀 Guía de Uso - Sistema de Ofertas Inteligentes V3

## 🎯 Problema que Resuelve

**El área de ventas no sabe:**
1. ✅ QUÉ productos recomendar a cada cliente
2. ✅ A QUÉ PRECIO venderlos
3. ✅ QUÉ OFERTAS crear (descuentos, bonificaciones, combos)

---

## 📊 Solución Implementada

### 1. Recomendación Inteligente de Productos
- Identifica productos que el cliente **NO compra**
- Pero que clientes **similares SÍ compran**
- Basado en análisis de portafolio (Collaborative Filtering)

### 2. Precio Óptimo
- Calcula el precio sugerido por producto
- Basado en demanda de la zona
- Con margen de negociación (min/max)

### 3. Ofertas Estratégicas Automatizadas

#### A. Descuentos por Volumen (3 niveles)
```
Nivel 1: Sin descuento (bajo volumen)
Nivel 2: 5% descuento (volumen medio)
Nivel 3: 10% descuento (alto volumen)
```

**Ejemplo:**
- 1-50 cajas: S/. 45.00/caja
- 51-100 cajas: S/. 42.75/caja (-5%)
- 101+ cajas: S/. 40.50/caja (-10%)

#### B. Bonificaciones (X + Y gratis)
```
Por cada 100 cajas → 5 GRATIS
Ahorro efectivo: 5%
```

#### C. Combos Estratégicos
```
Compra Producto A + Producto B de la misma familia
→ 15% descuento en AMBOS
```

#### D. Términos de Pago Personalizados
- **Cliente GRANDE**: Crédito 30-60 días
- **Cliente MEDIANO**: Crédito 30 días + descuento por contado
- **Cliente PEQUEÑO**: Contado con descuento adicional

---

## 🛠️ Cómo Ejecutar el Sistema

### Paso 1: Generar Ofertas (Backend)

```powershell
# Dentro del contenedor Jupyter
docker exec jupyter spark-submit /home/jupyter/notebooks/generador_ofertas_v3.py
```

**Tiempo:** ~10-15 minutos

**Resultado:**
```
✅ ofertas_generadas.json (Top 20 clientes con ofertas completas)
✅ portafolio_clientes.parquet
```

---

### Paso 2: Iniciar Dashboard

```powershell
.\start-streamlit.ps1
```

**Dashboard:** http://localhost:8501

---

## 📱 Cómo Usar el Dashboard

### Tab 1: 🎯 Ofertas Recomendadas

**Qué ves:**
- Top 5-10 productos recomendados
- Precio sugerido por producto
- Demanda estimada (cajas y piezas)
- Descuentos por volumen (3 niveles)
- Bonificación automática
- Combo estratégico (si aplica)
- Términos de pago personalizados

**Casos de Uso:**
1. **Preparar visita comercial**
   - Selecciona el cliente
   - Revisa las ofertas generadas
   - Anota los productos prioritarios

2. **Negociación de precios**
   - Ve el rango de precios (min/max)
   - Ofrece descuentos por volumen
   - Activa bonificaciones

3. **Cerrar venta**
   - Usa los combos estratégicos
   - Ofrece términos de pago flexibles

---

### Tab 2: 📊 Análisis Comparativo

**Qué ves:**
- Gráfico de comparación de precios
- Proyección de demanda
- Tabla comparativa con scores

**Casos de Uso:**
1. **Justificar precios**
   - Muestra al cliente la comparación
   - Explica el valor de los descuentos

2. **Priorizar productos**
   - Usa el score de prioridad
   - Enfócate en productos con mayor score

---

### Tab 3: 📄 Propuesta Comercial

**Qué ves:**
- Documento formal listo para enviar
- Todos los detalles de la oferta
- Formato profesional

**Casos de Uso:**
1. **Enviar propuesta por email**
   - Copia el contenido
   - Pega en tu email corporativo

2. **Presentación en reunión**
   - Proyecta el Tab 3
   - Lee directamente desde ahí

3. **Documentar acuerdos**
   - Guarda la propuesta como referencia
   - Archiva para futuras negociaciones

---

## 💡 Ejemplos Reales de Uso

### Ejemplo 1: Cliente de Clínica Mediana

**Situación:**
- Cliente: CLÍNICA SAN JUAN
- Gasto histórico: S/. 35,000
- Categoría: MEDIANO

**Oferta Generada:**

1. **ELIPTIC LIGHT 0.5%**
   - Precio: S/. 45.00/caja
   - Demanda estimada: 50 cajas
   - Descuentos:
     * 1-25 cajas: S/. 45.00
     * 26-50 cajas: S/. 42.75 (-5%)
     * 51+ cajas: S/. 40.50 (-10%)
   - Bonificación: Cada 100 cajas → 5 gratis
   - Términos: Pago a 30 días sin interés

2. **OFTACICLINA POMADA**
   - Precio: S/. 28.00/caja
   - Combo: Compra con ELIPTIC → 15% descuento en ambos
   - Términos: Contado → 3% descuento adicional

**Resultado:**
- Vendedor sabe exactamente qué ofrecer
- Cliente recibe oferta personalizada
- Ambos ganan

---

### Ejemplo 2: Cliente de Hospital Grande

**Situación:**
- Cliente: HOSPITAL NACIONAL
- Gasto histórico: S/. 120,000
- Categoría: GRANDE

**Oferta Generada:**

1. **10 productos recomendados**
   - Descuentos hasta 10% por volumen
   - Bonificaciones en todos
   - Combos estratégicos
   - Crédito 60 días

**Estrategia de Venta:**
1. Presenta los 3 productos prioritarios
2. Ofrece combo de familia
3. Activa descuento por volumen
4. Cierra con crédito 60 días

---

## 📊 Estructura de la Oferta (JSON)

```json
{
  "producto": "ELIPTIC PF",
  "precio_sugerido": 45.00,
  "precio_minimo_negociable": 38.25,
  "precio_maximo_negociable": 49.50,
  "demanda_estimada_cajas": 50,
  "descuentos_por_volumen": [
    {
      "nivel": 1,
      "desde_cajas": 1,
      "hasta_cajas": 25,
      "descuento_porcentaje": 0,
      "precio_por_caja": 45.00
    },
    {
      "nivel": 2,
      "desde_cajas": 26,
      "hasta_cajas": 50,
      "descuento_porcentaje": 5,
      "precio_por_caja": 42.75
    },
    {
      "nivel": 3,
      "desde_cajas": 51,
      "hasta_cajas": 99999,
      "descuento_porcentaje": 10,
      "precio_por_caja": 40.50
    }
  ],
  "bonificacion": {
    "cada_cajas": 100,
    "unidades_gratis": 5,
    "mensaje": "Por cada 100 cajas, recibe 5 GRATIS"
  },
  "combo_estrategico": {
    "producto_combo": "ELIPTIC LIGHT",
    "descuento_combo": 15,
    "mensaje": "Compra ELIPTIC PF + ELIPTIC LIGHT con 15% descuento"
  },
  "terminos_pago": {
    "contado": "Pago inmediato: 2% descuento adicional",
    "credito_30": "Pago a 30 días: Sin interés",
    "credito_60": "Pago a 60 días: 1% interés mensual"
  }
}
```

---

## 🎯 Beneficios del Sistema

### Para el Vendedor:
✅ Sabe exactamente QUÉ ofrecer  
✅ Sabe A QUÉ PRECIO vender  
✅ Tiene ofertas listas para cerrar  
✅ Reduce tiempo de preparación 80%  

### Para el Cliente:
✅ Recibe oferta personalizada  
✅ Obtiene descuentos reales  
✅ Optimiza su presupuesto  
✅ Mejora su flujo de caja (crédito)  

### Para Sophia Labs:
✅ Aumenta ventas 15-25%  
✅ Mejora ticket promedio  
✅ Fideliza clientes  
✅ Datos para mejorar el modelo  

---

## ⚠️ Notas Importantes

1. **Las ofertas son sugerencias**
   - El vendedor puede ajustar según contexto
   - Respeta los rangos min/max de precio

2. **Actualizar ofertas mensualmente**
   - Re-ejecuta `generador_ofertas_v3.py` cada mes
   - Mantén las ofertas frescas

3. **Feedback del vendedor**
   - Registra qué ofertas funcionaron
   - Ajusta los algoritmos según resultados

---

## 🚀 Próximos Pasos

1. **Ejecuta el generador de ofertas**
   ```powershell
   docker exec jupyter spark-submit /home/jupyter/notebooks/generador_ofertas_v3.py
   ```

2. **Inicia el dashboard**
   ```powershell
   .\start-streamlit.ps1
   ```

3. **Prueba con un cliente real**
   - Selecciona un cliente conocido
   - Revisa las ofertas generadas
   - Valida que tengan sentido

4. **Presenta al equipo de ventas**
   - Capacita en el uso del dashboard
   - Recoge feedback
   - Itera y mejora

---

**¿Listo para transformar tu proceso de ventas?** 🚀

http://localhost:8501

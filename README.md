# NinjaSpam

**NinjaSpam** es un proyecto académico y experimental orientado al análisis de correos electrónicos mediante tecnologías web e inteligencia artificial, con el propósito de apoyar la identificación de posibles mensajes no deseados, sospechosos o con características asociadas al spam.

El sistema permite conectarse automáticamente a una cuenta de correo mediante IMAP, cargar mensajes recientes de forma síncrona mediante una API REST y analizar su contenido utilizando modelos de IA locales, todo desde una interfaz web moderna y segura.

---

## Créditos del proyecto

Este proyecto fue desarrollado como parte de una actividad académica.

- **Alumno 1 — Product Owner / Idea Original:** Pablo Emmanuel Caballero Sagredo (SinPECS) - sinpecs@gmail.com
- **Alumno 2 — Desarrollo:** Francisco Eduardo Pérez Carranza - bpasfepcmexico001@gmail.com
- **Alumno 3 — Calidad y Documentación:** Jonathan André Rojas Baron - jonyrojas88jarb@gmail.com

---

## Descripción general

NinjaSpam funciona como un cliente web de correo electrónico con capacidades de análisis antispam de última generación. Su objetivo es demostrar cómo una aplicación web puede conectarse a un buzón mediante IMAP, recuperar correos y procesar su contenido para apoyar la revisión de mensajes potencialmente sospechosos.

## Fases del Proyecto (Entregas Académicas)

El desarrollo de este sistema está estructurado en tres entregas principales que marcan la evolución del proyecto:

### Entrega 1: Fundamentos y Análisis Estático (Estado Actual)
Desarrollo de un cliente de correo funcional y una interfaz web con temática moderna. Esta fase incluye la conexión IMAP, lectura de la bandeja de entrada, autenticación básica e integración de dos motores de análisis independientes:
- **Motor Técnico:** Revisión matemática de metadatos y cabeceras de seguridad (SPF, DKIM, DMARC, SpamAssassin, Message-ID).
- **Motor Semántico Base:** Conexión con un LLM local (Ollama) mediante prompts estructurados para otorgar una calificación probabilística inicial de spam.

### Entrega 2: NLP y Aprendizaje Automático
Los botones de **Mark as SPAM** y **Mark as HAM** integrarán Procesamiento del Lenguaje Natural (NLP) y Aprendizaje Automático. Python se utilizará para extraer, limpiar y analizar los elementos principales del correo electrónico, como asunto, cuerpo, remitente, enlaces, encabezados y señales técnicas. El Procesamiento del Lenguaje Natural permitirá comprender el contexto, la intención, la estructura semántica y los patrones lingüísticos del mensaje, superando las limitaciones de reglas estáticas y expresiones regulares. El Aprendizaje Automático se aplicará en la creación de un modelo de clasificación de correos capaz de identificar mensajes como SPAM o HAM, evolucionando mediante la retroalimentación continua del usuario y del administrador. Cada confirmación manual, realizada mediante acciones como “Mark as SPAM” o “Mark as HAM”, se registrará como dato supervisado para fortalecer el entrenamiento del modelo y mejorar progresivamente la precisión del análisis antispam.

### Entrega 3: Versión Beta
Se contempla entregar un sistema "funcional" con un depurador integrado (debug básico) al que llamaremos versión "Beta". Esta entrega cerrará el ciclo del aprendizaje supervisado y consolidará la aplicación para su evaluación final.

---

## Objetivo académico

El objetivo principal de este proyecto es aplicar conocimientos de desarrollo de software, integración de servicios, análisis de información y documentación técnica en un caso práctico relacionado con seguridad, correo electrónico e inteligencia artificial.

Este proyecto no pretende sustituir soluciones profesionales de filtrado antispam, sino servir como base funcional y conceptual para fines de aprendizaje, demostración y mejora continua.

---

## Tecnologías utilizadas

El proyecto utiliza principalmente:

- Python 3.10+
- Flask
- IMAPClient
- Requests
- python-dotenv
- Ollama (Inteligencia Artificial Local)
- HTML5 / Vanilla CSS / JavaScript
- Bootstrap 5

---

## Requisitos previos

Antes de ejecutar el proyecto, se recomienda contar con:

- Python 3.10 o superior.
- Acceso a una cuenta de correo con IMAP habilitado.
- Conexión a internet y a un servidor de Ollama (ej. gemma4:e4b).
- Git instalado.
- Entorno virtual de Python configurado.

---

## Instalación local

Clonar el repositorio:

```bash
git clone https://github.com/carranzafp/ninjaspam.git
cd ninjaspam
```

Crear y activar un entorno virtual:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Configurar las Variables de Entorno:

1. Entrar a la carpeta `mailclient`.
2. Crear un archivo `.env` tomando como base la configuración requerida:

```ini
WEB_AUTH_USER=tu_usuario_web
WEB_AUTH_PASS=tu_contraseña_web
IMAP_USER=tu_correo@dominio.com
IMAP_PASS=tu_password_imap
OLLAMA_URL=http://tu-servidor-ollama:11434/api/chat
```

---

## Ejecución del proyecto

Entrar a la carpeta principal de la aplicación:

```bash
cd mailclient
```

Ejecutar la aplicación:

```bash
python app.py
```

Después, abrir en el navegador web e introducir las credenciales web configuradas en el `.env`:

```text
http://localhost:5000
```

---

## NLP en código Python puro

El notebook `workbook/NLP_1022G.ipynb` fue pensado para migrarse a código Python puro bajo la carpeta raíz `backend/`.

### Archivos nuevos

- `backend/nlp_models.py`: utilidades compartidas, limpieza de texto, rutas y carga de modelos.
- `backend/nlp_training.py`: CLI de entrenamiento para generar archivos `.pkl`.
- `backend/nlp_prediction_service.py`: servicio TCP local que responde peticiones JSON.
- `backend/nlp_service_client.py`: cliente Python para consumir el servicio.

### Entrenamiento bajo demanda

Entrenar detector de idioma:

```bash
python -m backend.nlp_training train-language
# o
python backend/nlp_training.py train-language
```

El entrenamiento de idioma ahora:
- usa un mínimo de longitud menos agresivo por defecto (`--min-language-text-length 10`)
- prueba varias combinaciones de `ngram_range`, `min_df` y `C`
- reporta matriz de confusión y métricas por longitud del texto
- guarda solo un artefacto final: `model_files/language_detector.pkl`

Para evitar congelar una laptop o desktop, el grid search ahora usa una configuración
segura por defecto:
- `--jobs 1` (un proceso de entrenamiento a la vez)
- `--cv-folds 3`

Si quieres subir la intensidad manualmente, puedes hacerlo por ejemplo con:

```bash
python backend/nlp_training.py train-language --jobs 2 --cv-folds 3
```

Para una corrida más ligera de prueba:

```bash
python backend/nlp_training.py train-language \
  --max-samples-per-language 50000 \
  --min-language-text-length 10 \
  --jobs 1 \
  --cv-folds 2
```

Entrenar clasificador SPAM/HAM:

```bash
python -m backend.nlp_training train-spam
# o
python backend/nlp_training.py train-spam
```

Entrenar clasificador SPAM/HAM incluyendo correos etiquetados manualmente en `mailclient/maildatabase.json`:

```bash
python -m backend.nlp_training train-spam --include-local-db
# o
python backend/nlp_training.py train-spam --include-local-db
```

Entrenar todo en el orden correcto:

```bash
python -m backend.nlp_training train-all --include-local-db
# o
python backend/nlp_training.py train-all --include-local-db
```

### Regla para usar datos del maildatabase

Solo se incluyen registros del `maildatabase.json` que cumplan estas condiciones:

- estén etiquetados manualmente como `SPAM` o `HAM`
- tengan **subject** y **body** no vacíos
- su idioma detectado sea uno de los soportados por defecto: `english`, `spanish`, `french`

> Nota: `portuguese` se dejó fuera por defecto porque el archivo actual `model_files/pt.txt`
> es desproporcionadamente grande (~1.2 GB). Se puede reactivar después con una versión
> recortada o curada del corpus para mantener el repositorio manejable.

### Servicio de predicción por socket TCP

Iniciar el servicio local:

```bash
python -m backend.nlp_prediction_service --host 127.0.0.1 --port 8765
# o
python backend/nlp_prediction_service.py --host 127.0.0.1 --port 8765
```

Para despliegue remoto se agregó un script de arranque que entra al directorio
del proyecto y levanta el servicio usando directamente el Python del virtualenv
de cPanel:

```bash
./backend/start_nlp_prediction_service.sh
```

El mismo script ahora también funciona como administrador básico del servicio:

```bash
./backend/start_nlp_prediction_service.sh start
./backend/start_nlp_prediction_service.sh status
./backend/start_nlp_prediction_service.sh restart
./backend/start_nlp_prediction_service.sh stop
```

Además se agregó un wrapper dedicado para detenerlo:

```bash
./backend/stop_nlp_prediction_service.sh
```

Internamente el script:
- usa directamente el ejecutable Python del virtualenv remoto
- guarda el PID en `tmp/nlp_prediction_service.pid`
- escribe logs en `logs/nlp_prediction_service.log`
- evita iniciar una segunda copia si ya existe una en ejecución

También acepta parámetros opcionales:

```bash
./backend/start_nlp_prediction_service.sh --host 127.0.0.1 --port 8765 --log-level INFO
```

Y permite sobreescribir valores por variables de entorno:

```bash
NLP_SERVICE_HOST=127.0.0.1 \
NLP_SERVICE_PORT=9000 \
NLP_SERVICE_LOG_LEVEL=DEBUG \
./backend/start_nlp_prediction_service.sh
```

Si cPanel crea el virtualenv en una ruta distinta, puedes sobreescribir el
ejecutable Python sin editar el script:

```bash
NLP_SERVICE_PYTHON=/ruta/real/al/virtualenv/bin/python \
./backend/start_nlp_prediction_service.sh start
```

Para `crontab` en cPanel, lo más simple es usar el comando `start`, porque no
duplicará el proceso si ya está corriendo:

```bash
*/5 * * * * /home/labsinpecs/public_html/unir/ninjaspam/backend/start_nlp_prediction_service.sh start >/dev/null 2>&1
```

Y después de un reentrenamiento de modelos puedes usar:

```bash
/home/labsinpecs/public_html/unir/ninjaspam/backend/start_nlp_prediction_service.sh restart
```

### Script para reentrenamiento SPAM con cron

Se agregó un script dedicado para reentrenar **solo** el clasificador SPAM/HAM,
usando también los correos etiquetados manualmente en `mailclient/maildatabase.json`:

```bash
./backend/run_spam_retraining.sh
```

Este script:
- usa directamente el Python del virtualenv de cPanel
- ejecuta `train-spam --include-local-db`
- escribe logs en `logs/nlp_spam_retraining.log`
- usa un lock en `tmp/nlp_spam_retraining.lock` para evitar ejecuciones solapadas
- **no** reinicia el servicio de predicción

Ejemplo de cron cada 24 horas:

```bash
0 2 * * * /home/labsinpecs/public_html/unir/ninjaspam/backend/run_spam_retraining.sh >/dev/null 2>&1
```

Si el Python del virtualenv cambia de ruta, puedes sobreescribirlo así:

```bash
NLP_SERVICE_PYTHON=/ruta/real/al/virtualenv/bin/python \
./backend/run_spam_retraining.sh
```

Protocolo: una línea JSON por conexión.

Ejemplo de request:

```json
{"action":"predict_email","subject":"Win a free prize","message":"Click here now"}
```

Ejemplo de request de salud:

```json
{"action":"health"}
```

### Cliente shell para probar el servicio

Se agregó un cliente de prueba en:

```bash
./backend/test_prediction_service.sh
```

Ejemplo de uso:

```bash
./backend/test_prediction_service.sh \
  --subject "Win a free prize" \
  --body "Click here now to claim your reward" \
  --host 127.0.0.1 \
  --port 8765
```

Esto envía una petición `predict_email` al servicio TCP y muestra la respuesta JSON formateada.

### Operación con crontab

Si el reentrenamiento corre cada 24 horas vía `crontab`, la recomendación es:

1. reentrenar modelos
2. sobrescribir los `.pkl` en `model_files/`
3. reiniciar el servicio `backend.nlp_prediction_service`

Ese enfoque es más simple y seguro que recargar modelos en caliente en esta primera versión.

---

## Despliegue en servidor cPanel

Para ejecutar el proyecto en un servidor cPanel con soporte para aplicaciones Python, se recomienda crear una aplicación Python (Passenger) desde el panel de control.

Configuración sugerida:

```text
Python version: 3.10 o superior
Application root: ruta/de/la/aplicacion
Application URL: dominio.com/ruta/del/proyecto
Application startup file: passenger_wsgi.py
Application entry point: application
```

Asegúrate de crear tu archivo `.env` en el servidor y de instalar las dependencias dentro del entorno virtual provisto por cPanel antes de iniciar la aplicación.

---

## Dependencias recomendadas

El archivo `requirements.txt` debe incluir, al menos:

```text
Flask
IMAPClient
requests
python-dotenv
```

---

## Seguridad y manejo de credenciales

Este proyecto maneja datos sensibles como contraseñas IMAP y credenciales de acceso web.

Por seguridad:

- **Se ha implementado `python-dotenv`** para que ninguna credencial quede fija en el código.
- El archivo `.env` **JAMÁS** debe subirse al repositorio (está excluido vía `.gitignore`).
- Usa siempre cuentas de prueba o de desarrollo.
- Evita exponer archivos de configuración privados en entornos públicos.
- No utilizar este proyecto en producción sin una revisión completa de seguridad (ej. implementación de HTTPS y certificados válidos).

---

## Contribución

Los colaboradores del proyecto pueden proponer mejoras mediante ramas de trabajo y pull requests.

Flujo recomendado:

```bash
git checkout main
git pull origin main
git checkout -b nombre-de-la-mejora
```

Después de realizar cambios:

```bash
git add .
git commit -m "Descripción clara del cambio"
git push origin nombre-de-la-mejora
```

Finalmente, crear un Pull Request hacia la rama `main`.

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT.

Consulta el archivo `LICENSE` incluido en este repositorio para conocer los términos completos de uso, copia, modificación y distribución del software.

---

## Disclaimer

NinjaSpam es un proyecto académico y experimental. No debe considerarse una solución profesional, definitiva o certificada de ciberseguridad, filtrado antispam, protección de correo electrónico o análisis forense.

El uso de este software es responsabilidad de quien lo instala, ejecuta o modifica. Los autores y colaboradores no garantizan que el sistema detecte correctamente todos los mensajes de spam, phishing, malware, fraude, suplantación de identidad o cualquier otro riesgo asociado al correo electrónico.

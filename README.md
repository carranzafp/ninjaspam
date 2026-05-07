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

El proyecto contempla:

- Conexión a buzones de correo mediante IMAP.
- Interfaz web moderna con diseño "Glassmorphism" (tema de playa).
- Autenticación básica de seguridad para proteger el acceso a la herramienta.
- Carga y visualización de mensajes recientes de la bandeja de entrada.
- Procesamiento de correos para análisis de cabeceras de seguridad (SPF, DKIM, etc.).
- Integración con servicios locales de IA (Ollama) para evaluación y razonamiento probabilístico de spam.
- Comunicación robusta Cliente-Servidor mediante API REST (Fetch).

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

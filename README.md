# Simple Multimedia Download Manager (SMDM)

Un gestor ejecutable, ligero y portable para la descarga de video y audio optimizado para Windows. Diseñado para ofrecer la máxima velocidad de transferencia incluso en redes corporativas o entornos con restricciones de ancho de banda.

---

## ✨ Características Principales

* **Formatos de Descarga Directos:**
  * **Video MP4 (1080p):** Descarga nativa en alta definición con códec de video H.264 y audio AAC.
  * **Video MP4 (720p):** Opción balanceada para descargas rápidas conservando excelente calidad visual.
  * **Audio MP3 (192kbps):** Extracción directa y conversión limpia ideal para dispositivos locales y reproductores multimedia.
* **Optimización Anti-Throttling (Redes de Trabajo):** Incorpora una configuración avanzada de buffers y bloques de transferencia masivos (`--http-chunk-size`). Esto evita de forma automática el "capado" o límite de velocidad clásico (de hasta 50 KB/s) impuesto por firewalls empresariales o antivirus de red.
* **Entorno Portable Autónomo:** Gestiona, descarga y repara en caliente todos sus componentes binarios (`yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` y `deno.exe`) en su propio directorio raíz, sin ensuciar el registro del sistema operativo.
* **Actualizador Inteligente Basado en API:** Conexión directa con las APIs globales de GitHub Releases. Garantiza estabilidad absoluta y descargas veloces, mitigando caídas imprevistas de servidores web externos de terceros.
* **Interfaz Limpia en Consola:** Soporte estético dinámico que actualiza el título de la terminal nativamente tanto en Windows como en entornos Unix.

---

## 🚀 Guía de Uso del Ejecutable (.exe)

Al ser una herramienta diseñada bajo el concepto de **Portabilidad Absoluta**, no requiere ningún asistente de instalación tradicional:

1. Coloca el archivo `SMDM_downloader.exe` en la carpeta de tu preferencia (por ejemplo, en una memoria USB o en tu escritorio).
2. Dale **doble clic** para ejecutarlo.
3. Al iniciar por primera vez, el programa creará automáticamente un archivo local `config.txt` para recordar tu ruta de descargas preferida y un entorno portable limpio.
4. Si el sistema te advierte que faltan componentes binarios, simplemente selecciona la **Opción [5] Actualizar / Reparar Componentes** para que el gestor monte el entorno en segundos de forma automática.

> 💡 **Nota de Red:** No necesitas ejecutar este programa con privilegios de Administrador del sistema. Gracias a su enmascaramiento interno de red, el gestor obtendrá la máxima velocidad disponible en tu conexión por defecto.

---

## 🛠️ Requisitos del Sistema

* **Sistema Operativo:** Windows 10 o superior (compatible con arquitecturas de 64 bits).
* **Conexión a Internet:** Requerida para la descarga de contenidos multimedia y para la sincronización inicial de los binarios portables.
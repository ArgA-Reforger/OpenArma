# Guía de Resolución de Problemas y Diagnóstico / Troubleshooting Guide

[Español](#español) | [English](#english)

---

<a id="español"></a>

## 🇪🇸 Diagnóstico y Resolución de Problemas (Español)

Esta guía documenta hallazgos arquitectónicos, problemas comunes durante la integración entre Arma Reforger Workbench y OpenArma, y los pasos para su resolución.

### 1. Panel de Situación muestra `arma.noSituation` o `arma.situationPanel`

#### Síntomas
- En la interfaz web (`/projects/{id}/chat`), en el panel lateral derecho con "En ejecución" titilando, el acordeón se titula `arma.situationPanel` y su interior muestra `arma.noSituation`.
- En Workbench el logo de OpenArma está en verde y envía latidos cada 30 segundos con éxito (`POST /api/v1/open/cmd/situation 200 OK`).

#### Causas Raíz
1. **Desfase en la consulta del endpoint backend (`admin.py`):**
   - El endpoint `GET /api/v1/open/admin/{project_id}/situation` en `backend/app/open/api/v1/admin.py` consulta la tabla legada `oa_situation_log`.
   - La arquitectura actual migró el almacenamiento en tiempo real a `oa_battle_snapshot` (`BattleSnapshot`), por lo que `oa_situation_log` permanece vacía y la API retorna `data: null`.
2. **Claves de internacionalización (i18n) faltantes:**
   - Las claves `arma.situationPanel` y `arma.noSituation` no están definidas en `frontend/src/lib/i18n/locales/es-ES.json` ni en `en-US.json`. Al no encontrarse, el helper `t()` retorna el nombre literal de la clave.
3. **Worker de Celery inactivo:**
   - La función `command_service.py` despacha la evaluación del LLM mediante Celery (`process_situation_task.delay()`). Si no se ejecuta `uv run fba celery worker -l info`, los reportes quedan encolados en Redis (DB 1, cola `celery`).

#### Solución Pendiente / Próximos Pasos
- **Backend:** Actualizar `get_latest_situation` en `backend/app/open/api/v1/admin.py` para consultar directamente `BattleSnapshot` filtrando por `project_id` y ordenando por `request_id DESC`.
- **Frontend:** Añadir las cadenas a los archivos de locale:
  ```json
  "situationPanel": "Panel de situación",
  "noSituation": "Esperando datos de la batalla..."
  ```
- **Ejecución:** Mantener `uv run fba celery worker -l info` activo durante las sesiones de juego.

---

### 2. El Mod en Workbench no conecta (Logo Rojo)

#### Síntomas
- El logo HUD de OpenArma en la esquina superior izquierda permanece en rojo.
- En la consola de Workbench (`Ctrl + \` / External console) se observan errores HTTP de conexión rechazada.

#### Causas y Verificaciones
1. **URL del backend inaccesible:**
   - Verificar en `Scripts/Game/OA/OA_Config.c` que `ApiUrl` sea `"http://127.0.0.1:28000"`.
   - Confirmar que el backend esté escuchando ejecutando en PowerShell:
     ```powershell
     Test-NetConnection -ComputerName 127.0.0.1 -Port 28000
     ```
2. **API Key desactualizada:**
   - El `ApiKey` en `OA_Config.c` debe coincidir exactamente con el campo `api_key` de la tabla `oa_project` correspondiente al proyecto activo.

---

### 3. Tareas acumuladas en Redis (Celery Queue)

Si el servidor backend estuvo recibiendo telemetría mientras el worker de Celery estaba apagado, pueden acumularse tareas viejas en Redis. Para verificar y limpiar si es necesario:

```bash
uv run python -c "
import redis
r = redis.Redis(host='127.0.0.1', port=26379, db=1, password='openarma123')
print('Tareas pendientes en Celery:', r.llen('celery'))
# Para purgar cola acumulada:
# r.delete('celery')
"
```

---

<a id="english"></a>

## 🇬🇧 Troubleshooting and Diagnostics (English)

This guide documents known architectural findings, common issues during Arma Reforger Workbench integration, and solutions.

### 1. Situation Panel Displays `arma.noSituation` or `arma.situationPanel`

#### Symptoms
- In the web chat panel (`/projects/{id}/chat`), under the right sidebar with "Running" active, the accordion title reads `arma.situationPanel` and displays `arma.noSituation`.
- Workbench OpenArma HUD indicator is green and telemetry is delivered successfully (`POST /api/v1/open/cmd/situation 200 OK`).

#### Root Causes
1. **Backend Endpoint Query Mismatch (`admin.py`):**
   - `GET /api/v1/open/admin/{project_id}/situation` queries the legacy `oa_situation_log` table.
   - The platform migrated frame storage to `oa_battle_snapshot` (`BattleSnapshot`). Because `oa_situation_log` remains empty, the API responds with `data: null`.
2. **Missing i18n Translation Keys:**
   - `arma.situationPanel` and `arma.noSituation` were omitted from `locales/es-ES.json` and `en-US.json`. The translation helper `t()` falls back to displaying the raw key.
3. **Celery Worker Not Running:**
   - `command_service.py` enqueues LLM evaluation tasks into Celery (`process_situation_task.delay()`). Without `uv run fba celery worker -l info`, tasks wait indefinitely in Redis.

#### Action Items
- **Backend:** Update `get_latest_situation` in `backend/app/open/api/v1/admin.py` to query `BattleSnapshot` directly by `project_id` ordered by `request_id DESC`.
- **Frontend:** Add missing keys to locale files (`situationPanel` and `noSituation`).
- **Runtime:** Ensure Celery worker runs alongside the backend.

### 2. Mod HUD in Workbench Stays Red

- Ensure `ApiUrl` in `OA_Config.c` is set to `"http://127.0.0.1:28000"`.
- Ensure `ApiKey` matches the active project's key.
- Verify backend is running and listening on port 28000.

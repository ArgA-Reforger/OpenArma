# Guía de Pruebas e Integración con Arma Reforger Workbench
# Arma Reforger Workbench Integration & Testing Guide

[Español](#español) | [English](#english)

---

<a id="español"></a>

## 🇪🇸 Guía de Integración con Workbench (Español)

Esta guía detalla el procedimiento paso a paso para abrir, configurar y probar el mod principal de OpenArma (**`OpenArma-Mod-Main`**) directamente desde **Arma Reforger Workbench**, conectándolo con el backend local de OpenArma y los modelos de IA.

---

### 1. Arquitectura del Mod en Enfusion

El mod `OpenArma-Mod-Main` actúa como un **cliente Agent MCP (Model Context Protocol)** dentro del motor Enfusion. El mod recopila telemetría táctica y ejecuta waypoints, mientras que el backend de OpenArma y el modelo LLM toman las decisiones de combate.

```
SCR_BaseGameMode (Inyección automática vía OA_GameModeInjector.c)
  └── OA_Main (Controlador Singleton)
        ├── OA_WorldObserver      → Escanea unidades, salud, munición y contactos
        ├── OA_DecisionBridge     → Puente REST HTTP POST a /api/v1/open/command
        ├── OA_CommandExecutor    → Convierte órdenes de IA en waypoints del motor Enfusion
        ├── OA_EventTracker       → Registra contactos, bajas y avistamientos
        └── OA_HudIndicator       → Muestra el estado de conexión en pantalla
```

#### Indicador HUD y Estados
En la esquina de la pantalla del juego verás el indicador de estado de OpenArma:
* **Gris:** Desconectado (el mod está inactivo o esperando login).
* **Amarillo:** Conectado / En espera (autenticado con el backend; esperando que presiones *Start* en la web).
* **Verde parpadeante:** En ejecución (la IA está evaluando activamente y emitiendo órdenes militares).
* **Rojo:** Error de comunicación (la URL de la API es inaccesible o la API Key es inválida).

---

### 2. Ubicación del Mod en tu Sistema

En el entorno de desarrollo, el mod se encuentra en:
```
D:/Bibliotecas/Documentos/My Games/ArmaReforgerWorkbench/addons/OpenArma-Mod-Main/
```
Archivo de proyecto de Workbench:
```
addon.gproj (ID: "ArgAOpenArma", Título: "Arga Open Arma")
```

---

### 3. Configuración de Conexión (`OA_Config.c`)

El archivo de configuración local del mod se encuentra en:
`D:/Bibliotecas/Documentos/My Games/ArmaReforgerWorkbench/addons/OpenArma-Mod-Main/Scripts/Game/OA/OA_Config.c`

Para desarrollo local, debe contener:
```c
class OA_Config
{
    string ApiUrl = "http://127.0.0.1:28000";
    string ApiKey = "oa_arland_989e99a6625a160a8b9b72240efa9211"; // O la API Key de tu proyecto

    float DecisionInterval = 30.0;
    bool EmergencyDetection = true;
    int MaxSquads = 12;
    string GameMode = "game_master";
    string Language = "en";
}
```

> **Nota:** Aunque estos valores queden fijados por defecto, el comando de chat `/oalogin` permite sobrescribir la API Key y la URL dinámicamente en cualquier momento.

---

### 4. Paso a Paso: Ejecución en Workbench

#### Paso 4.1: Cargar el proyecto en Workbench
1. Abre **Arma Reforger Workbench**.
2. En la lista de proyectos cargados, selecciona y abre el proyecto **Arga Open Arma** (`OpenArma-Mod-Main/addon.gproj`).

#### Paso 4.2: Abrir el escenario en World Editor
1. Presiona `F2` o abre la herramienta **World Editor**.
2. Abre un mundo o misión basada en **Arland** (ej. cualquier escenario que incluya un GameMode derivado de `SCR_BaseGameMode`, como `GameMode_GameMaster_Arland.ent`).
3. Ubica las fuerzas en el mapa cerca del objetivo (ej. **Arleville**):
   - Escuadras de la **USSR** (controladas por la IA).
   - Escuadras de **US** (controladas por humanos o como fuerza de incursión).
   *(Si utilizas Game Master, puedes spawnearlas en vivo durante la partida).*

#### Paso 4.3: Iniciar la simulación (Play Mode)
1. Presiona el botón verde de **Play** en la barra superior o `F5` / `Ctrl + F5`.
2. Una vez que spawnees con tu personaje en el mundo:
   - Observa el círculo del HUD de OpenArma en la esquina de la pantalla. Estará en **Gris** (desconectado).

#### Paso 4.4: Conectar mediante el comando de Chat
1. Abre la consola de chat del juego presionando la tecla `Enter` o `Y`.
2. Escribe el comando de inicio de sesión:
   ```
   /oalogin <API_KEY> [URL_DEL_BACKEND]
   ```
   *Ejemplo para el proyecto Arland Demo:*
   ```
   /oalogin oa_arland_989e99a6625a160a8b9b72240efa9211 http://127.0.0.1:28000
   ```
3. Presiona `Enter`.
   - En el log de consola verás: `[OA] Requesting login → server...`
   - El HUD cambiará de Gris a **Amarillo** (*Conectado / En espera*).

#### Paso 4.5: Activar el Comandante de IA en la Web
1. En tu navegador, ingresa al panel de control de OpenArma:
   `http://localhost:23000/projects/2215656377748164608/chat`
2. En la pestaña lateral derecha (**Arma Settings**), bajo el bloque **Control de ejecución (Run Control)**, haz clic en **Start (Play)**.
3. El indicador HUD en el juego pasará a **Verde parpadeante**.
4. ¡El comandante soviético en Ollama comenzará a analizar la posición y a emitir órdenes a las escuadras en Arleville!

---

### 5. Comandos de Chat Disponibles en el Juego

Todos los comandos requieren privilegios de Game Master / Administrador:

| Comando | Sintaxis | Descripción |
| :--- | :--- | :--- |
| **/oalogin** | `/oalogin <api_key> [local\|url]` | Conecta el mod al backend de OpenArma. Si se usa `local`, apunta a `http://localhost:8000`. Si se especifica una URL completa (ej. `http://127.0.0.1:28000`), se conecta a esa dirección. |
| **/oalogout** | `/oalogout` | Desconecta la sesión activa de OpenArma y detiene los latidos. |
| **/oachat** | `/oachat <mensaje>` | Envía un mensaje táctico directo desde el juego al canal de chat de OpenArma. |
| **/oatest** | `/oatest` | Ejecuta un test de diagnóstico de telemetría y comunicación con el backend. |

---

### 6. Solución de Problemas Frecuentes

1. **El HUD permanece en Rojo:**
   - Verifica que el backend esté corriendo (`uv run fba run`) en `http://127.0.0.1:28000`.
   - Revisa que la API Key sea exactamente la asignada a tu proyecto.
   - En Workbench, abre la consola (`F1`) y busca mensajes con el prefijo `[OA]` para ver el código de error HTTP.

2. **El HUD está en Amarillo pero no pasa a Verde:**
   - El mod está conectado pero la IA está en pausa.
   - Ve a la interfaz web de OpenArma en `/projects/[id]/chat` y presiona **Start (Play)** en **Run Control**.

3. **La IA no emite órdenes:**
   - Asegúrate de que Ollama esté corriendo con el modelo cargado (`ollama run hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS`).
   - Verifica en el **Panel de Situación** de la web si el tiempo de respuesta del LLM (`processing_time_ms`) registra actividad.

---

<a id="english"></a>

## 🇬🇧 Workbench Integration & Testing Guide (English)

This guide provides step-by-step instructions to load, configure, and test the **`OpenArma-Mod-Main`** runtime directly inside **Arma Reforger Workbench**, linking it with the local OpenArma backend and AI models.

---

### 1. Enfusion Mod Architecture

The `OpenArma-Mod-Main` mod acts as an **Agent MCP (Model Context Protocol) client** inside the Enfusion engine:

```
SCR_BaseGameMode (Auto-injected via OA_GameModeInjector.c)
  └── OA_Main (Singleton Controller)
        ├── OA_WorldObserver      → Scans units, health, weapons, contacts
        ├── OA_DecisionBridge     → REST HTTP POST bridge to /api/v1/open/command
        ├── OA_CommandExecutor    → Converts AI JSON orders into engine Waypoints
        ├── OA_EventTracker       → Tracks contact, casualty, and sighting events
        └── OA_HudIndicator       → Displays connection status on screen
```

#### HUD Indicator Status
* **Grey:** Disconnected (waiting for login).
* **Yellow:** Connected / Idle (authenticated; waiting for web Start button).
* **Flashing Green:** Running (AI commander actively evaluating and issuing orders).
* **Red:** Communication error (unreachable API URL or invalid API key).

---

### 2. Mod Location

On your development machine:
```
D:/Bibliotecas/Documentos/My Games/ArmaReforgerWorkbench/addons/OpenArma-Mod-Main/
```
Workbench project file:
```
addon.gproj (ID: "ArgAOpenArma", Title: "Arga Open Arma")
```

---

### 3. Connection Configuration (`OA_Config.c`)

Location:
`D:/Bibliotecas/Documentos/My Games/ArmaReforgerWorkbench/addons/OpenArma-Mod-Main/Scripts/Game/OA/OA_Config.c`

Default settings for local development:
```c
class OA_Config
{
    string ApiUrl = "http://127.0.0.1:28000";
    string ApiKey = "oa_arland_989e99a6625a160a8b9b72240efa9211";

    float DecisionInterval = 30.0;
    bool EmergencyDetection = true;
    int MaxSquads = 12;
    string GameMode = "game_master";
    string Language = "en";
}
```

---

### 4. Step-by-Step Workbench Workflow

#### Step 4.1: Load Project in Workbench
1. Open **Arma Reforger Workbench**.
2. Select and open **Arga Open Arma** (`OpenArma-Mod-Main/addon.gproj`).

#### Step 4.2: Open Scenario in World Editor
1. Press `F2` to launch **World Editor**.
2. Open an **Arland** world or mission with a `SCR_BaseGameMode` GameMode.
3. Place units around **Arleville** (USSR defense units and US attacking units).

#### Step 4.3: Start Simulation (Play)
1. Click the green **Play** button or press `F5` / `Ctrl + F5`.
2. Once spawned, observe the OpenArma HUD indicator (initially **Grey**).

#### Step 4.4: Connect via Chat Command
1. Open in-game chat by pressing `Enter` or `Y`.
2. Enter the login command:
   ```
   /oalogin oa_arland_989e99a6625a160a8b9b72240efa9211 http://127.0.0.1:28000
   ```
3. Press `Enter`. The HUD circle will turn **Yellow** (*Connected / Idle*).

#### Step 4.5: Start AI Commander in the Web Dashboard
1. In your browser, open OpenArma at:
   `http://localhost:23000/projects/2215656377748164608/chat`
2. Under the **Arma Settings** panel, in the **Run Control** section, click **Start (Play)**.
3. The in-game HUD turns **Flashing Green**.
4. The local Ollama model begins commanding Soviet forces to defend Arleville.

---

### 5. In-Game Chat Commands

| Command | Usage | Description |
| :--- | :--- | :--- |
| **/oalogin** | `/oalogin <api_key> [local\|url]` | Logs into OpenArma backend with the specified API key and target URL. |
| **/oalogout** | `/oalogout` | Disconnects the active session and halts polling heartbeats. |
| **/oachat** | `/oachat <message>` | Sends a tactical radio message from in-game chat to the OpenArma web thread. |
| **/oatest** | `/oatest` | Runs diagnostic heartbeat and telemetry tests. |

# Manual de Operación y Uso de OpenArma / OpenArma User & Operations Guide

[Español](#español) | [English](#english)

---

<a id="español"></a>

## 🇪🇸 Manual de Operación de OpenArma (Español)

Una vez que OpenArma está desplegado y los servicios están activos (backend en `http://localhost:28000` y frontend en `http://localhost:23000`), esta guía describe el flujo operativo completo para configurar agentes, diseñar misiones y comandar batallas en Arma Reforger.

---

### 1. Acceso Inicial a la Plataforma

1. Abre tu navegador en **`http://localhost:23000`** (o `http://localhost:8080` si usas el stack completo de Docker con Nginx).
2. Inicia sesión con las credenciales por defecto:
   - **Usuario:** `admin`
   - **Contraseña:** `123456`
3. Serás redirigido automáticamente al panel de **Proyectos (`/projects`)**.

---

### 2. Configuración Previa Esencial (Primer Uso)

Antes de lanzar una misión, es necesario configurar tus modelos de IA y comandantes:

#### Paso 2.1: Configurar Proveedores de LLM (`/llm-providers`)
OpenArma utiliza LiteLLM para soportar múltiples proveedores comerciales y locales:
1. En el menú lateral izquierdo, haz clic en **Proveedores de LLM**.
2. Haz clic en **Nuevo Proveedor** (o edita los preconfigurados).
3. Selecciona tu proveedor:
   - **Comerciales:** OpenAI, Anthropic, Google Gemini, DeepSeek, etc.
   - **Locales/Auto-hospedados:** Ollama, vLLM, LocalAI (ingresando la URL base, ej: `http://localhost:11434`).
4. Ingresa tu **API Key** y selecciona los modelos a habilitar (ej. `gpt-4o`, `deepseek-chat`, `claude-3-5-sonnet`).

**Alternativa: Claude con tu suscripción (`Claude (Subscription)`)**
Este proveedor usa el SDK de Claude Agent con tu suscripción de Claude, sin API Key ni URL base:
- **Requisito:** el CLI de Claude Code debe estar instalado y con la sesión iniciada (`claude login`) en la misma máquina y con el mismo usuario que ejecutan el backend y el worker de Celery. No funciona en contenedores sin esa sesión.
- **Modelos:** el botón de descarga de modelos consulta al SDK (no consume mensajes). Los preconfigurados son `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5` y `claude-fable-5-1`.
- **Verificar:** el botón de verificación envía una consulta mínima real y consume un poco de tu cuota.
- **Límites:** `temperature`, `top_p`, penalizaciones y `max_tokens` se ignoran (el log lo avisa una vez). Las herramientas (Tools) del agente no se ejecutan con este proveedor.
- **Variable obligatoria en `backend/.env`:** `CLAUDE_SDK_TIMEOUT_SECONDS` (por ejemplo `300`, sin valor por defecto: el backend no arranca sin ella). Reinicia el backend y el worker tras cambiarla.
- **Pensamiento y esfuerzo por agente:** al elegir este proveedor en un agente, el formulario pide **Pensamiento** (activado o desactivado) y **Esfuerzo** (`low`, `medium`, `high`, `xhigh` o `max`). Ambos son obligatorios y no tienen valor por defecto. Si ya tenías la base de datos creada, añade las columnas una vez: `ALTER TABLE oa_agent ADD COLUMN think BOOLEAN, ADD COLUMN effort VARCHAR(16);`
- **Latencia y cuota:** cada consulta arranca el CLI de Claude (unos 2,5 s de arranque). Un ciclo del comandante consume la ventana de uso de tu suscripción; revisa que los términos de tu plan permitan este uso automatizado.

#### Paso 2.2: Configurar Comandantes de IA (`/agents`)
1. Ve a **Agentes** en el menú lateral.
2. Crea un nuevo agente o selecciona uno existente para personalizarlo:
   - **Rol y Nombre:** Ej. *Comandante de Infantería OTAN*.
   - **Modelo LLM:** Asigna el modelo configurado en el paso anterior.
   - **System Prompt:** Define la doctrina táctica, agresividad, reglas de enfrentamiento (ROE) y priorización de armamento.
   - **Herramientas (Tools):** Activa las herramientas que el comandante puede consultar de forma autónoma (análisis de vegetación, cálculo de rutas A*, línea de visión, RAG táctico).

#### Paso 2.3: Diseñar Topologías Multiagente (`/topologies` - Opcional)
Para simular un Estado Mayor militar completo:
1. Accede a **Topologías**.
2. Utiliza el editor visual DAG basado en React Flow.
3. Conecta múltiples agentes especializados:
   - *Oficial de Reconocimiento* (análisis de terreno y contactos).
   - *Oficial de Fuego de Apoyo* (evaluación de artillería y morteros).
   - *Jefe de Estado Mayor* (toma la decisión final consolidada).

---

### 3. Flujo de Trabajo: Proyecto y Misión de Combate

#### Paso 3.1: Crear o Seleccionar un Proyecto (`/projects`)
1. En **Proyectos**, crea uno nuevo (ej. `Operación Everon`).
2. Entra al proyecto. En el panel lateral verás las secciones del proyecto:
   - **Agentes:** Vincula los agentes autorizados para este proyecto.
   - **Mapas:** Asocia el mapa del terreno (Everon, Arland, etc.) desde la pestaña de configuración del proyecto.
   - **Base de Conocimiento:** Asocia documentos y lecciones tácticas aprendidas.

#### Paso 3.2: Configurar la Misión y la Batalla (`/projects/[id]/chat`)
1. Haz clic en **Chat** dentro del proyecto y crea una nueva conversación/misión.
2. En el panel de configuración lateral derecho (**Arma Settings**):
   - **Objetivo de Misión (Mission Objective):**
     - Selecciona el tipo: `attack` (ataque), `defend` (defensa), `patrol` (patrulla), `search_destroy` (búsqueda y destrucción), `recon` (reconocimiento), o `custom`.
     - Define la descripción y restricciones tácticas (ej. *"Capturar el cruce vial minimizando bajas"*).
     - Configura el Área de Operaciones (AO): puntos focales con coordenadas X, Z y radio.
     - Haz clic en **Generar Briefing de AO** para que el sistema analice el terreno automáticamente.
   - **Bandos y Control (Faction Config):**
     - Configura cada bando (US, USSR, FIA, etc.).
     - Asigna el tipo de control:
       - **IA (`llm`):** Controlado por el comandante de IA.
       - **Humano (`human`):** Jugador real en Arma Reforger.
       - *Soporta IA vs Humano o IA vs IA (con niebla de guerra separada).*
   - **Ajustes de Simulación (Game Settings):**
     - **Intervalo de decisión:** Tiempo en segundos entre evaluaciones tácticas (ej. 30s).
     - **Detección de emergencias:** Si se activa, la IA reacciona de inmediato ante emboscadas o fuego enemigo sin esperar al siguiente ciclo.
     - **Máximo de escuadras:** Límite de escuadras a comandar en simultáneo.

---

### 4. Conexión con Arma Reforger y Ejecución

1. **Obtener la API Key del Proyecto:**
   - En la sección **API Key** del panel del proyecto, copia la clave generada.
2. **Configurar el Mod en Arma Reforger:**
   - En el servidor o cliente de Arma Reforger (con `OpenArma-Mod-Main` activo):
   - Establece la URL de la API: `http://<IP_DEL_HOST>:28000/api/v1/open`
   - Ingresa la API Key del proyecto.
3. **Iniciar la Batalla:**
   - En el panel web de OpenArma, en **Run Control**, presiona el botón **Start (Play)**.
   - El estado pasará a verde pulsante (`Running`).

---

### 5. Monitoreo en Vivo y Post-Batalla

- **Panel de Situación en Vivo (`Situation Panel`):**
  - Muestra el ID de la solicitud actual, tiempos de inferencia del LLM y comandos en cola.
  - Lista de escuadras aliadas y enemigas identificadas, bajas, postura, modo de combate y órdenes vigentes.
- **Replay de Combate (`/projects/[id]/replay`):**
  - Permite revisar frame por frame toda la misión sobre el mapa táctico.
- **Aprendizaje RAG:**
  - Las decisiones y resultados se almacenan en la base de datos vectorial Qdrant para mejorar la toma de decisiones en futuras misiones.

---

<a id="english"></a>

## 🇬🇧 OpenArma Operations & User Guide (English)

Once OpenArma is running (backend at `http://localhost:28000` and frontend at `http://localhost:23000`), this manual explains how to configure agents, set up missions, and command AI forces in Arma Reforger.

---

### 1. Initial Login

1. Open your browser at **`http://localhost:23000`** (or `http://localhost:8080` if using full Docker stack).
2. Sign in with the default credentials:
   - **Username:** `admin`
   - **Password:** `123456`
3. You will be redirected to the **Projects (`/projects`)** overview.

---

### 2. Initial Setup (First Time Use)

#### Step 2.1: Configure LLM Providers (`/llm-providers`)
1. Click **LLM Providers** in the left sidebar navigation.
2. Click **New Provider** (or edit preconfigured providers).
3. Select your provider (OpenAI, Anthropic, Gemini, DeepSeek, or local Ollama / vLLM).
4. Enter your **API Key** and enable target models (e.g. `gpt-4o`, `deepseek-chat`).

**Alternative: Claude on your subscription (`Claude (Subscription)`)**
This provider uses the Claude Agent SDK with your Claude subscription, with no API key or base URL:
- **Requirement:** the Claude Code CLI must be installed and logged in (`claude login`) on the same machine and user that run the backend and the Celery worker. It does not work in containers without that session.
- **Models:** the fetch-models button asks the SDK (it sends no prompt). The presets are `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5` and `claude-fable-5-1`.
- **Verify:** the verify button sends one tiny real query and uses a little of your quota.
- **Limits:** `temperature`, `top_p`, penalties and `max_tokens` are ignored (the log warns once). Agent Tools are not executed with this provider.
- **Required variable in `backend/.env`:** `CLAUDE_SDK_TIMEOUT_SECONDS` (for example `300`, no default: the backend does not start without it). Restart the backend and the worker after changing it.
- **Thinking and effort per agent:** when an agent uses this provider, the form asks for **Thinking** (on or off) and **Effort** (`low`, `medium`, `high`, `xhigh` or `max`). Both are required and have no default. If your database already exists, add the columns once: `ALTER TABLE oa_agent ADD COLUMN think BOOLEAN, ADD COLUMN effort VARCHAR(16);`
- **Latency and quota:** every query starts the Claude CLI (about 2.5 s of startup). A commander cycle consumes your subscription usage window; check that your plan's terms allow this automated use.

#### Step 2.2: Configure AI Commanders (`/agents`)
1. Navigate to **Agents** in the sidebar.
2. Create or customize commander profiles:
   - **Name & Persona:** e.g. *NATO Tactical Commander*.
   - **LLM Model:** Select the model configured in the previous step.
   - **System Prompt:** Define rules of engagement (ROE), tactical doctrine, weapon usage restrictions.
   - **Tools:** Grant access to map analysis, pathfinding, terrain awareness, and RAG retrieval.

#### Step 2.3: Visual Multi-Agent Topologies (`/topologies` - Optional)
1. Navigate to **Topologies** to build DAG-based collaboration workflows.
2. Connect specialized roles (Recon Officer -> Fire Support -> Chief of Staff) for multi-round tactical deliberation.

---

### 3. Project and Combat Mission Workflow

#### Step 3.1: Create or Open a Project (`/projects`)
1. Create a project (e.g. `Operation Everon`).
2. Link the game map (Everon, Arland) and assign available agents and knowledge bases.

#### Step 3.2: Configure the Mission (`/projects/[id]/chat`)
1. Open **Chat** inside the project and start a new mission conversation.
2. In the right-hand **Arma Settings** panel:
   - **Mission Objective:** Set mission type (`attack`, `defend`, `patrol`, `recon`), focal coordinates, and generate AO briefing.
   - **Faction Config:** Assign factions (US, USSR, FIA) and control mode (`llm` or `human`).
   - **Game Settings:** Set decision interval (e.g. 30s), emergency triggers, and max squads.

---

### 4. Connecting Arma Reforger and Executing

1. **Copy Project API Key:** Found under the API Key panel in the project settings.
2. **Configure Arma Reforger Mod:** In Reforger with `OpenArma-Mod-Main`, set the endpoint to `http://<HOST_IP>:28000/api/v1/open` and enter the API key.
3. **Start the Mission:** Click **Start (Play)** under **Run Control** in the OpenArma web dashboard.

---

### 5. Live Monitoring and Replay

- **Live Situation Panel:** Displays real-time unit positions, health, casualties, contacts, and active orders.
- **Combat Replay (`/projects/[id]/replay`):** Review missions step-by-step on the tactical map for post-action debriefing.

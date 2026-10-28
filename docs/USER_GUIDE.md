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

# Guía de Ejecución de OpenArma / OpenArma Run Guide

[Español](#español) | [English](#english)

---

<a id="español"></a>

## 🇪🇸 Guía de Ejecución de OpenArma (Español)

Esta guía detalla todos los requisitos, configuraciones y pasos necesarios para ejecutar OpenArma tanto en **modo desarrollo local** (recomendado para desarrollo y pruebas) como en **modo contenedor completo con Docker** (para despliegues completos de producción o staging).

---

### 1. Requisitos Previos

Antes de comenzar, asegúrate de tener instaladas las siguientes herramientas en tu sistema:

| Herramienta | Versión mínima | Propósito | Enlace |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ (Recomendado 3.10 – 3.12) | Runtime del backend | [python.org](https://www.python.org/) |
| **uv** | Última versión | Gestor de paquetes y entornos virtuales de Python | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **Node.js** | 18+ (Recomendado 20 o 22 LTS) | Runtime del frontend | [nodejs.org](https://nodejs.org/) |
| **pnpm** | 9+ | Gestor de paquetes de Node.js | [pnpm.io](https://pnpm.io/) |
| **Docker & Docker Compose** | v2+ | Servicios auxiliares (PostgreSQL, Redis, Qdrant, MinIO) | [docker.com](https://www.docker.com/) |
| **Git** | Cualquier versión reciente | Control de versiones | [git-scm.com](https://git-scm.com/) |

---

### 2. Arquitectura de Servicios y Puertos

OpenArma consta de frontend, backend y un conjunto de servicios de infraestructura. Para evitar conflictos de puertos con servicios locales existentes durante el desarrollo, `docker-compose.dev.yml` mapea los puertos del host sumando `20000` a los puertos estándar.

#### Mapa de Puertos en Desarrollo Local (`docker-compose.dev.yml`)

| Servicio | Puerto Host | Puerto Interno | Credenciales / Datos por defecto |
| :--- | :--- | :--- | :--- |
| **PostgreSQL 16 (pgvector)** | `25432` | `5432` | BD: `openarma`, Usuario: `postgres`, Pass: `openarma123` |
| **Redis 7** | `26379` | `6379` | Pass: `openarma123` (DB 0: Cache, DB 1: Celery Broker) |
| **Qdrant (Vector DB)** | `26333` | `6333` | Vector DB para embeddings de mapas y RAG |
| **MinIO (API S3)** | `29000` | `9000` | User: `minioadmin`, Pass: `minioadmin`, Bucket: `openarma` |
| **MinIO (Consola Web)** | `29001` | `9001` | Consola de administración de objetos MinIO |
| **RabbitMQ (AMQP - opcional)** | `25672` | `5672` | User: `openarma`, Pass: `openarma123` (perfil `rabbit`) |
| **RabbitMQ (UI - opcional)** | `35672` | `15672` | Panel de gestión web de RabbitMQ |
| **Backend API (fba / Granian)** | `28000` | - | `http://127.0.0.1:28000` (Docs: `/docs`, API: `/api/v1`) |
| **Frontend (Next.js)** | `23000` | - | `http://127.0.0.1:23000` |
| **Celery Flower (opcional)** | `8555` | - | `http://127.0.0.1:8555` (User: `admin`, Pass: `123456`) |

---

### 3. Modo 1: Desarrollo Local (Recomendado)

En este modo, los servicios de infraestructura corren en Docker mientras que el backend de FastAPI y el frontend de Next.js se ejecutan de forma nativa en tu máquina con recarga en caliente (hot reload).

#### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/ArgA-Reforger/OpenArma.git
cd OpenArma
```

#### Paso 2: Iniciar los servicios de soporte en Docker

Ejecuta el compose de desarrollo para levantar PostgreSQL (con extensión pgvector), Redis, Qdrant y MinIO:

```bash
docker compose -f docker-compose.dev.yml up -d
```

> **Nota:** Si deseas utilizar RabbitMQ como broker de Celery en lugar de Redis, añade el perfil `--profile rabbit`:
> ```bash
> docker compose -f docker-compose.dev.yml --profile rabbit up -d
> ```

Verifica que todos los contenedores estén en estado `Up`:

```bash
docker compose -f docker-compose.dev.yml ps
```

#### Paso 3: Configurar el Backend

1. **Crear el archivo `.env`:**
   Copia el archivo de plantilla a `backend/.env`:
   - En Linux/macOS:
     ```bash
     cp backend/.env.example backend/.env
     ```
   - En Windows (PowerShell):
     ```powershell
     Copy-Item backend/.env.example backend/.env
     ```

2. **Editar `backend/.env`:**
   Asegúrate de que los puertos y credenciales apunten a los servicios de `docker-compose.dev.yml`:
   ```env
   # Entorno
   ENVIRONMENT='dev'

   # Base de datos (PostgreSQL en puerto mapeado 25432)
   DATABASE_TYPE='postgresql'
   DATABASE_HOST='127.0.0.1'
   DATABASE_PORT=25432
   DATABASE_USER='postgres'
   DATABASE_PASSWORD='openarma123'

   # Redis (puerto mapeado 26379)
   REDIS_HOST='127.0.0.1'
   REDIS_PORT=26379
   REDIS_PASSWORD='openarma123'
   REDIS_DATABASE=0

   # Secreto para JWT (genera una cadena aleatoria segura)
   TOKEN_SECRET_KEY='1VkVF75nsNABBjK_7-qz7GtzNy3AMvktc9TCPwKczCk'

   # Qdrant (puerto mapeado 26333)
   QDRANT_HOST='127.0.0.1'
   QDRANT_PORT=26333
   QDRANT_API_KEY=''

   # MinIO (puerto mapeado 29000)
   MINIO_ENDPOINT='127.0.0.1:29000'
   MINIO_ACCESS_KEY='minioadmin'
   MINIO_SECRET_KEY='minioadmin'
   MINIO_BUCKET='openarma'
   MINIO_SECURE=false

   # Celery
   CELERY_BROKER_REDIS_DATABASE=1
   CELERY_RABBITMQ_HOST='127.0.0.1'
   CELERY_RABBITMQ_PORT=25672
   CELERY_RABBITMQ_USERNAME='openarma'
   CELERY_RABBITMQ_PASSWORD='openarma123'
   ```

#### Paso 4: Instalar dependencias del Backend

Utiliza `uv` para sincronizar las dependencias e instalar el entorno virtual automáticamente:

```bash
uv sync
```

#### Paso 5: Inicializar la Base de Datos

Inicializa las tablas, extensiones (pgvector) y carga los datos de prueba iniciales:

```bash
uv run fba init
```

*Cuando el asistente pregunte si deseas continuar con la reconstrucción/creación de tablas, responde `y`.*

> **Alternativa automatizada:**
> ```bash
> uv run fba init --auto
> ```

#### Paso 6: Iniciar el servidor Backend

Ejecuta el servidor FastAPI con Granian:

```bash
uv run fba run
```

Por defecto escuchará en `http://127.0.0.1:28000`.

- **Swagger UI:** [http://127.0.0.1:28000/docs](http://127.0.0.1:28000/docs)
- **Redoc UI:** [http://127.0.0.1:28000/redoc](http://127.0.0.1:28000/redoc)
- **API Base:** [http://127.0.0.1:28000/api/v1](http://127.0.0.1:28000/api/v1)

#### Paso 7: Iniciar Celery Worker (Requerido para el Comandante IA)

Para que el modelo de lenguaje procese los reportes tácticos de situación enviados por Arma Reforger y emita órdenes en tiempo real, es **obligatorio** que el worker de Celery esté en ejecución en una terminal independiente:

- **Worker (Requerido para órdenes tácticas):**
  ```bash
  uv run fba celery worker -l info
  ```
- **Beat (planificador periódico):**
  ```bash
  uv run fba celery beat -l info
  ```
- **Flower (monitor web opcional):**
  ```bash
  uv run fba celery flower --port=8555
  ```

#### Paso 8: Configurar y levantar el Frontend

1. Dirígete al directorio `frontend`:
   ```bash
   cd frontend
   ```

2. Instala las dependencias con `pnpm`:
   ```bash
   pnpm install
   ```

3. *(Opcional)* Si modificaste el puerto del backend, crea `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_BASE=http://localhost:28000/api/v1
   ```

4. Inicia el servidor de desarrollo de Next.js:
   ```bash
   pnpm dev
   ```

5. Abre en tu navegador:
   **[http://localhost:23000](http://localhost:23000)**

---

### 4. Credenciales de Acceso por Defecto

Los scripts de inicialización cargan los siguientes usuarios de prueba:

| Usuario | Contraseña por defecto | Rol | Propósito |
| :--- | :--- | :--- | :--- |
| **admin** | `123456` | Superadministrador | Acceso total a configuración, plugins, LLMs y analítica |
| **test** | `123456` | Usuario estándar | Pruebas de permisos y uso regular |

---

### 5. Modo 2: Despliegue Completo con Docker Compose

Si prefieres levantar la totalidad del stack (frontend compilado, backend en contenedor, Nginx como proxy reverso, base de datos, colas y observabilidad con Grafana):

1. **Configurar el entorno del servidor:**
   ```bash
   cp deploy/backend/docker-compose/.env.server.example deploy/backend/docker-compose/.env.server
   ```
   *(Ajusta contraseñas y claves según corresponda en `deploy/backend/docker-compose/.env.server`)*

2. **Construir las imágenes de Docker:**
   ```bash
   docker compose build
   ```

3. **Iniciar los servicios:**
   ```bash
   docker compose up -d
   ```

4. **Acceso a los servicios:**
   - **Frontend & API (Nginx):** `http://localhost:8080`
   - **Backend directo:** `http://localhost:8001`
   - **Grafana (Métricas & Logs):** `http://localhost:13000`
   - **Celery Flower:** `http://localhost:8555`
   - **RabbitMQ UI:** `http://localhost:15672`

---

### 6. Integración con Arma Reforger

OpenArma se conecta con Arma Reforger a través de su API Abierta (`/api/v1/open/`):

1. **Endpoints de comunicación:**
   - Órdenes militares y decisiones: `/api/v1/open/command`
   - Configuración de simulación: `/api/v1/open/admin/arma_config`
   - Replay de combate: `/api/v1/open/admin/replay`

2. **Mods necesarios para Arma Reforger:**
   - **[OpenArma Mod Main](https://github.com/ArgA-Reforger/OpenArma-Mod-Main):** Mod principal con el runtime del comandante de IA dentro del juego.
   - **[OpenArma Mod MapExporter](https://github.com/ArgA-Reforger/OpenArma-Mod-MapExporter):** Herramienta para exportar datos topográficos y de vegetación desde Arma Reforger Workbench.
   - **[OpenArma Mod MapScanner](https://github.com/ArgA-Reforger/OpenArma-Mod-MapScanner):** Escáner in-game del terreno.

3. **Configuración de conexión:**
   En la configuración del mod dentro del juego o del servidor dedicado de Reforger, ingresa la URL accesible del backend:
   ```
   http://<IP_DEL_SERVIDOR>:28000/api/v1/open
   ```

---

### 7. Comandos Frecuentes y Solución de Problemas

#### Detener los servicios de desarrollo
```bash
docker compose -f docker-compose.dev.yml down
```

#### Reiniciar desde cero la base de datos y cachés (eliminar volúmenes locales)
```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
uv run fba init
```

#### Gestión de Migraciones de Base de Datos (Alembic)
- Ver versión actual de migraciones:
  ```bash
  uv run fba alembic current
  ```
- Aplicar migraciones pendientes:
  ```bash
  uv run fba alembic upgrade head
  ```
- Crear una nueva migración automática:
  ```bash
  uv run fba alembic revision -m "descripcion_del_cambio"
  ```

#### Problemas Comunes
- **Error de conexión a la base de datos (puerto 5432 vs 25432):**
  Recuerda que en desarrollo local con `docker-compose.dev.yml`, PostgreSQL expone el puerto `25432`. Verifica que `DATABASE_PORT=25432` en `backend/.env`.
- **Error con pgvector:**
  La imagen utilizada en `docker-compose.dev.yml` es `pgvector/pgvector:pg16`. Si usas una instalación nativa de PostgreSQL sin la extensión `vector`, `fba init` fallará.
- **Error CORS al conectar Frontend con Backend:**
  Verifica que `http://localhost:23000` y `http://127.0.0.1:23000` estén presentes en `CORS_ALLOWED_ORIGINS` en `backend/core/conf.py`.

---

<a id="english"></a>

## 🇬🇧 OpenArma Run Guide (English)

This guide covers all prerequisites, configuration requirements, and step-by-step instructions to run OpenArma in **local development mode** (recommended for testing and feature development) or **full containerized Docker mode** (production and staging).

---

### 1. Prerequisites

Ensure you have the following tools installed:

| Tool | Minimum Version | Purpose | Link |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ (3.10 – 3.12 recommended) | Backend runtime | [python.org](https://www.python.org/) |
| **uv** | Latest | Fast Python package and virtual environment manager | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **Node.js** | 18+ (20 or 22 LTS recommended) | Frontend runtime | [nodejs.org](https://nodejs.org/) |
| **pnpm** | 9+ | Fast Node.js package manager | [pnpm.io](https://pnpm.io/) |
| **Docker & Docker Compose** | v2+ | Infrastructure services (PostgreSQL, Redis, Qdrant, MinIO) | [docker.com](https://www.docker.com/) |
| **Git** | Recent version | Version control | [git-scm.com](https://git-scm.com/) |

---

### 2. Service Architecture and Port Mapping

To prevent port conflicts with services already running on developer machines, `docker-compose.dev.yml` maps host ports by adding `20000` to standard service ports.

#### Local Development Port Map (`docker-compose.dev.yml`)

| Service | Host Port | Internal Port | Default Credentials / Notes |
| :--- | :--- | :--- | :--- |
| **PostgreSQL 16 (pgvector)** | `25432` | `5432` | DB: `openarma`, User: `postgres`, Pass: `openarma123` |
| **Redis 7** | `26379` | `6379` | Pass: `openarma123` (DB 0: Cache, DB 1: Celery Broker) |
| **Qdrant (Vector DB)** | `26333` | `6333` | Vector DB for map embeddings and RAG |
| **MinIO (S3 API)** | `29000` | `9000` | User: `minioadmin`, Pass: `minioadmin`, Bucket: `openarma` |
| **MinIO (Web Console)** | `29001` | `9001` | Web management interface |
| **RabbitMQ (AMQP - optional)** | `25672` | `5672` | User: `openarma`, Pass: `openarma123` (`rabbit` profile) |
| **RabbitMQ (UI - optional)** | `35672` | `15672` | RabbitMQ Web Management |
| **Backend API (fba / Granian)** | `28000` | - | `http://127.0.0.1:28000` (Docs: `/docs`, API: `/api/v1`) |
| **Frontend (Next.js)** | `23000` | - | `http://127.0.0.1:23000` |
| **Celery Flower (optional)** | `8555` | - | `http://127.0.0.1:8555` (User: `admin`, Pass: `123456`) |

---

### 3. Mode 1: Local Development (Recommended)

In this mode, supporting data stores run inside Docker containers, while the FastAPI backend and Next.js frontend run directly on the host with hot reload.

#### Step 1: Clone the repository

```bash
git clone https://github.com/ArgA-Reforger/OpenArma.git
cd OpenArma
```

#### Step 2: Start Support Services in Docker

Launch PostgreSQL (pgvector enabled), Redis, Qdrant, and MinIO:

```bash
docker compose -f docker-compose.dev.yml up -d
```

> **Note:** To run RabbitMQ as Celery broker instead of Redis, include `--profile rabbit`:
> ```bash
> docker compose -f docker-compose.dev.yml --profile rabbit up -d
> ```

Check container status:

```bash
docker compose -f docker-compose.dev.yml ps
```

#### Step 3: Configure the Backend

1. **Create the `.env` file:**
   - Linux/macOS:
     ```bash
     cp backend/.env.example backend/.env
     ```
   - Windows (PowerShell):
     ```powershell
     Copy-Item backend/.env.example backend/.env
     ```

2. **Update `backend/.env`:**
   Configure connection variables to match `docker-compose.dev.yml`:
   ```env
   ENVIRONMENT='dev'

   DATABASE_TYPE='postgresql'
   DATABASE_HOST='127.0.0.1'
   DATABASE_PORT=25432
   DATABASE_USER='postgres'
   DATABASE_PASSWORD='openarma123'

   REDIS_HOST='127.0.0.1'
   REDIS_PORT=26379
   REDIS_PASSWORD='openarma123'
   REDIS_DATABASE=0

   TOKEN_SECRET_KEY='generate_a_random_token_secret_here'

   QDRANT_HOST='127.0.0.1'
   QDRANT_PORT=26333
   QDRANT_API_KEY=''

   MINIO_ENDPOINT='127.0.0.1:29000'
   MINIO_ACCESS_KEY='minioadmin'
   MINIO_SECRET_KEY='minioadmin'
   MINIO_BUCKET='openarma'
   MINIO_SECURE=false

   CELERY_BROKER_REDIS_DATABASE=1
   CELERY_RABBITMQ_HOST='127.0.0.1'
   CELERY_RABBITMQ_PORT=25672
   CELERY_RABBITMQ_USERNAME='openarma'
   CELERY_RABBITMQ_PASSWORD='openarma123'
   ```

#### Step 4: Install Backend Dependencies

Sync packages and create the virtual environment using `uv`:

```bash
uv sync
```

#### Step 5: Initialize the Database

Run schema creation, pgvector activation, and initial seed scripts:

```bash
uv run fba init
```

*Press `y` when prompted to confirm rebuilding/creating tables.*

> **Automated mode:**
> ```bash
> uv run fba init --auto
> ```

#### Step 6: Start the Backend Server

Start the API service via Granian:

```bash
uv run fba run
```

The API will listen at `http://127.0.0.1:28000`.

- **Swagger Documentation:** [http://127.0.0.1:28000/docs](http://127.0.0.1:28000/docs)
- **Redoc Documentation:** [http://127.0.0.1:28000/redoc](http://127.0.0.1:28000/redoc)
- **API Base URL:** [http://127.0.0.1:28000/api/v1](http://127.0.0.1:28000/api/v1)

#### Step 7: Start Celery Worker (Required for AI Commander)

In order for the LLM to process tactical battlefield situation reports from Arma Reforger and issue real-time orders, the Celery worker **must** be running in a separate terminal:

- **Worker (Required for tactical orders):**
  ```bash
  uv run fba celery worker -l info
  ```
- **Beat (periodic scheduler):**
  ```bash
  uv run fba celery beat -l info
  ```
- **Flower (optional monitoring UI):**
  ```bash
  uv run fba celery flower --port=8555
  ```

#### Step 8: Configure and Start Frontend

1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```

2. Install dependencies with `pnpm`:
   ```bash
   pnpm install
   ```

3. *(Optional)* If using a non-standard backend port, set `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_BASE=http://localhost:28000/api/v1
   ```

4. Start the development server:
   ```bash
   pnpm dev
   ```

5. Visit the platform in your browser:
   **[http://localhost:23000](http://localhost:23000)**

---

### 4. Default Seed Credentials

Initial seed scripts create the following default accounts:

| Username | Default Password | Role | Notes |
| :--- | :--- | :--- | :--- |
| **admin** | `123456` | Superuser | Full system administration, LLM configurations, analytics |
| **test** | `123456` | Standard User | Permission and general feature verification |

---

### 5. Mode 2: Full Docker Stack Deployment

To run all services inside Docker containers (production/staging setup):

1. **Configure server environment:**
   ```bash
   cp deploy/backend/docker-compose/.env.server.example deploy/backend/docker-compose/.env.server
   ```
2. **Build container images:**
   ```bash
   docker compose build
   ```
3. **Start all services:**
   ```bash
   docker compose up -d
   ```
4. **Service Access:**
   - **Frontend & API (Nginx):** `http://localhost:8080`
   - **Backend Direct:** `http://localhost:8001`
   - **Grafana Dashboards:** `http://localhost:13000`
   - **Celery Flower:** `http://localhost:8555`
   - **RabbitMQ Management:** `http://localhost:15672`

---

### 6. Arma Reforger Integration

OpenArma communicates with Arma Reforger via Open API endpoints (`/api/v1/open/`):

- **Open API Endpoints:**
  - AI Command & Control: `/api/v1/open/command`
  - Arma Game Configuration: `/api/v1/open/admin/arma_config`
  - Replay Capture: `/api/v1/open/admin/replay`

- **Arma Reforger Mods:**
  - **[OpenArma Mod Main](https://github.com/ArgA-Reforger/OpenArma-Mod-Main)**: Core AI commander runtime.
  - **[OpenArma Mod MapExporter](https://github.com/ArgA-Reforger/OpenArma-Mod-MapExporter)**: Terrain & vegetation export from Reforger Workbench.
  - **[OpenArma Mod MapScanner](https://github.com/ArgA-Reforger/OpenArma-Mod-MapScanner)**: In-game map scanning.

Point the Arma Reforger mod configuration to:
```
http://<SERVER_IP>:28000/api/v1/open
```

---

### 7. Common Commands & Troubleshooting

#### Stop Local Dev Services
```bash
docker compose -f docker-compose.dev.yml down
```

#### Wipe and Reset Dev Environment
```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
uv run fba init
```

#### Database Migrations (Alembic)
- Check current migration revision:
  ```bash
  uv run fba alembic current
  ```
- Upgrade database to head:
  ```bash
  uv run fba alembic upgrade head
  ```
- Generate a new migration revision:
  ```bash
  uv run fba alembic revision -m "migration_summary"
  ```

#### Common Pitfalls
- **Port Mismatch (5432 vs 25432):** In local development, `docker-compose.dev.yml` maps PostgreSQL to port `25432`. Ensure `DATABASE_PORT=25432` in `backend/.env`.
- **pgvector Extension Missing:** The database requires the PostgreSQL `vector` extension. Using standard PostgreSQL without `pgvector` will fail during table creation.
- **CORS Issues:** Make sure `http://localhost:23000` is listed in `CORS_ALLOWED_ORIGINS` (`backend/core/conf.py`).

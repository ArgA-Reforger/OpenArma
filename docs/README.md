# Documentación de OpenArma / OpenArma Documentation

[Español](#español) | [English](#english)

---

<a id="español"></a>

## 🇪🇸 Índice de Documentación (Español)

Bienvenido a la documentación oficial del entorno OpenArma mantenido por **ArgA-Reforger**. Aquí encontrarás todas las guías paso a paso para desplegar, operar, probar y conectar la plataforma con Arma Reforger.

| Documento | Descripción |
| :--- | :--- |
| **[`RUN.md`](RUN.md)** | **Guía de Despliegue y Ejecución:** Prerrequisitos (`uv`, `pnpm`, `docker`), puertos offset (+20000), inicialización de base de datos (`fba init`), arranque de backend, frontend y stack completo de producción. |
| **[`USER_GUIDE.md`](USER_GUIDE.md)** | **Manual de Operación de la Plataforma:** Flujo paso a paso desde el primer login, configuración de proveedores LLM, agentes, diseño de topologías DAG, proyectos y misiones tácticas. |
| **[`WORKBENCH_GUIDE.md`](WORKBENCH_GUIDE.md)** | **Guía de Integración con Arma Reforger Workbench:** Procedimiento detallado para abrir el mod `OpenArma-Mod-Main`, lanzar misiones en World Editor, comandos de chat in-game (`/oalogin`, `/oachat`), estados del HUD y solución de problemas. |
| **[`SCENARIO_ARLAND_DEMO.md`](SCENARIO_ARLAND_DEMO.md)** | **Ficha Técnica del Escenario Arland Demo:** Configuración completa del escenario de prueba (Defensa de Arleville con Ollama local `gemma-4-26B`, bandos US vs USSR, API Key y parámetros tácticos). |
| **[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)** | **Diagnóstico y Resolución de Problemas:** Causas y soluciones para `arma.noSituation`, configuración de Celery Worker, estado del HUD en Workbench y gestión de colas en Redis. |

---

<a id="english"></a>

## 🇬🇧 Documentation Index (English)

Welcome to the official OpenArma documentation maintained by **ArgA-Reforger**. Below you will find all step-by-step guides to deploy, operate, test, and integrate the platform with Arma Reforger.

| Document | Description |
| :--- | :--- |
| **[`RUN.md`](RUN.md)** | **Deployment & Run Guide:** Prerequisites (`uv`, `pnpm`, `docker`), offset port map (+20000), database initialization (`fba init`), backend/frontend startup, and full Docker Compose deployment. |
| **[`USER_GUIDE.md`](USER_GUIDE.md)** | **Platform User Guide:** End-to-end operation from initial login, LLM provider setup, agent customization, DAG topologies, projects, and combat missions. |
| **[`WORKBENCH_GUIDE.md`](WORKBENCH_GUIDE.md)** | **Arma Reforger Workbench Guide:** Step-by-step workflow to run `OpenArma-Mod-Main` in Workbench, launch World Editor simulations, in-game chat commands (`/oalogin`, `/oachat`), HUD states, and troubleshooting. |
| **[`SCENARIO_ARLAND_DEMO.md`](SCENARIO_ARLAND_DEMO.md)** | **Arland Demo Scenario Specification:** Complete technical parameters of the demo scenario (Arleville defense using local Ollama `gemma-4-26B`, US vs USSR factions, API key, and tactical settings). |
| **[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)** | **Troubleshooting and Diagnostics:** Root causes and fixes for `arma.noSituation`, Celery worker requirements, Workbench HUD status, and Redis task queues. |

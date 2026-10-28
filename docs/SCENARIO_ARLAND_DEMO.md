# Escenario de Demostración: Arland Demo (Defensa de Arleville)
# Demo Scenario: Arland Demo (Defense of Arleville)

[Español](#español) | [English](#english)

---

<a id="español"></a>

## 🇪🇸 Ficha Técnica del Escenario: Arland Demo (Español)

Este documento registra la configuración técnica completa del escenario creado para pruebas entre OpenArma, Ollama y Arma Reforger en la isla de Arland.

---

### 1. Parámetros Generales del Proyecto

* **Nombre del Proyecto:** `Arland Demo`
* **ID en Base de Datos:** `2215656377748164608`
* **Descripción:** *Prueba de OpenArma en Arland*
* **Estado:** `active`
* **API Key de Conexión:**
  ```
  oa_arland_989e99a6625a160a8b9b72240efa9211
  ```
* **URL de Acceso Web:**
  [http://localhost:23000/projects/2215656377748164608/chat](http://localhost:23000/projects/2215656377748164608/chat)

---

### 2. Motor de Inteligencia Artificial (LLM)

* **Proveedor:** Ollama Local (`http://localhost:11434`)
* **ID de Proveedor:** `2215645759489966080`
* **Modelo Asignado:**
  ```
  hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS
  ```
* **Comandante de IA:** `Comandante USSR (Arleville)` (ID: `2215656377727193088`)
* **System Prompt:**
  ```text
  Sos el comandante táctico de las fuerzas del Ejército Soviético (USSR) en la isla de Arland.
  Tu misión prioritaria e innegociable es DEFENDER el pueblo de Arleville frente a incursiones de fuerzas hostiles de los Estados Unidos (US).

  Doctrina y Directivas Tácticas:
  1. Establecé una defensa perimetral y en profundidad en torno al pueblo de Arleville y sus accesos viales clave.
  2. Asigná escuadras de fusileros y apoyo pesado a posiciones elevadas y coberturas urbanas sólidas.
  3. Desplegá patrullas de detección temprana y observación para identificar los ejes de avance del enemigo antes de que alcancen el núcleo urbano.
  4. Si el enemigo inicia un asalto, contenelo con fuego concentrado y organizá contrataques o repliegues escalonados sin ceder el control del poblado.
  5. Reaccioná inmediatamente ante cualquier contacto armado o fuego enemigo para mantener la iniciativa defensiva.
  ```

---

### 3. Configuración de Simulación y Bandos

* **Configuración de Arma (ID):** `2215656377869799424`
* **Bandos / Facciones:**
  * **US (BLUFOR):** Control **Humano** (`human`) — Tropas atacantes / Jugador.
  * **USSR (OPFOR):** Control **IA** (`llm`) — Tropas defensoras comandadas por Ollama.
* **Intervalo de Decisión:** `30.0` segundos.
* **Detección de Emergencias:** `true` (reacción táctica inmediata ante fuego enemigo o emboscadas sin esperar al siguiente ciclo de 30s).
* **Límite Máximo de Escuadras:** `12`.
* **Modo de Juego:** `game_master`.
* **Idioma de IA:** `en`.

---

### 4. Objetivo Táctico de Misión (Mission Objective)

```json
{
  "type": "defend",
  "description": "Defender el pueblo de Arleville contra incursiones de fuerzas de EE.UU.",
  "constraints": "Mantener el perímetro urbano de Arleville, asegurar los accesos y repeler avances enemigos"
}
```

---

### 5. Conversaciones Vinculadas

* **Conversación USSR (Principal / Grupo ID `2215656377832050688`):**
  * Título: `Arma Commander - USSR`
  * Bando: `USSR`
  * Agente Vinculado: `Comandante USSR (Arleville)`
* **Conversación US (ID `2215656377848827904`):**
  * Título: `Arma Commander - US`
  * Bando: `US`
  * Control: Humano

---

### 6. Comando Rápido de Conexión en Workbench

En el chat de Arma Reforger (`Enter`):
```
/oalogin oa_arland_989e99a6625a160a8b9b72240efa9211 http://127.0.0.1:28000
```

---

<a id="english"></a>

## 🇬🇧 Scenario Technical Specification: Arland Demo (English)

This document contains the complete technical specification of the demo scenario created for testing OpenArma, Ollama, and Arma Reforger on the island of Arland.

---

### 1. General Project Parameters

* **Project Name:** `Arland Demo`
* **Database ID:** `2215656377748164608`
* **Description:** *OpenArma test on Arland*
* **Status:** `active`
* **API Key:**
  ```
  oa_arland_989e99a6625a160a8b9b72240efa9211
  ```
* **Web Access URL:**
  [http://localhost:23000/projects/2215656377748164608/chat](http://localhost:23000/projects/2215656377748164608/chat)

---

### 2. AI Engine (LLM)

* **Provider:** Local Ollama (`http://localhost:11434`)
* **Model:** `hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS`
* **Agent:** `Comandante USSR (Arleville)` (ID: `2215656377727193088`)
* **Factions:**
  * `US`: **Human** control
  * `USSR`: **LLM** control
* **Mission Type:** `defend` (Arleville village)
* **Decision Interval:** `30.0` seconds (Emergency detection enabled)

---

### 3. In-Game Login Command

```
/oalogin oa_arland_989e99a6625a160a8b9b72240efa9211 http://127.0.0.1:28000
```

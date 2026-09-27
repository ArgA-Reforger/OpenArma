# Code Generator

Code generator plugin for generating common business code.

> [!TIP]
> The current version only includes backend code generation.

> [!WARNING]
> Because Jinja2 may have formatting issues when rendering templates in text mode, the `preview` endpoint may not visually preview code accurately; this is a preset prepared for the frontend.

## Global Configuration

Add the following to `backend/core/conf.py`:

```python
##################################################
# [ Plugin ] code_generator
##################################################
# Basic configuration (in plugin.toml)
CODE_GENERATOR_DOWNLOAD_ZIP_FILENAME: str
```

## Introduction

The code generator is implemented via API calls and includes two modules. The design may have limitations; please open an issue for any related problems.

### Code Generation Business

Contains configuration related to code generation. For details, see: `code_generator/model/gen_business.py`

### Code Generation Model Columns

Contains model column information required for code generation, just like defining model columns normally. Currently supported features are limited.

## Usage

1. Start the backend service and operate directly via the Swagger docs.
2. Send API requests using a third-party API debugging tool.
3. Start both the frontend and backend, and operate from the web interface.

Endpoint parameters are documented; please review them carefully.

### Manual Mode

1. Manually add a business record via the create business endpoint.
2. Manually add model columns via the create model column endpoint.
3. Access the `preview` (preview), `generate` (write to disk), and `download` (download) endpoints to perform corresponding backend code generation tasks.

### Automatic Mode

1. Access the `tables` endpoint to get a list of database table names.
2. Import existing database table data via the `import` endpoint, which automatically creates business table data and model table data.
3. Access the `preview` (preview), `generate` (write to disk), and `download` (download) endpoints to perform corresponding backend code generation tasks.

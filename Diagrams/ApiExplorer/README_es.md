# API Explorer - Arquitectura y Documentación Técnica

## Resumen

API Explorer es un framework web integral diseñado para proporcionar capacidades dinámicas de exploración y prueba de APIs para módulos Python. Construido sobre FastAPI con soporte WebSocket avanzado, ofrece una interfaz moderna y responsiva que permite a múltiples módulos registrar sus APIs en tiempo de ejecución, proporcionando formularios de parámetros interactivos, transmisión de eventos en tiempo real de alto rendimiento, visualización de datos avanzada y capacidades de prueba. El sistema implementa un patrón singleton para accesibilidad global mientras mantiene operaciones thread-safe, arquitectura de worker pools escalable y procesamiento de eventos optimizado.

## Arquitectura General

### Patrón Arquitectónico Principal

El API Explorer sigue una **arquitectura de servicio basada en singleton** combinada con patrones **observer**, **registry** y **worker pool**, organizando la funcionalidad en capas bien definidas con optimizaciones de rendimiento:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA CLIENTE                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Navegador   │  │ Cliente HTTP│  │  Cliente WebSocket  │ │
│  │ Web Modular │  │   (REST)    │  │   (Alto Rendimiento)│ │
│  │ (Managers)  │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 CAPA PRESENTACIÓN                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Plantillas │  │     CSS     │  │    Módulos          │ │
│  │    HTML     │  │   Estilos   │  │   JavaScript        │ │
│  │  (Jinja2)   │  │ (Responsivo)│  │   (Chart.js)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   FRAMEWORK WEB                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Servidor  │  │  WebSocket  │  │   Servicio de       │ │
│  │   FastAPI   │  │   Manager   │  │   Archivos          │ │
│  │  (uvicorn)  │  │ (Worker Pool)│  │   Estáticos         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   SERVICIO CORE                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ ApiExplorer │  │  Registro   │  │ Difusión Optimizada │ │
│  │ (Singleton) │  │ de Módulos  │  │    de Eventos       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Serialización│  │ Validación  │  │    Gestión de       │ │
│  │ de Alto     │  │Parámetros   │  │   Conexiones        │ │
│  │ Rendimiento │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     CAPA DATOS                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Información │  │ Información │  │   Información       │ │
│  │ de Módulos  │  │ de Métodos  │  │ de Parámetros       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Core y Arquitectura

### 1. **API Explorer Core** (`api_explorer.py`)

**Propósito**: Servicio singleton central que gestiona todo el framework de exploración de APIs con arquitectura de alto rendimiento.

#### Componentes:
- **`ApiExplorer`**: Clase singleton principal que coordina todas las operaciones
- **Registro de Módulos**: Sistema de registro dinámico para módulos externos
- **`WebSocketManager`**: Manejador de comunicación en tiempo real con worker pools
- **Gestión de Rutas**: Generación dinámica de rutas FastAPI
- **Difusión de Eventos**: Sistema de distribución de eventos multi-cliente optimizado

#### Características Clave:
- **Patrón Singleton**: Instancia única thread-safe con double-checked locking
- **Registro Dinámico**: Registro de módulos y métodos en tiempo de ejecución
- **Operaciones Thread-Safe**: Múltiples locks para thread safety granular
- **Worker Pool Architecture**: Procesamiento distribuido para WebSockets
- **Gestión de Puertos**: Detección automática de puertos y asignación
- **Ciclo de Vida del Servidor**: Gestión completa de inicio/parada del servidor

```python
# Ejemplo de uso con características optimizadas
from api_explorer import ApiExplorer

explorer = ApiExplorer.get_instance()
explorer.register_module("mi_modulo", "Mi Módulo", "Descripción")
explorer.add_method_group("mi_modulo", "control", "Métodos de Control")
explorer.register_method("mi_modulo", "control", "iniciar", method_info, handler)

# Broadcasting de alto rendimiento
explorer.broadcast_event("mi_modulo", {
    "timestamp": time.time(),
    "data": high_frequency_data,
    "visualization": {"chart_type": "line"}
})
```

#### Detalles de Arquitectura:
- **Thread Safety**: Múltiples locks (`_lock`, locks específicos de router)
- **Worker Pool Management**: Pools adaptativos por módulo para escalabilidad
- **Sistema de Eventos Optimizado**: Difusión de eventos con throttling adaptativo
- **Integración Sistema de Archivos**: Navegación de directorios del lado del servidor
- **Manejo de Errores**: Aislamiento comprehensivo de errores y recuperación
- **Performance Monitoring**: Estadísticas en tiempo real de WebSocket workers

### 2. **Sistema WebSocket de Alto Rendimiento**

#### WebSocketManager (`websocket_manager.py`)

**Propósito**: Gestor central de conexiones WebSocket con arquitectura de worker pools escalable.

##### Componentes:
- **`WebSocketManager`**: Coordinador principal de conexiones y workers
- **`WebSocketWorkerPool`**: Pool de workers para procesamiento distribuido
- **`WorkerStats`**: Métricas de rendimiento por worker
- **`FastJSONSerializer`**: Serialización optimizada con soporte orjson

##### Características:
- **Arquitectura Worker Pool**: Distribución de carga entre múltiples workers
- **Throttling Adaptativo**: Limitación inteligente de mensajes por frecuencia
- **Serialización Optimizada**: orjson para máximo rendimiento
- **Load Balancing**: Distribución round-robin entre workers
- **Performance Tracking**: Métricas detalladas de procesamiento

```python
# Worker pool automático por módulo
{
    "module_id": "data_stream",
    "worker_count": 4,
    "messages_per_second": 1000,
    "avg_processing_time": 0.001,
    "queue_utilization": 0.75
}
```

#### Serialización de Alto Rendimiento (`serialization.py`)

**Propósito**: Sistema de serialización JSON optimizado para transmisión de datos de alta frecuencia.

##### Características:
- **orjson Integration**: Uso de orjson para máxima velocidad de serialización
- **Template Caching**: Pre-compilación de estructuras JSON frecuentes
- **Compact Mode**: Modo compacto para reducir ancho de banda
- **Fallback Safety**: Degradación grácil a stdlib json si orjson no está disponible
- **Data Sanitization**: Limpieza automática de datos no serializables

### 3. **Módulo Principal Optimizado** (`main.py`)

**Propósito**: Punto de entrada y gestión de servidor de alto nivel con capacidades de worker pool.

#### Componentes:
- **`run_explorer()`**: Función principal para iniciar el API Explorer optimizado
- **`main()`**: Punto de entrada de línea de comandos
- **Configuración del Servidor**: Configuración de host, puerto y workers
- **Gestión de Rutas**: Configuración de rutas Python para importaciones

#### Características:
- **Despliegue Flexible**: Soporta modos de servidor bloqueante y no bloqueante
- **Worker Pool Initialization**: Configuración automática de pools por módulo
- **Gestión de Configuración**: Configuración de host, puerto y workers
- **Gestión de Importaciones**: Resolución automática de rutas para importaciones de módulos
- **Performance Optimization**: Inicialización optimizada de componentes

### 4. **Arquitectura Frontend Modular**

#### JavaScript Modular (`static/js/`)

**Propósito**: Arquitectura frontend basada en managers con comunicación event-driven.

##### Componentes Principales:

###### **APIExplorer Coordinator** (`script.js`)
- **Manager Coordination**: Coordinación central de todos los managers
- **Event-Driven Communication**: Sistema de eventos entre managers
- **Module Initialization**: Inicialización secuencial de módulos
- **Cross-Manager Communication**: Comunicación desacoplada entre componentes

###### **DarkModeManager** (`modules/darkModeManager.js`)
- **Theme Management**: Gestión centralizada de temas oscuro/claro
- **Callback System**: Notificación de cambios de tema a otros managers
- **Chart Integration**: Actualización automática de temas de Chart.js
- **Persistence**: Almacenamiento de preferencias de usuario

###### **WebSocketManager** (`modules/webSocketManager.js`)
- **Connection Management**: Gestión de múltiples conexiones WebSocket
- **Event Buffering**: Buffering inteligente para eventos de alta frecuencia
- **Performance Optimization**: Limitación de updates para suavidad visual
- **Error Handling**: Reconexión automática y manejo de errores

###### **ChartManager** (`modules/chartManager.js`)
- **Chart Coordination**: Gestión de múltiples instancias Chart.js
- **Batched Updates**: Actualizaciones por lotes para optimización
- **Adaptive Throttling**: Throttling basado en frecuencia de datos
- **Multi-Channel Support**: Visualización separada o combinada de canales
- **Theme Integration**: Actualización automática con cambios de tema

###### **EventDisplayManager** (`modules/eventDisplayManager.js`)
- **Event Coordination**: Coordinación de display de eventos en tiempo real
- **Auto-Scrolling**: Scroll automático inteligente
- **Performance Buffers**: Buffering para eventos de alta frecuencia
- **Cross-Manager Events**: Coordinación con ChartManager

###### **FileBrowserManager** (`modules/fileBrowserManager.js`)
- **Server Integration**: Integración con navegación de archivos del servidor
- **Modal Management**: Gestión de modal de navegador de archivos
- **Path Resolution**: Resolución de rutas cross-platform
- **File Selection**: Selección interactiva con filtros

###### **APIMethodsManager** (`modules/apiMethodsManager.js`)
- **Method Execution**: Ejecución de métodos API con validación
- **Parameter Handling**: Gestión de parámetros dinámicos
- **Request Preparation**: Preparación de requests con validación
- **Response Handling**: Manejo de respuestas y errores

```javascript
// Ejemplo de arquitectura manager
class APIExplorer {
    constructor() {
        this.darkModeManager = new DarkModeManager();
        this.webSocketManager = new WebSocketManager();
        this.chartManager = new ChartManager();
        this.eventDisplayManager = new EventDisplayManager();
    }

    setupManagerCommunication() {
        // Event-driven communication between managers
        this.darkModeManager.onModeChange((isDark) => {
            this.chartManager.updateTheme(isDark);
        });

        this.webSocketManager.onDataReceived((moduleId, data) => {
            this.chartManager.updateData(moduleId, data);
            this.eventDisplayManager.addDataEvent(moduleId, data);
        });
    }
}
```

#### Plantilla HTML Responsiva (`templates/index.html`)

**Propósito**: Interfaz web dinámica y responsiva con framework Bootstrap optimizado.

##### Componentes Clave:
- **Interfaz de Registro de Módulos**: Generación dinámica de lista de módulos
- **Pestañas de Explorador API**: Interfaz de exploración API por módulo
- **Paneles de Eventos en Tiempo Real**: Visualización optimizada de eventos WebSocket
- **Formularios de Parámetros**: Generación dinámica con validación en tiempo real
- **Modal de Navegador de Archivos**: Navegación del sistema de archivos del lado del servidor
- **Visualización de Datos Avanzada**: Integración Chart.js con múltiples modos de visualización

##### Características:
- **Diseño Responsivo**: Layout responsivo basado en Bootstrap
- **Modo Oscuro/Claro**: Sistema completo de temas con persistencia
- **Contenido Dinámico**: Plantillas Jinja2 con actualizaciones optimizadas
- **Actualizaciones en Tiempo Real**: Updates en vivo optimizados via WebSocket
- **Formularios Interactivos**: Validación avanzada y controles específicos por tipo

#### Estilos CSS Avanzados (`static/css/styles.css`)

**Propósito**: Sistema de estilos comprehensivo con soporte de tema dual y optimizaciones visuales.

##### Componentes:
- **Estilos Modo Oscuro**: Implementación completa de tema oscuro profesional
- **Estilos Modo Claro**: Tema claro por defecto con apariencia moderna
- **Estilos de Componentes**: Estilos consistentes para todos los componentes UI
- **Layout Responsivo**: Principios de diseño responsivo mobile-first
- **Integración de Gráficos**: Temas Chart.js integrados
- **Performance Styles**: Optimizaciones CSS para animaciones suaves

##### Características:
- **Consistencia de Tema**: Paleta de colores unificada y tipografía
- **Accesibilidad**: Ratios de alto contraste y cumplimiento WCAG
- **Diseño Moderno**: Principios de diseño web contemporáneo
- **Compatibilidad Cross-browser**: Apariencia consistente entre navegadores
- **Chart Styling**: Estilos optimizados para visualizaciones de datos

## Estructuras de Datos y Modelos Optimizados

### 1. **ModuleInfo Expandido**
**Propósito**: Almacenamiento completo de metadatos y configuración de módulos con capacidades de worker pool.

#### Atributos:
- **Identidad del Módulo**: ID, nombre, descripción y preferencias de display
- **Grupos de Métodos**: Colección organizada de métodos relacionados
- **Integración Router**: Router FastAPI para endpoints HTTP
- **Worker Pool Configuration**: Configuración de pools específicos por módulo
- **Performance Settings**: Configuraciones de throttling y buffering

### 2. **WorkerStats**
**Propósito**: Métricas de rendimiento detalladas para monitoreo de worker pools.

#### Atributos:
- **Message Processing**: Conteo de mensajes procesados por worker
- **Timing Metrics**: Tiempo promedio de procesamiento
- **Queue Utilization**: Utilización de colas de mensajes
- **Activity Tracking**: Timestamp de última actividad
- **Performance Analytics**: Métricas para optimización automática

### 3. **EventData Optimizado**
**Propósito**: Estructura de datos optimizada para eventos de alta frecuencia.

#### Atributos:
- **Timestamp Precision**: Timestamps de alta precisión
- **Data Compression**: Datos comprimidos para eficiencia
- **Visualization Metadata**: Metadatos para renderizado optimizado
- **Serialization Cache**: Cache de serialización para performance
- **Type Classification**: Clasificación para throttling inteligente

## Características y Capacidades Avanzadas

### 1. **Visualización de Datos de Alto Rendimiento**

#### Integración de Gráficos Optimizada:
- **Framework Chart.js**: Gráficos profesionales con optimizaciones de rendimiento
- **Streaming en Tiempo Real**: Actualizaciones de datos en vivo con throttling adaptativo
- **Soporte Multi-canal**: Visualización separada para diferentes canales de datos
- **Batched Updates**: Actualizaciones por lotes para suavidad visual
- **Memory Management**: Gestión inteligente de memoria para datasets grandes

#### Modos de Visualización Avanzados:
- **Gráficos Combinados**: Todos los canales en un solo gráfico para comparación
- **Gráficos Separados**: Gráficos individuales por canal para análisis detallado
- **Filtrado por Tipo**: Filtrar display por tipo de datos (EEG, EMG, etc.)
- **Auto-escalado Inteligente**: Escalado dinámico basado en análisis estadístico
- **Adaptive Rendering**: Renderizado adaptativo basado en capacidad del cliente

### 2. **Sistema de Eventos WebSocket de Alto Rendimiento**

#### Comunicación en Tiempo Real Optimizada:
- **Worker Pool Architecture**: Procesamiento distribuido para escalabilidad
- **Adaptive Message Throttling**: Limitación inteligente basada en frecuencia
- **Load Balancing**: Distribución equitativa entre workers
- **Performance Monitoring**: Métricas en tiempo real de rendimiento
- **Memory Efficient Buffering**: Buffering optimizado para memoria

#### Tipos de Eventos Expandidos:
- **High-Frequency Data**: Eventos de datos de alta frecuencia optimizados
- **Batch Events**: Eventos por lotes para eficiencia
- **Priority Events**: Sistema de prioridades para eventos críticos
- **Compressed Events**: Eventos comprimidos para ancho de banda limitado
- **Analytics Events**: Eventos de analytics para monitoreo de rendimiento

### 3. **Serialización JSON de Alto Rendimiento**

#### Optimizaciones de Serialización:
- **orjson Integration**: Uso de orjson para máxima velocidad
- **Template Pre-compilation**: Pre-compilación de estructuras frecuentes
- **Compact Serialization**: Modo compacto para reducir payload
- **Batch Serialization**: Serialización por lotes para eficiencia
- **Cache Management**: Cache inteligente de objetos serializados

#### Características:
- **Fallback Safety**: Degradación grácil si orjson no está disponible
- **Data Sanitization**: Limpieza automática de datos problemáticos
- **Type Optimization**: Optimizaciones específicas por tipo de datos
- **Memory Efficiency**: Gestión optimizada de memoria durante serialización

### 4. **Formularios de Parámetros Dinámicos Avanzados**

#### Generación de Formularios Optimizada:
- **Lazy Loading**: Carga perezosa de controles complejos
- **Real-time Validation**: Validación en tiempo real con debouncing
- **Adaptive UI**: Controles adaptativos basados en tipo de dispositivo
- **Performance Forms**: Formularios optimizados para entrada rápida
- **Smart Defaults**: Valores por defecto inteligentes basados en historial

## Patrones de Integración y Uso Optimizados

### 1. **Patrón de Registro de Módulos con Worker Pools**

```python
# Registro optimizado de módulo con worker pools
explorer = ApiExplorer.get_instance()
explorer.register_module("data_stream", "Data Stream", "High-frequency data")

# Configuración de worker pool específico
explorer.websocket_manager._determine_pool_size("data_stream")  # Auto-sizing

# Métodos optimizados para alta frecuencia
method_info = {
    "name": "Stream Data",
    "description": "High-frequency data streaming",
    "type": "streaming",
    "performance": {
        "expected_frequency": 1000,  # Hz
        "throttling": "adaptive",
        "batch_size": 10
    }
}
```

### 2. **Patrón de Difusión de Eventos de Alto Rendimiento**

```python
# Broadcasting optimizado con worker pools
event_data = {
    "timestamp": time.time_ns(),  # Nanosecond precision
    "type": "high_frequency_data",
    "data": compressed_data,
    "visualization": {
        "chart_type": "line",
        "update_mode": "batch_append",
        "throttle_ms": 16  # 60 FPS
    },
    "priority": "normal"  # normal, high, critical
}

# Broadcasting distribuido
explorer.broadcast_event("data_stream", event_data)
```

### 3. **Patrón de Integración del Servidor con Worker Pools**

```python
# Inicialización optimizada con worker pools
def initialize_optimized_api():
    explorer = ApiExplorer.get_instance()

    # Configuración de performance
    explorer.websocket_manager._setup_json_templates()

    # Registro con configuración de worker pool
    setup_high_frequency_module(explorer)

    # Inicio con workers pre-inicializados
    explorer.start_server(host="localhost", port=8000, block=False)

    return explorer
```

## Patrones Arquitectónicos Implementados

### 1. **Patrón Singleton Optimizado**
- **`ApiExplorer`**: Singleton thread-safe con optimizaciones de performance
- **Gestión de Estado Global**: Estado consistente con cache distribuido
- **Resource Sharing**: Compartición eficiente de worker pools y conexiones

### 2. **Patrón Worker Pool**
- **Distributed Processing**: Procesamiento distribuido para WebSockets
- **Load Balancing**: Balanceo de carga automático entre workers
- **Adaptive Scaling**: Escalado automático basado en carga

### 3. **Patrón Observer Optimizado**
- **High-Frequency Events**: Eventos de alta frecuencia con throttling
- **Batch Notifications**: Notificaciones por lotes para eficiencia
- **Priority Queuing**: Colas con prioridades para eventos críticos

### 4. **Patrón Factory Avanzado**
- **Dynamic Worker Creation**: Creación dinámica de workers por módulo
- **Adaptive Configuration**: Configuración adaptativa basada en carga
- **Performance Optimization**: Optimización automática de parámetros

## Características de Rendimiento y Escalabilidad

### 1. **Manejo Eficiente de Datos de Alta Frecuencia**
- **Worker Pool Processing**: Procesamiento distribuido para escalabilidad
- **Adaptive Throttling**: Throttling inteligente basado en capacidad del cliente
- **Memory Pool Management**: Gestión optimizada de memoria con pools
- **Batch Processing**: Procesamiento por lotes para eficiencia
- **Compression Pipeline**: Pipeline de compresión para datos grandes

### 2. **Gestión Avanzada de Conexiones**
- **Worker Pool Architecture**: Arquitectura escalable de worker pools
- **Connection Load Balancing**: Balanceo de carga entre conexiones
- **Adaptive Resource Management**: Gestión adaptativa de recursos
- **Performance Monitoring**: Monitoreo continuo de performance
- **Automatic Optimization**: Optimización automática basada en métricas

### 3. **Rendimiento de UI Optimizado**
- **Batched DOM Updates**: Actualizaciones de DOM por lotes
- **Adaptive Frame Rate**: Frame rate adaptativo basado en carga
- **Memory Efficient Rendering**: Renderizado optimizado para memoria
- **Lazy Component Loading**: Carga perezosa de componentes complejos
- **Performance Profiling**: Profiling automático de performance frontend

## Stack Tecnológico y Dependencias Optimizadas

### Tecnologías Backend Optimizadas:
- **FastAPI**: Framework web de alto rendimiento con worker pools
- **Uvicorn**: Servidor ASGI optimizado con workers múltiples
- **orjson**: Serialización JSON ultra-rápida
- **asyncio**: Programación asíncrona para concurrencia
- **WebSockets**: Comunicación bidireccional optimizada

### Tecnologías Frontend Optimizadas:
- **Modular JavaScript**: Arquitectura de managers para escalabilidad
- **Chart.js**: Visualización optimizada con batched updates
- **Bootstrap 5**: Framework CSS responsivo optimizado
- **WebSocket APIs**: APIs WebSocket nativas optimizadas
- **CSS Grid/Flexbox**: Layout moderno con optimizaciones de rendimiento

### Herramientas de Optimización:
- **Worker Pools**: Procesamiento distribuido para escalabilidad
- **Adaptive Throttling**: Limitación inteligente de recursos
- **Performance Monitoring**: Monitoreo continuo de métricas
- **Memory Management**: Gestión optimizada de memoria
- **Compression**: Compresión de datos para eficiencia

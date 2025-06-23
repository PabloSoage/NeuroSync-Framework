# EEG Processor - Arquitectura y Documentación Técnica

## Resumen

EEG Processor es un framework modular para procesamiento de señales EEG en tiempo real que soporta múltiples dispositivos de hardware (OpenBCI, g.tec, Muse, ANT Neuro, Neurosity), análisis avanzado (ICA, wavelet transforms, MNE-Python), y múltiples interfaces (GUI Qt5, CLI, REST API). Implementa una **arquitectura orientada a servicios** con **patrones dirigidos por eventos** para procesamiento de neuroseñales.

## Arquitectura General

### Patrón Arquitectónico Principal

La aplicación sigue una **arquitectura orientada a servicios (SOA)** combinada con patrones **dirigidos por eventos**, **Singleton** y **MVC**, organizando el código en capas especializadas:

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACES EXTERNAS                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    GUI      │  │     CLI     │  │     REST API        │ │
│  │  (Qt5 MVC)  │  │   (Typer)   │  │  (WebSocket+HTTP)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      ADAPTADORES                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │QtInteraction│  │ CLI Commands│  │ API Integrations    │ │
│  │   Adapter   │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE SERVICIOS                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Collector    │  │Data Access  │  │  Advanced Analysis  │ │
│  │  Service    │  │  Service    │  │     Services        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLADORES UI                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Panel-Based  │  │ MNE Panel   │  │   Advanced Panel    │ │
│  │   MVC       │  │ Controller  │  │   Controller        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      NÚCLEO                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Event System │  │Signal       │  │   Hardware          │ │
│  │             │  │Processing   │  │  Abstraction        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Submódulos y Componentes

### 1. **Core Event System** (`core/`)

**Propósito**: Sistema de eventos centralizado thread-safe para comunicación desacoplada entre componentes.

#### Componentes:
- **`EventDispatcher`**: Singleton thread-safe con RLock protection
- **`EventType`**: Enumeración de 40+ tipos de eventos (CONNECTION, PROCESSING, VISUALIZATION, MNE, ICA, etc.)
- **`Event`**: Dataclass con timestamp, source y data payload

#### Características:
- **Operaciones thread-safe**: Sincronización basada en RLock
- **Seguimiento de historial de eventos**: 1000 eventos con rotación automática
- **Soporte para suscriptores tardíos**: Entrega automática del último evento
- **Aislamiento de errores**: Fallos en callbacks no afectan otros suscriptores
- **Optimización de rendimiento**: Almacenamiento basado en conjuntos para operaciones O(1)

```python
# Uso del sistema de eventos
from core import dispatch, subscribe, EventType

def on_filter_applied(event):
    print(f"Filtro aplicado: {event.data}")

subscribe(EventType.FILTER_APPLY, on_filter_applied)
dispatch(EventType.FILTER_APPLY, {
    "bandpass": {"low": 1, "high": 50},
    "notch": {"freq": 50},
    "channels": [1, 2, 3, 4]
})
```

### 2. **Interfaces** (`interfaces/`)

**Propósito**: Contratos ABC para arquitectura modular y testeable.

#### Componentes:
- **`CollectorInterface`**: Base para colectores EEG
- **`MarkerInterface`**: Inserción de marcadores durante grabación
- **`ConfigurableCollectorInterface`**: Configuración de dispositivos
- **`BoardInterface`**: Gestión de configuración de placas
- **`MNEInterfaces`**: Contratos para procesamiento MNE-Python
- **`RecordingInterface`**: Almacenamiento y grabación continua

#### Características:
- **Clases base abstractas**: Contratos estrictos con `@abstractmethod`
- **Anotaciones de tipo**: Tipado completo con `numpy.ndarray`, `Dict[str, Any]`
- **Segregación de interfaces**: Interfaces específicas para diferentes capacidades
- **Facilidad de pruebas**: Mocking e inyección de dependencias facilitados

### 3. **Collectors** (`collectors/`)

**Propósito**: Capa de abstracción de hardware para dispositivos EEG con soporte BrainFlow.

#### Componentes:
- **`EEGCollector`**: Implementación principal con múltiples interfaces
- **`BrainFlowBoardConfiguration`**: Gestión de configuración de 20+ fabricantes
- **`BoardConfiguration`**: Wrapper estático para compatibilidad

#### EEGCollector - Características:
- **Soporte multi-preset**: Flujos de datos DEFAULT, AUXILIARY, ANCILLARY
- **Inserción de marcadores en tiempo real**: Sincronización de microsegundo con datos EEG
- **Soporte multi-placa**: OpenBCI, g.tec Unicorn, Muse, ANT Neuro, Neurosity, BrainBit, etc.
- **Soporte para placas de streaming**: Configuración de placa maestra con validación de preset
- **Detección automática de canales**: EEG, EMG, ECG, acelerómetro, giroscopio
- **Operaciones thread-safe**: Gestión de buffer y recuperación de datos

```python
# Capacidades de configuración de placas
SUPPORTED_BOARDS = {
    "OpenBCI": [BoardIds.CYTON_BOARD, BoardIds.GANGLION_BOARD],
    "g.tec": [BoardIds.UNICORN_BOARD],
    "Muse": [BoardIds.MUSE_2_BOARD, BoardIds.MUSE_S_BOARD],
    "ANT Neuro": [BoardIds.ANT_NEURO_EE_410_BOARD],
    "Neurosity": [BoardIds.NOTION_1_BOARD, BoardIds.NOTION_2_BOARD],
    "BrainBit": [BoardIds.BRAINBIT_BOARD, BoardIds.BRAINBIT_BLED_BOARD]
}
```

### 4. **Processors** (`processors/`)

**Propósito**: Motor de procesamiento de señales con algoritmos avanzados.

#### Componentes:
- **`SignalProcessor`**: Motor principal con múltiples algoritmos

#### Características:
- **Múltiples tipos de filtros**: Butterworth, Chebyshev Tipo 1, Bessel (fase cero)
- **Monitoreo inteligente de estabilidad**: Ajuste automático para datos sintéticos
- **Procesamiento wavelet**: 15+ tipos (Daubechies, Biorthogonal, Coiflets, Symlets)
- **Análisis de componentes independientes**: FastICA con configuración de 1-16 componentes
- **Evaluación de calidad de señal**: Sistema de 5 niveles con detección de porcentaje saturado
- **Métricas EEG**: Potencias de banda (Delta, Theta, Alpha, Beta, Gamma)
- **Métricas cognitivas basadas en ML**: Puntuaciones de atención plena, descanso, concentración

```python
# Filtrado avanzado con monitoreo de estabilidad
processor = SignalProcessor(sampling_rate=250)
filtered_data = processor.bandpass_filter(
    data=eeg_data,
    start_freq=1.0,
    stop_freq=50.0,
    order=4,
    filter_type=FilterTypes.BUTTERWORTH,
    ripple=0.1  # Auto-ajustado para estabilidad Chebyshev
)
```

### 5. **Services** (`services/`)

**Propósito**: Capa de servicios singleton para lógica de negocio y coordinación.

#### Componentes Principales:
- **`CollectorService`**: Gestión singleton de colección EEG
- **`DataAccessService`**: Acceso centralizado con gestión de buffer
- **`ProcessorService`**: Coordinación de filtros y procesamiento
- **`RecordingService`**: Grabación continua multi-formato
- **`VisualizationService`**: Gestión de componentes visuales
- **`InteractionService`**: Puente API-interno con validación
- **`AdvancedProcessingService`**: ICA, wavelet, submuestreo
- **`MNEService`**: Fachada para integración MNE-Python

#### Servicios Especializados:

##### **ICA Services** (`services/ica/`):
- **`ICAProcessService`**: ICA multiproceso con integración de señales Qt
- **`ICARealtimeService`**: Monitoreo tiempo real con ventana deslizante
- **`ExportService`**: Exportación por lotes con seguimiento de progreso

##### **MNE Services** (`services/mne/`):
- **`MNEConverterService`**: Conversión BrainFlow→MNE asíncrona
- **`MNEVisualizerService`**: Visualización avanzada (PSD, topomaps, espectrogramas)
- **`MNERealtimeService`**: Procesamiento tiempo real con sesiones configurables
- **`MNEResultStorage`**: Almacenamiento thread-safe con gestión de ciclo de vida
- **`MNEProcessManager`**: Coordinación multiproceso para operaciones CPU-intensivas

#### Características:
- **Operaciones thread-safe**: Estrategia de bloqueo granular
- **Patrón Singleton**: Bloqueo de verificación doble con inicialización perezosa
- **Sistemas de callbacks**: Patrones reactivos para consumidores externos
- **Gestión de memoria**: Límites de buffer y limpieza automática
- **Procesamiento en segundo plano**: Pool de hilos para operaciones no bloqueantes

### 6. **UI** (`ui/`)

**Propósito**: Arquitectura MVC basada en paneles con controladores especializados.

#### Estructura Base:
- **`BasePanel`**: Clase fundacional con mensajería estandarizada
- **Clases de Panel**: ConnectionPanel, ProcessingPanel, RecordingPanel, etc.
- **Controladores especializados**: MNEPanelController, AdvancedPanelController

#### Paneles UI:

##### **ConnectionPanel**:
- **Selección de placa**: Filtrado inteligente y categorización
- **Validación dinámica de parámetros**: Retroalimentación visual para campos requeridos/opcionales
- **Configuración de placa de streaming**: Validación de preset con prevención de errores de socket
- **Información de placa en tiempo real**: Mapeo de canales, frecuencia de muestreo, detalles de hardware

##### **ProcessingPanel**:
- **Aplicación de filtros en tiempo real**: Actualizaciones dinámicas durante procesamiento activo
- **Filtrado integral**: Pasabanda (1-200 Hz), Notch (50/60 Hz), Detrend
- **Cálculo de métricas EEG**: Potencias de banda, análisis estadístico
- **Visualización de mapa cerebral**: Optimización de rendimiento con datos de streaming

##### **MNE Panel** (`ui/mne/`):
- **Implementación principios SOLID**: Controlador con composición de widgets
- **Conversión multi-modo**: Flexible (todos los canales), Rendimiento (seleccionados), Tiempo real
- **Visualización avanzada**: PSD, topomaps, espectrogramas, datos en bruto
- **Sesiones de procesamiento en tiempo real**: Actualizaciones de parámetros sin reinicio
- **Integración de filtros**: Coordinación fluida con panel de procesamiento

##### **Advanced Panel** (`ui/advanced/`):
- **ICA Widget**: Monitoreo tiempo real con capacidades de exportación
- **Wavelet Widget**: Análisis de transformadas con soporte de eliminación de ruido
- **Advanced Filter Widget**: Filtrado multi-tipo con análisis de estabilidad
- **Downsampling Widget**: Optimización de rendimiento con métodos de agregación

#### Widgets Especializados:

##### **MNE Widgets** (`ui/mne/widgets/`):
- **`MNEConversionWidget`**: Interfaz multi-modo con advertencias de rendimiento
- **`MNEVisualizationWidget`**: Controles de visualización con actualizaciones en tiempo real
- **`MNEStatusWidget`**: Monitoreo tiempo real con métricas de rendimiento
- **`ChannelSelectionDialog`**: Selección basada en cuadrícula con indicadores de optimización

##### **Advanced Widgets** (`ui/advanced/widgets/`):
- **`ICAWidget`**: Configuración de cantidad de componentes (1-16) con selección de canales
- **`WaveletWidget`**: Selección de tipo de wavelet con niveles de descomposición
- **`AdvancedFilterWidget`**: Selección de tipo de filtro, orden, función de ventana
- **`DownsamplingWidget`**: Configuración de factor con métodos de agregación

#### Características UI:
- **Integración de tema oscuro**: Estilo consistente entre componentes
- **Actualizaciones en tiempo real**: Modificación dinámica de parámetros sin reinicio de sesión
- **Monitoreo de rendimiento**: Advertencias de uso de CPU y sugerencias de optimización
- **Arquitectura dirigida por eventos**: Señales Qt para bajo acoplamiento
- **Operaciones thread-safe**: Manejo adecuado del hilo de la interfaz de usuario

### 7. **Visualizers** (`visualizers/`)

**Propósito**: Componentes de visualización científica en tiempo real.

#### Componentes:
- **`MultiSignalVisualizer`**: Visualización biosignal multi-página
- **`BrainMapVisualizer`**: Mapeo topográfico cerebral

#### MultiSignalVisualizer - Características:
- **Detección inteligente de canales**: EEG, EMG, ECG, EOG, EDA, PPG, acelerómetro, giroscopio
- **Arquitectura de carga perezosa**: Caché para optimización de rendimiento
- **Interfaz multi-pestaña**: Separación por modalidad de señal
- **Integración de datos en tiempo real**: Coordinación con DataAccessService
- **Optimización de rendimiento**: Actualizaciones selectivas de pestañas, operaciones eficientes en memoria

#### BrainMapVisualizer - Características:
- **Posicionamiento internacional 10-20/10-10**: Posiciones estándar de electrodos
- **Calidad de señal en tiempo real**: Indicadores codificados por color (sistema de 5 niveles)
- **Regiones anatómicas cerebrales**: Superposiciones frontal, central, parietal, occipital
- **Compatibilidad G.tec Unicorn**: Mapeo automático de canales
- **Elementos interactivos**: Etiquetas de electrodos con leyenda de calidad

```python
# Capacidades de detección de tipos de canal
SUPPORTED_CHANNEL_TYPES = {
    "EEG": "Señales de electroencefalografía",
    "EMG": "Señales de electromiografía",
    "ECG": "Señales de electrocardiografía",
    "EOG": "Señales de electrooculografía",
    "EDA": "Actividad electrodérmica",
    "PPG": "Fotopletismografía",
    "Accelerometer": "Aceleración de 3 ejes",
    "Gyroscope": "Velocidad angular de 3 ejes"
}
```

### 8. **Utils** (`utils/`)

**Propósito**: Utilidades y sistemas de soporte para la aplicación.

#### Componentes:
- **`ThemeManager`**: Estilizado avanzado y tema oscuro
- **`HelpSystem`**: Sistema de ayuda contextual con 25+ temas

#### ThemeManager - Características:
- **Implementación de tema oscuro**: Optimización de estilizado de widgets Qt
- **Esquema de color consistente**: Colores semánticos (éxito, advertencia, error, acento)
- **Cobertura de widgets**: Botones, entradas, pestañas, barras de desplazamiento, grupos
- **Cumplimiento de accesibilidad**: Relaciones de contraste apropiadas

#### HelpSystem - Características:
- **25+ temas detallados**: Hardware, procesamiento, visualización, grabación, análisis
- **Ayuda sensible al contexto**: Integración HelpButton en UI
- **Interfaz de ayuda con pestañas**: Organización por áreas funcionales
- **Contenido educativo**: Conceptos básicos EEG, teoría de procesamiento de señales, análisis avanzado

### 9. **CLI** (`cli/`)

**Propósito**: Interfaz de línea de comandos con capacidades avanzadas.

#### Componentes:
- **`CLIApp`**: Aplicación Typer principal con registro de comandos
- **`CLIShell`**: Shell interactivo para ejecución amigable de comandos
- **`CLIConfig`**: Configuración y gestión de estado para CLI
- **`HeadlessEEGProcessor`**: Stack sin cabeza para uso programático

#### Módulos de Comandos:
- **`DataCommands`**: Acceso y visualización de datos/metadatos EEG
- **`MonitorCommands`**: Monitoreo tiempo real de streams, canales, calidad de señal
- **`InteractionCommands`**: Control del procesador (conectar, stream, grabar, filtros)

#### Características:
- **Framework Typer**: CLI moderno con autocompletado
- **Salida de consola Rich**: Tablas, paneles, visualizaciones en tiempo real
- **Soporte multiplataforma**: Compatibilidad Windows/Linux/macOS
- **Modo sin cabeza**: Uso mínimo de recursos para scripting
- **Shell interactivo**: Interfaz estilo REPL con historial de comandos

```bash
# Ejemplos de uso CLI
eeg-processor data current-data --max-samples 1000
eeg-processor control connect-board --board-id 1 --preset 0
eeg-processor monitor realtime --channels 1,2,3,4
eeg-processor control apply-filters --bandpass-low 1 --bandpass-high 50
```

### 10. **Adapters** (`adapters/`)

**Propósito**: Puentes thread-safe entre frameworks y servicios centrales.

#### Componentes:
- **`QtInteractionAdapter`**: Puente Qt-servicio thread-safe

#### Características:
- **Ejecución thread-safe**: ThreadPoolExecutor con gestión de timeout (5s por defecto)
- **Aislamiento de framework**: Separación clara entre Qt y servicios centrales
- **Cobertura de API**: Todas las operaciones de panel y recuperación de configuraciones
- **Manejo de errores**: Detección de timeout y degradación elegante
- **Comunicación entre hilos**: Ejecución basada en QTimer del hilo principal

### 11. **API Integration** (archivos raíz)

**Propósito**: REST API con WebSocket para acceso remoto y control.

#### Componentes:
- **`EEGDataAPI`**: API estática para acceso a datos
- **`EEGProcessorInteractionAPI`**: API estática para control del sistema
- **`EEGProcessorApiIntegration`**: Integración WebSocket para streaming de datos
- **`EEGProcessorInteractionApiIntegration`**: Integración API para operaciones de control

#### Características:
- **Streaming de datos de modo dual**: Modo directo (baja latencia ~15ms), Modo multiproceso
- **WebSocket tiempo real**: Difusión de payload estructurado
- **API de control integral**: Gestión de placas, procesamiento, grabación, análisis
- **Operaciones thread-safe**: Todas las llamadas API thread-safe con gestión de timeout
- **Integración de sistemas externos**: Documentación automática vía API Explorer

```python
# Capacidades de API Integration
API_ENDPOINTS = {
    "Data Access": ["get_current_data", "get_eeg_data", "get_metadata"],
    "Board Control": ["connect_board", "start_stream", "insert_marker"],
    "Processing": ["apply_filters", "calculate_metrics", "perform_ica"],
    "Recording": ["start_recording", "stop_recording", "save_data"],
    "Advanced": ["convert_to_mne", "compute_wavelet", "apply_downsampling"]
}
```

## Patrones Arquitectónicos Implementados

### 1. **Arquitectura Orientada a Servicios (SOA)**
- **Servicios singleton** con inicialización thread-safe
- **Coordinación de servicios** vía InteractionService
- **Límites claros de servicio** con interfaces bien definidas
- **Inyección de dependencias** para pruebas y modularidad

### 2. **Arquitectura Dirigida por Eventos**
- **Core Event System** como columna vertebral de comunicación
- **Patrón Pub/Sub** para acoplamiento suelto
- **Coordinación entre componentes** sin dependencias directas
- **Sincronización API-GUI** vía eventos

### 3. **Modelo-Vista-Controlador (MVC)**
- **MVC basado en paneles**: Controladores coordinando múltiples widgets
- **Controladores especializados**: MNEPanelController, AdvancedPanelController
- **Comunicación señal/slot**: Arquitectura Qt para UI responsiva
- **Gestión de estado**: Consistente a través de contextos operacionales

### 4. **Multiprocesamiento y Multihilo**
- **Operaciones CPU-intensivas**: Procesamiento ICA, MNE en procesos separados
- **Hilos en segundo plano**: Colección de datos, procesamiento tiempo real
- **Comunicación thread-safe**: Señales Qt, colas multiproceso
- **Gestión de ciclo de vida de recursos**: Limpieza apropiada y optimización de memoria

### 5. **Patrones Factory y Strategy**
- **Factory de configuración de placas**: Creación dinámica de parámetros
- **Strategy de procesamiento**: Múltiples tipos de filtros y algoritmos
- **Strategy de visualización**: UI adaptativa basada en capacidades del dispositivo
- **Strategy de detección de canales**: Reconocimiento inteligente de tipos

### 6. **Patrón Adapter**
- **Integración de framework**: Puentes Qt-servicio
- **Abstracción de hardware**: Integración de dispositivos BrainFlow
- **Adaptación de API**: Integración de sistemas externos
- **Compatibilidad multiplataforma**: Interfaces unificadas

## Características Clave del Sistema

### 1. **Soporte Extensivo de Hardware**
- **20+ fabricantes**: OpenBCI, g.tec, Muse, ANT Neuro, Neurosity, BrainBit, etc.
- **Colección de datos multi-preset**: Streams DEFAULT, AUXILIARY, ANCILLARY
- **Detección automática de dispositivos**: Mapeo de canales y configuración
- **Inserción de marcadores en tiempo real**: Sincronización de timestamp de microsegundo

### 2. **Procesamiento Avanzado de Señales**
- **Múltiples implementaciones de filtros**: Butterworth, Chebyshev, Bessel
- **Análisis wavelet**: 15+ familias wavelet con eliminación de ruido
- **Análisis de Componentes Independientes**: FastICA con 1-16 componentes
- **Procesamiento tiempo real**: Actualizaciones dinámicas de parámetros sin reinicio
- **Evaluación de calidad de señal**: Puntuación de 5 niveles con indicadores de rendimiento

### 3. **Integración MNE-Python**
- **Conversión de datos asíncrona**: Formato BrainFlow→MNE
- **Visualización avanzada**: PSD, espectrogramas, topomaps
- **Sesiones de procesamiento tiempo real**: Intervalos de actualización configurables
- **Soporte multiproceso**: Operaciones CPU-intensivas
- **Salida de calidad de publicación**: Gráficos de alta resolución (200 DPI)

### 4. **Capacidades Tiempo Real**
- **Actualizaciones de alta frecuencia**: Pipelines de renderizado de 50-100ms
- **Monitoreo de rendimiento**: Optimización de uso de CPU
- **Gestión adaptiva de timeout**: Basada en complejidad de procesamiento
- **Operaciones eficientes en memoria**: Gestión automática de buffer
- **Operaciones thread-safe**: Soporte de procesamiento concurrente

### 5. **Arquitectura Multi-Interfaz**
- **Qt5 GUI**: Interfaz basada en paneles con tema oscuro
- **CLI**: Shell interactivo con salida de consola Rich
- **REST API**: Streaming WebSocket con control HTTP
- **Multiplataforma**: Soporte Windows, Linux, macOS

### 6. **Características Educativas y de Investigación**
- **Sistema de ayuda integral**: 25+ temas con antecedentes teóricos
- **Orientación sensible al contexto**: Recomendaciones de parámetros
- **Complejidad progresiva**: Configuración básica → investigación avanzada
- **Integración de documentación**: Ayuda en línea con mejores prácticas

## Flujo de Datos Principal

```
1. Dispositivo Hardware → EEGCollector (BrainFlow) → Datos EEG en Bruto
2. Datos en Bruto → SignalProcessor → Datos Filtrados/Procesados
3. Datos Procesados → DataAccessService → Buffer Centralizado
4. Buffer → {Paneles UI, Monitor CLI, Streams API, Grabación}
5. Análisis Avanzado → {ICA, Wavelet, MNE} → Almacenamiento de Resultados
6. Actualizaciones Tiempo Real → {Señales Qt, WebSocket, Display CLI}
7. Sistema de Eventos → Coordinación Entre Componentes
```

## Casos de Uso Principales

### 1. **Investigación Neurocientífica**
- **Colección de datos EEG** con múltiples dispositivos
- **Análisis avanzado de señales** (ICA, wavelet, potencias de banda)
- **Procesamiento tiempo real** con integración MNE-Python
- **Visualización calidad publicación** con capacidades de exportación

### 2. **Interfaces Cerebro-Computadora**
- **Extracción de características tiempo real** con métricas de machine learning
- **Procesamiento baja latencia** para sistemas de retroalimentación
- **Análisis multi-canal** con optimización de rendimiento
- **Integración de sistemas externos** vía REST API

### 3. **Aplicaciones Clínicas**
- **Monitoreo de calidad de señal** con indicadores tiempo real
- **Detección de artefactos** mediante análisis ICA y wavelet
- **Grabación multi-formato** con inserción de marcadores
- **Registro integral** para documentación clínica

### 4. **Propósitos Educativos**
- **Exploración interactiva EEG** con sistema de ayuda
- **Aprendizaje de procesamiento de señales** con ajuste de parámetros tiempo real
- **Experiencia práctica** con múltiples dispositivos de hardware
- **Antecedentes teóricos** integrados con aplicación práctica

### 5. **Desarrollo y Pruebas**
- **Desarrollo de aplicaciones EEG** con acceso API
- **Pruebas de compatibilidad de hardware** entre fabricantes
- **Validación de algoritmos de procesamiento de señales** con conjuntos de datos conocidos
- **Benchmarking de rendimiento** con análisis multi-hilo

## Tecnologías y Dependencias

### Framework Central
- **Python 3.8+**: Tipado moderno y soporte asyncio
- **PyQt5**: Framework GUI profesional con apariencia nativa
- **BrainFlow**: Biblioteca multiplataforma para integración de dispositivos EEG
- **NumPy**: Operaciones de array optimizadas para procesamiento de señales

### Procesamiento de Señales
- **SciPy**: Funciones matemáticas avanzadas para filtrado
- **MNE-Python** (opcional): Capacidades de análisis neurofisiológico
- **Matplotlib**: Gráficos calidad publicación con integración de backend Qt
- **scikit-learn**: Componentes de machine learning para métricas cognitivas (usado en la librería MNE)

### CLI y API
- **Typer**: Framework CLI moderno con autocompletado
- **Rich**: Salida de consola avanzada con tablas y displays tiempo real
- **API Explorer**: Framework web para APIs documentadas
- **WebSocket**: Comunicación bidireccional tiempo real

### Concurrencia y Rendimiento
- **Threading**: Colección de datos y procesamiento en segundo plano
- **Multiprocessing**: Operaciones de análisis CPU-intensivas
- **Qt Signals/Slots**: Comunicación UI thread-safe
- **Asyncio**: Coordinación de operaciones asíncronas

### Desarrollo y Pruebas
- **Clases Base Abstractas**: Contratos de interfaz para modularidad
- **Anotaciones de tipo**: Tipado completo para asistencia de desarrollo
- **Inyección de dependencias**: Coordinación de servicios y soporte de pruebas
- **Compatibilidad multiplataforma**: Soporte Windows, Linux, macOS

## Arquitectura de Despliegue

```
Aplicación EEG Processor
├── Modo Aplicación GUI
│   ├── Interfaz completa de características
│   ├── Visualización tiempo real
│   ├── Paneles de análisis avanzado
│   └── Sistema de ayuda interactivo
├── Modo CLI
│   ├── Shell interactivo
│   ├── Operaciones scriptables
│   ├── Monitoreo tiempo real
│   └── Procesamiento sin cabeza
├── Modo Servidor API
│   ├── Endpoints REST
│   ├── Streaming WebSocket
│   ├── Integración externa
│   └── Interfaz de documentación
└── Modos Híbridos
    ├── GUI + API concurrente
    ├── Coordinación CLI + API
    ├── Capa de servicio compartida
    └── Limpieza coordinada
```

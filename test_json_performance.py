"""
Script para probar el rendimiento de la serialización JSON optimizada
"""

import time
import json
from typing import Dict, Any

# Intentar importar orjson
try:
    import orjson
    HAS_ORJSON = True
    print("✅ orjson instalado correctamente")
except ImportError:
    HAS_ORJSON = False
    print("❌ orjson no disponible")

def create_test_data(num_channels: int = 64) -> Dict[str, Any]:
    """Crear datos de prueba similares a los eventos reales."""
    return {
        "event_type": "sensor_data",
        "timestamp": time.time(),
        "visualization_data": {
            "list_view": [
                {
                    "channel": f"CH{i:02d}",
                    "type": "eeg",
                    "value": 123.456789 + i * 0.1
                }
                for i in range(num_channels)
            ]
        },
        "metadata": {
            "sampling_rate": 1000,
            "device_id": "test_device_001",
            "session_id": "session_12345"
        }
    }

def test_json_stdlib(data: Dict[str, Any], iterations: int = 1000) -> float:
    """Probar serialización con json estándar."""
    start_time = time.time()
    
    for _ in range(iterations):
        result = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    
    end_time = time.time()
    return end_time - start_time

def test_json_orjson(data: Dict[str, Any], iterations: int = 1000) -> float:
    """Probar serialización con orjson."""
    if not HAS_ORJSON:
        return 0
    
    start_time = time.time()
    
    for _ in range(iterations):
        result = orjson.dumps(data).decode()
    
    end_time = time.time()
    return end_time - start_time

def compare_output_sizes(data: Dict[str, Any]):
    """Comparar tamaños de salida."""
    json_std = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    json_pretty = json.dumps(data, indent=2)
    
    print(f"\n📊 Comparación de tamaños:")
    print(f"JSON estándar (compacto): {len(json_std)} bytes")
    print(f"JSON estándar (bonito):   {len(json_pretty)} bytes")
    
    if HAS_ORJSON:
        json_orjson = orjson.dumps(data).decode()
        print(f"orjson (compacto):        {len(json_orjson)} bytes")
        print(f"Diferencia vs estándar:   {len(json_std) - len(json_orjson)} bytes")

def main():
    print("🧪 Probando rendimiento de serialización JSON\n")
    
    # Crear datos de prueba
    test_channels = [8, 32, 64, 128]
    iterations = 1000
    
    for num_channels in test_channels:
        print(f"📡 Probando con {num_channels} canales ({iterations} iteraciones)")
        
        data = create_test_data(num_channels)
        
        # Probar json estándar
        time_stdlib = test_json_stdlib(data, iterations)
        
        # Probar orjson si está disponible
        time_orjson = test_json_orjson(data, iterations) if HAS_ORJSON else 0
        
        print(f"  JSON estándar: {time_stdlib:.4f}s ({iterations/time_stdlib:.0f} ops/sec)")
        
        if HAS_ORJSON and time_orjson > 0:
            speedup = time_stdlib / time_orjson
            print(f"  orjson:        {time_orjson:.4f}s ({iterations/time_orjson:.0f} ops/sec)")
            print(f"  🚀 Speedup:    {speedup:.1f}x más rápido")
        
        # Mostrar tamaños solo para el primer test
        if num_channels == test_channels[0]:
            compare_output_sizes(data)
        
        print()

if __name__ == "__main__":
    main()

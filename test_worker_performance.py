"""
Script para probar el rendimiento con y sin worker pools
"""

import asyncio
import time
import threading
from typing import Dict, Any, List
import random
import json

# Importar nuestras clases
from api_explorer.api_explorer import WebSocketManager, FastJSONSerializer

class MockWebSocket:
    """Mock WebSocket para pruebas."""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.messages_received = 0
        self.last_message_time = 0
        self.is_connected = True
    
    async def send_text(self, message: str):
        """Simular envío de mensaje."""
        self.messages_received += 1
        self.last_message_time = time.time()
        # Simular pequeña latencia de red
        await asyncio.sleep(0.0001)  # 0.1ms de latencia

class PerformanceTester:
    """Tester para comparar rendimiento con y sin workers."""
    
    def __init__(self):
        self.results = {}
        
    def create_test_data(self, channels: int = 64) -> Dict[str, Any]:
        """Crear datos de prueba realistas."""
        return {
            "event_type": "sensor_data_update",
            "timestamp": time.time(),
            "visualization_data": {
                "list_view": [
                    {
                        "channel": f"CH{i:02d}",
                        "type": "eeg",
                        "value": random.uniform(-100, 100)
                    }
                    for i in range(channels)
                ]
            },
            "device_id": "test_device_001",
            "session_id": "session_12345"
        }
    
    async def test_without_workers(self, num_events: int, num_connections: int, channels: int):
        """Probar rendimiento SIN worker pools (simulando el sistema anterior)."""
        print(f"\n🔧 Probando SIN workers: {num_events} eventos, {num_connections} conexiones, {channels} canales")
        
        # Crear conexiones mock
        connections = [MockWebSocket(f"conn_{i}") for i in range(num_connections)]
        serializer = FastJSONSerializer()
        
        # Estadísticas
        start_time = time.time()
        total_sent = 0
        
        # Simular envío secuencial (como era antes)
        for event_num in range(num_events):
            # Crear evento de prueba
            event_data = self.create_test_data(channels)
            
            # Serializar
            serialized = serializer.serialize_event(event_data, compact=True)
            
            # Enviar a todas las conexiones secuencialmente
            for conn in connections:
                await conn.send_text(serialized)
                total_sent += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Calcular estadísticas
        events_per_sec = num_events / duration
        messages_per_sec = total_sent / duration
        avg_latency = duration / num_events
        
        return {
            "mode": "without_workers",
            "duration": duration,
            "events_per_sec": events_per_sec,
            "messages_per_sec": messages_per_sec,
            "avg_latency_ms": avg_latency * 1000,
            "total_events": num_events,
            "total_messages": total_sent,
            "connections": num_connections,
            "channels": channels
        }
    
    async def test_with_workers(self, num_events: int, num_connections: int, channels: int):
        """Probar rendimiento CON worker pools."""
        print(f"\n⚡ Probando CON workers: {num_events} eventos, {num_connections} conexiones, {channels} canales")
        
        # Crear manager con workers
        manager = WebSocketManager()
        module_id = "test_module"
        
        # Crear conexiones mock
        connections = [MockWebSocket(f"conn_{i}") for i in range(num_connections)]
        
        # Agregar conexiones al manager
        for conn in connections:
            await manager.add_connection(module_id, conn)
        
        # Estadísticas
        start_time = time.time()
        messages_queued = 0
        
        # Enviar eventos usando worker pool
        for event_num in range(num_events):
            # Crear evento de prueba
            event_data = self.create_test_data(channels)
            
            # Serializar
            serialized = manager.json_serializer.serialize_event(event_data, compact=True)
            
            # Queue para workers
            success = manager.queue_message(module_id, serialized)
            if success:
                messages_queued += 1
        
        # Esperar a que los workers procesen todo
        await asyncio.sleep(0.1)  # Dar tiempo inicial
        
        max_wait_time = 30  # máximo 30 segundos
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait_time:
            stats = manager.get_module_stats(module_id)
            if stats and stats["total_queue_size"] == 0:
                break
            await asyncio.sleep(0.01)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Obtener estadísticas de workers
        worker_stats = manager.get_module_stats(module_id)
        
        # Cleanup
        for conn in connections:
            await manager.remove_connection(module_id, conn)
        
        # Calcular estadísticas finales
        events_per_sec = num_events / duration
        messages_per_sec = messages_queued / duration
        avg_latency = duration / num_events
        
        return {
            "mode": "with_workers",
            "duration": duration,
            "events_per_sec": events_per_sec,
            "messages_per_sec": messages_per_sec,
            "avg_latency_ms": avg_latency * 1000,
            "total_events": num_events,
            "total_messages": messages_queued,
            "connections": num_connections,
            "channels": channels,
            "worker_stats": worker_stats
        }
    
    async def run_comparison_test(self, 
                                 events: int = 1000,  # Cambié de num_events a events
                                 connections: int = 5,  # Cambié de num_connections a connections  
                                 channels: int = 64):
        """Ejecutar test comparativo."""
        print(f"🚀 Iniciando test comparativo de rendimiento")
        print(f"   Eventos: {events}")
        print(f"   Conexiones: {connections}")
        print(f"   Canales por evento: {channels}")
        print("=" * 60)
        
        # Test sin workers
        result_without = await self.test_without_workers(events, connections, channels)
        
        # Pequeña pausa entre tests
        await asyncio.sleep(1)
        
        # Test con workers
        result_with = await self.test_with_workers(events, connections, channels)
        
        # Comparar resultados
        self.compare_results(result_without, result_with)
        
        return result_without, result_with
    
    def compare_results(self, without_workers: Dict, with_workers: Dict):
        """Comparar y mostrar resultados."""
        print("\n" + "=" * 60)
        print("📊 RESULTADOS DE RENDIMIENTO")
        print("=" * 60)
        
        # Mostrar resultados individuales
        print(f"\n🔧 SIN Workers:")
        print(f"   Duración: {without_workers['duration']:.3f}s")
        print(f"   Eventos/seg: {without_workers['events_per_sec']:.0f}")
        print(f"   Mensajes/seg: {without_workers['messages_per_sec']:.0f}")
        print(f"   Latencia promedio: {without_workers['avg_latency_ms']:.2f}ms")
        
        print(f"\n⚡ CON Workers:")
        print(f"   Duración: {with_workers['duration']:.3f}s")
        print(f"   Eventos/seg: {with_workers['events_per_sec']:.0f}")
        print(f"   Mensajes/seg: {with_workers['messages_per_sec']:.0f}")
        print(f"   Latencia promedio: {with_workers['avg_latency_ms']:.2f}ms")
        
        if 'worker_stats' in with_workers and with_workers['worker_stats']:
            stats = with_workers['worker_stats']
            print(f"   Workers activos: {stats['pool_size']}")
            print(f"   Mensajes procesados: {stats['total_messages_processed']}")
            print(f"   Cola promedio: {stats['avg_queue_size']:.1f}")
        
        # Calcular mejoras
        if without_workers['events_per_sec'] > 0:
            speed_improvement = with_workers['events_per_sec'] / without_workers['events_per_sec']
            latency_improvement = without_workers['avg_latency_ms'] / with_workers['avg_latency_ms'] if with_workers['avg_latency_ms'] > 0 else 1
            
            print(f"\n🚀 MEJORAS:")
            print(f"   Velocidad: {speed_improvement:.1f}x más rápido")
            print(f"   Latencia: {latency_improvement:.1f}x mejor")
            
            if speed_improvement > 1.2:
                print("   ✅ Mejora significativa con workers!")
            elif speed_improvement > 1.05:
                print("   ⚡ Mejora moderada con workers")
            else:
                print("   ⚠️  Mejora mínima o no detectada")
        else:
            print("   ⚠️  No se pudo calcular mejora (división por cero)")
        
        print("=" * 60)

async def main():
    """Función principal para ejecutar los tests."""
    tester = PerformanceTester()
    
    print("🧪 TEST DE RENDIMIENTO: Workers vs Sin Workers\n")
    
    # Tests con diferentes cargas
    test_scenarios = [
        {"events": 500, "connections": 2, "channels": 32},    # Carga baja
        {"events": 1000, "connections": 5, "channels": 64},   # Carga media
        {"events": 2000, "connections": 10, "channels": 128}, # Carga alta
    ]
    
    all_results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*20} ESCENARIO {i} {'='*20}")
        
        try:
            result_without, result_with = await tester.run_comparison_test(**scenario)
            all_results.append((result_without, result_with))
        except Exception as e:
            print(f"❌ Error en escenario {i}: {e}")
            continue
        
        # Pausa entre escenarios
        if i < len(test_scenarios):
            print(f"\nEsperando antes del siguiente test...")
            await asyncio.sleep(2)
    
    # Resumen final solo si tenemos resultados
    if all_results:
        print(f"\n{'='*60}")
        print("📈 RESUMEN FINAL")
        print("="*60)
        
        for i, (without, with_workers) in enumerate(all_results, 1):
            if without['events_per_sec'] > 0:
                speedup = with_workers['events_per_sec'] / without['events_per_sec']
                print(f"Escenario {i}: {speedup:.1f}x mejora con workers")
        
        avg_speedup = sum(
            with_w['events_per_sec'] / without_w['events_per_sec'] 
            for without_w, with_w in all_results
            if without_w['events_per_sec'] > 0
        ) / len(all_results)
        
        print(f"Mejora promedio: {avg_speedup:.1f}x")
        
        if avg_speedup > 2:
            print("🚀 ¡Excelente! Los workers proporcionan una mejora significativa")
        elif avg_speedup > 1.5:
            print("⚡ Buena mejora con workers")
        elif avg_speedup > 1.1:
            print("✅ Mejora moderada con workers")
        else:
            print("⚠️  Mejora mínima detectada")
    else:
        print("❌ No se completaron tests exitosamente")

if __name__ == "__main__":
    asyncio.run(main())

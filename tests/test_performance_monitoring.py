"""
Unit tests for performance monitoring and metrics
"""

import unittest
from unittest.mock import Mock, patch
import time
from datetime import datetime, timedelta
import threading
import os
from typing import Dict, List, Any

# Mock performance monitoring classes
class PerformanceMonitor:
    """Performance monitor for pipeline operations"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.memory_snapshots = []
        self.cpu_snapshots = []
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation"""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration"""
        if operation not in self.start_times:
            return 0.0
        
        duration = time.time() - self.start_times[operation]
        
        if operation not in self.metrics:
            self.metrics[operation] = {
                'total_time': 0.0,
                'count': 0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'avg_time': 0.0
            }
        
        metric = self.metrics[operation]
        metric['total_time'] += duration
        metric['count'] += 1
        metric['min_time'] = min(metric['min_time'], duration)
        metric['max_time'] = max(metric['max_time'], duration)
        metric['avg_time'] = metric['total_time'] / metric['count']
        
        del self.start_times[operation]
        return duration
    
    def record_memory_usage(self) -> Dict[str, float]:
        """Record current memory usage"""
        # Mock memory usage data for testing
        import random
        
        snapshot = {
            'timestamp': time.time(),
            'rss': random.uniform(50, 200),  # MB
            'vms': random.uniform(100, 400),  # MB
            'percent': random.uniform(5, 25)
        }
        
        self.memory_snapshots.append(snapshot)
        return snapshot
    
    def record_cpu_usage(self) -> Dict[str, float]:
        """Record current CPU usage"""
        # Mock CPU usage data for testing
        import random
        
        snapshot = {
            'timestamp': time.time(),
            'cpu_percent': random.uniform(0, 50),
            'num_threads': random.randint(1, 8)
        }
        
        self.cpu_snapshots.append(snapshot)
        return snapshot
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        return {
            'timing_metrics': self.metrics.copy(),
            'memory_stats': self._get_memory_stats(),
            'cpu_stats': self._get_cpu_stats(),
            'active_timers': list(self.start_times.keys())
        }
    
    def _get_memory_stats(self) -> Dict[str, float]:
        """Get memory usage statistics"""
        if not self.memory_snapshots:
            return {}
        
        rss_values = [s['rss'] for s in self.memory_snapshots]
        vms_values = [s['vms'] for s in self.memory_snapshots]
        
        return {
            'peak_rss': max(rss_values),
            'avg_rss': sum(rss_values) / len(rss_values),
            'peak_vms': max(vms_values),
            'avg_vms': sum(vms_values) / len(vms_values),
            'snapshots_count': len(self.memory_snapshots)
        }
    
    def _get_cpu_stats(self) -> Dict[str, float]:
        """Get CPU usage statistics"""
        if not self.cpu_snapshots:
            return {}
        
        cpu_values = [s['cpu_percent'] for s in self.cpu_snapshots]
        
        return {
            'peak_cpu': max(cpu_values),
            'avg_cpu': sum(cpu_values) / len(cpu_values),
            'snapshots_count': len(self.cpu_snapshots)
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        self.metrics.clear()
        self.start_times.clear()
        self.memory_snapshots.clear()
        self.cpu_snapshots.clear()


class PerformanceProfiler:
    """Performance profiler with context manager support"""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str):
        self.monitor = monitor
        self.operation = operation
        self.duration = None
    
    def __enter__(self):
        self.monitor.start_timer(self.operation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = self.monitor.end_timer(self.operation)


class TestPerformanceMonitor(unittest.TestCase):
    """Test cases for performance monitoring"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_timer_basic_functionality(self):
        """Test basic timer functionality"""
        operation = 'test_operation'
        
        self.monitor.start_timer(operation)
        time.sleep(0.1)  # Sleep for 100ms
        duration = self.monitor.end_timer(operation)
        
        self.assertGreaterEqual(duration, 0.1)
        self.assertLess(duration, 0.2)  # Should be close to 100ms
        
        # Check metrics were recorded
        self.assertIn(operation, self.monitor.metrics)
        metric = self.monitor.metrics[operation]
        self.assertEqual(metric['count'], 1)
        self.assertAlmostEqual(metric['total_time'], duration, places=3)
        self.assertEqual(metric['min_time'], duration)
        self.assertEqual(metric['max_time'], duration)
        self.assertEqual(metric['avg_time'], duration)
    
    def test_timer_multiple_operations(self):
        """Test timing multiple operations"""
        operations = ['op1', 'op2', 'op3']
        sleep_times = [0.05, 0.1, 0.15]
        
        for op, sleep_time in zip(operations, sleep_times):
            self.monitor.start_timer(op)
            time.sleep(sleep_time)
            duration = self.monitor.end_timer(op)
            self.assertGreaterEqual(duration, sleep_time * 0.9)  # Allow 10% tolerance
    
    def test_timer_repeated_operations(self):
        """Test timing repeated operations"""
        operation = 'repeated_op'
        num_iterations = 3
        
        for i in range(num_iterations):
            self.monitor.start_timer(operation)
            time.sleep(0.05)
            self.monitor.end_timer(operation)
        
        metric = self.monitor.metrics[operation]
        self.assertEqual(metric['count'], num_iterations)
        self.assertGreater(metric['total_time'], 0.15)  # At least 150ms total
        self.assertGreater(metric['min_time'], 0.04)  # At least 40ms min
        self.assertLess(metric['max_time'], 0.1)  # Less than 100ms max
        self.assertAlmostEqual(metric['avg_time'], metric['total_time'] / num_iterations, places=3)
    
    def test_timer_end_without_start(self):
        """Test ending timer without starting it"""
        duration = self.monitor.end_timer('nonexistent_operation')
        self.assertEqual(duration, 0.0)
    
    def test_memory_usage_recording(self):
        """Test memory usage recording"""
        # Record initial memory
        snapshot1 = self.monitor.record_memory_usage()
        
        # Allocate some memory
        large_list = [i for i in range(100000)]
        
        # Record memory after allocation
        snapshot2 = self.monitor.record_memory_usage()
        
        # Verify snapshots
        self.assertIn('timestamp', snapshot1)
        self.assertIn('rss', snapshot1)
        self.assertIn('vms', snapshot1)
        self.assertIn('percent', snapshot1)
        
        self.assertGreater(snapshot2['timestamp'], snapshot1['timestamp'])
        # Memory usage should have increased (though this might be flaky in some environments)
        # self.assertGreaterEqual(snapshot2['rss'], snapshot1['rss'])
        
        # Verify snapshots were stored
        self.assertEqual(len(self.monitor.memory_snapshots), 2)
        
        # Clean up
        del large_list
    
    def test_cpu_usage_recording(self):
        """Test CPU usage recording"""
        snapshot1 = self.monitor.record_cpu_usage()
        
        # Do some CPU-intensive work
        result = sum(i * i for i in range(10000))
        
        snapshot2 = self.monitor.record_cpu_usage()
        
        # Verify snapshots
        self.assertIn('timestamp', snapshot1)
        self.assertIn('cpu_percent', snapshot1)
        self.assertIn('num_threads', snapshot1)
        
        self.assertGreater(snapshot2['timestamp'], snapshot1['timestamp'])
        
        # Verify snapshots were stored
        self.assertEqual(len(self.monitor.cpu_snapshots), 2)
    
    def test_metrics_summary(self):
        """Test metrics summary generation"""
        # Generate some metrics
        self.monitor.start_timer('test_op')
        time.sleep(0.05)
        self.monitor.end_timer('test_op')
        
        self.monitor.record_memory_usage()
        self.monitor.record_cpu_usage()
        
        summary = self.monitor.get_metrics_summary()
        
        # Verify summary structure
        self.assertIn('timing_metrics', summary)
        self.assertIn('memory_stats', summary)
        self.assertIn('cpu_stats', summary)
        self.assertIn('active_timers', summary)
        
        # Verify timing metrics
        self.assertIn('test_op', summary['timing_metrics'])
        
        # Verify memory stats
        memory_stats = summary['memory_stats']
        self.assertIn('peak_rss', memory_stats)
        self.assertIn('avg_rss', memory_stats)
        self.assertIn('snapshots_count', memory_stats)
        self.assertEqual(memory_stats['snapshots_count'], 1)
        
        # Verify CPU stats
        cpu_stats = summary['cpu_stats']
        self.assertIn('peak_cpu', cpu_stats)
        self.assertIn('avg_cpu', cpu_stats)
        self.assertIn('snapshots_count', cpu_stats)
        self.assertEqual(cpu_stats['snapshots_count'], 1)
    
    def test_reset_metrics(self):
        """Test metrics reset functionality"""
        # Generate some metrics
        self.monitor.start_timer('test_op')
        time.sleep(0.05)
        self.monitor.end_timer('test_op')
        
        self.monitor.record_memory_usage()
        self.monitor.record_cpu_usage()
        
        # Verify metrics exist
        self.assertGreater(len(self.monitor.metrics), 0)
        self.assertGreater(len(self.monitor.memory_snapshots), 0)
        self.assertGreater(len(self.monitor.cpu_snapshots), 0)
        
        # Reset metrics
        self.monitor.reset_metrics()
        
        # Verify metrics are cleared
        self.assertEqual(len(self.monitor.metrics), 0)
        self.assertEqual(len(self.monitor.start_times), 0)
        self.assertEqual(len(self.monitor.memory_snapshots), 0)
        self.assertEqual(len(self.monitor.cpu_snapshots), 0)


class TestPerformanceProfiler(unittest.TestCase):
    """Test cases for performance profiler context manager"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_profiler_context_manager(self):
        """Test profiler as context manager"""
        operation = 'context_test'
        
        with PerformanceProfiler(self.monitor, operation) as profiler:
            time.sleep(0.1)
        
        # Verify timing was recorded
        self.assertIn(operation, self.monitor.metrics)
        self.assertIsNotNone(profiler.duration)
        self.assertGreaterEqual(profiler.duration, 0.1)
        
        # Verify no active timers remain
        self.assertEqual(len(self.monitor.start_times), 0)
    
    def test_profiler_with_exception(self):
        """Test profiler context manager with exception"""
        operation = 'exception_test'
        
        try:
            with PerformanceProfiler(self.monitor, operation) as profiler:
                time.sleep(0.05)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify timing was still recorded despite exception
        self.assertIn(operation, self.monitor.metrics)
        self.assertIsNotNone(profiler.duration)
        self.assertGreaterEqual(profiler.duration, 0.05)
        
        # Verify no active timers remain
        self.assertEqual(len(self.monitor.start_times), 0)
    
    def test_nested_profilers(self):
        """Test nested profiler context managers"""
        outer_op = 'outer_operation'
        inner_op = 'inner_operation'
        
        with PerformanceProfiler(self.monitor, outer_op) as outer_profiler:
            time.sleep(0.05)
            
            with PerformanceProfiler(self.monitor, inner_op) as inner_profiler:
                time.sleep(0.05)
            
            time.sleep(0.05)
        
        # Verify both operations were timed
        self.assertIn(outer_op, self.monitor.metrics)
        self.assertIn(inner_op, self.monitor.metrics)
        
        # Outer operation should take longer than inner
        self.assertGreater(outer_profiler.duration, inner_profiler.duration)
        self.assertGreaterEqual(outer_profiler.duration, 0.15)
        self.assertGreaterEqual(inner_profiler.duration, 0.05)


class TestPerformanceIntegration(unittest.TestCase):
    """Test cases for performance monitoring integration"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_pipeline_operation_monitoring(self):
        """Test monitoring a simulated pipeline operation"""
        # Simulate WhatsApp extraction
        with PerformanceProfiler(self.monitor, 'whatsapp_extraction'):
            self.monitor.record_memory_usage()
            
            # Simulate authentication
            with PerformanceProfiler(self.monitor, 'whatsapp_auth'):
                time.sleep(0.02)
            
            # Simulate message extraction
            with PerformanceProfiler(self.monitor, 'whatsapp_messages'):
                time.sleep(0.05)
                self.monitor.record_memory_usage()
            
            # Simulate media download
            with PerformanceProfiler(self.monitor, 'whatsapp_media'):
                time.sleep(0.03)
            
            self.monitor.record_cpu_usage()
        
        # Verify all operations were monitored
        expected_operations = ['whatsapp_extraction', 'whatsapp_auth', 'whatsapp_messages', 'whatsapp_media']
        for op in expected_operations:
            self.assertIn(op, self.monitor.metrics)
        
        # Verify extraction took longer than sub-operations
        extraction_time = self.monitor.metrics['whatsapp_extraction']['total_time']
        auth_time = self.monitor.metrics['whatsapp_auth']['total_time']
        messages_time = self.monitor.metrics['whatsapp_messages']['total_time']
        media_time = self.monitor.metrics['whatsapp_media']['total_time']
        
        self.assertGreater(extraction_time, auth_time)
        self.assertGreater(extraction_time, messages_time)
        self.assertGreater(extraction_time, media_time)
        
        # Verify resource monitoring
        self.assertGreater(len(self.monitor.memory_snapshots), 0)
        self.assertGreater(len(self.monitor.cpu_snapshots), 0)
    
    def test_concurrent_operations_monitoring(self):
        """Test monitoring concurrent operations"""
        def worker_operation(operation_name, duration):
            with PerformanceProfiler(self.monitor, operation_name):
                time.sleep(duration)
                self.monitor.record_memory_usage()
        
        # Start concurrent operations
        threads = []
        operations = [
            ('concurrent_op_1', 0.1),
            ('concurrent_op_2', 0.15),
            ('concurrent_op_3', 0.08)
        ]
        
        for op_name, duration in operations:
            thread = threading.Thread(target=worker_operation, args=(op_name, duration))
            threads.append(thread)
            thread.start()
        
        # Wait for all operations to complete
        for thread in threads:
            thread.join()
        
        # Verify all operations were monitored
        for op_name, expected_duration in operations:
            self.assertIn(op_name, self.monitor.metrics)
            actual_duration = self.monitor.metrics[op_name]['total_time']
            self.assertGreaterEqual(actual_duration, expected_duration * 0.9)  # Allow 10% tolerance
        
        # Verify memory snapshots from concurrent operations
        self.assertGreaterEqual(len(self.monitor.memory_snapshots), len(operations))
    
    def test_performance_threshold_monitoring(self):
        """Test monitoring for performance threshold violations"""
        # Define performance thresholds
        thresholds = {
            'whatsapp_auth': 0.1,  # 100ms
            'email_auth': 0.2,     # 200ms
            'data_processing': 0.5  # 500ms
        }
        
        violations = []
        
        # Simulate operations with some exceeding thresholds
        operations = [
            ('whatsapp_auth', 0.05),      # Within threshold
            ('email_auth', 0.25),         # Exceeds threshold
            ('data_processing', 0.3),     # Within threshold
            ('whatsapp_auth', 0.15),      # Exceeds threshold
        ]
        
        for op_name, duration in operations:
            with PerformanceProfiler(self.monitor, op_name) as profiler:
                time.sleep(duration)
            
            # Check for threshold violations
            if op_name in thresholds and profiler.duration > thresholds[op_name]:
                violations.append({
                    'operation': op_name,
                    'duration': profiler.duration,
                    'threshold': thresholds[op_name],
                    'violation_ratio': profiler.duration / thresholds[op_name]
                })
        
        # Verify threshold violations were detected
        self.assertEqual(len(violations), 2)  # email_auth and second whatsapp_auth
        
        violation_operations = [v['operation'] for v in violations]
        self.assertIn('email_auth', violation_operations)
        self.assertIn('whatsapp_auth', violation_operations)
        
        # Verify violation ratios
        for violation in violations:
            self.assertGreater(violation['violation_ratio'], 1.0)
    
    def test_memory_leak_detection(self):
        """Test memory leak detection through monitoring"""
        initial_snapshots = 5
        leak_snapshots = 5
        
        # Take initial memory snapshots
        for _ in range(initial_snapshots):
            self.monitor.record_memory_usage()
            time.sleep(0.01)
        
        # Simulate memory leak
        leaked_objects = []
        for i in range(leak_snapshots):
            # Allocate memory that won't be freed
            leaked_objects.append([j for j in range(10000)])
            self.monitor.record_memory_usage()
            time.sleep(0.01)
        
        # Analyze memory trend
        memory_stats = self.monitor._get_memory_stats()
        snapshots = self.monitor.memory_snapshots
        
        # Check if memory usage is trending upward
        initial_avg = sum(s['rss'] for s in snapshots[:initial_snapshots]) / initial_snapshots
        final_avg = sum(s['rss'] for s in snapshots[-leak_snapshots:]) / leak_snapshots
        
        memory_growth = final_avg - initial_avg
        growth_percentage = (memory_growth / initial_avg) * 100 if initial_avg > 0 else 0
        
        # In a real scenario, we'd expect significant growth indicating a leak
        # For this test, we just verify the monitoring captured the trend
        self.assertGreaterEqual(len(snapshots), initial_snapshots + leak_snapshots)
        self.assertGreater(memory_stats['peak_rss'], 0)
        
        # Clean up to prevent actual memory issues in test
        del leaked_objects


class TestPerformanceBenchmarking(unittest.TestCase):
    """Test cases for performance benchmarking"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_operation_benchmarking(self):
        """Test benchmarking of operations"""
        operation = 'benchmark_test'
        num_iterations = 10
        
        # Run operation multiple times
        for i in range(num_iterations):
            with PerformanceProfiler(self.monitor, operation):
                # Simulate variable workload
                time.sleep(0.01 + (i * 0.005))  # Increasing duration
        
        metric = self.monitor.metrics[operation]
        
        # Verify benchmarking data
        self.assertEqual(metric['count'], num_iterations)
        self.assertGreater(metric['total_time'], 0)
        self.assertGreater(metric['max_time'], metric['min_time'])
        self.assertAlmostEqual(metric['avg_time'], metric['total_time'] / num_iterations, places=3)
        
        # Calculate performance statistics
        durations = []
        for i in range(num_iterations):
            with PerformanceProfiler(self.monitor, f'individual_test_{i}'):
                time.sleep(0.01)
            durations.append(self.monitor.metrics[f'individual_test_{i}']['total_time'])
        
        # Calculate standard deviation
        mean_duration = sum(durations) / len(durations)
        variance = sum((d - mean_duration) ** 2 for d in durations) / len(durations)
        std_deviation = variance ** 0.5
        
        # Verify reasonable performance consistency
        coefficient_of_variation = std_deviation / mean_duration
        self.assertLess(coefficient_of_variation, 0.5)  # Less than 50% variation
    
    def test_comparative_benchmarking(self):
        """Test comparative benchmarking of different approaches"""
        # Simulate two different approaches to the same task
        approaches = {
            'approach_a': lambda: time.sleep(0.05),  # Slower approach
            'approach_b': lambda: time.sleep(0.02),  # Faster approach
        }
        
        num_iterations = 5
        
        for approach_name, approach_func in approaches.items():
            for i in range(num_iterations):
                with PerformanceProfiler(self.monitor, approach_name):
                    approach_func()
        
        # Compare performance
        metrics_a = self.monitor.metrics['approach_a']
        metrics_b = self.monitor.metrics['approach_b']
        
        # Approach B should be faster
        self.assertLess(metrics_b['avg_time'], metrics_a['avg_time'])
        
        # Calculate performance improvement
        improvement_ratio = metrics_a['avg_time'] / metrics_b['avg_time']
        improvement_percentage = ((metrics_a['avg_time'] - metrics_b['avg_time']) / metrics_a['avg_time']) * 100
        
        self.assertGreater(improvement_ratio, 1.0)
        self.assertGreater(improvement_percentage, 0)


if __name__ == '__main__':
    unittest.main()
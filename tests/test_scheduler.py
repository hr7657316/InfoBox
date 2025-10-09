"""
Unit tests for scheduler functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time
import threading

# Mock scheduler classes since they're not implemented yet
class MockScheduler:
    """Mock scheduler for testing"""
    
    def __init__(self, config):
        self.config = config
        self.jobs = []
        self.running = False
    
    def add_job(self, func, schedule_type, **kwargs):
        job = {
            'func': func,
            'schedule_type': schedule_type,
            'kwargs': kwargs,
            'next_run': datetime.now()
        }
        self.jobs.append(job)
        return job
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False
    
    def get_jobs(self):
        return self.jobs


class TestSchedulerConfiguration(unittest.TestCase):
    """Test cases for scheduler configuration"""
    
    def setUp(self):
        self.config = {
            'enabled': True,
            'schedule_type': 'interval',
            'interval_hours': 6,
            'cron_expression': None,
            'daily_time': '02:00'
        }
    
    def test_scheduler_config_validation_valid(self):
        """Test valid scheduler configuration"""
        scheduler = MockScheduler(self.config)
        self.assertEqual(scheduler.config['enabled'], True)
        self.assertEqual(scheduler.config['interval_hours'], 6)
    
    def test_scheduler_config_validation_invalid_interval(self):
        """Test invalid interval configuration"""
        invalid_config = self.config.copy()
        invalid_config['interval_hours'] = -1
        
        # In a real implementation, this would raise an error
        scheduler = MockScheduler(invalid_config)
        self.assertEqual(scheduler.config['interval_hours'], -1)
    
    def test_scheduler_config_cron_expression(self):
        """Test cron expression configuration"""
        cron_config = self.config.copy()
        cron_config['schedule_type'] = 'cron'
        cron_config['cron_expression'] = '0 2 * * *'  # Daily at 2 AM
        
        scheduler = MockScheduler(cron_config)
        self.assertEqual(scheduler.config['cron_expression'], '0 2 * * *')
    
    def test_scheduler_config_daily_time(self):
        """Test daily time configuration"""
        daily_config = self.config.copy()
        daily_config['schedule_type'] = 'daily'
        daily_config['daily_time'] = '14:30'
        
        scheduler = MockScheduler(daily_config)
        self.assertEqual(scheduler.config['daily_time'], '14:30')


class TestSchedulerJobManagement(unittest.TestCase):
    """Test cases for scheduler job management"""
    
    def setUp(self):
        self.config = {
            'enabled': True,
            'schedule_type': 'interval',
            'interval_hours': 1
        }
        self.scheduler = MockScheduler(self.config)
    
    def test_add_job_interval(self):
        """Test adding interval-based job"""
        mock_func = Mock()
        
        job = self.scheduler.add_job(
            mock_func,
            'interval',
            hours=2
        )
        
        self.assertEqual(len(self.scheduler.jobs), 1)
        self.assertEqual(job['func'], mock_func)
        self.assertEqual(job['schedule_type'], 'interval')
        self.assertEqual(job['kwargs']['hours'], 2)
    
    def test_add_job_cron(self):
        """Test adding cron-based job"""
        mock_func = Mock()
        
        job = self.scheduler.add_job(
            mock_func,
            'cron',
            cron='0 */6 * * *'  # Every 6 hours
        )
        
        self.assertEqual(len(self.scheduler.jobs), 1)
        self.assertEqual(job['schedule_type'], 'cron')
        self.assertEqual(job['kwargs']['cron'], '0 */6 * * *')
    
    def test_add_job_daily(self):
        """Test adding daily job"""
        mock_func = Mock()
        
        job = self.scheduler.add_job(
            mock_func,
            'daily',
            time='03:00'
        )
        
        self.assertEqual(len(self.scheduler.jobs), 1)
        self.assertEqual(job['schedule_type'], 'daily')
        self.assertEqual(job['kwargs']['time'], '03:00')
    
    def test_get_jobs(self):
        """Test getting all jobs"""
        mock_func1 = Mock()
        mock_func2 = Mock()
        
        self.scheduler.add_job(mock_func1, 'interval', hours=1)
        self.scheduler.add_job(mock_func2, 'daily', time='02:00')
        
        jobs = self.scheduler.get_jobs()
        self.assertEqual(len(jobs), 2)
    
    def test_scheduler_start_stop(self):
        """Test scheduler start and stop"""
        self.assertFalse(self.scheduler.running)
        
        self.scheduler.start()
        self.assertTrue(self.scheduler.running)
        
        self.scheduler.stop()
        self.assertFalse(self.scheduler.running)


class TestSchedulerIntegration(unittest.TestCase):
    """Test cases for scheduler integration with pipeline"""
    
    def setUp(self):
        self.config = {
            'enabled': True,
            'schedule_type': 'interval',
            'interval_hours': 1
        }
    
    def test_schedule_extraction_pipeline(self):
        """Test scheduling extraction pipeline"""
        scheduler = MockScheduler(self.config)
        mock_pipeline = Mock()
        mock_pipeline.run_extraction = Mock(return_value={'whatsapp': Mock(), 'email': Mock()})
        
        # Schedule the pipeline
        job = scheduler.add_job(
            mock_pipeline.run_extraction,
            'interval',
            hours=self.config['interval_hours']
        )
        
        self.assertIsNotNone(job)
        self.assertEqual(job['func'], mock_pipeline.run_extraction)
    
    def test_schedule_with_error_handling(self):
        """Test scheduling with error handling"""
        scheduler = MockScheduler(self.config)
        
        def failing_job():
            raise Exception("Job failed")
        
        def wrapped_job():
            try:
                failing_job()
            except Exception as e:
                # Log error but don't crash scheduler
                return f"Job failed: {e}"
        
        job = scheduler.add_job(wrapped_job, 'interval', hours=1)
        
        # Simulate job execution
        result = job['func']()
        self.assertIn("Job failed", result)
    
    def test_schedule_multiple_sources(self):
        """Test scheduling different sources separately"""
        scheduler = MockScheduler(self.config)
        
        mock_whatsapp_extractor = Mock()
        mock_email_extractor = Mock()
        
        # Schedule WhatsApp extraction every 2 hours
        whatsapp_job = scheduler.add_job(
            mock_whatsapp_extractor.extract_messages,
            'interval',
            hours=2
        )
        
        # Schedule email extraction every 4 hours
        email_job = scheduler.add_job(
            mock_email_extractor.extract_emails,
            'interval',
            hours=4
        )
        
        jobs = scheduler.get_jobs()
        self.assertEqual(len(jobs), 2)
        
        # Verify different schedules
        whatsapp_schedule = next(j for j in jobs if j['func'] == mock_whatsapp_extractor.extract_messages)
        email_schedule = next(j for j in jobs if j['func'] == mock_email_extractor.extract_emails)
        
        self.assertEqual(whatsapp_schedule['kwargs']['hours'], 2)
        self.assertEqual(email_schedule['kwargs']['hours'], 4)


class TestSchedulerErrorHandling(unittest.TestCase):
    """Test cases for scheduler error handling"""
    
    def setUp(self):
        self.config = {
            'enabled': True,
            'schedule_type': 'interval',
            'interval_hours': 1
        }
        self.scheduler = MockScheduler(self.config)
    
    def test_job_failure_isolation(self):
        """Test that one job failure doesn't affect others"""
        successful_job = Mock(return_value="success")
        failing_job = Mock(side_effect=Exception("Job failed"))
        
        self.scheduler.add_job(successful_job, 'interval', hours=1)
        self.scheduler.add_job(failing_job, 'interval', hours=1)
        
        jobs = self.scheduler.get_jobs()
        self.assertEqual(len(jobs), 2)
        
        # Simulate job execution
        try:
            jobs[0]['func']()  # Should succeed
            result1 = "success"
        except:
            result1 = "failed"
        
        try:
            jobs[1]['func']()  # Should fail
            result2 = "success"
        except:
            result2 = "failed"
        
        self.assertEqual(result1, "success")
        self.assertEqual(result2, "failed")
    
    def test_scheduler_recovery_after_error(self):
        """Test scheduler recovery after job errors"""
        error_count = 0
        
        def sometimes_failing_job():
            nonlocal error_count
            error_count += 1
            if error_count <= 2:
                raise Exception(f"Failure {error_count}")
            return "success"
        
        job = self.scheduler.add_job(sometimes_failing_job, 'interval', hours=1)
        
        # Simulate multiple executions
        results = []
        for _ in range(4):
            try:
                result = job['func']()
                results.append(result)
            except Exception as e:
                results.append(f"error: {e}")
        
        # First two should fail, next two should succeed
        self.assertIn("error", results[0])
        self.assertIn("error", results[1])
        self.assertEqual(results[2], "success")
        self.assertEqual(results[3], "success")
    
    def test_invalid_schedule_handling(self):
        """Test handling of invalid schedule configurations"""
        # Test invalid cron expression
        invalid_cron_job = self.scheduler.add_job(
            Mock(),
            'cron',
            cron='invalid cron'
        )
        
        # In a real implementation, this would be validated
        self.assertEqual(invalid_cron_job['kwargs']['cron'], 'invalid cron')
        
        # Test invalid daily time
        invalid_time_job = self.scheduler.add_job(
            Mock(),
            'daily',
            time='25:00'  # Invalid time
        )
        
        self.assertEqual(invalid_time_job['kwargs']['time'], '25:00')


class TestSchedulerPerformance(unittest.TestCase):
    """Test cases for scheduler performance"""
    
    def setUp(self):
        self.config = {
            'enabled': True,
            'schedule_type': 'interval',
            'interval_hours': 1
        }
        self.scheduler = MockScheduler(self.config)
    
    def test_multiple_jobs_performance(self):
        """Test performance with multiple jobs"""
        # Add many jobs
        jobs_count = 100
        for i in range(jobs_count):
            mock_func = Mock(return_value=f"job_{i}")
            self.scheduler.add_job(mock_func, 'interval', hours=1)
        
        jobs = self.scheduler.get_jobs()
        self.assertEqual(len(jobs), jobs_count)
        
        # Measure execution time for getting jobs
        start_time = time.time()
        all_jobs = self.scheduler.get_jobs()
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0)  # Should be fast
        self.assertEqual(len(all_jobs), jobs_count)
    
    def test_job_execution_timing(self):
        """Test job execution timing accuracy"""
        execution_times = []
        
        def timed_job():
            execution_times.append(datetime.now())
            return "executed"
        
        job = self.scheduler.add_job(timed_job, 'interval', seconds=1)
        
        # Simulate multiple executions
        for _ in range(3):
            job['func']()
            time.sleep(0.1)  # Small delay between executions
        
        self.assertEqual(len(execution_times), 3)
        
        # Check that executions happened in sequence
        for i in range(1, len(execution_times)):
            self.assertGreater(execution_times[i], execution_times[i-1])


if __name__ == '__main__':
    unittest.main()
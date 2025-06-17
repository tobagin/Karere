// tests/unit/service-manager.test.js
// Unit tests for the service manager module

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';

// Mock dependencies
jest.unstable_mockModule('../../logger.js', () => ({
    log: {
        info: jest.fn(),
        warn: jest.fn(),
        error: jest.fn(),
        debug: jest.fn(),
    },
    errorHandler: {
        generic: jest.fn((error, context) => ({
            type: 'generic_error',
            message: 'An unexpected error occurred',
            details: error?.message || 'Unknown error'
        })),
    },
    health: {
        logSystemInfo: jest.fn(),
        logStartup: jest.fn(),
        logShutdown: jest.fn(),
    },
}));

jest.unstable_mockModule('node-cron', () => ({
    default: {
        schedule: jest.fn(() => ({
            start: jest.fn(),
            stop: jest.fn(),
        })),
    },
}));

jest.unstable_mockModule('fs/promises', () => ({
    default: {
        readdir: jest.fn(() => Promise.resolve(['test.log'])),
        stat: jest.fn(() => Promise.resolve({ size: 1024 })),
    },
}));

describe('Service Manager Module', () => {
    let ServiceManager;
    let serviceManager;
    let mockCron;

    beforeEach(async () => {
        // Import service manager after mocking
        const serviceManagerModule = await import('../../service-manager.js');
        ServiceManager = serviceManagerModule.default.constructor;
        serviceManager = new ServiceManager();
        
        // Mock cron
        const cronModule = await import('node-cron');
        mockCron = cronModule.default;
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Service Manager initialization', () => {
        test('should initialize successfully', async () => {
            await expect(serviceManager.initialize()).resolves.not.toThrow();
        });

        test('should setup shutdown handlers', () => {
            const originalOn = process.on;
            process.on = jest.fn();
            
            serviceManager.setupShutdownHandlers();
            
            expect(process.on).toHaveBeenCalledWith('SIGTERM', expect.any(Function));
            expect(process.on).toHaveBeenCalledWith('SIGINT', expect.any(Function));
            expect(process.on).toHaveBeenCalledWith('SIGUSR2', expect.any(Function));
            expect(process.on).toHaveBeenCalledWith('uncaughtException', expect.any(Function));
            expect(process.on).toHaveBeenCalledWith('unhandledRejection', expect.any(Function));
            
            process.on = originalOn;
        });
    });

    describe('Service registration and management', () => {
        test('should register service successfully', () => {
            const serviceName = 'testService';
            const service = {
                start: jest.fn(),
                stop: jest.fn(),
                shutdown: jest.fn(),
            };
            
            serviceManager.registerService(serviceName, service);
            
            expect(serviceManager.getService(serviceName)).toBe(service);
        });

        test('should get registered service', () => {
            const serviceName = 'testService';
            const service = { test: 'data' };
            
            serviceManager.registerService(serviceName, service);
            const retrievedService = serviceManager.getService(serviceName);
            
            expect(retrievedService).toBe(service);
        });

        test('should return undefined for non-existent service', () => {
            const retrievedService = serviceManager.getService('nonExistentService');
            
            expect(retrievedService).toBeUndefined();
        });
    });

    describe('Health check management', () => {
        test('should add health check successfully', () => {
            const checkName = 'testCheck';
            const checkFunction = jest.fn(() => ({ healthy: true, details: {} }));
            
            serviceManager.addHealthCheck(checkName, checkFunction);
            
            expect(serviceManager.healthChecks.has(checkName)).toBe(true);
        });

        test('should run health checks successfully', async () => {
            const checkFunction1 = jest.fn(() => ({ healthy: true, details: { test: 'pass' } }));
            const checkFunction2 = jest.fn(() => ({ healthy: false, details: { test: 'fail' } }));
            
            serviceManager.addHealthCheck('check1', checkFunction1);
            serviceManager.addHealthCheck('check2', checkFunction2);
            
            const result = await serviceManager.runHealthChecks();
            
            expect(checkFunction1).toHaveBeenCalled();
            expect(checkFunction2).toHaveBeenCalled();
            expect(result.healthy).toBe(false); // Overall health should be false
            expect(result.checks).toHaveProperty('check1');
            expect(result.checks).toHaveProperty('check2');
            expect(result.checks.check1.healthy).toBe(true);
            expect(result.checks.check2.healthy).toBe(false);
        });

        test('should handle health check errors', async () => {
            const checkFunction = jest.fn(() => {
                throw new Error('Health check failed');
            });
            
            serviceManager.addHealthCheck('errorCheck', checkFunction);
            
            const result = await serviceManager.runHealthChecks();
            
            expect(result.healthy).toBe(false);
            expect(result.checks.errorCheck.healthy).toBe(false);
            expect(result.checks.errorCheck.details.error).toBe('Health check failed');
        });

        test('should handle async health checks', async () => {
            const checkFunction = jest.fn(async () => {
                await new Promise(resolve => setTimeout(resolve, 10));
                return { healthy: true, details: { async: 'test' } };
            });
            
            serviceManager.addHealthCheck('asyncCheck', checkFunction);
            
            const result = await serviceManager.runHealthChecks();
            
            expect(result.checks.asyncCheck.healthy).toBe(true);
            expect(result.checks.asyncCheck.details.async).toBe('test');
        });
    });

    describe('Cron job management', () => {
        test('should add cron job successfully', () => {
            const jobName = 'testJob';
            const schedule = '0 * * * *';
            const task = jest.fn();
            
            const mockJob = {
                start: jest.fn(),
                stop: jest.fn(),
            };
            mockCron.schedule.mockReturnValue(mockJob);
            
            serviceManager.addCronJob(jobName, schedule, task);
            
            expect(mockCron.schedule).toHaveBeenCalledWith(
                schedule,
                expect.any(Function),
                { scheduled: false }
            );
            expect(mockJob.start).toHaveBeenCalled();
            expect(serviceManager.cronJobs.has(jobName)).toBe(true);
        });

        test('should not add duplicate cron job', () => {
            const jobName = 'testJob';
            const schedule = '0 * * * *';
            const task = jest.fn();
            
            const mockJob = {
                start: jest.fn(),
                stop: jest.fn(),
            };
            mockCron.schedule.mockReturnValue(mockJob);
            
            serviceManager.addCronJob(jobName, schedule, task);
            serviceManager.addCronJob(jobName, schedule, task); // Try to add again
            
            expect(mockCron.schedule).toHaveBeenCalledTimes(1);
        });

        test('should remove cron job successfully', () => {
            const jobName = 'testJob';
            const schedule = '0 * * * *';
            const task = jest.fn();
            
            const mockJob = {
                start: jest.fn(),
                stop: jest.fn(),
            };
            mockCron.schedule.mockReturnValue(mockJob);
            
            serviceManager.addCronJob(jobName, schedule, task);
            serviceManager.removeCronJob(jobName);
            
            expect(mockJob.stop).toHaveBeenCalled();
            expect(serviceManager.cronJobs.has(jobName)).toBe(false);
        });

        test('should handle cron job task errors', async () => {
            const jobName = 'errorJob';
            const schedule = '0 * * * *';
            const task = jest.fn(() => {
                throw new Error('Task failed');
            });
            
            const mockJob = {
                start: jest.fn(),
                stop: jest.fn(),
            };
            let cronCallback;
            mockCron.schedule.mockImplementation((sched, callback, options) => {
                cronCallback = callback;
                return mockJob;
            });
            
            serviceManager.addCronJob(jobName, schedule, task);
            
            // Execute the cron callback
            await expect(cronCallback()).resolves.not.toThrow();
            expect(task).toHaveBeenCalled();
        });
    });

    describe('Performance metrics', () => {
        test('should get performance metrics', () => {
            const metrics = serviceManager.getPerformanceMetrics();
            
            expect(metrics).toHaveProperty('memory');
            expect(metrics).toHaveProperty('cpu');
            expect(metrics).toHaveProperty('uptime');
            expect(metrics).toHaveProperty('pid');
            expect(metrics).toHaveProperty('version');
            expect(metrics).toHaveProperty('platform');
            
            expect(metrics.memory).toHaveProperty('heapUsed');
            expect(metrics.memory).toHaveProperty('heapTotal');
            expect(metrics.memory).toHaveProperty('external');
            expect(metrics.memory).toHaveProperty('rss');
            
            expect(metrics.cpu).toHaveProperty('user');
            expect(metrics.cpu).toHaveProperty('system');
        });
    });

    describe('Status reporting', () => {
        test('should get status successfully', () => {
            const serviceName = 'testService';
            const service = { test: 'data' };
            serviceManager.registerService(serviceName, service);
            
            const checkName = 'testCheck';
            const checkFunction = jest.fn();
            serviceManager.addHealthCheck(checkName, checkFunction);
            
            const status = serviceManager.getStatus();
            
            expect(status).toHaveProperty('isShuttingDown');
            expect(status).toHaveProperty('uptime');
            expect(status).toHaveProperty('startTime');
            expect(status).toHaveProperty('services');
            expect(status).toHaveProperty('healthChecks');
            expect(status).toHaveProperty('cronJobs');
            expect(status).toHaveProperty('performance');
            
            expect(status.services).toContain(serviceName);
            expect(status.healthChecks).toContain(checkName);
            expect(status.isShuttingDown).toBe(false);
        });
    });

    describe('Log rotation check', () => {
        test('should check log rotation successfully', async () => {
            await expect(serviceManager.checkLogRotation()).resolves.not.toThrow();
        });

        test('should handle log rotation check errors', async () => {
            const fsModule = await import('fs/promises');
            fsModule.default.readdir.mockRejectedValue(new Error('Directory not found'));
            
            await expect(serviceManager.checkLogRotation()).resolves.not.toThrow();
        });
    });
});

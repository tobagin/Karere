// tests/unit/logger.test.js
// Unit tests for the logger module

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import fs from 'fs/promises';
import path from 'path';

// Mock winston before importing logger
jest.unstable_mockModule('winston', () => ({
    default: {
        createLogger: jest.fn(() => ({
            info: jest.fn(),
            warn: jest.fn(),
            error: jest.fn(),
            debug: jest.fn(),
        })),
        format: {
            combine: jest.fn(),
            timestamp: jest.fn(),
            errors: jest.fn(),
            printf: jest.fn(),
            colorize: jest.fn(),
        },
        transports: {
            Console: jest.fn(),
            File: jest.fn(),
        },
    },
}));

describe('Logger Module', () => {
    let logger, log, errorHandler, performance, health;
    let mockWinstonLogger;
    let tempDir;

    beforeEach(async () => {
        // Create temp directory for test logs
        tempDir = await testUtils.createTempDir();
        
        // Mock winston logger
        mockWinstonLogger = {
            info: jest.fn(),
            warn: jest.fn(),
            error: jest.fn(),
            debug: jest.fn(),
        };

        // Import logger module after mocking
        const loggerModule = await import('../../logger.js');
        log = loggerModule.log;
        errorHandler = loggerModule.errorHandler;
        performance = loggerModule.performance;
        health = loggerModule.health;
    });

    afterEach(async () => {
        await testUtils.cleanupTempDir(tempDir);
        jest.clearAllMocks();
    });

    describe('log object', () => {
        test('should have all required logging methods', () => {
            expect(log).toHaveProperty('info');
            expect(log).toHaveProperty('warn');
            expect(log).toHaveProperty('error');
            expect(log).toHaveProperty('debug');
            expect(log).toHaveProperty('websocket');
            expect(log).toHaveProperty('baileys');
            expect(log).toHaveProperty('auth');
            expect(log).toHaveProperty('message');
            expect(log).toHaveProperty('performance');
        });

        test('should log info messages with metadata', () => {
            const message = 'Test info message';
            const meta = { userId: '123', action: 'test' };
            
            log.info(message, meta);
            
            // Since we're mocking winston, we can't directly test the logger calls
            // but we can test that the function doesn't throw
            expect(() => log.info(message, meta)).not.toThrow();
        });

        test('should log error messages with error objects', () => {
            const message = 'Test error message';
            const error = new Error('Test error');
            const meta = { context: 'test' };
            
            expect(() => log.error(message, error, meta)).not.toThrow();
        });

        test('should log specialized messages with component metadata', () => {
            const message = 'WebSocket connection established';
            const meta = { connectionId: 'ws123' };
            
            expect(() => log.websocket(message, meta)).not.toThrow();
            expect(() => log.baileys(message, meta)).not.toThrow();
            expect(() => log.auth(message, meta)).not.toThrow();
            expect(() => log.message(message, meta)).not.toThrow();
        });

        test('should log performance metrics', () => {
            const operation = 'database_query';
            const duration = 150;
            const meta = { query: 'SELECT * FROM messages' };
            
            expect(() => log.performance(operation, duration, meta)).not.toThrow();
        });
    });

    describe('errorHandler object', () => {
        test('should have all required error handler methods', () => {
            expect(errorHandler).toHaveProperty('websocket');
            expect(errorHandler).toHaveProperty('baileys');
            expect(errorHandler).toHaveProperty('messaging');
            expect(errorHandler).toHaveProperty('database');
            expect(errorHandler).toHaveProperty('generic');
        });

        test('should handle WebSocket errors', () => {
            const error = new Error('WebSocket connection failed');
            const context = 'connection establishment';
            
            const result = errorHandler.websocket(error, context);
            
            expect(result).toEqual({
                type: 'websocket_error',
                message: 'WebSocket connection error',
                details: 'WebSocket connection failed'
            });
        });

        test('should handle Baileys errors', () => {
            const error = new Error('Authentication failed');
            const context = 'QR code generation';
            
            const result = errorHandler.baileys(error, context);
            
            expect(result).toEqual({
                type: 'baileys_error',
                message: 'WhatsApp connection error',
                details: 'Authentication failed'
            });
        });

        test('should handle messaging errors', () => {
            const error = new Error('Message send failed');
            const context = 'send message';
            
            const result = errorHandler.messaging(error, context);
            
            expect(result).toEqual({
                type: 'messaging_error',
                message: 'Message processing error',
                details: 'Message send failed'
            });
        });

        test('should handle database errors', () => {
            const error = new Error('Database connection lost');
            const context = 'save message';
            
            const result = errorHandler.database(error, context);
            
            expect(result).toEqual({
                type: 'database_error',
                message: 'Database operation error',
                details: 'Database connection lost'
            });
        });

        test('should handle generic errors', () => {
            const error = new Error('Unknown error');
            const context = 'general operation';
            
            const result = errorHandler.generic(error, context);
            
            expect(result).toEqual({
                type: 'generic_error',
                message: 'An unexpected error occurred',
                details: 'Unknown error'
            });
        });

        test('should handle errors without error objects', () => {
            const result = errorHandler.generic(null, 'test context');
            
            expect(result).toEqual({
                type: 'generic_error',
                message: 'An unexpected error occurred',
                details: 'Unknown error'
            });
        });
    });

    describe('performance object', () => {
        test('should provide performance timing functionality', () => {
            expect(performance).toHaveProperty('start');
            expect(typeof performance.start).toBe('function');
        });

        test('should measure operation duration', () => {
            const operation = 'test_operation';
            const timer = performance.start(operation);
            
            expect(timer).toHaveProperty('end');
            expect(typeof timer.end).toBe('function');
            
            // Simulate some work
            const duration = timer.end({ testMeta: 'value' });
            
            expect(typeof duration).toBe('number');
            expect(duration).toBeGreaterThanOrEqual(0);
        });
    });

    describe('health object', () => {
        test('should have all required health methods', () => {
            expect(health).toHaveProperty('logSystemInfo');
            expect(health).toHaveProperty('logStartup');
            expect(health).toHaveProperty('logShutdown');
        });

        test('should log system information', () => {
            expect(() => health.logSystemInfo()).not.toThrow();
        });

        test('should log startup information', () => {
            expect(() => health.logStartup()).not.toThrow();
        });

        test('should log shutdown information', () => {
            const reason = 'SIGTERM';
            expect(() => health.logShutdown(reason)).not.toThrow();
        });
    });

    describe('error handling edge cases', () => {
        test('should handle undefined errors gracefully', () => {
            const result = errorHandler.websocket(undefined, 'test');
            expect(result.details).toBe('Unknown error');
        });

        test('should handle errors without message property', () => {
            const error = { code: 'ERR_CONNECTION_REFUSED' };
            const result = errorHandler.websocket(error, 'test');
            expect(result.details).toBe('Unknown error');
        });

        test('should handle string errors', () => {
            const error = 'String error message';
            const result = errorHandler.generic(error, 'test');
            expect(result.details).toBe('Unknown error');
        });
    });
});

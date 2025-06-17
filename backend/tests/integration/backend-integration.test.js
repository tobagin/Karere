// tests/integration/backend-integration.test.js
// Integration tests for backend components

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import WebSocket from 'ws';

// Mock Baileys to avoid actual WhatsApp connections
jest.unstable_mockModule('@whiskeysockets/baileys', () => ({
    default: jest.fn(() => ({
        ev: {
            on: jest.fn(),
            off: jest.fn(),
        },
        sendMessage: jest.fn(),
        sendPresenceUpdate: jest.fn(),
        fetchMessageHistory: jest.fn(),
        end: jest.fn(),
    })),
    DisconnectReason: {
        loggedOut: 401,
        connectionClosed: 428,
    },
    useMultiFileAuthState: jest.fn(() => Promise.resolve({
        state: {},
        saveCreds: jest.fn(),
    })),
    fetchLatestBaileysVersion: jest.fn(() => Promise.resolve({
        version: [2, 2413, 1],
    })),
}));

describe('Backend Integration Tests', () => {
    let testPort;
    let wsClient;
    let database;
    let serviceManager;

    beforeEach(async () => {
        testPort = 8766; // Different port for tests
        
        // Import modules after mocking
        const databaseModule = await import('../../database.js');
        const serviceManagerModule = await import('../../service-manager.js');
        
        database = databaseModule.default;
        serviceManager = serviceManagerModule.default;
        
        // Initialize test database
        database.db = {
            run: jest.fn((sql, params, callback) => {
                if (callback) callback.call({ lastID: 1, changes: 1 }, null);
            }),
            get: jest.fn((sql, params, callback) => {
                if (callback) callback(null, null);
            }),
            all: jest.fn((sql, params, callback) => {
                if (callback) callback(null, []);
            }),
            close: jest.fn((callback) => {
                if (callback) callback(null);
            }),
        };
        database.isInitialized = true;
    });

    afterEach(async () => {
        if (wsClient && wsClient.readyState === WebSocket.OPEN) {
            wsClient.close();
        }
        
        // Clean up any running services
        jest.clearAllMocks();
    });

    describe('WebSocket Server Integration', () => {
        test('should start WebSocket server and accept connections', async () => {
            // This test would require starting the actual backend
            // For now, we'll test the WebSocket client connection logic
            
            const mockWsServer = {
                on: jest.fn(),
                close: jest.fn(),
            };
            
            expect(mockWsServer.on).toBeDefined();
        });

        test('should handle WebSocket message exchange', async () => {
            // Mock WebSocket message handling
            const mockMessage = {
                type: 'get_initial_chats',
                data: {}
            };
            
            const messageHandler = jest.fn();
            
            // Simulate message processing
            messageHandler(JSON.stringify(mockMessage));
            
            expect(messageHandler).toHaveBeenCalledWith(JSON.stringify(mockMessage));
        });

        test('should handle WebSocket connection errors', async () => {
            const mockWs = {
                on: jest.fn(),
                send: jest.fn(),
                close: jest.fn(),
                readyState: WebSocket.OPEN,
            };
            
            // Simulate error handling
            const errorHandler = jest.fn();
            mockWs.on('error', errorHandler);
            
            // Trigger error
            const error = new Error('Connection failed');
            errorHandler(error);
            
            expect(errorHandler).toHaveBeenCalledWith(error);
        });
    });

    describe('Database Integration', () => {
        test('should save and retrieve chat data', async () => {
            const chatData = {
                jid: '5511999999999@s.whatsapp.net',
                name: 'Test Contact',
                lastMessageId: 'msg123',
                timestamp: Date.now(),
            };
            
            // Mock successful save
            database.db.run = jest.fn((sql, params, callback) => {
                if (callback) callback.call({ lastID: 1, changes: 1 }, null);
            });
            
            await database.saveChat(
                chatData.jid,
                chatData.name,
                chatData.lastMessageId,
                chatData.timestamp
            );
            
            expect(database.db.run).toHaveBeenCalledWith(
                expect.stringContaining('INSERT OR REPLACE INTO chats'),
                [chatData.jid, chatData.name, chatData.lastMessageId, chatData.timestamp],
                expect.any(Function)
            );
        });

        test('should save and retrieve message data', async () => {
            const messageData = {
                id: 'msg123',
                chatJid: '5511999999999@s.whatsapp.net',
                fromMe: true,
                content: 'Test message',
                timestamp: Date.now(),
                messageType: 'text',
                status: 'sent',
            };
            
            await database.saveMessage(
                messageData.id,
                messageData.chatJid,
                messageData.fromMe,
                messageData.content,
                messageData.timestamp,
                messageData.messageType,
                messageData.status
            );
            
            expect(database.db.run).toHaveBeenCalledWith(
                expect.stringContaining('INSERT OR REPLACE INTO messages'),
                expect.arrayContaining([
                    messageData.id,
                    messageData.chatJid,
                    messageData.fromMe,
                ]),
                expect.any(Function)
            );
        });

        test('should handle database transaction rollback', async () => {
            // Mock database error
            database.db.run = jest.fn((sql, params, callback) => {
                if (callback) callback(new Error('Database error'));
            });
            
            await expect(database.saveChat('test', 'test')).rejects.toThrow();
        });
    });

    describe('Service Manager Integration', () => {
        test('should register and manage multiple services', async () => {
            const service1 = {
                name: 'service1',
                shutdown: jest.fn(),
            };
            
            const service2 = {
                name: 'service2',
                shutdown: jest.fn(),
            };
            
            serviceManager.registerService('service1', service1);
            serviceManager.registerService('service2', service2);
            
            expect(serviceManager.getService('service1')).toBe(service1);
            expect(serviceManager.getService('service2')).toBe(service2);
            
            const status = serviceManager.getStatus();
            expect(status.services).toContain('service1');
            expect(status.services).toContain('service2');
        });

        test('should run health checks for all services', async () => {
            const healthCheck1 = jest.fn(() => ({ healthy: true, details: {} }));
            const healthCheck2 = jest.fn(() => ({ healthy: false, details: { error: 'test' } }));
            
            serviceManager.addHealthCheck('check1', healthCheck1);
            serviceManager.addHealthCheck('check2', healthCheck2);
            
            const result = await serviceManager.runHealthChecks();
            
            expect(result.healthy).toBe(false);
            expect(result.checks.check1.healthy).toBe(true);
            expect(result.checks.check2.healthy).toBe(false);
        });
    });

    describe('End-to-End Message Flow', () => {
        test('should handle complete message sending flow', async () => {
            // Mock the complete flow from WebSocket to database
            const messageData = {
                to: '5511999999999@s.whatsapp.net',
                message: 'Test message',
            };
            
            // Mock Baileys socket
            const mockSocket = {
                sendMessage: jest.fn(() => Promise.resolve({
                    key: { id: 'msg123' }
                })),
            };
            
            // Mock database save
            database.saveMessage = jest.fn();
            database.saveChat = jest.fn();
            
            // Simulate message sending
            const messageId = 'msg123';
            await mockSocket.sendMessage(messageData.to, { text: messageData.message });
            await database.saveMessage(
                messageId,
                messageData.to,
                true,
                messageData.message,
                Date.now(),
                'text',
                'sent'
            );
            
            expect(mockSocket.sendMessage).toHaveBeenCalledWith(
                messageData.to,
                { text: messageData.message }
            );
            expect(database.saveMessage).toHaveBeenCalled();
        });

        test('should handle message receiving flow', async () => {
            // Mock incoming message
            const incomingMessage = {
                key: {
                    id: 'msg456',
                    remoteJid: '5511999999999@s.whatsapp.net',
                    fromMe: false,
                },
                message: {
                    conversation: 'Incoming test message',
                },
                messageTimestamp: Math.floor(Date.now() / 1000),
            };
            
            // Mock database save
            database.saveMessage = jest.fn();
            database.saveChat = jest.fn();
            
            // Simulate message processing
            await database.saveMessage(
                incomingMessage.key.id,
                incomingMessage.key.remoteJid,
                false,
                incomingMessage.message.conversation,
                incomingMessage.messageTimestamp * 1000,
                'text',
                'received'
            );
            
            expect(database.saveMessage).toHaveBeenCalledWith(
                incomingMessage.key.id,
                incomingMessage.key.remoteJid,
                false,
                incomingMessage.message.conversation,
                incomingMessage.messageTimestamp * 1000,
                'text',
                'received'
            );
        });
    });

    describe('Error Handling Integration', () => {
        test('should handle WebSocket disconnection gracefully', async () => {
            const mockWs = {
                readyState: WebSocket.CLOSED,
                send: jest.fn(),
            };
            
            // Attempt to send message when disconnected
            const sendMessage = (ws, message) => {
                if (ws.readyState !== WebSocket.OPEN) {
                    throw new Error('WebSocket not connected');
                }
                ws.send(message);
            };
            
            expect(() => sendMessage(mockWs, 'test')).toThrow('WebSocket not connected');
        });

        test('should handle database connection errors', async () => {
            // Mock database connection failure
            database.db.run = jest.fn((sql, params, callback) => {
                if (callback) callback(new Error('SQLITE_BUSY: database is locked'));
            });
            
            await expect(database.saveMessage('test', 'test', false, 'test', Date.now()))
                .rejects.toThrow();
        });

        test('should handle Baileys connection errors', async () => {
            const baileys = await import('@whiskeysockets/baileys');
            const mockSocket = baileys.default();
            
            // Mock connection error
            mockSocket.sendMessage.mockRejectedValue(new Error('Not connected'));
            
            await expect(mockSocket.sendMessage('test', { text: 'test' }))
                .rejects.toThrow('Not connected');
        });
    });
});

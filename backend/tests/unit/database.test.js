// tests/unit/database.test.js
// Unit tests for the database module

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import path from 'path';

// Mock sqlite3 and logger
jest.unstable_mockModule('sqlite3', () => ({
    default: {
        Database: jest.fn(() => ({
            run: jest.fn(),
            get: jest.fn(),
            all: jest.fn(),
            close: jest.fn(),
        })),
    },
}));

jest.unstable_mockModule('../../logger.js', () => ({
    log: {
        info: jest.fn(),
        warn: jest.fn(),
        error: jest.fn(),
        debug: jest.fn(),
    },
    errorHandler: {
        database: jest.fn((error, context) => ({
            type: 'database_error',
            message: 'Database operation error',
            details: error?.message || 'Unknown error'
        })),
    },
    performance: {
        start: jest.fn(() => ({
            end: jest.fn(() => 100),
        })),
    },
}));

describe('Database Module', () => {
    let Database;
    let mockSqliteDb;
    let database;

    beforeEach(async () => {
        // Mock sqlite3 database instance
        mockSqliteDb = {
            run: jest.fn((sql, params, callback) => {
                if (callback) callback.call({ lastID: 1, changes: 1 }, null);
            }),
            get: jest.fn((sql, params, callback) => {
                if (callback) callback(null, { id: 1, test: 'data' });
            }),
            all: jest.fn((sql, params, callback) => {
                if (callback) callback(null, [{ id: 1, test: 'data' }]);
            }),
            close: jest.fn((callback) => {
                if (callback) callback(null);
            }),
        };

        // Import database module after mocking
        const databaseModule = await import('../../database.js');
        Database = databaseModule.default.constructor;
        database = new Database();
        database.db = mockSqliteDb;
        database.isInitialized = true;
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Database initialization', () => {
        test('should initialize database successfully', async () => {
            const newDatabase = new Database();
            newDatabase.db = mockSqliteDb;
            
            await expect(newDatabase.initialize()).resolves.not.toThrow();
        });

        test('should handle initialization errors', async () => {
            const newDatabase = new Database();
            const errorDb = {
                ...mockSqliteDb,
                run: jest.fn((sql, params, callback) => {
                    if (callback) callback(new Error('Database error'));
                }),
            };
            newDatabase.db = errorDb;
            
            await expect(newDatabase.initialize()).rejects.toThrow();
        });
    });

    describe('Basic database operations', () => {
        test('should run SQL commands successfully', async () => {
            const sql = 'INSERT INTO test (name) VALUES (?)';
            const params = ['test'];
            
            const result = await database.run(sql, params);
            
            expect(mockSqliteDb.run).toHaveBeenCalledWith(sql, params, expect.any(Function));
            expect(result).toEqual({ lastID: 1, changes: 1 });
        });

        test('should get single row successfully', async () => {
            const sql = 'SELECT * FROM test WHERE id = ?';
            const params = [1];
            
            const result = await database.get(sql, params);
            
            expect(mockSqliteDb.get).toHaveBeenCalledWith(sql, params, expect.any(Function));
            expect(result).toEqual({ id: 1, test: 'data' });
        });

        test('should get all rows successfully', async () => {
            const sql = 'SELECT * FROM test';
            const params = [];
            
            const result = await database.all(sql, params);
            
            expect(mockSqliteDb.all).toHaveBeenCalledWith(sql, params, expect.any(Function));
            expect(result).toEqual([{ id: 1, test: 'data' }]);
        });

        test('should handle database errors in run operation', async () => {
            mockSqliteDb.run = jest.fn((sql, params, callback) => {
                if (callback) callback(new Error('SQL error'));
            });
            
            await expect(database.run('INVALID SQL')).rejects.toThrow('SQL error');
        });
    });

    describe('Chat operations', () => {
        test('should save chat successfully', async () => {
            const jid = '5511999999999@s.whatsapp.net';
            const name = 'Test Contact';
            const lastMessageId = 'msg123';
            const timestamp = Date.now();
            
            await database.saveChat(jid, name, lastMessageId, timestamp);
            
            expect(mockSqliteDb.run).toHaveBeenCalledWith(
                expect.stringContaining('INSERT OR REPLACE INTO chats'),
                [jid, name, lastMessageId, timestamp],
                expect.any(Function)
            );
        });

        test('should get chats successfully', async () => {
            mockSqliteDb.all = jest.fn((sql, params, callback) => {
                const mockChats = [
                    {
                        jid: '5511999999999@s.whatsapp.net',
                        name: 'Test Contact 1',
                        last_message_content: 'Hello',
                        last_message_timestamp: Date.now(),
                    },
                    {
                        jid: '5511888888888@s.whatsapp.net',
                        name: 'Test Contact 2',
                        last_message_content: 'Hi there',
                        last_message_timestamp: Date.now() - 1000,
                    },
                ];
                if (callback) callback(null, mockChats);
            });
            
            const chats = await database.getChats(10);
            
            expect(mockSqliteDb.all).toHaveBeenCalledWith(
                expect.stringContaining('SELECT c.*, m.content'),
                [10],
                expect.any(Function)
            );
            expect(chats).toHaveLength(2);
            expect(chats[0]).toHaveProperty('jid');
            expect(chats[0]).toHaveProperty('name');
        });
    });

    describe('Message operations', () => {
        test('should save message successfully', async () => {
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
            
            expect(mockSqliteDb.run).toHaveBeenCalledWith(
                expect.stringContaining('INSERT OR REPLACE INTO messages'),
                [
                    messageData.id,
                    messageData.chatJid,
                    messageData.fromMe,
                    messageData.messageType,
                    messageData.content,
                    messageData.timestamp,
                    messageData.status,
                ],
                expect.any(Function)
            );
        });

        test('should get messages successfully', async () => {
            const chatJid = '5511999999999@s.whatsapp.net';
            const limit = 50;
            const offset = 0;
            
            mockSqliteDb.all = jest.fn((sql, params, callback) => {
                const mockMessages = [
                    {
                        id: 'msg1',
                        chat_jid: chatJid,
                        from_me: 0,
                        content: 'Hello',
                        timestamp: Date.now() - 2000,
                        status: 'received',
                    },
                    {
                        id: 'msg2',
                        chat_jid: chatJid,
                        from_me: 1,
                        content: 'Hi there',
                        timestamp: Date.now() - 1000,
                        status: 'sent',
                    },
                ];
                if (callback) callback(null, mockMessages);
            });
            
            const messages = await database.getMessages(chatJid, limit, offset);
            
            expect(mockSqliteDb.all).toHaveBeenCalledWith(
                expect.stringContaining('SELECT * FROM messages'),
                [chatJid, limit, offset],
                expect.any(Function)
            );
            expect(messages).toHaveLength(2);
            expect(messages[0]).toHaveProperty('id');
            expect(messages[0]).toHaveProperty('content');
        });

        test('should update message status successfully', async () => {
            const messageId = 'msg123';
            const status = 'delivered';
            
            await database.updateMessageStatus(messageId, status);
            
            expect(mockSqliteDb.run).toHaveBeenCalledWith(
                'UPDATE messages SET status = ? WHERE id = ?',
                [status, messageId],
                expect.any(Function)
            );
        });
    });

    describe('Contact operations', () => {
        test('should save contact successfully', async () => {
            const jid = '5511999999999@s.whatsapp.net';
            const name = 'Test Contact';
            const phoneNumber = '+5511999999999';
            
            await database.saveContact(jid, name, phoneNumber);
            
            expect(mockSqliteDb.run).toHaveBeenCalledWith(
                expect.stringContaining('INSERT OR REPLACE INTO contacts'),
                [jid, name, phoneNumber],
                expect.any(Function)
            );
        });

        test('should get contact successfully', async () => {
            const jid = '5511999999999@s.whatsapp.net';
            
            mockSqliteDb.get = jest.fn((sql, params, callback) => {
                const mockContact = {
                    jid,
                    name: 'Test Contact',
                    phone_number: '+5511999999999',
                };
                if (callback) callback(null, mockContact);
            });
            
            const contact = await database.getContact(jid);
            
            expect(mockSqliteDb.get).toHaveBeenCalledWith(
                'SELECT * FROM contacts WHERE jid = ?',
                [jid],
                expect.any(Function)
            );
            expect(contact).toHaveProperty('jid', jid);
            expect(contact).toHaveProperty('name');
        });
    });

    describe('Settings operations', () => {
        test('should set setting successfully', async () => {
            const key = 'theme';
            const value = 'dark';
            
            await database.setSetting(key, value);
            
            expect(mockSqliteDb.run).toHaveBeenCalledWith(
                expect.stringContaining('INSERT OR REPLACE INTO settings'),
                [key, JSON.stringify(value)],
                expect.any(Function)
            );
        });

        test('should get setting successfully', async () => {
            const key = 'theme';
            const expectedValue = 'dark';
            
            mockSqliteDb.get = jest.fn((sql, params, callback) => {
                const mockSetting = {
                    value: JSON.stringify(expectedValue),
                };
                if (callback) callback(null, mockSetting);
            });
            
            const value = await database.getSetting(key);
            
            expect(mockSqliteDb.get).toHaveBeenCalledWith(
                'SELECT value FROM settings WHERE key = ?',
                [key],
                expect.any(Function)
            );
            expect(value).toBe(expectedValue);
        });

        test('should return default value when setting not found', async () => {
            const key = 'nonexistent';
            const defaultValue = 'default';
            
            mockSqliteDb.get = jest.fn((sql, params, callback) => {
                if (callback) callback(null, null);
            });
            
            const value = await database.getSetting(key, defaultValue);
            
            expect(value).toBe(defaultValue);
        });
    });

    describe('Database cleanup and maintenance', () => {
        test('should perform cleanup successfully', async () => {
            await database.cleanup();
            
            expect(mockSqliteDb.run).toHaveBeenCalledWith(
                expect.stringContaining('DELETE FROM messages WHERE timestamp < ?'),
                expect.any(Array),
                expect.any(Function)
            );
            expect(mockSqliteDb.run).toHaveBeenCalledWith(
                'VACUUM',
                expect.any(Function)
            );
        });

        test('should close database successfully', async () => {
            await database.close();
            
            expect(mockSqliteDb.close).toHaveBeenCalled();
        });
    });
});

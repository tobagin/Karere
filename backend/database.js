// database.js
// SQLite database for message persistence and chat history

import sqlite3 from 'sqlite3';
import { log, errorHandler, performance } from './logger.js';
import fs from 'fs';
import path from 'path';

// Create data directory if it doesn't exist
const dataDir = 'data';
if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir);
}

const dbPath = path.join(dataDir, 'karere.db');

class Database {
    constructor() {
        this.db = null;
        this.isInitialized = false;
    }

    async initialize() {
        const timer = performance.start('database_initialization');
        
        try {
            log.info('Initializing database', { path: dbPath });
            
            this.db = new sqlite3.Database(dbPath, (err) => {
                if (err) {
                    throw err;
                }
            });

            // Enable foreign keys and WAL mode for better performance
            await this.run('PRAGMA foreign_keys = ON');
            await this.run('PRAGMA journal_mode = WAL');
            await this.run('PRAGMA synchronous = NORMAL');
            await this.run('PRAGMA cache_size = 1000');
            await this.run('PRAGMA temp_store = memory');

            await this.createTables();
            this.isInitialized = true;
            
            timer.end();
            log.info('Database initialized successfully');
            
        } catch (error) {
            timer.end({ error: true });
            throw errorHandler.database(error, 'initialization');
        }
    }

    async createTables() {
        const tables = [
            // Chats table
            `CREATE TABLE IF NOT EXISTS chats (
                jid TEXT PRIMARY KEY,
                name TEXT,
                last_message_id TEXT,
                last_message_timestamp INTEGER,
                unread_count INTEGER DEFAULT 0,
                is_archived BOOLEAN DEFAULT FALSE,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )`,

            // Messages table
            `CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_jid TEXT NOT NULL,
                from_me BOOLEAN NOT NULL,
                message_type TEXT DEFAULT 'text',
                content TEXT,
                timestamp INTEGER NOT NULL,
                status TEXT DEFAULT 'sent',
                reply_to_id TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (chat_jid) REFERENCES chats (jid) ON DELETE CASCADE,
                FOREIGN KEY (reply_to_id) REFERENCES messages (id) ON DELETE SET NULL
            )`,

            // Media table for file attachments
            `CREATE TABLE IF NOT EXISTS media (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                file_path TEXT,
                file_name TEXT,
                file_size INTEGER,
                mime_type TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
            )`,

            // Contacts table
            `CREATE TABLE IF NOT EXISTS contacts (
                jid TEXT PRIMARY KEY,
                name TEXT,
                phone_number TEXT,
                avatar_path TEXT,
                is_blocked BOOLEAN DEFAULT FALSE,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )`,

            // Settings table
            `CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )`
        ];

        for (const table of tables) {
            await this.run(table);
        }

        // Create indexes for better performance
        const indexes = [
            'CREATE INDEX IF NOT EXISTS idx_messages_chat_jid ON messages (chat_jid)',
            'CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_messages_from_me ON messages (from_me)',
            'CREATE INDEX IF NOT EXISTS idx_chats_updated_at ON chats (updated_at)',
            'CREATE INDEX IF NOT EXISTS idx_media_message_id ON media (message_id)'
        ];

        for (const index of indexes) {
            await this.run(index);
        }

        log.info('Database tables and indexes created successfully');
    }

    // Promisify database operations
    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.run(sql, params, function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve({ lastID: this.lastID, changes: this.changes });
                }
            });
        });
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.get(sql, params, (err, row) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(row);
                }
            });
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.all(sql, params, (err, rows) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(rows);
                }
            });
        });
    }

    // Chat operations
    async saveChat(jid, name = null, lastMessageId = null, timestamp = null) {
        const timer = performance.start('save_chat');
        
        try {
            const sql = `
                INSERT OR REPLACE INTO chats (jid, name, last_message_id, last_message_timestamp, updated_at)
                VALUES (?, ?, ?, ?, strftime('%s', 'now'))
            `;
            
            await this.run(sql, [jid, name, lastMessageId, timestamp]);
            timer.end();
            
            log.debug('Chat saved', { jid, name });
            
        } catch (error) {
            timer.end({ error: true });
            throw errorHandler.database(error, 'saveChat');
        }
    }

    async getChats(limit = 50) {
        const timer = performance.start('get_chats');
        
        try {
            const sql = `
                SELECT c.*, m.content as last_message_content, m.timestamp as last_message_timestamp
                FROM chats c
                LEFT JOIN messages m ON c.last_message_id = m.id
                WHERE c.is_archived = FALSE
                ORDER BY c.updated_at DESC
                LIMIT ?
            `;
            
            const chats = await this.all(sql, [limit]);
            timer.end({ count: chats.length });
            
            return chats;
            
        } catch (error) {
            timer.end({ error: true });
            throw errorHandler.database(error, 'getChats');
        }
    }

    // Message operations
    async saveMessage(id, chatJid, fromMe, content, timestamp, messageType = 'text', status = 'sent') {
        const timer = performance.start('save_message');
        
        try {
            const sql = `
                INSERT OR REPLACE INTO messages (id, chat_jid, from_me, message_type, content, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            `;
            
            await this.run(sql, [id, chatJid, fromMe, messageType, content, timestamp, status]);
            
            // Update chat's last message
            await this.run(`
                UPDATE chats 
                SET last_message_id = ?, last_message_timestamp = ?, updated_at = strftime('%s', 'now')
                WHERE jid = ?
            `, [id, timestamp, chatJid]);
            
            timer.end();
            log.debug('Message saved', { id, chatJid, fromMe });
            
        } catch (error) {
            timer.end({ error: true });
            throw errorHandler.database(error, 'saveMessage');
        }
    }

    async getMessages(chatJid, limit = 50, offset = 0) {
        const timer = performance.start('get_messages');
        
        try {
            const sql = `
                SELECT * FROM messages 
                WHERE chat_jid = ? 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            `;
            
            const messages = await this.all(sql, [chatJid, limit, offset]);
            timer.end({ count: messages.length });
            
            return messages.reverse(); // Return in chronological order
            
        } catch (error) {
            timer.end({ error: true });
            throw errorHandler.database(error, 'getMessages');
        }
    }

    async updateMessageStatus(messageId, status) {
        try {
            await this.run('UPDATE messages SET status = ? WHERE id = ?', [status, messageId]);
            log.debug('Message status updated', { messageId, status });
        } catch (error) {
            throw errorHandler.database(error, 'updateMessageStatus');
        }
    }

    // Contact operations
    async saveContact(jid, name, phoneNumber = null) {
        try {
            const sql = `
                INSERT OR REPLACE INTO contacts (jid, name, phone_number, updated_at)
                VALUES (?, ?, ?, strftime('%s', 'now'))
            `;
            
            await this.run(sql, [jid, name, phoneNumber]);
            log.debug('Contact saved', { jid, name });
            
        } catch (error) {
            throw errorHandler.database(error, 'saveContact');
        }
    }

    async getContact(jid) {
        try {
            return await this.get('SELECT * FROM contacts WHERE jid = ?', [jid]);
        } catch (error) {
            throw errorHandler.database(error, 'getContact');
        }
    }

    // Settings operations
    async setSetting(key, value) {
        try {
            const sql = `
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, strftime('%s', 'now'))
            `;
            
            await this.run(sql, [key, JSON.stringify(value)]);
            log.debug('Setting saved', { key });
            
        } catch (error) {
            throw errorHandler.database(error, 'setSetting');
        }
    }

    async getSetting(key, defaultValue = null) {
        try {
            const row = await this.get('SELECT value FROM settings WHERE key = ?', [key]);
            return row ? JSON.parse(row.value) : defaultValue;
        } catch (error) {
            throw errorHandler.database(error, 'getSetting');
        }
    }

    // Cleanup operations
    async cleanup() {
        try {
            // Delete old messages (older than 6 months)
            const sixMonthsAgo = Date.now() - (6 * 30 * 24 * 60 * 60 * 1000);
            const result = await this.run('DELETE FROM messages WHERE timestamp < ?', [sixMonthsAgo]);
            
            if (result.changes > 0) {
                log.info('Cleaned up old messages', { deletedCount: result.changes });
            }
            
            // Vacuum database to reclaim space
            await this.run('VACUUM');
            
        } catch (error) {
            throw errorHandler.database(error, 'cleanup');
        }
    }

    async close() {
        if (this.db) {
            return new Promise((resolve) => {
                this.db.close((err) => {
                    if (err) {
                        log.error('Error closing database', err);
                    } else {
                        log.info('Database connection closed');
                    }
                    resolve();
                });
            });
        }
    }
}

// Create singleton instance
const database = new Database();

export default database;

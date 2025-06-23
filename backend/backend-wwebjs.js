#!/usr/bin/env node

import pkg from 'whatsapp-web.js';
const { Client, LocalAuth, MessageMedia } = pkg;
import fs from 'fs';
import path from 'path';
import Database from './database.js';
import { WebSocketServer } from 'ws';
import { log, errorHandler, performance } from './logger.js';
import QRCode from 'qrcode';

// Initialize database
const database = Database;

// Initialize WhatsApp client with local authentication
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './data/wwebjs_auth'
    }),
    puppeteer: {
        headless: true, // Use headless mode for better compatibility
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--no-first-run',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-sync',
            '--disable-translate',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-ipc-flooding-protection',
            '--single-process', // Avoid process singleton issues
            '--no-zygote',
            '--disable-crash-reporter',
            '--disable-logging',
            '--disable-permissions-api',
            '--disable-notifications'
        ],
        executablePath: '/usr/bin/chromium-browser',
        timeout: 60000,
        userDataDir: './data/wwebjs_auth/browser_data' // Use separate user data directory
    }
});

// State variables
let isReady = false;
let qrCode = null;
let clientSocket = null;

// WebSocket server setup
const wss = new WebSocketServer({ port: 8765 });
log.info('WebSocket server started on port 8765');

wss.on('connection', (ws) => {
    log.websocket('Frontend client connected');
    clientSocket = ws;

    ws.on('message', async (message) => {
        try {
            const parsedMessage = JSON.parse(message);
            log.websocket('Received command from frontend', { type: parsedMessage.type });
            await handleFrontendCommand(parsedMessage);
        } catch (error) {
            log.error('Error processing frontend command', error);
            sendToFrontend('error', { message: error.message });
        }
    });

    ws.on('close', () => {
        log.websocket('Frontend client disconnected');
        clientSocket = null;
    });

    // Send current status when client connects
    sendToFrontend('status_update', {
        ready: isReady,
        qr: qrCode
    });
});

// Event handlers
client.on('qr', async (qr) => {
    try {
        log.info('QR Code received, generating image...');
        qrCode = qr;

        // Generate QR code as data URL
        const qrDataUrl = await QRCode.toDataURL(qr, {
            errorCorrectionLevel: 'M',
            type: 'image/png',
            quality: 0.92,
            margin: 1,
            color: {
                dark: '#000000',
                light: '#FFFFFF'
            },
            width: 256
        });

        log.info('QR Code image generated successfully');
        sendToFrontend('qr', { url: qrDataUrl });

    } catch (error) {
        log.error('Failed to generate QR code image', error);
        // Fallback to raw QR string
        sendToFrontend('qr', { url: qr });
    }
});

client.on('ready', async () => {
    log.info('WhatsApp client is ready!');
    isReady = true;

    sendToFrontend('baileys_ready', {
        status: 'connected',
        message: 'WhatsApp Web client is ready'
    });

    // Start syncing data
    await syncContacts();
    await syncChats();
});

client.on('authenticated', () => {
    log.info('WhatsApp client authenticated');
    sendToFrontend('status_update', 'authenticated');
});

client.on('auth_failure', (msg) => {
    log.error('Authentication failed', { error: msg });
    isReady = false;
    qrCode = null;
    sendToFrontend('auth_failure', {
        message: 'Authentication failed. Please scan the QR code again.',
        error: msg
    });
});

client.on('disconnected', async (reason) => {
    log.info('WhatsApp client disconnected', { reason });
    isReady = false;
    qrCode = null;

    // Handle different disconnection reasons
    if (reason === 'LOGOUT' || reason === 'NAVIGATION') {
        log.info('User logged out from phone, clearing session data');

        // Clear session data
        try {
            await clearSessionData();
            log.info('Session data cleared successfully');
        } catch (error) {
            log.error('Failed to clear session data', error);
        }

        // Notify frontend that user needs to scan QR again
        sendToFrontend('session_logout', {
            message: 'You have been logged out. Please scan the QR code to reconnect.',
            reason: reason
        });

        // Restart the client to generate new QR code
        setTimeout(() => {
            log.info('Restarting WhatsApp client after logout');
            client.initialize();
        }, 2000);

    } else {
        // Other disconnection reasons - try to reconnect
        sendToFrontend('connection_lost', {
            message: 'Connection lost. Attempting to reconnect...',
            reason: reason
        });

        // Try to reconnect after a delay
        setTimeout(() => {
            log.info('Attempting to reconnect WhatsApp client');
            client.initialize();
        }, 5000);
    }
});

// Add function to clear session data
async function clearSessionData() {
    const fs = require('fs').promises;
    const path = require('path');

    try {
        // Clear whatsapp-web.js session data
        const sessionPath = './data/wwebjs_auth';
        await fs.rm(sessionPath, { recursive: true, force: true });
        log.info('WhatsApp Web session data cleared');

        // Clear database data (optional - you might want to keep chat history)
        // await database.clearAllData();

    } catch (error) {
        log.error('Error clearing session data', error);
        throw error;
    }
}

client.on('message', async (message) => {
    log.info('New message received', { from: message.from, hasMedia: message.hasMedia });
    await handleNewMessage(message);
});

// Helper functions
function sendToFrontend(type, data) {
    try {
        if (clientSocket && clientSocket.readyState === clientSocket.OPEN) {
            const message = JSON.stringify({ type, data });
            clientSocket.send(message);
            log.websocket('Sent message to frontend', { type, dataSize: message.length });
        } else {
            log.warn('Cannot send to frontend: no active connection', { type });
        }
    } catch (error) {
        log.error('Error sending message to frontend', error, { type });
    }
}

async function handleFrontendCommand(parsedMessage) {
    const { type, data } = parsedMessage;

    switch (type) {
        case 'get_initial_chats':
            await handleGetInitialChats();
            break;

        case 'send_message':
            await handleSendMessage(data);
            break;

        case 'get_message_history':
            await handleGetMessageHistory(data);
            break;

        case 'health_check':
            await handleHealthCheck();
            break;

        case 'sync_contacts':
            await handleSyncContacts();
            break;

        default:
            log.warn('Unknown command type', { type });
            sendToFrontend('error', {
                type: 'unknown_command',
                message: `Unknown command: ${type}`
            });
    }
}

async function handleGetInitialChats() {
    try {
        const chats = await database.getChats(50);
        sendToFrontend('initial_chats', { chats });
    } catch (error) {
        log.error('Failed to get initial chats', error);
        sendToFrontend('error', { message: 'Failed to load chats' });
    }
}

async function handleSendMessage(data) {
    try {
        const { to, message } = data;
        if (isReady) {
            const chat = await client.getChatById(to);
            const sentMessage = await chat.sendMessage(message);

            // Save sent message to database
            await database.saveMessage(
                sentMessage.id._serialized,
                to,
                true,
                message,
                sentMessage.timestamp * 1000,
                'text',
                'sent',
                null
            );

            sendToFrontend('message_sent', {
                chatId: to,
                messageId: sentMessage.id._serialized,
                message: message
            });
        } else {
            sendToFrontend('message_error', { message: 'WhatsApp client not ready' });
        }
    } catch (error) {
        log.error('Failed to send message', error);
        sendToFrontend('message_error', { message: 'Failed to send message' });
    }
}

async function handleGetMessageHistory(data) {
    try {
        const { chatId, limit = 50 } = data;
        const messages = await database.getMessages(chatId, limit);
        sendToFrontend('message_history', { chatId, messages });
    } catch (error) {
        log.error('Failed to get message history', error);
        sendToFrontend('error', { message: 'Failed to load message history' });
    }
}

async function handleHealthCheck() {
    sendToFrontend('health_check_response', {
        status: 'ok',
        ready: isReady,
        timestamp: Date.now()
    });
}

async function handleSyncContacts() {
    try {
        await syncContacts();
        sendToFrontend('sync_complete', { message: 'Contacts synced successfully' });
    } catch (error) {
        log.error('Failed to sync contacts', error);
        sendToFrontend('sync_error', { message: 'Failed to sync contacts' });
    }
}

async function syncContacts() {
    const timer = performance.start('sync_contacts');

    try {
        log.info('Starting contact synchronization');
        const contacts = await client.getContacts();

        let syncedCount = 0;
        for (const contact of contacts) {
            if (contact.isMyContact || contact.isGroup) {
                await database.saveContact(
                    contact.id._serialized,
                    contact.name || contact.pushname || contact.number,
                    contact.number,
                    contact.profilePicUrl || null
                );
                syncedCount++;
            }
        }

        timer.end({ syncedCount });
        log.info('Contact synchronization completed', { syncedCount });

        sendToFrontend('sync_progress', {
            stage: 'contacts',
            message: `Synced ${syncedCount} contacts`,
            count: syncedCount
        });

    } catch (error) {
        timer.end({ error: true });
        log.error('Failed to sync contacts', error);
        sendToFrontend('sync_error', { message: 'Failed to sync contacts' });
    }
}

async function syncChats() {
    const timer = performance.start('sync_chats');

    try {
        log.info('Starting chat synchronization');
        const chats = await client.getChats();

        let syncedCount = 0;
        const processedChats = [];

        for (const chat of chats) {
            try {
                // Get chat info
                const contact = await chat.getContact();
                const chatName = chat.name || contact.name || contact.pushname || contact.number;

                await database.saveChat(
                    chat.id._serialized,
                    chatName,
                    chat.lastMessage?.id._serialized || null,
                    chat.timestamp || Date.now(),
                    contact.profilePicUrl || null
                );

                // Sync recent messages for this chat
                const messageCount = await syncChatMessages(chat);

                processedChats.push({
                    jid: chat.id._serialized,
                    name: chatName,
                    lastMessage: chat.lastMessage?.body || 'Loading messages...',
                    timestamp: chat.timestamp || Date.now(),
                    unreadCount: chat.unreadCount || 0,
                    messageCount: messageCount
                });

                syncedCount++;

                // Send progress update every 5 chats
                if (syncedCount % 5 === 0) {
                    sendToFrontend('sync_progress', {
                        stage: 'chats',
                        message: `Processed ${syncedCount}/${chats.length} chats`,
                        processed: syncedCount,
                        total: chats.length
                    });
                }

            } catch (chatError) {
                log.warn('Failed to process chat', { chatId: chat.id._serialized, error: chatError.message });
            }
        }

        timer.end({ syncedCount });
        log.info('Chat synchronization completed', { syncedCount });

        // Send the initial chats to frontend
        sendToFrontend('initial_chats', { chats: processedChats });

        sendToFrontend('sync_complete', {
            message: `Synced ${syncedCount} chats successfully`,
            count: syncedCount
        });

    } catch (error) {
        timer.end({ error: true });
        log.error('Failed to sync chats', error);
        sendToFrontend('sync_error', { message: 'Failed to sync chats' });
    }
}

async function syncChatMessages(chat, limit = 50) {
    const timer = performance.start('sync_chat_messages');

    try {
        log.debug('Syncing messages for chat', { chatId: chat.id._serialized, chatName: chat.name });

        // Fetch messages from the chat
        const messages = await chat.fetchMessages({ limit: limit });

        let savedCount = 0;
        for (const message of messages) {
            // Check if message already exists
            const existingMessage = await database.getMessage(message.id._serialized);
            if (existingMessage) {
                continue;
            }

            // Get message content
            let messageContent = message.body || '';
            let messageType = 'text';

            if (message.hasMedia) {
                messageType = message.type;
                // For now, just store the media type, we can implement media download later
                messageContent = `[${messageType.toUpperCase()}]`;
            }

            await database.saveMessage(
                message.id._serialized,
                chat.id._serialized,
                message.fromMe,
                messageContent,
                message.timestamp * 1000,
                messageType,
                message.fromMe ? 'sent' : 'received',
                message.author || null
            );

            savedCount++;
        }

        timer.end({ chatId: chat.id._serialized, savedCount, totalFound: messages.length });
        log.info('Chat messages synced', {
            chatId: chat.id._serialized,
            chatName: chat.name,
            savedCount,
            totalFound: messages.length
        });

        return savedCount;

    } catch (error) {
        timer.end({ error: true });
        log.debug('Failed to sync messages for chat', { chatId: chat.id._serialized, error: error.message });
        return 0;
    }
}

async function handleNewMessage(message) {
    const timer = performance.start('handle_new_message');

    try {
        // Save the new message to database
        const chat = await message.getChat();
        const contact = await chat.getContact();

        let messageContent = message.body || '';
        let messageType = 'text';

        if (message.hasMedia) {
            messageType = message.type;
            messageContent = `[${messageType.toUpperCase()}]`;
        }

        await database.saveMessage(
            message.id._serialized,
            chat.id._serialized,
            message.fromMe,
            messageContent,
            message.timestamp * 1000,
            messageType,
            message.fromMe ? 'sent' : 'received',
            message.author || null
        );

        timer.end({ messageId: message.id._serialized, chatId: chat.id._serialized });

        // Notify frontend
        sendToFrontend('new_message', {
            chatId: chat.id._serialized,
            messageId: message.id._serialized,
            content: messageContent,
            messageType: messageType,
            fromMe: message.fromMe,
            timestamp: message.timestamp * 1000,
            senderName: contact.name || contact.pushname || contact.number
        });

    } catch (error) {
        timer.end({ error: true });
        log.error('Failed to handle new message', error);
    }
}

// Process termination handlers

// Initialize the backend
async function startBackend() {
    try {
        log.info('Starting Karere WhatsApp Web backend');

        log.info('Initializing database...');
        await database.initialize();

        log.info('Starting WhatsApp Web client...');

        // Add error handling for client initialization
        client.on('error', (error) => {
            log.error('WhatsApp client error', error);
            sendToFrontend('status_update', 'error');
        });

        try {
            await client.initialize();
            log.info('WhatsApp Web client initialized successfully');
        } catch (initError) {
            log.error('Failed to initialize WhatsApp Web client', initError);
            sendToFrontend('status_update', 'initialization_failed');
            throw initError;
        }

        log.info('Backend initialization completed');

    } catch (error) {
        log.error('Failed to start backend', error);
        process.exit(1);
    }
}

startBackend();

// Handle process termination
process.on('SIGINT', async () => {
    log.info('Received SIGINT, shutting down gracefully...');
    try {
        await client.destroy();
        await database.close();
        wss.close();
        log.info('Graceful shutdown completed');
        process.exit(0);
    } catch (error) {
        log.error('Error during shutdown', error);
        process.exit(1);
    }
});

process.on('SIGTERM', async () => {
    log.info('Received SIGTERM, shutting down gracefully...');
    try {
        await client.destroy();
        await database.close();
        wss.close();
        log.info('Graceful shutdown completed');
        process.exit(0);
    } catch (error) {
        log.error('Error during shutdown', error);
        process.exit(1);
    }
});

// backend.js
// Enhanced Karere backend with comprehensive error handling, logging, and persistence

import { Boom } from '@hapi/boom';
import baileys from '@whiskeysockets/baileys';
import { WebSocketServer } from 'ws';
import qrcode from 'qrcode';
import fs from 'fs/promises';

// Import enhanced modules
import { log, errorHandler, performance } from './logger.js';
import database from './database.js';
import serviceManager from './service-manager.js';

const makeWASocket = baileys.default;
const {
    DisconnectReason,
    useMultiFileAuthState,
    fetchLatestBaileysVersion
} = baileys;

// Configuration
const PORT = process.env.PORT || 8765;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 5000; // 5 seconds

// Global state
let clientSocket = null;
let initialChatsPayload = null;
let baileysConnectionStatus = 'closed';
let sock = null;
let clientIsWaitingForChats = false;
let reconnectAttempts = 0;
let isInitialized = false;

// WebSocket server with enhanced error handling
let wss = null;

// Initialize the backend
async function initializeBackend() {
    if (isInitialized) {
        log.warn('Backend already initialized');
        return;
    }

    try {
        log.info('Starting Karere Backend initialization');

        // Initialize service manager
        await serviceManager.initialize();

        // Initialize database
        await database.initialize();
        serviceManager.registerService('database', database);

        // Initialize WebSocket server
        await initializeWebSocketServer();
        serviceManager.registerService('websocket', { shutdown: closeWebSocketServer });

        // Initialize WhatsApp connection
        await connectToWhatsApp();

        isInitialized = true;
        log.info('Karere Backend initialized successfully');

    } catch (error) {
        log.error('Failed to initialize backend', error);
        process.exit(1);
    }
}

async function initializeWebSocketServer() {
    const timer = performance.start('websocket_server_init');

    try {
        wss = new WebSocketServer({
            port: PORT,
            perMessageDeflate: false // Disable compression for better performance
        });

        wss.on('connection', handleWebSocketConnection);
        wss.on('error', (error) => {
            log.error('WebSocket server error', error);
        });

        timer.end();
        log.info(`WebSocket server started on ws://localhost:${PORT}`);

    } catch (error) {
        timer.end({ error: true });
        throw errorHandler.websocket(error, 'server initialization');
    }
}

async function closeWebSocketServer() {
    if (wss) {
        return new Promise((resolve) => {
            wss.close(() => {
                log.info('WebSocket server closed');
                resolve();
            });
        });
    }
}

function getDisplayMessage(msg) {
    if (!msg || !msg.message) return '';
    const message = msg.message;
    if (message.conversation) return message.conversation;
    if (message.extendedTextMessage) return message.extendedTextMessage.text;
    if (message.imageMessage) return message.imageMessage.caption || '[Image]';
    if (message.videoMessage) return message.videoMessage.caption || '[Video]';
    return '[Unsupported Message]';
}

function handleWebSocketConnection(ws) {
    const timer = performance.start('websocket_connection');

    log.websocket('Frontend client connected');
    clientSocket = ws;

    // Send ready signal if Baileys is already connected
    if (baileysConnectionStatus === 'open') {
        log.websocket('Frontend connected while Baileys is ready. Sending ready signal.');
        sendToFrontend('baileys_ready', {});
    }

    ws.on('message', async (message) => {
        const messageTimer = performance.start('websocket_message_processing');

        try {
            const parsedMessage = JSON.parse(message);
            log.websocket('Received command from frontend', { type: parsedMessage.type });

            await handleFrontendCommand(parsedMessage);

            messageTimer.end({ type: parsedMessage.type });

        } catch (error) {
            messageTimer.end({ error: true });
            const errorResponse = errorHandler.websocket(error, 'message processing');
            sendToFrontend('error', errorResponse);
        }
    });

    ws.on('close', (code, reason) => {
        clientSocket = null;
        clientIsWaitingForChats = false;
        timer.end();
        log.websocket('Frontend client disconnected', { code, reason: reason?.toString() });
    });

    ws.on('error', (error) => {
        const errorResponse = errorHandler.websocket(error, 'connection');
        log.websocket('WebSocket connection error', errorResponse);
    });
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

        case 'typing_start':
            await handleTypingStart(data);
            break;

        case 'typing_stop':
            await handleTypingStop(data);
            break;

        case 'health_check':
            await handleHealthCheck();
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
        if (initialChatsPayload) {
            log.info('Client requested chats. Sending cached list.');
            sendToFrontend('initial_chats', initialChatsPayload);
        } else {
            // Try to load from database
            const dbChats = await database.getChats();
            if (dbChats.length > 0) {
                const chats = dbChats.map(chat => ({
                    jid: chat.jid,
                    name: chat.name || chat.jid,
                    lastMessage: chat.last_message_content || 'No messages yet',
                    timestamp: chat.last_message_timestamp,
                    unreadCount: chat.unread_count || 0
                }));

                sendToFrontend('initial_chats', { chats });
                log.info('Sent chats from database', { count: chats.length });
            } else {
                log.info('Cache is empty, setting client waiting flag to true.');
                clientIsWaitingForChats = true;
            }
        }
    } catch (error) {
        const errorResponse = errorHandler.database(error, 'get initial chats');
        sendToFrontend('error', errorResponse);
    }
}

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

async function handleSendMessage(data) {
    const timer = performance.start('send_message');
    const { to, message } = data;

    try {
        // Validate input
        if (!to || !message) {
            throw new Error('Missing required fields: to, message');
        }

        if (!sock || baileysConnectionStatus !== 'open') {
            throw new Error('Not connected to WhatsApp');
        }

        log.message('Sending message', { to, messageLength: message.length });

        // Generate message ID
        const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        // Send message via Baileys
        const sentMessage = await sock.sendMessage(to, { text: message });
        const actualMessageId = sentMessage.key.id;

        // Save to database
        await database.saveMessage(
            actualMessageId,
            to,
            true, // fromMe
            message,
            Date.now(),
            'text',
            'sent'
        );

        // Update chat in database
        await database.saveChat(to, null, actualMessageId, Date.now());

        // Confirm message sent
        sendToFrontend('message_sent', {
            to,
            message,
            messageId: actualMessageId,
            timestamp: Date.now()
        });

        timer.end({ to, messageLength: message.length });
        log.message('Message sent successfully', { to, messageId: actualMessageId });

    } catch (error) {
        timer.end({ error: true });
        const errorResponse = errorHandler.messaging(error, 'send message');
        sendToFrontend('message_error', errorResponse);

        // Try to save failed message to database for retry
        try {
            await database.saveMessage(
                `failed_${Date.now()}`,
                to,
                true,
                message,
                Date.now(),
                'text',
                'failed'
            );
        } catch (dbError) {
            log.error('Failed to save failed message to database', dbError);
        }
    }
}

async function handleGetMessageHistory(data) {
    const timer = performance.start('get_message_history');
    const { jid, limit = 50, offset = 0 } = data;

    try {
        log.message('Fetching message history', { jid, limit, offset });

        // First try to get from database
        let messages = await database.getMessages(jid, limit, offset);

        if (messages.length === 0 && sock && baileysConnectionStatus === 'open') {
            // If no messages in database, try to fetch from Baileys
            try {
                const baileysMessages = await sock.fetchMessageHistory(jid, limit);

                // Save to database and process
                for (const msg of baileysMessages) {
                    const messageContent = getDisplayMessage(msg);
                    if (messageContent) {
                        await database.saveMessage(
                            msg.key.id,
                            jid,
                            msg.key.fromMe,
                            messageContent,
                            msg.messageTimestamp * 1000, // Convert to milliseconds
                            'text',
                            'received'
                        );
                    }
                }

                // Get the saved messages
                messages = await database.getMessages(jid, limit, offset);

            } catch (baileysError) {
                log.warn('Failed to fetch from Baileys, using database only', baileysError);
            }
        }

        // Process messages for frontend
        const processedMessages = messages.map(msg => ({
            id: msg.id,
            from: msg.chat_jid,
            fromMe: msg.from_me === 1,
            text: msg.content,
            timestamp: msg.timestamp,
            status: msg.status
        }));

        sendToFrontend('message_history', { jid, messages: processedMessages });

        timer.end({ jid, messageCount: processedMessages.length });
        log.message('Message history sent', { jid, count: processedMessages.length });

    } catch (error) {
        timer.end({ error: true });
        const errorResponse = errorHandler.messaging(error, 'get message history');
        sendToFrontend('message_history_error', errorResponse);
    }
}

async function handleTypingStart(data) {
    const { to } = data;

    try {
        if (sock && baileysConnectionStatus === 'open') {
            await sock.sendPresenceUpdate('composing', to);
            log.debug('Typing indicator started', { to });
        }
    } catch (error) {
        log.error('Failed to send typing indicator', error, { to });
    }
}

async function handleTypingStop(data) {
    const { to } = data;

    try {
        if (sock && baileysConnectionStatus === 'open') {
            await sock.sendPresenceUpdate('paused', to);
            log.debug('Typing indicator stopped', { to });
        }
    } catch (error) {
        log.error('Failed to stop typing indicator', error, { to });
    }
}

async function handleHealthCheck() {
    try {
        const health = await serviceManager.runHealthChecks();
        const status = serviceManager.getStatus();

        sendToFrontend('health_status', {
            ...health,
            backend: status,
            baileys: {
                status: baileysConnectionStatus,
                connected: baileysConnectionStatus === 'open'
            }
        });

        log.debug('Health check completed', health);

    } catch (error) {
        const errorResponse = errorHandler.generic(error, 'health check');
        sendToFrontend('health_error', errorResponse);
    }
}

async function connectToWhatsApp() {
    const timer = performance.start('whatsapp_connection');

    try {
        log.baileys('Initializing WhatsApp connection');

        const { state, saveCreds } = await useMultiFileAuthState('baileys_auth_info');
        const { version } = await fetchLatestBaileysVersion();
        log.baileys(`Using WhatsApp version ${version.join('.')}`);

        sock = makeWASocket({
            version,
            auth: state,
            printQRInTerminal: false,
            browser: ['Karere', 'Desktop', '1.0.0'],
            connectTimeoutMs: 60000,
            defaultQueryTimeoutMs: 60000,
            keepAliveIntervalMs: 10000
        });

        sock.ev.on('connection.update', handleConnectionUpdate);
        sock.ev.on('creds.update', saveCreds);
        sock.ev.on('messages.upsert', handleMessagesUpsert);
        sock.ev.on('presence.update', handlePresenceUpdate);
        sock.ev.on('chats.set', handleHistorySet);
        sock.ev.on('messaging-history.set', handleHistorySet);

        timer.end();
        log.baileys('WhatsApp socket initialized successfully');

        return sock;

    } catch (error) {
        timer.end({ error: true });
        const errorResponse = errorHandler.baileys(error, 'connection initialization');

        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            log.warn(`Reconnection attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} in ${RECONNECT_DELAY}ms`);
            setTimeout(() => connectToWhatsApp(), RECONNECT_DELAY);
        } else {
            log.error('Max reconnection attempts reached');
            sendToFrontend('connection_failed', errorResponse);
        }
    }
}

async function handleConnectionUpdate(update) {
    const { connection, lastDisconnect, qr } = update;

    try {
        if (qr) {
            log.baileys('QR Code received, generating image');
            qrcode.toDataURL(qr, (err, url) => {
                if (err) {
                    log.error('Error generating QR code', err);
                    return;
                }
                sendToFrontend('qr', { url });
                log.baileys('QR code sent to frontend');
            });
        }

        baileysConnectionStatus = connection;

        if (connection === 'close') {
            initialChatsPayload = null;
            const statusCode = (lastDisconnect?.error instanceof Boom) ?
                lastDisconnect.error.output.statusCode : 500;
            const reason = lastDisconnect?.error?.message || 'Unknown reason';

            log.baileys('Connection closed', { statusCode, reason });
            sendToFrontend('connection_status', { status: 'closed', reason });

            if (statusCode === DisconnectReason.loggedOut) {
                log.baileys('Logged out, deleting credentials and restarting');
                try {
                    await fs.rm('baileys_auth_info', { recursive: true, force: true });
                    log.baileys('Authentication credentials deleted');
                } catch (e) {
                    log.error('Error deleting auth credentials', e);
                }
                reconnectAttempts = 0; // Reset for fresh start
                setTimeout(() => connectToWhatsApp(), 2000);

            } else if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                log.baileys(`Scheduling reconnection attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);
                setTimeout(() => connectToWhatsApp(), RECONNECT_DELAY);
            } else {
                log.error('Max reconnection attempts reached');
                sendToFrontend('connection_failed', { reason: 'Max reconnection attempts reached' });
            }

        } else if (connection === 'open') {
            reconnectAttempts = 0;
            log.baileys('WhatsApp connection is open');
            sendToFrontend('baileys_ready', {});
            sendToFrontend('connection_status', { status: 'open' });
            await loadInitialChats();

        } else if (connection === 'connecting') {
            log.baileys('Connecting to WhatsApp...');
            sendToFrontend('connection_status', { status: 'connecting' });
        }

    } catch (error) {
        log.error('Error in connection update handler', error);
    }
}

async function handleHistorySet(item) {
    const timer = performance.start('history_set');

    try {
        const eventType = item.isLatest ? 'messaging-history.set' : 'chats.set';
        log.baileys(`Received history via "${eventType}"`, { chatCount: item.chats.length });

        const chats = [];

        for (const chat of item.chats) {
            const chatData = {
                jid: chat.id,
                name: chat.name || chat.id,
                lastMessage: getDisplayMessage(chat.messages?.[0]) || 'No messages yet',
                timestamp: chat.messages?.[0]?.messageTimestamp * 1000 || Date.now(),
                unreadCount: chat.unreadCount || 0
            };

            chats.push(chatData);

            // Save to database
            await database.saveChat(
                chatData.jid,
                chatData.name,
                chat.messages?.[0]?.key?.id,
                chatData.timestamp
            );
        }

        initialChatsPayload = { chats };

        if (clientIsWaitingForChats) {
            log.baileys('Client was waiting for chats, sending now');
            sendToFrontend('initial_chats', initialChatsPayload);
            clientIsWaitingForChats = false;
        }

        timer.end({ chatCount: chats.length });

    } catch (error) {
        timer.end({ error: true });
        log.error('Error handling history set', error);
    }
}

// Add missing message handling functions
async function handleMessagesUpsert(m) {
    const timer = performance.start('message_upsert');

    try {
        const msg = m.messages[0];
        if (!msg.key.fromMe && m.type === 'notify') {
            const messageContent = getDisplayMessage(msg);
            if (messageContent) {
                // Save to database
                await database.saveMessage(
                    msg.key.id,
                    msg.key.remoteJid,
                    false, // fromMe
                    messageContent,
                    msg.messageTimestamp * 1000,
                    'text',
                    'received'
                );

                // Update chat
                await database.saveChat(msg.key.remoteJid, null, msg.key.id, msg.messageTimestamp * 1000);

                // Send to frontend
                sendToFrontend('newMessage', {
                    from: msg.key.remoteJid,
                    body: messageContent,
                    timestamp: msg.messageTimestamp * 1000
                });

                log.message('New message received', {
                    from: msg.key.remoteJid,
                    messageLength: messageContent.length
                });
            }
        }

        timer.end();

    } catch (error) {
        timer.end({ error: true });
        log.error('Error handling message upsert', error);
    }
}

async function handlePresenceUpdate(update) {
    try {
        const { id, presences } = update;
        for (const [jid, presence] of Object.entries(presences)) {
            if (presence.lastKnownPresence === 'composing') {
                sendToFrontend('typing_start', { from: jid });
            } else if (presence.lastKnownPresence === 'paused') {
                sendToFrontend('typing_stop', { from: jid });
            }
        }
    } catch (error) {
        log.error('Error handling presence update', error);
    }
}

async function loadInitialChats() {
    const timer = performance.start('load_initial_chats');

    try {
        log.baileys('Loading initial chats');

        // Try to get from database first
        const dbChats = await database.getChats();
        if (dbChats.length > 0) {
            const chats = dbChats.map(chat => ({
                jid: chat.jid,
                name: chat.name || chat.jid,
                lastMessage: chat.last_message_content || 'No messages yet',
                timestamp: chat.last_message_timestamp,
                unreadCount: chat.unread_count || 0
            }));

            initialChatsPayload = { chats };

            if (clientIsWaitingForChats) {
                sendToFrontend('initial_chats', initialChatsPayload);
                clientIsWaitingForChats = false;
            }

            timer.end({ source: 'database', count: chats.length });
            log.baileys('Initial chats loaded from database', { count: chats.length });
        }

    } catch (error) {
        timer.end({ error: true });
        log.error('Error loading initial chats', error);
    }
}

// Main initialization
async function main() {
    try {
        await initializeBackend();
    } catch (error) {
        log.error('FATAL ERROR in main execution', error);
        process.exit(1);
    }
}

// Start the application
main().catch((error) => {
    console.error('Failed to start application:', error);
    process.exit(1);
});

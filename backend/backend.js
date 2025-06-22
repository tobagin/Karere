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

        case 'sync_contacts':
            await handleSyncContacts();
            break;

        case 'get_contact_info':
            await handleGetContactInfo(data);
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
                    name: chat.contact_name || chat.name || chat.jid, // Prefer contact name
                    lastMessage: chat.last_message_content || 'No messages yet',
                    timestamp: chat.last_message_timestamp,
                    unreadCount: chat.unread_count || 0,
                    avatarBase64: chat.contact_avatar_base64,
                    phoneNumber: chat.contact_phone_number
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

async function handleSyncContacts() {
    const timer = performance.start('sync_contacts_manual');

    try {
        log.info('Manual contact synchronization requested');

        if (!sock || baileysConnectionStatus !== 'open') {
            throw new Error('Not connected to WhatsApp');
        }

        // Get all contacts that need syncing
        const chats = await database.getChats(200);
        let syncedCount = 0;
        let errorCount = 0;

        sendToFrontend('sync_contacts_started', { totalChats: chats.length });

        for (const chat of chats) {
            try {
                const jid = chat.jid;
                // Avatar sync removed - using base64 only now

                // Send progress update every 10 contacts
                if ((syncedCount + errorCount) % 10 === 0) {
                    sendToFrontend('sync_contacts_progress', {
                        processed: syncedCount + errorCount,
                        synced: syncedCount,
                        total: chats.length
                    });
                }

                // Small delay to avoid rate limiting
                await new Promise(resolve => setTimeout(resolve, 200));

            } catch (contactError) {
                errorCount++;
                log.debug('Failed to sync contact', {
                    jid: chat.jid,
                    error: contactError.message
                });
            }
        }

        timer.end({ syncedCount, errorCount });

        sendToFrontend('sync_contacts_completed', {
            syncedCount,
            errorCount,
            totalProcessed: chats.length
        });

        log.info('Manual contact synchronization completed', {
            syncedCount,
            errorCount
        });

    } catch (error) {
        timer.end({ error: true });
        const errorResponse = errorHandler.generic(error, 'sync contacts');
        sendToFrontend('sync_contacts_error', errorResponse);
    }
}

async function handleGetContactInfo(data) {
    const timer = performance.start('get_contact_info');
    const { jid } = data;

    try {
        if (!jid) {
            throw new Error('Missing required field: jid');
        }

        log.debug('Getting contact info', { jid });

        // Get contact from database
        const contact = await database.getContact(jid);

        // Get chat info
        const chat = await database.getChatWithContact(jid);

        // Get avatar base64 data
        let avatarBase64 = contact?.avatar_base64;

        const contactInfo = {
            jid,
            name: contact?.name || chat?.contact_name || chat?.name || jid,
            phoneNumber: contact?.phone_number || chat?.contact_phone_number,
            avatarBase64: avatarBase64,
            isBlocked: contact?.is_blocked || false,
            lastSeen: chat?.last_message_timestamp,
            messageCount: 0 // Could be enhanced to count messages
        };

        sendToFrontend('contact_info', { jid, contactInfo });

        timer.end({ jid, hasAvatar: !!avatarBase64 });
        log.debug('Contact info sent', { jid, hasAvatar: !!avatarBase64 });

    } catch (error) {
        timer.end({ error: true });
        const errorResponse = errorHandler.generic(error, 'get contact info');
        sendToFrontend('contact_info_error', { jid, error: errorResponse });
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

            // Check if this is first login or if we need comprehensive sync
            const isFirstLogin = await isFirstTimeLogin();
            if (isFirstLogin) {
                log.info('First time login detected, starting comprehensive data download');
                sendToFrontend('initial_download_started', { message: 'Downloading your WhatsApp data...' });

                // Try to get chats directly from the socket store first
                await tryFetchChatsFromStore();

                await performComprehensiveDataDownload();
            } else {
                await loadInitialChats();
                // Sync existing chats to update any missing data
                await syncExistingChats();
                // Perform incremental sync for existing data
                await performIncrementalSync();
            }

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

            // Save chat to database
            await database.saveChat(
                chatData.jid,
                chatData.name,
                chat.messages?.[0]?.key?.id,
                chatData.timestamp
            );

            // Save contact information if available
            if (chat.name && chat.name !== chat.id) {
                await database.saveContact(chat.id, chat.name);
                log.debug(`Saved contact: ${chat.id} -> ${chat.name}`);
            }

            // Save messages from this chat
            if (chat.messages && chat.messages.length > 0) {
                for (const msg of chat.messages.slice(0, 10)) { // Save up to 10 recent messages
                    try {
                        const messageContent = getDisplayMessage(msg);
                        if (messageContent && msg.key?.id) {
                            await database.saveMessage(
                                msg.key.id,
                                chat.id,
                                msg.key.fromMe || false,
                                messageContent,
                                msg.messageTimestamp * 1000,
                                'text',
                                'received',
                                msg.pushName || chat.name
                            );
                            log.debug(`Saved message: ${msg.key.id} in chat ${chat.id}`);
                        }
                    } catch (msgError) {
                        log.debug('Failed to save message from history', {
                            chatId: chat.id,
                            messageId: msg.key?.id,
                            error: msgError.message
                        });
                    }
                }
            }
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
                // Get contact name from WhatsApp data
                const contactName = msg.pushName || msg.notify || null;
                const jid = msg.key.remoteJid;

                // Save message to database with sender name
                await database.saveMessage(
                    msg.key.id,
                    jid,
                    false, // fromMe
                    messageContent,
                    msg.messageTimestamp * 1000,
                    'text',
                    'received',
                    contactName // Pass sender name
                );

                // Get updated contact info
                const contact = await database.getContact(jid);

                // Send to frontend with enhanced data
                sendToFrontend('newMessage', {
                    from: jid,
                    body: messageContent,
                    timestamp: msg.messageTimestamp * 1000,
                    contactName: contactName,
                    avatarBase64: contact?.avatar_base64,
                    senderName: contactName
                });

                log.message('New message received', {
                    from: jid,
                    messageLength: messageContent.length,
                    hasAvatar: !!contact?.avatar_base64
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
                name: chat.contact_name || chat.name || chat.jid, // Prefer contact name
                lastMessage: chat.last_message_content || 'No messages yet',
                timestamp: chat.last_message_timestamp,
                unreadCount: chat.unread_count || 0,
                avatarBase64: chat.contact_avatar_base64,
                phoneNumber: chat.contact_phone_number
            }));

            initialChatsPayload = { chats };

            if (clientIsWaitingForChats) {
                sendToFrontend('initial_chats', initialChatsPayload);
                clientIsWaitingForChats = false;
            }

            timer.end({ source: 'database', count: chats.length });
            log.baileys('Initial chats loaded from database', { count: chats.length });

            // Start background contact synchronization
            syncContactsInBackground();
        }

    } catch (error) {
        timer.end({ error: true });
        log.error('Error loading initial chats', error);
    }
}

async function syncContactsInBackground() {
    const timer = performance.start('sync_contacts_background');

    try {
        if (!sock || baileysConnectionStatus !== 'open') {
            log.debug('Skipping contact sync - not connected');
            return;
        }

        log.info('Starting background contact synchronization');

        // Get all chats that need contact info
        const chats = await database.getChats(100);
        let syncedCount = 0;

        for (const chat of chats) {
            try {
                const jid = chat.jid;

                // Always try to save contact info if we have a name
                let contactName = chat.contact_name || chat.name;

                // Save contact if we have a meaningful name (not just the JID)
                if (contactName && contactName !== jid && !contactName.includes('@')) {
                    await database.saveContact(jid, contactName);
                    syncedCount++;
                    log.debug(`Synced contact: ${jid} -> ${contactName}`);
                }

                // Small delay to avoid overwhelming WhatsApp
                await new Promise(resolve => setTimeout(resolve, 100));

            } catch (contactError) {
                log.debug('Failed to sync contact', {
                    jid: chat.jid,
                    error: contactError.message
                });
            }
        }

        timer.end({ syncedCount });
        log.info('Background contact synchronization completed', { syncedCount });

    } catch (error) {
        timer.end({ error: true });
        log.error('Error in background contact sync', error);
    }
}

// Sync existing chats to update any missing data
async function syncExistingChats() {
    const timer = performance.start('sync_existing_chats');

    try {
        if (!sock || baileysConnectionStatus !== 'open') {
            log.debug('Skipping existing chat sync - not connected');
            return;
        }

        log.info('Starting sync of existing chats');

        // Get all chats from database
        const chats = await database.getChats(100);
        let syncedCount = 0;

        for (const chat of chats) {
            try {
                const jid = chat.jid;
                // Basic sync - just ensure chat data is up to date
                // Avatar sync removed - using base64 only now

                // Small delay to avoid overwhelming WhatsApp
                await new Promise(resolve => setTimeout(resolve, 50));

            } catch (chatError) {
                log.debug('Failed to sync existing chat', {
                    jid: chat.jid,
                    error: chatError.message
                });
            }
        }

        timer.end({ syncedCount });
        log.info('Existing chat sync completed', { syncedCount });

    } catch (error) {
        timer.end({ error: true });
        log.error('Error syncing existing chats', error);
    }
}

// Try to fetch chats directly from the socket store
async function tryFetchChatsFromStore() {
    const timer = performance.start('fetch_chats_from_store');

    try {
        if (!sock || baileysConnectionStatus !== 'open') {
            log.debug('Cannot fetch chats from store - not connected');
            return false;
        }

        log.info('Attempting to fetch chats from socket store');

        // Get chats from the store
        const storeChats = Object.values(sock.store?.chats || {});
        log.info(`Found ${storeChats.length} chats in socket store`);

        if (storeChats.length === 0) {
            return false;
        }

        const processedChats = [];

        // Process up to 50 chats
        for (const chat of storeChats.slice(0, 50)) {
            try {
                const chatData = {
                    jid: chat.id,
                    name: chat.name || chat.id,
                    lastMessage: 'Loading messages...',
                    timestamp: Date.now(),
                    unreadCount: chat.unreadCount || 0
                };

                processedChats.push(chatData);

                // Save chat to database
                await database.saveChat(
                    chatData.jid,
                    chatData.name,
                    null, // No message ID yet
                    chatData.timestamp
                );

                // Save contact information if available
                if (chat.name && chat.name !== chat.id) {
                    await database.saveContact(chat.id, chat.name);
                    log.debug(`Saved contact from store: ${chat.id} -> ${chat.name}`);
                }

                log.debug(`Processed chat from store: ${chatData.jid}`);

            } catch (chatError) {
                log.debug('Failed to process chat from store', {
                    chatId: chat.id,
                    error: chatError.message
                });
            }
        }

        if (processedChats.length > 0) {
            log.info(`Successfully processed ${processedChats.length} chats from store`);

            // Set the initial chats payload
            initialChatsPayload = { chats: processedChats };

            // Send to frontend if waiting
            if (clientIsWaitingForChats) {
                log.info('Client was waiting for chats, sending store chats now');
                sendToFrontend('initial_chats', initialChatsPayload);
                clientIsWaitingForChats = false;
            }

            timer.end({ success: true, count: processedChats.length });
            return true;
        }

        timer.end({ success: false, count: 0 });
        return false;

    } catch (error) {
        timer.end({ error: true });
        log.error('Error fetching chats from store', error);
        return false;
    }
}

// Check if this is the first time login (no chats in database)
async function isFirstTimeLogin() {
    try {
        const chats = await database.getChats(1);
        return chats.length === 0;
    } catch (error) {
        log.error('Error checking first time login', error);
        return false;
    }
}

// Perform comprehensive data download for first-time login
async function performComprehensiveDataDownload() {
    const timer = performance.start('comprehensive_data_download');

    try {
        log.info('Starting comprehensive data download');
        sendToFrontend('download_progress', {
            stage: 'starting',
            message: 'Initializing data download...',
            progress: 0
        });

        // Wait for WhatsApp to send initial chat history
        await waitForInitialHistory();

        // Get all chats from database
        const chats = await database.getChats(1000);
        log.info(`Found ${chats.length} chats to process`);

        if (chats.length === 0) {
            log.warn('No chats found after waiting for history');
            sendToFrontend('download_complete', {
                message: 'No chats found to download',
                stats: { chats: 0, contacts: 0, messages: 0, avatars: 0 }
            });
            return;
        }

        sendToFrontend('download_progress', {
            stage: 'downloading',
            message: `Downloading data for ${chats.length} chats...`,
            progress: 10,
            totalChats: chats.length
        });

        let processedChats = 0;
        let downloadedMessages = 0;
        let downloadedAvatars = 0;
        let updatedContacts = 0;

        // Process each chat
        for (const chat of chats) {
            try {
                const jid = chat.jid;
                log.debug(`Processing chat: ${jid}`);

                // Download message history for this chat
                const messageCount = await downloadMessageHistory(jid);
                downloadedMessages += messageCount;

                // Download contact info and avatar
                const contactUpdated = await downloadContactInfo(jid);
                if (contactUpdated.nameUpdated) updatedContacts++;
                if (contactUpdated.avatarDownloaded) downloadedAvatars++;

                processedChats++;

                // Send progress update every 5 chats or on last chat
                if (processedChats % 5 === 0 || processedChats === chats.length) {
                    const progress = 10 + (processedChats / chats.length) * 80; // 10-90%
                    sendToFrontend('download_progress', {
                        stage: 'downloading',
                        message: `Processed ${processedChats}/${chats.length} chats`,
                        progress: Math.round(progress),
                        processedChats,
                        totalChats: chats.length,
                        stats: {
                            messages: downloadedMessages,
                            avatars: downloadedAvatars,
                            contacts: updatedContacts
                        }
                    });
                }

                // Small delay to avoid overwhelming WhatsApp
                await new Promise(resolve => setTimeout(resolve, 200));

            } catch (chatError) {
                log.warn(`Failed to process chat ${chat.jid}`, chatError);
                processedChats++;
            }
        }

        // Final statistics
        const finalStats = {
            chats: chats.length,
            messages: downloadedMessages,
            contacts: updatedContacts,
            avatars: downloadedAvatars
        };

        timer.end(finalStats);
        log.info('Comprehensive data download completed', finalStats);

        sendToFrontend('download_progress', {
            stage: 'complete',
            message: 'Download complete!',
            progress: 100,
            stats: finalStats
        });

        sendToFrontend('download_complete', {
            message: 'All your WhatsApp data has been downloaded successfully',
            stats: finalStats
        });

        // Mark first login as complete
        await database.setSetting('first_login_complete', true);

    } catch (error) {
        timer.end({ error: true });
        log.error('Error in comprehensive data download', error);
        sendToFrontend('download_error', {
            message: 'Failed to download data',
            error: error.message
        });
    }
}

// Wait for WhatsApp to send initial chat history
async function waitForInitialHistory() {
    return new Promise(async (resolve) => {
        const maxWaitTime = 30000; // 30 seconds
        const checkInterval = 1000; // 1 second
        let waitTime = 0;

        // Try to actively fetch chat list from WhatsApp
        try {
            if (sock && baileysConnectionStatus === 'open') {
                log.info('Actively fetching chat list from WhatsApp');

                // Try to get chats using the store
                const chats = Object.values(sock.store?.chats || {});
                log.info(`Found ${chats.length} chats in store`);

                if (chats.length > 0) {
                    // Process the chats we found
                    const processedChats = [];

                    for (const chat of chats.slice(0, 50)) { // Limit to first 50 chats
                        try {
                            const chatData = {
                                jid: chat.id,
                                name: chat.name || chat.id,
                                lastMessage: 'Loading...',
                                timestamp: Date.now(),
                                unreadCount: chat.unreadCount || 0
                            };

                            processedChats.push(chatData);

                            // Save to database
                            await database.saveChat(
                                chatData.jid,
                                chatData.name,
                                null, // No message ID yet
                                chatData.timestamp
                            );

                        } catch (chatError) {
                            log.debug('Failed to process chat from store', { chatId: chat.id, error: chatError.message });
                        }
                    }

                    if (processedChats.length > 0) {
                        log.info(`Processed ${processedChats.length} chats from store`);
                        // Trigger the history set handler manually
                        await handleHistorySet({ chats: chats.slice(0, 50), isLatest: true });
                        return; // Exit early since we found chats
                    }
                }
            }
        } catch (error) {
            log.debug('Failed to fetch chats from store', error);
        }

        const checkForHistory = async () => {
            try {
                const chats = await database.getChats(1);
                if (chats.length > 0) {
                    log.info('Initial history received');
                    resolve();
                    return;
                }
            } catch (error) {
                log.debug('Error checking for history', error);
            }

            waitTime += checkInterval;
            if (waitTime >= maxWaitTime) {
                log.warn('Timeout waiting for initial history');
                resolve();
            } else {
                setTimeout(checkForHistory, checkInterval);
            }
        };

        checkForHistory();
    });
}

// Download message history for a specific chat
async function downloadMessageHistory(jid, limit = 50) {
    const timer = performance.start('download_message_history');

    try {
        if (!sock || baileysConnectionStatus !== 'open') {
            return 0;
        }

        // Check if we already have messages for this chat
        const existingMessages = await database.getMessages(jid, 5);
        if (existingMessages.length > 0) {
            log.debug(`Chat ${jid} already has messages, skipping download`);
            return 0;
        }

        log.debug(`Downloading message history for ${jid}`);

        // Fetch message history from WhatsApp
        const messages = await sock.fetchMessageHistory(jid, limit);
        let savedCount = 0;

        for (const msg of messages) {
            try {
                const messageContent = getDisplayMessage(msg);
                if (messageContent) {
                    await database.saveMessage(
                        msg.key.id,
                        jid,
                        msg.key.fromMe,
                        messageContent,
                        msg.messageTimestamp * 1000,
                        'text',
                        'received'
                    );
                    savedCount++;
                }
            } catch (msgError) {
                log.debug('Failed to save message', { jid, error: msgError.message });
            }
        }

        timer.end({ jid, savedCount });
        log.debug(`Downloaded ${savedCount} messages for ${jid}`);
        return savedCount;

    } catch (error) {
        timer.end({ error: true });
        log.debug(`Failed to download message history for ${jid}`, error);
        return 0;
    }
}

// Download contact information and avatar for a specific JID
async function downloadContactInfo(jid) {
    const timer = performance.start('download_contact_info');

    try {
        let nameUpdated = false;
        let avatarDownloaded = false;

        if (!sock || baileysConnectionStatus !== 'open') {
            return { nameUpdated, avatarDownloaded };
        }

        // Get existing contact info
        const existingContact = await database.getContact(jid);

        // Try to get contact name from WhatsApp if we don't have it
        if (!existingContact?.name || existingContact.name === jid) {
            try {
                // For group chats, get group metadata
                if (jid.endsWith('@g.us')) {
                    const groupMetadata = await sock.groupMetadata(jid);
                    if (groupMetadata?.subject) {
                        await database.saveContact(jid, groupMetadata.subject);
                        nameUpdated = true;
                        log.debug(`Updated group name: ${jid} -> ${groupMetadata.subject}`);
                    }
                }
                // For individual contacts, we'll rely on message pushName or existing data
            } catch (nameError) {
                log.debug(`Failed to get contact name for ${jid}`, nameError);
            }
        }

        // Avatar downloading removed - using base64 only now

        timer.end({ jid, nameUpdated, avatarDownloaded });
        return { nameUpdated, avatarDownloaded };

    } catch (error) {
        timer.end({ error: true });
        log.debug(`Failed to download contact info for ${jid}`, error);
        return { nameUpdated: false, avatarDownloaded: false };
    }
}

// Perform incremental sync for existing installations
async function performIncrementalSync() {
    const timer = performance.start('incremental_sync');

    try {
        log.info('Starting incremental sync');
        sendToFrontend('sync_started', { message: 'Syncing latest data...' });

        // Load initial chats from database first
        await loadInitialChats();

        // Perform comprehensive sync to catch any changes
        await performComprehensiveSync();

        timer.end();
        log.info('Incremental sync completed');
        sendToFrontend('sync_complete', { message: 'Data sync complete' });

    } catch (error) {
        timer.end({ error: true });
        log.error('Error in incremental sync', error);
        sendToFrontend('sync_error', {
            message: 'Failed to sync data',
            error: error.message
        });
    }
}

// Perform comprehensive sync to update existing data
async function performComprehensiveSync() {
    const timer = performance.start('comprehensive_sync');

    try {
        if (!sock || baileysConnectionStatus !== 'open') {
            log.warn('Cannot perform sync - not connected to WhatsApp');
            return;
        }

        log.info('Starting comprehensive sync');
        sendToFrontend('sync_progress', {
            stage: 'starting',
            message: 'Checking for updates...',
            progress: 0
        });

        // Get last sync timestamp
        const lastSyncTime = await database.getSetting('last_sync_timestamp', 0);
        const currentTime = Date.now();

        log.info(`Last sync: ${new Date(lastSyncTime).toISOString()}, Current: ${new Date(currentTime).toISOString()}`);

        // Get all chats from database
        const chats = await database.getChats(1000);
        log.info(`Syncing ${chats.length} chats`);

        if (chats.length === 0) {
            log.info('No chats to sync');
            return;
        }

        sendToFrontend('sync_progress', {
            stage: 'syncing',
            message: `Syncing ${chats.length} chats...`,
            progress: 10,
            totalChats: chats.length
        });

        let processedChats = 0;
        let updatedChats = 0;
        let newMessages = 0;
        let updatedContacts = 0;
        let downloadedAvatars = 0;

        // Process each chat for updates
        for (const chat of chats) {
            try {
                const jid = chat.jid;
                log.debug(`Syncing chat: ${jid}`);

                // Check for new messages since last sync
                const messageUpdates = await syncChatMessages(jid, lastSyncTime);
                newMessages += messageUpdates;

                // Update contact information
                const contactUpdates = await syncContactData(jid);
                if (contactUpdates.nameUpdated) updatedContacts++;
                if (contactUpdates.avatarDownloaded) downloadedAvatars++;

                if (messageUpdates > 0 || contactUpdates.nameUpdated || contactUpdates.avatarDownloaded) {
                    updatedChats++;
                }

                processedChats++;

                // Send progress update every 10 chats or on last chat
                if (processedChats % 10 === 0 || processedChats === chats.length) {
                    const progress = 10 + (processedChats / chats.length) * 80; // 10-90%
                    sendToFrontend('sync_progress', {
                        stage: 'syncing',
                        message: `Synced ${processedChats}/${chats.length} chats`,
                        progress: Math.round(progress),
                        processedChats,
                        totalChats: chats.length,
                        stats: {
                            updatedChats,
                            newMessages,
                            updatedContacts,
                            downloadedAvatars
                        }
                    });
                }

                // Small delay to avoid overwhelming WhatsApp
                await new Promise(resolve => setTimeout(resolve, 150));

            } catch (chatError) {
                log.warn(`Failed to sync chat ${chat.jid}`, chatError);
                processedChats++;
            }
        }

        // Update last sync timestamp
        await database.setSetting('last_sync_timestamp', currentTime);

        // Final statistics
        const syncStats = {
            totalChats: chats.length,
            updatedChats,
            newMessages,
            updatedContacts,
            downloadedAvatars,
            syncDuration: Date.now() - currentTime
        };

        timer.end(syncStats);
        log.info('Comprehensive sync completed', syncStats);

        sendToFrontend('sync_progress', {
            stage: 'complete',
            message: 'Sync complete!',
            progress: 100,
            stats: syncStats
        });

        // If there were significant updates, refresh the chat list
        if (updatedChats > 0 || newMessages > 0) {
            await refreshChatList();
        }

    } catch (error) {
        timer.end({ error: true });
        log.error('Error in comprehensive sync', error);
        sendToFrontend('sync_error', {
            message: 'Failed to sync data',
            error: error.message
        });
    }
}

// Sync messages for a specific chat since last sync time
async function syncChatMessages(jid, lastSyncTime) {
    const timer = performance.start('sync_chat_messages');

    try {
        if (!sock || baileysConnectionStatus !== 'open') {
            return 0;
        }

        // Get the most recent message timestamp from database
        const recentMessages = await database.getMessages(jid, 1);
        const lastMessageTime = recentMessages.length > 0 ? recentMessages[0].timestamp : lastSyncTime;

        // Only fetch if we haven't checked recently (avoid too frequent checks)
        const timeSinceLastCheck = Date.now() - lastMessageTime;
        if (timeSinceLastCheck < 60000) { // Less than 1 minute
            return 0;
        }

        log.debug(`Checking for new messages in ${jid} since ${new Date(lastMessageTime).toISOString()}`);

        // Fetch recent message history
        const messages = await sock.fetchMessageHistory(jid, 20);
        let newMessageCount = 0;

        for (const msg of messages) {
            try {
                const messageTime = msg.messageTimestamp * 1000;

                // Only process messages newer than our last known message
                if (messageTime <= lastMessageTime) {
                    continue;
                }

                const messageContent = getDisplayMessage(msg);
                if (messageContent) {
                    // Check if message already exists
                    const existingMessage = await database.getMessage(msg.key.id);
                    if (!existingMessage) {
                        await database.saveMessage(
                            msg.key.id,
                            jid,
                            msg.key.fromMe,
                            messageContent,
                            messageTime,
                            'text',
                            'received',
                            msg.pushName || null
                        );
                        newMessageCount++;
                        log.debug(`Synced new message in ${jid}: ${msg.key.id}`);
                    }
                }
            } catch (msgError) {
                log.debug('Failed to sync message', { jid, messageId: msg.key.id, error: msgError.message });
            }
        }

        timer.end({ jid, newMessageCount });
        if (newMessageCount > 0) {
            log.info(`Synced ${newMessageCount} new messages for ${jid}`);
        }
        return newMessageCount;

    } catch (error) {
        timer.end({ error: true });
        log.debug(`Failed to sync messages for ${jid}`, error);
        return 0;
    }
}

// Sync contact data for a specific JID
async function syncContactData(jid) {
    const timer = performance.start('sync_contact_data');

    try {
        let nameUpdated = false;
        let avatarDownloaded = false;

        if (!sock || baileysConnectionStatus !== 'open') {
            return { nameUpdated, avatarDownloaded };
        }

        // Get existing contact info
        const existingContact = await database.getContact(jid);

        // Check if we need to update group metadata
        if (jid.endsWith('@g.us')) {
            try {
                const groupMetadata = await sock.groupMetadata(jid);
                if (groupMetadata?.subject && groupMetadata.subject !== existingContact?.name) {
                    await database.saveContact(jid, groupMetadata.subject);
                    nameUpdated = true;
                    log.debug(`Updated group name: ${jid} -> ${groupMetadata.subject}`);
                }
            } catch (groupError) {
                log.debug(`Failed to get group metadata for ${jid}`, groupError);
            }
        }

        // Avatar sync removed - using base64 only now

        timer.end({ jid, nameUpdated, avatarDownloaded });
        return { nameUpdated, avatarDownloaded };

    } catch (error) {
        timer.end({ error: true });
        log.debug(`Failed to sync contact data for ${jid}`, error);
        return { nameUpdated: false, avatarDownloaded: false };
    }
}

// Refresh the chat list and send to frontend
async function refreshChatList() {
    try {
        log.info('Refreshing chat list');

        const dbChats = await database.getChats();
        const chats = dbChats.map(chat => ({
            jid: chat.jid,
            name: chat.contact_name || chat.name || chat.jid,
            lastMessage: chat.last_message_content || 'No messages yet',
            timestamp: chat.last_message_timestamp,
            unreadCount: chat.unread_count || 0,
            avatarBase64: chat.contact_avatar_base64,
            phoneNumber: chat.contact_phone_number
        }));

        initialChatsPayload = { chats };
        sendToFrontend('chats_updated', initialChatsPayload);

        log.info(`Refreshed chat list with ${chats.length} chats`);

    } catch (error) {
        log.error('Failed to refresh chat list', error);
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

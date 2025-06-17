// backend.js
// This script sets up the Baileys WhatsApp connection and a WebSocket server
// to communicate with the Python GTK4 frontend.

import { Boom } from '@hapi/boom';
import baileys from '@whiskeysockets/baileys';
import { WebSocketServer } from 'ws';
import qrcode from 'qrcode';
import fs from 'fs/promises'; // Import the file system module for automatic cleanup

const makeWASocket = baileys.default;
const {
    DisconnectReason,
    useMultiFileAuthState,
    fetchLatestBaileysVersion
} = baileys;

const PORT = 8765;
const wss = new WebSocketServer({ port: PORT });

let clientSocket = null;
let initialChatsPayload = null; // Cache for the initial chat list
let baileysConnectionStatus = 'closed'; // Track the Baileys connection status
let sock = null; // Make the socket instance accessible globally within the module
let clientIsWaitingForChats = false; // Flag to track if the client has requested chats

console.log(`WebSocket server started on ws://localhost:${PORT}`);

function getDisplayMessage(msg) {
    if (!msg || !msg.message) return '';
    const message = msg.message;
    if (message.conversation) return message.conversation;
    if (message.extendedTextMessage) return message.extendedTextMessage.text;
    if (message.imageMessage) return message.imageMessage.caption || '[Image]';
    if (message.videoMessage) return message.videoMessage.caption || '[Video]';
    return '[Unsupported Message]';
}

wss.on('connection', ws => {
    console.log('Frontend client connected');
    clientSocket = ws;

    if (baileysConnectionStatus === 'open') {
        console.log('Frontend connected while Baileys is ready. Sending ready signal.');
        sendToFrontend('baileys_ready', {});
    }

    ws.on('message', message => {
        try {
            const parsedMessage = JSON.parse(message);
            console.log('Received command from frontend:', parsedMessage.type);

            if (parsedMessage.type === 'get_initial_chats') {
                if (initialChatsPayload) {
                    console.log('Client requested chats. Sending cached list.');
                    sendToFrontend('initial_chats', initialChatsPayload);
                } else {
                    console.log('Cache is empty, setting client waiting flag to true.');
                    clientIsWaitingForChats = true;
                }
            }

        } catch (error) {
            console.error('Error processing message from frontend:', error);
        }
    });

    ws.on('close', () => {
        clientSocket = null;
        clientIsWaitingForChats = false; // Reset flag on disconnect
        console.log('Frontend client disconnected');
    });
    ws.on('error', (error) => { console.error('WebSocket error:', error); });
});

function sendToFrontend(type, data) {
    if (clientSocket && clientSocket.readyState === clientSocket.OPEN) {
        clientSocket.send(JSON.stringify({ type, data }));
    }
}

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('baileys_auth_info');
    const { version } = await fetchLatestBaileysVersion();
	console.log(`using WA v${version.join('.')}`);
    
    // Assign to the module-level variable
    sock = makeWASocket({ version, auth: state, printQRInTerminal: false });

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;
        baileysConnectionStatus = connection;

        if (qr) {
            qrcode.toDataURL(qr, (err, url) => {
                if (err) return console.error('Error generating QR code', err);
                sendToFrontend('qr', { url: url });
            });
        }

        if (connection === 'close') {
            initialChatsPayload = null;
            const statusCode = (lastDisconnect.error instanceof Boom) ? lastDisconnect.error.output.statusCode : 500;
            
            if (statusCode === DisconnectReason.loggedOut) {
                console.log('Connection closed: Logged Out. Deleting authentication credentials and restarting...');
                try {
                    // Automatically delete the auth folder
                    await fs.rm('baileys_auth_info', { recursive: true, force: true });
                    console.log('Authentication credentials deleted.');
                } catch (e) {
                    console.error('Error deleting auth credentials:', e);
                }
                // Restart the connection process to get a new QR code
                connectToWhatsApp();
            } else {
                console.log(`Connection closed due to statusCode ${statusCode}. Reconnecting...`);
                connectToWhatsApp();
            }

        } else if (connection === 'open') {
            console.log("WhatsApp connection is open. Sending baileys_ready signal.");
            sendToFrontend('baileys_ready', {});
        }
    });

    sock.ev.on('creds.update', saveCreds);

    // Create a shared handler for history events to avoid duplicate code
    const handleHistorySet = (item) => {
        const eventType = item.isLatest ? 'messaging-history.set' : 'chats.set';
        console.log(`Received history via "${eventType}" with ${item.chats.length} chats. Caching.`);
        
        const chats = item.chats.map(chat => ({
            jid: chat.id,
            name: chat.name || chat.id,
            lastMessage: getDisplayMessage(chat.messages?.[0]) || 'No messages yet'
        }));
        initialChatsPayload = { chats };
        
        // If the client was already waiting for this list, send it now.
        if (clientIsWaitingForChats) {
            console.log("Client was waiting for chats. Sending now.");
            sendToFrontend('initial_chats', initialChatsPayload);
            clientIsWaitingForChats = false; // Reset the flag
        }
    };

    // Listen to both events. Whichever fires first will populate the cache.
    sock.ev.on('chats.set', handleHistorySet);
    sock.ev.on('messaging-history.set', handleHistorySet);


    sock.ev.on('messages.upsert', m => {
        const msg = m.messages[0];
        if (!msg.key.fromMe && m.type === 'notify') {
             const messageContent = getDisplayMessage(msg);
             if (messageContent) {
                 sendToFrontend('newMessage', { from: msg.key.remoteJid, body: messageContent });
             }
        }
    });

    return sock;
}

async function main() {
    try {
        await connectToWhatsApp();
    } catch (e) {
        console.error("FATAL ERROR in main execution:", e);
    }
}

main();
console.log('Baileys setup process initiated.');

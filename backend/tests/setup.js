// tests/setup.js
// Global test setup and configuration

const fs = require('fs').promises;
const path = require('path');

// Global test configuration
global.TEST_CONFIG = {
    DATABASE_PATH: ':memory:', // Use in-memory database for tests
    LOG_LEVEL: 'error', // Reduce log noise during tests
    WEBSOCKET_PORT: 8766, // Different port for tests
    TEST_TIMEOUT: 10000, // 10 second timeout for tests
};

// Mock console methods to reduce noise during tests
const originalConsole = { ...console };
global.console = {
    ...console,
    log: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: originalConsole.error, // Keep errors visible
    debug: jest.fn(),
};

// Global test utilities
global.testUtils = {
    // Create a temporary directory for test files
    async createTempDir() {
        const tempDir = path.join(process.cwd(), 'tests', 'temp', `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
        await fs.mkdir(tempDir, { recursive: true });
        return tempDir;
    },

    // Clean up temporary directory
    async cleanupTempDir(tempDir) {
        try {
            await fs.rm(tempDir, { recursive: true, force: true });
        } catch (error) {
            // Ignore cleanup errors
        }
    },

    // Wait for a condition to be true
    async waitFor(condition, timeout = 5000, interval = 100) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            if (await condition()) {
                return true;
            }
            await new Promise(resolve => setTimeout(resolve, interval));
        }
        throw new Error(`Condition not met within ${timeout}ms`);
    },

    // Create mock WebSocket client
    createMockWebSocket() {
        const mockWs = {
            send: jest.fn(),
            close: jest.fn(),
            readyState: 1, // OPEN
            OPEN: 1,
            CLOSED: 3,
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
        };
        return mockWs;
    },

    // Create mock Baileys socket
    createMockBaileysSocket() {
        const mockSocket = {
            ev: {
                on: jest.fn(),
                off: jest.fn(),
                emit: jest.fn(),
            },
            sendMessage: jest.fn(),
            sendPresenceUpdate: jest.fn(),
            fetchMessageHistory: jest.fn(),
            end: jest.fn(),
        };
        return mockSocket;
    },

    // Generate test message data
    generateTestMessage(overrides = {}) {
        return {
            key: {
                id: `test_msg_${Date.now()}`,
                remoteJid: '5511999999999@s.whatsapp.net',
                fromMe: false,
                ...overrides.key
            },
            message: {
                conversation: 'Test message content',
                ...overrides.message
            },
            messageTimestamp: Math.floor(Date.now() / 1000),
            ...overrides
        };
    },

    // Generate test chat data
    generateTestChat(overrides = {}) {
        return {
            id: '5511999999999@s.whatsapp.net',
            name: 'Test Contact',
            messages: [],
            unreadCount: 0,
            ...overrides
        };
    },

    // Mock environment variables
    mockEnv(envVars) {
        const originalEnv = { ...process.env };
        Object.assign(process.env, envVars);
        return () => {
            process.env = originalEnv;
        };
    },

    // Create test database with sample data
    async createTestDatabase(database) {
        await database.initialize();
        
        // Add sample data
        await database.saveChat('5511999999999@s.whatsapp.net', 'Test Contact 1');
        await database.saveChat('5511888888888@s.whatsapp.net', 'Test Contact 2');
        
        await database.saveMessage(
            'msg1',
            '5511999999999@s.whatsapp.net',
            false,
            'Hello from test contact',
            Date.now(),
            'text',
            'received'
        );
        
        await database.saveMessage(
            'msg2',
            '5511999999999@s.whatsapp.net',
            true,
            'Hello back from me',
            Date.now() + 1000,
            'text',
            'sent'
        );
        
        return database;
    }
};

// Global setup before all tests
beforeAll(async () => {
    // Create temp directory for tests
    const tempDir = path.join(process.cwd(), 'tests', 'temp');
    await fs.mkdir(tempDir, { recursive: true });
});

// Global cleanup after all tests
afterAll(async () => {
    // Clean up temp directory
    const tempDir = path.join(process.cwd(), 'tests', 'temp');
    try {
        await fs.rm(tempDir, { recursive: true, force: true });
    } catch (error) {
        // Ignore cleanup errors
    }
    
    // Restore console
    global.console = originalConsole;
});

// Setup before each test
beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Reset environment
    process.env.NODE_ENV = 'test';
    process.env.LOG_LEVEL = 'error';
});

// Cleanup after each test
afterEach(() => {
    // Additional cleanup if needed
});

export default {};

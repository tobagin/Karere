#!/usr/bin/env node
// download-all-contact-data.js
// Comprehensive download of all contact data and avatars

import WebSocket from 'ws';
import database from './database.js';
import avatarManager from './avatar-manager.js';

const WS_URL = 'ws://localhost:8765';

class ComprehensiveDownloader {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.totalChats = 0;
        this.processedChats = 0;
        this.successfulDownloads = 0;
        this.errors = 0;
        this.startTime = Date.now();
    }

    async connect() {
        return new Promise((resolve, reject) => {
            console.log('🔌 Connecting to backend for comprehensive download...');
            
            this.ws = new WebSocket(WS_URL);
            
            this.ws.on('open', () => {
                console.log('✅ Connected to backend WebSocket');
                this.connected = true;
                resolve();
            });
            
            this.ws.on('message', (data) => {
                try {
                    const message = JSON.parse(data.toString());
                    this.handleMessage(message);
                } catch (error) {
                    console.error('❌ Error parsing message:', error);
                }
            });
            
            this.ws.on('error', (error) => {
                console.error('❌ WebSocket error:', error);
                reject(error);
            });
            
            this.ws.on('close', () => {
                console.log('🔌 WebSocket connection closed');
                this.connected = false;
            });
        });
    }

    handleMessage(message) {
        const { type, data } = message;
        
        switch (type) {
            case 'sync_contacts_started':
                this.totalChats = data.totalChats;
                console.log(`🚀 Starting comprehensive download for ${this.totalChats} chats`);
                break;
                
            case 'sync_contacts_progress':
                this.processedChats = data.processed;
                this.successfulDownloads = data.synced;
                this.errors = data.processed - data.synced;
                
                const percentage = ((this.processedChats / this.totalChats) * 100).toFixed(1);
                const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(1);
                
                console.log(`📊 Progress: ${this.processedChats}/${this.totalChats} (${percentage}%) | ✅ ${this.successfulDownloads} synced | ❌ ${this.errors} errors | ⏱️ ${elapsed}s`);
                break;
                
            case 'sync_contacts_completed':
                const totalTime = ((Date.now() - this.startTime) / 1000).toFixed(1);
                console.log(`\n🎉 Comprehensive download completed!`);
                console.log(`   📊 Total processed: ${data.totalProcessed}`);
                console.log(`   ✅ Successfully synced: ${data.syncedCount}`);
                console.log(`   ❌ Errors: ${data.errorCount}`);
                console.log(`   ⏱️ Total time: ${totalTime}s`);
                console.log(`   📈 Rate: ${(data.totalProcessed / totalTime).toFixed(1)} contacts/sec`);
                break;
                
            case 'sync_contacts_error':
                console.error('❌ Sync error:', data);
                break;
                
            default:
                // Suppress other messages during bulk download
                break;
        }
    }

    send(type, data = {}) {
        if (!this.connected) {
            console.error('❌ Not connected to backend');
            return;
        }
        
        const message = JSON.stringify({ type, data });
        this.ws.send(message);
    }

    async downloadAllContactData() {
        console.log('\n🔄 Starting Comprehensive Contact Data Download...\n');
        
        try {
            // Step 1: Check current database state
            await database.initialize();
            
            console.log('📋 Current database state:');
            const chats = await database.getChats(1000);
            const contacts = await database.getAllContacts(1000);
            const avatarStats = avatarManager.getStats();
            
            console.log(`   💬 Chats in database: ${chats.length}`);
            console.log(`   👤 Contacts in database: ${contacts.length}`);
            console.log(`   🖼️ Avatars downloaded: ${avatarStats.count}`);
            console.log(`   💾 Avatar storage size: ${(avatarStats.totalSize / 1024 / 1024).toFixed(2)} MB`);
            
            await database.close();
            
            // Step 2: Trigger comprehensive sync via WebSocket
            console.log('\n🚀 Triggering comprehensive contact synchronization...');
            this.send('sync_contacts');
            
            // Step 3: Wait for completion
            console.log('⏳ Waiting for download to complete...\n');
            
            // Wait for sync to complete (max 5 minutes)
            let waitTime = 0;
            const maxWaitTime = 300000; // 5 minutes
            const checkInterval = 1000; // 1 second
            
            while (waitTime < maxWaitTime) {
                await this.wait(checkInterval);
                waitTime += checkInterval;
                
                // Check if we've processed all chats
                if (this.processedChats >= this.totalChats && this.totalChats > 0) {
                    console.log('\n✅ All chats processed!');
                    break;
                }
            }
            
            if (waitTime >= maxWaitTime) {
                console.log('\n⚠️ Download timeout reached, but continuing...');
            }
            
            // Step 4: Final verification
            await this.wait(2000); // Wait a bit more for final updates
            await this.verifyResults();
            
        } catch (error) {
            console.error('❌ Download failed:', error);
        }
    }

    async verifyResults() {
        console.log('\n🔍 Verifying download results...\n');
        
        try {
            await database.initialize();
            
            // Get updated stats
            const chats = await database.getChats(1000);
            const contacts = await database.getAllContacts(1000);
            const contactsWithAvatars = contacts.filter(c => c.avatar_path);
            const avatarStats = avatarManager.getStats();
            
            console.log('📊 Final Results:');
            console.log(`   💬 Total chats: ${chats.length}`);
            console.log(`   👤 Total contacts: ${contacts.length}`);
            console.log(`   🖼️ Contacts with avatars: ${contactsWithAvatars.length}`);
            console.log(`   📁 Avatar files: ${avatarStats.count}`);
            console.log(`   💾 Total avatar size: ${(avatarStats.totalSize / 1024 / 1024).toFixed(2)} MB`);
            
            // Show sample of successfully downloaded contacts
            console.log('\n✅ Sample of contacts with complete data:');
            const sampleContacts = contactsWithAvatars.slice(0, 10);
            
            sampleContacts.forEach((contact, index) => {
                console.log(`   ${index + 1}. ${contact.name || contact.jid}`);
                console.log(`      JID: ${contact.jid}`);
                console.log(`      Avatar: ${contact.avatar_path ? '✅' : '❌'}`);
                console.log(`      Updated: ${new Date(contact.updated_at * 1000).toLocaleString()}`);
                console.log('');
            });
            
            // Show chats with enhanced data
            console.log('💬 Sample of chats with contact integration:');
            const enhancedChats = chats.filter(c => c.contact_name || c.contact_avatar_path).slice(0, 5);
            
            enhancedChats.forEach((chat, index) => {
                console.log(`   ${index + 1}. ${chat.contact_name || chat.name || chat.jid}`);
                console.log(`      JID: ${chat.jid}`);
                console.log(`      Contact Name: ${chat.contact_name || 'N/A'}`);
                console.log(`      Avatar: ${chat.contact_avatar_path ? '✅' : '❌'}`);
                console.log(`      Last Message: ${(chat.last_message_content || 'N/A').substring(0, 50)}${chat.last_message_content?.length > 50 ? '...' : ''}`);
                console.log('');
            });
            
            await database.close();
            
            // Calculate success rate
            const successRate = contacts.length > 0 ? ((contactsWithAvatars.length / contacts.length) * 100).toFixed(1) : 0;
            
            console.log(`🎯 Success Rate: ${successRate}% of contacts have complete data`);
            
            if (successRate > 80) {
                console.log('🎉 Excellent! Most contacts have complete data.');
            } else if (successRate > 50) {
                console.log('👍 Good! Majority of contacts have data.');
            } else {
                console.log('⚠️ Some contacts may need manual retry.');
            }
            
        } catch (error) {
            console.error('❌ Verification failed:', error);
        }
    }

    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Run the comprehensive downloader
async function main() {
    const downloader = new ComprehensiveDownloader();
    
    try {
        await downloader.connect();
        await downloader.downloadAllContactData();
        
    } catch (error) {
        console.error('❌ Comprehensive download failed:', error);
    } finally {
        downloader.disconnect();
        console.log('\n👋 Comprehensive download finished');
        process.exit(0);
    }
}

// Run if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main().catch(console.error);
}

export default ComprehensiveDownloader;

/**
 * Mofid Anniversary 31 - Score Encryption Module
 * ================================================
 * 
 * A clean implementation of the game score encoding system used in Mofid's
 * Anniversary 40 celebration (31st anniversary of the foundation).
 * This module provides HMAC-SHA256 based score encryption and API interaction functions.
 * 
 * @author  NabiKAZ <x.com/NabiKAZ>
 * @channel https://t.me/BotSorati
 * @see     https://landing.emofid.com/anniversary40/login?invite_code=NV4NI3
 * @project https://github.com/NabiKAZ/mofid_anniversary31
 * @license MIT
 * 
 * Features:
 * - HMAC-SHA256 score signature generation
 * - Base64 encoding with timestamp
 * - Score validation and verification
 * - API integration for game session management
 * - Proxy support for debugging
 * 
 * Format: base64(score.timestamp.hmac_signature)
 * See: runExample() function at the below for usage examples.
 */

import crypto from 'crypto';
import https from 'https';
import fetch from 'node-fetch';
import { HttpsProxyAgent } from 'https-proxy-agent';

// Secret key used for HMAC signing
const SECRET_KEY = 'A40@2025-ASDasd!@#123CCCvvvaaa';

// Delimiter between parts
const DELIMITER = '.';

// API Configuration
const API_BASE = 'https://landing.emofid.com/api-service/anniversary40';

// Global proxy configuration
let globalProxyAgent = null;

/**
 * Set global proxy for all API requests
 * @param {string} proxyUrl - Proxy URL (e.g., 'http://127.0.0.1:8080')
 */
function setGlobalProxy(proxyUrl) {
    if (proxyUrl) {
        globalProxyAgent = new HttpsProxyAgent(proxyUrl, {
            rejectUnauthorized: false
        });
        console.log(`✓ Global proxy set: ${proxyUrl}`);
    } else {
        globalProxyAgent = null;
        console.log('✓ Global proxy cleared');
    }
}

/**
 * Get appropriate agent for fetch (proxy or default)
 * @returns {object} HTTPS agent
 */
function getAgent() {
    if (globalProxyAgent) {
        return globalProxyAgent;
    }
    
    return new https.Agent({ rejectUnauthorized: false });
}

/**
 * Delay execution for specified milliseconds
 * @param {number} ms - Milliseconds to wait
 * @returns {Promise<void>}
 */
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Generate HMAC-SHA256 signature for a message
 * @param {string} message - The message to sign
 * @returns {string} Hex string of the signature
 */
function generateHMAC(message) {
    const hmac = crypto.createHmac('sha256', SECRET_KEY);
    hmac.update(message);
    return hmac.digest('hex');
}

/**
 * Encode points with timestamp and signature
 * @param {number} points - Game score to encode
 * @returns {string} Base64 encoded string: base64(score.timestamp.signature)
 */
function encodeScore(points) {
    // Get current timestamp in milliseconds
    const timestamp = Date.now().toString();
    
    // Create payload: score.timestamp
    const payload = `${points}${DELIMITER}${timestamp}`;
    
    // Generate HMAC signature for payload
    const signature = generateHMAC(payload);
    
    // Final format: score.timestamp.signature
    const finalString = `${payload}${DELIMITER}${signature}`;
    
    // Encode to base64
    const encoded = Buffer.from(finalString).toString('base64');
    
    return encoded;
}

/**
 * Decode and verify an encoded score
 * @param {string} encoded - Base64 encoded score string
 * @returns {object} Object with score, timestamp, signature, and isValid
 */
function decodeScore(encoded) {
    try {
        // Decode from base64
        const decoded = Buffer.from(encoded, 'base64').toString('utf-8');
        
        // Split by delimiter
        const parts = decoded.split(DELIMITER);
        
        if (parts.length !== 3) {
            throw new Error('Invalid format: expected 3 parts');
        }
        
        const [score, timestamp, receivedSignature] = parts;
        
        // Recreate payload and verify signature
        const payload = `${score}${DELIMITER}${timestamp}`;
        const expectedSignature = generateHMAC(payload);
        
        const isValid = receivedSignature === expectedSignature;
        
        return {
            score: parseInt(score),
            timestamp: parseInt(timestamp),
            signature: receivedSignature,
            isValid: isValid,
            date: new Date(parseInt(timestamp)),
            raw: decoded
        };
    } catch (error) {
        return {
            error: error.message,
            isValid: false
        };
    }
}

/**
 * Check if user can start the game
 * @param {string} token - Authorization token (user_id|api_token)
 * @param {string} game - Game name (rocket or shooter)
 * @returns {Promise<object>} Response with can_start, total_points, remaining_chances
 */
async function startGame(token, game = 'rocket') {
    try {
        const url = `${API_BASE}/can-start?game=${game}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'authorization': `Bearer ${token}`,
                'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            },
            agent: getAgent()
        });
        
        const data = await response.json();
        
        return {
            success: true,
            canStart: data.can_start === 1,
            totalPoints: data.total_points,
            remainingChances: data.remaining_chances,
            raw: data
        };
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Submit game score to server
 * @param {string} token - Authorization token (user_id|api_token)
 * @param {number} score - Game score
 * @param {string} missionName - Game name (rocket or shooter)
 * @param {number} duration - Remaining time (ms or sec per backend) when lives ended; if time expires but lives remain, send 0
 * @returns {Promise<object>} Response with success status and message
 */
async function finishGame(token, score, missionName = 'rocket', duration = 0) {
    try {
        // Encode the score
        const pointsEarned = encodeScore(score);
        
        const url = `${API_BASE}/finish-game`;
        
        const body = {
            points_earned: pointsEarned,
            mission_name: missionName,
            duration: duration
        };
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'authorization': `Bearer ${token}`,
                'content-type': 'application/json',
                'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            },
            body: JSON.stringify(body),
            agent: getAgent()
        });
        
        const data = await response.json();
        
        return {
            success: data.success === true,
            message: data.message,
            score: score,
            encoded: pointsEarned,
            raw: data
        };
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}

// Example usage
async function runExample() {
    // Constants
    const PROXY = 'http://127.0.0.1:8080'; // Set to null or '' to disable proxy
    const TOKEN = '11111|111111111111111111111111111111111111111111111111'; // Replace with valid token
    const GAME_DELAY_MS = 3000; // Simulated game duration
    const SCORE = 1500; // Example score
    const REMAINING_TIME_SEC = 0; // Remaining time when game ends
    const GAME_NAME = 'rocket'; // Game name: 'rocket' or 'shooter'
    
    console.log('=== Score Encoding Example ===\n');
    
    // Set proxy for debugging (uncomment to use)
    // setGlobalProxy(PROXY);
    
    // Encode a score
    console.log(`Original Score: ${SCORE}`);
    
    const encoded = encodeScore(SCORE);
    console.log(`Encoded: ${encoded}`);
    console.log(`Length: ${encoded.length} chars\n`);
    
    // Decode and verify
    const decoded = decodeScore(encoded);
    console.log('Decoded Result:');
    console.log(`  Score: ${decoded.score}`);
    console.log(`  Timestamp: ${decoded.timestamp}`);
    console.log(`  Date: ${decoded.date.toLocaleString('fa-IR')}`);
    console.log(`  Valid: ${decoded.isValid ? '✓ YES' : '✗ NO'}`);
    console.log(`  Signature: ${decoded.signature.substring(0, 16)}...`);
    console.log(`  Raw: ${decoded.raw}\n`);
    
    // API Example (requires valid token)
    console.log('=== API Example ===\n');
    console.log(`Token: ${TOKEN.substring(0, 20)}...`);
    console.log(`Game: ${GAME_NAME}`);
    console.log(`Delay: ${GAME_DELAY_MS}ms`);
    console.log(`Score: ${SCORE}`);
    console.log(`Remaining Time: ${REMAINING_TIME_SEC}\n`);
    
    // 1. Check if can start game
    console.log('1. Checking if can start game...');
    const checkStart = await startGame(TOKEN, GAME_NAME);
    console.log(`   Can Start: ${checkStart.canStart}`);
    console.log(`   Total Points: ${checkStart.totalPoints}`);
    console.log(`   Remaining Chances: ${checkStart.remainingChances}\n`);
    
    if (!checkStart.canStart) {
        console.log('❌ Cannot start game. Skipping score submission.\n');
        return;
    }
    
    // 2. Simulate game duration
    console.log(`2. Simulating game play (${GAME_DELAY_MS / 1000} second delay)...`);
    await delay(GAME_DELAY_MS);
    console.log('   Game finished!\n');
    
    // 3. Submit score
    console.log('3. Submitting score...');
    const result = await finishGame(TOKEN, SCORE, GAME_NAME, REMAINING_TIME_SEC);
    console.log(`   Success: ${result.success}`);
    console.log(`   Message: ${result.message}`);
    console.log(`   Encoded Score: ${result.encoded}\n`);
}

// Export functions
export {
    encodeScore,
    decodeScore,
    generateHMAC,
    startGame,
    finishGame,
    setGlobalProxy,
    delay,
    SECRET_KEY,
    DELIMITER
};

// Run example if executed directly
if (import.meta.url === `file:///${process.argv[1].replace(/\\/g, '/')}`) {
    runExample();
}

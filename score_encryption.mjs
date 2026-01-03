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
 * @version 2.0.0
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
 * Countdown delay with periodic logging
 * @param {number} ms - Total milliseconds to wait
 * @param {number} stepMs - Interval for updates
 */
async function countdownDelay(ms, stepMs = 1000) {
    let remaining = ms;

    function formatHMS(msLeft) {
        let totalSec = Math.ceil(msLeft / 1000);
        const h = Math.floor(totalSec / 3600);
        const m = Math.floor((totalSec % 3600) / 60);
        const s = totalSec % 60;
        return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    // Initial display
    process.stdout.write(`   Remaining: ${formatHMS(remaining)}`);

    while (remaining > 0) {
        const chunk = Math.min(stepMs, remaining);
        await delay(chunk);
        remaining -= chunk;
        process.stdout.write(`\r   Remaining: ${formatHMS(remaining)}   `);
    }

    process.stdout.write('\n');
}

/**
 * Generate a realistic fractional duration in seconds matching observed pattern
 * Uses mathematical formula: (random5digit + 1/3) / 100000 to create repeating '3' pattern
 * @param {number} baseMs - Base duration in milliseconds
 * @returns {number} Duration in seconds with realistic fractional pattern
 */
function generateRealisticDuration(baseMs) {
    const seconds = Math.floor(baseMs / 1000);
    
    // Generate 5-digit random number (0-99999)
    const random5Digit = Math.floor(Math.random() * 100000);
    
    // Mathematical formula: (BaseRandom + 1/3) / 100000
    // This creates the pattern: 5digits followed by repeating 3s
    const decimalValue = (random5Digit + 1/3) / 100000;
    
    // Combine and limit precision to 14 digits for consistency
    return parseFloat((seconds + decimalValue).toFixed(14));
}

/**
 * Compute 'What' duration (integer seconds) from a simulated duration value.
 * Picks a random offset between minOffsetSec and maxOffsetSec (defaults 1–4s).
 * Options allow changing rounding behavior for testing.
 * @param {number} simulatedDurationSec - duration in seconds (float)
 * @param {object} [options] - { minOffsetSec:number, maxOffsetSec:number, rounding: 'round'|'floor'|'ceil' }
 * @returns {number} integer seconds to use as What (>=0)
 */
function computeWhatDuration(simulatedDurationSec, options = {}) {
    const { minOffsetSec = 1, maxOffsetSec = 4, rounding = 'round' } = options;
    const offset = minOffsetSec + Math.random() * (maxOffsetSec - minOffsetSec);
    let value = simulatedDurationSec - offset;
    if (rounding === 'floor') value = Math.floor(value);
    else if (rounding === 'ceil') value = Math.ceil(value);
    else value = Math.round(value);
    return Math.max(0, value);
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
    // console.log('Payload before base64 (score.timestamp.signature):', finalString); //TODO:debug
    
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
 * Start the game
 * @param {string} token - Authorization token (user_id|api_token)
 * @param {string} game - Game name (rocket or shooter)
 * @returns {Promise<object>} Response with can_start, coins_required, user_coins
 */
async function startGame(token, game = 'rocket') {
    try {
        const url = `${API_BASE}/missions/${game}/start/`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Priority': 'u=4',
                'Cookie': `anniversary40_token=${token};`,
            },
            referrer: 'https://landing.emofid.com/anniversary40/games/',
            agent: getAgent()
        });
        
        const data = await response.json();
        
        return {
            success: true,
            canStart: data.can_start === true,
            coinsRequired: data.coins_required,
            userCoins: data.user_coins,
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
 * Check whether a game can start (GET /can-start?game=<game>)
 * @param {string} token - Authorization token (user_id|api_token)
 * @param {string} game - Game name (rocket or shooter)
 * @returns {Promise<object>} Response with can_start, coins_required, user_coins
 */
async function checkCanStart(token, game = 'rocket') {
    try {
        const url = `${API_BASE}/can-start?game=${encodeURIComponent(game)}`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Priority': 'u=4',
                'Cookie': `anniversary40_token=${token};`,
            },
            referrer: 'https://landing.emofid.com/anniversary40/games/',
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
 * @param {number} duration - Game duration in milliseconds
 * @returns {Promise<object>} Response with success status and message
 */
async function finishGame(token, score, missionName = 'rocket', duration = 0) {
    try {
        // Encode the score
        const pointsEarned = encodeScore(score);
        
        // Derive a realistic duration (seconds with fractional part) from base ms
        const simulatedDurationSec = generateRealisticDuration(duration);
        
        // Compute What using helper (default: offset 1-4s, rounding=round)
        const whatDurationSec = computeWhatDuration(simulatedDurationSec);
        const whatEncoded = encodeScore(whatDurationSec);
        
        const url = `${API_BASE}/finish-game/`;

        const body = {
            points_earned: pointsEarned,
            mission_name: missionName,
            duration: simulatedDurationSec
        };
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Priority': 'u=4',
                'Cookie': `anniversary40_token=${token};`,
                'What': whatEncoded,
            },
            referrer: 'https://landing.emofid.com/anniversary40/games/',
            body: JSON.stringify(body),
            agent: getAgent()
        });

        const data = await response.json();
        
        return {
            success: data.success === true,
            message: data.message,
            score: score,
            encoded: pointsEarned,
            simulatedDurationSec,
            whatDurationSec,
            what: whatEncoded,
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
    const PROXY = ''; // Set to null or '' to disable proxy or e.g. 'http://127.0.0.1:8080'
    const TOKEN = '11111|111111111111111111111111111111111111111111111111'; // Replace with valid token
    const DURATION = 10000; // Game duration in milliseconds
    const SCORE = 5000; // Example score
    const GAME_NAME = 'rocket'; // Game name: 'rocket' or 'shooter'
    
    console.log('=== Score Encoding Example ===\n');
    
    // Set proxy for debugging (uncomment to use)
    setGlobalProxy(PROXY);
    
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
    console.log(`Duration: ${DURATION}ms`);
    console.log(`Score: ${SCORE}\n`);
    
    // 1. Start the game
    console.log('1. Starting the game...');
    const startRes = await startGame(TOKEN, GAME_NAME);
    console.log(`   Raw: `, startRes.raw);
    console.log(`   Can Start: ${startRes.canStart}`);
    console.log(`   Coins Required: ${startRes.coinsRequired}`);
    console.log(`   User Coins: ${startRes.userCoins}\n`);

    if (!startRes.canStart) {
        console.log('❌ Start failed. Aborting.\n');
        return;
    }

    // 2. Check can-start after starting
    console.log('2. Checking can-start after starting the game...');
    const postStartCheck = await checkCanStart(TOKEN, GAME_NAME);
    console.log(`   Raw: `, postStartCheck.raw);
    console.log(`   Can Start: ${postStartCheck.canStart}`);
    console.log(`   Total Points: ${postStartCheck.totalPoints}`);
    console.log(`   Remaining Chances: ${postStartCheck.remainingChances}\n`);

    if (!postStartCheck.canStart) {
        console.log('❌ Cannot continue (can-start false after start). Aborting.\n');
        return;
    }

    // 3. Simulate game duration
    console.log(`3. Simulating game play (${DURATION / 1000} second delay)...`);
    await countdownDelay(DURATION, 1000);
    console.log('   Game finished!\n');

    // 4. Submit score
    console.log('4. Submitting score...');
    const result = await finishGame(TOKEN, SCORE, GAME_NAME, DURATION);
    console.log(`   Raw: `, result.raw);
    console.log(`   Success: ${result.success}`);
    console.log(`   Message: ${result.message}`);
    console.log(`   Encoded Score: ${result.encoded}`);
    console.log(`   Simulated Duration (sec): ${result.simulatedDurationSec}`);
    console.log(`   What Duration (sec): ${result.whatDurationSec}`);
    console.log(`   What Encoded: ${result.what}\n`);
}

// Export functions
export {
    encodeScore,
    decodeScore,
    generateHMAC,
    startGame,
    checkCanStart,
    finishGame,
    setGlobalProxy,
    delay,
    generateRealisticDuration,
    computeWhatDuration,
    SECRET_KEY,
    DELIMITER
};

// Run example if executed directly
if (import.meta.url === `file:///${process.argv[1].replace(/\\/g, '/')}`) {
    runExample();
}

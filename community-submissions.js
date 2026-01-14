/**
 * Community Submissions Module
 * Handles user-generated infographic submissions to a public temporary pool
 * Uses JSONBin.io for serverless JSON storage (free tier: 10,000 requests/month)
 * 
 * Features:
 * - Submit infographics with metadata (username, date, title, IP)
 * - View all pending submissions publicly
 * - Admin approval workflow
 * - Like/download functionality for other users
 */

// ============================================
// CONFIGURATION
// ============================================

// JSONBin.io Configuration - Replace with your own bin
// To set up: 
// 1. Go to https://jsonbin.io and create a free account
// 2. Create a new bin with initial content: {"submissions": [], "approved": []}
// 3. Get your bin ID and API key
// 4. Update these values

const JSONBIN_CONFIG = {
    // Public bin ID for submissions (you'll need to create this)
    BIN_ID: 'YOUR_BIN_ID_HERE', // Replace with actual bin ID
    // Master key for read/write (keep secret for admin operations)
    MASTER_KEY: '$2a$10$YOUR_MASTER_KEY_HERE', // Replace with actual key
    // Access key for public read (optional, for rate limiting)
    ACCESS_KEY: '$2a$10$YOUR_ACCESS_KEY_HERE', // Replace with actual key
    BASE_URL: 'https://api.jsonbin.io/v3/b'
};

// Admin PIN for approval operations (simple security)
// In production, use a more secure method
const ADMIN_PIN = '309030'; // Change this to your preferred PIN

// IP lookup service (free, no API key needed)
const IP_SERVICE_URL = 'https://api.ipify.org?format=json';

// Local storage key for caching
const COMMUNITY_CACHE_KEY = 'ophthalmic_community_cache';
const COMMUNITY_CACHE_EXPIRY = 5 * 60 * 1000; // 5 minutes

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Get user's IP address using ipify.org
 */
async function getUserIP() {
    try {
        const response = await fetch(IP_SERVICE_URL);
        if (response.ok) {
            const data = await response.json();
            return data.ip;
        }
    } catch (err) {
        console.log('Could not fetch IP address:', err.message);
    }
    return 'Unknown';
}

/**
 * Generate a unique submission ID
 */
function generateSubmissionId() {
    return `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Format date for display
 */
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Sanitize user input
 */
function sanitizeInput(input) {
    if (typeof input !== 'string') return '';
    return input
        .trim()
        .replace(/[<>]/g, '') // Remove potential HTML tags
        .substring(0, 500); // Limit length
}

// ============================================
// JSONBin.io API Functions
// ============================================

/**
 * Check if JSONBin is configured
 */
function isJSONBinConfigured() {
    return JSONBIN_CONFIG.BIN_ID && 
           JSONBIN_CONFIG.BIN_ID !== 'YOUR_BIN_ID_HERE' &&
           JSONBIN_CONFIG.MASTER_KEY !== '$2a$10$YOUR_MASTER_KEY_HERE';
}

/**
 * Fetch all submissions from JSONBin
 */
async function fetchSubmissions() {
    if (!isJSONBinConfigured()) {
        console.warn('JSONBin not configured. Using demo mode with localStorage.');
        return getLocalDemoSubmissions();
    }

    // Check cache first
    const cached = localStorage.getItem(COMMUNITY_CACHE_KEY);
    if (cached) {
        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < COMMUNITY_CACHE_EXPIRY) {
            console.log('Using cached community submissions');
            return data;
        }
    }

    try {
        const response = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${JSONBIN_CONFIG.BIN_ID}/latest`, {
            headers: {
                'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY
            }
        });

        if (!response.ok) {
            throw new Error(`JSONBin fetch failed: ${response.status}`);
        }

        const result = await response.json();
        const data = result.record || { submissions: [], approved: [] };

        // Cache the result
        localStorage.setItem(COMMUNITY_CACHE_KEY, JSON.stringify({
            data,
            timestamp: Date.now()
        }));

        return data;
    } catch (err) {
        console.error('Error fetching submissions:', err);
        return getLocalDemoSubmissions();
    }
}

/**
 * Update submissions in JSONBin
 */
async function updateSubmissions(data) {
    if (!isJSONBinConfigured()) {
        console.warn('JSONBin not configured. Saving to localStorage demo mode.');
        saveLocalDemoSubmissions(data);
        return true;
    }

    try {
        const response = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${JSONBIN_CONFIG.BIN_ID}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`JSONBin update failed: ${response.status}`);
        }

        // Clear cache to force refresh
        localStorage.removeItem(COMMUNITY_CACHE_KEY);
        return true;
    } catch (err) {
        console.error('Error updating submissions:', err);
        return false;
    }
}

// ============================================
// LOCAL DEMO MODE (Fallback when JSONBin not configured)
// ============================================

const LOCAL_DEMO_KEY = 'ophthalmic_community_demo';

function getLocalDemoSubmissions() {
    try {
        const data = localStorage.getItem(LOCAL_DEMO_KEY);
        return data ? JSON.parse(data) : { submissions: [], approved: [] };
    } catch {
        return { submissions: [], approved: [] };
    }
}

function saveLocalDemoSubmissions(data) {
    localStorage.setItem(LOCAL_DEMO_KEY, JSON.stringify(data));
}

// ============================================
// SUBMISSION FUNCTIONS
// ============================================

/**
 * Submit an infographic to the community pool
 * @param {Object} infographicData - The infographic data to submit
 * @param {string} userName - The submitter's name
 * @returns {Promise<Object>} - Result with success status and message
 */
async function submitToCommunity(infographicData, userName) {
    if (!infographicData) {
        return { success: false, message: 'No infographic data provided.' };
    }

    if (!userName || userName.trim().length === 0) {
        return { success: false, message: 'Please provide your name.' };
    }

    try {
        // Get user IP
        const userIP = await getUserIP();

        // Create submission object
        const submission = {
            id: generateSubmissionId(),
            userName: sanitizeInput(userName),
            title: infographicData.title || 'Untitled Infographic',
            summary: infographicData.summary || '',
            submittedAt: new Date().toISOString(),
            userIP: userIP,
            likes: 0,
            likedBy: [], // Array of IPs who liked
            status: 'pending', // pending, approved, rejected
            data: infographicData
        };

        // Fetch current submissions
        const currentData = await fetchSubmissions();

        // Add new submission
        currentData.submissions = currentData.submissions || [];
        currentData.submissions.unshift(submission);

        // Update storage
        const success = await updateSubmissions(currentData);

        if (success) {
            return { 
                success: true, 
                message: 'Your infographic has been submitted for review!',
                submissionId: submission.id
            };
        } else {
            return { success: false, message: 'Failed to submit. Please try again.' };
        }
    } catch (err) {
        console.error('Submission error:', err);
        return { success: false, message: 'An error occurred. Please try again.' };
    }
}

/**
 * Get all pending submissions (for public view)
 */
async function getPendingSubmissions() {
    const data = await fetchSubmissions();
    return (data.submissions || []).filter(s => s.status === 'pending');
}

/**
 * Get all approved submissions (for public gallery)
 */
async function getApprovedSubmissions() {
    const data = await fetchSubmissions();
    return data.approved || [];
}

/**
 * Get all submissions (for admin view)
 */
async function getAllSubmissions() {
    return await fetchSubmissions();
}

/**
 * Like a submission
 * @param {string} submissionId - The submission to like
 */
async function likeSubmission(submissionId) {
    try {
        const userIP = await getUserIP();
        const data = await fetchSubmissions();

        // Find in pending submissions
        let submission = (data.submissions || []).find(s => s.id === submissionId);
        let isApproved = false;

        // If not found, check approved
        if (!submission) {
            submission = (data.approved || []).find(s => s.id === submissionId);
            isApproved = true;
        }

        if (!submission) {
            return { success: false, message: 'Submission not found.' };
        }

        // Check if already liked
        submission.likedBy = submission.likedBy || [];
        if (submission.likedBy.includes(userIP)) {
            return { success: false, message: 'You have already liked this.' };
        }

        // Add like
        submission.likedBy.push(userIP);
        submission.likes = (submission.likes || 0) + 1;

        // Update storage
        await updateSubmissions(data);

        return { success: true, likes: submission.likes };
    } catch (err) {
        console.error('Like error:', err);
        return { success: false, message: 'Failed to like.' };
    }
}

// ============================================
// ADMIN FUNCTIONS
// ============================================

/**
 * Verify admin PIN
 */
function verifyAdminPIN(pin) {
    return pin === ADMIN_PIN;
}

/**
 * Approve a submission (admin only)
 * @param {string} submissionId - The submission to approve
 * @param {string} pin - Admin PIN for verification
 */
async function approveSubmission(submissionId, pin) {
    if (!verifyAdminPIN(pin)) {
        return { success: false, message: 'Invalid admin PIN.' };
    }

    try {
        const data = await fetchSubmissions();
        
        // Find the submission
        const index = (data.submissions || []).findIndex(s => s.id === submissionId);
        if (index === -1) {
            return { success: false, message: 'Submission not found.' };
        }

        // Move to approved
        const submission = data.submissions.splice(index, 1)[0];
        submission.status = 'approved';
        submission.approvedAt = new Date().toISOString();

        data.approved = data.approved || [];
        data.approved.unshift(submission);

        // Update storage
        const success = await updateSubmissions(data);

        if (success) {
            return { success: true, message: 'Submission approved!' };
        } else {
            return { success: false, message: 'Failed to approve.' };
        }
    } catch (err) {
        console.error('Approve error:', err);
        return { success: false, message: 'An error occurred.' };
    }
}

/**
 * Reject a submission (admin only)
 * @param {string} submissionId - The submission to reject
 * @param {string} pin - Admin PIN for verification
 */
async function rejectSubmission(submissionId, pin) {
    if (!verifyAdminPIN(pin)) {
        return { success: false, message: 'Invalid admin PIN.' };
    }

    try {
        const data = await fetchSubmissions();
        
        // Find and remove the submission
        const index = (data.submissions || []).findIndex(s => s.id === submissionId);
        if (index === -1) {
            return { success: false, message: 'Submission not found.' };
        }

        // Remove from pending
        data.submissions.splice(index, 1);

        // Update storage
        const success = await updateSubmissions(data);

        if (success) {
            return { success: true, message: 'Submission rejected and removed.' };
        } else {
            return { success: false, message: 'Failed to reject.' };
        }
    } catch (err) {
        console.error('Reject error:', err);
        return { success: false, message: 'An error occurred.' };
    }
}

// ============================================
// DOWNLOAD FUNCTIONS
// ============================================

/**
 * Download a community submission to local library
 * @param {string} submissionId - The submission to download
 */
async function downloadToLocalLibrary(submissionId) {
    try {
        const data = await fetchSubmissions();
        
        // Find in both pending and approved
        let submission = (data.submissions || []).find(s => s.id === submissionId);
        if (!submission) {
            submission = (data.approved || []).find(s => s.id === submissionId);
        }

        if (!submission || !submission.data) {
            return { success: false, message: 'Submission not found.' };
        }

        // Get local library
        const LIBRARY_KEY = 'ophthalmic_infographic_library';
        let library = [];
        try {
            library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');
        } catch {
            library = [];
        }

        // Check if already exists
        const exists = library.some(item => 
            item.communityId === submissionId ||
            (item.title === submission.title && item.date === submission.submittedAt)
        );

        if (exists) {
            return { success: false, message: 'This infographic is already in your library.' };
        }

        // Calculate next seqId
        let nextSeqId = 1;
        if (library.length > 0) {
            const maxSeqId = library.reduce((max, item) => 
                (item.seqId > max ? item.seqId : max), 0);
            nextSeqId = maxSeqId + 1;
        }

        // Create local library item
        const newItem = {
            id: Date.now(),
            seqId: nextSeqId,
            title: submission.title,
            summary: submission.summary,
            date: new Date().toISOString(),
            data: submission.data,
            chapterId: 'uncategorized',
            // Track community origin
            communityId: submissionId,
            communityAuthor: submission.userName,
            communityDate: submission.submittedAt
        };

        library.unshift(newItem);
        localStorage.setItem(LIBRARY_KEY, JSON.stringify(library));

        return { 
            success: true, 
            message: `"${submission.title}" added to your library!` 
        };
    } catch (err) {
        console.error('Download error:', err);
        return { success: false, message: 'Failed to download.' };
    }
}

// ============================================
// UI HELPER FUNCTIONS
// ============================================

/**
 * Generate HTML for a submission card
 */
function generateSubmissionCardHTML(submission, isAdmin = false) {
    const dateStr = formatDate(submission.submittedAt);
    const statusBadge = submission.status === 'approved' 
        ? '<span class="status-badge approved">✓ Approved</span>'
        : '<span class="status-badge pending">⏳ Pending Review</span>';

    return `
        <div class="community-card" data-id="${submission.id}">
            <div class="community-card-header">
                <h3 class="community-card-title">${sanitizeInput(submission.title)}</h3>
                ${statusBadge}
            </div>
            <p class="community-card-summary">${sanitizeInput(submission.summary || 'No summary available.')}</p>
            <div class="community-card-meta">
                <span class="meta-item">
                    <span class="material-symbols-rounded">person</span>
                    ${sanitizeInput(submission.userName)}
                </span>
                <span class="meta-item">
                    <span class="material-symbols-rounded">calendar_today</span>
                    ${dateStr}
                </span>
                ${isAdmin ? `
                <span class="meta-item ip-info">
                    <span class="material-symbols-rounded">language</span>
                    ${submission.userIP || 'Unknown'}
                </span>
                ` : ''}
                <span class="meta-item likes-count">
                    <span class="material-symbols-rounded">favorite</span>
                    ${submission.likes || 0}
                </span>
            </div>
            <div class="community-card-actions">
                <button class="community-btn like-btn" onclick="handleLikeSubmission('${submission.id}')">
                    <span class="material-symbols-rounded">thumb_up</span>
                    Like
                </button>
                <button class="community-btn preview-btn" onclick="handlePreviewSubmission('${submission.id}')">
                    <span class="material-symbols-rounded">visibility</span>
                    Preview
                </button>
                <button class="community-btn download-btn" onclick="handleDownloadSubmission('${submission.id}')">
                    <span class="material-symbols-rounded">download</span>
                    Add to Library
                </button>
                ${isAdmin ? `
                <button class="community-btn approve-btn" onclick="handleApproveSubmission('${submission.id}')">
                    <span class="material-symbols-rounded">check_circle</span>
                    Approve
                </button>
                <button class="community-btn reject-btn" onclick="handleRejectSubmission('${submission.id}')">
                    <span class="material-symbols-rounded">cancel</span>
                    Reject
                </button>
                ` : ''}
            </div>
        </div>
    `;
}

// ============================================
// EXPORTS
// ============================================

// Export functions for use in other scripts
window.CommunitySubmissions = {
    // Configuration
    isConfigured: isJSONBinConfigured,
    
    // Submission functions
    submit: submitToCommunity,
    getPending: getPendingSubmissions,
    getApproved: getApprovedSubmissions,
    getAll: getAllSubmissions,
    
    // User actions
    like: likeSubmission,
    downloadToLibrary: downloadToLocalLibrary,
    
    // Admin functions
    verifyAdmin: verifyAdminPIN,
    approve: approveSubmission,
    reject: rejectSubmission,
    
    // Utilities
    getUserIP,
    formatDate,
    generateCardHTML: generateSubmissionCardHTML
};

console.log('Community Submissions module loaded.');
console.log('JSONBin configured:', isJSONBinConfigured());

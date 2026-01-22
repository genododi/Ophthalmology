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

// GitHub Gist Configuration - Replaces JSONBin
// 1. Create a new Gist at https://gist.github.com/
// 2. Name the file "community_data.json"
// 3. Add initial content: {"submissions": [], "approved": [], "deleted": []}
// 4. Get the Gist ID from the URL (after username/)
// 5. Generate a Personal Access Token (PAT) with "gist" scope at https://github.com/settings/tokens

const GITHUB_CONFIG = {
    // Your Gist ID - Please Create a Gist at gist.github.com
    GIST_ID: 'YOUR_GIST_ID_HERE',
    // Your GitHub Personal Access Token (PAT) will be read from localStorage
    GIST_TOKEN: '',
    FILENAME: 'community_data.json',
    API_URL: 'https://api.github.com/gists'
};

// Admin PIN for approval operations (simple security)
const ADMIN_PIN = '309030';

// IP lookup service (free, no API key needed)
const IP_SERVICE_URL = 'https://api.ipify.org?format=json';

// Local storage key for caching
const COMMUNITY_CACHE_KEY = 'ophthalmic_community_cache';
const COMMUNITY_CACHE_EXPIRY = 5 * 60 * 1000; // 5 minutes

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Auto-detect chapter from title keywords
 * Enhanced clinical ophthalmology keywords
 */
function autoDetectChapterFromTitle(title) {
    if (!title) return 'uncategorized';

    const titleLower = title.toLowerCase();

    // Clinical ophthalmology auto-categorization rules
    const rules = [
        // Neuro-ophthalmology
        { keywords: ['neuro', 'optic nerve', 'optic neuritis', 'papill', 'visual field', 'pupil', 'nystagmus', 'cranial nerve', 'chiasm', 'intracranial', 'iih', 'horner', 'anisocoria', 'gaze palsy', 'diplopia cranial', 'aion', 'naion'], chapter: 'neuro' },
        // Glaucoma
        { keywords: ['glaucoma', 'iop', 'intraocular pressure', 'trabeculectomy', 'angle closure', 'poag', 'pacg', 'migs', 'tube shunt', 'filtering', 'rnfl', 'optic disc cupping', 'visual field glaucoma', 'pigmentary glaucoma', 'pseudoexfoliation'], chapter: 'glaucoma' },
        // Vitreoretinal
        { keywords: ['vitreous', 'retinal detachment', 'vitrectomy', 'macular hole', 'pvd', 'epiretinal membrane', 'erm', 'scleral buckle', 'rhegmatogenous', 'tractional', 'pvr', 'silicone oil', 'floaters'], chapter: 'vitreoretinal' },
        // Medical Retina
        { keywords: ['diabetic retinopathy', 'macular degeneration', 'amd', 'csr', 'cscr', 'retinal vein', 'retinal artery', 'macular edema', 'dme', 'cme', 'brvo', 'crvo', 'drusen', 'cnv', 'anti-vegf', 'intravitreal', 'wet amd', 'dry amd', 'geographic atrophy'], chapter: 'medical_retina' },
        // Cornea
        { keywords: ['cornea', 'keratitis', 'keratoconus', 'corneal transplant', 'dsaek', 'dmek', 'pterygium', 'dry eye', 'fuchs', 'corneal dystrophy', 'corneal ulcer', 'herpetic', 'acanthamoeba', 'cross-linking', 'graft rejection'], chapter: 'cornea' },
        // Lens / Cataract
        { keywords: ['cataract', 'lens', 'phaco', 'iol', 'posterior capsule', 'pco', 'yag capsulotomy', 'femtosecond', 'ectopia lentis', 'aphakia', 'pseudophakia'], chapter: 'lens' },
        // Uveitis
        { keywords: ['uveitis', 'iritis', 'iridocyclitis', 'choroiditis', 'panuveitis', 'hla-b27', 'behcet', 'sarcoid', 'vkh', 'birdshot', 'hypopyon', 'synechia', 'toxoplasm', 'cmv retinitis'], chapter: 'uveitis' },
        // Strabismus
        { keywords: ['strabismus', 'squint', 'esotropia', 'exotropia', 'hypertropia', 'diplopia', 'motility', 'extraocular', 'eom', 'binocular', 'amblyopia', 'cover test', 'duane', 'brown syndrome'], chapter: 'strabismus' },
        // Paediatric
        { keywords: ['paediatric', 'pediatric', 'child', 'congenital', 'rop', 'retinopathy of prematurity', 'leukocoria', 'retinoblastoma child', 'infantile', 'neonatal'], chapter: 'paediatric' },
        // Orbit
        { keywords: ['orbit', 'proptosis', 'exophthalmos', 'thyroid eye', 'graves', 'orbital cellulitis', 'blow out', 'orbital fracture', 'orbital tumor', 'decompression'], chapter: 'orbit' },
        // Lids
        { keywords: ['lid', 'eyelid', 'ptosis', 'ectropion', 'entropion', 'blephar', 'chalazion', 'hordeolum', 'trichiasis', 'lagophthalmos', 'lid tumor', 'bcc eyelid', 'levator', 'blepharoplasty'], chapter: 'lids' },
        // Lacrimal
        { keywords: ['lacrimal', 'tear duct', 'dacryocyst', 'nasolacrimal', 'epiphora', 'dcr', 'punctum', 'canalicul', 'watery eye'], chapter: 'lacrimal' },
        // Conjunctiva
        { keywords: ['conjunctiv', 'pinguecula', 'allergic eye', 'vernal', 'trachoma', 'subconjunctival', 'chemosis', 'pemphigoid ocular', 'stevens-johnson'], chapter: 'conjunctiva' },
        // Sclera
        { keywords: ['scleritis', 'episcleritis', 'sclera', 'necrotizing scleritis'], chapter: 'sclera' },
        // Refractive
        { keywords: ['refractive', 'refraction', 'myopia', 'hyperopia', 'astigmatism', 'lasik', 'prk', 'smile', 'presbyopia', 'icl', 'phakic iol', 'biometry', 'iol calculation'], chapter: 'refractive' },
        // Trauma
        { keywords: ['trauma', 'injury', 'foreign body', 'hyphema', 'open globe', 'chemical burn', 'penetrating', 'iofb', 'commotio'], chapter: 'trauma' },
        // Tumours
        { keywords: ['tumour', 'tumor', 'melanoma', 'retinoblastoma', 'lymphoma', 'metasta', 'choroidal nevus', 'enucleation', 'plaque'], chapter: 'tumours' },
        // Surgery
        { keywords: ['surgery', 'surgical', 'anaesthe', 'anesthe', 'perioperative', 'complication', 'post-op', 'intraoperative'], chapter: 'surgery_care' },
        // Lasers
        { keywords: ['laser', 'yag', 'argon', 'photocoagulation', 'slt', 'prp', 'panretinal', 'micropulse', 'pdt'], chapter: 'lasers' },
        // Therapeutics
        { keywords: ['drug', 'medication', 'drops', 'antibiotic', 'steroid eye', 'anti-vegf', 'pharmacology', 'intravitreal injection', 'eylea', 'lucentis', 'avastin'], chapter: 'therapeutics' },
        // Clinical Skills
        { keywords: ['examination', 'slit lamp', 'fundoscopy', 'tonometry', 'gonioscopy', 'visual acuity', 'ophthalmoscopy', 'clinical assessment'], chapter: 'clinical_skills' },
        // Investigations
        { keywords: ['investigation', 'imaging', 'angiography', 'oct', 'ffa', 'icg', 'visual field test', 'perimetry', 'ultrasound eye', 'b-scan', 'topography', 'electrophysiology'], chapter: 'investigations' },
        // Evidence
        { keywords: ['trial', 'study', 'evidence', 'guideline', 'areds', 'drcr'], chapter: 'evidence' },
    ];

    for (const rule of rules) {
        for (const keyword of rule.keywords) {
            if (titleLower.includes(keyword)) {
                return rule.chapter;
            }
        }
    }

    return 'uncategorized';
}

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
// GitHub Gist API Functions
// ============================================

/**
 * Check if a storage backend is configured
 */
function isConfigured() {
    // Check localStorage first (User configured)
    const localId = localStorage.getItem('gist_id');
    const localToken = localStorage.getItem('gist_token');
    if (localId && localToken) {
        // Update config in memory
        GITHUB_CONFIG.GIST_ID = localId;
        GITHUB_CONFIG.GIST_TOKEN = localToken;
        return true;
    }

    // Check hardcoded config
    if (GITHUB_CONFIG.GIST_ID && GITHUB_CONFIG.GIST_ID !== 'YOUR_GIST_ID_HERE') return true;
    return false;
}

/**
 * Configure Gist Credentials (for UI)
 */
function configureGist(id, token) {
    if (id && token) {
        localStorage.setItem('gist_id', id);
        localStorage.setItem('gist_token', token);
        GITHUB_CONFIG.GIST_ID = id;
        GITHUB_CONFIG.GIST_TOKEN = token;
        return true;
    }
    return false;
}

/**
 * Fetch all submissions from configured storage
 */
async function fetchSubmissions() {
    // Ensure config is loaded
    isConfigured();

    if (!isConfigured()) {
        console.warn('No storage backend configured. Using local demo mode.');
        return getLocalDemoSubmissions();
    }

    try {
        const response = await fetch(`${GITHUB_CONFIG.API_URL}/${GITHUB_CONFIG.GIST_ID}`, {
            headers: {
                // If token is present, use it to get higher rate limits (optional for public gists)
                ...(GITHUB_CONFIG.GIST_TOKEN && GITHUB_CONFIG.GIST_TOKEN !== 'YOUR_GITHUB_TOKEN_HERE'
                    ? { 'Authorization': `token ${GITHUB_CONFIG.GIST_TOKEN}` }
                    : {})
            }
        });

        if (!response.ok) throw new Error(`GitHub Gist error (${response.status})`);

        const gist = await response.json();
        const file = gist.files[GITHUB_CONFIG.FILENAME];

        if (!file) throw new Error(`File ${GITHUB_CONFIG.FILENAME} not found in Gist`);

        // Parse content
        let data = JSON.parse(file.content);

        // Format check
        if (!data.submissions) data.submissions = [];
        if (!data.approved) data.approved = [];
        if (!data.deleted) data.deleted = [];

        return data;

    } catch (err) {
        console.error('Error fetching submissions:', err);
        // Fallback to cache if available
        const cached = localStorage.getItem(COMMUNITY_CACHE_KEY);
        if (cached) {
            console.log('Using cached community data');
            return JSON.parse(cached);
        }
        return { submissions: [], approved: [], deleted: [] };
    }
}

/**
 * Update the storage (Add/Modify submissions)
 */
async function updateSubmissions(data) {
    if (!isConfigured()) {
        console.warn('Storage not configured. Saving to localStorage demo mode.');
        saveLocalDemoSubmissions(data);
        return { success: true };
    }

    if (!GITHUB_CONFIG.GIST_TOKEN || GITHUB_CONFIG.GIST_TOKEN === 'YOUR_GITHUB_TOKEN_HERE') {
        // If we want to allow public submissions without embedding a token, we must use a proxy or Issues.
        // BUT for this task, we assume the user might provide a token OR acts as admin.
        // If "Remote User" tries to submit without a token, this will fail.

        // AUTO-FIX: Check if there's a user-provided token in localStorage
        const userToken = localStorage.getItem('github_personal_token');
        if (userToken) {
            GITHUB_CONFIG.GIST_TOKEN = userToken;
        } else {
            return {
                success: false,
                message: 'Write access required. Please providing a GitHub Token in settings or ask Admin.'
            };
        }
    }

    try {
        const payload = {
            files: {
                [GITHUB_CONFIG.FILENAME]: {
                    content: JSON.stringify(data, null, 2)
                }
            }
        };

        const response = await fetch(`${GITHUB_CONFIG.API_URL}/${GITHUB_CONFIG.GIST_ID}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `token ${GITHUB_CONFIG.GIST_TOKEN}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`GitHub Gist update failed (${response.status}): ${errText}`);
        }

        // Clear cache to force refresh
        localStorage.removeItem(COMMUNITY_CACHE_KEY);
        return { success: true };
    } catch (err) {
        console.error('Error updating submissions:', err);
        return { success: false, message: err.message || 'Unknown network error' };
    }
}

/**
 * Get deleted items (for sync)
 */
async function getDeletedItems() {
    const data = await fetchSubmissions();
    return data.deleted || [];
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
        const result = await updateSubmissions(currentData);

        if (result.success) {
            return {
                success: true,
                message: 'Your infographic has been submitted for review!',
                submissionId: submission.id
            };
        } else {
            return { success: false, message: `Submission failed: ${result.message || 'Unknown error'}` };
        }
    } catch (err) {
        console.error('Submission error:', err);
        return { success: false, message: 'An error occurred. Please try again.' };
    }
}

/**
 * Submit MULTIPLE infographics to the community pool (Batch)
 * Fetches once, appends all, updates once to prevent race conditions
 */
async function submitMultiple(infographicsList, userName) {
    if (!infographicsList || infographicsList.length === 0) {
        return { success: false, message: 'No infographics provided.' };
    }

    if (!userName || userName.trim().length === 0) {
        return { success: false, message: 'Please provide your name.' };
    }

    try {
        const userIP = await getUserIP();
        const currentData = await fetchSubmissions();
        currentData.submissions = currentData.submissions || [];

        const newSubmissions = [];

        // Prepare all submissions
        for (const item of infographicsList) {
            const submission = {
                id: generateSubmissionId() + Math.random().toString(36).substr(2, 5), // Ensure unique ID
                userName: sanitizeInput(userName),
                title: (item.title || item.data?.title) || 'Untitled Infographic',
                summary: (item.summary || item.data?.summary) || '',
                submittedAt: new Date().toISOString(),
                userIP: userIP,
                likes: 0,
                likedBy: [],
                status: 'pending',
                data: item.data || item
            };
            newSubmissions.push(submission);
        }

        // Batch prepend (newest first)
        currentData.submissions.unshift(...newSubmissions);

        // Single update
        const result = await updateSubmissions(currentData);

        if (result.success) {
            return {
                success: true,
                count: newSubmissions.length,
                message: `Successfully submitted ${newSubmissions.length} infographics!`
            };
        } else {
            return { success: false, message: `Batch submission failed: ${result.message || 'Please try again'}` };
        }
    } catch (err) {
        console.error('Batch submission error:', err);
        return { success: false, message: 'An error occurred during batch submission.' };
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
        const result = await updateSubmissions(data);
        if (!result.success) throw new Error(result.message);

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
        const result = await updateSubmissions(data);

        if (result.success) {
            return { success: true, message: 'Submission approved!' };
        } else {
            return { success: false, message: `Failed to approve: ${result.message}` };
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
        const result = await updateSubmissions(data);

        if (result.success) {
            return { success: true, message: 'Submission rejected and removed.' };
        } else {
            return { success: false, message: `Failed to rejection: ${result.message}` };
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

        // DUPLICATE CHECK: Normalize title for comparison
        const normalizeTitle = (t) => (t || '').toLowerCase().trim().replace(/[^a-z0-9]/g, '');
        const submissionTitleNorm = normalizeTitle(submission.title);

        // Check if already exists by communityId, exact match, OR normalized title
        const existsExact = library.some(item =>
            item.communityId === submissionId ||
            (item.title === submission.title && item.date === submission.submittedAt)
        );

        const existsByTitle = library.some(item => {
            const itemTitleNorm = normalizeTitle(item.title);
            return itemTitleNorm === submissionTitleNorm && itemTitleNorm.length > 0;
        });

        if (existsExact) {
            return { success: false, message: 'This infographic is already in your library.' };
        }

        if (existsByTitle) {
            return { success: false, message: `An infographic with a similar title "${submission.title}" already exists in your library.` };
        }

        // Calculate next seqId (highest number for newest)
        let nextSeqId = 1;
        if (library.length > 0) {
            const maxSeqId = library.reduce((max, item) =>
                (item.seqId > max ? item.seqId : max), 0);
            nextSeqId = maxSeqId + 1;
        }

        // Auto-detect chapter from title
        const autoChapter = autoDetectChapterFromTitle(submission.title);

        // Create local library item
        const newItem = {
            id: Date.now(),
            seqId: nextSeqId,
            title: submission.title,
            summary: submission.summary,
            date: new Date().toISOString(),
            data: submission.data,
            chapterId: autoChapter, // Auto-chapterize instead of uncategorized
            _newlyImported: Date.now(), // Mark as newly imported for green highlight
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
// DELETION TRACKING (Admin sync)
// ============================================

/**
 * Normalize title for matching (consistent with script.js)
 */
function normalizeTitle(t) {
    return (t || '').toLowerCase().trim().replace(/[^a-z0-9]/g, '');
}

/**
 * Remove a deleted item from ALL pools: pending, approved, and adds to deleted list
 * This ensures when admin deletes something, it's gone everywhere
 * @param {string} title - The title of the item (will be normalized)
 */
async function removeFromAllPools(title) {
    if (!isConfigured()) {
        console.log('JSONBin not configured, cannot remove from community pools.');
        return { success: false, removed: { pending: 0, approved: 0 } };
    }

    try {
        const data = await fetchSubmissions();
        const normTitle = normalizeTitle(title);

        let removedFromPending = 0;
        let removedFromApproved = 0;

        // Remove from pending submissions
        if (data.submissions && data.submissions.length > 0) {
            const originalLength = data.submissions.length;
            data.submissions = data.submissions.filter(sub => {
                const subNormTitle = normalizeTitle(sub.title);
                return subNormTitle !== normTitle;
            });
            removedFromPending = originalLength - data.submissions.length;
        }

        // Remove from approved submissions
        if (data.approved && data.approved.length > 0) {
            const originalLength = data.approved.length;
            data.approved = data.approved.filter(sub => {
                const subNormTitle = normalizeTitle(sub.title);
                return subNormTitle !== normTitle;
            });
            removedFromApproved = originalLength - data.approved.length;
        }

        // Also add to deleted list so remote users will remove it
        if (!data.deleted) {
            data.deleted = [];
        }
        if (!data.deleted.includes(normTitle)) {
            data.deleted.push(normTitle);
            // Keep only last 100 deletions
            if (data.deleted.length > 100) {
                data.deleted = data.deleted.slice(-100);
            }
        }

        // Update the bin if anything was changed
        if (removedFromPending > 0 || removedFromApproved > 0) {
            const result = await updateSubmissions(data);
            if (!result.success) console.error(`Failed to sync removals: ${result.message}`);
            console.log(`[Admin Delete] Removed from pools - Pending: ${removedFromPending}, Approved: ${removedFromApproved}`);
        } else {
            // Still update to ensure deleted list is saved
            const result = await updateSubmissions(data);
            if (!result.success) console.error(`Failed to sync deletion list: ${result.message}`);
            console.log(`[Admin Delete] No matches found in pools, but added to deleted list: "${normTitle}"`);
        }

        return {
            success: true,
            removed: {
                pending: removedFromPending,
                approved: removedFromApproved
            }
        };
    } catch (err) {
        console.error('Error removing from pools:', err);
        return { success: false, removed: { pending: 0, approved: 0 } };
    }
}

/**
 * Track a deleted item so remote users will also delete it
 * @param {string} normalizedTitle - Normalized title of the deleted item
 */
async function trackDeletion(normalizedTitle) {
    if (!isConfigured()) {
        console.log('JSONBin not configured, cannot track deletion for remote sync.');
        return { success: false };
    }

    try {
        const data = await fetchSubmissions();

        // Initialize deleted array if it doesn't exist
        if (!data.deleted) {
            data.deleted = [];
        }

        // Add to deleted list if not already there
        if (!data.deleted.includes(normalizedTitle)) {
            data.deleted.push(normalizedTitle);

            // Keep only last 100 deletions to prevent unbounded growth
            if (data.deleted.length > 100) {
                data.deleted = data.deleted.slice(-100);
            }

            const result = await updateSubmissions(data);
            if (!result.success) throw new Error(result.message);
            console.log(`[Deletion Sync] Tracked deletion of: ${normalizedTitle}`);
        }

        return { success: true };
    } catch (err) {
        console.error('Error tracking deletion:', err);
        return { success: false };
    }
}

/**
 * Get list of deleted item titles for sync
 */
async function getDeletedItems() {
    if (!isConfigured()) {
        return [];
    }

    try {
        const data = await fetchSubmissions();
        return data.deleted || [];
    } catch (err) {
        console.error('Error getting deleted items:', err);
        return [];
    }
}

// ============================================
// EXPORTS
// ============================================

// Export functions for use in other scripts
window.CommunitySubmissions = {
    // Configuration
    isConfigured: isConfigured,
    configure: configureGist,

    // Submission functions
    submit: submitToCommunity,
    submitMultiple: submitMultiple, // Batch submit
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

    // Deletion sync
    trackDeletion: trackDeletion,
    getDeletedItems: getDeletedItems,
    removeFromAllPools: removeFromAllPools,

    // Utilities
    getUserIP,
    formatDate,
    generateCardHTML: generateSubmissionCardHTML
};

console.log('Community Submissions module loaded.');
console.log('Storage configured:', isConfigured());

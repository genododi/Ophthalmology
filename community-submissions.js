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

// JSONBin.io Configuration - Multi-Bin Sharding to bypass 100kb limit
// Each bin type stays under 100kb by only storing its specific data
// 
// To set up: 
// 1. Go to https://jsonbin.io and create a free account
// 2. Create THREE bins with initial content:
//    - PENDING_BIN: {"submissions": []}
//    - APPROVED_BIN: {"approved": []}
//    - META_BIN: {"deleted": [], "stats": {}}
// 3. Get your bin IDs and API key
// 4. Update these values

const JSONBIN_CONFIG = {
    // Master key for read/write operations
    MASTER_KEY: '$2a$10$jrX.sdAp9v5.opYyQMLuvONbp9SWT3VF7i7eiQbaSpJHiKztRhS9W',
    BASE_URL: 'https://api.jsonbin.io/v3/b',

    // Multi-bin architecture - each bin < 100kb for FREE tier
    // This bypasses the 100kb limit by splitting data across bins
    BINS: {
        // Pending submissions bin (user submissions awaiting approval)
        PENDING: '69679ff543b1c97be9303398',
        // Approved submissions bin (admin-approved content) - NEWLY CREATED
        APPROVED: '69704dc143b1c97be93e4d8c',
        // Metadata bin (deleted items, stats) - uses pending bin
        META: null
    },

    // Legacy single-bin ID (for backwards compatibility during migration)
    LEGACY_BIN_ID: '69679ff543b1c97be9303398'
};

// Admin PIN for approval operations (simple security)
// In production, use a more secure method
const ADMIN_PIN = '309030'; // Change this to your preferred PIN

// IP lookup service (free, no API key needed)
const IP_SERVICE_URL = 'https://api.ipify.org?format=json';

// Local storage keys for caching (separate for each bin type)
const CACHE_KEYS = {
    PENDING: 'ophthalmic_community_pending_cache',
    APPROVED: 'ophthalmic_community_approved_cache',
    META: 'ophthalmic_community_meta_cache',
    // Legacy cache key
    LEGACY: 'ophthalmic_community_cache'
};
const COMMUNITY_CACHE_KEY = CACHE_KEYS.LEGACY; // For backwards compatibility
const COMMUNITY_CACHE_EXPIRY = 1 * 60 * 1000; // 1 minute (reduced from 5 for better cross-user sync)

// ============================================
// STORAGE PROVIDER SELECTION
// ============================================

// Storage provider: 'firebase', 'jsonbin', or 'auto'
// 'auto' = use Firebase if configured, otherwise JSONBin
const STORAGE_PROVIDER = 'auto';

/**
 * Get the active storage provider
 * Returns 'firebase' if Firebase is configured and available, otherwise 'jsonbin'
 */
function getActiveStorageProvider() {
    if (STORAGE_PROVIDER === 'firebase') return 'firebase';
    if (STORAGE_PROVIDER === 'jsonbin') return 'jsonbin';

    // Auto-detect: prefer Firebase if configured
    if (typeof window.FirebaseStorage !== 'undefined' && window.FirebaseStorage.isConfigured()) {
        console.log('[Storage] Using Firebase (no size limits)');
        return 'firebase';
    }

    // Fallback to JSONBin
    console.log('[Storage] Using JSONBin (100kb limit applies)');
    return 'jsonbin';
}

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
    // Enhanced with more clinical terms, abbreviations, and compound phrases
    const rules = [
        // Neuro-ophthalmology - Very comprehensive for visual pathway disorders
        {
            keywords: [
                'neuro', 'optic nerve', 'optic neuritis', 'papill', 'visual field', 'pupil', 'nystagmus',
                'cranial nerve', 'chiasm', 'intracranial', 'iih', 'horner', 'anisocoria', 'gaze palsy',
                'diplopia cranial', 'aion', 'naion', 'pion', 'lhon',
                // Additional neuro terms
                'gca', 'giant cell arteritis', 'temporal arteritis', 'brao', 'crao',
                'iii nerve', 'iv nerve', 'vi nerve', 'third nerve', 'fourth nerve', 'sixth nerve',
                'cn iii', 'cn iv', 'cn vi', 'oculomotor', 'trochlear', 'abducens',
                'pseudotumor cerebri', 'optic disc drusen', 'optic atrophy', 'disc swelling',
                'relative afferent', 'rapd', 'marcus gunn', 'afferent pupil',
                'myasthenia', 'nmj', 'neuromuscular junction', 'ocular myasthenia',
                'supranuclear', 'ino', 'internuclear', 'one-and-a-half syndrome',
                'functional visual loss', 'non-organic', 'functional'
            ], chapter: 'neuro'
        },
        // Glaucoma
        {
            keywords: [
                'glaucoma', 'iop', 'intraocular pressure', 'trabeculectomy', 'angle closure',
                'poag', 'pacg', 'migs', 'tube shunt', 'filtering', 'rnfl', 'optic disc cupping',
                'visual field glaucoma', 'pigmentary glaucoma', 'pseudoexfoliation',
                'kahook', 'kdb', 'istent', 'hydrus', 'xen gel', 'preserflo',
                'ahmed valve', 'baerveldt', 'goniotomy', 'trabeculotomy',
                'selective laser', 'slt', 'alt', 'cyclodiode', 'cyclophotocoagulation'
            ], chapter: 'glaucoma'
        },
        // Vitreoretinal
        {
            keywords: [
                'vitreous', 'retinal detachment', 'vitrectomy', 'macular hole', 'pvd',
                'epiretinal membrane', 'erm', 'scleral buckle', 'rhegmatogenous', 'tractional',
                'pvr', 'silicone oil', 'floaters', 'vitreomacular', 'vmt'
            ], chapter: 'vitreoretinal'
        },
        // Medical Retina - Expanded with all anti-VEGF agents
        {
            keywords: [
                'diabetic retinopathy', 'macular degeneration', 'amd', 'csr', 'cscr',
                'retinal vein', 'retinal artery', 'macular edema', 'dme', 'cme', 'brvo', 'crvo',
                'drusen', 'cnv', 'anti-vegf', 'intravitreal', 'wet amd', 'dry amd', 'geographic atrophy',
                // Anti-VEGF agents
                'eylea', 'lucentis', 'avastin', 'vabysmo', 'beovu', 'brolucizumab', 'faricimab',
                'ranibizumab', 'aflibercept', 'bevacizumab',
                // DR staging
                'pdr', 'npdr', 'proliferative', 'non-proliferative',
                'ozurdex', 'iluvien', 'dexamethasone implant'
            ], chapter: 'medical_retina'
        },
        // Cornea
        {
            keywords: [
                'cornea', 'keratitis', 'keratoconus', 'corneal transplant', 'dsaek', 'dmek',
                'pterygium', 'dry eye', 'fuchs', 'corneal dystrophy', 'corneal ulcer', 'herpetic',
                'acanthamoeba', 'cross-linking', 'graft rejection',
                'dalk', 'pk', 'penetrating keratoplasty', 'endothelial keratoplasty'
            ], chapter: 'cornea'
        },
        // Lens / Cataract - Expanded IOL terms
        {
            keywords: [
                'cataract', 'lens', 'phaco', 'iol', 'posterior capsule', 'pco', 'yag capsulotomy',
                'femtosecond', 'ectopia lentis', 'aphakia', 'pseudophakia',
                'intraocular lens', 'multifocal iol', 'toric iol', 'edof', 'monofocal',
                'refractive lens exchange', 'rle', 'clear lens extraction',
                'flacs', 'femto cataract'
            ], chapter: 'lens'
        },
        // Uveitis
        {
            keywords: [
                'uveitis', 'iritis', 'iridocyclitis', 'choroiditis', 'panuveitis', 'hla-b27',
                'behcet', 'sarcoid', 'vkh', 'birdshot', 'hypopyon', 'synechia', 'toxoplasm',
                'cmv retinitis', 'vogt-koyanagi-harada', 'sympathetic ophthalmia'
            ], chapter: 'uveitis'
        },
        // Strabismus - Expanded with patterns and surgical terms
        {
            keywords: [
                'strabismus', 'squint', 'esotropia', 'exotropia', 'hypertropia', 'diplopia',
                'motility', 'extraocular', 'eom', 'binocular', 'amblyopia', 'cover test',
                'duane', 'brown syndrome',
                'a-pattern', 'v-pattern', 'alphabet pattern', 'hess chart', 'lees screen',
                'prism', 'prism diopter', 'recession', 'resection', 'adjustable suture',
                'concomitant', 'incomitant', 'paralytic', 'restrictive'
            ], chapter: 'strabismus'
        },
        // Paediatric
        {
            keywords: [
                'paediatric', 'pediatric', 'child', 'congenital', 'rop', 'retinopathy of prematurity',
                'leukocoria', 'retinoblastoma child', 'infantile', 'neonatal',
                'ophthalmia neonatorum', 'congenital cataract', 'childhood glaucoma'
            ], chapter: 'paediatric'
        },
        // Orbit
        {
            keywords: [
                'orbit', 'proptosis', 'exophthalmos', 'thyroid eye', 'graves', 'orbital cellulitis',
                'blow out', 'orbital fracture', 'orbital tumor', 'decompression',
                'ted', 'thyroid eye disease', 'graves orbitopathy'
            ], chapter: 'orbit'
        },
        // Lids
        {
            keywords: [
                'lid', 'eyelid', 'ptosis', 'ectropion', 'entropion', 'blephar', 'chalazion',
                'hordeolum', 'trichiasis', 'lagophthalmos', 'lid tumor', 'bcc eyelid',
                'levator', 'blepharoplasty', 'dermatochalasis'
            ], chapter: 'lids'
        },
        // Lacrimal
        {
            keywords: [
                'lacrimal', 'tear duct', 'dacryocyst', 'nasolacrimal', 'epiphora', 'dcr',
                'punctum', 'canalicul', 'watery eye', 'dacryocystorhinostomy'
            ], chapter: 'lacrimal'
        },
        // Conjunctiva
        {
            keywords: [
                'conjunctiv', 'pinguecula', 'allergic eye', 'vernal', 'trachoma',
                'subconjunctival', 'chemosis', 'pemphigoid ocular', 'stevens-johnson'
            ], chapter: 'conjunctiva'
        },
        // Sclera
        { keywords: ['scleritis', 'episcleritis', 'sclera', 'necrotizing scleritis'], chapter: 'sclera' },
        // Refractive - Enhanced
        {
            keywords: [
                'refractive', 'refraction', 'myopia', 'hyperopia', 'astigmatism', 'lasik', 'prk',
                'smile', 'presbyopia', 'icl', 'phakic iol', 'biometry', 'iol calculation',
                'spectacles', 'glasses', 'contact lens', 'orthokeratology',
                'excimer', 'femtosecond laser'
            ], chapter: 'refractive'
        },
        // Trauma
        {
            keywords: [
                'trauma', 'injury', 'foreign body', 'hyphema', 'open globe', 'chemical burn',
                'penetrating', 'iofb', 'commotio', 'laceration', 'blunt trauma',
                'thermal injury', 'alkali burn', 'acid burn'
            ], chapter: 'trauma'
        },
        // Tumours
        {
            keywords: [
                'tumour', 'tumor', 'melanoma', 'retinoblastoma', 'lymphoma', 'metasta',
                'choroidal nevus', 'enucleation', 'plaque', 'ocular oncology'
            ], chapter: 'tumours'
        },
        // Surgery
        {
            keywords: [
                'surgery', 'surgical', 'anaesthe', 'anesthe', 'perioperative', 'complication',
                'post-op', 'intraoperative', 'topical anesthesia', 'retrobulbar', 'peribulbar'
            ], chapter: 'surgery_care'
        },
        // Lasers
        {
            keywords: [
                'laser', 'yag', 'argon', 'photocoagulation', 'slt', 'prp', 'panretinal',
                'micropulse', 'pdt', 'photodynamic'
            ], chapter: 'lasers'
        },
        // Therapeutics
        {
            keywords: [
                'drug', 'medication', 'drops', 'antibiotic', 'steroid eye', 'anti-vegf',
                'pharmacology', 'intravitreal injection', 'eylea', 'lucentis', 'avastin',
                'topical therapy', 'preservative free'
            ], chapter: 'therapeutics'
        },
        // Clinical Skills
        {
            keywords: [
                'examination', 'slit lamp', 'fundoscopy', 'tonometry', 'gonioscopy',
                'visual acuity', 'ophthalmoscopy', 'clinical assessment', 'refraction technique'
            ], chapter: 'clinical_skills'
        },
        // Investigations
        {
            keywords: [
                'investigation', 'imaging', 'angiography', 'oct', 'ffa', 'icg', 'visual field test',
                'perimetry', 'ultrasound eye', 'b-scan', 'topography', 'electrophysiology',
                'oct-a', 'octa', 'specular microscopy', 'pachymetry', 'biometry'
            ], chapter: 'investigations'
        },
        // Evidence
        { keywords: ['trial', 'study', 'evidence', 'guideline', 'areds', 'drcr', 'protocol'], chapter: 'evidence' },
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
// JSONBin.io API Functions
// ============================================

/**
 * Check if JSONBin is configured
 */
function isJSONBinConfigured() {
    const hasPendingBin = JSONBIN_CONFIG.BINS?.PENDING || JSONBIN_CONFIG.LEGACY_BIN_ID;
    const hasMasterKey = JSONBIN_CONFIG.MASTER_KEY && JSONBIN_CONFIG.MASTER_KEY !== '$2a$10$YOUR_MASTER_KEY_HERE';
    return hasPendingBin && hasMasterKey;
}

/**
 * Get the appropriate bin ID for a given type
 * Falls back to LEGACY_BIN_ID for backwards compatibility
 */
function getBinId(type = 'PENDING') {
    if (JSONBIN_CONFIG.BINS && JSONBIN_CONFIG.BINS[type]) {
        return JSONBIN_CONFIG.BINS[type];
    }
    // Fallback to legacy single-bin
    return JSONBIN_CONFIG.LEGACY_BIN_ID;
}

/**
 * Fetch all submissions from JSONBin
 * @param {boolean} forceRefresh - If true, bypass cache and fetch fresh data
 */
async function fetchSubmissions(forceRefresh = false) {
    // Check which storage provider to use
    const provider = getActiveStorageProvider();

    if (provider === 'firebase' && window.FirebaseStorage) {
        console.log('[Fetch] Using Firebase storage');
        return await window.FirebaseStorage.fetchSubmissions();
    }

    // Use JSONBin with MULTI-BIN SHARDING
    if (!isJSONBinConfigured()) {
        console.warn('JSONBin not configured. Using demo mode with localStorage.');
        return getLocalDemoSubmissions();
    }

    // Force refresh: clear all caches
    if (forceRefresh) {
        localStorage.removeItem(CACHE_KEYS.PENDING);
        localStorage.removeItem(CACHE_KEYS.APPROVED);
        localStorage.removeItem(COMMUNITY_CACHE_KEY);
        console.log('Force refresh: all caches cleared');
    }

    // Check cache first (unless force refresh)
    if (!forceRefresh) {
        const cached = localStorage.getItem(COMMUNITY_CACHE_KEY);
        if (cached) {
            const { data, timestamp } = JSON.parse(cached);
            if (Date.now() - timestamp < COMMUNITY_CACHE_EXPIRY) {
                console.log('Using cached community submissions');
                return data;
            }
        }
    }

    try {
        // MULTI-BIN FETCH: Read from separate bins in parallel
        const pendingBinId = getBinId('PENDING');
        const approvedBinId = getBinId('APPROVED');
        const useMultiBin = JSONBIN_CONFIG.BINS.APPROVED && approvedBinId !== pendingBinId;

        if (useMultiBin) {
            console.log('[Fetch] Using multi-bin sharding (no 100kb limit!)');

            // Fetch from both bins in parallel
            const [pendingRes, approvedRes] = await Promise.all([
                fetch(`${JSONBIN_CONFIG.BASE_URL}/${pendingBinId}/latest`, {
                    headers: { 'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY }
                }),
                fetch(`${JSONBIN_CONFIG.BASE_URL}/${approvedBinId}/latest`, {
                    headers: { 'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY }
                })
            ]);

            const pendingData = pendingRes.ok ? (await pendingRes.json()).record : { submissions: [] };
            const approvedData = approvedRes.ok ? (await approvedRes.json()).record : { approved: [] };

            // Aggregate data from both bins
            const data = {
                submissions: pendingData.submissions || [],
                approved: approvedData.approved || [],
                deleted: pendingData.deleted || [],
                _pendingVersion: pendingRes.ok ? (await pendingRes.json())?.metadata?.version : null,
                _approvedVersion: approvedRes.ok ? (await approvedRes.json())?.metadata?.version : null
            };

            // Cache the aggregated result
            localStorage.setItem(COMMUNITY_CACHE_KEY, JSON.stringify({
                data,
                timestamp: Date.now()
            }));

            console.log(`[Fetch] Got ${data.submissions.length} pending, ${data.approved.length} approved`);
            return data;
        }

        // LEGACY: Single-bin mode (fallback)
        console.log('[Fetch] Using single-bin mode');
        const response = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${pendingBinId}/latest`, {
            headers: { 'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY }
        });

        if (!response.ok) {
            throw new Error(`JSONBin fetch failed: ${response.status}`);
        }

        const result = await response.json();
        const data = result.record || { submissions: [], approved: [] };
        data._binVersion = result.metadata?.version;

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
        return { success: true };
    }

    try {
        const headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY
        };

        // Add version header if available (required for v3 API updates)
        if (data._binVersion !== undefined && data._binVersion !== null) {
            headers['X-Bin-Version'] = data._binVersion;
        }

        const payload = { ...data };
        delete payload._binVersion;

        const binId = getBinId('PENDING'); // Use pending bin for all writes (legacy mode)
        const response = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${binId}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            // If version conflict, try fetching fresh and retry
            if (response.status === 409) {
                console.log('Version conflict, refreshing and retrying...');
                localStorage.removeItem(COMMUNITY_CACHE_KEY);
                const freshData = await fetchSubmissions();
                freshData.submissions = freshData.submissions || [];
                // Re-add new submissions
                const newSubs = data.submissions.filter(s =>
                    !freshData.submissions.some(fs => fs.id === s.id)
                );
                freshData.submissions.unshift(...newSubs);
                return updateSubmissions(freshData);
            }

            let errorDetails = '';
            try {
                const responseText = await response.text();
                if (responseText) {
                    try {
                        const parsed = JSON.parse(responseText);
                        errorDetails = parsed.message || parsed.error || responseText;
                    } catch {
                        errorDetails = responseText;
                    }
                }
            } catch {
                // Ignore read errors
            }

            return {
                success: false,
                message: `JSONBin Error: ${response.status} ${response.statusText}${errorDetails ? ` - ${errorDetails}` : ''}`
            };
        }

        // Clear cache to force refresh
        localStorage.removeItem(COMMUNITY_CACHE_KEY);
        return { success: true };
    } catch (err) {
        console.error('Error updating submissions:', err);
        return {
            success: false,
            message: `Network Error: ${err.message}`
        };
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
// DATA SIZE MANAGEMENT (100kb limit workaround)
// ============================================

// AGGRESSIVE limits to keep bin under 100kb
// Each infographic with sections can be 2-5kb, so these limits are conservative
const MAX_PENDING_SUBMISSIONS = 15;  // Reduced from 30
const MAX_APPROVED_SUBMISSIONS = 25; // Reduced from 50
const PENDING_MAX_AGE_DAYS = 14;     // Reduced from 30 days
const MAX_BIN_SIZE_BYTES = 95000;    // 95kb target (with 5kb safety margin)

/**
 * Minimize infographic data for storage (strips unnecessary fields)
 * This reduces data size significantly while preserving core content
 */
function minimizeInfographicData(data) {
    if (!data) return data;

    const minimized = {
        title: data.title || '',
        summary: data.summary || '',
        sections: []
    };

    // Copy sections but strip SVG illustrations (largest data culprit)
    if (data.sections && Array.isArray(data.sections)) {
        minimized.sections = data.sections.map(section => ({
            title: section.title || '',
            type: section.type || '',
            layout: section.layout || 'half_width',
            color_theme: section.color_theme || 'blue',
            content: section.content
            // Omit: icon (small), any embedded SVGs or large strings
        }));
    }

    // Exclude summary_illustration (SVG) as it's typically very large
    // It can be regenerated if needed

    return minimized;
}

/**
 * Calculate approximate JSON size in bytes
 */
function estimateJSONSize(obj) {
    return new TextEncoder().encode(JSON.stringify(obj)).length;
}

/**
 * Clean up old pending submissions and limit counts to stay under 100kb
 * Uses AGGRESSIVE iterative pruning to guarantee staying under limit
 * Called automatically before submissions
 */
function cleanupDataForSizeLimit(data) {
    let modified = false;

    // 1. Remove pending submissions older than MAX_AGE_DAYS
    if (data.submissions && data.submissions.length > 0) {
        const cutoffDate = Date.now() - (PENDING_MAX_AGE_DAYS * 24 * 60 * 60 * 1000);
        const originalCount = data.submissions.length;

        data.submissions = data.submissions.filter(sub => {
            const submittedAt = new Date(sub.submittedAt).getTime();
            return submittedAt > cutoffDate;
        });

        if (data.submissions.length < originalCount) {
            console.log(`[Size Cleanup] Removed ${originalCount - data.submissions.length} old pending submissions`);
            modified = true;
        }
    }

    // 2. Limit pending submissions to MAX_PENDING
    if (data.submissions && data.submissions.length > MAX_PENDING_SUBMISSIONS) {
        const removed = data.submissions.length - MAX_PENDING_SUBMISSIONS;
        data.submissions = data.submissions.slice(0, MAX_PENDING_SUBMISSIONS);
        console.log(`[Size Cleanup] Trimmed ${removed} oldest pending submissions (over limit)`);
        modified = true;
    }

    // 3. Limit approved submissions to MAX_APPROVED (keep newest)
    if (data.approved && data.approved.length > MAX_APPROVED_SUBMISSIONS) {
        const removed = data.approved.length - MAX_APPROVED_SUBMISSIONS;
        data.approved = data.approved.slice(0, MAX_APPROVED_SUBMISSIONS);
        console.log(`[Size Cleanup] Trimmed ${removed} oldest approved submissions (over limit)`);
        modified = true;
    }

    // 4. Strip large likedBy arrays from all submissions (can grow unbounded)
    const stripLikedByArrays = (items) => {
        if (!items) return;
        items.forEach(item => {
            if (item.likedBy && item.likedBy.length > 10) {
                item.likedBy = item.likedBy.slice(-10); // Keep only last 10 likes
                modified = true;
            }
        });
    };
    stripLikedByArrays(data.submissions);
    stripLikedByArrays(data.approved);

    // 5. AGGRESSIVE ITERATIVE PRUNING: Keep removing oldest until under 95kb
    let estimatedSize = estimateJSONSize(data);
    let iterations = 0;
    const maxIterations = 20; // Safety limit

    while (estimatedSize > MAX_BIN_SIZE_BYTES && iterations < maxIterations) {
        iterations++;
        let removedSomething = false;

        // First try removing oldest approved (they're larger and already downloaded)
        if (data.approved && data.approved.length > 5) {
            data.approved.pop(); // Remove oldest approved
            removedSomething = true;
            console.log(`[Size Prune ${iterations}] Removed oldest approved to reduce size`);
        }
        // Then try removing oldest pending
        else if (data.submissions && data.submissions.length > 3) {
            data.submissions.pop(); // Remove oldest pending
            removedSomething = true;
            console.log(`[Size Prune ${iterations}] Removed oldest pending to reduce size`);
        }
        // If still over, remove deleted list items
        else if (data.deleted && data.deleted.length > 10) {
            data.deleted = data.deleted.slice(-10);
            removedSomething = true;
            console.log(`[Size Prune ${iterations}] Trimmed deleted list`);
        }

        if (!removedSomething) {
            console.warn('[Size Prune] Cannot reduce size further - minimum items reached');
            break;
        }

        estimatedSize = estimateJSONSize(data);
        modified = true;
    }

    console.log(`[Size Check] Final bin size: ${(estimatedSize / 1024).toFixed(1)} KB (target: <${MAX_BIN_SIZE_BYTES / 1024}KB)`);

    if (estimatedSize > MAX_BIN_SIZE_BYTES) {
        console.error('[Size Error] Still over 95kb after maximum pruning!');
    }

    return { data, modified, estimatedSize };
}


// SUBMISSION FUNCTIONS
// ============================================

/**
 * Submit an infographic to the community pool
 * Uses Firebase if configured (no size limits), otherwise JSONBin
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

        // Create submission object - AUTO APPROVED
        const submission = {
            id: generateSubmissionId(),
            userName: sanitizeInput(userName),
            title: infographicData.title || 'Untitled Infographic',
            summary: infographicData.summary || '',
            submittedAt: new Date().toISOString(),
            approvedAt: new Date().toISOString(), // Auto-approved timestamp
            userIP: userIP,
            likes: 0,
            likedBy: [],
            status: 'approved', // Auto-approve
            data: minimizeInfographicData(infographicData)
        };

        // Check which storage provider to use
        const provider = getActiveStorageProvider();

        if (provider === 'firebase' && window.FirebaseStorage) {
            // Use Firebase - no size limits!
            console.log('[Submit] Using Firebase storage');
            return await window.FirebaseStorage.submit(submission);
        }

        // Use JSONBin with size management
        console.log('[Submit] Using JSONBin storage (Auto-Approved)');

        // Fetch current submissions
        const currentData = await fetchSubmissions();

        // Add to APPROVED list immediately
        currentData.approved = currentData.approved || [];
        currentData.approved.unshift(submission);

        // Cleanup old/excess submissions to prevent 100kb limit
        const { data: cleanedData, estimatedSize } = cleanupDataForSizeLimit(currentData);

        // Update storage
        // CHECK FOR MULTI-BIN MODE
        const useMultiBin = JSONBIN_CONFIG.BINS.APPROVED &&
            getBinId('APPROVED') !== getBinId('PENDING');

        if (useMultiBin) {
            console.log('[Submit] Using multi-bin mode - saving to Approved bin');
            // Save APPROVED bin
            const approvedResult = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${getBinId('APPROVED')}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY
                },
                body: JSON.stringify({ approved: cleanedData.approved })
            });

            // We also need to save PENDING bin if cleanup modified it (e.g. pruned pending items)
            // But main action is Approved. Let's try to update Pending too just to be safe and consistent
            const pendingResult = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${getBinId('PENDING')}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY
                },
                body: JSON.stringify({
                    submissions: cleanedData.submissions,
                    deleted: cleanedData.deleted || []
                })
            });

            if (approvedResult.ok) {
                localStorage.removeItem(COMMUNITY_CACHE_KEY);
                return {
                    success: true,
                    message: 'Your infographic has been published to the Community!',
                    submissionId: submission.id
                };
            } else {
                return { success: false, message: 'Failed to publish to approved bin.' };
            }

        } else {
            // Legacy Single Bin
            const result = await updateSubmissions(cleanedData);
            if (result.success) {
                return {
                    success: true,
                    message: 'Your infographic has been published to the Community!',
                    submissionId: submission.id
                };
            } else {
                return { success: false, message: result.message || 'Failed to submit. Please try again.' };
            }
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
        currentData.approved = currentData.approved || []; // Target APPROVED

        const newSubmissions = [];

        // Prepare all submissions - AUTO APPROVED
        for (const item of infographicsList) {
            const submission = {
                id: generateSubmissionId() + Math.random().toString(36).substr(2, 5), // Ensure unique ID
                userName: sanitizeInput(userName),
                title: (item.title || item.data?.title) || 'Untitled Infographic',
                summary: (item.summary || item.data?.summary) || '',
                submittedAt: new Date().toISOString(),
                approvedAt: new Date().toISOString(),
                userIP: userIP,
                likes: 0,
                likedBy: [],
                status: 'approved', // Auto-approve
                data: item.data || item
            };
            newSubmissions.push(submission);
        }

        // Batch prepend to APPROVED (newest first)
        currentData.approved.unshift(...newSubmissions);

        // Cleanup size
        const { data: cleanedData, estimatedSize } = cleanupDataForSizeLimit(currentData);

        // Check Multi-Bin
        const useMultiBin = JSONBIN_CONFIG.BINS.APPROVED &&
            getBinId('APPROVED') !== getBinId('PENDING');

        if (useMultiBin) {
            console.log('[Batch Submit] Using multi-bin mode - saving to Approved bin');
            const approvedResult = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${getBinId('APPROVED')}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY },
                body: JSON.stringify({ approved: cleanedData.approved })
            });
            // Update Pending too just in case cleanup pruned something
            await fetch(`${JSONBIN_CONFIG.BASE_URL}/${getBinId('PENDING')}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY },
                body: JSON.stringify({ submissions: cleanedData.submissions, deleted: cleanedData.deleted || [] })
            });

            if (approvedResult.ok) {
                localStorage.removeItem(COMMUNITY_CACHE_KEY);
                return {
                    success: true,
                    count: newSubmissions.length,
                    message: `Successfully published ${newSubmissions.length} infographics!`
                };
            } else {
                return { success: false, message: 'Failed to batch publish.' };
            }
        } else {
            // Single Bin Legacy
            const result = await updateSubmissions(cleanedData);
            if (result.success) {
                return {
                    success: true,
                    count: newSubmissions.length,
                    message: `Successfully published ${newSubmissions.length} infographics!`
                };
            } else {
                return { success: false, message: result.message || 'Batch submission failed. Please try again.' };
            }
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
        // Update storage
        const result = await updateSubmissions(data);

        if (!result.success) {
            return { success: false, message: result.message || 'Failed to like.' };
        }

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
    /*
    if (!verifyAdminPIN(pin)) {
        return { success: false, message: 'Invalid admin PIN.' };
    }
    */

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

        // MULTI-BIN MODE: Write to separate bins
        const useMultiBin = JSONBIN_CONFIG.BINS.APPROVED &&
            getBinId('APPROVED') !== getBinId('PENDING');

        if (useMultiBin) {
            console.log('[Approve] Using multi-bin mode - updating both bins');

            // Update PENDING bin (remove the approved item)
            const pendingResult = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${getBinId('PENDING')}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY
                },
                body: JSON.stringify({
                    submissions: data.submissions,
                    deleted: data.deleted || []
                })
            });

            // Update APPROVED bin (add the approved item)
            const approvedResult = await fetch(`${JSONBIN_CONFIG.BASE_URL}/${getBinId('APPROVED')}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Master-Key': JSONBIN_CONFIG.MASTER_KEY
                },
                body: JSON.stringify({ approved: data.approved })
            });

            if (pendingResult.ok && approvedResult.ok) {
                // Clear cache to force refresh
                localStorage.removeItem(COMMUNITY_CACHE_KEY);
                return { success: true, message: 'Submission approved!' };
            } else {
                const errText = !pendingResult.ok ? await pendingResult.text() : await approvedResult.text();
                return { success: false, message: `Failed to approve: ${errText}` };
            }
        }

        // LEGACY: Single-bin mode
        const result = await updateSubmissions(data);

        if (result.success) {
            return { success: true, message: 'Submission approved!' };
        } else {
            return { success: false, message: result.message || 'Failed to approve.' };
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
    /*
    if (!verifyAdminPIN(pin)) {
        return { success: false, message: 'Invalid admin PIN.' };
    }
    */

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
        // Update storage
        const result = await updateSubmissions(data);

        if (result.success) {
            return { success: true, message: 'Submission rejected and removed.' };
        } else {
            return { success: false, message: result.message || 'Failed to reject.' };
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
    if (!isJSONBinConfigured()) {
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
            if (result.success) {
                console.log(`[Admin Delete] Removed from pools - Pending: ${removedFromPending}, Approved: ${removedFromApproved}`);
            }
        } else {
            // Still update to ensure deleted list is saved
            const result = await updateSubmissions(data);
            if (result.success) {
                console.log(`[Admin Delete] No matches found in pools, but added to deleted list: "${normTitle}"`);
            }
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
    if (!isJSONBinConfigured()) {
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
            if (result.success) {
                console.log(`[Deletion Sync] Tracked deletion of: ${normalizedTitle}`);
            }
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
    if (!isJSONBinConfigured()) {
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
    isConfigured: isJSONBinConfigured,

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
console.log('JSONBin configured:', isJSONBinConfigured());

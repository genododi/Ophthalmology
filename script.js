import { GoogleGenerativeAI } from "@google/generative-ai";

const generateBtn = document.getElementById('generate-btn');
const apiKeyInput = document.getElementById('api-key');
const topicInput = document.getElementById('topic-input');
const outputContainer = document.getElementById('output-container');

// Add Print Button Logic if not present (will be added to HTML separately)
function setupPrintButton() {
    const printBtn = document.getElementById('print-btn');
    if (printBtn) {
        printBtn.addEventListener('click', () => {
            window.print();
        });
    }
}

const downloadBtn = document.getElementById('download-pdf-btn');

// Home Button Logic
const homeBtn = document.getElementById('home-btn');
if (homeBtn) {
    homeBtn.addEventListener('click', () => {
        if (confirm("Return to Home? This will clear current work.")) {
            window.location.reload();
        }
    });
}

// Sidebar Toggle Functionality
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const appContainer = document.querySelector('.app-container');

function collapseSidebar() {
    if (sidebar && appContainer) {
        sidebar.classList.add('collapsed');
        appContainer.classList.add('sidebar-collapsed');
    }
}

function expandSidebar() {
    if (sidebar && appContainer) {
        sidebar.classList.remove('collapsed');
        appContainer.classList.remove('sidebar-collapsed');
    }
}

function toggleSidebar() {
    if (sidebar && sidebar.classList.contains('collapsed')) {
        expandSidebar();
    } else {
        collapseSidebar();
    }
}

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', toggleSidebar);
}

function setupPosterButton() {
    const posterBtn = document.getElementById('poster-btn');
    if (posterBtn) {
        posterBtn.addEventListener('click', () => {
            const sheet = document.querySelector('.poster-sheet');
            if (sheet) {
                const isLandscape = sheet.classList.toggle('landscape');
                document.body.classList.toggle('landscape-mode');

                if (isLandscape) {
                    posterBtn.classList.add('active-btn');
                    posterBtn.innerHTML = '<span class="material-symbols-rounded">crop_portrait</span>';
                    posterBtn.title = "Switch to Portrait";
                } else {
                    posterBtn.classList.remove('active-btn');
                    posterBtn.innerHTML = '<span class="material-symbols-rounded">panorama</span>';
                    posterBtn.title = "Switch to Landscape";
                    sheet.style.fontSize = '';
                }
            }
        });
    }

    // Always enable download button if it exists
    if (downloadBtn) {
        downloadBtn.style.display = 'flex';
        downloadBtn.addEventListener('click', () => {
            const sheet = document.querySelector('.poster-sheet');
            if (sheet) exportToPDF(sheet);
            else alert("Please generate an infographic first.");
        });
    }
}

function fitContentToLandscape(sheet) {
    if (!sheet.classList.contains('landscape')) return;

    let fontSize = 16;
    sheet.style.fontSize = `${fontSize}px`;

    const minFontSize = 10;
    const maxIterations = 20;
    let i = 0;

    while (sheet.scrollHeight > sheet.clientHeight && fontSize > minFontSize && i < maxIterations) {
        fontSize -= 0.5;
        sheet.style.fontSize = `${fontSize}px`;
        i++;
    }
}

// TEXT-RENDERED PDF EXPORT (NOT IMAGE-BASED)
async function exportToPDF(element) {
    try {
        if (downloadBtn) {
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<span class="material-symbols-rounded margin-right:0;">hourglass_top</span>';
            document.body.style.cursor = 'wait';
        }

        if (!currentInfographicData) {
            alert("No infographic data available for export.");
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<span class="material-symbols-rounded">download</span>';
                document.body.style.cursor = 'default';
            }
            return;
        }

        const isLandscape = element.classList.contains('landscape');
        const orientation = isLandscape ? 'landscape' : 'portrait';
        const data = currentInfographicData;

        // Create PDF with text rendering
        const pdf = new jspdf.jsPDF({
            orientation: orientation,
            unit: 'mm',
            format: 'a4'
        });

        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const margin = 18;
        const contentWidth = pageWidth - (margin * 2);
        let yPos = margin;

        // Color definitions
        const colors = {
            primary: [37, 99, 235],      // Blue
            primaryDark: [30, 41, 59],   // Dark blue-gray
            text: [31, 41, 55],          // Dark text
            textSecondary: [75, 85, 99], // Secondary text
            red: [220, 38, 38],
            green: [16, 185, 129],
            yellow: [245, 158, 11],
            purple: [139, 92, 246],
            border: [226, 232, 240]
        };

        // Helper: Add new page if needed
        const checkPageBreak = (neededHeight) => {
            if (yPos + neededHeight > pageHeight - margin) {
                pdf.addPage();
                yPos = margin;
                return true;
            }
            return false;
        };

        // Helper: Draw colored box
        const drawBox = (x, y, w, h, color, filled = true) => {
            if (filled) {
                pdf.setFillColor(...color);
                pdf.rect(x, y, w, h, 'F');
            } else {
                pdf.setDrawColor(...color);
                pdf.rect(x, y, w, h, 'S');
            }
        };

        // Header bar
        drawBox(0, 0, pageWidth, 8, colors.primary);
        yPos = 12;

        // Title
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(24);
        pdf.setTextColor(...colors.primaryDark);
        const titleLines = pdf.splitTextToSize(data.title || 'Infographic', contentWidth);
        pdf.text(titleLines, margin, yPos);
        yPos += titleLines.length * 10 + 5;

        // Summary
        if (data.summary) {
            pdf.setFont('helvetica', 'normal');
            pdf.setFontSize(11);
            pdf.setTextColor(...colors.textSecondary);
            const summaryLines = pdf.splitTextToSize(data.summary, contentWidth);
            pdf.text(summaryLines, margin, yPos);
            yPos += summaryLines.length * 5 + 10;
        }

        // Separator line
        pdf.setDrawColor(...colors.border);
        pdf.setLineWidth(0.5);
        pdf.line(margin, yPos, pageWidth - margin, yPos);
        yPos += 10;

        // Sections
        if (data.sections && Array.isArray(data.sections)) {
            // Helper: Auto-fit text block with font size adjustment
            const autoFitTextBlock = (text, maxWidth, maxFontSize = 10, minFontSize = 7) => {
                const textStr = String(text || '');
                let fontSize = maxFontSize;
                let lines;
                let lineHeight;

                while (fontSize >= minFontSize) {
                    pdf.setFontSize(fontSize);
                    lineHeight = fontSize * 0.45;
                    lines = pdf.splitTextToSize(textStr, maxWidth);

                    // Accept if reasonable line count
                    if (lines.length <= 8) {
                        return { fontSize, lines, lineHeight };
                    }
                    fontSize -= 0.5;
                }

                // Use minimum and accept any line count
                pdf.setFontSize(minFontSize);
                lineHeight = minFontSize * 0.45;
                lines = pdf.splitTextToSize(textStr, maxWidth);
                return { fontSize: minFontSize, lines, lineHeight };
            };

            for (const section of data.sections) {
                // Estimate section height for page break check
                checkPageBreak(30);

                // Section title with color indicator
                const themeColor = colors[section.color_theme] || colors.primary;

                // Color bar for section
                drawBox(margin, yPos - 2, 3, 8, themeColor);

                pdf.setFont('helvetica', 'bold');
                pdf.setFontSize(14);
                pdf.setTextColor(...colors.primaryDark);
                pdf.text(section.title || 'Section', margin + 6, yPos + 4);
                yPos += 12;

                // Section content based on type
                pdf.setFont('helvetica', 'normal');
                pdf.setFontSize(10);
                pdf.setTextColor(...colors.text);

                switch (section.type) {
                    case 'red_flag':
                        const flags = Array.isArray(section.content) ? section.content : [section.content];
                        for (const flag of flags) {
                            // Auto-fit the flag text
                            const fit = autoFitTextBlock(flag, contentWidth - 14, 10, 7);
                            const flagHeight = fit.lines.length * fit.lineHeight + 4;

                            checkPageBreak(flagHeight);

                            // Red warning indicator
                            pdf.setFillColor(...colors.red);
                            pdf.circle(margin + 2, yPos + 2, 1.5, 'F');

                            // Draw all lines
                            pdf.setFontSize(fit.fontSize);
                            pdf.setTextColor(...colors.red);
                            fit.lines.forEach((line, idx) => {
                                pdf.text(line, margin + 8, yPos + idx * fit.lineHeight);
                            });
                            yPos += flagHeight;
                        }
                        pdf.setTextColor(...colors.text);
                        break;

                    case 'chart':
                        const chartData = section.content?.data || [];
                        for (const item of chartData) {
                            // Auto-fit chart label
                            const labelFit = autoFitTextBlock(item.label, contentWidth * 0.68, 9, 7);
                            const labelHeight = labelFit.lines.length * labelFit.lineHeight;

                            checkPageBreak(labelHeight + 8);

                            pdf.setFontSize(labelFit.fontSize);
                            labelFit.lines.forEach((line, idx) => {
                                pdf.text(line, margin, yPos + idx * labelFit.lineHeight);
                            });
                            yPos += labelHeight + 1;

                            // Draw bar background
                            drawBox(margin, yPos, contentWidth * 0.7, 5, [226, 232, 240]);
                            // Draw bar fill
                            const barWidth = (contentWidth * 0.7) * (item.value / 100);
                            drawBox(margin, yPos, barWidth, 5, themeColor);
                            // Value text
                            pdf.setFontSize(8);
                            pdf.text(`${item.value}%`, margin + contentWidth * 0.72, yPos + 4);
                            yPos += 8;
                        }
                        break;

                    case 'remember':
                        const mem = section.content || {};

                        // Auto-fit explanation text
                        const expFit = autoFitTextBlock(mem.explanation || '', contentWidth - 14, 10, 7);
                        const expHeight = expFit.lines.length * expFit.lineHeight;
                        const boxHeight = Math.max(22, 12 + expHeight + 4);

                        checkPageBreak(boxHeight + 5);

                        // Mnemonic box
                        drawBox(margin, yPos, contentWidth, boxHeight, [253, 252, 255]);
                        pdf.setDrawColor(...colors.purple);
                        pdf.rect(margin, yPos, contentWidth, boxHeight, 'S');

                        // Mnemonic title
                        pdf.setFont('helvetica', 'bold');
                        pdf.setFontSize(18);
                        pdf.setTextColor(...colors.purple);
                        pdf.text(mem.mnemonic || 'REMEMBER', margin + contentWidth / 2, yPos + 8, { align: 'center' });

                        // Explanation - all lines
                        pdf.setFont('helvetica', 'normal');
                        pdf.setFontSize(expFit.fontSize);
                        pdf.setTextColor(...colors.text);
                        expFit.lines.forEach((line, idx) => {
                            pdf.text(line, margin + 5, yPos + 14 + idx * expFit.lineHeight);
                        });
                        yPos += boxHeight + 5;
                        break;

                    case 'mindmap':
                        const map = section.content || {};
                        checkPageBreak(25);

                        // Center concept
                        pdf.setFillColor(...colors.primaryDark);
                        const centerText = map.center || 'Concept';
                        pdf.setFontSize(10);
                        const centerWidth = pdf.getTextWidth(centerText) + 10;
                        pdf.roundedRect(margin + (contentWidth - centerWidth) / 2, yPos, centerWidth, 8, 2, 2, 'F');
                        pdf.setTextColor(255, 255, 255);
                        pdf.setFont('helvetica', 'bold');
                        pdf.text(centerText, margin + contentWidth / 2, yPos + 5.5, { align: 'center' });
                        yPos += 12;

                        // Branches - with auto-fit for each
                        pdf.setTextColor(...colors.text);
                        pdf.setFont('helvetica', 'normal');
                        const branches = map.branches || [];
                        const numBranchCols = Math.min(branches.length, 3);
                        const branchWidth = contentWidth / numBranchCols;

                        for (let i = 0; i < branches.length; i++) {
                            if (i > 0 && i % 3 === 0) {
                                yPos += 10;
                            }

                            const colIdx = i % 3;
                            const branchX = margin + colIdx * branchWidth;

                            // Auto-fit branch text
                            const branchFit = autoFitTextBlock(branches[i], branchWidth - 8, 9, 6);
                            const branchHeight = Math.max(8, branchFit.lines.length * branchFit.lineHeight + 4);

                            checkPageBreak(branchHeight);

                            drawBox(branchX, yPos, branchWidth - 3, branchHeight, [248, 250, 252]);
                            pdf.setDrawColor(...colors.border);
                            pdf.rect(branchX, yPos, branchWidth - 3, branchHeight, 'S');

                            pdf.setFontSize(branchFit.fontSize);
                            branchFit.lines.forEach((line, idx) => {
                                pdf.text(line, branchX + 2, yPos + 3 + idx * branchFit.lineHeight);
                            });
                        }
                        yPos += 12;
                        break;

                    case 'key_point':
                    case 'process':
                        const points = Array.isArray(section.content) ? section.content : [section.content];
                        for (let i = 0; i < points.length; i++) {
                            // Auto-fit point text
                            const pointFit = autoFitTextBlock(points[i], contentWidth - 14, 10, 7);
                            const pointHeight = pointFit.lines.length * pointFit.lineHeight + 3;

                            checkPageBreak(pointHeight);

                            // Bullet
                            pdf.setFillColor(...themeColor);
                            pdf.circle(margin + 2, yPos + 2, 1.2, 'F');

                            // All text lines
                            pdf.setFontSize(pointFit.fontSize);
                            pointFit.lines.forEach((line, idx) => {
                                pdf.text(line, margin + 8, yPos + idx * pointFit.lineHeight);
                            });
                            yPos += pointHeight;
                        }
                        break;

                    case 'table':
                        if (section.content?.headers && section.content?.rows) {
                            const headers = section.content.headers;
                            const rows = section.content.rows;
                            const numCols = headers.length;

                            // Calculate column widths - minimum 25mm, evenly distributed
                            const minColWidth = 25;
                            const tableWidth = contentWidth - 4; // 2mm padding on each side
                            const colWidth = Math.max(minColWidth, tableWidth / numCols);
                            const actualTableWidth = Math.min(tableWidth, colWidth * numCols);

                            // Helper: Auto-size text to fit in cell
                            // Returns { fontSize, lines, lineHeight }
                            const autoFitText = (text, maxWidth, maxFontSize = 8, minFontSize = 5) => {
                                const cellText = String(text || '');
                                let fontSize = maxFontSize;
                                let lines;
                                let lineHeight;

                                while (fontSize >= minFontSize) {
                                    pdf.setFontSize(fontSize);
                                    lineHeight = fontSize * 0.4; // ~40% of font size for line height
                                    lines = pdf.splitTextToSize(cellText, maxWidth);

                                    // If text fits in a reasonable number of lines (max 6), accept it
                                    if (lines.length <= 6) {
                                        return { fontSize, lines, lineHeight };
                                    }
                                    fontSize -= 0.5;
                                }

                                // Use minimum font size if still doesn't fit
                                pdf.setFontSize(minFontSize);
                                lineHeight = minFontSize * 0.4;
                                lines = pdf.splitTextToSize(cellText, maxWidth);
                                return { fontSize: minFontSize, lines, lineHeight };
                            };

                            // Calculate header row with auto-fitting
                            let headerHeight = 8;
                            const fittedHeaders = headers.map(h => {
                                const fit = autoFitText(h, colWidth - 4, 8, 6);
                                const cellHeight = fit.lines.length * fit.lineHeight + 4;
                                headerHeight = Math.max(headerHeight, cellHeight);
                                return fit;
                            });

                            checkPageBreak(headerHeight + 10);

                            // Draw header background
                            drawBox(margin, yPos, actualTableWidth, headerHeight, [248, 250, 252]);
                            pdf.setDrawColor(...colors.border);
                            pdf.rect(margin, yPos, actualTableWidth, headerHeight, 'S');

                            // Draw header text with fitted fonts
                            pdf.setFont('helvetica', 'bold');
                            fittedHeaders.forEach((fit, i) => {
                                pdf.setFontSize(fit.fontSize);
                                fit.lines.forEach((line, lineIdx) => {
                                    pdf.text(line, margin + i * colWidth + 2, yPos + 3.5 + lineIdx * fit.lineHeight);
                                });
                                // Draw vertical separator
                                if (i < numCols - 1) {
                                    pdf.line(margin + (i + 1) * colWidth, yPos, margin + (i + 1) * colWidth, yPos + headerHeight);
                                }
                            });
                            yPos += headerHeight;

                            // Data rows with auto-fitting
                            pdf.setFont('helvetica', 'normal');
                            for (const row of rows) {
                                // Auto-fit each cell
                                let rowHeight = 6;
                                const fittedCells = row.map((cell, i) => {
                                    const fit = autoFitText(cell, colWidth - 4, 8, 5);
                                    const cellHeight = fit.lines.length * fit.lineHeight + 3;
                                    rowHeight = Math.max(rowHeight, cellHeight);
                                    return fit;
                                });

                                checkPageBreak(rowHeight);

                                // Draw bottom border
                                pdf.setDrawColor(...colors.border);
                                pdf.line(margin, yPos + rowHeight, margin + actualTableWidth, yPos + rowHeight);

                                // Draw cell content with individual font sizes
                                fittedCells.forEach((fit, i) => {
                                    pdf.setFontSize(fit.fontSize);
                                    fit.lines.forEach((line, lineIdx) => {
                                        pdf.text(line, margin + i * colWidth + 2, yPos + 3 + lineIdx * fit.lineHeight);
                                    });
                                    // Draw vertical separator
                                    if (i < numCols - 1) {
                                        pdf.line(margin + (i + 1) * colWidth, yPos, margin + (i + 1) * colWidth, yPos + rowHeight);
                                    }
                                });

                                yPos += rowHeight;
                            }
                        }
                        yPos += 8;
                        break;

                    default:
                        // Plain text
                        const textContent = String(section.content || '');
                        const textLines = pdf.splitTextToSize(textContent, contentWidth);
                        for (const line of textLines) {
                            checkPageBreak(6);
                            pdf.text(line, margin, yPos);
                            yPos += 5;
                        }
                        break;
                }

                yPos += 8; // Space between sections
            }
        }

        // Save PDF - Content remains visible (no hiding)
        const filename = `${data.title || 'infographic'}-${orientation}.pdf`.replace(/[^a-zA-Z0-9-_.]/g, '_');
        pdf.save(filename);

    } catch (err) {
        console.error("PDF Export failed:", err);
        alert("Failed to export PDF: " + err.message);
    } finally {
        if (downloadBtn) {
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<span class="material-symbols-rounded">download</span>';
            document.body.style.cursor = 'default';
        }
    }
}

/* Knowledge Base / Library System with Chapters and Rename */
const LIBRARY_KEY = 'ophthalmic_infographic_library';
const CHAPTERS_KEY = 'ophthalmic_infographic_chapters';

// Default ophthalmic chapters
const DEFAULT_CHAPTERS = [
    { id: 'uncategorized', name: 'Uncategorized', color: '#64748b' },
    { id: 'clinical_skills', name: 'Clinical Skills', color: '#3b82f6' },
    { id: 'investigations', name: 'Investigations & Interpretation', color: '#10b981' },
    { id: 'trauma', name: 'Ocular Trauma', color: '#ef4444' },
    { id: 'lids', name: 'Lids', color: '#f59e0b' },
    { id: 'lacrimal', name: 'Lacrimal', color: '#6366f1' },
    { id: 'conjunctiva', name: 'Conjunctiva', color: '#8b5cf6' },
    { id: 'cornea', name: 'Cornea', color: '#ec4899' },
    { id: 'sclera', name: 'Sclera', color: '#06b6d4' },
    { id: 'lens', name: 'Lens', color: '#14b8a6' },
    { id: 'glaucoma', name: 'Glaucoma', color: '#22c55e' },
    { id: 'uveitis', name: 'Uveitis', color: '#eab308' },
    { id: 'vitreoretinal', name: 'Vitreoretinal', color: '#f97316' },
    { id: 'medical_retina', name: 'Medical Retina', color: '#f43f5e' },
    { id: 'orbit', name: 'Orbit', color: '#a855f7' },
    { id: 'tumours', name: 'Intraocular Tumours', color: '#d946ef' },
    { id: 'neuro', name: 'Neuro-ophthalmology', color: '#0ea5e9' },
    { id: 'strabismus', name: 'Strabismus', color: '#84cc16' },
    { id: 'paediatric', name: 'Paediatric Ophthalmology', color: '#fbbf24' },
    { id: 'refractive', name: 'Refractive Ophthalmology', color: '#f472b6' },
    { id: 'aids', name: 'Aids to Diagnosis', color: '#fb7185' },
    { id: 'vision_context', name: 'Vision in Context', color: '#38bdf8' },
    { id: 'surgery_care', name: 'Surgery: Anaesthetics & Care', color: '#4ade80' },
    { id: 'theatre', name: 'Surgery: Theatre Notes', color: '#2dd4bf' },
    { id: 'lasers', name: 'Lasers', color: '#f87171' },
    { id: 'therapeutics', name: 'Therapeutics', color: '#c084fc' },
    { id: 'evidence', name: 'Evidence-based Ophthalmology', color: '#94a3b8' },
    { id: 'resources', name: 'Resources', color: '#64748b' }
];

/* Safe Fetch Wrapper to handle file:// protocol and GitHub Pages */
const SERVER_URL = 'http://localhost:3000';
const GITHUB_PAGES_HOST = 'genododi.github.io';

function isGitHubPages() {
    return window.location.hostname === GITHUB_PAGES_HOST;
}

async function safeFetch(url, options) {
    if (window.location.protocol === 'file:') {
        // Point to localhost server if running locally
        const fullUrl = url.startsWith('http') ? url : `${SERVER_URL}/${url}`;
        return fetch(fullUrl, options);
    }
    return fetch(url, options);
}

// Fetch library from static JSON file (for GitHub Pages)
async function fetchLibraryFromStatic() {
    try {
        // Try fetching the pre-generated library index
        const response = await fetch('library-index.json');
        if (response.ok) {
            return await response.json();
        }

        // Fallback: try fetching individual files from Library folder listing
        // This won't work on GitHub Pages without a proper index, so return empty
        return [];
    } catch (err) {
        console.log('Could not fetch static library index:', err.message);
        return null; // Return null on error to distinguish from empty library
    }
}

function getChapters() {
    // Strict Mode: Always return DEFAULT_CHAPTERS to prevent duplicates/legacy chapters
    // We ignore localStorage 'ophthalmic_infographic_chapters' to clean up
    return DEFAULT_CHAPTERS;
}

// Helper: Reassign Sequential IDs 
// Newest item = HIGHEST number (library.length), Oldest = 1
// Called after any addition or deletion to ensure no gaps or duplicates
function reassignSequentialIds(library) {
    if (!library || library.length === 0) return false;

    // Sort by date ASCENDING (oldest first gets #1)
    const sortedByDate = [...library].sort((a, b) => new Date(a.date) - new Date(b.date));

    let modified = false;
    const totalCount = library.length;

    // Assign sequential numbers: oldest = 1, newest = totalCount
    sortedByDate.forEach((sortedItem, index) => {
        const newSeqId = index + 1; // oldest gets 1, newest gets totalCount
        // Find the original item in library and update its seqId
        const originalItem = library.find(item => item.id === sortedItem.id);
        if (originalItem && originalItem.seqId !== newSeqId) {
            originalItem.seqId = newSeqId;
            modified = true;
        }
    });

    return modified;
}

// Legacy function - now calls reassignSequentialIds for full reordering
function assignSequentialIds(library) {
    return reassignSequentialIds(library);
}

// Auto-chapterize: Detect chapter from title keywords
// Organized by clinical ophthalmology subspecialties with comprehensive terminology
function autoDetectChapter(title) {
    if (!title) return 'uncategorized';

    const titleLower = title.toLowerCase();

    // CLINICAL OPHTHALMOLOGY AUTO-CATEGORIZATION RULES
    // Order matters: more specific conditions first, then broader categories
    // Based on standard ophthalmology subspecialty organization
    const rules = [
        // ══════════════════════════════════════════════════════════════════
        // NEURO-OPHTHALMOLOGY - Disorders of visual pathway & cranial nerves
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Optic nerve conditions
                'optic neuritis', 'optic neuropathy', 'optic atrophy', 'papilledema', 'papilloedema',
                'disc swelling', 'disc edema', 'disc oedema', 'aion', 'naion', 'pion', 'lhon',
                'ischaemic optic', 'ischemic optic', 'optic nerve head', 'optic disc drusen',
                // Cranial nerve palsies
                'third nerve', 'fourth nerve', 'sixth nerve', 'cn iii', 'cn iv', 'cn vi',
                'oculomotor', 'trochlear', 'abducens', 'cranial nerve pals',
                // Pupil disorders
                'anisocoria', 'pupil', 'horner', 'adie', 'argyll robertson', 'rapd', 'apd',
                'relative afferent', 'marcus gunn',
                // Visual pathway
                'chiasm', 'optic tract', 'optic radiation', 'visual cortex', 'hemianop',
                'quadrantanop', 'bitemporal', 'homonymous',
                // Nystagmus & eye movements
                'nystagmus', 'gaze palsy', 'ino', 'internuclear', 'one-and-a-half',
                'supranuclear', 'infranuclear', 'saccad',
                // Intracranial conditions
                'iih', 'pseudotumor', 'benign intracranial', 'idiopathic intracranial',
                'raised icp', 'intracranial pressure', 'pituitary', 'sellar',
                // General neuro-ophth
                'neuro-ophth', 'neuroophth', 'visual pathway', 'afferent', 'efferent'
            ], chapter: 'neuro'
        },

        // ══════════════════════════════════════════════════════════════════
        // GLAUCOMA - IOP-related optic neuropathy & angle disorders
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Types of glaucoma
                'glaucoma', 'poag', 'pacg', 'primary open angle', 'primary angle closure',
                'normal tension', 'ntg', 'low tension', 'ocular hypertension', 'oht',
                'secondary glaucoma', 'neovascular glaucoma', 'nvg', 'uveitic glaucoma',
                'pigmentary glaucoma', 'pigment dispersion', 'pseudoexfoliation', 'pxf', 'pex',
                'exfoliation syndrome', 'steroid-induced', 'traumatic glaucoma',
                'congenital glaucoma', 'juvenile glaucoma', 'developmental glaucoma',
                'angle recession glaucoma', 'inflammatory glaucoma', 'lens-induced',
                // IOP & anatomy
                'intraocular pressure', 'iop', 'aqueous', 'trabecular meshwork',
                'schlemm', 'angle closure', 'narrow angle', 'plateau iris',
                'pupillary block', 'appositional', 'synechial',
                // Glaucoma surgery
                'trabeculectomy', 'tube shunt', 'ahmed', 'baerveldt', 'molteno',
                'migs', 'istent', 'hydrus', 'xen', 'preserflo', 'goniotomy',
                'trabeculotomy', 'trabectome', 'kahook', 'gonioscopy-assisted',
                'cyclophotocoagulation', 'cyclodiode', 'filtering surgery', 'bleb',
                // Diagnostic
                'rnfl', 'ganglion cell', 'optic disc cupping', 'cup-to-disc', 'c:d ratio',
                'visual field loss', 'arcuate scotoma', 'nasal step'
            ], chapter: 'glaucoma'
        },

        // ══════════════════════════════════════════════════════════════════
        // VITREORETINAL - Surgical retina conditions
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Retinal detachment
                'retinal detachment', 'rd', 'rhegmatogenous', 'tractional', 'exudative',
                'macula-off', 'macula-on', 'pvr', 'proliferative vitreoretinopathy',
                // Vitreous conditions
                'vitreous', 'pvd', 'posterior vitreous', 'vitreous hemorrhage', 'vit haem',
                'vitreous opacities', 'floaters', 'asteroid hyalosis', 'synchysis',
                // Macular surgery
                'macular hole', 'epiretinal membrane', 'erm', 'macular pucker',
                'vitreomacular traction', 'vmt', 'lamellar hole',
                // Surgical procedures
                'vitrectomy', 'ppv', 'pars plana', 'scleral buckle', 'pneumatic retinopexy',
                'silicone oil', 'gas tamponade', 'sf6', 'c3f8', 'endolaser', 'cryotherapy',
                'internal limiting membrane', 'ilm peel',
                // Peripheral retina
                'retinal tear', 'retinal break', 'horseshoe tear', 'lattice degeneration',
                'retinoschisis', 'peripheral retinal', 'prophylactic laser'
            ], chapter: 'vitreoretinal'
        },

        // ══════════════════════════════════════════════════════════════════
        // MEDICAL RETINA - Non-surgical retinal conditions
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Diabetic eye disease
                'diabetic retinopathy', 'dr', 'npdr', 'pdr', 'proliferative diabetic',
                'non-proliferative', 'diabetic macular', 'dme', 'csme', 'clinically significant',
                'microaneurysm', 'hard exudate', 'cotton wool', 'irma', 'nve', 'nvd',
                // AMD
                'age-related macular', 'amd', 'armd', 'macular degeneration',
                'drusen', 'geographic atrophy', 'wet amd', 'dry amd', 'neovascular amd',
                'cnv', 'choroidal neovascul', 'polypoidal', 'pcv', 'rac', 'rpe detachment',
                // Vascular conditions
                'retinal vein occlusion', 'rvo', 'brvo', 'crvo', 'hemi-rvo',
                'retinal artery occlusion', 'rao', 'brao', 'crao', 'branch retinal',
                'central retinal', 'ocular ischemic', 'venous stasis',
                // Macular conditions
                'macular edema', 'cme', 'cystoid macular', 'irvine-gass',
                'central serous', 'csr', 'csc', 'cscr', 'pachychoroid',
                'myopic maculopathy', 'pathological myopia', 'macular atrophy',
                'epiretinal', 'macular dystrophy', 'vitelliform', 'best disease',
                'stargardt', 'pattern dystrophy',
                // Other medical retina
                'retinitis pigmentosa', 'rp', 'rod-cone', 'cone-rod', 'choroideremia',
                'retinal dystrophy', 'inherited retinal', 'ird',
                'hypertensive retinopathy', 'radiation retinopathy', 'solar retinopathy',
                'chloroquine', 'hydroxychloroquine', 'drug toxicity retina',
                // Anti-VEGF related
                'anti-vegf', 'intravitreal injection', 'aflibercept', 'ranibizumab',
                'bevacizumab', 'faricimab', 'brolucizumab'
            ], chapter: 'medical_retina'
        },

        // ══════════════════════════════════════════════════════════════════
        // CORNEA & EXTERNAL - Corneal conditions & ocular surface
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Infections
                'keratitis', 'corneal ulcer', 'microbial keratitis', 'bacterial keratitis',
                'fungal keratitis', 'acanthamoeba', 'herpetic keratitis', 'hsv keratitis',
                'herpes simplex', 'herpes zoster ophthalmicus', 'hzo', 'disciform',
                'dendrit', 'geographic ulcer',
                // Dystrophies
                'corneal dystrophy', 'fuchs', 'endothelial dystrophy', 'fced',
                'keratoconus', 'pellucid', 'ectasia', 'corneal ectasia',
                'lattice dystrophy', 'granular dystrophy', 'macular dystrophy',
                'map-dot-fingerprint', 'ebmd', 'reis-bucklers', 'thiel-behnke',
                'posterior polymorphous', 'congenital hereditary endothelial',
                // Degenerations
                'pterygium', 'pinguecula', 'band keratopathy', 'salzmann',
                'terrien', 'mooren', 'dellen', 'arcus senilis',
                // Dry eye & ocular surface
                'dry eye', 'ded', 'meibomian gland', 'mgd', 'blepharitis',
                'ocular surface disease', 'osd', 'tear film', 'schirmer',
                'tbut', 'tear break-up', 'sjogren', 'sicca', 'gvhd ocular',
                // Surgery
                'corneal transplant', 'keratoplasty', 'pk', 'penetrating keratoplasty',
                'dsaek', 'dsek', 'dmek', 'dalk', 'endothelial keratoplasty',
                'corneal graft', 'graft rejection', 'graft failure',
                'cross-linking', 'cxl', 'collagen cross', 'intacs', 'corneal ring',
                // Other corneal
                'corneal opacity', 'corneal scar', 'corneal edema', 'bullous keratopathy',
                'exposure keratopathy', 'neurotrophic', 'persistent epithelial defect',
                'recurrent erosion', 'epithelial basement membrane'
            ], chapter: 'cornea'
        },

        // ══════════════════════════════════════════════════════════════════
        // LENS & CATARACT
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Cataract types
                'cataract', 'nuclear sclerosis', 'cortical cataract', 'posterior subcapsular',
                'psc', 'mature cataract', 'hypermature', 'morgagnian', 'brunescent',
                'white cataract', 'intumescent', 'traumatic cataract', 'congenital cataract',
                'developmental cataract', 'metabolic cataract', 'drug-induced cataract',
                // Surgery
                'phacoemulsification', 'phaco', 'ecce', 'icce', 'sics', 'msics',
                'femtosecond', 'flacs', 'cataract surgery', 'cataract extraction',
                // IOL
                'intraocular lens', 'iol', 'monofocal', 'multifocal', 'toric',
                'edof', 'accommodating iol', 'iol calculation', 'biometry',
                'iol power', 'a-constant', 'srk', 'barrett', 'holladay', 'haigis',
                'piggyback iol', 'sulcus iol', 'secondary iol', 'scleral fixated',
                // Complications
                'posterior capsule opacification', 'pco', 'after-cataract',
                'nd:yag capsulotomy', 'yag capsulotomy', 'pcr', 'posterior capsule rupture',
                'vitreous loss', 'dropped nucleus', 'endophthalmitis', 'tass',
                'cme post cataract', 'iol dislocation', 'iol decentration',
                // Lens conditions
                'lens', 'crystalline lens', 'ectopia lentis', 'lens subluxation',
                'lens dislocation', 'marfan lens', 'homocystinuria', 'weill-marchesani',
                'microspherophakia', 'lenticonus', 'lentiglobus', 'aphakia', 'pseudophakia',
                'zonular weakness', 'zonulopathy'
            ], chapter: 'lens'
        },

        // ══════════════════════════════════════════════════════════════════
        // UVEITIS & OCULAR INFLAMMATION
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Anatomical classification
                'uveitis', 'iritis', 'iridocyclitis', 'anterior uveitis', 'aau',
                'intermediate uveitis', 'pars planitis', 'posterior uveitis',
                'panuveitis', 'choroiditis', 'chorioretinitis', 'retinochoroiditis',
                // Specific entities
                'hla-b27', 'ankylosing spondylitis', 'reactive arthritis', 'psoriatic',
                'inflammatory bowel', 'crohn', 'ulcerative colitis',
                'behcet', 'sarcoid', 'sarcoidosis', 'vogt-koyanagi-harada', 'vkh',
                'sympathetic ophthalmia', 'birdshot', 'multifocal choroiditis', 'mcp',
                'serpiginous', 'acute posterior multifocal', 'apmppe', 'mewds',
                'punctate inner choroidopathy', 'pic', 'white dot syndrome',
                // Infectious uveitis
                'toxoplasm', 'toxocara', 'cmv retinitis', 'cytomegalovirus',
                'herpes uveitis', 'arn', 'acute retinal necrosis', 'porn',
                'tuberculosis uveitis', 'tb uveitis', 'ocular tb', 'syphilitic uveitis',
                'endogenous endophthalmitis', 'fungal endophthalmitis',
                // Signs & complications
                'hypopyon', 'keratic precipitate', 'kp', 'mutton fat', 'stellate',
                'synechia', 'posterior synechia', 'peripheral anterior synechia',
                'iris bombe', 'seclusio pupillae', 'cyclitic membrane',
                'band keratopathy uveitis', 'uveitic glaucoma', 'uveitic cataract',
                // Treatment-related
                'immunosuppression', 'steroid-sparing', 'biologic', 'adalimumab', 'infliximab'
            ], chapter: 'uveitis'
        },

        // ══════════════════════════════════════════════════════════════════
        // STRABISMUS & OCULAR MOTILITY
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Types of strabismus
                'strabismus', 'squint', 'heterotropia', 'esotropia', 'exotropia',
                'hypertropia', 'hypotropia', 'infantile esotropia', 'accommodative',
                'non-accommodative', 'partially accommodative', 'sensory strabismus',
                'consecutive', 'divergence excess', 'convergence insufficiency',
                'convergence excess', 'divergence insufficiency',
                // Specific patterns
                'a-pattern', 'v-pattern', 'duane syndrome', 'duane retraction',
                'brown syndrome', 'superior oblique palsy', 'inferior oblique overaction',
                'double elevator palsy', 'monocular elevation deficiency',
                'congenital fibrosis', 'cfeom', 'mobius',
                // Motility & binocularity
                'ocular motility', 'eom', 'extraocular muscle', 'eye movement',
                'binocular vision', 'binocular single vision', 'bsv', 'diplopia',
                'suppression', 'anomalous correspondence', 'arc',
                // Amblyopia
                'amblyopia', 'lazy eye', 'anisometropic', 'strabismic amblyopia',
                'deprivation amblyopia', 'occlusion therapy', 'penalization',
                // Assessment & surgery
                'cover test', 'prism cover', 'hirschberg', 'krimsky',
                'hess chart', 'lancaster', 'diplopia chart',
                'strabismus surgery', 'recession', 'resection', 'transposition',
                'adjustable suture', 'botulinum strabismus'
            ], chapter: 'strabismus'
        },

        // ══════════════════════════════════════════════════════════════════
        // PAEDIATRIC OPHTHALMOLOGY
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // General paediatric
                'paediatric', 'pediatric', 'child', 'children', 'infant', 'neonatal',
                'congenital', 'developmental', 'hereditary eye',
                // ROP
                'retinopathy of prematurity', 'rop', 'zone i', 'zone ii', 'plus disease',
                'threshold rop', 'pre-threshold', 'aggressive rop', 'arop',
                // Congenital conditions
                'congenital cataract', 'congenital glaucoma', 'buphthalmos',
                'persistent fetal vasculature', 'pfv', 'phpv', 'coloboma',
                'aniridia', 'peters anomaly', 'axenfeld-rieger', 'anterior segment dysgenesis',
                // Childhood conditions
                'leukocoria', 'white pupil', 'red reflex', 'bruckner',
                'nasolacrimal duct obstruction', 'nldo', 'dacryocele', 'congenital dacryocystocele',
                'childhood blindness', 'cortical visual impairment', 'cvi',
                // Genetic/metabolic
                'retinoblastoma', 'coats disease', 'norrie', 'familial exudative',
                'fevr', 'incontinentia pigmenti', 'albinism ocular'
            ], chapter: 'paediatric'
        },

        // ══════════════════════════════════════════════════════════════════
        // ORBIT & OCULOPLASTICS - ORBIT
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Thyroid eye disease
                'thyroid eye disease', 'ted', 'graves ophthalmopathy', 'graves orbitopathy',
                'dysthyroid', 'thyroid-associated', 'tao', 'exophthalmos', 'proptosis',
                'lid retraction thyroid', 'compressive optic neuropathy', 'con',
                'orbital decompression',
                // Orbital inflammation
                'orbital cellulitis', 'preseptal cellulitis', 'postseptal',
                'orbital abscess', 'subperiosteal abscess', 'cavernous sinus thrombosis',
                'idiopathic orbital inflammation', 'orbital pseudotumor', 'tolosa-hunt',
                'igg4-related', 'dacryoadenitis', 'myositis orbital',
                // Orbital tumors
                'orbital tumor', 'orbital mass', 'lacrimal gland tumor',
                'cavernous hemangioma', 'lymphangioma', 'dermoid', 'orbital dermoid',
                'optic nerve glioma', 'optic nerve meningioma', 'orbital meningioma',
                'rhabdomyosarcoma', 'orbital lymphoma', 'orbital metastasis',
                // Trauma & other
                'orbital fracture', 'blow-out fracture', 'medial wall fracture',
                'floor fracture', 'enophthalmos', 'orbital reconstruction',
                'orbital hemorrhage', 'retrobulbar hemorrhage',
                'orbit', 'orbital anatomy', 'extraocular muscle anatomy'
            ], chapter: 'orbit'
        },

        // ══════════════════════════════════════════════════════════════════
        // OCULOPLASTICS - LIDS
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Lid position
                'ptosis', 'blepharoptosis', 'congenital ptosis', 'aponeurotic ptosis',
                'myogenic ptosis', 'neurogenic ptosis', 'mechanical ptosis',
                'ectropion', 'entropion', 'cicatricial ectropion', 'involutional',
                'paralytic ectropion', 'spastic entropion',
                'lid retraction', 'lagophthalmos', 'exposure keratopathy lid',
                // Lid tumors
                'eyelid tumor', 'lid tumor', 'basal cell carcinoma', 'bcc',
                'squamous cell carcinoma eyelid', 'sebaceous carcinoma',
                'meibomian gland carcinoma', 'merkel cell', 'eyelid melanoma',
                'chalazion', 'hordeolum', 'stye', 'lid cyst', 'dermoid cyst lid',
                'papilloma lid', 'xanthelasma', 'syringoma',
                // Inflammation
                'blepharitis', 'anterior blepharitis', 'posterior blepharitis',
                'meibomian gland dysfunction', 'mgd', 'rosacea ocular',
                'demodex', 'preseptal', 'lid margin disease',
                // Structural
                'trichiasis', 'distichiasis', 'madarosis', 'epicanthus',
                'telecanthus', 'blepharophimosis', 'coloboma lid', 'ankyloblepharon',
                'floppy eyelid syndrome', 'dermatochalasis',
                // Surgery
                'blepharoplasty', 'ptosis surgery', 'levator', 'muller muscle',
                'frontalis sling', 'tarsal strip', 'lid reconstruction',
                'mohs', 'hughes flap', 'cutler-beard', 'lid sharing',
                'botulinum toxin lid', 'facial palsy', 'bell palsy eye'
            ], chapter: 'lids'
        },

        // ══════════════════════════════════════════════════════════════════
        // LACRIMAL SYSTEM
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                'lacrimal', 'tear duct', 'nasolacrimal', 'nldo',
                'dacryocystitis', 'dacryocystocele', 'dacryoadenitis',
                'epiphora', 'watery eye', 'tearing', 'lacrimation',
                'punctal stenosis', 'punctum', 'canalicular', 'canaliculitis',
                'dcr', 'dacryocystorhinostomy', 'endonasal dcr', 'external dcr',
                'jones tube', 'lacrimal stent', 'intubation lacrimal',
                'lacrimal gland', 'lacrimal sac', 'lacrimal drainage',
                'dry eye lacrimal', 'tear production', 'reflex tearing'
            ], chapter: 'lacrimal'
        },

        // ══════════════════════════════════════════════════════════════════
        // CONJUNCTIVA
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                'conjunctivitis', 'red eye', 'pink eye', 'viral conjunctivitis',
                'bacterial conjunctivitis', 'allergic conjunctivitis',
                'vernal keratoconjunctivitis', 'vkc', 'atopic keratoconjunctivitis', 'akc',
                'giant papillary', 'gpc', 'seasonal allergic', 'perennial allergic',
                'chlamydial', 'trachoma', 'ophthalmia neonatorum', 'gonococcal',
                'adenoviral', 'epidemic keratoconjunctivitis', 'ekc',
                'subconjunctival hemorrhage', 'chemosis', 'follicles', 'papillae',
                'pinguecula', 'conjunctival degeneration',
                'ocular cicatricial pemphigoid', 'ocp', 'mucous membrane pemphigoid',
                'stevens-johnson syndrome', 'sjs', 'toxic epidermal', 'ten',
                'symblepharon', 'fornix shortening', 'conjunctival scarring',
                'conjunctival tumor', 'ocular surface squamous', 'ossn', 'cin',
                'conjunctival melanoma', 'conjunctival nevus', 'pan'
            ], chapter: 'conjunctiva'
        },

        // ══════════════════════════════════════════════════════════════════
        // SCLERA
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                'scleritis', 'episcleritis', 'anterior scleritis', 'posterior scleritis',
                'nodular scleritis', 'necrotizing scleritis', 'scleromalacia',
                'diffuse scleritis', 'scleral inflammation',
                'blue sclera', 'scleral thinning', 'staphyloma',
                'scleral buckle complication', 'scleral perforation'
            ], chapter: 'sclera'
        },

        // ══════════════════════════════════════════════════════════════════
        // REFRACTIVE SURGERY & ERRORS
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Refractive errors
                'refractive error', 'refraction', 'ametropia',
                'myopia', 'short-sighted', 'near-sighted', 'high myopia', 'pathological myopia',
                'hyperopia', 'hypermetropia', 'long-sighted', 'far-sighted',
                'astigmatism', 'regular astigmatism', 'irregular astigmatism',
                'anisometropia', 'aniseikonia', 'presbyopia',
                // Refractive surgery
                'lasik', 'lasek', 'prk', 'photorefractive', 'smile', 'relex',
                'femtosecond laser refractive', 'excimer', 'refractive surgery',
                'enhancement', 'retreatment', 'regression',
                'icl', 'phakic iol', 'implantable collamer', 'artisan', 'artiflex',
                'refractive lens exchange', 'rle', 'clear lens extraction',
                // Complications
                'ectasia post-lasik', 'dry eye post-lasik', 'flap complication',
                'epithelial ingrowth', 'interface inflammation', 'dlk',
                // Assessment
                'wavefront', 'aberrometry', 'topography', 'tomography',
                'keratometry', 'corneal power', 'axial length', 'biometry',
                'spectacle', 'glasses', 'contact lens'
            ], chapter: 'refractive'
        },

        // ══════════════════════════════════════════════════════════════════
        // OCULAR TRAUMA
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                'ocular trauma', 'eye injury', 'eye trauma',
                'open globe', 'ruptured globe', 'penetrating injury', 'perforating injury',
                'closed globe', 'blunt trauma', 'contusion',
                'foreign body', 'iofb', 'intraocular foreign body', 'corneal foreign body',
                'hyphema', 'traumatic hyphema', 'eight ball hyphema',
                'chemical burn', 'chemical injury', 'alkali burn', 'acid burn',
                'thermal burn', 'radiation injury',
                'commotio retinae', 'berlin edema', 'choroidal rupture',
                'traumatic cataract', 'lens dislocation trauma', 'iridodialysis',
                'cyclodialysis', 'angle recession', 'vitreous hemorrhage trauma',
                'traumatic optic neuropathy', 'retinal detachment trauma',
                'siderosis', 'chalcosis', 'sympathetic ophthalmia trauma'
            ], chapter: 'trauma'
        },

        // ══════════════════════════════════════════════════════════════════
        // OCULAR TUMORS
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Intraocular tumors
                'uveal melanoma', 'choroidal melanoma', 'iris melanoma', 'ciliary body melanoma',
                'choroidal nevus', 'iris nevus', 'choroidal metastasis', 'ocular metastasis',
                'retinoblastoma', 'choroidal hemangioma', 'retinal hemangioblastoma',
                'intraocular lymphoma', 'vitreoretinal lymphoma',
                'melanocytoma', 'adenoma', 'medulloepithelioma',
                // Treatments
                'plaque brachytherapy', 'proton beam', 'gamma knife', 'stereotactic',
                'transpupillary thermotherapy', 'ttt', 'photodynamic tumor',
                'enucleation', 'evisceration', 'exenteration', 'orbital implant',
                // General
                'ocular tumor', 'intraocular tumor', 'eye cancer', 'ocular oncology'
            ], chapter: 'tumours'
        },

        // ══════════════════════════════════════════════════════════════════
        // OPHTHALMIC SURGERY & ANAESTHESIA
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Anaesthesia
                'ophthalmic anaesthesia', 'ocular anesthesia', 'local anaesthetic',
                'topical anaesthesia', 'sub-tenon', 'subtenon', 'peribulbar',
                'retrobulbar', 'block', 'orbital block',
                'general anaesthesia eye', 'sedation eye',
                // Surgical principles
                'surgical technique', 'intraoperative', 'perioperative',
                'post-operative', 'postoperative', 'complication',
                'surgical complication', 'informed consent',
                'ophthalmic instruments', 'microsurgery', 'operating microscope',
                // Specific mentions
                'theatre', 'operating room', 'aseptic technique', 'sterile'
            ], chapter: 'surgery_care'
        },

        // ══════════════════════════════════════════════════════════════════
        // OPHTHALMIC LASERS
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                'laser', 'argon laser', 'yag laser', 'nd:yag',
                'diode laser', 'green laser', 'micropulse',
                'photocoagulation', 'panretinal photocoagulation', 'prp',
                'focal laser', 'grid laser', 'macular laser',
                'laser trabeculoplasty', 'slt', 'alt', 'selective laser',
                'peripheral iridotomy', 'pi', 'laser iridotomy',
                'yag capsulotomy', 'posterior capsulotomy',
                'photodynamic therapy', 'pdt', 'verteporfin',
                'laser retinopexy', 'barrage laser'
            ], chapter: 'lasers'
        },

        // ══════════════════════════════════════════════════════════════════
        // OCULAR PHARMACOLOGY & THERAPEUTICS
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Drug delivery
                'eye drop', 'topical', 'intravitreal', 'subconjunctival',
                'intracameral', 'periocular', 'sustained release', 'implant',
                // Anti-infectives
                'antibiotic eye', 'antifungal eye', 'antiviral eye',
                'fluoroquinolone', 'aminoglycoside', 'chloramphenicol',
                'acyclovir', 'ganciclovir', 'valganciclovir',
                // Anti-inflammatories
                'corticosteroid', 'prednisolone', 'dexamethasone',
                'fluorometholone', 'loteprednol', 'difluprednate',
                'nsaid eye', 'ketorolac', 'nepafenac', 'bromfenac',
                // Glaucoma medications
                'prostaglandin analogue', 'latanoprost', 'travoprost', 'bimatoprost',
                'beta-blocker eye', 'timolol', 'betaxolol',
                'alpha-agonist', 'brimonidine', 'apraclonidine',
                'carbonic anhydrase inhibitor', 'dorzolamide', 'brinzolamide',
                'acetazolamide', 'rho kinase', 'netarsudil',
                // Other
                'cycloplegic', 'mydriatic', 'miotic', 'pilocarpine',
                'atropine', 'cyclopentolate', 'tropicamide', 'phenylephrine',
                'artificial tears', 'lubricant', 'preservative-free',
                'anti-vegf', 'vegf inhibitor', 'ranibizumab', 'aflibercept',
                'bevacizumab', 'faricimab', 'ozurdex', 'iluvien',
                'pharmacology', 'drug interaction', 'adverse effect', 'toxicity'
            ], chapter: 'therapeutics'
        },

        // ══════════════════════════════════════════════════════════════════
        // CLINICAL EXAMINATION SKILLS
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // History & examination
                'history taking', 'clinical examination', 'ocular examination',
                'systematic examination', 'ophthalmic assessment',
                // Visual assessment
                'visual acuity', 'snellen', 'logmar', 'etdrs', 'pinhole',
                'near vision', 'reading addition', 'contrast sensitivity',
                'colour vision', 'ishihara', 'farnsworth',
                // Anterior segment
                'slit lamp', 'biomicroscopy', 'anterior segment examination',
                'external examination', 'lid examination',
                // Posterior segment
                'fundoscopy', 'ophthalmoscopy', 'direct ophthalmoscopy',
                'indirect ophthalmoscopy', 'fundus examination', 'dilated examination',
                '90d', '78d', 'volk lens', 'panfundoscope',
                // IOP
                'tonometry', 'goldmann tonometry', 'applanation', 'icare',
                'tonopen', 'non-contact tonometry',
                // Gonioscopy
                'gonioscopy', 'angle examination', 'shaffer', 'spaeth',
                // Other
                'confrontation field', 'amsler grid', 'red desaturation',
                'swinging flashlight', 'cover test examination'
            ], chapter: 'clinical_skills'
        },

        // ══════════════════════════════════════════════════════════════════
        // OPHTHALMIC INVESTIGATIONS
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                // Imaging
                'oct', 'optical coherence tomography', 'oct-a', 'octa',
                'angiography', 'ffa', 'fluorescein angiography', 'fa',
                'icg', 'indocyanine green', 'fundus autofluorescence', 'faf',
                'fundus photography', 'colour fundus', 'red-free',
                'ultrasound eye', 'b-scan', 'a-scan', 'ubm', 'ultrasound biomicroscopy',
                'ct orbit', 'mri orbit', 'neuroimaging',
                // Corneal assessment
                'topography', 'tomography', 'pentacam', 'orbscan', 'galilei',
                'scheimpflug', 'placido', 'keratometry', 'pachymetry',
                'specular microscopy', 'endothelial cell count',
                // Visual field
                'perimetry', 'visual field', 'humphrey', 'octopus', 'goldmann perimetry',
                'automated perimetry', 'kinetic perimetry', 'esterman',
                // Electrophysiology
                'electrophysiology', 'erg', 'electroretinogram', 'full-field erg',
                'pattern erg', 'multifocal erg', 'vep', 'visual evoked potential',
                'eog', 'electro-oculogram',
                // Biometry
                'biometry', 'iol master', 'lenstar', 'axial length measurement',
                // Other
                'exophthalmometry', 'hertel', 'tear osmolarity', 'meibography'
            ], chapter: 'investigations'
        },

        // ══════════════════════════════════════════════════════════════════
        // EVIDENCE-BASED OPHTHALMOLOGY
        // ══════════════════════════════════════════════════════════════════
        {
            keywords: [
                'clinical trial', 'randomized controlled', 'rct', 'evidence-based',
                'systematic review', 'meta-analysis', 'cochrane',
                'guideline', 'nice guideline', 'aao preferred practice',
                'drcr', 'catt trial', 'comparison trial', 'areds', 'areds2',
                'emgt', 'ohts', 'agis', 'cigts', 'cntgs',
                'etdrs', 'drs', 'ukpds', 'dcct', 'field study',
                'marina', 'anchor', 'view', 'rise', 'ride', 'vivid', 'vista',
                'hawk', 'harrier', 'tenaya', 'lucerne'
            ], chapter: 'evidence'
        },
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

// Auto-Sync to Server Logic
// Track if we've already shown the GitHub Pages message
let _gitHubPagesMessageShown = false;

async function syncLibraryToServer() {
    // Skip sync on GitHub Pages (static hosting, no backend)
    if (isGitHubPages()) {
        // Only log once per session to avoid console spam
        if (!_gitHubPagesMessageShown) {
            console.log("GitHub Pages detected - server sync disabled (expected behavior for static hosting)");
            _gitHubPagesMessageShown = true;
        }
        return;
    }

    if (window.location.protocol === 'file:') {
        // Try to sync anyway via localhost API
    }
    const libraryData = localStorage.getItem(LIBRARY_KEY) || '[]';
    console.log("Syncing library to server...");
    try {
        const response = await safeFetch('api/library/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: libraryData
        });
        if (response.ok) {
            console.log("Library synced to server successfully.");
        } else {
            console.error("Failed to sync library:", response.statusText);
        }
    } catch (err) {
        console.error("Error syncing library:", err);
    }
}

function setupKnowledgeBase() {
    const saveBtn = document.getElementById('save-btn');
    const libraryBtn = document.getElementById('library-btn');
    const libraryBtnEmpty = document.getElementById('library-btn-empty');
    const modal = document.getElementById('library-modal');
    const closeBtn = document.getElementById('close-modal-btn');
    const listContainer = document.getElementById('saved-items-list');
    const importBtn = document.getElementById('import-server-btn');
    const exportBtn = document.getElementById('export-server-btn');
    const emptyMsg = document.getElementById('empty-library-msg');

    let currentChapterFilter = 'all';
    let currentSearchTerm = ''; // NEW: Search state
    let currentSortMode = 'date'; // NEW: Sort state
    let selectionMode = false;
    let selectedItems = new Set();

    // Toggle Export Button
    function updateExportButtonVisibility() {
        if (exportBtn) {
            exportBtn.style.display = (selectionMode && selectedItems.size > 0) ? 'block' : 'none';
        }
    }

    // EXPORT TO SERVER (or Community Pool for remote users)
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            // Check removed to allow attempt
            if (selectedItems.size === 0) return;

            const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');
            const itemsToExport = library.filter(item => selectedItems.has(item.id));

            // REMOTE USER: Redirect to Community Pool instead of server
            // No limit on number of items - users can submit as many as they want
            if (isGitHubPages()) {
                const itemWord = itemsToExport.length === 1 ? 'infographic' : 'infographics';
                if (!confirm(`You are accessing remotely. ${itemsToExport.length} ${itemWord} will be submitted to the Community Pool for admin review. Continue?`)) return;

                const originalIcon = exportBtn.innerHTML;
                exportBtn.innerHTML = '<span class="material-symbols-rounded">sync</span>';

                try {
                    // Prompt for username
                    const savedUsername = localStorage.getItem('community_username') || '';
                    const userName = prompt('Enter your name for the submissions:', savedUsername);

                    if (!userName || !userName.trim()) {
                        alert('A name is required for community submissions.');
                        return;
                    }

                    localStorage.setItem('community_username', userName.trim());

                    // Submit each item to community pool
                    let successCount = 0;
                    let failCount = 0;

                    for (const item of itemsToExport) {
                        try {
                            const result = await CommunitySubmissions.submit(item.data || item, userName.trim());
                            if (result.success) {
                                successCount++;
                            } else {
                                failCount++;
                                console.error('Failed to submit:', item.title, result.message);
                            }
                        } catch (err) {
                            failCount++;
                            console.error('Error submitting:', item.title, err);
                        }
                    }

                    if (successCount > 0) {
                        const msg = failCount > 0
                            ? `✅ ${successCount} submitted successfully.\n❌ ${failCount} failed.`
                            : `✅ ${successCount} ${successCount === 1 ? 'infographic' : 'infographics'} submitted successfully!`;
                        alert(msg + '\n\nThe admin will review your submissions.');
                        selectionMode = false;
                        selectedItems.clear();
                        renderLibraryList();
                    } else {
                        alert('All submissions failed. Please try again.');
                    }
                } catch (err) {
                    console.error('Community submission error:', err);
                    alert('Error submitting to community pool: ' + err.message);
                } finally {
                    exportBtn.innerHTML = originalIcon;
                }
                return;
            }

            // LOCAL SERVER: Original behavior
            if (!confirm(`Export ${selectedItems.size} selected items to the server knowledge base?`)) return;

            const originalIcon = exportBtn.innerHTML;
            exportBtn.innerHTML = '<span class="material-symbols-rounded">sync</span>';

            try {
                const response = await safeFetch('api/library/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(itemsToExport)
                });

                if (response.ok) {
                    alert('Export successful!');
                    selectionMode = false;
                    selectedItems.clear();
                    renderLibraryList();
                } else {
                    alert('Failed to export to server.');
                }
            } catch (err) {
                console.error('Export error:', err);
                alert('Error connecting to server.');
            } finally {
                exportBtn.innerHTML = originalIcon;
            }
        });
    }

    // REFACTORED: Unified Sync Function
    async function syncFromServer(silent = false) {
        if (window.location.protocol === 'file:') {
            console.log("Running in file:// mode. Attempting to connect to localhost server...");
        }

        const originalIcon = importBtn ? importBtn.innerHTML : '';
        if (importBtn) importBtn.innerHTML = '<span class="material-symbols-rounded">sync</span>';

        try {
            let serverItems = [];
            let communityApproved = [];

            // GitHub Pages: Use static JSON file instead of API
            if (isGitHubPages()) {
                console.log("Running on GitHub Pages. Fetching from static library index...");
                serverItems = await fetchLibraryFromStatic();

                // Safety Check: If serverItems is null, it means fetch failed (network error or file missing).
                // Do NOT proceed with sync or deletion to avoid wiping data accidentally.
                if (serverItems === null) {
                    console.error("Failed to fetch library index. Aborting sync.");
                    if (!silent) alert("Could not fetch library from server. Sync aborted to protect local data.");
                    return;
                }

                if (serverItems.length === 0 && !silent) {
                    console.log("Static library index is empty.");
                }

                // Also fetch approved community submissions (the cloud pool)
                try {
                    if (typeof CommunitySubmissions !== 'undefined' && CommunitySubmissions.isConfigured()) {
                        console.log("Fetching approved community submissions...");
                        const communityData = await CommunitySubmissions.getAll();
                        communityApproved = communityData.approved || [];
                        if (communityApproved.length > 0) {
                            console.log(`Found ${communityApproved.length} approved community infographics.`);
                        }
                    }
                } catch (communityErr) {
                    console.log("Could not fetch community submissions:", communityErr.message);
                }
            } else {
                // Local/Server mode: Use API
                const response = await safeFetch('api/library/list');
                if (response.ok) {
                    serverItems = await response.json();
                } else {
                    throw new Error('API response not ok');
                }
            }

            // Merge community approved items into serverItems for unified processing
            // Convert community format to library format
            communityApproved.forEach(submission => {
                if (submission.data) {
                    const libraryItem = {
                        id: submission.id || Date.now(),
                        title: submission.title || submission.data.title || 'Community Infographic',
                        summary: submission.summary || submission.data.summary || '',
                        date: submission.approvedAt || submission.submittedAt || new Date().toISOString(),
                        data: submission.data,
                        chapterId: submission.chapterId || 'uncategorized',
                        communitySource: true, // Mark as from community
                        author: submission.userName
                    };
                    serverItems.push(libraryItem);
                }
            });

            if (serverItems.length > 0 || isGitHubPages()) {
                let localLibrary = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');
                let addedCount = 0;
                let updatedCount = 0;
                let skippedDuplicates = 0;
                let deletedCount = 0;
                const skippedTitles = [];
                const deletedTitles = [];

                // 1. AUTO-DELETE: Check for items that were on server (synced) but are now missing
                // This means the Admin deleted them from the server, so we must remove them locally.
                if (serverItems.length > 0) { // Only run if we have a valid server list
                    const serverIdMap = new Set(serverItems.map(i => String(i.id)));
                    const originalLength = localLibrary.length;

                    localLibrary = localLibrary.filter(item => {
                        // Only check items that CAME from server (marked as synced)
                        // User-created local items (not synced) are preserved
                        if (item._serverSynced) {
                            // If item ID is NOT in the new server list, it was deleted by Admin
                            if (item.id && !serverIdMap.has(String(item.id))) {
                                console.log(`[Auto-Delete] Removing "${item.title}" because it was deleted from server.`);
                                deletedTitles.push(item.title);
                                return false; // Delete it
                            }
                        }
                        return true; // Keep it
                    });

                    const autoDeleteCount = originalLength - localLibrary.length;
                    deletedCount += autoDeleteCount;
                }

                // 2. ADMIN DELETION SYNC (Community Tracking): Check for explicitly tracked deletions
                // Remote users will have these items removed from their library
                try {
                    if (typeof CommunitySubmissions !== 'undefined' && CommunitySubmissions.getDeletedItems) {
                        const deletedItems = await CommunitySubmissions.getDeletedItems();
                        if (deletedItems && deletedItems.length > 0) {
                            const normalizeTitle = (t) => (t || '').toLowerCase().trim().replace(/[^a-z0-9]/g, '');
                            const originalLength = localLibrary.length;

                            localLibrary = localLibrary.filter(item => {
                                const normTitle = normalizeTitle(item.title);
                                if (deletedItems.includes(normTitle)) {
                                    deletedTitles.push(item.title?.substring(0, 30) || 'Unknown');
                                    return false; // Remove this item
                                }
                                return true; // Keep this item
                            });

                            deletedCount = originalLength - localLibrary.length;
                            if (deletedCount > 0) {
                                console.log(`[Sync] Removed ${deletedCount} item(s) deleted by admin.`);
                                localStorage.setItem(LIBRARY_KEY, JSON.stringify(localLibrary));
                            }
                        }
                    }
                } catch (err) {
                    console.log('Could not check for admin deletions:', err.message);
                }

                // Create a map of local items for faster lookup (by ID)
                const localMap = new Map();
                localLibrary.forEach(item => {
                    // Use ID if available, otherwise fallback to title+date as key (legacy support)
                    const key = item.id || (item.title + item.date);
                    localMap.set(String(key), item);
                });

                // DUPLICATE PREVENTION: Build a normalized title index for ALL local items
                // This prevents importing ANY item with a duplicate title
                const normalizeTitle = (t) => (t || '').toLowerCase().trim().replace(/[^a-z0-9]/g, '');
                const localTitleIndex = new Set();
                localLibrary.forEach(item => {
                    const normTitle = normalizeTitle(item.title);
                    if (normTitle.length > 0) {
                        localTitleIndex.add(normTitle);
                    }
                });

                // Track what changed for detailed logging
                const updateDetails = [];

                // Helper function to normalize strings for comparison
                // Aggressive normalization to prevent false positives
                const normalizeStr = (str) => {
                    if (!str) return '';
                    return String(str)
                        .trim()
                        .normalize('NFC')
                        .replace(/\s+/g, ' ')  // Collapse multiple spaces
                        .replace(/[\u200B-\u200D\uFEFF]/g, ''); // Remove zero-width chars
                };

                serverItems.forEach(serverItem => {
                    const serverKey = String(serverItem.id || (serverItem.title + serverItem.date));

                    if (localMap.has(serverKey)) {
                        // Item exists locally. Check if we need to update.
                        // We assume Server is the "Truth" for synchronization when fetching.
                        const localItem = localMap.get(serverKey);

                        // Check for REAL differences that matter
                        const changes = [];

                        // CHAPTER SYNC: Server is source of truth for chapters
                        // BUT: We never revert a categorized item to 'uncategorized'
                        const localChapter = normalizeStr(localItem.chapterId) || 'uncategorized';
                        let serverChapter = normalizeStr(serverItem.chapterId) || 'uncategorized';

                        // If server is uncategorized but local ALREADY has a category, preserve the local one
                        if (serverChapter === 'uncategorized' && localChapter !== 'uncategorized') {
                            serverChapter = localChapter;
                            serverItem.chapterId = localItem.chapterId;
                        } else if (serverChapter === 'uncategorized' && localChapter === 'uncategorized') {
                            // Both are uncategorized, try auto-detecting from title
                            const autoChapter = autoDetectChapter(serverItem.title || localItem.title);
                            if (autoChapter !== 'uncategorized') {
                                serverChapter = autoChapter;
                                serverItem.chapterId = autoChapter;
                            }
                        }

                        if (localChapter !== serverChapter) {
                            const chapters = getChapters();
                            const oldChapterName = chapters.find(c => c.id === localChapter)?.name || localChapter;
                            const newChapterName = chapters.find(c => c.id === serverChapter)?.name || serverChapter;
                            changes.push(`chapter: ${oldChapterName} → ${newChapterName}`);
                            localItem.chapterId = serverItem.chapterId;
                            // Mark as recently updated for visual feedback
                            localItem._chapterUpdated = Date.now();
                        }

                        // For title/summary: Only update if item has a "lastServerSync" marker older than server
                        // OR if this is first sync. Skip title/summary comparison to avoid false positives.
                        // Trust that server title is correct - update once and mark as synced
                        if (!localItem._serverSynced) {
                            // First time syncing this item - accept server values
                            if (localItem.title !== serverItem.title) {
                                localItem.title = serverItem.title;
                            }
                            if (localItem.summary !== serverItem.summary) {
                                localItem.summary = serverItem.summary;
                            }
                            localItem.data = serverItem.data;
                            localItem._serverSynced = true;
                        }

                        // Preserve local seqId if it exists, otherwise use server's or generate new
                        if (!localItem.seqId && serverItem.seqId) localItem.seqId = serverItem.seqId;

                        if (changes.length > 0) {
                            updatedCount++;
                            updateDetails.push({ title: serverItem.title?.substring(0, 30), changes });
                        }
                    } else {
                        // New Item from Server - CHECK FOR DUPLICATES FIRST
                        // Use pre-built title index for fast duplicate detection
                        const serverTitleNorm = normalizeTitle(serverItem.title);

                        // Check if this title already exists in local library
                        const isDuplicate = serverTitleNorm.length > 0 && localTitleIndex.has(serverTitleNorm);

                        if (isDuplicate) {
                            // Skip this item - it's a duplicate
                            skippedDuplicates++;
                            skippedTitles.push(serverItem.title?.substring(0, 30) || 'Untitled');
                            console.log(`[Sync] Skipping duplicate: "${serverItem.title}"`);
                        } else {
                            // Not a duplicate - safe to add
                            // CRITICAL: Strip the server's seqId so we assign a new LOCAL one
                            const newItem = { ...serverItem };
                            delete newItem.seqId;

                            // PRESERVE CHAPTER: Keep the server's chapterId if available
                            // Auto-detect chapter if not set
                            if (!newItem.chapterId || newItem.chapterId === 'uncategorized') {
                                const autoChapter = autoDetectChapter(newItem.title);
                                newItem.chapterId = autoChapter;
                            }

                            // Mark as newly imported for green hashtag display
                            newItem._newlyImported = Date.now();

                            localLibrary.push(newItem);
                            addedCount++;

                            // Add to title index to prevent duplicates within same sync batch
                            if (serverTitleNorm.length > 0) {
                                localTitleIndex.add(serverTitleNorm);
                            }
                        }
                    }
                });

                if (addedCount > 0 || updatedCount > 0 || assignSequentialIds(localLibrary)) {
                    // Sort by date desc
                    localLibrary.sort((a, b) => new Date(b.date) - new Date(a.date));
                    localStorage.setItem(LIBRARY_KEY, JSON.stringify(localLibrary));
                    renderLibraryList();
                    if (!silent) {
                        const msg = [];
                        if (addedCount) msg.push(`${addedCount} new`);
                        if (updatedCount) msg.push(`${updatedCount} updated`);
                        if (deletedCount) msg.push(`${deletedCount} removed (admin deleted)`);
                        if (skippedDuplicates) msg.push(`${skippedDuplicates} skipped (duplicates)`);

                        // Build detailed message showing what was updated
                        let detailMsg = `Sync Complete: ${msg.join(', ')}.`;

                        if (updateDetails.length > 0) {
                            detailMsg += '\n\nUpdated items:';
                            updateDetails.slice(0, 10).forEach(item => {
                                detailMsg += `\n• ${item.title}... (${item.changes.join(', ')})`;
                            });
                            if (updateDetails.length > 10) {
                                detailMsg += `\n...and ${updateDetails.length - 10} more`;
                            }
                        }

                        if (deletedTitles.length > 0) {
                            detailMsg += '\n\nRemoved by admin:';
                            deletedTitles.slice(0, 5).forEach(title => {
                                detailMsg += `\n• ${title}...`;
                            });
                            if (deletedTitles.length > 5) {
                                detailMsg += `\n...and ${deletedTitles.length - 5} more`;
                            }
                        }

                        if (skippedTitles.length > 0) {
                            detailMsg += '\n\nSkipped duplicates:';
                            skippedTitles.slice(0, 5).forEach(title => {
                                detailMsg += `\n• ${title}...`;
                            });
                            if (skippedTitles.length > 5) {
                                detailMsg += `\n...and ${skippedTitles.length - 5} more`;
                            }
                        }

                        alert(detailMsg);
                    }

                    // Detailed logging for debugging
                    console.log(`Auto-Sync: Imported ${addedCount}, Updated ${updatedCount}, Skipped ${skippedDuplicates} duplicates.`);
                    if (updateDetails.length > 0) {
                        console.log('Updated items:');
                        updateDetails.forEach(item => {
                            console.log(`  • "${item.title}..." - ${item.changes.join(', ')}`);
                        });
                    }
                    if (skippedTitles.length > 0) {
                        console.log('Skipped duplicates:');
                        skippedTitles.forEach(title => {
                            console.log(`  • "${title}..." (already in library)`);
                        });
                    }
                } else if (skippedDuplicates > 0) {
                    // Only duplicates were found, nothing new to add
                    if (!silent) {
                        let msg = `Sync Complete: ${skippedDuplicates} item(s) skipped (already in library).`;
                        if (skippedTitles.length > 0) {
                            msg += '\n\nSkipped duplicates:';
                            skippedTitles.slice(0, 5).forEach(title => {
                                msg += `\n• ${title}...`;
                            });
                            if (skippedTitles.length > 5) {
                                msg += `\n...and ${skippedTitles.length - 5} more`;
                            }
                        }
                        alert(msg);
                    }
                    console.log(`Auto-Sync: Skipped ${skippedDuplicates} duplicates (already in library).`);
                } else {
                    if (!silent) alert('Library is up to date.');
                    console.log("Auto-Sync: Library is up to date (no changes needed).");
                }

                // BIDIRECTIONAL SYNC: Upload local-only items to server
                // Also upload items that are newer locally? 
                // For now, let's just upload items that don't exist on server.
                // Re-read server items to be sure (or just use the list we got)
                const serverIdMap = new Set(serverItems.map(i => String(i.id || (i.title + i.date))));

                const localOnlyItems = localLibrary.filter(localItem =>
                    !serverIdMap.has(String(localItem.id || (localItem.title + localItem.date)))
                );

                // Also identify items that exist but might be newer locally? 
                // That requires "Last Modified" timestamp which we don't have reliably yet.
                // So we only push NEW items. Updates MUST be triggered manually by "Save" or "Rename" pushing.

                // BIDIRECTIONAL SYNC: Only for non-GitHub Pages (requires backend)
                if (!isGitHubPages() && localOnlyItems.length > 0) {
                    try {
                        await safeFetch('api/library/upload', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(localOnlyItems)
                        });
                        console.log(`Bidirectional Sync: Uploaded ${localOnlyItems.length} local-only items to server.`);
                    } catch (uploadErr) {
                        console.log('Bidirectional Sync: Could not upload local items:', uploadErr.message);
                    }
                }
            }
        } catch (err) {
            if (!silent) {
                console.error('Import error:', err);
                if (!isGitHubPages()) {
                    alert('Error connecting to server.');
                }
            } else {
                console.log("Auto-Sync: Could not connect to server (backend likely offline or running on static hosting).");
            }
        } finally {
            if (importBtn) importBtn.innerHTML = originalIcon;
        }
    }

    // Sync Button Logic
    const syncBtn = document.getElementById('sync-btn');

    // SILENT DUPLICATE CLEANUP ON STARTUP
    // This removes any existing duplicates from localStorage without showing alerts
    (function silentDuplicateCleanup() {
        try {
            const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');
            if (library.length === 0) return;

            const normalizeTitle = (t) => (t || '').toLowerCase().trim().replace(/[^a-z0-9]/g, '');
            const seenTitles = new Map(); // normalized title -> index of first occurrence
            const indicesToRemove = new Set();

            // Find duplicates (keep the OLDER one based on date)
            library.forEach((item, index) => {
                const normTitle = normalizeTitle(item.title);
                if (normTitle.length === 0) return;

                if (seenTitles.has(normTitle)) {
                    // Duplicate found - compare dates to keep the older one
                    const existingIndex = seenTitles.get(normTitle);
                    const existingDate = new Date(library[existingIndex].date);
                    const currentDate = new Date(item.date);

                    if (currentDate < existingDate) {
                        // Current is older, we are keeping 'item' (index) and removing library[existingIndex]
                        // Transfer category if keeping uncategorized but removing categorized
                        if ((!library[index].chapterId || library[index].chapterId === 'uncategorized') &&
                            (library[existingIndex].chapterId && library[existingIndex].chapterId !== 'uncategorized')) {
                            library[index].chapterId = library[existingIndex].chapterId;
                        }
                        indicesToRemove.add(existingIndex);
                        seenTitles.set(normTitle, index);
                    } else {
                        // Existing is older, we are keeping library[existingIndex] and removing 'item' (index)
                        // Transfer category if keeping uncategorized but removing categorized
                        if ((!library[existingIndex].chapterId || library[existingIndex].chapterId === 'uncategorized') &&
                            (item.chapterId && item.chapterId !== 'uncategorized')) {
                            library[existingIndex].chapterId = item.chapterId;
                        }
                        indicesToRemove.add(index);
                    }
                } else {
                    seenTitles.set(normTitle, index);
                }
            });

            if (indicesToRemove.size > 0) {
                // Remove duplicates
                const cleanedLibrary = library.filter((_, index) => !indicesToRemove.has(index));

                // Reassign sequential IDs
                reassignSequentialIds(cleanedLibrary);

                localStorage.setItem(LIBRARY_KEY, JSON.stringify(cleanedLibrary));
                console.log(`[Startup] Silently removed ${indicesToRemove.size} duplicate(s) from library.`);
            }
        } catch (err) {
            console.error('[Startup] Duplicate cleanup error:', err);
        }
    })();

    // AUTO-SYNC ON STARTUP
    setTimeout(() => {
        syncFromServer(true); // Run silently
    }, 1000); // Small delay to ensure UI is ready

    // Sync Button Click Listener
    if (syncBtn) {
        syncBtn.addEventListener('click', () => {
            syncBtn.classList.add('rotating');
            syncFromServer(false).finally(() => {
                syncBtn.classList.remove('rotating');
            });
        });
    }

    // IMPORT BUTTON HANDLER
    if (importBtn) {
        importBtn.addEventListener('click', async () => {
            if (!confirm('Import saved infographics from the server? This will add any missing items.')) return;
            await syncFromServer(false);
        });
    }

    // FIND DUPLICATES
    const findDuplicatesBtn = document.getElementById('find-duplicates-btn');
    if (findDuplicatesBtn) {
        findDuplicatesBtn.addEventListener('click', () => {
            const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');

            if (library.length === 0) {
                alert('Library is empty. No duplicates to find.');
                return;
            }

            // Normalize title for comparison
            const normalizeTitle = (title) => {
                if (!title) return '';
                return String(title).trim().toLowerCase().normalize('NFC');
            };

            // Find duplicates by title
            const titleMap = new Map();
            const duplicates = [];

            library.forEach((item, index) => {
                const normalizedTitle = normalizeTitle(item.title);

                if (titleMap.has(normalizedTitle)) {
                    // Found a duplicate
                    const originalIndex = titleMap.get(normalizedTitle);
                    duplicates.push({
                        title: item.title,
                        duplicateId: item.id,
                        duplicateIndex: index,
                        originalId: library[originalIndex].id,
                        originalIndex: originalIndex,
                        duplicateDate: item.date,
                        originalDate: library[originalIndex].date
                    });
                } else {
                    titleMap.set(normalizedTitle, index);
                }
            });

            if (duplicates.length === 0) {
                alert('✅ No duplicates found! Your library is clean.');
                return;
            }

            // Build message showing duplicates
            let msg = `Found ${duplicates.length} duplicate(s):\n\n`;
            duplicates.forEach((dup, i) => {
                const dupDate = new Date(dup.duplicateDate).toLocaleDateString();
                const origDate = new Date(dup.originalDate).toLocaleDateString();
                msg += `${i + 1}. "${dup.title}"\n   - Original: ${origDate}\n   - Duplicate: ${dupDate}\n\n`;
            });
            msg += `\nDelete all ${duplicates.length} duplicate(s)? (Keeps the older/original version)`;

            if (confirm(msg)) {
                // Admin password required for bulk delete
                const password = prompt('Enter admin password to delete duplicates:');
                if (password !== '309030') {
                    if (password !== null) {
                        alert('Incorrect password. Deletion requires admin access.');
                    }
                    return;
                }

                // Get IDs to delete (the newer duplicates)
                const idsToDelete = new Set(duplicates.map(d => d.duplicateId));

                // Transfer categories before deleting
                duplicates.forEach(dup => {
                    const originalItem = library[dup.originalIndex];
                    const duplicateItem = library[dup.duplicateIndex];

                    // If original is uncategorized but duplicate is categorized, transfer the category
                    if ((!originalItem.chapterId || originalItem.chapterId === 'uncategorized') &&
                        (duplicateItem.chapterId && duplicateItem.chapterId !== 'uncategorized')) {
                        originalItem.chapterId = duplicateItem.chapterId;
                    }
                });

                // Filter out duplicates
                const cleanedLibrary = library.filter(item => !idsToDelete.has(item.id));

                // Reassign sequential IDs
                reassignSequentialIds(cleanedLibrary);

                // Save
                localStorage.setItem(LIBRARY_KEY, JSON.stringify(cleanedLibrary));

                alert(`✅ Deleted ${duplicates.length} duplicate(s). Library now has ${cleanedLibrary.length} items.`);

                // Refresh the library view
                renderLibraryList();

                // Sync to server
                syncLibraryToServer();
            }
        });
    }

    // AUTO-CHAPTERIZE
    const autoChapterBtn = document.getElementById('auto-chapter-btn');
    if (autoChapterBtn) {
        autoChapterBtn.addEventListener('click', () => {
            // Admin password required
            const password = prompt('Enter admin password to auto-chapterize:');
            if (password !== '309030') {
                if (password !== null) {
                    alert('Incorrect password. Auto-chapterization requires admin access.');
                }
                return;
            }

            const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');

            if (library.length === 0) {
                alert('Library is empty. Nothing to chapterize.');
                return;
            }

            let changedCount = 0;
            const changes = [];

            library.forEach(item => {
                // Only auto-chapterize if currently uncategorized
                if (item.chapterId === 'uncategorized' || !item.chapterId) {
                    const detectedChapter = autoDetectChapter(item.title);
                    if (detectedChapter !== 'uncategorized') {
                        const oldChapter = item.chapterId || 'uncategorized';
                        item.chapterId = detectedChapter;
                        changedCount++;

                        // Get chapter name for display
                        const chapterObj = DEFAULT_CHAPTERS.find(c => c.id === detectedChapter);
                        changes.push({
                            title: item.title.substring(0, 40),
                            chapter: chapterObj ? chapterObj.name : detectedChapter
                        });
                    }
                }
            });

            if (changedCount === 0) {
                alert('✅ All items are already categorized or no matches found.');
                return;
            }

            // Build summary message
            let msg = `Auto-chapterized ${changedCount} item(s):\n\n`;
            changes.slice(0, 15).forEach((c, i) => {
                msg += `${i + 1}. "${c.title}..." → ${c.chapter}\n`;
            });
            if (changes.length > 15) {
                msg += `\n...and ${changes.length - 15} more`;
            }
            msg += '\n\nApply these changes?';

            if (confirm(msg)) {
                localStorage.setItem(LIBRARY_KEY, JSON.stringify(library));
                alert(`✅ ${changedCount} item(s) auto-chapterized!`);
                renderLibraryList();
                syncLibraryToServer();
            }
        });
    }


    // COMPARING WITH SERVER
    const diffBtn = document.getElementById('diff-btn');
    if (diffBtn) {
        diffBtn.addEventListener('click', async () => {
            const originalIcon = diffBtn.innerHTML;
            diffBtn.innerHTML = '<span class="material-symbols-rounded" style="animation: spin 1s linear infinite;">sync</span>';
            // Add spin style if not exists
            if (!document.getElementById('spin-style')) {
                const style = document.createElement('style');
                style.id = 'spin-style';
                style.innerHTML = '@keyframes spin { 100% { -webkit-transform: rotate(360deg); transform:rotate(360deg); } }';
                document.head.appendChild(style);
            }

            try {
                // Fetch server items
                let serverItems = [];
                if (isGitHubPages()) {
                    serverItems = await fetchLibraryFromStatic();
                } else {
                    const response = await safeFetch('api/library/list');
                    if (response.ok) serverItems = await response.json();
                }

                const localLibrary = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');

                // Normalization helper
                const normalize = (t) => (t || '').toLowerCase().trim().replace(/[^a-z0-9]/g, '');

                // Index by Normalized Title for "Identity" comparison (since IDs might differ if re-imported)
                const localMap = new Map();
                localLibrary.forEach(i => localMap.set(normalize(i.title), i));

                const serverMap = new Map();
                serverItems.forEach(i => serverMap.set(normalize(i.title), i));

                const onlyLocal = [];
                const onlyServer = [];
                const different = [];

                // Check Local against Server
                localLibrary.forEach(local => {
                    const normTitle = normalize(local.title);
                    if (!serverMap.has(normTitle)) {
                        onlyLocal.push(local.title);
                    } else {
                        // Exists on both - check for differences
                        const server = serverMap.get(normTitle);
                        // Compare Chapters
                        if ((local.chapterId || 'uncategorized') !== (server.chapterId || 'uncategorized')) {
                            different.push(`${local.title} (Local: ${local.chapterId || 'None'} / Server: ${server.chapterId || 'None'})`);
                        }
                    }
                });

                // Check Server against Local
                serverItems.forEach(server => {
                    const normTitle = normalize(server.title);
                    if (!localMap.has(normTitle)) {
                        onlyServer.push(server.title);
                    }
                });

                let msg = `📊 Library Sync Status\n\n`;
                let totalDiff = onlyLocal.length + onlyServer.length + different.length;

                if (totalDiff === 0) {
                    msg += "✅ Perfectly Synced! Libraries are identical.";
                } else {
                    if (onlyLocal.length > 0) {
                        msg += `🏠 On Local Only (${onlyLocal.length}):\n`;
                        msg += onlyLocal.slice(0, 5).map(t => `  • ${t}`).join('\n');
                        if (onlyLocal.length > 5) msg += `\n  ...and ${onlyLocal.length - 5} more`;
                        msg += "\n\n";
                    }

                    if (onlyServer.length > 0) {
                        msg += `☁️ On Server Only (${onlyServer.length}):\n`;
                        msg += onlyServer.slice(0, 5).map(t => `  • ${t}`).join('\n');
                        if (onlyServer.length > 5) msg += `\n  ...and ${onlyServer.length - 5} more`;
                        msg += "\n\n";
                    }

                    if (different.length > 0) {
                        msg += `⚠️ Mismatches (${different.length}):\n`;
                        msg += different.slice(0, 5).map(d => `  • ${d}`).join('\n');
                        if (different.length > 5) msg += `\n  ...and ${different.length - 5} more`;
                    }
                }

                alert(msg);

            } catch (err) {
                console.error('Diff error:', err);
                alert('Error comparing libraries: ' + err.message);
            } finally {
                diffBtn.innerHTML = originalIcon;
            }
        });
    }

    // SAVE
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            if (!currentInfographicData) {
                alert("Only generated infographics can be saved.");
                return;
            }

            const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');

            // Auto-detect chapter from title
            const itemTitle = currentInfographicData.title || "Untitled Infographic";
            const autoChapter = autoDetectChapter(itemTitle);

            const newItem = {
                id: Date.now(),
                seqId: 1, // Will be reassigned below
                title: itemTitle,
                summary: currentInfographicData.summary || "",
                date: new Date().toISOString(),
                data: currentInfographicData,
                chapterId: autoChapter // Auto-assigned based on title keywords
            };

            library.unshift(newItem);

            // Reassign all sequential IDs (oldest = 1, newest = highest)
            reassignSequentialIds(library);

            localStorage.setItem(LIBRARY_KEY, JSON.stringify(library));

            // Auto-upload to server so it saves to the library/ folder
            safeFetch('api/library/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify([newItem])
            }).then(() => {
                console.log('Saved to server library folder.');
            }).catch(err => {
                console.log('Server sync skipped (server offline):', err.message);
            });

            const originalIcon = saveBtn.innerHTML;
            saveBtn.innerHTML = '<span class="material-symbols-rounded">check</span>';
            setTimeout(() => {
                saveBtn.innerHTML = originalIcon;
            }, 2000);
        });
    }

    // OPEN LIBRARY
    const openLibrary = () => {
        renderLibraryList();
        modal.classList.add('active');
    };

    if (libraryBtn) {
        libraryBtn.addEventListener('click', openLibrary);
    }

    if (libraryBtnEmpty) {
        libraryBtnEmpty.addEventListener('click', openLibrary);
    }

    // Sidebar library button (below text entry)
    const sidebarLibraryBtn = document.getElementById('sidebar-library-btn');
    if (sidebarLibraryBtn) {
        sidebarLibraryBtn.addEventListener('click', openLibrary);
    }

    // CLOSE LIBRARY
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
            selectionMode = false;
            selectedItems.clear();
        });
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
                selectionMode = false;
                selectedItems.clear();
            }
        });
    }

    function renderLibraryList() {
        const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');

        // Ensure IDs are assigned (Migration check)
        if (assignSequentialIds(library)) {
            localStorage.setItem(LIBRARY_KEY, JSON.stringify(library));
        }

        // Update count badge
        const countBadge = document.getElementById('library-count-badge');
        if (countBadge) {
            countBadge.textContent = library.length;
            countBadge.style.display = library.length > 0 ? 'inline-block' : 'none';
        }

        // Detect uncategorized infographics
        const uncategorizedCount = library.filter(item => !item.chapterId || item.chapterId === 'uncategorized').length;
        let uncategorizedBanner = modal.querySelector('.uncategorized-banner');

        if (uncategorizedCount > 0 && library.length > 0) {
            if (!uncategorizedBanner) {
                uncategorizedBanner = document.createElement('div');
                uncategorizedBanner.className = 'uncategorized-banner';
                const modalHeader = modal.querySelector('.modal-header');
                if (modalHeader && modalHeader.nextSibling) {
                    modalHeader.parentNode.insertBefore(uncategorizedBanner, modalHeader.nextSibling);
                }
            }
            uncategorizedBanner.innerHTML = `
                <span class="material-symbols-rounded">category</span>
                <span><strong>${uncategorizedCount}</strong> infographic${uncategorizedCount > 1 ? 's' : ''} uncategorized</span>
                <button class="btn-small btn-categorize-all" style="margin-left: auto;">
                    <span class="material-symbols-rounded">auto_awesome</span>
                    Auto-Categorize
                </button>
            `;
            uncategorizedBanner.style.display = 'flex';

            // Add click handler for auto-categorize button
            const categorizeBtn = uncategorizedBanner.querySelector('.btn-categorize-all');
            if (categorizeBtn) {
                categorizeBtn.onclick = () => {
                    const autoChapterBtn = document.getElementById('auto-chapter-btn');
                    if (autoChapterBtn) {
                        autoChapterBtn.click();
                    }
                };
            }
        } else if (uncategorizedBanner) {
            uncategorizedBanner.style.display = 'none';
        }

        const chapters = getChapters();

        // 1. Filter by Chapter
        let filteredLibrary = currentChapterFilter === 'all'
            ? library
            : library.filter(item => item.chapterId === currentChapterFilter);

        // 2. Filter by Search Term
        if (currentSearchTerm) {
            const term = currentSearchTerm.toLowerCase();
            filteredLibrary = filteredLibrary.filter(item =>
                (item.title || '').toLowerCase().includes(term) ||
                (item.summary || '').toLowerCase().includes(term)
            );
        }

        // 3. Apply Sorting
        if (currentSortMode === 'date') {
            filteredLibrary.sort((a, b) => new Date(b.date) - new Date(a.date));
        } else if (currentSortMode === 'name') {
            filteredLibrary.sort((a, b) => {
                const nameA = (a.title || '').toLowerCase();
                const nameB = (b.title || '').toLowerCase();
                return nameA.localeCompare(nameB);
            });
        } else if (currentSortMode === 'chapter') {
            const chapterOrder = new Map(chapters.map((ch, idx) => [ch.id, idx]));
            filteredLibrary.sort((a, b) => {
                const idxA = chapterOrder.get(a.chapterId) ?? 999;
                const idxB = chapterOrder.get(b.chapterId) ?? 999;
                if (idxA !== idxB) return idxA - idxB;
                // Secondary sort by date
                return new Date(b.date) - new Date(a.date);
            });
        } else if (currentSortMode === 'newly_added') {
            // Sort by _newlyImported timestamp (most recent first), then by date
            filteredLibrary.sort((a, b) => {
                const aNew = a._newlyImported || 0;
                const bNew = b._newlyImported || 0;
                if (aNew !== bNew) return bNew - aNew; // Newly imported first
                return new Date(b.date) - new Date(a.date); // Then by date
            });
        }

        // Build chapter filter tabs
        const modalBody = modal.querySelector('.modal-body');

        // Check if chapter tabs exist, if not create them
        let chapterTabs = modal.querySelector('.chapter-tabs');
        if (!chapterTabs) {
            chapterTabs = document.createElement('div');
            chapterTabs.className = 'chapter-tabs';
            modalBody.insertBefore(chapterTabs, listContainer);
        }

        // Render chapter tabs
        chapterTabs.innerHTML = `
            <button class="chapter-tab ${currentChapterFilter === 'all' ? 'active' : ''}" data-chapter="all">
                All
            </button>
            ${chapters.map(ch => `
                <button class="chapter-tab ${currentChapterFilter === ch.id ? 'active' : ''}" 
                        data-chapter="${ch.id}" 
                        style="--chapter-color: ${ch.color}">
                    ${ch.name}
                </button>
            `).join('')}
        `;

        // Chapter tab click handlers
        chapterTabs.querySelectorAll('.chapter-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                currentChapterFilter = tab.dataset.chapter;
                renderLibraryList();
            });
        });

        // Selection toolbar & Search Bar
        let toolbar = modal.querySelector('.selection-toolbar');
        if (!toolbar) {
            toolbar = document.createElement('div');
            toolbar.className = 'selection-toolbar';
            modalBody.insertBefore(toolbar, listContainer);
        }

        toolbar.innerHTML = `
            <div class="toolbar-row" style="display: flex; gap: 10px; width: 100%; margin-bottom: 10px;">
                <div class="search-wrapper" style="flex: 1; position: relative;">
                    <span class="material-symbols-rounded" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: 1.2rem;">search</span>
                    <input type="text" id="library-search" placeholder="Search saved infographics..." value="${currentSearchTerm}" 
                        style="width: 100%; padding: 8px 10px 8px 35px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem;">
                </div>
                <div class="sort-wrapper">
                    <select id="sort-select" style="padding: 8px 10px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; background-color: white; cursor: pointer;">
                        <option value="date" ${currentSortMode === 'date' ? 'selected' : ''}>Sort by Date</option>
                        <option value="name" ${currentSortMode === 'name' ? 'selected' : ''}>Sort by Name</option>
                        <option value="chapter" ${currentSortMode === 'chapter' ? 'selected' : ''}>Sort by Chapter</option>
                        <option value="newly_added" ${currentSortMode === 'newly_added' ? 'selected' : ''}>Sort by Newly Added</option>
                    </select>
                </div>
            </div>
            <div class="toolbar-row" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <button class="btn-small ${selectionMode ? 'btn-active' : ''}" id="toggle-selection-btn">
                    <span class="material-symbols-rounded">checklist</span>
                    ${selectionMode ? 'Cancel Selection' : 'Select Items'}
                </button>
                ${selectionMode ? `
                    <button class="btn-small" id="select-all-btn">
                        <span class="material-symbols-rounded">select_all</span>
                        Select All
                    </button>
                ` : ''}
                ${selectionMode && selectedItems.size > 0 ? `
                    <button class="btn-small btn-delete-selected" id="delete-selected-btn" style="background-color: #fee2e2; color: #ef4444; border-color: #fca5a5;">
                        <span class="material-symbols-rounded">delete</span>
                        Delete Selected (${selectedItems.size})
                    </button>
                    <select id="assign-chapter-select" class="chapter-select">
                        <option value="">Assign to Chapter...</option>
                        ${chapters.map(ch => `<option value="${ch.id}">${ch.name}</option>`).join('')}
                    </select>
                ` : ''}
            </div>
        `;

        // Search Handler
        const searchInput = toolbar.querySelector('#library-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                currentSearchTerm = e.target.value;
                renderLibraryList();
                // Restore focus after re-render (since re-render wipes DOM)
                const newInput = modal.querySelector('#library-search');
                if (newInput) {
                    newInput.focus();
                    newInput.setSelectionRange(newInput.value.length, newInput.value.length);
                }
            });
        }

        // Sort Handler
        const sortSelect = toolbar.querySelector('#sort-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                currentSortMode = e.target.value;
                renderLibraryList();
            });
        }

        // Toggle selection mode
        toolbar.querySelector('#toggle-selection-btn').addEventListener('click', () => {
            selectionMode = !selectionMode;
            selectedItems.clear();
            renderLibraryList();
            updateExportButtonVisibility();
        });

        // Select All Handler
        const selectAllBtn = toolbar.querySelector('#select-all-btn');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                filteredLibrary.forEach(item => selectedItems.add(item.id));
                renderLibraryList();
                updateExportButtonVisibility();
            });
        }

        // Initial Listeners consolidated items

        // DELETE SELECTED HANDLER
        const deleteSelectedBtn = toolbar.querySelector('#delete-selected-btn');
        if (deleteSelectedBtn) {
            deleteSelectedBtn.addEventListener('click', async () => {
                const password = prompt('Enter admin password to delete selected items:');
                if (password !== '309030') {
                    if (password !== null) alert('Incorrect password.');
                    return;
                }

                if (!confirm(`Are you sure you want to PERMANENTLY delete ${selectedItems.size} items?`)) return;

                const idsToDelete = Array.from(selectedItems);

                // 1. Delete from Server (if connected)
                try {
                    const response = await safeFetch('api/library/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ids: idsToDelete })
                    });
                    const result = await response.json();
                    if (!result.success) {
                        console.error('Server delete failed:', result.error);
                        alert('Warning: Failed to delete some files from server.');
                    }
                } catch (err) {
                    console.error('Server connection failed during delete:', err);
                }

                // 2. Delete from LocalStorage
                const updatedLibrary = library.filter(item => !selectedItems.has(item.id));
                localStorage.setItem(LIBRARY_KEY, JSON.stringify(updatedLibrary));

                // 3. Reset UI
                selectionMode = false;
                selectedItems.clear();
                renderLibraryList();
                alert('Selected items deleted.');
            });
        }

        // Assign chapter handler
        const assignSelect = toolbar.querySelector('#assign-chapter-select');
        if (assignSelect) {
            assignSelect.addEventListener('change', (e) => {
                if (e.target.value && selectedItems.size > 0) {
                    const newChapterId = e.target.value;
                    const updatedLibrary = library.map(item => {
                        if (selectedItems.has(item.id)) {
                            return { ...item, chapterId: newChapterId };
                        }
                        return item;
                    });
                    localStorage.setItem(LIBRARY_KEY, JSON.stringify(updatedLibrary));

                    // Auto-sync enabled
                    syncLibraryToServer();

                    selectionMode = false;
                    selectedItems.clear();
                    renderLibraryList();
                    updateExportButtonVisibility();
                }
            });
        }

        listContainer.innerHTML = '';

        if (filteredLibrary.length === 0) {
            emptyMsg.style.display = 'flex';
            emptyMsg.innerHTML = currentSearchTerm
                ? `<p>No results found for "${currentSearchTerm}"</p>`
                : `<div class="empty-icon-container"><span class="material-symbols-rounded">folder_open</span></div><h3>No Saved Infographics</h3><p>Generate an infographic and click "Save" to build your knowledge base.</p>`;
            listContainer.style.display = 'none';
        } else {
            emptyMsg.style.display = 'none';
            listContainer.style.display = 'flex';

            filteredLibrary.forEach(item => {
                const chapter = chapters.find(ch => ch.id === item.chapterId) || chapters[0];
                const isSelected = selectedItems.has(item.id);

                // Check if item is newly imported (within last 24 hours)
                const isNewlyImported = item._newlyImported && (Date.now() - item._newlyImported) < 24 * 60 * 60 * 1000;
                // Check if chapter was recently updated (within last 24 hours)
                const isChapterUpdated = item._chapterUpdated && (Date.now() - item._chapterUpdated) < 24 * 60 * 60 * 1000;
                const isNew = isNewlyImported || isChapterUpdated;
                const hashtagColor = isNew ? '#22c55e' : '#94a3b8'; // Green for new/updated, gray for regular
                const hashtagTitle = isNewlyImported ? 'Newly synced' : (isChapterUpdated ? 'Chapter updated' : '');

                const el = document.createElement('div');
                el.className = `saved-item ${isSelected ? 'selected' : ''} ${isNew ? 'newly-imported' : ''}`;
                el.innerHTML = `
                    ${selectionMode ? `
                        <input type="checkbox" class="item-checkbox" data-id="${item.id}" ${isSelected ? 'checked' : ''}>
                    ` : `
                        <div class="item-number" style="font-weight: bold; color: ${hashtagColor}; font-size: 0.9rem; margin-right: 12px; min-width: 25px;" title="${hashtagTitle}">#${item.seqId || '?'}${isNew ? ' ✨' : ''}</div>
                    `}
                    <div class="saved-info">
                        <div class="saved-title-row">
                            <span class="chapter-badge" style="background: ${chapter.color}">${chapter.name}</span>
                            <span class="saved-title">${item.title}</span>
                        </div>
                        <div class="saved-date">${new Date(item.date).toLocaleString()}</div>
                    </div>
                    <div class="saved-actions">
                        <button class="btn-small btn-rename" data-id="${item.id}" title="Rename">
                            <span class="material-symbols-rounded" style="font-size: 1rem;">edit</span>
                        </button>
                        <button class="btn-small btn-load" data-id="${item.id}">Load</button>
                        <button class="btn-small btn-delete" data-id="${item.id}" title="Delete">
                            <span class="material-symbols-rounded" style="font-size: 1.2rem;">delete</span>
                        </button>
                    </div>
                `;
                listContainer.appendChild(el);
            });

            // Checkbox handlers
            listContainer.querySelectorAll('.item-checkbox').forEach(cb => {
                cb.addEventListener('change', (e) => {
                    const id = parseInt(e.target.dataset.id);
                    if (e.target.checked) {
                        selectedItems.add(id);
                    } else {
                        selectedItems.delete(id);
                    }
                    renderLibraryList(); // Re-render to update selected styling if needed, or just update class
                    updateExportButtonVisibility();
                });
            });

            // Rename handlers
            listContainer.querySelectorAll('.btn-rename').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const button = e.target.closest('.btn-rename');
                    const id = parseInt(button.dataset.id);
                    const targetItem = library.find(i => i.id === id);

                    if (targetItem) {
                        const password = prompt('Enter admin password to rename:');
                        if (password === '309030') {
                            const newTitle = prompt('Enter new title:', targetItem.title);
                            if (newTitle && newTitle.trim()) {
                                targetItem.title = newTitle.trim();
                                if (targetItem.data) {
                                    targetItem.data.title = newTitle.trim();
                                }
                                localStorage.setItem(LIBRARY_KEY, JSON.stringify(library));

                                // Auto-Sync
                                syncLibraryToServer();

                                renderLibraryList();
                            }
                        } else if (password !== null) {
                            alert('Incorrect password. Renaming requires admin access.');
                        }
                    }
                });
            });

            // Load handlers
            listContainer.querySelectorAll('.btn-load').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = parseInt(e.target.dataset.id);
                    const targetItem = library.find(i => i.id === id);
                    if (targetItem) {
                        currentInfographicData = targetItem.data;
                        renderInfographic(targetItem.data);
                        modal.classList.remove('active');
                    }
                });
            });

            // Delete handlers
            listContainer.querySelectorAll('.btn-delete').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const button = e.target.closest('.btn-delete');
                    const id = parseInt(button.dataset.id);
                    const itemToDelete = library.find(i => i.id === id);

                    const password = prompt('Enter admin password to delete:');
                    if (password === '309030') {
                        if (confirm('Are you sure you want to delete this item?\n\nThis will also remove it from all remote users\' libraries on their next sync.')) {
                            const newLibrary = library.filter(i => i.id !== id);

                            // Reassign sequential IDs after deletion (no gaps)
                            reassignSequentialIds(newLibrary);

                            localStorage.setItem(LIBRARY_KEY, JSON.stringify(newLibrary));

                            // Track deletion for remote sync (by normalized title)
                            if (itemToDelete && itemToDelete.title) {
                                const normalizedTitle = (itemToDelete.title || '').toLowerCase().trim().replace(/[^a-z0-9]/g, '');
                                if (typeof CommunitySubmissions !== 'undefined' && CommunitySubmissions.trackDeletion) {
                                    try {
                                        await CommunitySubmissions.trackDeletion(normalizedTitle);
                                        console.log(`[Admin Delete] Tracked deletion for remote sync: "${itemToDelete.title}"`);
                                    } catch (err) {
                                        console.log('Could not track deletion for remote sync:', err.message);
                                    }
                                }
                            }

                            // Delete from Server
                            try {
                                await safeFetch('api/library/delete', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ ids: [id] })
                                });
                            } catch (err) {
                                console.error('Failed to delete from server:', err);
                            }

                            // Auto-Sync
                            syncLibraryToServer();

                            renderLibraryList();
                            alert('Item deleted. Remote users will have this item removed on their next sync.');
                        }
                    } else if (password !== null) {
                        alert('Incorrect password. Deletion requires admin access.');
                    }
                });
            });
        }
    }
}

/* FTP Server Control Panel */
function setupFTPServer() {
    const ftpBtn = document.getElementById('ftp-btn');
    const ftpModal = document.getElementById('ftp-modal');
    const closeFtpBtn = document.getElementById('close-ftp-modal-btn');

    if (!ftpBtn || !ftpModal) return;

    ftpBtn.addEventListener('click', () => {
        ftpModal.classList.add('active');
        if (window.location.protocol !== 'file:') {
            updateFTPStatus();
        } else {
            const statusEl = document.getElementById('ftp-status');
            if (statusEl) {
                statusEl.innerHTML = `
                    <div class="ftp-status-badge stopped">
                        <span class="material-symbols-rounded">block</span>
                        Not Available
                    </div>
                    <p class="ftp-info">FTP Server control is not available on file:// protocol.</p>
                `;
            }
        }
    });

    if (closeFtpBtn) {
        closeFtpBtn.addEventListener('click', () => {
            ftpModal.classList.remove('active');
        });
    }

    ftpModal.addEventListener('click', (e) => {
        if (e.target === ftpModal) {
            ftpModal.classList.remove('active');
        }
    });

    // Start/Stop FTP server
    const startFtpBtn = document.getElementById('start-ftp-btn');
    const stopFtpBtn = document.getElementById('stop-ftp-btn');

    if (startFtpBtn) {
        startFtpBtn.addEventListener('click', async () => {
            try {
                const response = await safeFetch('api/ftp/start', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    alert(`FTP Server started on port ${result.port}`);
                    updateFTPStatus();
                } else {
                    alert('Failed to start FTP server: ' + result.error);
                }
            } catch (err) {
                alert('FTP server requires the Node.js backend. Please run: node server.js');
            }
        });
    }

    if (stopFtpBtn) {
        stopFtpBtn.addEventListener('click', async () => {
            try {
                const response = await safeFetch('api/ftp/stop', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    alert('FTP Server stopped');
                    updateFTPStatus();
                }
            } catch (err) {
                console.error('Failed to stop FTP server:', err);
            }
        });
    }

    async function updateFTPStatus() {
        const statusEl = document.getElementById('ftp-status');
        if (!statusEl) return;

        try {
            const response = await safeFetch('api/ftp/status');
            const result = await response.json();

            if (result.running) {
                statusEl.innerHTML = `
                    <div class="ftp-status-badge running">
                        <span class="material-symbols-rounded">cloud_done</span>
                        Running on port ${result.port}
                    </div>
                    <p class="ftp-info">Connect with any FTP client using:</p>
                    <code>ftp://${result.host || 'your-ip'}:${result.port}</code>
                    <p class="ftp-info">Username: <strong>ophthalmics</strong></p>
                    <p class="ftp-info">Password: <strong>157108</strong></p>
                `;
            } else {
                statusEl.innerHTML = `
                    <div class="ftp-status-badge stopped">
                        <span class="material-symbols-rounded">cloud_off</span>
                        Not Running
                    </div>
                    <p class="ftp-info">Start the FTP server to allow remote users to access the knowledge base.</p>
                `;
            }
        } catch (err) {
            statusEl.innerHTML = `
                <div class="ftp-status-badge error">
                    <span class="material-symbols-rounded">error</span>
                    Backend Not Available
                </div>
                <p class="ftp-info">To enable FTP server functionality, start the Node.js backend:</p>
                <code>node server.js</code>
            `;
        }
    }
}

// Initial Listeners consolidated below

let currentInfographicData = null;

document.addEventListener('DOMContentLoaded', () => {
    setupPrintButton();
    setupPosterButton();
    setupKnowledgeBase();
    setupFTPServer();
});

function setLoading(isLoading) {
    generateBtn.disabled = isLoading;
    if (isLoading) {
        generateBtn.innerHTML = '<div class="loader-animation" style="width:20px; height:20px; border-width:2px;"></div> Generating...';
        outputContainer.innerHTML = `
            <div class="loading-wrapper">
                <div class="loader-animation"></div>
                <div class="loading-text">Designing your Infographic...</div>
            </div>`;
        outputContainer.classList.remove('empty-state');
    } else {
        generateBtn.innerHTML = 'Generate Infographic';
    }
}

generateBtn.addEventListener('click', async () => {
    const apiKey = apiKeyInput.value.trim();
    const topic = topicInput.value.trim();

    if (!apiKey) {
        alert('Please enter your Gemini API Key');
        return;
    }

    if (!topic) {
        alert('Please enter a topic or text content');
        return;
    }

    setLoading(true);

    try {
        const data = await generateInfographicData(apiKey, topic);
        currentInfographicData = data;
        renderInfographic(data);
    } catch (error) {
        console.error('Generation Error:', error);
        outputContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon-container" style="background: #fee2e2; color: #ef4444;">
                    <span class="material-symbols-rounded">error_outline</span>
                </div>
                <h2>Generation Failed</h2>
                <p>${error.message || 'Something went wrong. Please check your API key and try again.'}</p>
            </div>
        `;
    } finally {
        setLoading(false);
    }
});



async function generateInfographicData(apiKey, topic) {
    const genAI = new GoogleGenerativeAI(apiKey);

    const modelsToTry = [
        "gemini-3-flash-preview",
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-pro"
    ];

    let lastError = null;

    for (const modelName of modelsToTry) {
        try {
            console.log(`Attempting to generate with model: ${modelName}`);
            const model = genAI.getGenerativeModel({ model: modelName });

            const prompt = `
                You are a world-class Ophthalmic Content Strategist and Information Designer.
                
                Goal: Transform the user's input Topic ("${topic}") into a VIBRANT, COLORFUL, and VISUAL poster.
                
                *** CRITICAL: ZERO OMISSION & EXACT PRESERVATION POLICY ***
                1. You MUST include EVERY SINGLE WORD, SENTENCE, and statistic from the input text.
                2. Do NOT summarize, abbreviate, or omit ANY details. The output must be EXHAUSTIVE.
                3. This is a "Visual Reformatting" task, NOT a summarization task. 
                4. If the input is long, create AS MANY SECTIONS AS NEEDED. Do not cut content to fit.
                5. Use "plain_text" blocks to preserve large chunks of text verbatim if they don't fit into charts/lists.
                6. **RESTRICTED SCOPE**: You must NOT add any information, facts, or context that is not explicitly present in the provided input text. Do not hallucinate or fetch outside knowledge.
                7. **VERIFICATION**: Before outputting, verify that n% of the input text is present in the output JSON.
                
                Guidelines:
                1. **Visual Variety**: Use charts, warning boxes, mindmaps, mnemonics, and lists.
                2. **Poster Layout**: The output will be arranged in a masonry grid. Important sections should be marked to span across the poster.
                3. **Tone**: Educational yet highly engaging.
                4. **Completeness**: Create as many sections as needed to cover 100% of the input text context.

                JSON Schema (Strict):
                {
                    "title": "A Punchy, Poster-Style Title",
                    "summary": "A 2-3 sentence engaging summary.",
                    "summary_illustration": "<svg ...> ... </svg>", // A simple, clean, iconic SVG illustration valid code.
                    "sections": [
                        // Create as many sections as needed to cover ALL input text.
                        {
                            "title": "Section Title",
                            "icon": "material_symbol_name", 
                            "type": "layout_type", // "chart", "red_flag", "mindmap", "remember", "key_point", "process", "plain_text", "table"
                            "layout": "full_width" | "half_width", // Use "full_width" for large diagrams or main headers
                            "color_theme": "blue" | "red" | "green" | "yellow" | "purple", 
                            "content": ... // see content rules
                        }
                    ]
                }
                
                Layout Types & Content Rules:
                1. "chart": { "type": "bar", "data": [ {"label": "Label A", "value": 80}, {"label": "Label B", "value": 45} ] } 
                   (Simple comparative data. Values 0-100 relative scale)
                
                2. "red_flag": [ "Warning Sign 1", "Contraindication 2" ] 
                   (Crucial warnings. Theme MUST be 'red')
                
                3. "remember": { "mnemonic": "ABCD", "explanation": "A for Age, B for..." } 
                   (Memory aids. Theme usually 'yellow' or 'purple')
                
                4. "mindmap": { "center": "Main Concept", "branches": ["Branch A", "Branch B", "Branch C"] }
                   (Simple central concept with radiating ideas. Break complex concepts into multiple mindmaps if needed.)

                5. "key_point": [ "Point 1", "Point 2" ] (Standard bullets. Use this for lists. ENSURE NO ITEM IS DROPPED.)
                
                6. "process": [ "Step 1: ...", "Step 2: ..." ] (Sequential steps)

                7. "plain_text": "Content string..." (Use this to include paragraphs verbatim if they don't fit other structures.)

                8. "table": { "headers": ["Col 1", "Col 2"], "rows": [ ["Row 1 Col 1", "Row 1 Col 2"], ... ] }
                   (Use this for ANY structured data or comparisons in the input text.)

                Special Instruction for 'summary_illustration':
                - Generate a valid, minimal SVG string that visually represents the core topic.
                - Use a flat, modern, vector art style.
                - Use the primary color (hsl(215, 90%, 45%)) or relevant accents.
                - Keep it simple (iconic representation rather than complex scene).
                - Ensure viewBox is set.

                Design Focus:
                - If the text contains a list of 20 items, create a section with 20 items. Do not pick "top 5".
                - If the text contains specific data points, ensure ALL are mapped to charts or text.
                - If the topic has stages or hierarchy, use "mindmap".
                - If there are clear contraindications, use "red_flag".
                - The Illustration should be high quality and relevant to Ophthalmology.

                User Topic/Text: "${topic}"
            `;

            const result = await model.generateContent(prompt);
            const response = await result.response;
            let text = response.text();
            text = text.replace(/```json/g, '').replace(/```/g, '').trim();
            return JSON.parse(text);

        } catch (error) {
            console.warn(`Failed with model ${modelName}:`, error);
            lastError = error;
            if (!error.message.includes('404') && !error.message.includes('not found')) {
                // optionally break here
            }
        }
    }
    throw lastError || new Error("All models failed.");
}

function renderInfographic(data) {
    outputContainer.innerHTML = '';
    outputContainer.classList.remove('empty-state');

    // Create the main Poster Sheet container
    const posterSheet = document.createElement('div');
    posterSheet.className = 'poster-sheet';

    // Header (Inside the sheet)
    const header = document.createElement('header');
    header.className = 'poster-header';

    // Illustration Container
    let illustrationHtml = '';
    if (data.summary_illustration) {
        illustrationHtml = `
            <div class="poster-illustration">
                ${data.summary_illustration}
            </div>
        `;
    }

    header.innerHTML = `
        <div class="header-decoration"></div>
        <h1 class="poster-title">${data.title}</h1>
        <div class="header-content-wrapper" style="display: flex; gap: 2rem; align-items: start;">
            <p class="poster-summary" style="flex: 1;">${data.summary}</p>
            ${illustrationHtml}
        </div>
    `;
    posterSheet.appendChild(header);

    // Grid (Inside the sheet)
    const grid = document.createElement('div');
    grid.className = 'poster-grid';

    data.sections.forEach((section, index) => {
        const card = document.createElement('div');
        const layoutClass = section.layout === 'full_width' ? 'col-span-2' : '';
        const colorClass = `theme-${section.color_theme || 'blue'}`;
        card.className = `poster-card card-${section.type} ${layoutClass} ${colorClass}`;

        card.style.animationDelay = `${index * 100}ms`;

        const iconName = section.icon || 'circle';

        let contentHtml = '';

        switch (section.type) {
            case 'red_flag':
                const flags = Array.isArray(section.content) ? section.content : [section.content];
                contentHtml = `<ul class="warning-list">
                    ${flags.map(item => `<li>
                        <span class="material-symbols-rounded warning-icon">warning</span>
                        ${item}
                    </li>`).join('')}
                </ul>`;
                break;

            case 'chart':
                const chartContent = section.content || {};
                const chartData = chartContent.data || [];
                contentHtml = `<div class="bar-chart">
                    ${chartData.map(d => `
                        <div class="chart-row">
                            <div class="chart-label">${d.label}</div>
                            <div class="chart-bar-container">
                                <div class="chart-bar" style="width: ${d.value}%"></div>
                                <span class="chart-val">${d.value}%</span>
                            </div>
                        </div>
                    `).join('')}
                </div>`;
                break;

            case 'remember':
                const mem = section.content || {};
                contentHtml = `<div class="mnemonic-box">
                    <div class="mnemonic-title">${mem.mnemonic || 'REMEMBER'}</div>
                    <div class="mnemonic-text">${mem.explanation}</div>
                </div>`;
                break;

            case 'mindmap':
                const map = section.content || {};
                const branches = map.branches || [];
                contentHtml = `<div class="mindmap-container">
                    <div class="mindmap-center">${map.center}</div>
                    <div class="mindmap-branches">
                        ${branches.map(b => `<div class="mindmap-branch">${b}</div>`).join('')}
                    </div>
                </div>`;
                break;

            case 'key_point':
            case 'process':
                const points = Array.isArray(section.content) ? section.content : [section.content];
                contentHtml = `<ul class="card-list">
                    ${points.map(item => `<li>${item}</li>`).join('')}
                </ul>`;
                break;

            case 'table':
                if (section.content && section.content.headers && section.content.rows) {
                    const headers = section.content.headers || [];
                    const rows = section.content.rows || [];
                    contentHtml = `
                    <div class="table-wrapper">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    ${headers.map(h => `<th>${h}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${rows.map(row => `
                                    <tr>
                                        ${row.map(cell => `<td>${cell}</td>`).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>`;
                } else {
                    contentHtml = `<p class="plain-text">Invalid table data received.</p>`;
                }
                break;

            default:
                contentHtml = `<p class="plain-text">${section.content}</p>`;
        }

        const titleHtml = `
            <h3 class="card-title">
                <div class="icon-box"><span class="material-symbols-rounded">${iconName}</span></div>
                ${section.title}
            </h3>`;

        card.innerHTML = `
            ${titleHtml}
            <div class="card-content">
                ${contentHtml}
            </div>
            <div class="card-deco"></div>
        `;
        grid.appendChild(card);
    });

    posterSheet.appendChild(grid);
    outputContainer.appendChild(posterSheet);

    // Enable Studio Tools when infographic is generated
    enableStudioTools();

    // Auto-collapse sidebar to give more space for viewing the infographic
    setTimeout(() => {
        collapseSidebar();
    }, 500); // Small delay to let the user see the result first
}

/* ========================================
   STUDIO TOOLS - NotebookLM-Style Features
   ======================================== */

function enableStudioTools() {
    const studioPanel = document.getElementById('studio-panel');
    if (studioPanel) {
        studioPanel.classList.add('studio-panel-enabled');
        const buttons = studioPanel.querySelectorAll('.studio-tool-btn');
        buttons.forEach(btn => btn.disabled = false);
    }
}

function disableStudioTools() {
    const studioPanel = document.getElementById('studio-panel');
    if (studioPanel) {
        studioPanel.classList.remove('studio-panel-enabled');
        const buttons = studioPanel.querySelectorAll('.studio-tool-btn');
        buttons.forEach(btn => btn.disabled = true);
    }
}

/* ========================================
   AI-POWERED STUDIO TOOLS HELPER
   Uses Gemini 2.0 Flash for enhanced content generation
   ======================================== */

async function callGeminiForStudioTool(prompt, fallbackFn = null) {
    const apiKey = document.getElementById('api-key')?.value?.trim();

    if (!apiKey) {
        console.log('No API key provided, using fallback method');
        return fallbackFn ? fallbackFn() : null;
    }

    try {
        const genAI = new GoogleGenerativeAI(apiKey);

        // Try Gemini 2.0 Flash first, then fallbacks
        const modelsToTry = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest"
        ];

        let lastError = null;

        for (const modelName of modelsToTry) {
            try {
                console.log(`Studio Tool: Trying model ${modelName}`);
                const model = genAI.getGenerativeModel({ model: modelName });
                const result = await model.generateContent(prompt);
                const response = await result.response;
                return response.text();
            } catch (err) {
                console.log(`Model ${modelName} failed:`, err.message);
                lastError = err;
            }
        }

        throw lastError || new Error('All models failed');
    } catch (error) {
        console.error('Gemini API call failed:', error);
        return fallbackFn ? fallbackFn() : null;
    }
}

// AI-Enhanced Transcript Generation
async function generateAITranscript() {
    if (!currentInfographicData) return null;

    const voiceStyle = document.getElementById('voice-select')?.value || 'default';
    const styleGuide = {
        'default': 'professional and educational',
        'friendly': 'warm, conversational, and engaging like talking to a colleague',
        'formal': 'academic and authoritative like a medical lecture'
    };

    const prompt = `You are creating an audio narration script for a medical education podcast.

Topic: ${currentInfographicData.title}

Content to cover:
${JSON.stringify(currentInfographicData.sections?.map(s => ({ title: s.title, content: s.content })) || [], null, 2)}

Summary: ${currentInfographicData.summary || ''}

Create a ${styleGuide[voiceStyle]} narration script that:
1. Opens with an engaging introduction
2. Covers ALL key points from the content
3. Uses clear transitions between topics
4. Includes brief clinical pearls or memorable takeaways
5. Ends with a concise summary

Write the script as flowing paragraphs (not bullet points) suitable for text-to-speech. 
Keep it under 800 words for a 5-minute audio overview.
Do not include any stage directions or speaker labels - just the narration text.`;

    return await callGeminiForStudioTool(prompt);
}

// AI-Enhanced Flashcard Generation
async function generateAIFlashcards() {
    if (!currentInfographicData) return null;

    const prompt = `You are creating medical education flashcards for ophthalmology students.

Topic: ${currentInfographicData.title}

Content:
${JSON.stringify(currentInfographicData.sections?.map(s => ({ title: s.title, content: s.content })) || [], null, 2)}

Create 10-15 high-quality flashcards in this exact JSON format:
[
    {
        "question": "Clear, specific question testing understanding",
        "answer": "Concise but complete answer"
    }
]

Guidelines:
1. Mix question types: definitions, comparisons, clinical scenarios, mechanisms
2. Include questions about key facts, differential diagnosis, and management
3. Make answers memorable and clinically relevant
4. Include mnemonics where helpful
5. Test both recall and application of knowledge

Return ONLY valid JSON array, no other text.`;

    const result = await callGeminiForStudioTool(prompt);
    if (result) {
        try {
            // Extract JSON from response
            const jsonMatch = result.match(/\[[\s\S]*\]/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
        } catch (e) {
            console.error('Failed to parse AI flashcards:', e);
        }
    }
    return null;
}

// AI-Enhanced Quiz Generation
async function generateAIQuiz() {
    if (!currentInfographicData) return null;

    const prompt = `You are creating a medical knowledge quiz for ophthalmology education.

Topic: ${currentInfographicData.title}

Content:
${JSON.stringify(currentInfographicData.sections?.map(s => ({ title: s.title, content: s.content })) || [], null, 2)}

Create 8-10 multiple choice questions in this exact JSON format:
[
    {
        "question": "Question text here?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correctAnswer": "The exact text of the correct option",
        "explanation": "Brief explanation of why this answer is correct"
    }
]

Guidelines:
1. Questions should test understanding, not just memorization
2. All 4 options should be plausible to someone who didn't study
3. Avoid "all of the above" or "none of the above"
4. Include clinical scenario questions where appropriate
5. Vary difficulty from basic recall to clinical application
6. Explanations should be educational and reinforce learning

Return ONLY valid JSON array, no other text.`;

    const result = await callGeminiForStudioTool(prompt);
    if (result) {
        try {
            const jsonMatch = result.match(/\[[\s\S]*\]/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
        } catch (e) {
            console.error('Failed to parse AI quiz:', e);
        }
    }
    return null;
}

// Simple Markdown to HTML converter
function convertMarkdownToHTML(markdown) {
    if (!markdown) return '';

    return markdown
        // Headers
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Bullet lists
        .replace(/^\- (.*$)/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        // Numbered lists
        .replace(/^\d+\. (.*$)/gm, '<li>$1</li>')
        // Paragraphs (double newlines)
        .replace(/\n\n/g, '</p><p>')
        // Single newlines
        .replace(/\n/g, '<br>')
        // Wrap in paragraph
        .replace(/^(.+)$/gm, (match) => {
            if (match.startsWith('<h') || match.startsWith('<ul') || match.startsWith('<li') || match.startsWith('<p')) {
                return match;
            }
            return `<p>${match}</p>`;
        });
}

// AI-Enhanced Report Generation
async function generateAIReport(format) {
    if (!currentInfographicData) return null;

    const formatGuides = {
        'summary': 'Create a concise 2-3 paragraph executive summary highlighting the most critical clinical points.',
        'detailed': 'Create a comprehensive study guide with detailed explanations of each topic, including pathophysiology and clinical correlations.',
        'bullet': 'Create a well-organized bullet-point summary with clear headers and sub-points for quick review.',
        'study-guide': 'Create a structured study guide with learning objectives, key concepts, clinical pearls, and review questions.'
    };

    const prompt = `You are creating educational content for ophthalmology professionals.

Topic: ${currentInfographicData.title}

Source Content:
${JSON.stringify(currentInfographicData, null, 2)}

Task: ${formatGuides[format] || formatGuides['summary']}

Requirements:
1. Cover ALL information from the source content
2. Use clear medical terminology
3. Organize information logically
4. Include clinical relevance where appropriate
5. Format with proper headers using markdown (## for main sections, ### for subsections)

Create the ${format} report now:`;

    return await callGeminiForStudioTool(prompt);
}

/* ========================================
   AUDIO OVERVIEW FEATURE
   ======================================== */

let audioContext = null;
let audioSource = null;
let isPlaying = false;
let audioTranscript = '';

function setupAudioOverview() {
    const audioBtn = document.getElementById('audio-overview-btn');
    const audioModal = document.getElementById('audio-modal');
    const closeBtn = document.getElementById('close-audio-modal-btn');
    const generateBtn = document.getElementById('generate-audio-btn');
    const playBtn = document.getElementById('audio-play-btn');
    const downloadBtn = document.getElementById('download-audio-btn');

    if (!audioBtn || !audioModal) return;

    audioBtn.addEventListener('click', () => {
        if (!currentInfographicData) {
            alert('Please generate an infographic first.');
            return;
        }
        audioModal.classList.add('active');
        generateTranscript();
    });

    closeBtn?.addEventListener('click', () => {
        audioModal.classList.remove('active');
        stopAudio();
    });

    audioModal.addEventListener('click', (e) => {
        if (e.target === audioModal) {
            audioModal.classList.remove('active');
            stopAudio();
        }
    });

    generateBtn?.addEventListener('click', () => {
        generateAudio();
    });

    playBtn?.addEventListener('click', () => {
        if (isPlaying) {
            stopAudio();
        } else {
            playAudio();
        }
    });
}

async function generateTranscript() {
    if (!currentInfographicData) return;

    const transcriptEl = document.getElementById('audio-transcript-text');
    const generateBtn = document.getElementById('generate-audio-btn');

    // Show loading state
    if (transcriptEl) {
        transcriptEl.innerHTML = '<em>Generating AI-powered transcript with Gemini...</em>';
    }
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="material-symbols-rounded rotating">sync</span> Generating...';
    }

    // Try AI-powered transcript first
    const aiTranscript = await generateAITranscript();

    if (aiTranscript) {
        audioTranscript = aiTranscript;
        if (transcriptEl) {
            transcriptEl.textContent = audioTranscript;
        }
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<span class="material-symbols-rounded">record_voice_over</span> Generate Audio';
        }
        return;
    }

    // Fallback to basic transcript generation
    console.log('Using fallback transcript generation');
    const data = currentInfographicData;
    let transcript = `${data.title}.\n\n`;
    transcript += `${data.summary}\n\n`;

    if (data.sections) {
        data.sections.forEach(section => {
            transcript += `${section.title}.\n`;

            if (Array.isArray(section.content)) {
                section.content.forEach(item => {
                    transcript += `${item}.\n`;
                });
            } else if (typeof section.content === 'object') {
                if (section.content.mnemonic) {
                    transcript += `Remember: ${section.content.mnemonic}. ${section.content.explanation}.\n`;
                } else if (section.content.center) {
                    transcript += `Central concept: ${section.content.center}. `;
                    if (section.content.branches) {
                        transcript += `Key branches include: ${section.content.branches.join(', ')}.\n`;
                    }
                } else if (section.content.data) {
                    section.content.data.forEach(d => {
                        transcript += `${d.label}: ${d.value} percent.\n`;
                    });
                } else if (section.content.headers && section.content.rows) {
                    section.content.rows.forEach(row => {
                        transcript += row.join(', ') + '.\n';
                    });
                }
            } else {
                transcript += `${section.content}.\n`;
            }
            transcript += '\n';
        });
    }

    audioTranscript = transcript;
    if (transcriptEl) {
        transcriptEl.textContent = transcript;
    }
    if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<span class="material-symbols-rounded">record_voice_over</span> Generate Audio';
    }
}

function generateAudio() {
    if (!audioTranscript) {
        generateTranscript();
    }

    // Use Web Speech API for text-to-speech
    if ('speechSynthesis' in window) {
        const voiceSelect = document.getElementById('voice-select');
        const voiceStyle = voiceSelect?.value || 'default';

        // Create animated waveform
        createWaveformAnimation();

        const generateBtn = document.getElementById('generate-audio-btn');
        const downloadBtn = document.getElementById('download-audio-btn');

        if (generateBtn) {
            generateBtn.innerHTML = '<span class="material-symbols-rounded">check</span> Audio Ready';
        }
        if (downloadBtn) {
            downloadBtn.style.display = 'flex';
        }

        alert('Audio generated! Click Play to listen. Note: Audio uses browser\'s text-to-speech capabilities.');
    } else {
        alert('Text-to-speech is not supported in this browser.');
    }
}

function createWaveformAnimation() {
    const waveform = document.querySelector('.audio-waveform');
    if (!waveform) return;

    waveform.innerHTML = '';
    for (let i = 0; i < 40; i++) {
        const bar = document.createElement('div');
        bar.className = 'bar';
        bar.style.animationDelay = `${i * 0.05}s`;
        bar.style.height = `${20 + Math.random() * 60}%`;
        waveform.appendChild(bar);
    }
}

function playAudio() {
    if (!audioTranscript) return;

    const utterance = new SpeechSynthesisUtterance(audioTranscript);
    const voiceSelect = document.getElementById('voice-select');
    const voiceStyle = voiceSelect?.value || 'default';

    // Set voice properties based on style
    switch (voiceStyle) {
        case 'friendly':
            utterance.rate = 1.1;
            utterance.pitch = 1.1;
            break;
        case 'formal':
            utterance.rate = 0.9;
            utterance.pitch = 0.9;
            break;
        default:
            utterance.rate = 1;
            utterance.pitch = 1;
    }

    utterance.onstart = () => {
        isPlaying = true;
        updatePlayButton();
        animateProgress();
    };

    utterance.onend = () => {
        isPlaying = false;
        updatePlayButton();
        resetProgress();
    };

    speechSynthesis.speak(utterance);
}

function stopAudio() {
    speechSynthesis.cancel();
    isPlaying = false;
    updatePlayButton();
    resetProgress();
}

function updatePlayButton() {
    const playBtn = document.getElementById('audio-play-btn');
    if (playBtn) {
        playBtn.innerHTML = isPlaying
            ? '<span class="material-symbols-rounded">pause</span>'
            : '<span class="material-symbols-rounded">play_arrow</span>';
    }
}

function animateProgress() {
    const progressBar = document.getElementById('audio-progress-bar');
    if (progressBar) {
        progressBar.style.transition = 'width 60s linear';
        progressBar.style.width = '100%';
    }
}

function resetProgress() {
    const progressBar = document.getElementById('audio-progress-bar');
    if (progressBar) {
        progressBar.style.transition = 'none';
        progressBar.style.width = '0%';
    }
}

/* ========================================
   VIDEO OVERVIEW FEATURE
   ======================================== */

let videoSlides = [];
let currentVideoSlide = 0;
let videoAutoPlay = null;

function setupVideoOverview() {
    const videoBtn = document.getElementById('video-overview-btn');
    const videoModal = document.getElementById('video-modal');
    const closeBtn = document.getElementById('close-video-modal-btn');
    const generateBtn = document.getElementById('generate-video-btn');
    const playBtn = document.getElementById('video-play-btn');
    const prevBtn = document.getElementById('video-prev-btn');
    const nextBtn = document.getElementById('video-next-btn');
    const exportBtn = document.getElementById('export-video-btn');

    if (!videoBtn || !videoModal) return;

    videoBtn.addEventListener('click', () => {
        if (!currentInfographicData) {
            alert('Please generate an infographic first.');
            return;
        }
        videoModal.classList.add('active');
    });

    closeBtn?.addEventListener('click', () => {
        videoModal.classList.remove('active');
        stopVideoAutoPlay();
    });

    videoModal.addEventListener('click', (e) => {
        if (e.target === videoModal) {
            videoModal.classList.remove('active');
            stopVideoAutoPlay();
        }
    });

    generateBtn?.addEventListener('click', generateVideoSlides);
    playBtn?.addEventListener('click', toggleVideoAutoPlay);
    prevBtn?.addEventListener('click', () => navigateVideoSlide(-1));
    nextBtn?.addEventListener('click', () => navigateVideoSlide(1));
    exportBtn?.addEventListener('click', exportVideoAsHTML);
}

function generateVideoSlides() {
    if (!currentInfographicData) return;

    const data = currentInfographicData;
    videoSlides = [];

    // Title slide
    videoSlides.push({
        type: 'title',
        title: data.title,
        subtitle: data.summary
    });

    // Section slides
    if (data.sections) {
        data.sections.forEach(section => {
            videoSlides.push({
                type: 'section',
                title: section.title,
                content: section.content,
                sectionType: section.type,
                colorTheme: section.color_theme
            });
        });
    }

    // Summary slide
    videoSlides.push({
        type: 'end',
        title: 'Key Takeaways',
        subtitle: 'Review and practice the concepts covered'
    });

    currentVideoSlide = 0;
    renderVideoSlide();
    updateVideoCounter();

    const exportBtn = document.getElementById('export-video-btn');
    if (exportBtn) exportBtn.style.display = 'flex';
}

function renderVideoSlide() {
    const slideContainer = document.getElementById('current-slide');
    if (!slideContainer || videoSlides.length === 0) return;

    const slide = videoSlides[currentVideoSlide];

    if (slide.type === 'title' || slide.type === 'end') {
        slideContainer.innerHTML = `
            <h2>${slide.title}</h2>
            <p>${slide.subtitle || ''}</p>
        `;
        slideContainer.style.background = 'linear-gradient(135deg, #1e293b, #334155)';
    } else {
        let contentHtml = '';

        if (Array.isArray(slide.content)) {
            contentHtml = `<ul>${slide.content.map(item => `<li>${item}</li>`).join('')}</ul>`;
        } else if (typeof slide.content === 'object') {
            if (slide.content.mnemonic) {
                contentHtml = `<p><strong>${slide.content.mnemonic}</strong><br>${slide.content.explanation}</p>`;
            } else if (slide.content.center) {
                contentHtml = `<p><strong>${slide.content.center}</strong></p>`;
                if (slide.content.branches) {
                    contentHtml += `<ul>${slide.content.branches.map(b => `<li>${b}</li>`).join('')}</ul>`;
                }
            } else if (slide.content.data) {
                contentHtml = `<ul>${slide.content.data.map(d => `<li>${d.label}: ${d.value}%</li>`).join('')}</ul>`;
            }
        } else {
            contentHtml = `<p>${slide.content}</p>`;
        }

        const bgColor = getSlideBackground(slide.colorTheme);
        slideContainer.innerHTML = `
            <h2>${slide.title}</h2>
            ${contentHtml}
        `;
        slideContainer.style.background = bgColor;
    }
}

function getSlideBackground(theme) {
    const themes = {
        blue: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
        red: 'linear-gradient(135deg, #ef4444, #dc2626)',
        green: 'linear-gradient(135deg, #10b981, #059669)',
        yellow: 'linear-gradient(135deg, #f59e0b, #d97706)',
        purple: 'linear-gradient(135deg, #8b5cf6, #7c3aed)'
    };
    return themes[theme] || 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
}

function navigateVideoSlide(direction) {
    if (videoSlides.length === 0) return;

    currentVideoSlide += direction;
    if (currentVideoSlide < 0) currentVideoSlide = videoSlides.length - 1;
    if (currentVideoSlide >= videoSlides.length) currentVideoSlide = 0;

    renderVideoSlide();
    updateVideoCounter();
}

function updateVideoCounter() {
    const counter = document.getElementById('slide-counter');
    if (counter) {
        counter.textContent = `${currentVideoSlide + 1} / ${videoSlides.length}`;
    }
}

function toggleVideoAutoPlay() {
    const playBtn = document.getElementById('video-play-btn');

    if (videoAutoPlay) {
        stopVideoAutoPlay();
        if (playBtn) playBtn.innerHTML = '<span class="material-symbols-rounded">play_arrow</span>';
    } else {
        videoAutoPlay = setInterval(() => {
            navigateVideoSlide(1);
        }, 4000);
        if (playBtn) playBtn.innerHTML = '<span class="material-symbols-rounded">pause</span>';
    }
}

function stopVideoAutoPlay() {
    if (videoAutoPlay) {
        clearInterval(videoAutoPlay);
        videoAutoPlay = null;
    }
}

function exportVideoAsHTML() {
    if (videoSlides.length === 0) return;

    let html = `<!DOCTYPE html>
<html>
<head>
    <title>${currentInfographicData.title} - Video Presentation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #000; }
        .slide { width: 100vw; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; padding: 4rem; text-align: center; }
        h2 { font-size: 3rem; margin-bottom: 2rem; }
        p { font-size: 1.5rem; opacity: 0.9; }
        ul { font-size: 1.3rem; text-align: left; list-style: none; }
        li { padding: 0.5rem 0; }
        li::before { content: "▸ "; color: rgba(255,255,255,0.7); }
    </style>
</head>
<body>
${videoSlides.map((slide, i) => `
    <div class="slide" style="background: ${slide.type === 'title' || slide.type === 'end' ? 'linear-gradient(135deg, #1e293b, #334155)' : getSlideBackground(slide.colorTheme)}">
        <h2>${slide.title}</h2>
        ${slide.subtitle ? `<p>${slide.subtitle}</p>` : ''}
        ${Array.isArray(slide.content) ? `<ul>${slide.content.map(c => `<li>${c}</li>`).join('')}</ul>` : ''}
    </div>
`).join('')}
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentInfographicData.title.replace(/[^a-z0-9]/gi, '_')}_presentation.html`;
    a.click();
    URL.revokeObjectURL(url);
}

/* ========================================
   MIND MAP FEATURE
   ======================================== */

let mindmapZoom = 1;

function setupMindMap() {
    const mindmapBtn = document.getElementById('mindmap-view-btn');
    const mindmapModal = document.getElementById('mindmap-modal');
    const closeBtn = document.getElementById('close-mindmap-modal-btn');
    const zoomInBtn = document.getElementById('mindmap-zoom-in');
    const zoomOutBtn = document.getElementById('mindmap-zoom-out');
    const resetBtn = document.getElementById('mindmap-reset');
    const exportBtn = document.getElementById('export-mindmap-btn');

    if (!mindmapBtn || !mindmapModal) return;

    mindmapBtn.addEventListener('click', () => {
        if (!currentInfographicData) {
            alert('Please generate an infographic first.');
            return;
        }
        mindmapModal.classList.add('active');
        generateMindMap();
    });

    closeBtn?.addEventListener('click', () => mindmapModal.classList.remove('active'));
    mindmapModal.addEventListener('click', (e) => {
        if (e.target === mindmapModal) mindmapModal.classList.remove('active');
    });

    zoomInBtn?.addEventListener('click', () => {
        mindmapZoom = Math.min(mindmapZoom + 0.2, 2);
        applyMindmapZoom();
    });

    zoomOutBtn?.addEventListener('click', () => {
        mindmapZoom = Math.max(mindmapZoom - 0.2, 0.5);
        applyMindmapZoom();
    });

    resetBtn?.addEventListener('click', () => {
        mindmapZoom = 1;
        applyMindmapZoom();
    });

    exportBtn?.addEventListener('click', exportMindMapAsPNG);
}

function generateMindMap() {
    const canvas = document.getElementById('mindmap-canvas');
    if (!canvas || !currentInfographicData) return;

    const data = currentInfographicData;
    const centerX = 450;
    const centerY = 300;
    const radius = 180;

    let svg = `<svg class="mindmap-svg" viewBox="0 0 900 600" style="transform: scale(${mindmapZoom})">`;

    // Draw connections first (behind nodes)
    const sections = data.sections || [];
    const angleStep = (2 * Math.PI) / Math.max(sections.length, 1);

    sections.forEach((section, i) => {
        const angle = i * angleStep - Math.PI / 2;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);

        // Draw line from center to branch
        svg += `<line class="mindmap-line" x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}"/>`;
    });

    // Draw center node
    svg += `<g class="mindmap-node">
        <circle class="mindmap-node-center" cx="${centerX}" cy="${centerY}" r="60"/>
        <text class="mindmap-text" x="${centerX}" y="${centerY}">${truncateText(data.title, 20)}</text>
    </g>`;

    // Draw branch nodes
    sections.forEach((section, i) => {
        const angle = i * angleStep - Math.PI / 2;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);

        const colors = {
            blue: '#3b82f6',
            red: '#ef4444',
            green: '#10b981',
            yellow: '#f59e0b',
            purple: '#8b5cf6'
        };
        const color = colors[section.color_theme] || '#3b82f6';

        svg += `<g class="mindmap-node">
            <circle cx="${x}" cy="${y}" r="45" fill="${color}"/>
            <text class="mindmap-text" x="${x}" y="${y}">${truncateText(section.title, 15)}</text>
        </g>`;

        // Draw leaf nodes for content
        if (Array.isArray(section.content)) {
            const leafRadius = 60;
            const leafCount = Math.min(section.content.length, 4);
            const leafAngleStep = Math.PI / 3 / Math.max(leafCount - 1, 1);
            const startLeafAngle = angle - Math.PI / 6;

            section.content.slice(0, 4).forEach((item, j) => {
                const leafAngle = startLeafAngle + j * leafAngleStep;
                const lx = x + leafRadius * Math.cos(leafAngle);
                const ly = y + leafRadius * Math.sin(leafAngle);

                svg += `<line class="mindmap-line" x1="${x}" y1="${y}" x2="${lx}" y2="${ly}" style="stroke-width: 1; opacity: 0.5"/>`;
                svg += `<g class="mindmap-node">
                    <rect class="mindmap-node-leaf" x="${lx - 40}" y="${ly - 12}" width="80" height="24" rx="4"/>
                    <text class="mindmap-text mindmap-text-leaf" x="${lx}" y="${ly}">${truncateText(item, 12)}</text>
                </g>`;
            });
        }
    });

    svg += '</svg>';
    canvas.innerHTML = svg;
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 2) + '...';
}

function applyMindmapZoom() {
    const svg = document.querySelector('.mindmap-svg');
    if (svg) {
        svg.style.transform = `scale(${mindmapZoom})`;
    }
}

function exportMindMapAsPNG() {
    const canvas = document.getElementById('mindmap-canvas');
    if (!canvas) return;

    // Create a canvas element and draw the SVG
    const svg = canvas.querySelector('svg');
    if (!svg) return;

    const svgData = new XMLSerializer().serializeToString(svg);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentInfographicData?.title || 'mindmap'}_mindmap.svg`;
    a.click();
    URL.revokeObjectURL(url);
}

/* ========================================
   REPORTS FEATURE
   ======================================== */

let currentReportFormat = 'summary';
let currentReportContent = '';

function setupReports() {
    const reportBtn = document.getElementById('report-btn');
    const reportsModal = document.getElementById('reports-modal');
    const closeBtn = document.getElementById('close-reports-modal-btn');
    const formatBtns = document.querySelectorAll('.format-btn');
    const copyBtn = document.getElementById('copy-report-btn');
    const downloadBtn = document.getElementById('download-report-btn');
    const printBtn = document.getElementById('print-report-btn');

    if (!reportBtn || !reportsModal) return;

    reportBtn.addEventListener('click', () => {
        if (!currentInfographicData) {
            alert('Please generate an infographic first.');
            return;
        }
        reportsModal.classList.add('active');
        generateReport(currentReportFormat);
    });

    closeBtn?.addEventListener('click', () => reportsModal.classList.remove('active'));
    reportsModal.addEventListener('click', (e) => {
        if (e.target === reportsModal) reportsModal.classList.remove('active');
    });

    formatBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            formatBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentReportFormat = btn.dataset.format;
            generateReport(currentReportFormat);
        });
    });

    copyBtn?.addEventListener('click', () => {
        navigator.clipboard.writeText(currentReportContent).then(() => {
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '<span class="material-symbols-rounded">check</span> Copied!';
            setTimeout(() => copyBtn.innerHTML = originalText, 2000);
        });
    });

    downloadBtn?.addEventListener('click', () => {
        const blob = new Blob([currentReportContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentInfographicData?.title || 'report'}_${currentReportFormat}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    });

    printBtn?.addEventListener('click', () => {
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
            <head><title>${currentInfographicData?.title || 'Report'}</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; padding: 2rem; max-width: 800px; margin: 0 auto; }
                h1 { color: #2563eb; margin-bottom: 1rem; }
                h2 { color: #334155; margin-top: 1.5rem; }
                ul { margin-left: 1.5rem; }
                li { margin-bottom: 0.5rem; }
            </style>
            </head>
            <body>${document.getElementById('report-content')?.innerHTML || ''}</body>
            </html>
        `);
        printWindow.document.close();
        printWindow.print();
    });
}

async function generateReport(format) {
    if (!currentInfographicData) return;

    const data = currentInfographicData;
    const reportContainer = document.getElementById('report-content');
    if (!reportContainer) return;

    // Show loading state
    reportContainer.innerHTML = `
        <div class="report-placeholder">
            <span class="material-symbols-rounded rotating">sync</span>
            <p>Generating AI-powered ${format} report...</p>
        </div>
    `;

    // Try AI-powered report generation
    const aiReport = await generateAIReport(format);

    if (aiReport) {
        // Convert markdown to HTML
        const htmlContent = convertMarkdownToHTML(aiReport);
        reportContainer.innerHTML = `<div class="report-text">${htmlContent}</div>`;
        currentReportContent = aiReport;
        return;
    }

    // Fallback to basic generation
    console.log('Using fallback report generation');

    let html = '';
    let text = '';

    switch (format) {
        case 'summary':
            html = `<div class="report-text">
                <h1>${data.title}</h1>
                <p>${data.summary}</p>
                <h2>Key Points</h2>
                <ul>
                    ${(data.sections || []).map(s => `<li><strong>${s.title}</strong></li>`).join('')}
                </ul>
            </div>`;
            text = `${data.title}\n\n${data.summary}\n\nKey Points:\n${(data.sections || []).map(s => `- ${s.title}`).join('\n')}`;
            break;

        case 'detailed':
            html = `<div class="report-text">
                <h1>${data.title}</h1>
                <p>${data.summary}</p>
                ${(data.sections || []).map(s => `
                    <h2>${s.title}</h2>
                    ${formatSectionContent(s)}
                `).join('')}
            </div>`;
            text = `${data.title}\n\n${data.summary}\n\n${(data.sections || []).map(s => `${s.title}\n${formatSectionContentText(s)}`).join('\n\n')}`;
            break;

        case 'bullet':
            html = `<div class="report-text">
                <h1>${data.title}</h1>
                <ul>
                    ${(data.sections || []).map(s => `
                        <li><strong>${s.title}</strong>
                            ${formatSectionAsBullets(s)}
                        </li>
                    `).join('')}
                </ul>
            </div>`;
            text = `${data.title}\n\n${(data.sections || []).map(s => `• ${s.title}\n${formatSectionAsBulletsText(s)}`).join('\n')}`;
            break;

        case 'study-guide':
            html = `<div class="report-text">
                <h1>📚 Study Guide: ${data.title}</h1>
                <p><em>${data.summary}</em></p>
                <h2>Learning Objectives</h2>
                <p>After reviewing this material, you should be able to:</p>
                <ul>
                    ${(data.sections || []).map(s => `<li>Understand ${s.title}</li>`).join('')}
                </ul>
                <h2>Content Review</h2>
                ${(data.sections || []).map((s, i) => `
                    <h3>${i + 1}. ${s.title}</h3>
                    ${formatSectionContent(s)}
                `).join('')}
                <h2>Self-Assessment Questions</h2>
                <ul>
                    ${(data.sections || []).slice(0, 5).map(s => `<li>What are the key points about ${s.title}?</li>`).join('')}
                </ul>
            </div>`;
            text = `STUDY GUIDE: ${data.title}\n\n${data.summary}\n\nLEARNING OBJECTIVES:\n${(data.sections || []).map(s => `- Understand ${s.title}`).join('\n')}\n\nCONTENT:\n${(data.sections || []).map((s, i) => `${i + 1}. ${s.title}\n${formatSectionContentText(s)}`).join('\n\n')}`;
            break;
    }

    reportContainer.innerHTML = html;
    currentReportContent = text;
}

function formatSectionContent(section) {
    if (Array.isArray(section.content)) {
        return `<ul>${section.content.map(c => `<li>${c}</li>`).join('')}</ul>`;
    } else if (typeof section.content === 'object') {
        if (section.content.mnemonic) {
            return `<p><strong>${section.content.mnemonic}</strong>: ${section.content.explanation}</p>`;
        } else if (section.content.center) {
            return `<p><strong>${section.content.center}</strong></p>
                ${section.content.branches ? `<ul>${section.content.branches.map(b => `<li>${b}</li>`).join('')}</ul>` : ''}`;
        } else if (section.content.data) {
            return `<ul>${section.content.data.map(d => `<li>${d.label}: ${d.value}%</li>`).join('')}</ul>`;
        } else if (section.content.headers && section.content.rows) {
            return `<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
                <tr>${section.content.headers.map(h => `<th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">${h}</th>`).join('')}</tr>
                ${section.content.rows.map(row => `<tr>${row.map(cell => `<td style="border: 1px solid #ddd; padding: 8px;">${cell}</td>`).join('')}</tr>`).join('')}
            </table>`;
        }
    }
    return `<p>${section.content}</p>`;
}

function formatSectionContentText(section) {
    if (Array.isArray(section.content)) {
        return section.content.map(c => `  - ${c}`).join('\n');
    } else if (typeof section.content === 'object') {
        if (section.content.mnemonic) {
            return `  ${section.content.mnemonic}: ${section.content.explanation}`;
        } else if (section.content.center) {
            return `  ${section.content.center}\n${section.content.branches ? section.content.branches.map(b => `    - ${b}`).join('\n') : ''}`;
        } else if (section.content.data) {
            return section.content.data.map(d => `  - ${d.label}: ${d.value}%`).join('\n');
        }
    }
    return `  ${section.content}`;
}

function formatSectionAsBullets(section) {
    if (Array.isArray(section.content)) {
        return `<ul>${section.content.map(c => `<li>${c}</li>`).join('')}</ul>`;
    }
    return '';
}

function formatSectionAsBulletsText(section) {
    if (Array.isArray(section.content)) {
        return section.content.map(c => `  ◦ ${c}`).join('\n');
    }
    return '';
}

/* ========================================
   FLASHCARDS FEATURE
   ======================================== */

let flashcards = [];
let currentFlashcardIndex = 0;

function setupFlashcards() {
    const flashcardsBtn = document.getElementById('flashcards-btn');
    const flashcardsModal = document.getElementById('flashcards-modal');
    const closeBtn = document.getElementById('close-flashcards-modal-btn');
    const generateBtn = document.getElementById('generate-flashcards-btn');
    const prevBtn = document.getElementById('prev-card-btn');
    const nextBtn = document.getElementById('next-card-btn');
    const shuffleBtn = document.getElementById('shuffle-cards-btn');
    const flashcard = document.getElementById('current-flashcard');

    if (!flashcardsBtn || !flashcardsModal) return;

    flashcardsBtn.addEventListener('click', () => {
        if (!currentInfographicData) {
            alert('Please generate an infographic first.');
            return;
        }
        flashcardsModal.classList.add('active');
    });

    closeBtn?.addEventListener('click', () => flashcardsModal.classList.remove('active'));
    flashcardsModal.addEventListener('click', (e) => {
        if (e.target === flashcardsModal) flashcardsModal.classList.remove('active');
    });

    generateBtn?.addEventListener('click', generateFlashcards);
    prevBtn?.addEventListener('click', () => navigateFlashcard(-1));
    nextBtn?.addEventListener('click', () => navigateFlashcard(1));
    shuffleBtn?.addEventListener('click', shuffleFlashcards);

    flashcard?.addEventListener('click', () => {
        flashcard.classList.toggle('flipped');
    });
}

async function generateFlashcards() {
    if (!currentInfographicData) return;

    const generateBtn = document.getElementById('generate-flashcards-btn');
    const questionEl = document.getElementById('flashcard-question');

    // Show loading state
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="material-symbols-rounded rotating">sync</span> Generating with AI...';
    }
    if (questionEl) {
        questionEl.textContent = 'Generating AI-powered flashcards...';
    }

    // Try AI-powered flashcards first
    const aiFlashcards = await generateAIFlashcards();

    if (aiFlashcards && aiFlashcards.length > 0) {
        flashcards = aiFlashcards;
        currentFlashcardIndex = 0;
        renderFlashcard();
        updateFlashcardCounter();
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<span class="material-symbols-rounded">auto_fix_high</span> Regenerate';
        }
        return;
    }

    // Fallback to basic generation
    console.log('Using fallback flashcard generation');
    const data = currentInfographicData;
    flashcards = [];

    // Create flashcards from sections
    if (data.sections) {
        data.sections.forEach(section => {
            // Main section question
            flashcards.push({
                question: `What are the key points about ${section.title}?`,
                answer: formatFlashcardAnswer(section)
            });

            // Additional cards for specific content
            if (Array.isArray(section.content) && section.content.length > 3) {
                section.content.forEach((item, i) => {
                    if (i < 5) { // Limit per section
                        flashcards.push({
                            question: `In ${section.title}: Explain "${truncateText(item, 50)}"`,
                            answer: item
                        });
                    }
                });
            }

            if (section.content?.mnemonic) {
                flashcards.push({
                    question: `What does the mnemonic "${section.content.mnemonic}" stand for?`,
                    answer: section.content.explanation
                });
            }
        });
    }

    // Summary card
    flashcards.push({
        question: `Summarize: ${data.title}`,
        answer: data.summary
    });

    currentFlashcardIndex = 0;
    renderFlashcard();
    updateFlashcardCounter();

    if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<span class="material-symbols-rounded">auto_fix_high</span> Regenerate';
    }
}

function formatFlashcardAnswer(section) {
    if (Array.isArray(section.content)) {
        return section.content.slice(0, 5).join('\n• ');
    } else if (typeof section.content === 'object') {
        if (section.content.mnemonic) {
            return `${section.content.mnemonic}: ${section.content.explanation}`;
        } else if (section.content.center) {
            return `${section.content.center}: ${(section.content.branches || []).join(', ')}`;
        }
    }
    return String(section.content || '');
}

function renderFlashcard() {
    if (flashcards.length === 0) return;

    const card = flashcards[currentFlashcardIndex];
    const questionEl = document.getElementById('flashcard-question');
    const answerEl = document.getElementById('flashcard-answer');
    const flashcard = document.getElementById('current-flashcard');

    if (questionEl) questionEl.textContent = card.question;
    if (answerEl) answerEl.textContent = card.answer;
    if (flashcard) flashcard.classList.remove('flipped');
}

function navigateFlashcard(direction) {
    if (flashcards.length === 0) return;

    currentFlashcardIndex += direction;
    if (currentFlashcardIndex < 0) currentFlashcardIndex = flashcards.length - 1;
    if (currentFlashcardIndex >= flashcards.length) currentFlashcardIndex = 0;

    renderFlashcard();
    updateFlashcardCounter();
}

function updateFlashcardCounter() {
    const counter = document.getElementById('flashcard-counter');
    if (counter) {
        counter.textContent = flashcards.length > 0
            ? `${currentFlashcardIndex + 1} / ${flashcards.length}`
            : '0 / 0';
    }
}

function shuffleFlashcards() {
    for (let i = flashcards.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [flashcards[i], flashcards[j]] = [flashcards[j], flashcards[i]];
    }
    currentFlashcardIndex = 0;
    renderFlashcard();
    updateFlashcardCounter();
}

/* ========================================
   QUIZ FEATURE
   ======================================== */

let quizQuestions = [];
let currentQuestionIndex = 0;
let quizScore = 0;
let quizAnswered = false;

function setupQuiz() {
    const quizBtn = document.getElementById('quiz-btn');
    const quizModal = document.getElementById('quiz-modal');
    const closeBtn = document.getElementById('close-quiz-modal-btn');
    const startBtn = document.getElementById('start-quiz-btn');
    const nextBtn = document.getElementById('next-question-btn');
    const retakeBtn = document.getElementById('retake-quiz-btn');

    if (!quizBtn || !quizModal) return;

    quizBtn.addEventListener('click', () => {
        if (!currentInfographicData) {
            alert('Please generate an infographic first.');
            return;
        }
        quizModal.classList.add('active');
        resetQuiz();
    });

    closeBtn?.addEventListener('click', () => quizModal.classList.remove('active'));
    quizModal.addEventListener('click', (e) => {
        if (e.target === quizModal) quizModal.classList.remove('active');
    });

    startBtn?.addEventListener('click', startQuiz);
    nextBtn?.addEventListener('click', nextQuestion);
    retakeBtn?.addEventListener('click', startQuiz);
}

function generateQuizQuestions() {
    if (!currentInfographicData) return;

    const data = currentInfographicData;
    quizQuestions = [];

    if (data.sections) {
        data.sections.forEach(section => {
            if (Array.isArray(section.content) && section.content.length >= 2) {
                // Multiple choice from content
                const correctAnswer = section.content[0];
                const wrongAnswers = getRandomWrongAnswers(data.sections, section, correctAnswer);

                quizQuestions.push({
                    question: `Which of the following is true about ${section.title}?`,
                    options: shuffleArray([correctAnswer, ...wrongAnswers]),
                    correctAnswer: correctAnswer
                });
            }

            if (section.content?.mnemonic) {
                quizQuestions.push({
                    question: `What does the mnemonic "${section.content.mnemonic}" help remember?`,
                    options: shuffleArray([
                        section.content.explanation,
                        `A ${section.title} classification system`,
                        `Diagnostic criteria`,
                        `Treatment protocols`
                    ]),
                    correctAnswer: section.content.explanation
                });
            }
        });

        // Add general knowledge questions
        quizQuestions.push({
            question: `What is the main topic of this infographic?`,
            options: shuffleArray([
                data.title,
                'General Ophthalmology',
                'Clinical Examination',
                'Surgical Techniques'
            ]),
            correctAnswer: data.title
        });
    }

    // Limit to 10 questions max
    quizQuestions = quizQuestions.slice(0, 10);
}

function getRandomWrongAnswers(sections, currentSection, correctAnswer) {
    const wrongAnswers = [];

    sections.forEach(s => {
        if (s !== currentSection && Array.isArray(s.content)) {
            s.content.forEach(item => {
                if (item !== correctAnswer && wrongAnswers.length < 3) {
                    wrongAnswers.push(item);
                }
            });
        }
    });

    while (wrongAnswers.length < 3) {
        wrongAnswers.push(`Option ${wrongAnswers.length + 1}`);
    }

    return wrongAnswers.slice(0, 3);
}

function shuffleArray(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

function resetQuiz() {
    currentQuestionIndex = 0;
    quizScore = 0;
    quizAnswered = false;

    document.getElementById('quiz-container').style.display = 'block';
    document.getElementById('quiz-results').style.display = 'none';
    document.getElementById('start-quiz-btn').style.display = 'flex';
    document.getElementById('next-question-btn').style.display = 'none';
    document.getElementById('quiz-feedback').style.display = 'none';
    document.getElementById('quiz-question').textContent = 'Click "Start Quiz" to begin';
    document.getElementById('quiz-options').innerHTML = '';
    document.getElementById('quiz-progress-bar').style.width = '0%';
    updateQuizScore();
}

async function startQuiz() {
    const startBtn = document.getElementById('start-quiz-btn');
    const questionEl = document.getElementById('quiz-question');

    // Show loading state
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="material-symbols-rounded rotating">sync</span> Generating AI Quiz...';
    }
    if (questionEl) {
        questionEl.textContent = 'Generating AI-powered quiz questions...';
    }

    // Try AI-powered quiz first
    const aiQuiz = await generateAIQuiz();

    if (aiQuiz && aiQuiz.length > 0) {
        quizQuestions = aiQuiz;
        console.log(`Generated ${quizQuestions.length} AI quiz questions`);
    } else {
        // Fallback to basic quiz generation
        console.log('Using fallback quiz generation');
        generateQuizQuestions();
    }

    currentQuestionIndex = 0;
    quizScore = 0;
    quizAnswered = false;

    document.getElementById('quiz-results').style.display = 'none';
    document.getElementById('quiz-container').style.display = 'block';

    if (startBtn) {
        startBtn.style.display = 'none';
        startBtn.disabled = false;
        startBtn.innerHTML = '<span class="material-symbols-rounded">play_arrow</span> Start Quiz';
    }

    renderQuizQuestion();
    updateQuizScore();
}

function renderQuizQuestion() {
    if (quizQuestions.length === 0) return;

    const question = quizQuestions[currentQuestionIndex];
    const questionEl = document.getElementById('quiz-question');
    const optionsEl = document.getElementById('quiz-options');
    const progressBar = document.getElementById('quiz-progress-bar');
    const feedback = document.getElementById('quiz-feedback');

    questionEl.textContent = question.question;
    feedback.style.display = 'none';
    quizAnswered = false;

    const progress = ((currentQuestionIndex) / quizQuestions.length) * 100;
    progressBar.style.width = `${progress}%`;

    optionsEl.innerHTML = question.options.map((opt, i) => `
        <div class="quiz-option" data-answer="${opt}">
            <span class="quiz-option-letter">${String.fromCharCode(65 + i)}</span>
            <span>${truncateText(opt, 100)}</span>
        </div>
    `).join('');

    // Add click handlers
    optionsEl.querySelectorAll('.quiz-option').forEach(option => {
        option.addEventListener('click', () => selectQuizAnswer(option, question.correctAnswer));
    });
}

function selectQuizAnswer(optionEl, correctAnswer) {
    if (quizAnswered) return;
    quizAnswered = true;

    const selectedAnswer = optionEl.dataset.answer;
    const isCorrect = selectedAnswer === correctAnswer;
    const feedback = document.getElementById('quiz-feedback');
    const feedbackIcon = document.getElementById('feedback-icon');
    const feedbackText = document.getElementById('feedback-text');
    const nextBtn = document.getElementById('next-question-btn');

    // Mark selected option
    optionEl.classList.add(isCorrect ? 'correct' : 'incorrect');

    // Show correct answer if wrong
    if (!isCorrect) {
        document.querySelectorAll('.quiz-option').forEach(opt => {
            if (opt.dataset.answer === correctAnswer) {
                opt.classList.add('correct');
            }
        });
    } else {
        quizScore++;
    }

    // Show feedback with explanation if available
    feedback.style.display = 'flex';
    feedback.className = `quiz-feedback ${isCorrect ? 'correct' : 'incorrect'}`;
    feedbackIcon.textContent = isCorrect ? 'check_circle' : 'cancel';

    const currentQuestion = quizQuestions[currentQuestionIndex];
    let feedbackMessage = isCorrect ? 'Correct!' : `Incorrect. The correct answer was: "${truncateText(correctAnswer, 50)}"`;

    // Add explanation if available (from AI-generated questions)
    if (currentQuestion.explanation) {
        feedbackMessage += `\n\n💡 ${currentQuestion.explanation}`;
    }

    feedbackText.textContent = feedbackMessage;

    nextBtn.style.display = 'flex';
    updateQuizScore();
}

function nextQuestion() {
    currentQuestionIndex++;
    document.getElementById('next-question-btn').style.display = 'none';

    if (currentQuestionIndex >= quizQuestions.length) {
        showQuizResults();
    } else {
        renderQuizQuestion();
    }
}

function showQuizResults() {
    document.getElementById('quiz-container').style.display = 'none';
    document.getElementById('quiz-results').style.display = 'flex';

    const percentage = Math.round((quizScore / quizQuestions.length) * 100);
    document.getElementById('results-percentage').textContent = `${percentage}%`;

    let message = '';
    if (percentage >= 90) message = '🌟 Excellent! You\'ve mastered this topic!';
    else if (percentage >= 70) message = '👍 Great job! Keep studying to perfect your knowledge.';
    else if (percentage >= 50) message = '📚 Good effort! Review the material and try again.';
    else message = '💪 Keep practicing! Review the infographic and retake the quiz.';

    document.getElementById('results-message').textContent = message;
}

function updateQuizScore() {
    const scoreEl = document.getElementById('quiz-score');
    if (scoreEl) {
        scoreEl.textContent = `Score: ${quizScore}/${quizQuestions.length || 0}`;
    }
}

/* ========================================
   SLIDE DECK FEATURE
   ======================================== */

let slides = [];
let currentSlideIndex = 0;

function setupSlideDeck() {
    const slideBtn = document.getElementById('slidedeck-btn');
    const slideModal = document.getElementById('slidedeck-modal');
    const closeBtn = document.getElementById('close-slidedeck-modal-btn');
    const generateBtn = document.getElementById('generate-slides-btn');
    const prevBtn = document.getElementById('slide-prev-btn');
    const nextBtn = document.getElementById('slide-next-btn');
    const presentBtn = document.getElementById('present-slides-btn');
    const exportBtn = document.getElementById('export-slides-btn');

    if (!slideBtn || !slideModal) return;

    slideBtn.addEventListener('click', () => {
        if (!currentInfographicData) {
            alert('Please generate an infographic first.');
            return;
        }
        slideModal.classList.add('active');
    });

    closeBtn?.addEventListener('click', () => slideModal.classList.remove('active'));
    slideModal.addEventListener('click', (e) => {
        if (e.target === slideModal) slideModal.classList.remove('active');
    });

    generateBtn?.addEventListener('click', generateSlides);
    prevBtn?.addEventListener('click', () => navigateSlide(-1));
    nextBtn?.addEventListener('click', () => navigateSlide(1));
    presentBtn?.addEventListener('click', enterPresentationMode);
    exportBtn?.addEventListener('click', exportSlidesAsHTML);
}

function generateSlides() {
    if (!currentInfographicData) return;

    const data = currentInfographicData;
    slides = [];

    // Title slide
    slides.push({
        type: 'title',
        title: data.title,
        subtitle: data.summary
    });

    // Content slides from sections
    if (data.sections) {
        data.sections.forEach(section => {
            slides.push({
                type: 'section',
                title: section.title
            });

            slides.push({
                type: 'content',
                title: section.title,
                content: section.content,
                contentType: section.type
            });
        });
    }

    // Thank you slide
    slides.push({
        type: 'end',
        title: 'Thank You',
        subtitle: 'Questions?'
    });

    currentSlideIndex = 0;
    renderSlide();
    renderThumbnails();
    updateSlideIndicator();

    const presentBtn = document.getElementById('present-slides-btn');
    const exportBtn = document.getElementById('export-slides-btn');
    if (presentBtn) presentBtn.style.display = 'flex';
    if (exportBtn) exportBtn.style.display = 'flex';
}

function renderSlide() {
    if (slides.length === 0) return;

    const slideContent = document.getElementById('slide-content');
    const slide = slides[currentSlideIndex];

    slideContent.className = 'slide-content';

    if (slide.type === 'title') {
        slideContent.classList.add('title-slide');
        slideContent.innerHTML = `
            <h1>${slide.title}</h1>
            <p>${slide.subtitle || ''}</p>
        `;
    } else if (slide.type === 'section') {
        slideContent.classList.add('section-slide');
        slideContent.innerHTML = `<h2>${slide.title}</h2>`;
    } else if (slide.type === 'end') {
        slideContent.classList.add('title-slide');
        slideContent.innerHTML = `
            <h1>${slide.title}</h1>
            <p>${slide.subtitle || ''}</p>
        `;
    } else {
        slideContent.classList.add('content-slide');
        let contentHtml = '';

        if (Array.isArray(slide.content)) {
            contentHtml = `<ul>${slide.content.map(c => `<li>${c}</li>`).join('')}</ul>`;
        } else if (typeof slide.content === 'object') {
            if (slide.content.mnemonic) {
                contentHtml = `<p><strong style="font-size: 2rem; color: #8b5cf6;">${slide.content.mnemonic}</strong></p>
                    <p>${slide.content.explanation}</p>`;
            } else if (slide.content.center) {
                contentHtml = `<p><strong>${slide.content.center}</strong></p>`;
                if (slide.content.branches) {
                    contentHtml += `<ul>${slide.content.branches.map(b => `<li>${b}</li>`).join('')}</ul>`;
                }
            } else if (slide.content.data) {
                contentHtml = `<ul>${slide.content.data.map(d => `<li>${d.label}: ${d.value}%</li>`).join('')}</ul>`;
            }
        } else {
            contentHtml = `<p>${slide.content}</p>`;
        }

        slideContent.innerHTML = `
            <h3>${slide.title}</h3>
            ${contentHtml}
        `;
    }

    // Update thumbnail active state
    document.querySelectorAll('.slide-thumbnail').forEach((thumb, i) => {
        thumb.classList.toggle('active', i === currentSlideIndex);
    });
}

function renderThumbnails() {
    const container = document.getElementById('slide-thumbnails');
    if (!container) return;

    container.innerHTML = slides.map((slide, i) => `
        <div class="slide-thumbnail ${i === currentSlideIndex ? 'active' : ''}" data-index="${i}">
            ${slide.type === 'title' ? '📌 Title' : slide.type === 'section' ? '📂 Section' : slide.type === 'end' ? '🎉 End' : truncateText(slide.title, 15)}
        </div>
    `).join('');

    container.querySelectorAll('.slide-thumbnail').forEach(thumb => {
        thumb.addEventListener('click', () => {
            currentSlideIndex = parseInt(thumb.dataset.index);
            renderSlide();
            updateSlideIndicator();
        });
    });
}

function navigateSlide(direction) {
    if (slides.length === 0) return;

    currentSlideIndex += direction;
    if (currentSlideIndex < 0) currentSlideIndex = slides.length - 1;
    if (currentSlideIndex >= slides.length) currentSlideIndex = 0;

    renderSlide();
    updateSlideIndicator();
}

function updateSlideIndicator() {
    const indicator = document.getElementById('slide-indicator');
    if (indicator) {
        indicator.textContent = slides.length > 0
            ? `Slide ${currentSlideIndex + 1} of ${slides.length}`
            : 'Slide 0 of 0';
    }
}

function enterPresentationMode() {
    if (slides.length === 0) return;

    const presentationDiv = document.createElement('div');
    presentationDiv.className = 'presentation-mode';
    presentationDiv.id = 'presentation-mode';

    presentationDiv.innerHTML = `
        <div class="slide-frame">
            <div class="slide-content" id="presentation-slide-content"></div>
        </div>
        <div class="presentation-controls">
            <button id="pres-prev"><span class="material-symbols-rounded">chevron_left</span></button>
            <button id="pres-exit"><span class="material-symbols-rounded">close</span></button>
            <button id="pres-next"><span class="material-symbols-rounded">chevron_right</span></button>
        </div>
    `;

    document.body.appendChild(presentationDiv);
    renderPresentationSlide();

    document.getElementById('pres-prev').addEventListener('click', () => {
        navigateSlide(-1);
        renderPresentationSlide();
    });
    document.getElementById('pres-next').addEventListener('click', () => {
        navigateSlide(1);
        renderPresentationSlide();
    });
    document.getElementById('pres-exit').addEventListener('click', exitPresentationMode);

    // Keyboard navigation
    document.addEventListener('keydown', handlePresentationKeydown);
}

function renderPresentationSlide() {
    const content = document.getElementById('presentation-slide-content');
    if (!content) return;

    const slide = slides[currentSlideIndex];
    content.className = 'slide-content';

    if (slide.type === 'title' || slide.type === 'end') {
        content.classList.add('title-slide');
        content.innerHTML = `
            <h1>${slide.title}</h1>
            <p>${slide.subtitle || ''}</p>
        `;
    } else if (slide.type === 'section') {
        content.classList.add('section-slide');
        content.innerHTML = `<h2>${slide.title}</h2>`;
    } else {
        content.classList.add('content-slide');
        let contentHtml = '';

        if (Array.isArray(slide.content)) {
            contentHtml = `<ul>${slide.content.map(c => `<li>${c}</li>`).join('')}</ul>`;
        } else if (typeof slide.content === 'object') {
            if (slide.content.mnemonic) {
                contentHtml = `<p><strong style="font-size: 3rem; color: #8b5cf6;">${slide.content.mnemonic}</strong></p>
                    <p>${slide.content.explanation}</p>`;
            } else if (slide.content.center) {
                contentHtml = `<p><strong>${slide.content.center}</strong></p>
                    ${slide.content.branches ? `<ul>${slide.content.branches.map(b => `<li>${b}</li>`).join('')}</ul>` : ''}`;
            }
        } else {
            contentHtml = `<p>${slide.content}</p>`;
        }

        content.innerHTML = `
            <h3>${slide.title}</h3>
            ${contentHtml}
        `;
    }
}

function handlePresentationKeydown(e) {
    if (!document.getElementById('presentation-mode')) return;

    if (e.key === 'ArrowRight' || e.key === ' ') {
        navigateSlide(1);
        renderPresentationSlide();
    } else if (e.key === 'ArrowLeft') {
        navigateSlide(-1);
        renderPresentationSlide();
    } else if (e.key === 'Escape') {
        exitPresentationMode();
    }
}

function exitPresentationMode() {
    const presentation = document.getElementById('presentation-mode');
    if (presentation) {
        presentation.remove();
    }
    document.removeEventListener('keydown', handlePresentationKeydown);
}

function exportSlidesAsHTML() {
    if (slides.length === 0) return;

    let html = `<!DOCTYPE html>
<html>
<head>
    <title>${currentInfographicData.title} - Presentation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; }
        .slide { width: 100vw; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4rem; }
        .title-slide { background: linear-gradient(135deg, #1e293b, #334155); color: white; text-align: center; }
        .section-slide { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; text-align: center; }
        .content-slide { background: white; color: #1f2937; align-items: flex-start; }
        h1 { font-size: 3.5rem; margin-bottom: 1rem; }
        h2 { font-size: 3rem; }
        h3 { font-size: 2rem; color: #3b82f6; margin-bottom: 2rem; width: 100%; }
        p { font-size: 1.5rem; opacity: 0.9; }
        ul { font-size: 1.3rem; line-height: 2; list-style: none; }
        li::before { content: "▸ "; color: #3b82f6; }
        @media print { .slide { page-break-after: always; } }
    </style>
</head>
<body>
${slides.map(slide => {
        if (slide.type === 'title' || slide.type === 'end') {
            return `<div class="slide title-slide">
            <h1>${slide.title}</h1>
            <p>${slide.subtitle || ''}</p>
        </div>`;
        } else if (slide.type === 'section') {
            return `<div class="slide section-slide">
            <h2>${slide.title}</h2>
        </div>`;
        } else {
            let content = '';
            if (Array.isArray(slide.content)) {
                content = `<ul>${slide.content.map(c => `<li>${c}</li>`).join('')}</ul>`;
            } else if (typeof slide.content === 'string') {
                content = `<p>${slide.content}</p>`;
            }
            return `<div class="slide content-slide">
            <h3>${slide.title}</h3>
            ${content}
        </div>`;
        }
    }).join('\n')}
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentInfographicData.title.replace(/[^a-z0-9]/gi, '_')}_slides.html`;
    a.click();
    URL.revokeObjectURL(url);
}

/* ========================================
   COMMUNITY HUB FUNCTIONALITY
   ======================================== */

function setupCommunityHub() {
    const communityBtn = document.getElementById('community-btn');
    const submitCommunityBtn = document.getElementById('submit-community-btn');
    const communityModal = document.getElementById('community-modal');
    const submitModal = document.getElementById('submit-community-modal');
    const previewModal = document.getElementById('community-preview-modal');

    // Close buttons
    const closeCommBtn = document.getElementById('close-community-modal-btn');
    const closeSubmitBtn = document.getElementById('close-submit-modal-btn');
    const closePreviewBtn = document.getElementById('close-preview-modal-btn');
    const cancelSubmitBtn = document.getElementById('cancel-submit-btn');

    // Refresh button
    const refreshBtn = document.getElementById('refresh-community-btn');

    // Tabs
    const tabs = document.querySelectorAll('.community-tab');
    const pendingContent = document.getElementById('pending-content');
    const approvedContent = document.getElementById('approved-content');

    // Lists and counts
    const pendingList = document.getElementById('pending-submissions-list');
    const approvedList = document.getElementById('approved-submissions-list');
    const pendingEmpty = document.getElementById('pending-empty');
    const approvedEmpty = document.getElementById('approved-empty');
    const pendingCount = document.getElementById('pending-count');
    const approvedCount = document.getElementById('approved-count');
    const communityCountBadge = document.getElementById('community-count-badge');

    // Submit form elements
    const submitterNameInput = document.getElementById('submitter-name');
    const submitPreviewTitle = document.getElementById('submit-preview-title');
    const submitPreviewSummary = document.getElementById('submit-preview-summary');
    const confirmSubmitBtn = document.getElementById('confirm-submit-btn');

    // Preview elements
    const previewTitle = document.getElementById('preview-title');
    const previewAuthor = document.getElementById('preview-author');
    const previewContainer = document.getElementById('preview-infographic-container');
    const previewLikeBtn = document.getElementById('preview-like-btn');
    const previewDownloadBtn = document.getElementById('preview-download-btn');

    let currentPreviewId = null;
    let cachedSubmissions = { submissions: [], approved: [] };

    // Check if CommunitySubmissions module is loaded
    function isCommunityModuleLoaded() {
        return typeof window.CommunitySubmissions !== 'undefined';
    }

    // Open Community Modal
    async function openCommunityModal() {
        if (!isCommunityModuleLoaded()) {
            alert('Community module not loaded. Please refresh the page.');
            return;
        }

        communityModal.classList.add('active');
        await loadCommunitySubmissions();
    }

    // Load submissions
    async function loadCommunitySubmissions() {
        try {
            const data = await CommunitySubmissions.getAll();
            cachedSubmissions = data;

            const pending = data.submissions || [];
            const approved = data.approved || [];

            // Update counts
            pendingCount.textContent = pending.length;
            approvedCount.textContent = approved.length;

            // Update badge
            if (pending.length > 0) {
                communityCountBadge.textContent = pending.length;
                communityCountBadge.style.display = 'inline';
            } else {
                communityCountBadge.style.display = 'none';
            }

            // Render pending
            renderSubmissionsList(pending, pendingList, pendingEmpty, false);

            // Render approved
            renderSubmissionsList(approved, approvedList, approvedEmpty, true);

        } catch (err) {
            console.error('Error loading community submissions:', err);
        }
    }

    // Render submissions list
    function renderSubmissionsList(submissions, container, emptyElement, isApproved) {
        if (submissions.length === 0) {
            container.innerHTML = '';
            emptyElement.style.display = 'flex';
            return;
        }

        emptyElement.style.display = 'none';
        container.innerHTML = submissions.map(s => CommunitySubmissions.generateCardHTML(s, false)).join('');
    }

    // Tab switching
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const tabName = tab.dataset.tab;
            if (tabName === 'pending') {
                pendingContent.style.display = 'block';
                approvedContent.style.display = 'none';
            } else {
                pendingContent.style.display = 'none';
                approvedContent.style.display = 'block';
            }
        });
    });

    // Open Submit Modal
    function openSubmitModal() {
        if (!currentInfographicData) {
            alert('Please generate an infographic first before submitting to the community.');
            return;
        }

        // Update preview
        submitPreviewTitle.textContent = currentInfographicData.title || 'Untitled Infographic';
        submitPreviewSummary.textContent = currentInfographicData.summary || 'No summary available.';

        // Clear previous name
        submitterNameInput.value = localStorage.getItem('community_username') || '';

        submitModal.classList.add('active');
    }

    // Submit to community
    async function handleSubmitToCommunity() {
        const userName = submitterNameInput.value.trim();

        if (!userName) {
            alert('Please enter your name.');
            submitterNameInput.focus();
            return;
        }

        if (!currentInfographicData) {
            alert('No infographic data to submit.');
            return;
        }

        // Save username for future submissions
        localStorage.setItem('community_username', userName);

        // Show loading state
        const originalText = confirmSubmitBtn.innerHTML;
        confirmSubmitBtn.innerHTML = '<span class="material-symbols-rounded">sync</span> Submitting...';
        confirmSubmitBtn.disabled = true;

        try {
            const result = await CommunitySubmissions.submit(currentInfographicData, userName);

            if (result.success) {
                alert(result.message);
                submitModal.classList.remove('active');

                // Refresh community list if modal is open
                if (communityModal.classList.contains('active')) {
                    await loadCommunitySubmissions();
                }
            } else {
                alert('Submission failed: ' + result.message);
            }
        } catch (err) {
            console.error('Submission error:', err);
            alert('An error occurred while submitting. Please try again.');
        } finally {
            confirmSubmitBtn.innerHTML = originalText;
            confirmSubmitBtn.disabled = false;
        }
    }

    // Preview submission
    window.handlePreviewSubmission = async function (submissionId) {
        currentPreviewId = submissionId;

        // Find submission
        let submission = (cachedSubmissions.submissions || []).find(s => s.id === submissionId);
        if (!submission) {
            submission = (cachedSubmissions.approved || []).find(s => s.id === submissionId);
        }

        if (!submission) {
            alert('Could not find submission.');
            return;
        }

        // Update preview modal
        previewTitle.textContent = submission.title;
        previewAuthor.innerHTML = `<span class="material-symbols-rounded">person</span> ${submission.userName}`;

        // Render the infographic preview (simplified)
        if (submission.data) {
            previewContainer.innerHTML = `
                <div style="background: white; padding: 2rem; border-radius: 12px;">
                    <h2 style="margin-bottom: 1rem; color: #1f2937;">${submission.title}</h2>
                    <p style="color: #6b7280; margin-bottom: 1.5rem;">${submission.summary || ''}</p>
                    ${submission.data.sections ? `
                        <div style="display: grid; gap: 1rem;">
                            ${submission.data.sections.slice(0, 3).map(section => `
                                <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #3b82f6;">
                                    <h4 style="margin: 0 0 0.5rem 0; color: #334155;">${section.title || 'Section'}</h4>
                                    <p style="margin: 0; font-size: 0.9rem; color: #64748b;">
                                        ${Array.isArray(section.content)
                    ? section.content.slice(0, 3).join(', ') + (section.content.length > 3 ? '...' : '')
                    : (typeof section.content === 'string' ? section.content.substring(0, 150) : 'Content available')}
                                    </p>
                                </div>
                            `).join('')}
                            ${submission.data.sections.length > 3 ? `
                                <p style="text-align: center; color: #9ca3af; font-style: italic;">
                                    ...and ${submission.data.sections.length - 3} more sections
                                </p>
                            ` : ''}
                        </div>
                    ` : '<p style="color: #9ca3af;">Full content available after download.</p>'}
                </div>
            `;
        } else {
            previewContainer.innerHTML = '<p style="text-align: center; color: #9ca3af;">Preview not available.</p>';
        }

        previewModal.classList.add('active');
    };

    // Like submission
    window.handleLikeSubmission = async function (submissionId) {
        try {
            const result = await CommunitySubmissions.like(submissionId);

            if (result.success) {
                // Update the like count in UI
                const card = document.querySelector(`.community-card[data-id="${submissionId}"]`);
                if (card) {
                    const likesCount = card.querySelector('.likes-count');
                    if (likesCount) {
                        likesCount.innerHTML = `<span class="material-symbols-rounded">favorite</span> ${result.likes}`;
                    }
                }
            } else {
                alert(result.message || 'Could not like submission.');
            }
        } catch (err) {
            console.error('Like error:', err);
        }
    };

    // Download submission to local library
    window.handleDownloadSubmission = async function (submissionId) {
        try {
            const result = await CommunitySubmissions.downloadToLibrary(submissionId);

            if (result.success) {
                alert(result.message);
            } else {
                alert(result.message || 'Could not download.');
            }
        } catch (err) {
            console.error('Download error:', err);
            alert('An error occurred while downloading.');
        }
    };

    // Event Listeners
    if (communityBtn) {
        communityBtn.addEventListener('click', openCommunityModal);
    }

    if (submitCommunityBtn) {
        submitCommunityBtn.addEventListener('click', openSubmitModal);
    }

    if (closeCommBtn) {
        closeCommBtn.addEventListener('click', () => {
            communityModal.classList.remove('active');
        });
    }

    if (closeSubmitBtn) {
        closeSubmitBtn.addEventListener('click', () => {
            submitModal.classList.remove('active');
        });
    }

    if (cancelSubmitBtn) {
        cancelSubmitBtn.addEventListener('click', () => {
            submitModal.classList.remove('active');
        });
    }

    if (closePreviewBtn) {
        closePreviewBtn.addEventListener('click', () => {
            previewModal.classList.remove('active');
            currentPreviewId = null;
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            refreshBtn.classList.add('rotating');
            await loadCommunitySubmissions();
            setTimeout(() => refreshBtn.classList.remove('rotating'), 500);
        });
    }

    if (confirmSubmitBtn) {
        confirmSubmitBtn.addEventListener('click', handleSubmitToCommunity);
    }

    if (previewLikeBtn) {
        previewLikeBtn.addEventListener('click', () => {
            if (currentPreviewId) {
                handleLikeSubmission(currentPreviewId);
            }
        });
    }

    if (previewDownloadBtn) {
        previewDownloadBtn.addEventListener('click', () => {
            if (currentPreviewId) {
                // Only admin can add community submissions to library
                const password = prompt('Enter admin password to add this infographic to library:');
                if (password !== '309030') {
                    if (password !== null) {
                        alert('Only administrators can add community submissions to the library.');
                    }
                    return;
                }
                handleDownloadSubmission(currentPreviewId);
                previewModal.classList.remove('active');
            }
        });
    }

    // Close modals on overlay click
    [communityModal, submitModal, previewModal].forEach(modal => {
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('active');
                }
            });
        }
    });

    console.log('Community Hub initialized.');
}

/* ========================================
   BACKGROUND MUSIC PLAYER
   ======================================== */

function setupMusicPlayer() {
    const musicToggle = document.getElementById('music-toggle');
    const musicPanel = document.getElementById('music-panel');
    const musicIcon = document.getElementById('music-icon');
    const musicAudio = document.getElementById('music-audio');
    const playPauseBtn = document.getElementById('music-play-pause');
    const volumeSlider = document.getElementById('music-volume');
    const musicStatus = document.getElementById('music-status');
    const stationBtns = document.querySelectorAll('.station-btn');

    if (!musicToggle || !musicAudio) return;

    // Radio station URLs (public streams)
    const stations = {
        classical: {
            name: 'Classical FM',
            // Using Classic FM UK stream
            url: 'https://media-ice.musicradio.com/ClassicFMMP3',
            fallback: 'https://stream.classicfm.com/classicfm.mp3'
        },
        quran: {
            name: 'Quran - Al Minshawi',
            // Correct Quran radio stream - Mohammed Siddiq Al-Minshawi (Mujawwad)
            url: 'https://backup.qurango.net/radio/mohammed_siddiq_alminshawi_mojawwad',
            fallback: 'https://qurango.net/radio/mohammed_siddiq_alminshawi_mojawwad'
        }
    };

    let currentStation = null;
    let isPlaying = false;

    // Toggle panel
    musicToggle.addEventListener('click', () => {
        musicPanel.classList.toggle('hidden');
    });

    // Close panel when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.music-player')) {
            musicPanel.classList.add('hidden');
        }
    });

    // Station selection
    stationBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const stationId = btn.dataset.station;
            const station = stations[stationId];

            if (!station) return;

            // Update UI
            stationBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            currentStation = stationId;
            playPauseBtn.disabled = false;

            // Set status
            musicStatus.textContent = `Loading ${station.name}...`;
            musicStatus.className = 'music-status loading';

            // Try to load the stream
            try {
                musicAudio.src = station.url;
                musicAudio.volume = volumeSlider.value / 100;

                await musicAudio.play();
                isPlaying = true;
                updatePlayPauseIcon();
                musicStatus.textContent = `Playing: ${station.name}`;
                musicStatus.className = 'music-status playing';
                musicToggle.classList.add('playing');

            } catch (err) {
                console.log('Primary stream failed, trying fallback...', err);

                // Try fallback
                try {
                    musicAudio.src = station.fallback;
                    await musicAudio.play();
                    isPlaying = true;
                    updatePlayPauseIcon();
                    musicStatus.textContent = `Playing: ${station.name}`;
                    musicStatus.className = 'music-status playing';
                    musicToggle.classList.add('playing');

                } catch (fallbackErr) {
                    console.error('Fallback also failed:', fallbackErr);
                    musicStatus.textContent = 'Stream unavailable. Try again later.';
                    musicStatus.className = 'music-status error';
                    isPlaying = false;
                    updatePlayPauseIcon();
                }
            }
        });
    });

    // Play/Pause
    playPauseBtn.addEventListener('click', () => {
        if (!currentStation) return;

        if (isPlaying) {
            musicAudio.pause();
            isPlaying = false;
            musicStatus.textContent = 'Paused';
            musicStatus.className = 'music-status';
            musicToggle.classList.remove('playing');
        } else {
            musicAudio.play().then(() => {
                isPlaying = true;
                musicStatus.textContent = `Playing: ${stations[currentStation].name}`;
                musicStatus.className = 'music-status playing';
                musicToggle.classList.add('playing');
            }).catch(err => {
                console.error('Play failed:', err);
                musicStatus.textContent = 'Playback failed';
                musicStatus.className = 'music-status error';
            });
        }
        updatePlayPauseIcon();
    });

    function updatePlayPauseIcon() {
        const icon = playPauseBtn.querySelector('.material-symbols-rounded');
        if (icon) {
            icon.textContent = isPlaying ? 'pause' : 'play_arrow';
        }
        musicIcon.textContent = isPlaying ? 'music_note' : 'music_off';
    }

    // Volume control
    volumeSlider.addEventListener('input', () => {
        musicAudio.volume = volumeSlider.value / 100;
    });

    // Handle audio errors
    musicAudio.addEventListener('error', () => {
        musicStatus.textContent = 'Stream error. Try another station.';
        musicStatus.className = 'music-status error';
        isPlaying = false;
        updatePlayPauseIcon();
        musicToggle.classList.remove('playing');
    });

    // Handle stream end/stall
    musicAudio.addEventListener('stalled', () => {
        musicStatus.textContent = 'Buffering...';
        musicStatus.className = 'music-status loading';
    });

    musicAudio.addEventListener('playing', () => {
        if (currentStation) {
            musicStatus.textContent = `Playing: ${stations[currentStation].name}`;
            musicStatus.className = 'music-status playing';
        }
    });

    console.log('Music player initialized.');
}

/* ========================================
   INITIALIZE ALL STUDIO TOOLS
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all studio tools
    setupAudioOverview();
    setupVideoOverview();
    setupMindMap();
    setupReports();
    setupFlashcards();
    setupQuiz();
    setupSlideDeck();

    // Initialize Community Hub
    setupCommunityHub();

    // Initialize Music Player
    setupMusicPlayer();

    // Initially disable tools
    disableStudioTools();
});

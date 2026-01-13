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

/* Safe Fetch Wrapper to handle file:// protocol */
const SERVER_URL = 'http://localhost:3000';

async function safeFetch(url, options) {
    if (window.location.protocol === 'file:') {
        // Point to localhost server if running locally
        const fullUrl = url.startsWith('http') ? url : `${SERVER_URL}/${url}`;
        return fetch(fullUrl, options);
    }
    return fetch(url, options);
}

function getChapters() {
    let chapters = DEFAULT_CHAPTERS;
    const stored = localStorage.getItem(CHAPTERS_KEY);

    if (stored) {
        try {
            const parsed = JSON.parse(stored);
            // Merge strategies:
            // 1. Ensure all DEFAULT chapters exist (add if missing)
            // 2. Preserve custom chapters if any (though UI doesn't allow adding custom ones yet)
            // 3. Update names/colors of existing default chapters to ensure updates (like "Strabismus") propagation

            const defaultsMap = new Map(DEFAULT_CHAPTERS.map(c => [c.id, c]));

            // Start with parsed chapters
            chapters = parsed.map(ch => {
                // If it's a default chapter, use the latest definition (name/color) but keep the ID/order? 
                // Actually, simply overwriting with default definition is safer for updates.
                if (defaultsMap.has(ch.id)) {
                    return defaultsMap.get(ch.id);
                }
                return ch;
            });

            // Add any missing default chapters
            DEFAULT_CHAPTERS.forEach(def => {
                if (!chapters.some(ch => ch.id === def.id)) {
                    chapters.push(def);
                }
            });

            // Update storage with the merged list
            if (JSON.stringify(chapters) !== stored) {
                localStorage.setItem(CHAPTERS_KEY, JSON.stringify(chapters));
            }
        } catch (e) {
            console.warn("Error parsing chapters, resetting to defaults", e);
            localStorage.setItem(CHAPTERS_KEY, JSON.stringify(DEFAULT_CHAPTERS));
        }
    } else {
        localStorage.setItem(CHAPTERS_KEY, JSON.stringify(DEFAULT_CHAPTERS));
    }
    return chapters;
}

// Helper: Assign Persistent Sequential IDs
function assignSequentialIds(library) {
    // 1. Find current max seqId
    let maxId = 0;
    library.forEach(item => {
        if (item.seqId && item.seqId > maxId) maxId = item.seqId;
    });

    // 2. Identify items without seqId
    const unnumberedItems = library.filter(item => !item.seqId);

    // 3. Sort unnumbered items by DATE ASCENDING (Oldest gets lower number)
    unnumberedItems.sort((a, b) => new Date(a.date) - new Date(b.date));

    // 4. Assign new IDs
    let nextId = maxId + 1;
    let modified = false;

    unnumberedItems.forEach(item => {
        item.seqId = nextId++;
        modified = true;
    });

    return modified;
}

// Auto-Sync to Server Logic
async function syncLibraryToServer() {
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
    let selectionMode = false;
    let selectedItems = new Set();

    // Toggle Export Button
    function updateExportButtonVisibility() {
        if (exportBtn) {
            exportBtn.style.display = (selectionMode && selectedItems.size > 0) ? 'block' : 'none';
        }
    }

    // EXPORT TO SERVER
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            // Check removed to allow attempt
            if (selectedItems.size === 0) return;

            if (!confirm(`Export ${selectedItems.size} selected items to the server knowledge base?`)) return;

            const originalIcon = exportBtn.innerHTML;
            exportBtn.innerHTML = '<span class="material-symbols-rounded">sync</span>';

            try {
                const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');
                const itemsToExport = library.filter(item => selectedItems.has(item.id));

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
            const response = await safeFetch('api/library/list');
            if (response.ok) {
                const serverItems = await response.json();
                let localLibrary = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');
                let addedCount = 0;
                let updatedCount = 0;

                // Create a map of local items for faster lookup
                const localMap = new Map();
                localLibrary.forEach(item => {
                    // Use ID if available, otherwise fallback to title+date as key (legacy support)
                    const key = item.id || (item.title + item.date);
                    localMap.set(String(key), item);
                });

                serverItems.forEach(serverItem => {
                    const serverKey = String(serverItem.id || (serverItem.title + serverItem.date));

                    if (localMap.has(serverKey)) {
                        // Item exists locally. Check if we need to update.
                        // We assume Server is the "Truth" for synchronization when fetching.
                        // Ideally we would compare timestamps, but for now we update local to match server matches
                        // to ensure chapter changes propagate.
                        const localItem = localMap.get(serverKey);

                        // Check for differences that matter (Chapter, Title, Data)
                        if (localItem.chapterId !== serverItem.chapterId ||
                            localItem.title !== serverItem.title ||
                            localItem.summary !== serverItem.summary) {

                            // Update local properties
                            localItem.chapterId = serverItem.chapterId;
                            localItem.title = serverItem.title;
                            localItem.summary = serverItem.summary;
                            localItem.data = serverItem.data; // Sync content too
                            // Preserve local seqId if it exists, otherwise use server's or generate new
                            if (!localItem.seqId && serverItem.seqId) localItem.seqId = serverItem.seqId;

                            updatedCount++;
                        }
                    } else {
                        // New Item from Server
                        // CRITICAL: Strip the server's seqId so we assign a new LOCAL one
                        // This ensures hashtags are ordered strictly by the local server's sequence
                        const newItem = { ...serverItem };
                        // We might want to keep seqId if we want global consistency, 
                        // but the user requirement "sync chapterisation ... sequential hashtag numbers based on local library"
                        // suggests we might want to keep local numbering. 
                        // However, if we sync, we want the same numbers?
                        // User said: "imported infographics are assigned sequential hashtag numbers based on the local library's order, rather than inheriting server-side numbering."
                        // So we DELETE seqId.
                        delete newItem.seqId;

                        localLibrary.push(newItem);
                        addedCount++;
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
                        alert(`Sync Complete: ${msg.join(', ')} items.`);
                    }
                    console.log(`Auto-Sync: Imported ${addedCount}, Updated ${updatedCount}.`);
                } else {
                    if (!silent) alert('Library is up to date.');
                    console.log("Auto-Sync: Library up to date.");
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

                if (localOnlyItems.length > 0) {
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
            } else {
                if (!silent) alert('Failed to fetch from server.');
                console.warn("Auto-Sync: Failed to fetch from server.");
            }
        } catch (err) {
            if (!silent) {
                console.error('Import error:', err);
                alert('Error connecting to server.');
            } else {
                console.log("Auto-Sync: Could not connect to server (backend likely offline).");
            }
        } finally {
            if (importBtn) importBtn.innerHTML = originalIcon;
        }
    }

    // Sync Button Logic
    const syncBtn = document.getElementById('sync-btn');

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

    // SAVE
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            if (!currentInfographicData) {
                alert("Only generated infographics can be saved.");
                return;
            }

            const library = JSON.parse(localStorage.getItem(LIBRARY_KEY) || '[]');

            // Calculate next seqId
            let nextSeqId = 1;
            if (library.length > 0) {
                const maxSeqId = library.reduce((max, item) => (item.seqId > max ? item.seqId : max), 0);
                nextSeqId = maxSeqId + 1;
            }

            const newItem = {
                id: Date.now(),
                seqId: nextSeqId, // Persistent ID
                title: currentInfographicData.title || "Untitled Infographic",
                summary: currentInfographicData.summary || "",
                date: new Date().toISOString(),
                data: currentInfographicData,
                chapterId: 'uncategorized'
            };

            library.unshift(newItem);
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
                if (window.location.protocol !== 'file:') {
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

                const el = document.createElement('div');
                el.className = `saved-item ${isSelected ? 'selected' : ''}`;
                el.innerHTML = `
                    ${selectionMode ? `
                        <input type="checkbox" class="item-checkbox" data-id="${item.id}" ${isSelected ? 'checked' : ''}>
                    ` : `
                        <div class="item-number" style="font-weight: bold; color: #94a3b8; font-size: 0.9rem; margin-right: 12px; min-width: 25px;">#${item.seqId || '?'}</div>
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
                btn.addEventListener('click', (e) => {
                    const button = e.target.closest('.btn-delete');
                    const id = parseInt(button.dataset.id);

                    const password = prompt('Enter admin password to delete:');
                    if (password === '309030') {
                        if (confirm('Are you sure you want to delete this item?')) {
                            const newLibrary = library.filter(i => i.id !== id);
                            localStorage.setItem(LIBRARY_KEY, JSON.stringify(newLibrary));

                            // Auto-Sync
                            syncLibraryToServer();

                            renderLibraryList();
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
}

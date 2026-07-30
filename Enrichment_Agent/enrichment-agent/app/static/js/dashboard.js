/**
 * Enrichment Agent Dashboard JS
 * Pure Vanilla JavaScript implementation
 */

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  loadDashboardData();
  setupEventListeners();
});

let allRecords = [];

function initNavigation() {
  // Sidebar navigation removed - main view displays all enriched records directly
}

function setupEventListeners() {
  const closeBtn = document.getElementById('modal-close-btn');
  const overlay = document.getElementById('modal-overlay');

  if (closeBtn) {
    closeBtn.addEventListener('click', closeModal);
  }
  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
  }

  const simulateBtn = document.getElementById('btn-simulate-enrich');
  if (simulateBtn) {
    simulateBtn.addEventListener('click', openSimulateModal);
  }
}

async function loadDashboardData() {
  try {
    const [recResp, meetResp] = await Promise.all([
      fetch('/api/records'),
      fetch('/api/meetings')
    ]);

    const records = recResp.ok ? await recResp.json() : [];
    const meetings = meetResp.ok ? await meetResp.json() : [];

    const mappedMeetings = meetings.map(m => ({
      id: m.id,
      is_meeting: true,
      category: 'meeting',
      title: m.title,
      description: m.description || `Host: ${m.organizer || 'N/A'} | Platform: ${m.platform}`,
      priority: 'HIGH',
      status: m.status,
      original_data: {
        organizer: m.organizer,
        meeting_url: m.meeting_url,
        date: m.meeting_date,
        time_zone: m.time_zone
      },
      enriched_data: m.searched_details || {}
    }));

    allRecords = [...records, ...mappedMeetings];
    updateMetrics(allRecords);
    renderAllGrids(allRecords);

  } catch (err) {
    console.error('Error loading dashboard data:', err);
    showToast('Failed to load data from server', 'error');
  }
}

function updateMetrics(records) {
  const total = records.length;
  const hackathons = records.filter(r => r.category.toLowerCase() === 'hackathon').length;
  const internships = records.filter(r => r.category.toLowerCase() === 'internship').length;
  const certs = records.filter(r => r.category.toLowerCase() === 'certification').length;
  const enriched = records.filter(r => r.status === 'completed' || r.status === 'complete' || r.status === 'scheduled').length;

  document.getElementById('metric-total').innerText = total;
  document.getElementById('metric-hackathons').innerText = hackathons;
  document.getElementById('metric-internships').innerText = internships;
  document.getElementById('metric-certifications').innerText = certs;
  document.getElementById('metric-enriched').innerText = enriched;
}

function renderAllGrids(records) {
  const recentGrid = document.getElementById('grid-recent-records');
  const hackathonsGrid = document.getElementById('grid-hackathons');
  const internshipsGrid = document.getElementById('grid-internships');
  const certificationsGrid = document.getElementById('grid-certifications');
  const meetingsGrid = document.getElementById('grid-meetings');

  if (recentGrid) {
    recentGrid.innerHTML = records.length ? records.map(r => createRecordCardHTML(r)).join('') : emptyStateHTML('opportunity');
  }

  const hackathons = records.filter(r => (r.category || '').toLowerCase() === 'hackathon');
  if (hackathonsGrid) {
    hackathonsGrid.innerHTML = hackathons.length ? hackathons.map(r => createRecordCardHTML(r)).join('') : emptyStateHTML('hackathon');
  }

  const internships = records.filter(r => (r.category || '').toLowerCase() === 'internship');
  if (internshipsGrid) {
    internshipsGrid.innerHTML = internships.length ? internships.map(r => createRecordCardHTML(r)).join('') : emptyStateHTML('internship');
  }

  const certs = records.filter(r => (r.category || '').toLowerCase() === 'certification');
  if (certificationsGrid) {
    certificationsGrid.innerHTML = certs.length ? certs.map(r => createRecordCardHTML(r)).join('') : emptyStateHTML('certification');
  }

  const meetings = records.filter(r => (r.category || '').toLowerCase() === 'meeting');
  if (meetingsGrid) {
    meetingsGrid.innerHTML = meetings.length ? meetings.map(r => createRecordCardHTML(r)).join('') : emptyStateHTML('meeting');
  }
}

function emptyStateHTML(category) {
  return `
    <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">
      <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">No ${category} records found.</p>
      <p style="font-size: 0.85rem;">Click "+ Enrich Incoming Record" to test the Enrichment Agent.</p>
    </div>
  `;
}

function getSmartOpportunityName(record) {
  const enr = record.enriched_data || {};
  const orig = record.original_data || {};

  // Helper to clean prefixes like "Fwd:", "Re:", "Subject:", "Dear...", "Hi..."
  const cleanTitleStr = (str) => {
    if (!str || typeof str !== 'string') return '';
    let cleaned = str.trim()
      .replace(/^(fwd|re|subject)[\s:]+/i, '')
      .replace(/^(dear|hi|hello|greetings)\s+[\w\s,!-]+[\r\n.]*/i, '')
      .trim();
    return cleaned;
  };

  // 1. Prioritize clean extracted opportunity name from LLM / Web Search
  const rawEnrichedName = extractEnrichedVal(enr.opportunity_name) ||
                          extractEnrichedVal(enr.name) ||
                          extractEnrichedVal(enr.title) ||
                          extractEnrichedVal(enr.event_name) ||
                          extractEnrichedVal(enr.hackathon_name);

  const cleanEnriched = cleanTitleStr(rawEnrichedName);
  if (cleanEnriched && cleanEnriched !== 'null' && cleanEnriched !== 'Incoming Email Opportunity' && !/^(dear|hi|hello|greetings)/i.test(cleanEnriched)) {
    return cleanEnriched;
  }

  // 2. Fall back to record title cleaned
  const rawTitle = record.title || orig.title || '';
  const cleanRawTitle = cleanTitleStr(rawTitle);
  if (cleanRawTitle && cleanRawTitle !== 'null' && cleanRawTitle !== 'Incoming Email Opportunity' && !/^(dear|hi|hello|greetings)/i.test(cleanRawTitle)) {
    return cleanRawTitle;
  }

  // 3. Regex parse description if title was a greeting
  const desc = record.description || '';
  const match = desc.match(/(?:hackathon|event|challenge|competition|program|opportunity)\s+name[:\-]?\s*([A-Za-z0-9\s\-]{3,40})/i) ||
                desc.match(/([A-Z][A-Za-z0-9\s]{2,30}\s+(?:Hackathon|Datathon|Ideathon|Challenge|202\d))/);

  if (match && match[1]) {
    return match[1].trim();
  }

  return 'Opportunity';
}

function getSmartDeadline(record) {
  const enr = record.enriched_data || {};
  const orig = record.original_data || {};

  const val = extractEnrichedVal(enr.registration_deadline) ||
              extractEnrichedVal(enr.registration_date) ||
              extractEnrichedVal(enr.reg_date) ||
              extractEnrichedVal(enr.deadline) ||
              extractEnrichedVal(enr.application_deadline) ||
              extractEnrichedVal(enr.enrollment_deadline) ||
              extractEnrichedVal(enr.last_date) ||
              orig.registration_deadline ||
              orig.deadline;

  if (val && val !== 'null' && val !== 'Web Extracted' && val !== 'Web Search Extracted') {
    return val;
  }

  // Regex parse description if available
  const desc = record.description || '';
  const dateMatch = desc.match(/(?:deadline|last date|reg(?:istration)? date|due date)[\s:]*([A-Za-z0-9\s,\-]+(?:\d{4}|\d{1,2}(?:st|nd|rd|th)?))/i) ||
                    desc.match(/(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{0,4})/i) ||
                    desc.match(/((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,\s*\d{4})?)/i);

  if (dateMatch && dateMatch[1] && dateMatch[1].length > 2) {
    return dateMatch[1].trim();
  }

  return 'To Be Announced';
}

function getSmartSubmissionDate(record) {
  const enr = record.enriched_data || {};
  const orig = record.original_data || {};

  const val = extractEnrichedVal(enr.submission_deadline) ||
              extractEnrichedVal(enr.submission_date) ||
              extractEnrichedVal(enr.event_dates) ||
              extractEnrichedVal(enr.event_date) ||
              extractEnrichedVal(enr.dates) ||
              extractEnrichedVal(enr.timeline) ||
              extractEnrichedVal(enr.start_date) ||
              orig.submission_deadline ||
              orig.event_dates;

  if (val && val !== 'null' && val !== 'Web Extracted' && val !== 'Web Search Extracted') {
    return val;
  }

  return 'To Be Announced';
}

function getSmartPrizePool(record) {
  const enr = record.enriched_data || {};
  const orig = record.original_data || {};

  const val = extractEnrichedVal(enr.prize_pool) ||
              extractEnrichedVal(enr.stipend) ||
              extractEnrichedVal(enr.cost) ||
              extractEnrichedVal(enr.prizes) ||
              orig.prize_pool;

  if (val && val !== 'null' && val !== 'Verified' && val !== 'Disclosed') {
    return val;
  }

  return 'Disclosed on Website';
}

function getCleanUrl(urlVal) {
  if (!urlVal || typeof urlVal !== 'string') return null;
  const trimmed = urlVal.trim();
  if (/^(no|none|n\/a|not|unknown)/i.test(trimmed)) return null;
  const match = trimmed.match(/https?:\/\/[^\s<>"]+/i);
  if (match && match[0]) {
    const clean = match[0].replace(/[.,;)]+$/, '');
    if (clean.length > 10 && clean.includes('.')) {
      return clean;
    }
  }
  return null;
}

function cleanShortFieldVal(val, maxLen = 60) {
  if (!val || typeof val !== 'string') return '';
  let str = val.trim();
  str = str.replace(/\s*\([^)]*\)/g, '').trim();
  if (str.length > maxLen) {
    return str.substring(0, maxLen - 3) + '...';
  }
  return str;
}

function createRecordCardHTML(record) {
  const cat = (record.category || 'general').toUpperCase();
  const priorityClass = `badge-${(record.priority || 'medium').toLowerCase()}`;
  const enr = record.enriched_data || {};
  const oppName = getSmartOpportunityName(record);

  // Extract key dates & fields cleanly
  const regDeadline = cleanShortFieldVal(getSmartDeadline(record), 40);
  const submissionDate = cleanShortFieldVal(getSmartSubmissionDate(record), 40);
  const prizeOrStipend = cleanShortFieldVal(getSmartPrizePool(record), 30);
  const rawChallenge = extractEnrichedVal(enr.challenge) || extractEnrichedVal(enr.problem_statements) || extractEnrichedVal(enr.theme) || extractEnrichedVal(enr.role) || 'Featured';
  const challengeOrRole = cleanShortFieldVal(rawChallenge, 65);

  const rawOfficialSite = extractEnrichedVal(enr.official_website) || extractEnrichedVal(enr.registration_url);
  const officialSite = getCleanUrl(rawOfficialSite);

  return `
    <div class="record-card">
      <div>
        <div class="card-header">
          <div>
            <span class="card-title">${escapeHTML(oppName)}</span>
            <span style="display: inline-block; margin-left: 0.5rem; font-size: 0.72rem; font-weight: 700; background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo); padding: 2px 8px; border-radius: 12px; text-transform: uppercase;">
              ${cat}
            </span>
          </div>
          <span class="badge ${priorityClass}">${record.priority || 'MEDIUM'}</span>
        </div>
        
        <div class="card-fields" style="margin-top: 1rem;">
          <div class="field-row">
            <span class="field-key">REGISTRATION DEADLINE:</span>
            <span class="field-val" style="color: var(--accent-indigo); font-weight: 600;">${escapeHTML(regDeadline)}</span>
          </div>
          <div class="field-row">
            <span class="field-key">SUBMISSION / EVENT DATE:</span>
            <span class="field-val" style="color: var(--text-color);">${escapeHTML(submissionDate)}</span>
          </div>
          <div class="field-row">
            <span class="field-key">PRIZE POOL / VALUE:</span>
            <span class="field-val" style="color: var(--accent-emerald); font-weight: 600;">${escapeHTML(prizeOrStipend)}</span>
          </div>
          <div class="field-row">
            <span class="field-key">CHALLENGE / THEME:</span>
            <span class="field-val" style="color: var(--text-muted);">${escapeHTML(challengeOrRole)}</span>
          </div>
          ${officialSite ? `
            <div class="field-row" style="margin-top: 0.4rem;">
              <span class="field-key">OFFICIAL LINK:</span>
              <span class="field-val"><a href="${escapeHTML(officialSite)}" target="_blank" rel="noopener" style="color: var(--accent-cyan); text-decoration: underline;">${escapeHTML(officialSite.replace(/^https?:\/\//, '').split('/')[0])}</a></span>
            </div>
          ` : ''}
        </div>
      </div>

      <div class="card-footer" style="margin-top: 1rem;">
        <span class="status-tag">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
          Web Enriched
        </span>
        <button class="btn btn-secondary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;" onclick="viewRecordDetails('${record.id}', ${Boolean(record.is_meeting)})">
          View Details
        </button>
      </div>
    </div>
  `;
}

function extractEnrichedVal(fieldObj) {
  if (!fieldObj) return null;
  if (typeof fieldObj === 'object' && fieldObj.value) return fieldObj.value;
  if (typeof fieldObj === 'string') return fieldObj;
  return null;
}

async function viewRecordDetails(recordId, isMeeting = false) {
  try {
    let record;
    if (isMeeting || (typeof recordId === 'string' && recordId.includes('-'))) {
      const resp = await fetch(`/api/meetings/${recordId}`);
      if (!resp.ok) throw new Error('Meeting not found');
      const m = await resp.json();
      record = {
        title: m.title,
        category: 'meeting',
        description: m.description,
        original_data: { organizer: m.organizer, meeting_url: m.meeting_url, date: m.meeting_date, time_zone: m.time_zone },
        enriched_data: m.searched_details || {},
        sources: [],
        documents: []
      };
    } else {
      const resp = await fetch(`/api/records/${recordId}`);
      if (!resp.ok) throw new Error('Record not found');
      record = await resp.json();
    }

    document.getElementById('modal-title').innerText = record.title;

    const modalBody = document.getElementById('modal-body-content');
    modalBody.innerHTML = buildDetailModalHTML(record);

    document.getElementById('modal-overlay').classList.add('active');
  } catch (err) {
    console.error('Failed to view record details:', err);
    showToast('Failed to load record details', 'error');
  }
}

function buildDetailModalHTML(record) {
  const orig = record.original_data || {};
  const enr = record.enriched_data || {};
  const sources = record.sources || [];
  const docs = record.documents || [];
  const desc = record.description || orig.description || '';

  // Group fields into EMAIL DATA vs WEB-ENRICHED DATA
  let emailDataHTML = '';
  let webDataHTML = '';

  // Email Body Text Block (Omitted to keep view details clean and focused on web-enriched data)
  let emailBodyHTML = '';

  // Email Data Fields
  const origKeys = Object.keys(orig).filter(k => k !== 'description');
  if (origKeys.length > 0) {
    emailDataHTML = origKeys.map(k => `
      <div class="detail-item">
        <div class="detail-item-header">
          <span class="detail-label">${formatLabel(k)}</span>
          <span class="data-source-pill pill-email">INITIAL PAYLOAD</span>
        </div>
        <div class="detail-val">${escapeHTML(String(orig[k]))}</div>
      </div>
    `).join('');
  }

  // Web Enriched / Groq Extracted Fields
  const enrKeys = Object.keys(enr);
  const validEnrKeys = enrKeys.filter(k => enr[k] !== null && enr[k] !== undefined);

  if (validEnrKeys.length > 0) {
    webDataHTML = validEnrKeys.map(k => {
      const item = enr[k];
      const val = typeof item === 'object' ? item.value : item;
      const srcUrl = typeof item === 'object' ? item.source_url : '';
      const srcType = typeof item === 'object' ? (item.source_type || 'web') : 'web';
      const conf = typeof item === 'object' ? (item.confidence || 0.95) : 0.90;
      const confPct = Math.round(conf * 100);

      const pillClass = srcType === 'email_body' ? 'pill-email' : 'pill-web';
      const pillLabel = srcType === 'email_body' ? 'GROQ EMAIL EXTRACTED' : 'WEB ENRICHED';

      return `
        <div class="detail-item">
          <div class="detail-item-header">
            <span class="detail-label">${formatLabel(k)}</span>
            <span class="data-source-pill ${pillClass}">${pillLabel}</span>
          </div>
          <div class="detail-val" style="color: var(--accent-emerald);">${escapeHTML(String(val))}</div>
          ${srcUrl ? `
            <div class="confidence-indicator">
              <span>Source: ${srcUrl.startsWith('http') ? `<a href="${escapeHTML(srcUrl)}" target="_blank" style="color: var(--accent-indigo); text-decoration: underline;">${escapeHTML(srcUrl)}</a>` : `<span>${escapeHTML(srcUrl)}</span>`}</span>
              <span style="margin-left: auto; font-weight: 700; color: var(--accent-emerald);">${confPct}% Confidence</span>
            </div>
            <div class="confidence-bar"><div class="confidence-fill" style="width: ${confPct}%;"></div></div>
          ` : ''}
        </div>
      `;
    }).join('');
  } else {
    webDataHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No enriched fields extracted yet.</p>`;
  }

  // Sources list
  let sourcesHTML = '';
  if (sources.length > 0) {
    sourcesHTML = sources.map(s => `
      <tr style="border-bottom: 1px solid var(--border-color);">
        <td style="font-weight: 600; text-transform: uppercase; font-size: 0.78rem;">${escapeHTML(s.field_name)}</td>
        <td style="color: var(--accent-emerald); font-weight: 600;">${escapeHTML(s.value || s.field_value)}</td>
        <td><a href="${escapeHTML(s.source_url)}" target="_blank" class="doc-link">${escapeHTML(s.source_url)}</a></td>
        <td><span style="color: var(--accent-emerald); font-weight: 700;">${Math.round((s.confidence || 0.9) * 100)}%</span></td>
      </tr>
    `).join('');
  }

  // Documents list
  let docsHTML = '';
  if (docs.length > 0) {
    docsHTML = docs.map(d => `
      <div style="background: rgba(0, 0, 0, 0.3); padding: 0.85rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
        <div>
          <div style="font-weight: 600; font-size: 0.92rem; color: #fff;">${escapeHTML(d.document_name)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHTML(d.document_type)}</div>
        </div>
        <a href="${escapeHTML(d.document_url)}" target="_blank" class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">
          Download / Open
        </a>
      </div>
    `).join('');
  } else {
    docsHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No linked documents discovered for this record.</p>`;
  }

  // Extract special top highlight fields
  const nameVal = getSmartOpportunityName(record);
  const rawOfficialSite = extractEnrichedVal(enr.official_website) || extractEnrichedVal(enr.registration_url) || extractEnrichedVal(enr.course_url) || extractEnrichedVal(enr.application_url);
  const officialSite = getCleanUrl(rawOfficialSite);

  // Requested fields the user asked for — shown FIRST at the top
  const requestedFields = Array.isArray(record.requested_fields) ? record.requested_fields : [];

  let dynamicTopTilesHTML = `
    <div class="highlight-tile">
      <div class="highlight-label">🏆 OPPORTUNITY NAME</div>
      <div class="highlight-val" style="color: var(--accent-cyan); font-weight: 700;">${escapeHTML(nameVal)}</div>
    </div>
  `;

  if (requestedFields.length > 0) {
    // Show REQUESTED missing fields first at top with highlighted badge
    requestedFields.forEach(fieldKey => {
      const itemVal = extractEnrichedVal(enr[fieldKey]);
      const displayVal = itemVal && itemVal !== 'null' ? itemVal : '—  Not Found';
      const valColor = itemVal && itemVal !== 'null' ? 'var(--accent-emerald)' : 'var(--accent-rose)';
      dynamicTopTilesHTML += `
        <div class="highlight-tile" style="border: 1px solid rgba(99,102,241,0.4);">
          <div class="highlight-label" style="display:flex;align-items:center;gap:0.4rem;">
            ✨ ${formatLabel(fieldKey).toUpperCase()}
            <span style="font-size:0.65rem;background:rgba(99,102,241,0.25);color:#818cf8;padding:1px 6px;border-radius:8px;font-weight:700;">REQUESTED</span>
          </div>
          <div class="highlight-val" style="color:${valColor}; font-weight:700;">${escapeHTML(cleanShortFieldVal(String(displayVal), 55))}</div>
        </div>
      `;
    });

    // Then show any other enriched fields that weren't in the request
    const extraKeys = Object.keys(enr).filter(k =>
      !requestedFields.includes(k) &&
      !['opportunity_name', 'name', 'title', 'official_website', 'registration_url'].includes(k.toLowerCase())
    );
    extraKeys.forEach(key => {
      const itemVal = extractEnrichedVal(enr[key]);
      if (itemVal && itemVal !== 'null') {
        dynamicTopTilesHTML += `
          <div class="highlight-tile">
            <div class="highlight-label">📌 ${formatLabel(key).toUpperCase()}</div>
            <div class="highlight-val" style="color: var(--accent-amber);">${escapeHTML(cleanShortFieldVal(itemVal, 50))}</div>
          </div>
        `;
      }
    });
  } else {
    // No explicit requested fields — display all enriched fields
    const topFieldsKeys = Object.keys(enr).filter(k =>
      !['opportunity_name', 'name', 'title', 'official_website', 'registration_url'].includes(k.toLowerCase())
    );
    if (topFieldsKeys.length > 0) {
      topFieldsKeys.forEach(key => {
        const itemVal = extractEnrichedVal(enr[key]);
        if (itemVal && itemVal !== 'null') {
          dynamicTopTilesHTML += `
            <div class="highlight-tile">
              <div class="highlight-label">✨ ${formatLabel(key).toUpperCase()}</div>
              <div class="highlight-val" style="color: var(--accent-emerald);">${escapeHTML(cleanShortFieldVal(itemVal, 50))}</div>
            </div>
          `;
        }
      });
    } else {
      // Fallback standard fields
      dynamicTopTilesHTML += `
        <div class="highlight-tile deadline">
          <div class="highlight-label">📅 REGISTRATION DEADLINE</div>
          <div class="highlight-val" style="color: var(--accent-rose);">${escapeHTML(getSmartDeadline(record))}</div>
        </div>
        <div class="highlight-tile submission">
          <div class="highlight-label">⏳ SUBMISSION / DATES</div>
          <div class="highlight-val" style="color: var(--accent-amber);">${escapeHTML(getSmartSubmissionDate(record))}</div>
        </div>
        <div class="highlight-tile prizepool">
          <div class="highlight-label">💰 PRIZE POOL / VALUE</div>
          <div class="highlight-val" style="color: var(--accent-emerald);">${escapeHTML(getSmartPrizePool(record))}</div>
        </div>
      `;
    }
  }

  if (officialSite) {
    dynamicTopTilesHTML += `
      <div class="highlight-tile website">
        <div class="highlight-label">🌐 OFFICIAL WEBSITE</div>
        <div class="highlight-val">
          <a href="${escapeHTML(officialSite)}" target="_blank" rel="noopener" style="color: var(--accent-cyan); text-decoration: underline; font-size: 0.95rem;">
            ${escapeHTML(officialSite.replace(/^https?:\/\//, '').split('/')[0])} ↗
          </a>
        </div>
      </div>
    `;
  }

  const specialTopGridHTML = `
    <div class="special-top-grid">
      ${dynamicTopTilesHTML}
    </div>
  `;


  return `
    ${specialTopGridHTML}

    ${origKeys.length > 0 ? `
    <div class="section-block">
      <div class="section-title">Initial Payload Data</div>
      <div class="detail-grid">${emailDataHTML}</div>
    </div>
    ` : ''}

    <div class="section-block">
      <div class="section-title">Comprehensive Enriched Information</div>
      <div class="detail-grid">${webDataHTML}</div>
    </div>

    ${sources.length > 0 ? `
      <div class="section-block">
        <div class="section-title">Enrichment Source Audit</div>
        <table class="docs-table">
          <thead>
            <tr>
              <th>Field Name</th>
              <th>Enriched Value</th>
              <th>Source URL</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>${sourcesHTML}</tbody>
        </table>
      </div>
    ` : ''}
  `;
}

async function loadDocumentsData() {
  try {
    const resp = await fetch('/api/documents');
    if (!resp.ok) throw new Error('Failed to fetch documents');
    const docs = await resp.json();

    const tbody = document.getElementById('table-body-documents');
    if (!tbody) return;

    if (docs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No discovered documents available.</td></tr>`;
      return;
    }

    tbody.innerHTML = docs.map(d => `
      <tr>
        <td style="font-weight: 600; color: #fff;">${escapeHTML(d.document_name)}</td>
        <td><span class="badge badge-medium">${escapeHTML(d.category)}</span></td>
        <td>${escapeHTML(d.record_title)}</td>
        <td><span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHTML(d.document_type)}</span></td>
        <td>
          <a href="${escapeHTML(d.document_url)}" target="_blank" class="doc-link">
            Open Document
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
          </a>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading documents data:', err);
  }
}

function openSimulateModal() {
  const modalBody = document.getElementById('modal-body-content');
  document.getElementById('modal-title').innerText = 'Enrich Record';

  modalBody.innerHTML = `
    <form id="form-simulate-enrich" style="display: flex; flex-direction: column; gap: 1.1rem;">
      <div>
        <label style="display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-color); margin-bottom: 0.35rem;">Category</label>
        <select id="sim-category" style="width: 100%; padding: 0.65rem; background: var(--bg-card); border: 1px solid var(--border-color); color: #fff; border-radius: 8px; font-size: 0.9rem;">
          <option value="hackathon">Hackathon</option>
          <option value="internship">Internship</option>
          <option value="certification">Certification</option>
        </select>
      </div>

      <div>
        <label style="display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-color); margin-bottom: 0.35rem;">Email Body <span style="color: var(--accent-rose);">*</span></label>
        <textarea id="sim-email-body" rows="6" placeholder="Paste email content here..." style="width: 100%; padding: 0.75rem; background: var(--bg-card); border: 1px solid var(--border-color); color: #fff; border-radius: 8px; font-family: inherit; font-size: 0.9rem; resize: vertical;" required></textarea>
      </div>

      <div>
        <label style="display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-color); margin-bottom: 0.35rem;">Missing Fields <span style="color: var(--accent-rose);">*</span></label>
        <input type="text" id="sim-missing-fields" placeholder="e.g. prize_pool, registration_deadline, official_website" style="width: 100%; padding: 0.65rem; background: var(--bg-card); border: 1px solid var(--border-color); color: #fff; border-radius: 8px; font-size: 0.9rem;" />
        <div id="missing-fields-error" style="display:none; font-size:0.75rem; color:var(--accent-rose); margin-top:0.25rem;">Please enter missing fields to search for (comma-separated).</div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 1rem; margin-top: 0.5rem;">
        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">🔍 Search & Enrich</button>
      </div>
    </form>
  `;

  document.getElementById('modal-overlay').classList.add('active');

  document.getElementById('form-simulate-enrich').addEventListener('submit', async (e) => {
    e.preventDefault();

    const emailBodyText = document.getElementById('sim-email-body').value.trim();
    const rawMissing = document.getElementById('sim-missing-fields').value.trim();
    const missingFieldsList = rawMissing ? rawMissing.split(',').map(s => s.trim()).filter(Boolean) : [];

    // Validate: missing fields is required
    if (missingFieldsList.length === 0) {
      document.getElementById('missing-fields-error').style.display = 'block';
      document.getElementById('sim-missing-fields').style.borderColor = 'var(--accent-rose)';
      return;
    }
    document.getElementById('missing-fields-error').style.display = 'none';
    document.getElementById('sim-missing-fields').style.borderColor = 'var(--border-color)';

    if (!emailBodyText) return;

    const payload = {
      external_record_id: `sim_${Date.now()}`,
      category: document.getElementById('sim-category').value,
      title: "",
      email_body: emailBodyText,
      description: emailBodyText,
      missing_fields: missingFieldsList,
      sender: "research_agent@agentos.io",
      priority: "HIGH",
      links: [],
      existing_data: {}
    };

    closeModal();
    showToast(`Searching for: ${missingFieldsList.join(', ')}...`, 'info');

    try {
      const resp = await fetch('/api/enrich', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Enrichment failed');
      }
      const result = await resp.json();
      showToast(`Enrichment done! Found: ${Object.keys(result.enriched_data || {}).length} fields.`, 'success');
      loadDashboardData();
    } catch (err) {
      console.error('Enrichment error:', err);
      showToast(`Enrichment failed: ${err.message}`, 'error');
    }
  });
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
}

function formatLabel(str) {
  return str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function escapeHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(msg, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerText = msg;

  if (type === 'error') toast.style.borderColor = 'var(--accent-rose)';
  if (type === 'success') toast.style.borderColor = 'var(--accent-emerald)';

  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4000);
}

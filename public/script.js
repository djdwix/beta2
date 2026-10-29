var csrfToken = null;
var csrfTokenRefreshPromise = null;
var csrfTokenLastFetch = 0;
var CSRF_TOKEN_TTL = 300000;

function getCsrfTokenFromCookie() {
    try {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.indexOf('csrf_token=') === 0) {
                return cookie.substring('csrf_token='.length, cookie.length);
            }
        }
        return null;
    } catch (e) {
        return null;
    }
}

function setCsrfTokenCookie(token) {
    try {
        var expires = new Date(Date.now() + CSRF_TOKEN_TTL).toUTCString();
        document.cookie = 'csrf_token=' + token + '; expires=' + expires + '; path=/; SameSite=Strict; Secure';
    } catch (e) {}
}

function fetchCsrfToken() {
    if (csrfTokenRefreshPromise) {
        return csrfTokenRefreshPromise;
    }
    if (csrfToken && (Date.now() - csrfTokenLastFetch) < CSRF_TOKEN_TTL) {
        return Promise.resolve(csrfToken);
    }
    var cookieToken = getCsrfTokenFromCookie();
    if (cookieToken) {
        csrfToken = cookieToken;
        csrfTokenLastFetch = Date.now();
        return Promise.resolve(csrfToken);
    }
    csrfTokenRefreshPromise = fetch('/api/csrf-token', {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache'
        }
    }).then(function(response) {
        if (!response.ok) {
            throw new Error('Failed to fetch CSRF token: HTTP ' + response.status);
        }
        return response.json();
    }).then(function(data) {
        if (!data.csrf_token) {
            throw new Error('No CSRF token in response');
        }
        csrfToken = data.csrf_token;
        csrfTokenLastFetch = Date.now();
        setCsrfTokenCookie(csrfToken);
        csrfTokenRefreshPromise = null;
        return csrfToken;
    }).catch(function(error) {
        csrfTokenRefreshPromise = null;
        csrfToken = null;
        throw error;
    });
    return csrfTokenRefreshPromise;
}

function apiRequest(url, options) {
    if (!options) options = {};
    options.credentials = 'include';
    if (!options.headers) options.headers = {};
    options.headers['Content-Type'] = 'application/json';
    options.headers['Accept'] = 'application/json';
    var method = (options.method || 'GET').toUpperCase();
    if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') {
        return fetch(url, options).then(function(response) {
            return response.json().then(function(data) {
                if (!response.ok) {
                    throw new Error(data.error || '请求失败: ' + response.status);
                }
                return data;
            });
        });
    }
    return fetchCsrfToken().then(function(token) {
        options.headers['X-CSRF-Token'] = token;
        return fetch(url, options);
    }).then(function(response) {
        return response.json().then(function(data) {
            if (!response.ok) {
                if (response.status === 403 && data.error && data.error.includes('CSRF')) {
                    csrfToken = null;
                    csrfTokenLastFetch = 0;
                    return fetchCsrfToken().then(function(newToken) {
                        options.headers['X-CSRF-Token'] = newToken;
                        return fetch(url, options);
                    }).then(function(retryResponse) {
                        return retryResponse.json().then(function(retryData) {
                            if (!retryResponse.ok) {
                                throw new Error(retryData.error || '请求失败: ' + retryResponse.status);
                            }
                            return retryData;
                        });
                    });
                }
                throw new Error(data.error || '请求失败: ' + response.status);
            }
            return data;
        });
    });
}

function sha256Hex(str) {
    if (window.crypto && window.crypto.subtle) {
        var enc = new TextEncoder().encode(str);
        return window.crypto.subtle.digest('SHA-256', enc).then(function(buf) {
            var arr = Array.from(new Uint8Array(buf));
            return arr.map(function(b) { return b.toString(16).padStart(2, '0'); }).join('');
        });
    }
    return Promise.resolve(_fallbackSha256(str));
}

function _fallbackSha256(str) {
    function rrot(x, n) { return (x >>> n) | (x << (32 - n)); }
    var K = [
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    ];
    var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    function utf8(s) {
        var out = [], i, c;
        for (i = 0; i < s.length; i++) {
            c = s.charCodeAt(i);
            if (c < 0x80) { out.push(c); }
            else if (c < 0x800) { out.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F)); }
            else if (c < 0xD800 || c >= 0xE000) { out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F)); }
            else { i++; c = 0x10000 + (((c & 0x3FF) << 10) | (s.charCodeAt(i) & 0x3FF)); out.push(0xF0 | (c >> 18), 0x80 | ((c >> 12) & 0x3F), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F)); }
        }
        return out;
    }
    var bytes = utf8(str);
    var l = bytes.length;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) bytes.push(0);
    var lenHi = Math.floor(l * 8 / 0x100000000);
    var lenLo = (l * 8) >>> 0;
    bytes.push((lenHi >>> 24) & 0xFF, (lenHi >>> 16) & 0xFF, (lenHi >>> 8) & 0xFF, lenHi & 0xFF);
    bytes.push((lenLo >>> 24) & 0xFF, (lenLo >>> 16) & 0xFF, (lenLo >>> 8) & 0xFF, lenLo & 0xFF);
    var w = new Array(64);
    for (var j = 0; j < bytes.length; j += 64) {
        for (var t = 0; t < 16; t++) {
            w[t] = (bytes[j + t * 4] << 24) | (bytes[j + t * 4 + 1] << 16) | (bytes[j + t * 4 + 2] << 8) | bytes[j + t * 4 + 3];
        }
        for (t = 16; t < 64; t++) {
            var s0 = rrot(w[t - 15], 7) ^ rrot(w[t - 15], 18) ^ (w[t - 15] >>> 3);
            var s1 = rrot(w[t - 2], 17) ^ rrot(w[t - 2], 19) ^ (w[t - 2] >>> 10);
            w[t] = (w[t - 16] + s0 + w[t - 7] + s1) | 0;
        }
        var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
        for (t = 0; t < 64; t++) {
            var S1 = rrot(e, 6) ^ rrot(e, 11) ^ rrot(e, 25);
            var ch = (e & f) ^ (~e & g);
            var temp1 = (h + S1 + ch + K[t] + w[t]) | 0;
            var S0 = rrot(a, 2) ^ rrot(a, 13) ^ rrot(a, 22);
            var maj = (a & b) ^ (a & c) ^ (b & c);
            var temp2 = (S0 + maj) | 0;
            h = g; g = f; f = e; e = (d + temp1) | 0;
            d = c; c = b; b = a; a = (temp1 + temp2) | 0;
        }
        H[0] = (H[0] + a) | 0; H[1] = (H[1] + b) | 0; H[2] = (H[2] + c) | 0; H[3] = (H[3] + d) | 0;
        H[4] = (H[4] + e) | 0; H[5] = (H[5] + f) | 0; H[6] = (H[6] + g) | 0; H[7] = (H[7] + h) | 0;
    }
    return H.map(function(x) { return ('00000000' + (x >>> 0).toString(16)).slice(-8); }).join('');
}

function computeAttendanceBodyHash(dateStr, nonce) {
    var bodyJson = JSON.stringify({ date: dateStr, nonce: nonce });
    return sha256Hex(bodyJson).then(function(full) {
        return full.substring(0, 32);
    });
}

var currentUser = null;
var currentHiddenPhone = null;
var currentAuthCode = null;
var cooldownInterval = null;
var cooldownEndTime = null;
var isCheckingAuth = false;
var boostActive = false;
var boostExpiresIn = 0;
var boostTimerInterval = null;
var isVerified = false;
var announcementCollapsed = false;
var currentCancelMethod = 'email';
var cancelEmailCodeTimer = null;
var cancelEmailCountdownValue = 0;
var attendanceToken = null;
var attendanceTokenNonce = null;
var attendanceTokenBodyHash = null;
var attendanceTokenExpiresAt = 0;
var attendanceTokenTimer = null;
var attendanceSubmitting = false;

function updateGenerateButtonState(dailyEarned) {
    var generateBtn = document.getElementById('generateBtn');
    if (!generateBtn) return;
    if (dailyEarned >= 14) {
        generateBtn.disabled = true;
        generateBtn.textContent = '🚫 今日积分已满14分';
        generateBtn.style.opacity = '0.5';
        generateBtn.style.cursor = 'not-allowed';
    } else {
        if (!cooldownEndTime || Date.now() >= cooldownEndTime) {
            generateBtn.disabled = false;
            generateBtn.textContent = '✨ 生成手机号';
            generateBtn.style.opacity = '1';
            generateBtn.style.cursor = 'pointer';
        }
    }
}

async function updatePointsDisplay() {
    try {
        var data = await apiRequest('/api/get-points');
        var totalPointsEl = document.getElementById('totalPoints');
        if (totalPointsEl) totalPointsEl.textContent = data.totalPoints.toFixed(2);
        var dailyEarnedEl = document.getElementById('dailyEarnedPoints');
        if (dailyEarnedEl) dailyEarnedEl.textContent = data.dailyEarnedPoints.toFixed(2);
        var attendanceDailyEarnedEl = document.getElementById('attendanceDailyEarned');
        if (attendanceDailyEarnedEl) {
            attendanceDailyEarnedEl.textContent = data.dailyEarnedPoints.toFixed(1);
        }
        updateGenerateButtonState(data.dailyEarnedPoints);
        if (data.isNewUser) {
            var userInfo = document.getElementById('userInfo');
            if (userInfo && !userInfo.querySelector('.new-user-badge')) {
                userInfo.innerHTML = '👤 ' + currentUser + ' <span class="new-user-badge">新人8折</span>';
            }
        }
        await loadAttendanceInfo();
    } catch (error) {
        console.error('Update points failed:', error);
    }
}

async function updateMailBadge() {
    try {
        var data = await apiRequest('/api/mail/list');
        applyMailBadge(data.total || 0);
    } catch (e) {
        console.error('Update mail badge failed:', e);
    }
}

async function checkBoostStatus() {
    try {
        var data = await apiRequest('/api/get-boost-status');
        boostActive = data.boostActive;
        boostExpiresIn = data.boostExpiresIn;
        var boostType = data.boostType || 'premium';
        var boostIndicator = document.getElementById('boostIndicator');
        if (boostActive && boostExpiresIn > 0) {
            if (boostIndicator) {
                boostIndicator.style.display = 'inline-flex';
                boostIndicator.innerHTML = '💎 高级加成 <span id="boostTimer">' + formatBoostTime(boostExpiresIn) + '</span>';
            }
            updateBoostTimerDisplay();
            if (boostTimerInterval) clearInterval(boostTimerInterval);
            boostTimerInterval = setInterval(function() {
                if (boostExpiresIn > 0) {
                    boostExpiresIn--;
                    updateBoostTimerDisplay();
                    if (boostExpiresIn <= 0) {
                        clearInterval(boostTimerInterval);
                        if (boostIndicator) boostIndicator.style.display = 'none';
                        boostActive = false;
                    }
                }
            }, 1000);
        } else {
            if (boostIndicator) boostIndicator.style.display = 'none';
            if (boostTimerInterval) {
                clearInterval(boostTimerInterval);
                boostTimerInterval = null;
            }
        }
    } catch (error) {
        console.error('Check boost status failed:', error);
    }
}

function formatBoostTime(seconds) {
    var minutes = Math.floor(seconds / 60);
    var secs = seconds % 60;
    return minutes + ':' + secs.toString().padStart(2, '0');
}

function updateBoostTimerDisplay() {
    var boostTimer = document.getElementById('boostTimer');
    if (boostTimer && boostExpiresIn > 0) {
        boostTimer.textContent = formatBoostTime(boostExpiresIn);
    }
}

function startCooldown() {
    var generateBtn = document.getElementById('generateBtn');
    var cooldownTimer = document.getElementById('cooldownTimer');
    if (!generateBtn) return;
    if (cooldownInterval) clearInterval(cooldownInterval);
    generateBtn.disabled = true;
    cooldownEndTime = Date.now() + 3000;
    cooldownInterval = setInterval(function() {
        var now = Date.now();
        var remaining = cooldownEndTime - now;
        if (remaining <= 0) {
            clearInterval(cooldownInterval);
            cooldownInterval = null;
            cooldownEndTime = null;
            var dailyEarnedEl = document.getElementById('dailyEarnedPoints');
            var dailyEarned = dailyEarnedEl ? (parseFloat(dailyEarnedEl.textContent) || 0) : 0;
            if (dailyEarned >= 14) {
                generateBtn.disabled = true;
                generateBtn.textContent = '🚫 今日积分已满14分';
                generateBtn.style.opacity = '0.5';
                generateBtn.style.cursor = 'not-allowed';
            } else {
                generateBtn.disabled = false;
                generateBtn.textContent = '✨ 生成手机号';
                generateBtn.style.opacity = '1';
                generateBtn.style.cursor = 'pointer';
            }
            if (cooldownTimer) cooldownTimer.textContent = '';
        } else {
            if (cooldownTimer) cooldownTimer.textContent = '⏳ 冷却中: ' + Math.ceil(remaining / 1000) + '秒后可再次生成';
        }
    }, 100);
}

function loadAnnouncementState() {
    var saved = localStorage.getItem('announcement_collapsed');
    if (saved !== null) {
        announcementCollapsed = saved === 'true';
    }
    updateAnnouncementDisplay();
}

function updateAnnouncementDisplay() {
    var announcementList = document.getElementById('announcementList');
    var toggleBtn = document.getElementById('toggleAnnouncementBtn');
    if (announcementList && toggleBtn) {
        if (announcementCollapsed) {
            announcementList.classList.add('collapsed');
            toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
        } else {
            announcementList.classList.remove('collapsed');
            toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
        }
    }
}

function toggleAnnouncement() {
    announcementCollapsed = !announcementCollapsed;
    localStorage.setItem('announcement_collapsed', announcementCollapsed);
    updateAnnouncementDisplay();
}

function formatAnnouncementContent(content) {
    if (!content) return '';
    var formatted = content.replace(/\n/g, '<br>');
    var urlPattern = /(https?:\/\/[a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=]+)/g;
    formatted = formatted.replace(urlPattern, function(url) {
        return '<a href="' + url + '" target="_blank" rel="noopener noreferrer" style="color: #667eea; text-decoration: underline;">' + url + '</a>';
    });
    return formatted;
}

function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadAnnouncements() {
    try {
        var response = await fetch('/api/announcements', { credentials: 'include' });
        var data = await response.json();
        var section = document.getElementById('announcementSection');
        var announcementList = document.getElementById('announcementList');
        if (!section || !announcementList) return;
        if (data.announcements && data.announcements.length > 0) {
            section.style.display = 'block';
            announcementList.innerHTML = '';
            data.announcements.forEach(function(ann) {
                var item = document.createElement('div');
                item.className = 'announcement-item ' + ann.type + (ann.is_sticky ? ' sticky' : '');
                item.innerHTML = '<div class="announcement-title">' + (ann.is_sticky ? '📌 ' : '') + escapeHtml(ann.title) + '</div><div class="announcement-content">' + formatAnnouncementContent(escapeHtml(ann.content)) + '</div><div class="announcement-time">发布于: ' + new Date(ann.created_at).toLocaleString('zh-CN') + '</div>';
                announcementList.appendChild(item);
            });
            loadAnnouncementState();
        } else {
            section.style.display = 'none';
        }
    } catch (error) {
        console.error('Load announcements failed:', error);
    }
}

function applyMailBadge(count) {
    var badge = document.getElementById('mailBadge');
    if (badge) {
        if (count > 0) {
            badge.style.display = 'inline';
            badge.textContent = count > 99 ? '99+' : count;
        } else {
            badge.style.display = 'none';
        }
    }
    var mailLink = document.getElementById('mailLink');
    if (mailLink) {
        mailLink.style.color = count > 0 ? '#ffdd57' : '';
    }
}

function applyAttendanceInfo(data) {
    var totalEl = document.getElementById('attendanceTotalDays');
    if (totalEl) totalEl.textContent = data.totalDays;
    var consecEl = document.getElementById('attendanceConsecutiveDays');
    if (consecEl) consecEl.textContent = data.consecutiveDays;
    var dailyEarned = data.dailyEarnedPoints || 0;
    var attendDailyEl = document.getElementById('attendanceDailyEarned');
    if (attendDailyEl) attendDailyEl.textContent = dailyEarned.toFixed(1);
    var dailyEarnedEl = document.getElementById('dailyEarnedPoints');
    if (dailyEarnedEl) dailyEarnedEl.textContent = dailyEarned.toFixed(2);
    var attendanceBtn = document.getElementById('attendanceBtn');
    var btnWrapper = document.getElementById('attendanceBtnWrapper');
    if (data.hasAttendedToday) {
        if (attendanceBtn) attendanceBtn.remove();
        if (btnWrapper) btnWrapper.style.display = 'none';
        clearAttendanceToken();
    } else {
        if (btnWrapper) btnWrapper.style.display = 'flex';
        if (attendanceBtn) {
            if (dailyEarned < 3) {
                attendanceBtn.disabled = true;
                attendanceBtn.textContent = '⏳ 需达到3积分才可签到 (' + dailyEarned.toFixed(1) + '/3)';
                clearAttendanceToken();
            } else {
                attendanceBtn.disabled = false;
                attendanceBtn.textContent = '✅ 每日签到 (+0.3积分)';
                if (!attendanceToken || Date.now() >= attendanceTokenExpiresAt) {
                    requestAttendanceToken();
                }
            }
        }
    }
    updateGenerateButtonState(dailyEarned);
}

async function checkAuthAndLoad() {
    if (isCheckingAuth) return false;
    isCheckingAuth = true;
    try {
        var data = await apiRequest('/api/check-auth');
        if (data.authenticated) {
            currentUser = data.username;
            isVerified = data.isVerified || false;
            var userInfoEl = document.getElementById('userInfo');
            if (userInfoEl) {
                userInfoEl.innerHTML = '👤 ' + currentUser;
                if (data.isNewUser) {
                    userInfoEl.innerHTML = '👤 ' + currentUser + ' <span class="new-user-badge">新人8折</span>';
                }
            }
            if (data.totalPoints !== undefined) {
                var totalPointsEl = document.getElementById('totalPoints');
                if (totalPointsEl) totalPointsEl.textContent = data.totalPoints.toFixed(2);
                var dailyEarnedEl = document.getElementById('dailyEarnedPoints');
                if (dailyEarnedEl) dailyEarnedEl.textContent = (data.dailyEarnedPoints || 0).toFixed(2);
                var attendanceDailyEarnedEl = document.getElementById('attendanceDailyEarned');
                if (attendanceDailyEarnedEl) {
                    attendanceDailyEarnedEl.textContent = (data.dailyEarnedPoints || 0).toFixed(1);
                }
                updateGenerateButtonState(data.dailyEarnedPoints || 0);
            }
            var identityWarning = document.getElementById('identityWarning');
            var mainContent = document.getElementById('mainContent');
            if (!isVerified) {
                if (identityWarning) identityWarning.style.display = 'flex';
                if (mainContent) mainContent.style.display = 'none';
                isCheckingAuth = false;
                return true;
            } else {
                if (identityWarning) identityWarning.style.display = 'none';
                if (mainContent) mainContent.style.display = 'block';
            }
            await loadAttendanceInfo();
            await updateMailBadge();
            await loadRecords();
            await checkBoostStatus();
            await loadAnnouncements();
            var toggleBtn = document.getElementById('toggleAnnouncementBtn');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', toggleAnnouncement);
            }
            if (data.dailyBonusCode) {
                var dailyBonusSection = document.getElementById('dailyBonusSection');
                if (dailyBonusSection) {
                    dailyBonusSection.style.display = 'flex';
                    var claimBtn = document.getElementById('claimDailyBonusBtn');
                    if (claimBtn) {
                        claimBtn.textContent = '📬 前往邮箱领取';
                        claimBtn.onclick = function() {
                            window.location.href = '/mail.html';
                        };
                    }
                }
            }
            isCheckingAuth = false;
            return true;
        } else {
            isCheckingAuth = false;
            window.location.href = '/login.html';
            return false;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        isCheckingAuth = false;
        window.location.href = '/login.html';
        return false;
    }
}

async function loadAttendanceInfo() {
    try {
        var data = await apiRequest('/api/attendance-info');
        applyAttendanceInfo(data);
    } catch (error) {
        console.error('Load attendance info failed:', error);
    }
}

function clearAttendanceToken() {
    attendanceToken = null;
    attendanceTokenNonce = null;
    attendanceTokenBodyHash = null;
    attendanceTokenExpiresAt = 0;
    if (attendanceTokenTimer) {
        clearInterval(attendanceTokenTimer);
        attendanceTokenTimer = null;
    }
}

async function requestAttendanceToken() {
    try {
        var data = await apiRequest('/api/attendance/token', { method: 'POST', body: JSON.stringify({}) });
        if (data.success && data.token && data.nonce && data.body_hash) {
            attendanceToken = data.token;
            attendanceTokenNonce = data.nonce;
            attendanceTokenBodyHash = data.body_hash;
            attendanceTokenExpiresAt = Date.now() + (data.expires_in || 90) * 1000;
            if (attendanceTokenTimer) clearInterval(attendanceTokenTimer);
            attendanceTokenTimer = setInterval(function() {
                if (!attendanceToken) {
                    clearInterval(attendanceTokenTimer);
                    attendanceTokenTimer = null;
                    return;
                }
                if (Date.now() >= attendanceTokenExpiresAt) {
                    var attendanceBtn = document.getElementById('attendanceBtn');
                    if (attendanceBtn && !attendanceBtn.disabled) {
                        requestAttendanceToken();
                    } else {
                        clearAttendanceToken();
                    }
                }
            }, 15000);
            return true;
        }
        return false;
    } catch (error) {
        if (error.message && !error.message.includes('今日已签到')) {
            console.warn('Request attendance token failed:', error.message);
        }
        return false;
    }
}

async function doAttendance() {
    var attendanceBtn = document.getElementById('attendanceBtn');
    if (!attendanceBtn || attendanceBtn.disabled || attendanceSubmitting) return;

    if (!attendanceToken || Date.now() >= attendanceTokenExpiresAt) {
        var ok = await requestAttendanceToken();
        if (!ok) {
            toastMessage('签到令牌获取失败，请刷新页面重试', 'error');
            return;
        }
    }

    attendanceSubmitting = true;
    attendanceBtn.disabled = true;
    attendanceBtn.textContent = '签到中...';

    var today = new Date();
    var dateStr = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');

    try {
        var bodyHash = await computeAttendanceBodyHash(dateStr, attendanceTokenNonce);
        var data = await apiRequest('/api/attendance', {
            method: 'POST',
            body: JSON.stringify({
                attendance_token: attendanceToken,
                nonce: attendanceTokenNonce,
                date: dateStr,
                body_hash: bodyHash
            })
        });

        clearAttendanceToken();
        await updatePointsDisplay();
        await loadAttendanceInfo();
        await updateMailBadge();

        var toast = document.createElement('div');
        toast.textContent = '✅ 签到成功！获得 ' + data.pointsEarned + ' 积分 | 累计签到: ' + data.totalDays + '天 | 连续签到: ' + data.consecutiveDays + '天';
        toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#27ae60;color:white;padding:10px 20px;border-radius:40px;font-size:14px;z-index:2000;animation:fadeInOut 2s;';
        document.body.appendChild(toast);
        setTimeout(function() { toast.remove(); }, 3000);

        if (data.rewards && data.rewards.length > 0) {
            var rewardList = document.getElementById('rewardList');
            if (rewardList) {
                rewardList.innerHTML = '';
                data.rewards.forEach(function(reward) {
                    var div = document.createElement('div');
                    div.style.padding = '8px 0';
                    if (reward.type === 'points') {
                        div.innerHTML = '🎉 ' + reward.message;
                    } else if (reward.type === 'premium_code') {
                        div.innerHTML = '💎 ' + reward.message + '<br><code style="background:#f0f0f0;padding:4px 8px;border-radius:8px;display:inline-block;margin-top:4px;">' + reward.code + '</code>';
                    } else if (reward.type === 'premium_boost_code') {
                        div.innerHTML = '💄 ' + reward.message + '<br><code style="background:#f0f0f0;padding:4px 8px;border-radius:8px;display:inline-block;margin-top:4px;">' + reward.code + '</code>';
                    }
                    rewardList.appendChild(div);
                });
                var modal = document.getElementById('attendanceRewardModal');
                if (modal) modal.style.display = 'flex';
            }
        }
    } catch (error) {
        toastMessage(error.message, 'error');
        clearAttendanceToken();
        await loadAttendanceInfo();
    } finally {
        attendanceSubmitting = false;
        var btnNow = document.getElementById('attendanceBtn');
        if (btnNow) {
            btnNow.disabled = false;
        }
    }
}

function toastMessage(msg, type) {
    if (!type) type = 'success';
    var toast = document.createElement('div');
    toast.textContent = msg;
    toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:' + (type === 'success' ? '#27ae60' : '#e74c3c') + ';color:white;padding:10px 20px;border-radius:40px;font-size:14px;z-index:2000;animation:fadeInOut 2s;';
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 2000);
}

async function loadRecords() {
    try {
        var data = await apiRequest('/api/get-records');
        var recordsList = document.getElementById('recordsList');
        var recordCountSpan = document.getElementById('recordCount');
        if (!recordsList) return;
        if (data.records.length === 0) {
            recordsList.innerHTML = '<div class="empty-state">📭 暂无授权码记录</div>';
            if (recordCountSpan) recordCountSpan.textContent = '0';
            return;
        }
        if (recordCountSpan) recordCountSpan.textContent = data.records.length;
        recordsList.innerHTML = '';
        data.records.forEach(function(record) {
            var recordDiv = document.createElement('div');
            recordDiv.className = 'record-item' + (record.used ? ' used' : '');
            var timeStr = new Date(record.timestamp).toLocaleString('zh-CN');
            recordDiv.innerHTML = '<div class="record-time">⏰ ' + timeStr + '</div><div class="record-phone">📱 ' + record.hiddenPhone + '</div><div class="record-authcode" style="user-select:none;">🔑 授权码: ' + record.authCode + '</div><div class="record-status ' + (record.used ? 'status-used' : 'status-unused') + '">' + (record.used ? '✅ 已使用' : '⏳ 未使用') + '</div>';
            recordsList.appendChild(recordDiv);
        });
        recordsList.scrollTop = 0;
    } catch (error) {
        if (error.message.includes('请先完成身份认证')) {
            toastMessage('请先完成身份认证', 'error');
        }
        console.error('Load records failed:', error);
    }
}

var attendanceBtnInit = document.getElementById('attendanceBtn');
if (attendanceBtnInit) {
    attendanceBtnInit.addEventListener('click', doAttendance);
}

var logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', async function() {
        try {
            await apiRequest('/api/logout', { method: 'POST' });
            if (boostTimerInterval) clearInterval(boostTimerInterval);
            clearAttendanceToken();
            document.cookie.split(';').forEach(function(c) {
                document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
            });
            window.location.href = '/login.html';
        } catch (error) {
            console.error('Logout failed:', error);
        }
    });
}

var generateBtn = document.getElementById('generateBtn');
if (generateBtn) {
    generateBtn.addEventListener('click', async function() {
        var dailyEarnedEl = document.getElementById('dailyEarnedPoints');
        var dailyEarned = dailyEarnedEl ? (parseFloat(dailyEarnedEl.textContent) || 0) : 0;
        if (dailyEarned >= 14) {
            alert('今日积分已达上限14分，无法继续生成手机号');
            return;
        }
        if (cooldownEndTime && Date.now() < cooldownEndTime) {
            alert('请等待 ' + Math.ceil((cooldownEndTime - Date.now()) / 1000) + ' 秒后再试');
            return;
        }
        var btn = this;
        btn.disabled = true;
        try {
            var data = await apiRequest('/api/generate-phone', { method: 'POST', body: JSON.stringify({}) });
            currentHiddenPhone = data.hiddenPhone;
            currentAuthCode = data.authCode;
            var phoneDisplay = document.getElementById('phoneDisplay');
            if (phoneDisplay) phoneDisplay.innerHTML = '<span style="animation: pulse 0.3s;">' + data.hiddenPhone + '</span>';
            var fullPhoneDisplay = document.getElementById('fullPhoneDisplay');
            if (fullPhoneDisplay) fullPhoneDisplay.style.display = 'none';
            var authCodeInput = document.getElementById('authCodeInput');
            if (authCodeInput) {
                authCodeInput.value = '';
                authCodeInput.placeholder = '输入授权码验证获取积分';
            }
            var verifyBtn = document.getElementById('verifyBtn');
            if (verifyBtn) {
                verifyBtn.disabled = false;
                verifyBtn.textContent = '🔑 验证并获取积分';
            }
            await loadRecords();
            await updatePointsDisplay();
            startCooldown();
        } catch (error) {
            if (error.message.includes('请先完成身份认证')) {
                alert('请先完成身份认证');
                window.location.href = '/identity_verification.html';
            } else {
                alert(error.message);
            }
            var dailyEarnedEl2 = document.getElementById('dailyEarnedPoints');
            var dailyEarned2 = dailyEarnedEl2 ? (parseFloat(dailyEarnedEl2.textContent) || 0) : 0;
            if (dailyEarned2 >= 14) {
                btn.disabled = true;
                btn.textContent = '🚫 今日积分已满14分';
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
            } else {
                btn.disabled = false;
            }
        }
    });
}

var verifyBtnEl = document.getElementById('verifyBtn');
if (verifyBtnEl) {
    verifyBtnEl.addEventListener('click', async function() {
        var authCodeInput = document.getElementById('authCodeInput');
        var authCode = authCodeInput ? authCodeInput.value.trim().toUpperCase() : '';
        if (!authCode) {
            alert('请输入授权码');
            return;
        }
        try {
            var data = await apiRequest('/api/verify-authcode', {
                method: 'POST',
                body: JSON.stringify({ authCode: authCode })
            });
            var fullPhoneDisplay = document.getElementById('fullPhoneDisplay');
            if (fullPhoneDisplay) {
                var maskedDisplay = data.phoneNumber.substring(0, 3) + '*****' + data.phoneNumber.substring(data.phoneNumber.length - 4);
                fullPhoneDisplay.innerHTML = '🎉 <span style="font-size:32px;">✅</span><br><strong>验证成功！获得 ' + data.pointsEarned + ' 积分</strong><br><span style="font-size:13px;color:#666;">📞 完整号码: ' + maskedDisplay + '</span>';
                fullPhoneDisplay.style.display = 'block';
                fullPhoneDisplay.style.background = 'linear-gradient(135deg, #e8f5e9, #c8e6c9)';
            }
            if (authCodeInput) authCodeInput.value = '';
            var verifyBtn = document.getElementById('verifyBtn');
            if (verifyBtn) {
                verifyBtn.disabled = true;
                verifyBtn.textContent = '✅ 已验证';
            }
            await loadRecords();
            await updatePointsDisplay();
            var toast = document.createElement('div');
            toast.textContent = '🎉 验证成功！获得 ' + data.pointsEarned + ' 积分';
            toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#27ae60;color:white;padding:10px 20px;border-radius:40px;font-size:14px;z-index:2000;animation:fadeInOut 2s;';
            document.body.appendChild(toast);
            setTimeout(function() { toast.remove(); }, 3000);
            setTimeout(function() {
                var fpd = document.getElementById('fullPhoneDisplay');
                if (fpd) fpd.style.display = 'none';
            }, 5000);
        } catch (error) {
            if (error.message.includes('请先完成身份认证')) {
                alert('请先完成身份认证');
                window.location.href = '/identity_verification.html';
            } else {
                alert(error.message);
            }
        }
    });
}

var authCodeInputInit = document.getElementById('authCodeInput');
if (authCodeInputInit) {
    authCodeInputInit.addEventListener('input', function(e) {
        var verifyBtn = document.getElementById('verifyBtn');
        if (!verifyBtn) return;
        var value = e.target.value.toUpperCase();
        value = value.replace(/[^A-Z0-9]/g, '');
        e.target.value = value;
        if (value.trim().length > 0 && currentHiddenPhone) {
            verifyBtn.disabled = false;
            verifyBtn.textContent = '🔑 验证并获取积分';
        } else {
            verifyBtn.disabled = true;
        }
    });

    authCodeInputInit.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            var verifyBtn = document.getElementById('verifyBtn');
            if (verifyBtn && !verifyBtn.disabled) {
                verifyBtn.click();
            }
        }
    });
}

var claimDailyBonusBtn = document.getElementById('claimDailyBonusBtn');
if (claimDailyBonusBtn) {
    claimDailyBonusBtn.addEventListener('click', async function() {
        try {
            var data = await apiRequest('/api/claim-daily-bonus', { method: 'POST', body: JSON.stringify({}) });
            if (data.success) {
                alert('奖励已领取！卡密已放入背包');
                var section = document.getElementById('dailyBonusSection');
                if (section) section.style.display = 'none';
                await updateMailBadge();
            }
        } catch (error) {
            if (error.message.includes('请先完成身份认证')) {
                alert('请先完成身份认证');
                window.location.href = '/identity_verification.html';
            } else {
                alert(error.message);
            }
        }
    });
}

var cancellationModal = document.getElementById('cancellationModal');
var cancellationBtn = document.getElementById('cancellationBtn');
var confirmCancellationBtn = document.getElementById('confirmCancellationBtn');
var closeCancellationModal = document.getElementById('closeCancellationModal');
var cancelEmailMethod = document.getElementById('cancelEmailMethod');

if (cancellationBtn) {
    cancellationBtn.addEventListener('click', function() {
        if (cancellationModal) cancellationModal.style.display = 'flex';
        var cancelEmailInput = document.getElementById('cancelEmailInput');
        if (cancelEmailInput) cancelEmailInput.value = '';
        var cancelEmailCode = document.getElementById('cancelEmailCode');
        if (cancelEmailCode) cancelEmailCode.value = '';
        var promiseCheckbox = document.getElementById('promiseCheckbox');
        if (promiseCheckbox) promiseCheckbox.checked = false;
        var cancellationMessage = document.getElementById('cancellationMessage');
        if (cancellationMessage) cancellationMessage.textContent = '';
        var cancelEmailCountdown = document.getElementById('cancelEmailCountdown');
        if (cancelEmailCountdown) cancelEmailCountdown.textContent = '';
        var sendCancelEmailCodeBtn = document.getElementById('sendCancelEmailCodeBtn');
        if (sendCancelEmailCodeBtn) {
            sendCancelEmailCodeBtn.disabled = false;
            sendCancelEmailCodeBtn.textContent = '发送验证码';
        }
        if (cancelEmailCodeTimer) {
            clearInterval(cancelEmailCodeTimer);
            cancelEmailCodeTimer = null;
            cancelEmailCountdownValue = 0;
        }
        if (cancelEmailMethod) cancelEmailMethod.style.display = 'block';
        if (confirmCancellationBtn) confirmCancellationBtn.textContent = '确认注销 (邮箱验证)';
    });
}

if (closeCancellationModal) {
    closeCancellationModal.addEventListener('click', function() {
        if (cancellationModal) cancellationModal.style.display = 'none';
        if (cancelEmailCodeTimer) {
            clearInterval(cancelEmailCodeTimer);
            cancelEmailCodeTimer = null;
            cancelEmailCountdownValue = 0;
        }
    });
}

var sendCancelEmailCodeBtnEl = document.getElementById('sendCancelEmailCodeBtn');
if (sendCancelEmailCodeBtnEl) {
    sendCancelEmailCodeBtnEl.addEventListener('click', async function() {
        var cancelEmailInput = document.getElementById('cancelEmailInput');
        var email = cancelEmailInput ? cancelEmailInput.value.trim().toLowerCase() : '';
        var btn = this;
        var msg = document.getElementById('cancellationMessage');

        if (!email) {
            if (msg) {
                msg.textContent = '请输入您的绑定邮箱';
                msg.style.color = 'red';
            }
            return;
        }

        var emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(email)) {
            if (msg) {
                msg.textContent = '请输入有效的邮箱地址';
                msg.style.color = 'red';
            }
            return;
        }

        btn.disabled = true;
        if (msg) {
            msg.textContent = '发送中...';
            msg.style.color = '#666';
        }

        try {
            var data = await apiRequest('/api/send-verification-code', {
                method: 'POST',
                body: JSON.stringify({
                    email: email,
                    purpose: '注销'
                })
            });

            if (data.success) {
                if (msg) {
                    msg.textContent = data.message || '验证码已发送至您的邮箱';
                    msg.style.color = 'green';
                }
                startCancelEmailCountdown(60, btn);
            } else {
                if (msg) {
                    msg.textContent = data.error || '发送失败';
                    msg.style.color = 'red';
                }
                btn.disabled = false;
            }
        } catch (error) {
            if (msg) {
                msg.textContent = error.message || '发送失败，请重试';
                msg.style.color = 'red';
            }
            btn.disabled = false;
        }
    });
}

function startCancelEmailCountdown(seconds, btn) {
    cancelEmailCountdownValue = seconds;
    var countdownEl = document.getElementById('cancelEmailCountdown');
    if (cancelEmailCodeTimer) clearInterval(cancelEmailCodeTimer);
    btn.disabled = true;
    btn.textContent = seconds + 's';
    cancelEmailCodeTimer = setInterval(function() {
        cancelEmailCountdownValue--;
        if (cancelEmailCountdownValue <= 0) {
            clearInterval(cancelEmailCodeTimer);
            cancelEmailCodeTimer = null;
            btn.disabled = false;
            btn.textContent = '重新发送';
            if (countdownEl) countdownEl.textContent = '';
        } else {
            btn.textContent = cancelEmailCountdownValue + 's';
            if (countdownEl) countdownEl.textContent = '⏱️ ' + cancelEmailCountdownValue + '秒后可重新发送';
        }
    }, 1000);
}

if (confirmCancellationBtn) {
    confirmCancellationBtn.addEventListener('click', async function() {
        var messageDiv = document.getElementById('cancellationMessage');
        var promiseCheckbox = document.getElementById('promiseCheckbox');
        var promiseAgreed = promiseCheckbox ? promiseCheckbox.checked : false;
        var btn = this;

        if (!promiseAgreed) {
            if (messageDiv) {
                messageDiv.textContent = '请阅读并同意注销承诺书';
                messageDiv.style.color = 'red';
            }
            return;
        }

        var cancelEmailInput = document.getElementById('cancelEmailInput');
        var cancelEmailCode = document.getElementById('cancelEmailCode');
        var email = cancelEmailInput ? cancelEmailInput.value.trim().toLowerCase() : '';
        var verificationCode = cancelEmailCode ? cancelEmailCode.value.trim() : '';

        if (!email || !verificationCode) {
            if (messageDiv) {
                messageDiv.textContent = '请填写邮箱和验证码';
                messageDiv.style.color = 'red';
            }
            return;
        }

        if (verificationCode.length !== 6 || !/^\d{6}$/.test(verificationCode)) {
            if (messageDiv) {
                messageDiv.textContent = '验证码为6位数字，请检查输入';
                messageDiv.style.color = 'red';
            }
            return;
        }

        if (messageDiv) {
            messageDiv.textContent = '正在处理注销请求...';
            messageDiv.style.color = '#666';
        }
        btn.disabled = true;

        try {
            var data = await apiRequest('/api/account/cancel', {
                method: 'POST',
                body: JSON.stringify({
                    email: email,
                    verification_code: verificationCode,
                    promise_agreed: promiseAgreed
                })
            });

            if (messageDiv) {
                messageDiv.textContent = data.message || '注销成功';
                messageDiv.style.color = 'green';
            }
            setTimeout(function() {
                if (cancellationModal) cancellationModal.style.display = 'none';
                document.cookie.split(';').forEach(function(c) {
                    document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
                });
                window.location.href = '/login.html';
            }, 2000);
        } catch (error) {
            if (messageDiv) {
                messageDiv.textContent = error.message || '注销失败，请重试';
                messageDiv.style.color = 'red';
            }
            btn.disabled = false;
        }
    });
}

window.addEventListener('click', function(event) {
    if (event.target === cancellationModal) {
        if (cancellationModal) cancellationModal.style.display = 'none';
        if (cancelEmailCodeTimer) {
            clearInterval(cancelEmailCodeTimer);
            cancelEmailCodeTimer = null;
            cancelEmailCountdownValue = 0;
        }
    }
});

fetchCsrfToken().catch(function(e) {
    console.warn('CSRF pre-fetch failed:', e);
});

checkAuthAndLoad();

setInterval(function() {
    if (document.hidden) return;
    updateMailBadge();
}, 30000);
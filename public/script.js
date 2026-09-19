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

var currentUser = null;
var currentHiddenPhone = null;
var currentAuthCode = null;
var currentFullPhone = null;
var cooldownInterval = null;
var cooldownEndTime = null;
var isCheckingAuth = false;
var boostActive = false;
var boostExpiresIn = 0;
var boostTimerInterval = null;
var isVerified = false;
var announcementCollapsed = false;
var pendingVerificationData = null;

function updateGenerateButtonState(dailyEarned) {
    var generateBtn = document.getElementById('generateBtn');
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
        document.getElementById('totalPoints').textContent = data.totalPoints.toFixed(2);
        document.getElementById('dailyEarnedPoints').textContent = data.dailyEarnedPoints.toFixed(2);
        var dailyEarnedEl = document.getElementById('attendanceDailyEarned');
        if (dailyEarnedEl) {
            dailyEarnedEl.textContent = data.dailyEarnedPoints.toFixed(1);
        }
        updateGenerateButtonState(data.dailyEarnedPoints);
        if (data.isNewUser) {
            var userInfo = document.getElementById('userInfo');
            if (!userInfo.querySelector('.new-user-badge')) {
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
        var count = data.total || 0;
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
            if (count > 0) {
                mailLink.style.color = '#ffdd57';
            } else {
                mailLink.style.color = '';
            }
        }
    } catch (e) {
        console.error('Update mail badge failed:', e);
    }
}

async function checkBoostStatus() {
    try {
        var data = await apiRequest('/api/get-boost-status');
        boostActive = data.boostActive;
        boostExpiresIn = data.boostExpiresIn;
        var boostType = data.boostType || 'normal';
        var boostIndicator = document.getElementById('boostIndicator');
        var boostTimer = document.getElementById('boostTimer');
        if (boostActive && boostExpiresIn > 0) {
            if (boostIndicator) {
                boostIndicator.style.display = 'inline-flex';
                var icon = boostType === 'premium' ? '💎' : '⚡';
                var label = boostType === 'premium' ? '高级加成' : '加成';
                boostIndicator.innerHTML = icon + ' ' + label + ' <span id="boostTimer">' + formatBoostTime(boostExpiresIn) + '</span>';
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
            var dailyEarned = parseFloat(document.getElementById('dailyEarnedPoints').textContent) || 0;
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
            cooldownTimer.textContent = '';
        } else {
            cooldownTimer.textContent = '⏳ 冷却中: ' + Math.ceil(remaining / 1000) + '秒后可再次生成';
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

async function checkAuthAndLoad() {
    if (isCheckingAuth) return false;
    isCheckingAuth = true;
    try {
        var data = await apiRequest('/api/check-auth');
        if (data.authenticated) {
            currentUser = data.username;
            isVerified = data.isVerified || false;
            document.getElementById('userInfo').innerHTML = '👤 ' + currentUser;
            if (data.isNewUser) {
                document.getElementById('userInfo').innerHTML = '👤 ' + currentUser + ' <span class="new-user-badge">新人8折</span>';
            }
            if (data.hasCancellationCode) {
                document.getElementById('userInfo').innerHTML += '<span class="cancellation-badge">已购注销卡</span>';
            }
            if (data.totalPoints !== undefined) {
                document.getElementById('totalPoints').textContent = data.totalPoints.toFixed(2);
                document.getElementById('dailyEarnedPoints').textContent = (data.dailyEarnedPoints || 0).toFixed(2);
                var dailyEarnedEl = document.getElementById('attendanceDailyEarned');
                if (dailyEarnedEl) {
                    dailyEarnedEl.textContent = (data.dailyEarnedPoints || 0).toFixed(1);
                }
                updateGenerateButtonState(data.dailyEarnedPoints || 0);
            } else {
                await updatePointsDisplay();
            }
            var identityWarning = document.getElementById('identityWarning');
            var mainContent = document.getElementById('mainContent');
            if (!isVerified) {
                identityWarning.style.display = 'flex';
                mainContent.style.display = 'none';
                isCheckingAuth = false;
                return true;
            } else {
                identityWarning.style.display = 'none';
                mainContent.style.display = 'block';
            }
            await loadRecords();
            await checkBoostStatus();
            await loadAttendanceInfo();
            await loadAnnouncements();
            await updateMailBadge();
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
        document.getElementById('attendanceTotalDays').textContent = data.totalDays;
        document.getElementById('attendanceConsecutiveDays').textContent = data.consecutiveDays;
        var dailyEarned = data.dailyEarnedPoints || 0;
        document.getElementById('attendanceDailyEarned').textContent = dailyEarned.toFixed(1);
        document.getElementById('dailyEarnedPoints').textContent = dailyEarned.toFixed(2);
        var attendanceBtn = document.getElementById('attendanceBtn');
        var btnWrapper = document.getElementById('attendanceBtnWrapper');
        if (data.hasAttendedToday) {
            if (attendanceBtn) {
                attendanceBtn.remove();
            }
            if (btnWrapper) {
                btnWrapper.style.display = 'none';
            }
        } else {
            if (btnWrapper) {
                btnWrapper.style.display = 'flex';
            }
            if (attendanceBtn) {
                if (dailyEarned < 3) {
                    attendanceBtn.disabled = true;
                    attendanceBtn.textContent = '⏳ 需达到3积分才可签到 (' + dailyEarned.toFixed(1) + '/3)';
                } else {
                    attendanceBtn.disabled = false;
                    attendanceBtn.textContent = '✅ 每日签到 (+0.3积分)';
                }
            }
        }
        updateGenerateButtonState(dailyEarned);
    } catch (error) {
        console.error('Load attendance info failed:', error);
    }
}

async function doAttendance() {
    var attendanceBtn = document.getElementById('attendanceBtn');
    if (!attendanceBtn || attendanceBtn.disabled) return;
    attendanceBtn.disabled = true;
    attendanceBtn.textContent = '签到中...';
    try {
        var data = await apiRequest('/api/attendance', { method: 'POST' });
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
            rewardList.innerHTML = '';
            data.rewards.forEach(function(reward) {
                var div = document.createElement('div');
                div.style.padding = '8px 0';
                if (reward.type === 'points') {
                    div.innerHTML = '🎉 ' + reward.message;
                } else if (reward.type === 'premium_code') {
                    div.innerHTML = '💎 ' + reward.message + '<br><code style="background:#f0f0f0;padding:4px 8px;border-radius:8px;display:inline-block;margin-top:4px;">' + reward.code + '</code>';
                } else if (reward.type === 'boost_code') {
                    div.innerHTML = '⚡ ' + reward.message + '<br><code style="background:#f0f0f0;padding:4px 8px;border-radius:8px;display:inline-block;margin-top:4px;">' + reward.code + '</code>';
                } else if (reward.type === 'reset_code') {
                    div.innerHTML = '🔐 ' + reward.message + '<br><code style="background:#f0f0f0;padding:4px 8px;border-radius:8px;display:inline-block;margin-top:4px;">' + reward.code + '</code>';
                }
                rewardList.appendChild(div);
            });
            document.getElementById('attendanceRewardModal').style.display = 'flex';
        }
    } catch (error) {
        toastMessage(error.message, 'error');
        await loadAttendanceInfo();
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
        if (data.records.length === 0) {
            recordsList.innerHTML = '<div class="empty-state">📭 暂无授权码记录</div>';
            recordCountSpan.textContent = '0';
            return;
        }
        recordCountSpan.textContent = data.records.length;
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

var attendanceBtn = document.getElementById('attendanceBtn');
if (attendanceBtn) {
    attendanceBtn.addEventListener('click', doAttendance);
}

document.getElementById('logoutBtn').addEventListener('click', async function() {
    try {
        await apiRequest('/api/logout', { method: 'POST' });
        if (boostTimerInterval) clearInterval(boostTimerInterval);
        document.cookie.split(';').forEach(function(c) {
            document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
        });
        window.location.href = '/login.html';
    } catch (error) {
        console.error('Logout failed:', error);
    }
});

document.getElementById('generateBtn').addEventListener('click', async function() {
    var dailyEarned = parseFloat(document.getElementById('dailyEarnedPoints').textContent) || 0;
    if (dailyEarned >= 14) {
        alert('今日积分已达上限14分，无法继续生成手机号');
        return;
    }
    if (cooldownEndTime && Date.now() < cooldownEndTime) {
        alert('请等待 ' + Math.ceil((cooldownEndTime - Date.now()) / 1000) + ' 秒后再试');
        return;
    }
    var generateBtn = document.getElementById('generateBtn');
    generateBtn.disabled = true;
    try {
        var data = await apiRequest('/api/generate-phone', { method: 'POST' });
        currentHiddenPhone = data.hiddenPhone;
        currentAuthCode = data.authCode;
        pendingVerificationData = null;
        document.getElementById('phoneDisplay').innerHTML = '<span style="animation: pulse 0.3s;">' + data.hiddenPhone + '</span>';
        document.getElementById('fullPhoneDisplay').style.display = 'none';
        document.getElementById('copyFullPhoneBtn').style.display = 'none';
        document.getElementById('authCodeInput').value = '';
        document.getElementById('verifyBtn').disabled = false;
        document.getElementById('authCodeInput').placeholder = '输入授权码验证后回填完整号码';
        document.getElementById('verifyBtn').textContent = '🔑 验证授权码';
        var verifySection = document.querySelector('.verify-section');
        var existingBackfill = document.getElementById('backfillSection');
        if (existingBackfill) existingBackfill.remove();
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
        var dailyEarned2 = parseFloat(document.getElementById('dailyEarnedPoints').textContent) || 0;
        if (dailyEarned2 >= 14) {
            generateBtn.disabled = true;
            generateBtn.textContent = '🚫 今日积分已满14分';
            generateBtn.style.opacity = '0.5';
            generateBtn.style.cursor = 'not-allowed';
        } else {
            generateBtn.disabled = false;
        }
    }
});

document.getElementById('verifyBtn').addEventListener('click', async function() {
    var authCode = document.getElementById('authCodeInput').value.trim().toUpperCase();
    if (!authCode) {
        alert('请输入授权码');
        return;
    }
    try {
        var data = await apiRequest('/api/verify-authcode', {
            method: 'POST',
            body: JSON.stringify({ authCode: authCode })
        });
        pendingVerificationData = {
            fullPhone: data.phoneNumber,
            pointsEarned: data.pointsEarned,
            originalPoints: data.originalPoints,
            bonusMultiplier: data.bonusMultiplier,
            authCode: authCode
        };
        currentFullPhone = data.phoneNumber;
        var fullPhoneDisplay = document.getElementById('fullPhoneDisplay');
        var maskedDisplay = currentFullPhone.substring(0, 3) + '*****' + currentFullPhone.substring(currentFullPhone.length - 4);
        fullPhoneDisplay.innerHTML = '📞 完整号码: <span style="font-family:monospace;font-size:28px;color:#667eea;">' + maskedDisplay + '</span><br><span style="font-size:14px;color:#666;">验证成功！请点击下方按钮回填完整号码以获取积分</span>';
        fullPhoneDisplay.style.display = 'block';
        var copyBtn = document.getElementById('copyFullPhoneBtn');
        copyBtn.textContent = '📋 回填完整号码并获取积分';
        copyBtn.style.display = 'block';
        copyBtn.style.background = 'linear-gradient(135deg, #27ae60, #2ecc71)';
        copyBtn.onclick = confirmBackfillAndClaim;
        var existingBackfill = document.getElementById('backfillSection');
        if (!existingBackfill) {
            var backfillSection = document.createElement('div');
            backfillSection.id = 'backfillSection';
            backfillSection.style.cssText = 'margin-top:16px;padding:16px;background:#f0f8ff;border-radius:16px;border:2px dashed #667eea;display:block;';
            backfillSection.innerHTML = '<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;"><label style="font-size:14px;font-weight:600;color:#333;">📝 回填完整号码:</label><input type="text" id="backfillInput" placeholder="请输入完整手机号" style="flex:2;min-width:200px;padding:12px 16px;border:2px solid #e0e0e0;border-radius:60px;font-size:15px;font-family:monospace;outline:none;transition:all 0.3s;"><button id="backfillBtn" style="padding:12px 24px;background:linear-gradient(135deg,#27ae60,#2ecc71);color:white;border:none;border-radius:60px;font-size:15px;font-weight:600;cursor:pointer;transition:all 0.3s;">✅ 确认回填</button></div><div style="margin-top:8px;font-size:12px;color:#888;">💡 请输入完整号码 <strong style="color:#667eea;">' + currentFullPhone + '</strong> 以验证身份并获取积分</div>';
            var verifySection = document.querySelector('.verify-section');
            verifySection.appendChild(backfillSection);
            var backfillInput = document.getElementById('backfillInput');
            var backfillBtn = document.getElementById('backfillBtn');
            backfillInput.addEventListener('input', function(e) {
                var val = e.target.value.replace(/\D/g, '');
                e.target.value = val;
                if (val.length === 11) {
                    backfillBtn.style.background = 'linear-gradient(135deg, #27ae60, #2ecc71)';
                    backfillBtn.style.opacity = '1';
                } else {
                    backfillBtn.style.background = '#95a5a6';
                    backfillBtn.style.opacity = '0.6';
                }
            });
            backfillInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && backfillInput.value.length === 11) {
                    document.getElementById('backfillBtn').click();
                }
            });
            backfillBtn.addEventListener('click', function() {
                var inputVal = document.getElementById('backfillInput').value.trim();
                if (inputVal.length !== 11) {
                    alert('请输入完整的11位手机号码');
                    return;
                }
                if (inputVal !== currentFullPhone) {
                    alert('❌ 号码不匹配！请输入正确的完整号码: ' + currentFullPhone);
                    return;
                }
                claimPointsAfterBackfill();
            });
            backfillInput.focus();
        }
        document.getElementById('authCodeInput').value = '';
        document.getElementById('verifyBtn').disabled = true;
        document.getElementById('verifyBtn').textContent = '✅ 已验证';
        var toast = document.createElement('div');
        toast.textContent = '✅ 授权码验证成功！请回填完整号码获取积分';
        toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#667eea;color:white;padding:10px 20px;border-radius:40px;font-size:14px;z-index:2000;animation:fadeInOut 2s;';
        document.body.appendChild(toast);
        setTimeout(function() { toast.remove(); }, 3000);
    } catch (error) {
        if (error.message.includes('请先完成身份认证')) {
            alert('请先完成身份认证');
            window.location.href = '/identity_verification.html';
        } else {
            alert(error.message);
        }
    }
});

function confirmBackfillAndClaim() {
    var existingBackfill = document.getElementById('backfillSection');
    if (!existingBackfill) {
        var backfillSection = document.createElement('div');
        backfillSection.id = 'backfillSection';
        backfillSection.style.cssText = 'margin-top:16px;padding:16px;background:#f0f8ff;border-radius:16px;border:2px dashed #667eea;display:block;';
        backfillSection.innerHTML = '<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;"><label style="font-size:14px;font-weight:600;color:#333;">📝 回填完整号码:</label><input type="text" id="backfillInput" placeholder="请输入完整手机号" style="flex:2;min-width:200px;padding:12px 16px;border:2px solid #e0e0e0;border-radius:60px;font-size:15px;font-family:monospace;outline:none;transition:all 0.3s;"><button id="backfillBtn" style="padding:12px 24px;background:linear-gradient(135deg,#27ae60,#2ecc71);color:white;border:none;border-radius:60px;font-size:15px;font-weight:600;cursor:pointer;transition:all 0.3s;">✅ 确认回填</button></div><div style="margin-top:8px;font-size:12px;color:#888;">💡 请输入完整号码 <strong style="color:#667eea;">' + currentFullPhone + '</strong> 以验证身份并获取积分</div>';
        var verifySection = document.querySelector('.verify-section');
        verifySection.appendChild(backfillSection);
        var backfillInput = document.getElementById('backfillInput');
        var backfillBtn = document.getElementById('backfillBtn');
        backfillInput.addEventListener('input', function(e) {
            var val = e.target.value.replace(/\D/g, '');
            e.target.value = val;
            if (val.length === 11) {
                backfillBtn.style.background = 'linear-gradient(135deg, #27ae60, #2ecc71)';
                backfillBtn.style.opacity = '1';
            } else {
                backfillBtn.style.background = '#95a5a6';
                backfillBtn.style.opacity = '0.6';
            }
        });
        backfillInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && backfillInput.value.length === 11) {
                document.getElementById('backfillBtn').click();
            }
        });
        backfillBtn.addEventListener('click', function() {
            var inputVal = document.getElementById('backfillInput').value.trim();
            if (inputVal.length !== 11) {
                alert('请输入完整的11位手机号码');
                return;
            }
            if (inputVal !== currentFullPhone) {
                alert('❌ 号码不匹配！请输入正确的完整号码: ' + currentFullPhone);
                return;
            }
            claimPointsAfterBackfill();
        });
        backfillInput.focus();
    } else {
        existingBackfill.style.display = 'block';
        var input = document.getElementById('backfillInput');
        if (input) input.focus();
    }
}

async function claimPointsAfterBackfill() {
    if (!pendingVerificationData) {
        alert('请先验证授权码');
        return;
    }
    var backfillBtn = document.getElementById('backfillBtn');
    if (backfillBtn) {
        backfillBtn.disabled = true;
        backfillBtn.textContent = '⏳ 处理中...';
    }
    try {
        var data = await apiRequest('/api/claim-backfill-reward', {
            method: 'POST',
            body: JSON.stringify({
                phoneNumber: currentFullPhone,
                authCode: pendingVerificationData.authCode || ''
            })
        });
        pendingVerificationData = null;
        var fullPhoneDisplay = document.getElementById('fullPhoneDisplay');
        var bonusText = '';
        if (data.bonusMultiplier) {
            var multiplierDesc = '';
            if (data.bonusMultiplier === 2.47) {
                multiplierDesc = ' (时段30% + 高级加成90% = 120%)';
            } else if (data.bonusMultiplier === 1.95) {
                multiplierDesc = ' (时段30% + 加成50% = 80%)';
            } else if (data.bonusMultiplier === 1.9) {
                multiplierDesc = ' (高级加成90%)';
            } else if (data.bonusMultiplier === 1.5) {
                multiplierDesc = ' (加成卡50%)';
            } else if (data.bonusMultiplier === 1.3) {
                multiplierDesc = ' (时段30%)';
            }
            bonusText = '<br>🎁 积分加成' + multiplierDesc + '！ (' + data.originalPoints + ' → ' + data.pointsEarned + ')';
        }
        fullPhoneDisplay.innerHTML = '🎉 <span style="font-size:32px;">✅</span><br><strong>回填成功！获得 ' + data.pointsEarned + ' 积分</strong>' + bonusText + '<br><span style="font-size:13px;color:#666;">📞 完整号码: ' + currentFullPhone + '</span>';
        fullPhoneDisplay.style.background = 'linear-gradient(135deg, #e8f5e9, #c8e6c9)';
        var backfillSection = document.getElementById('backfillSection');
        if (backfillSection) {
            backfillSection.style.display = 'none';
        }
        document.getElementById('copyFullPhoneBtn').style.display = 'none';
        await loadRecords();
        await updatePointsDisplay();
        var toast = document.createElement('div');
        toast.textContent = '🎉 回填成功！获得 ' + data.pointsEarned + ' 积分';
        toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#27ae60;color:white;padding:10px 20px;border-radius:40px;font-size:14px;z-index:2000;animation:fadeInOut 2s;';
        document.body.appendChild(toast);
        setTimeout(function() { toast.remove(); }, 3000);
        setTimeout(function() {
            document.getElementById('fullPhoneDisplay').style.display = 'none';
        }, 5000);
    } catch (error) {
        alert(error.message || '回填失败，请重试');
        if (backfillBtn) {
            backfillBtn.disabled = false;
            backfillBtn.textContent = '✅ 确认回填';
        }
    }
}

document.getElementById('authCodeInput').addEventListener('input', function(e) {
    var verifyBtn = document.getElementById('verifyBtn');
    var value = e.target.value.toUpperCase();
    value = value.replace(/[^A-Z0-9]/g, '');
    e.target.value = value;
    if (value.trim().length > 0 && currentHiddenPhone) {
        verifyBtn.disabled = false;
        verifyBtn.textContent = '🔑 验证授权码';
    } else {
        verifyBtn.disabled = true;
    }
});

document.getElementById('authCodeInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !document.getElementById('verifyBtn').disabled) {
        document.getElementById('verifyBtn').click();
    }
});

document.getElementById('claimDailyBonusBtn').addEventListener('click', async function() {
    try {
        var data = await apiRequest('/api/claim-daily-bonus', { method: 'POST' });
        if (data.success) {
            alert('奖励已领取！卡密已放入背包');
            document.getElementById('dailyBonusSection').style.display = 'none';
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

var cancellationModal = document.getElementById('cancellationModal');
var cancellationBtn = document.getElementById('cancellationBtn');
var confirmCancellationBtn = document.getElementById('confirmCancellationBtn');
var closeCancellationModal = document.getElementById('closeCancellationModal');
var cancelTabCard = document.getElementById('cancelTabCard');
var cancelTabEmail = document.getElementById('cancelTabEmail');
var cancelCardMethod = document.getElementById('cancelCardMethod');
var cancelEmailMethod = document.getElementById('cancelEmailMethod');

function switchCancelMethod(method) {
    if (method === 'card') {
        cancelTabCard.className = 'cancel-tab-btn active';
        cancelTabCard.style.background = 'linear-gradient(135deg,#667eea,#764ba2)';
        cancelTabCard.style.color = 'white';
        cancelTabEmail.className = 'cancel-tab-btn';
        cancelTabEmail.style.background = 'transparent';
        cancelTabEmail.style.color = '#666';
        cancelCardMethod.style.display = 'block';
        cancelEmailMethod.style.display = 'none';
        confirmCancellationBtn.textContent = '确认注销 (卡密)';
        document.getElementById('cancellationMessage').textContent = '';
    } else {
        cancelTabEmail.className = 'cancel-tab-btn active';
        cancelTabEmail.style.background = 'linear-gradient(135deg,#667eea,#764ba2)';
        cancelTabEmail.style.color = 'white';
        cancelTabCard.className = 'cancel-tab-btn';
        cancelTabCard.style.background = 'transparent';
        cancelTabCard.style.color = '#666';
        cancelCardMethod.style.display = 'none';
        cancelEmailMethod.style.display = 'block';
        confirmCancellationBtn.textContent = '确认注销 (邮箱验证)';
        document.getElementById('cancellationMessage').textContent = '';
    }
}

if (cancelTabCard) {
    cancelTabCard.addEventListener('click', function() { switchCancelMethod('card'); });
}
if (cancelTabEmail) {
    cancelTabEmail.addEventListener('click', function() { switchCancelMethod('email'); });
}

cancellationBtn.addEventListener('click', async function() {
    cancellationModal.style.display = 'flex';
    document.getElementById('cancelCardEmail').value = '';
    document.getElementById('cancelCardPassword').value = '';
    document.getElementById('cancelCardCode').value = '';
    document.getElementById('cancelEmailInput').value = '';
    document.getElementById('cancelEmailCode').value = '';
    document.getElementById('promiseCheckbox').checked = false;
    document.getElementById('cancellationMessage').textContent = '';
    document.getElementById('cancelEmailCountdown').textContent = '';
    document.getElementById('sendCancelEmailCodeBtn').disabled = false;
    document.getElementById('sendCancelEmailCodeBtn').textContent = '发送验证码';
    if (cancelEmailCodeTimer) {
        clearInterval(cancelEmailCodeTimer);
        cancelEmailCodeTimer = null;
        cancelEmailCountdownValue = 0;
    }
    switchCancelMethod('card');
});

closeCancellationModal.addEventListener('click', function() {
    cancellationModal.style.display = 'none';
    if (cancelEmailCodeTimer) {
        clearInterval(cancelEmailCodeTimer);
        cancelEmailCodeTimer = null;
        cancelEmailCountdownValue = 0;
    }
});

var cancelEmailCodeTimer = null;
var cancelEmailCountdownValue = 0;

document.getElementById('sendCancelEmailCodeBtn').addEventListener('click', async function() {
    var email = document.getElementById('cancelEmailInput').value.trim().toLowerCase();
    var btn = this;
    var msg = document.getElementById('cancellationMessage');

    if (!email) {
        msg.textContent = '请输入您的绑定邮箱';
        msg.style.color = 'red';
        return;
    }

    var emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(email)) {
        msg.textContent = '请输入有效的邮箱地址';
        msg.style.color = 'red';
        return;
    }

    btn.disabled = true;
    msg.textContent = '发送中...';
    msg.style.color = '#666';

    try {
        var data = await apiRequest('/api/send-verification-code', {
            method: 'POST',
            body: JSON.stringify({
                email: email,
                purpose: '注销'
            })
        });

        if (data.success) {
            msg.textContent = data.message || '验证码已发送至您的邮箱';
            msg.style.color = 'green';
            startCancelEmailCountdown(60, btn);
        } else {
            msg.textContent = data.error || '发送失败';
            msg.style.color = 'red';
            btn.disabled = false;
        }
    } catch (error) {
        msg.textContent = error.message || '发送失败，请重试';
        msg.style.color = 'red';
        btn.disabled = false;
    }
});

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
            countdownEl.textContent = '';
        } else {
            btn.textContent = cancelEmailCountdownValue + 's';
            countdownEl.textContent = '⏱️ ' + cancelEmailCountdownValue + '秒后可重新发送';
        }
    }, 1000);
}

confirmCancellationBtn.addEventListener('click', async function() {
    var messageDiv = document.getElementById('cancellationMessage');
    var promiseAgreed = document.getElementById('promiseCheckbox').checked;

    if (!promiseAgreed) {
        messageDiv.textContent = '请阅读并同意注销承诺书';
        messageDiv.style.color = 'red';
        return;
    }

    if (currentCancelMethod === 'card') {
        var email = document.getElementById('cancelCardEmail').value.trim().toLowerCase();
        var password = document.getElementById('cancelCardPassword').value;
        var cancellationCode = document.getElementById('cancelCardCode').value.trim().toUpperCase();

        if (!email || !password || !cancellationCode) {
            messageDiv.textContent = '请填写所有字段（邮箱、密码、卡密）';
            messageDiv.style.color = 'red';
            return;
        }

        var codePattern = /^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/;
        if (!codePattern.test(cancellationCode)) {
            messageDiv.textContent = '卡密格式不正确，应为 XXXX-XXXX-XXXX-XXXX';
            messageDiv.style.color = 'red';
            return;
        }

        messageDiv.textContent = '正在处理注销请求...';
        messageDiv.style.color = '#666';
        this.disabled = true;

        try {
            var data = await apiRequest('/api/use-cancellation-code', {
                method: 'POST',
                body: JSON.stringify({
                    email: email,
                    password: password,
                    cancellationCode: cancellationCode,
                    promiseAgreed: promiseAgreed
                })
            });

            messageDiv.textContent = data.message;
            messageDiv.style.color = 'green';
            setTimeout(function() {
                cancellationModal.style.display = 'none';
                document.cookie.split(';').forEach(function(c) {
                    document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
                });
                window.location.href = '/login.html';
            }, 2000);
        } catch (error) {
            messageDiv.textContent = error.message;
            messageDiv.style.color = 'red';
            this.disabled = false;
        }
    } else {
        var email2 = document.getElementById('cancelEmailInput').value.trim().toLowerCase();
        var verificationCode = document.getElementById('cancelEmailCode').value.trim();

        if (!email2 || !verificationCode) {
            messageDiv.textContent = '请填写邮箱和验证码';
            messageDiv.style.color = 'red';
            return;
        }

        if (verificationCode.length !== 6 || !/^\d{6}$/.test(verificationCode)) {
            messageDiv.textContent = '验证码为6位数字，请检查输入';
            messageDiv.style.color = 'red';
            return;
        }

        messageDiv.textContent = '正在处理注销请求...';
        messageDiv.style.color = '#666';
        this.disabled = true;

        try {
            var data2 = await apiRequest('/api/account/cancel', {
                method: 'POST',
                body: JSON.stringify({
                    email: email2,
                    verification_code: verificationCode,
                    promise_agreed: promiseAgreed
                })
            });

            messageDiv.textContent = data2.message;
            messageDiv.style.color = 'green';
            setTimeout(function() {
                cancellationModal.style.display = 'none';
                document.cookie.split(';').forEach(function(c) {
                    document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
                });
                window.location.href = '/login.html';
            }, 2000);
        } catch (error) {
            messageDiv.textContent = error.message;
            messageDiv.style.color = 'red';
            this.disabled = false;
        }
    }
});

window.onclick = function(event) {
    if (event.target === cancellationModal) {
        cancellationModal.style.display = 'none';
        if (cancelEmailCodeTimer) {
            clearInterval(cancelEmailCodeTimer);
            cancelEmailCodeTimer = null;
            cancelEmailCountdownValue = 0;
        }
    }
};

fetchCsrfToken().catch(function(e) {
    console.warn('CSRF pre-fetch failed:', e);
});

checkAuthAndLoad();

setInterval(function() {
    if (document.hidden) return;
    updateMailBadge();
}, 30000);

var style = document.createElement('style');
style.textContent = '.cancellation-badge{background:#e74c3c;color:white;font-size:10px;padding:2px 6px;border-radius:20px;margin-left:8px;}.cancel-tab-btn{transition:all 0.3s;}.cancel-tab-btn:hover{opacity:0.85;}';
document.head.appendChild(style);
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
var isVerified = false;
var isCheckingAuth = false;
var claimTargetId = null;

function showToast(message, type) {
    type = type || 'success';
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDescription(desc, isBatch, quantity, codes) {
    if (!desc) return '';
    var formatted = desc.replace(/\n/g, '<br>');
    if (isBatch && codes && codes.length > 1) {
        var codeList = codes.map(function(c) {
            return '<code style="background:#f0f0f0;padding:2px 8px;border-radius:4px;font-family:monospace;font-size:12px;display:inline-block;margin:2px 0;">' + escapeHtml(c) + '</code>';
        }).join('<br>');
        formatted += '<div style="margin-top:8px;padding:8px 12px;background:#f8f9fa;border-radius:8px;border:1px solid #e8e8e8;font-size:12px;color:#333;max-height:150px;overflow-y:auto;">';
        formatted += '<div style="font-weight:600;color:#667eea;margin-bottom:4px;">📋 共 ' + quantity + ' 张卡密：</div>';
        formatted += codeList;
        formatted += '</div>';
    } else if (isBatch && quantity > 1) {
        formatted += '<div style="margin-top:8px;padding:8px 12px;background:#f8f9fa;border-radius:8px;border:1px solid #e8e8e8;font-size:13px;color:#667eea;font-weight:600;">📋 共 ' + quantity + ' 张卡密</div>';
    }
    return formatted;
}

async function loadMailList() {
    try {
        var data = await apiRequest('/api/mail/list');
        var container = document.getElementById('mailList');
        var emptyState = document.getElementById('emptyState');
        var stats = document.getElementById('unclaimedCount');
        stats.textContent = data.total || 0;
        if (data.total === 0) {
            container.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }
        container.style.display = 'flex';
        emptyState.style.display = 'none';
        var html = '';
        var now = Date.now();
        data.attachments.forEach(function(item) {
            var expireTime = item.expires_at || 0;
            var timeLeft = expireTime - now;
            var expireText = '';
            var isExpired = false;
            if (expireTime > 0) {
                if (timeLeft <= 0) {
                    expireText = '已过期';
                    isExpired = true;
                } else if (timeLeft < 3600000) {
                    var minutes = Math.ceil(timeLeft / 60000);
                    expireText = minutes + '分钟后过期';
                } else if (timeLeft < 28800000) {
                    var hours = Math.ceil(timeLeft / 3600000);
                    expireText = hours + '小时后过期';
                } else {
                    expireText = '有效期内';
                }
            } else {
                expireText = '永久有效';
            }
            var typeLabel = '';
            var badgeClass = '';
            var isBatch = item.is_batch || false;
            var quantity = item.quantity || 1;
            var codes = item.codes || [];
            var source = item.source || '';
            if (item.type === 'points') {
                typeLabel = '积分';
                badgeClass = 'points';
            } else if (item.type === 'point_code') {
                typeLabel = '普通积分卡';
                badgeClass = 'code';
            } else if (item.type === 'premium_point_code') {
                typeLabel = '高级积分卡';
                badgeClass = 'code';
            } else if (item.type === 'reset_code') {
                typeLabel = '重置密码卡';
                badgeClass = 'code';
            } else if (item.type === 'boost_code') {
                typeLabel = '加成卡';
                badgeClass = 'code';
            } else if (item.type === 'special_point_code') {
                typeLabel = '特殊积分卡';
                badgeClass = 'code';
            } else if (item.type === 'makeup_code') {
                typeLabel = '补签卡';
                badgeClass = 'code';
            } else if (item.type === 'gamblers_code') {
                typeLabel = '赌神卡';
                badgeClass = 'code';
            } else if (item.type === 'box_code') {
                typeLabel = '盲盒卡';
                badgeClass = 'box';
            } else if (item.type === 'plcard_code') {
                typeLabel = 'PL随机卡';
                badgeClass = 'plcard';
            } else if (item.type === 'premium_boost_code') {
                typeLabel = '高级加成卡';
                badgeClass = 'premium_boost';
            } else if (item.type === 'cancellation_code') {
                typeLabel = '注销卡';
                badgeClass = 'cancellation';
            } else if (item.type === 'coupon') {
                typeLabel = '优惠券';
                badgeClass = 'coupon';
            } else if (item.type === 'combined_reward') {
                typeLabel = '组合奖励';
                badgeClass = 'points';
            }
            var descHtml = formatDescription(item.description, isBatch, quantity, codes);
            var actionHtml = '';
            if (isExpired) {
                actionHtml = '<span class="expired-badge">⏰ 已过期</span>';
            } else if (item.claimed) {
                actionHtml = '<span class="claimed-badge">✅ 已领取</span>';
            } else {
                var btnText = '📬 领取';
                if (isBatch && quantity > 1) {
                    btnText = '📬 一键领取全部 (' + quantity + '张)';
                }
                actionHtml = '<button class="claim-btn" data-id="' + item.id + '" onclick="openClaimModal(\'' + item.id + '\')">' + btnText + '</button>';
            }
            var sourceMap = {
                'daily_bonus': '每日奖励',
                'attendance_reward': '签到奖励',
                'admin_grant': '管理员发放',
                'admin_reissue': '管理员补发',
                'ai_reissue': 'AI客服补发',
                'cdk_exchange': 'CDK兑换',
                'mall_purchase': '商城购买',
                'identity_verification_reward': '身份认证奖励',
                'box_reward': '盲盒开箱',
                'pool_reward': '积分瓜分',
                'newbie_pool': '新人奖池',
                'daifu_purchase': '代付购买'
            };
            var sourceText = sourceMap[source] || source || '系统';
            var sourceBadge = '';
            if (source === 'ai_reissue') {
                sourceBadge = ' <span class="badge ai-reissue" style="background:#9b59b620;color:#9b59b6;">🤖 AI补发</span>';
            } else if (source === 'admin_grant' || source === 'admin_reissue') {
                sourceBadge = ' <span class="badge admin" style="background:#8e44ad20;color:#8e44ad;">👑 管理员</span>';
            }
            html += '<div class="mail-item">';
            html += '<div class="mail-info">';
            html += '<div class="mail-title">' + escapeHtml(item.title) + ' <span class="badge ' + badgeClass + '">' + escapeHtml(typeLabel) + '</span>' + sourceBadge;
            if (isBatch && quantity > 1) {
                html += ' <span style="font-size:11px;color:#667eea;background:#667eea20;padding:1px 10px;border-radius:12px;">x' + quantity + '</span>';
            }
            html += '</div>';
            html += '<div class="mail-desc">' + descHtml + '</div>';
            html += '<div class="mail-expire">⏰ ' + expireText + ' | 来源: ' + escapeHtml(sourceText) + '</div>';
            html += '</div>';
            html += '<div class="mail-actions">';
            html += actionHtml;
            html += '</div>';
            html += '</div>';
        });
        container.innerHTML = html;
    } catch (error) {
        console.error('Load mail list failed:', error);
        document.getElementById('mailList').innerHTML = '<div class="loading-spinner" style="margin:20px auto;"></div><p style="text-align:center;color:#e74c3c;">加载失败，请刷新重试</p>';
        if (error.message && error.message.includes('请先完成身份认证')) {
            document.getElementById('identityWarning').style.display = 'flex';
        }
    }
}

function openClaimModal(attachmentId) {
    claimTargetId = attachmentId;
    var modal = document.getElementById('claimModal');
    var message = document.getElementById('claimModalMessage');
    var result = document.getElementById('claimResult');
    var confirmBtn = document.getElementById('confirmClaimBtn');
    var mailItem = document.querySelector('.claim-btn[data-id="' + attachmentId + '"]');
    if (mailItem) {
        var parentItem = mailItem.closest('.mail-item');
        if (parentItem) {
            var titleEl = parentItem.querySelector('.mail-title');
            var descEl = parentItem.querySelector('.mail-desc');
            var title = titleEl ? titleEl.textContent.replace(/<[^>]*>/g, '').trim() : '邮件附件';
            var desc = descEl ? descEl.textContent.replace(/<[^>]*>/g, '').trim() : '';
            var isBatch = desc.includes('共') && desc.includes('张卡密');
            if (isBatch) {
                message.innerHTML = '确认领取此邮件附件中的所有卡密？<br><span style="font-size:13px;color:#888;">' + desc + '</span>';
                confirmBtn.textContent = '✅ 一键领取全部';
            } else {
                message.textContent = '确认领取此邮件附件？';
                confirmBtn.textContent = '✅ 确认领取';
            }
        } else {
            message.textContent = '确认领取此邮件附件？';
            confirmBtn.textContent = '✅ 确认领取';
        }
    } else {
        message.textContent = '确认领取此邮件附件？';
        confirmBtn.textContent = '✅ 确认领取';
    }
    result.textContent = '';
    result.className = '';
    confirmBtn.disabled = false;
    confirmBtn.innerHTML = '确认领取';
    modal.style.display = 'flex';
}

document.getElementById('confirmClaimBtn').addEventListener('click', async function() {
    if (!claimTargetId) {
        showToast('❌ 无效的附件ID', 'error');
        return;
    }
    var btn = this;
    var result = document.getElementById('claimResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 领取中...';
    result.textContent = '';
    try {
        var data = await apiRequest('/api/mail/claim/' + claimTargetId, {
            method: 'POST'
        });
        if (data.success) {
            result.textContent = '✅ ' + data.message;
            result.className = 'success';
            showToast('✅ ' + data.message, 'success');
            setTimeout(function() {
                document.getElementById('claimModal').style.display = 'none';
                loadMailList();
                updateUserInfo();
            }, 1500);
        } else {
            result.textContent = '❌ ' + data.error;
            result.className = 'error';
            btn.disabled = false;
            btn.innerHTML = '确认领取';
        }
    } catch (error) {
        result.textContent = '❌ ' + error.message;
        result.className = 'error';
        btn.disabled = false;
        btn.innerHTML = '确认领取';
    }
});

document.getElementById('cancelClaimBtn').addEventListener('click', function() {
    document.getElementById('claimModal').style.display = 'none';
    claimTargetId = null;
});

document.getElementById('claimModal').addEventListener('click', function(e) {
    if (e.target === this) {
        this.style.display = 'none';
        claimTargetId = null;
    }
});

async function updateUserInfo() {
    try {
        var data = await apiRequest('/api/check-auth');
        if (data.authenticated) {
            currentUser = data.username;
            isVerified = data.isVerified || false;
            document.getElementById('userInfo').textContent = '👤 ' + currentUser;
            document.getElementById('pointsDisplay').textContent = '⭐ ' + (data.totalPoints || 0).toFixed(2) + ' 积分';
            var warning = document.getElementById('identityWarning');
            if (!isVerified) {
                warning.style.display = 'flex';
                document.getElementById('mainContent').style.display = 'none';
            } else {
                warning.style.display = 'none';
                document.getElementById('mainContent').style.display = 'block';
            }
            return true;
        } else {
            window.location.href = '/login.html';
            return false;
        }
    } catch (error) {
        console.error('Update user info failed:', error);
        return false;
    }
}

document.getElementById('refreshBtn').addEventListener('click', function() {
    var btn = this;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 刷新中...';
    Promise.all([updateUserInfo(), loadMailList()]).then(function() {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sync-alt"></i> 刷新';
        showToast('🔄 已刷新', 'success');
    }).catch(function() {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sync-alt"></i> 刷新';
    });
});

async function init() {
    try {
        await fetchCsrfToken().catch(function(e) { console.warn('CSRF pre-fetch failed:', e); });
        var userOk = await updateUserInfo();
        if (userOk && isVerified) {
            await loadMailList();
        }
        var expireInfo = document.getElementById('expireInfo');
        var now = new Date();
        var expireTime = new Date(now.getTime() + 8 * 60 * 60 * 1000);
        expireInfo.textContent = expireTime.toLocaleTimeString('zh-CN');
    } catch (error) {
        console.error('Init error:', error);
    }
}

init();

setInterval(function() {
    if (document.hidden) return;
    loadMailList();
}, 30000);
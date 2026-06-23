// ============================================================
// apifox-post-extractor.js — Apifox 后置脚本：复杂提取 + 上下文传递
// 用途: 复制到 Apifox 接口的「后置脚本」标签页
// 功能: JSONPath条件提取 / Token自动传递 / 动态参数生成
// ============================================================

(function() {
    try {
        const resp = pm.response.json();
        const code = pm.response.code;

        // ============================================================
        // 模块 A: 条件提取 — "status=active 且 created_at 最新" 的用户ID
        // ============================================================
        if (resp && resp.data && Array.isArray(resp.data)) {
            const activeUsers = resp.data.filter(u => u.status === 'active');
            console.log('[Extractor] Active users: ' + activeUsers.length + '/' + resp.data.length);

            if (activeUsers.length > 0) {
                activeUsers.sort((a, b) =>
                    new Date(b.created_at || b.createdAt || 0).getTime() -
                    new Date(a.created_at || a.createdAt || 0).getTime()
                );

                const latest = activeUsers[0];
                console.log('[Extractor] ✅ Latest active: id=' + latest.id +
                    ' name=' + (latest.first_name || '') + ' ' + (latest.last_name || '') +
                    ' created=' + (latest.created_at || latest.createdAt));

                pm.environment.set('latest_active_user_id', latest.id);
                pm.environment.set('latest_active_user_email', latest.email || '');
            } else {
                console.warn('[Extractor] ⚠️ No active users, using fallback id=2');
                pm.environment.set('latest_active_user_id', 2);
            }
        }

        // ============================================================
        // 模块 B: Token 自动提取与全局 Header 设置
        // ============================================================
        if (resp && resp.token) {
            pm.environment.set('auth_token', resp.token);
            console.log('[Extractor] ✅ Token: ' + resp.token.substring(0, 12) + '...');
        }

        // ============================================================
        // 模块 C: 新创建资源 ID 收集（用于 Teardown 清理）
        // ============================================================
        if (code === 201 && resp && resp.id) {
            pm.environment.set('last_created_user_id', resp.id);
            // 追加到清理列表
            let ids = pm.environment.get('created_user_ids') || '';
            ids = ids ? ids + ',' + resp.id : String(resp.id);
            pm.environment.set('created_user_ids', ids);
            console.log('[Extractor] ✅ Created id=' + resp.id + ' | cleanup list: [' + ids + ']');
        }

        // ============================================================
        // 模块 D: 慢接口告警
        // ============================================================
        const rt = pm.response.responseTime;
        const endpoint = pm.request.url.toString().split('?')[0];
        if (rt > 3000) {
            console.warn('[Perf] ⚠️ SLOW: ' + endpoint + ' → ' + rt + 'ms (threshold: 3000ms)');
            pm.environment.set('slow_api_alert', endpoint + ':' + rt + 'ms');
        }

    } catch (err) {
        console.error('[Extractor] ❌ ' + err.message);
        console.error('[Extractor] Stack: ' + err.stack);
    }
})();

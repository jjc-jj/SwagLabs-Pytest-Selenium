// ============================================================
// apifox-pre-sign.js — Apifox 前置脚本：动态请求签名
// 用途: 复制到 Apifox 接口的「前置脚本」标签页
// 功能: 参数字典排序 → MD5/SHA256 签名 → 注入请求
// ============================================================

(function() {
    try {
        const APP_SECRET = pm.environment.get('api_secret') || 'swaglabs_api_secret_2026';
        const SIGN_ALGO = 'md5';  // 'md5' | 'sha256'

        // 1. 收集所有请求参数（排除签名自身）
        let params = {};
        const queryParams = pm.request.url.query;
        if (queryParams && queryParams.count() > 0) {
            queryParams.each(function(item) {
                if (item.key !== 'sign') params[item.key] = item.value;
            });
        }

        // 2. 追加防重放参数
        params['timestamp'] = Math.floor(Date.now() / 1000).toString();
        params['nonce'] = Array(16).fill(0)
            .map(() => 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'
                .charAt(Math.floor(Math.random() * 54)))
            .join('');

        // 3. 按 key 字典排序 → 拼接
        const sortedKeys = Object.keys(params).sort();
        let signStr = sortedKeys
            .filter(k => params[k] !== null && params[k] !== undefined && params[k] !== '')
            .map(k => k + '=' + params[k])
            .join('&');
        signStr += '&key=' + APP_SECRET;

        console.log('[Sign] Canonical string: ' + signStr);

        // 4. 生成签名
        const signature = SIGN_ALGO === 'sha256'
            ? CryptoJS.SHA256(signStr).toString(CryptoJS.enc.Hex).toUpperCase()
            : CryptoJS.MD5(signStr).toString(CryptoJS.enc.Hex).toUpperCase();

        console.log('[Sign] Signature: ' + signature);

        // 5. 注入到请求
        pm.request.url.query.add('sign', signature);
        pm.request.url.query.add('timestamp', params['timestamp']);
        pm.request.url.query.add('nonce', params['nonce']);

        // 也可写入 Header（可选）
        // pm.request.headers.add({ key: 'X-Sign', value: signature });

        // 6. 环境变量持久化
        pm.environment.set('current_sign', signature);
        pm.environment.set('current_timestamp', params['timestamp']);

        console.log('[Sign] ✅ Injected | ts=' + params['timestamp'] + ' | nonce=' + params['nonce']);

    } catch (err) {
        console.error('[Sign] ❌ ' + err.message);
    }
})();

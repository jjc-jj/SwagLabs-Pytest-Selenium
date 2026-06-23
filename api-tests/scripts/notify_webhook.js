#!/usr/bin/env node
// ============================================================
// api-tests/scripts/notify_webhook.js
// 功能: 将 API 测试结果推送到飞书/钉钉/企业微信
// 用法: node notify_webhook.js --platform=feishu --report=report.json
// ============================================================

const https = require('https');
const fs = require('fs');

// ========================================
// 解析命令行参数
// ========================================
const args = {};
process.argv.slice(2).forEach(arg => {
    const [k, v] = arg.replace('--', '').split('=');
    args[k] = v;
});

const PLATFORM = args.platform || 'feishu';
const REPORT_PATH = args.report || './api-tests/reports/apifox-report.json';
const WEBHOOK_URL = process.env.WEBHOOK_URL;

if (!WEBHOOK_URL) {
    console.error('❌ WEBHOOK_URL environment variable is required');
    process.exit(1);
}

// ========================================
// 读取测试报告
// ========================================
let report = {};
try {
    if (fs.existsSync(REPORT_PATH)) {
        report = JSON.parse(fs.readFileSync(REPORT_PATH, 'utf8'));
    }
} catch (e) {
    console.warn('⚠️  Report not found, sending basic notification');
}

const total = report.totalTests || 0;
const passed = report.passedTests || 0;
const failed = report.failedTests || 0;
const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : 'N/A';

// ========================================
// 构建消息 Payload
// ========================================
const isSuccess = failed === 0;
const reportUrl = process.env.REPORT_URL || '';

function buildFeishuPayload() {
    return JSON.stringify({
        msg_type: 'interactive',
        card: {
            header: {
                title: {
                    tag: 'plain_text',
                    content: `${isSuccess ? '✅' : '🚫'} API Test — ${isSuccess ? 'PASSED' : 'FAILED'}`
                },
                template: isSuccess ? 'green' : 'red'
            },
            elements: [
                {
                    tag: 'markdown',
                    content:
                        `**Project**: Swag Labs API Test\n` +
                        `**Total**: ${total} | **Passed**: ${passed} | **Failed**: ${failed}\n` +
                        `**Pass Rate**: ${passRate}%\n` +
                        `**Branch**: ${process.env.GITHUB_REF_NAME || 'N/A'}\n` +
                        `**Actor**: ${process.env.GITHUB_ACTOR || 'N/A'}\n` +
                        (failed > 0 ? `\n⚠️ **${failed} test(s) failed** — check report for details` : '')
                },
                ...(reportUrl ? [{
                    tag: 'action',
                    actions: [{
                        tag: 'button',
                        text: { tag: 'plain_text', content: '📊 View Report' },
                        url: reportUrl,
                        type: 'primary'
                    }]
                }] : [])
            ]
        }
    });
}

function buildDingTalkPayload() {
    return JSON.stringify({
        msgtype: 'markdown',
        markdown: {
            title: `API Test — ${isSuccess ? 'PASSED' : 'FAILED'}`,
            text:
                `### ${isSuccess ? '✅' : '🚫'} Swag Labs API Test Results\n\n` +
                `- **Total**: ${total}\n` +
                `- **Passed**: ${passed}\n` +
                `- **Failed**: ${failed}\n` +
                `- **Pass Rate**: ${passRate}%\n` +
                `- **Branch**: ${process.env.GITHUB_REF_NAME || 'N/A'}\n` +
                (reportUrl ? `\n[📊 View Report](${reportUrl})` : '')
        }
    });
}

function buildWecomPayload() {
    return JSON.stringify({
        msgtype: 'markdown',
        markdown: {
            content:
                `## ${isSuccess ? '✅' : '🚫'} Swag Labs API Test\n` +
                `> Total: **${total}** | Passed: **${passed}** | Failed: **${failed}**\n` +
                `> Pass Rate: **${passRate}%**\n` +
                `> Branch: ${process.env.GITHUB_REF_NAME || 'N/A'}\n` +
                (reportUrl ? `\n[View Report](${reportUrl})` : '')
        }
    });
}

const payload = {
    feishu: buildFeishuPayload,
    dingtalk: buildDingTalkPayload,
    wecom: buildWecomPayload,
}[PLATFORM]();

if (!payload) {
    console.error('❌ Unsupported platform:', PLATFORM);
    console.error('   Use: feishu | dingtalk | wecom');
    process.exit(1);
}

// ========================================
// 发送 HTTP POST
// ========================================
const url = new URL(WEBHOOK_URL);
const options = {
    hostname: url.hostname,
    path: url.pathname + url.search,
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
    }
};

const req = https.request(options, (res) => {
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
        try {
            const resp = JSON.parse(body);
            const ok = resp.code === 0 || resp.errcode === 0 || resp.StatusCode === 200;
            if (ok) {
                console.log(`✅ ${PLATFORM} notification sent successfully`);
            } else {
                console.error(`❌ ${PLATFORM} notification failed:`, body);
            }
        } catch (e) {
            console.log(`ℹ️  ${PLATFORM} response:`, body.substring(0, 200));
        }
    });
});

req.on('error', (err) => {
    console.error(`❌ ${PLATFORM} network error:`, err.message);
});

req.write(payload);
req.end();

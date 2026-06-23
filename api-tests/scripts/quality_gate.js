#!/usr/bin/env node
// ============================================================
// api-tests/scripts/quality_gate.js
// 功能: 解析 Apifox 测试报告，执行质量门禁判定
// 用法: node quality_gate.js [report.json路径]
// 返回: 0 = 通过 / 1 = 阻断
// ============================================================

const fs = require('fs');
const path = require('path');

// ========================================
// 配置区
// ========================================
const CONFIG = {
    // 核心接口 (P0) — 必须 100% 通过
    p0Endpoints: [
        { method: 'POST', path: '/api/login' },
        { method: 'POST', path: '/api/register' },
        { method: 'GET',  path: '/api/users' },
        { method: 'POST', path: '/' },                          // Swag Labs 登录
        { method: 'POST', path: '/checkout-step-two.html' },    // Swag Labs 下单确认
    ],
    // 整体通过率阈值
    overallPassRateThreshold: 95,    // 低于此值 → 阻断
    // P0 通过率阈值
    p0PassRateThreshold: 100,        // 低于此值 → 阻断
    // 性能劣化阈值
    perfDegradationThreshold: 50,    // 响应时间增长超过50% → 告警不阻断
    // 报告路径
    reportPath: process.argv[2] || './api-tests/reports/apifox-report.json',
};

// ========================================
// 主流程
// ========================================
function main() {
    console.log('='.repeat(60));
    console.log('  API Quality Gate — Swag Labs');
    console.log('='.repeat(60));

    // 1. 读取报告
    if (!fs.existsSync(CONFIG.reportPath)) {
        console.error('❌ Report file not found:', CONFIG.reportPath);
        process.exit(1);
    }

    const report = JSON.parse(fs.readFileSync(CONFIG.reportPath, 'utf8'));
    const results = analyzeReport(report);

    // 2. 输出统计
    console.log(`\n📊 Test Statistics:`);
    console.log(`   Total    : ${results.total}`);
    console.log(`   Passed   : ${results.passed}`);
    console.log(`   Failed   : ${results.failed}`);
    console.log(`   Pass Rate: ${results.passRate}%`);
    console.log(`   P0 Total : ${results.p0Total}`);
    console.log(`   P0 Failed: ${results.p0Failed}`);
    console.log(`   P0 Rate  : ${results.p0PassRate}%`);
    console.log(`   Avg RT   : ${results.avgResponseTime}ms`);

    // 3. 执行门禁规则
    const gateResult = evaluateGate(results);

    // 4. 输出判定
    console.log(`\n${'='.repeat(60)}`);
    if (gateResult.passed) {
        console.log('✅ Quality Gate: PASSED — Continue deployment');
        console.log('='.repeat(60));
        process.exit(0);
    } else {
        console.error('🚫 Quality Gate: FAILED — Pipeline blocked');
        console.error(`\nViolations (${gateResult.violations.length}):`);
        gateResult.violations.forEach((v, i) => {
            console.error(`  ${i + 1}. ${v}`);
        });
        console.error('\n' + '='.repeat(60));
        process.exit(1);
    }
}

// ========================================
// 分析报告
// ========================================
function analyzeReport(report) {
    const results = {
        total: 0,
        passed: 0,
        failed: 0,
        passRate: 0,
        p0Total: 0,
        p0Failed: 0,
        p0PassRate: 100,
        avgResponseTime: 0,
        testDetails: [],
    };

    const tests = report.testResults || report.tests || [];

    tests.forEach(test => {
        results.total++;
        if (test.passed || test.status === 'passed') {
            results.passed++;
        } else {
            results.failed++;
            results.testDetails.push({
                name: test.name || test.title || 'Unknown',
                endpoint: `${test.method || 'GET'} ${test.endpoint || test.url || ''}`,
                error: test.error || test.message || 'Unknown error',
            });
        }

        // P0 检测
        const endpoint = `${test.method || 'GET'} ${test.endpoint || test.url || ''}`;
        const isP0 = CONFIG.p0Endpoints.some(p0 => {
            return endpoint.includes(p0.method) && endpoint.includes(p0.path);
        });

        if (isP0) {
            results.p0Total++;
            if (!test.passed && test.status !== 'passed') {
                results.p0Failed++;
            }
        }
    });

    // 计算通过率
    if (results.total > 0) {
        results.passRate = parseFloat(((results.passed / results.total) * 100).toFixed(2));
    }
    if (results.p0Total > 0) {
        results.p0PassRate = parseFloat((((results.p0Total - results.p0Failed) / results.p0Total) * 100).toFixed(2));
    }

    // 平均响应时间
    const responseTimes = tests
        .map(t => t.responseTime || t.duration || 0)
        .filter(rt => rt > 0);
    if (responseTimes.length > 0) {
        results.avgResponseTime = Math.round(
            responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
        );
    }

    return results;
}

// ========================================
// 质量门禁判定
// ========================================
function evaluateGate(results) {
    const gateResult = {
        passed: true,
        violations: [],
    };

    // 规则 1: P0 核心接口必须 100% 通过 (硬阻断)
    if (results.p0Failed > 0) {
        gateResult.passed = false;
        gateResult.violations.push(
            `🔴 HARD BLOCK: P0接口 ${results.p0Failed}/${results.p0Total} 失败 ` +
            `(通过率 ${results.p0PassRate}% < ${CONFIG.p0PassRateThreshold}%)`
        );
        // 列出具体的 P0 失败用例
        results.testDetails
            .filter(d => CONFIG.p0Endpoints.some(p0 => d.endpoint.includes(p0.path)))
            .forEach(d => {
                gateResult.violations.push(`   └─ ${d.endpoint}: ${d.name} — ${d.error}`);
            });
    }

    // 规则 2: 整体通过率 >= 阈值 (软阻断)
    if (results.passRate < CONFIG.overallPassRateThreshold) {
        gateResult.passed = false;
        gateResult.violations.push(
            `🟡 SOFT BLOCK: 整体通过率 ${results.passRate}% < ${CONFIG.overallPassRateThreshold}%`
        );
    }

    // 规则 3: 无服务端 500 错误
    const serverErrors = results.testDetails.filter(d =>
        d.error && (d.error.includes('500') || d.error.includes('Internal Server Error'))
    );
    if (serverErrors.length > 0) {
        gateResult.passed = false;
        gateResult.violations.push(
            `🔴 HARD BLOCK: 检测到 ${serverErrors.length} 个服务端500错误`
        );
    }

    // 规则 4 (告警不阻断): 全 Pass 但无 P0 标记的用例 (提示补充标记)
    if (results.p0Total === 0 && results.total > 0) {
        console.warn('⚠️  WARNING: No P0 interfaces detected — consider marking core interfaces with @P0');
    }

    return gateResult;
}

// ========================================
// 执行
// ========================================
main();

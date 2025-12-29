/**
 * SalesMind 管理画面 - 共通JavaScript関数
 * 
 * このファイルは以下のファイルで共通して使用される関数を提供します:
 * - provider_key_test.js
 * - model_configuration.js
 */

// 名前空間を定義
var SalesMindAdmin = SalesMindAdmin || {};

/**
 * CSRFトークンをCookieから取得
 * @param {string} name - Cookie名
 * @returns {string|null} Cookie値
 */
SalesMindAdmin.getCookie = function(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};

/**
 * CSRFトークンを取得（便利関数）
 * @returns {string|null} CSRFトークン
 */
SalesMindAdmin.getCSRFToken = function() {
    return SalesMindAdmin.getCookie('csrftoken');
};

/**
 * 成功メッセージのHTMLを生成
 * @param {string} message - メッセージ
 * @returns {string} HTML文字列
 */
SalesMindAdmin.successHtml = function(message) {
    return `
        <div style="padding: 10px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb; border-radius: 4px;">
            <strong>✓ 成功</strong><br>
            ${SalesMindAdmin.escapeHtml(message)}
        </div>
    `;
};

/**
 * エラーメッセージのHTMLを生成
 * @param {string} message - メッセージ
 * @returns {string} HTML文字列
 */
SalesMindAdmin.errorHtml = function(message) {
    return `
        <div style="padding: 10px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 4px;">
            <strong>✗ エラー</strong><br>
            ${SalesMindAdmin.escapeHtml(message)}
        </div>
    `;
};

/**
 * ローディング表示のHTMLを生成
 * @param {string} message - メッセージ（デフォルト: "処理中..."）
 * @returns {string} HTML文字列
 */
SalesMindAdmin.loadingHtml = function(message) {
    return `<div style="padding: 10px; background: #f0f0f0; border-radius: 4px;">${message || '処理中...'}</div>`;
};

/**
 * HTMLエスケープ
 * @param {string} text - エスケープする文字列
 * @returns {string} エスケープされた文字列
 */
SalesMindAdmin.escapeHtml = function(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

/**
 * AJAXリクエストを送信（POST）
 * @param {string} url - リクエストURL
 * @param {Object} data - 送信データ
 * @returns {Promise} レスポンスのPromise
 */
SalesMindAdmin.postJson = async function(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': SalesMindAdmin.getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data),
        credentials: 'same-origin'
    });
    return response.json();
};

// グローバル関数として getCookie も公開（後方互換性のため）
if (typeof getCookie === 'undefined') {
    var getCookie = SalesMindAdmin.getCookie;
}

console.log('SalesMindAdmin common.js loaded');


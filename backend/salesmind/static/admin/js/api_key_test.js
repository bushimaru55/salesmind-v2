/**
 * OpenAI APIキー疎通テスト用JavaScript
 */

// 一覧画面での疎通テスト
function testAPIKey(keyId) {
    const linkElement = document.getElementById(`test-link-${keyId}`);
    if (!linkElement) return;
    
    // テスト中表示
    linkElement.innerHTML = '⏳ テスト中...';
    linkElement.style.color = '#999';
    
    // APIリクエスト
    fetch(`/admin/spin/openaiapikey/test-api-key/${keyId}/`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            linkElement.innerHTML = `✓ 成功`;
            linkElement.style.color = 'green';
            linkElement.title = data.message;
            
            // 3秒後に元に戻す
            setTimeout(() => {
                linkElement.innerHTML = '🔌 疎通テスト';
                linkElement.style.color = '#417690';
                linkElement.title = '';
            }, 3000);
        } else {
            linkElement.innerHTML = `✗ 失敗`;
            linkElement.style.color = 'red';
            linkElement.title = data.message;
            
            // 5秒後に元に戻す
            setTimeout(() => {
                linkElement.innerHTML = '🔌 疎通テスト';
                linkElement.style.color = '#417690';
                linkElement.title = '';
            }, 5000);
        }
    })
    .catch(error => {
        console.error('API test error:', error);
        linkElement.innerHTML = '✗ エラー';
        linkElement.style.color = 'red';
        linkElement.title = 'テストに失敗しました';
        
        // 5秒後に元に戻す
        setTimeout(() => {
            linkElement.innerHTML = '🔌 疎通テスト';
            linkElement.style.color = '#417690';
            linkElement.title = '';
        }, 5000);
    });
}

// 詳細画面での疎通テスト
function testAPIKeyDetail(keyId) {
    const statusElement = document.getElementById(`test-status-${keyId}`);
    if (!statusElement) return;
    
    // テスト中表示
    statusElement.innerHTML = '<div style="padding: 10px; background: #f0f0f0; border-radius: 4px;">⏳ 疎通テスト実行中...</div>';
    
    // APIリクエスト
    fetch(`/admin/spin/openaiapikey/test-api-key/${keyId}/`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        let statusColor = data.success ? '#d4edda' : '#f8d7da';
        let textColor = data.success ? '#155724' : '#721c24';
        let borderColor = data.success ? '#c3e6cb' : '#f5c6cb';
        let icon = data.success ? '✓' : '✗';
        
        statusElement.innerHTML = `
            <div style="padding: 15px; background: ${statusColor}; color: ${textColor}; 
                        border: 1px solid ${borderColor}; border-radius: 4px; margin-top: 10px;">
                <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">
                    ${icon} ${data.status}
                </div>
                <div style="font-size: 14px;">
                    <strong>APIキー名:</strong> ${data.key_name}<br>
                    <strong>結果:</strong> ${data.message}
                </div>
            </div>
        `;
    })
    .catch(error => {
        console.error('API test error:', error);
        statusElement.innerHTML = `
            <div style="padding: 15px; background: #f8d7da; color: #721c24; 
                        border: 1px solid #f5c6cb; border-radius: 4px; margin-top: 10px;">
                <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">
                    ✗ エラー
                </div>
                <div style="font-size: 14px;">
                    疎通テストに失敗しました。ネットワーク接続を確認してください。
                </div>
            </div>
        `;
    });
}

// チャット履歴を保存するオブジェクト
const chatHistories = {};

// テストチャットメッセージを送信
function sendTestMessage(keyId) {
    const inputElement = document.getElementById(`chat-input-${keyId}`);
    const historyElement = document.getElementById(`chat-history-${keyId}`);
    
    if (!inputElement || !historyElement) return;
    
    const userMessage = inputElement.value.trim();
    if (!userMessage) {
        alert('メッセージを入力してください');
        return;
    }
    
    // チャット履歴を初期化（存在しない場合）
    if (!chatHistories[keyId]) {
        chatHistories[keyId] = [];
    }
    
    // ユーザーメッセージを表示
    appendChatMessage(keyId, 'user', userMessage);
    
    // 入力欄をクリア
    inputElement.value = '';
    
    // ローディング表示
    const loadingId = `loading-${Date.now()}`;
    historyElement.innerHTML += `
        <div id="${loadingId}" style="padding: 10px; margin: 5px 0; background: #f0f0f0; border-radius: 8px; text-align: left;">
            <strong>AI:</strong> <span style="color: #666;">⏳ 応答を生成中...</span>
        </div>
    `;
    historyElement.scrollTop = historyElement.scrollHeight;
    
    // CSRFトークンを取得
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // APIリクエスト
    fetch(`/admin/spin/openaiapikey/test-chat/${keyId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            message: userMessage,
            history: chatHistories[keyId]
        })
    })
    .then(response => response.json())
    .then(data => {
        // ローディング表示を削除
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }
        
        if (data.success) {
            // AIの応答を表示
            appendChatMessage(keyId, 'assistant', data.message);
            
            // 使用トークン情報を表示
            if (data.usage) {
                const usageInfo = `<div style="font-size: 11px; color: #999; margin-top: 5px;">
                    モデル: ${data.model} | トークン: ${data.usage.total_tokens} 
                    (入力: ${data.usage.prompt_tokens}, 出力: ${data.usage.completion_tokens})
                </div>`;
                historyElement.lastElementChild.innerHTML += usageInfo;
            }
            
            // 会話履歴に追加
            chatHistories[keyId].push({ role: 'user', content: userMessage });
            chatHistories[keyId].push({ role: 'assistant', content: data.message });
        } else {
            // エラーメッセージを表示
            historyElement.innerHTML += `
                <div style="padding: 10px; margin: 5px 0; background: #f8d7da; color: #721c24; border-radius: 8px; border: 1px solid #f5c6cb;">
                    <strong>エラー:</strong> ${data.message}
                </div>
            `;
        }
        
        historyElement.scrollTop = historyElement.scrollHeight;
    })
    .catch(error => {
        console.error('Chat error:', error);
        
        // ローディング表示を削除
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }
        
        historyElement.innerHTML += `
            <div style="padding: 10px; margin: 5px 0; background: #f8d7da; color: #721c24; border-radius: 8px; border: 1px solid #f5c6cb;">
                <strong>エラー:</strong> チャットリクエストに失敗しました。ネットワーク接続を確認してください。
            </div>
        `;
        historyElement.scrollTop = historyElement.scrollHeight;
    });
}

// チャットメッセージを表示に追加
function appendChatMessage(keyId, role, content) {
    const historyElement = document.getElementById(`chat-history-${keyId}`);
    if (!historyElement) return;
    
    const isUser = role === 'user';
    const bgColor = isUser ? '#e3f2fd' : '#f5f5f5';
    const align = isUser ? 'right' : 'left';
    const label = isUser ? 'あなた' : 'AI';
    
    historyElement.innerHTML += `
        <div style="padding: 10px; margin: 5px 0; background: ${bgColor}; border-radius: 8px; text-align: ${align};">
            <strong>${label}:</strong> ${escapeHtml(content)}
        </div>
    `;
    historyElement.scrollTop = historyElement.scrollHeight;
}

// チャット履歴をクリア
function clearChatHistory(keyId) {
    const historyElement = document.getElementById(`chat-history-${keyId}`);
    if (!historyElement) return;
    
    if (confirm('チャット履歴をクリアしますか？')) {
        historyElement.innerHTML = '';
        chatHistories[keyId] = [];
    }
}

// HTMLエスケープ
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Enterキーで送信（Shift+Enterで改行）
document.addEventListener('keydown', function(e) {
    if (e.target.id && e.target.id.startsWith('chat-input-')) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const keyId = e.target.id.replace('chat-input-', '');
            sendTestMessage(keyId);
        }
    }
});

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('OpenAI API Key Test JavaScript loaded');
});


// AIProviderKey接続テスト用JavaScript

function getCookie(name) {
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
}

async function testConnection(keyId) {
    // 常にフォームから値を取得（新規作成時も既存レコード編集時も）
    let apiKeyField = document.getElementById('id_api_key') || 
                     document.querySelector('input[name="api_key"]') ||
                     document.querySelector('input[type="text"]');
    let providerField = document.getElementById('id_provider') ||
                       document.querySelector('select[name="provider"]') ||
                       document.querySelector('select');
    
    let apiKey = apiKeyField?.value?.trim() || '';
    let provider = providerField?.value?.trim() || '';
    
    // デバッグ用ログ
    console.log('=== Connection Test Debug ===');
    console.log('keyId:', keyId);
    console.log('API Key field:', apiKeyField ? (apiKeyField.id || apiKeyField.name || 'found') : 'not found');
    console.log('API Key value:', apiKey ? apiKey.substring(0, 20) + '...' : 'empty');
    console.log('Provider field:', providerField ? (providerField.id || providerField.name || 'found') : 'not found');
    console.log('Provider value:', provider || 'empty');
    console.log('============================');
    
    // 出力エリアを設定
    let outputDiv;
    if (keyId) {
        outputDiv = document.getElementById(`test-output-${keyId}`);
    } else {
        outputDiv = document.getElementById('test-output-new');
    }
    
    if (outputDiv) {
        outputDiv.innerHTML = '<div style="padding: 10px; background: #f0f0f0; border-radius: 4px;">テスト中...</div>';
    }
    
    // フォームから値を取得できない場合はエラー
    if (!apiKey || !provider) {
        let errorDetails = [];
        if (!apiKeyField) {
            errorDetails.push('APIキーフィールドが見つかりません');
        } else if (!apiKey) {
            errorDetails.push('APIキーが入力されていません');
        }
        
        if (!providerField) {
            errorDetails.push('プロバイダーフィールドが見つかりません');
        } else if (!provider) {
            errorDetails.push('プロバイダーが選択されていません');
        }
        
        const errorMsg = 'APIキーとプロバイダーが必要です。\n\n' + errorDetails.join('\n');
        if (outputDiv) {
            outputDiv.innerHTML = `<div style="padding: 10px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 4px;"><strong>✗ エラー</strong><br>${errorMsg}</div>`;
        } else {
            alert(errorMsg);
        }
        return;
    }
    
    try {
        // 常にJSONで送信（key_idがあっても、フォームから取得した値を送信）
        const url = '/admin/spin/aiproviderkey/test-connection/';
        const body = JSON.stringify({
            api_key: apiKey,
            provider: provider,
            key_id: keyId || null  // key_idも送信（存在する場合）
        });
        
        console.log('Sending request:', { url, api_key: apiKey.substring(0, 20) + '...', provider });
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: body,
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        const successHtml = `
            <div style="padding: 10px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb; border-radius: 4px;">
                <strong>✓ 接続成功</strong><br>
                ${data.message}
            </div>
        `;
        
        const errorHtml = `
            <div style="padding: 10px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 4px;">
                <strong>✗ 接続失敗</strong><br>
                ${data.message}
            </div>
        `;
        
        if (outputDiv) {
            outputDiv.innerHTML = data.success ? successHtml : errorHtml;
        } else {
            if (data.success) {
                alert('✓ 接続成功: ' + data.message);
            } else {
                alert('✗ 接続失敗: ' + data.message);
            }
        }
    } catch (error) {
        console.error('Connection test error:', error);
        const errorHtml = `
            <div style="padding: 10px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 4px;">
                <strong>✗ エラー</strong><br>
                テスト中にエラーが発生しました: ${error.message}
            </div>
        `;
        
        if (outputDiv) {
            outputDiv.innerHTML = errorHtml;
        } else {
            alert('✗ エラー: ' + error.message);
        }
    }
}

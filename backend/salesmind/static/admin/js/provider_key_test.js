/**
 * AIProviderKey 接続テスト用JavaScript
 * 
 * 依存: common.js
 */

async function testConnection(keyId) {
    // フォームから値を取得
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
    console.log('API Key value:', apiKey ? apiKey.substring(0, 20) + '...' : 'empty');
    console.log('Provider value:', provider || 'empty');
    console.log('============================');
    
    // 出力エリアを設定
    let outputDiv = keyId 
        ? document.getElementById(`test-output-${keyId}`)
        : document.getElementById('test-output-new');
    
    if (outputDiv) {
        outputDiv.innerHTML = SalesMindAdmin.loadingHtml('テスト中...');
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
            outputDiv.innerHTML = SalesMindAdmin.errorHtml(errorMsg);
        } else {
            alert(errorMsg);
        }
        return;
    }
    
    try {
        const url = '/admin/spin/aiproviderkey/test-connection/';
        const data = await SalesMindAdmin.postJson(url, {
            api_key: apiKey,
            provider: provider,
            key_id: keyId || null
        });
        
        const html = data.success 
            ? SalesMindAdmin.successHtml('接続成功: ' + data.message)
            : SalesMindAdmin.errorHtml('接続失敗: ' + data.message);
        
        if (outputDiv) {
            outputDiv.innerHTML = html;
        } else {
            alert(data.success ? '✓ 接続成功: ' + data.message : '✗ 接続失敗: ' + data.message);
        }
    } catch (error) {
        console.error('Connection test error:', error);
        if (outputDiv) {
            outputDiv.innerHTML = SalesMindAdmin.errorHtml('テスト中にエラーが発生しました: ' + error.message);
        } else {
            alert('✗ エラー: ' + error.message);
        }
    }
}

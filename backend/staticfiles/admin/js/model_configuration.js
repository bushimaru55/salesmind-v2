// 用途別モデル設定画面用JavaScript
// プロバイダーキーが変更されたときに、対応するモデルの選択肢を動的に更新

(function($) {
    'use strict';
    
    // CSRFトークンを取得する関数
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
    
    // モデルフィールドの表示/非表示を切り替える関数
    function toggleModelFieldVisibility(modelSelectId, show) {
        const modelSelect = document.getElementById(modelSelectId);
        if (!modelSelect) {
            return;
        }
        
        // モデルセレクトボックスの親要素（form-row）を探す
        let fieldContainer = modelSelect.closest('.form-row');
        if (!fieldContainer) {
            // form-rowが見つからない場合、親のdivを探す
            fieldContainer = modelSelect.parentElement;
            while (fieldContainer && !fieldContainer.classList.contains('form-row')) {
                fieldContainer = fieldContainer.parentElement;
            }
        }
        
        if (fieldContainer) {
            if (show) {
                fieldContainer.style.display = '';
                console.log(`Showing model field: ${modelSelectId}`);
            } else {
                fieldContainer.style.display = 'none';
                console.log(`Hiding model field: ${modelSelectId}`);
            }
        } else {
            console.warn(`Could not find container for model field: ${modelSelectId}`);
        }
    }
    
    // モデル選択肢を更新する関数
    function updateModelOptions(providerKeySelectId, modelSelectId) {
        const providerKeySelect = document.getElementById(providerKeySelectId);
        const modelSelect = document.getElementById(modelSelectId);
        
        if (!providerKeySelect || !modelSelect) {
            console.log(`Fields not found: ${providerKeySelectId} or ${modelSelectId}`);
            return;
        }
        
        const selectedProviderKeyId = providerKeySelect.value;
        
        console.log(`Updating model options for provider key: ${selectedProviderKeyId}`);
        
        if (!selectedProviderKeyId) {
            // プロバイダーキーが選択されていない場合、モデルフィールドを非表示にする
            toggleModelFieldVisibility(modelSelectId, false);
            modelSelect.innerHTML = '<option value="">---------</option>';
            return;
        }
        
        // プロバイダーキーが選択されている場合、モデルフィールドを表示する
        toggleModelFieldVisibility(modelSelectId, true);
        
        // ローディング表示
        modelSelect.disabled = true;
        const originalHtml = modelSelect.innerHTML;
        modelSelect.innerHTML = '<option value="">読み込み中...</option>';
        
        // AJAXで選択されたプロバイダーキーのモデル一覧を取得
        const url = '/admin/spin/modelconfiguration/get-models-for-provider/';
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                provider_key_id: selectedProviderKeyId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            modelSelect.disabled = false;
            
            if (data.success && data.models && data.models.length > 0) {
                // 現在の選択値を保存
                const currentValue = modelSelect.getAttribute('data-current-value') || modelSelect.value;
                
                // 選択肢をクリア
                modelSelect.innerHTML = '<option value="">---------</option>';
                
                // 新しい選択肢を追加
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.id;
                    option.textContent = model.display_name;
                    if (String(model.id) === String(currentValue)) {
                        option.selected = true;
                    }
                    modelSelect.appendChild(option);
                });
                
                console.log(`Updated ${data.models.length} models for provider: ${data.provider}`);
            } else {
                // モデルが見つからない場合
                modelSelect.innerHTML = '<option value="">利用可能なモデルがありません</option>';
                console.warn('No models found for provider key:', selectedProviderKeyId);
            }
        })
        .catch(error => {
            modelSelect.disabled = false;
            modelSelect.innerHTML = '<option value="">エラー: モデルの取得に失敗しました</option>';
            console.error('Error updating model options:', error);
        });
    }
    
    // ページ読み込み時にイベントリスナーを設定
    function initializeEventListeners() {
        console.log('Initializing model configuration event listeners');
        
        // Primary provider keyの変更を監視
        const primaryProviderKeySelect = document.getElementById('id_primary_provider_key');
        if (primaryProviderKeySelect) {
            // 既存のイベントリスナーを削除（重複防止のため、一度削除して再追加）
            const newPrimarySelect = primaryProviderKeySelect.cloneNode(true);
            primaryProviderKeySelect.parentNode.replaceChild(newPrimarySelect, primaryProviderKeySelect);
            
            // イベントリスナーを追加
            newPrimarySelect.addEventListener('change', function(e) {
                console.log('Primary provider key changed:', this.value);
                updateModelOptions('id_primary_provider_key', 'id_primary_model');
            });
            
            // ページ読み込み時にも更新（既に値が選択されている場合）
            if (newPrimarySelect.value) {
                console.log('Initial primary provider key value:', newPrimarySelect.value);
                updateModelOptions('id_primary_provider_key', 'id_primary_model');
            } else {
                // 値が選択されていない場合、モデルフィールドを非表示にする
                toggleModelFieldVisibility('id_primary_model', false);
                const primaryModelSelect = document.getElementById('id_primary_model');
                if (primaryModelSelect) {
                    primaryModelSelect.innerHTML = '<option value="">---------</option>';
                }
            }
        } else {
            console.warn('Primary provider key select not found');
        }
        
        // Fallback provider keyの変更を監視
        const fallbackProviderKeySelect = document.getElementById('id_fallback_provider_key');
        if (fallbackProviderKeySelect) {
            // 既存のイベントリスナーを削除（重複防止のため、一度削除して再追加）
            const newFallbackSelect = fallbackProviderKeySelect.cloneNode(true);
            fallbackProviderKeySelect.parentNode.replaceChild(newFallbackSelect, fallbackProviderKeySelect);
            
            // イベントリスナーを追加
            newFallbackSelect.addEventListener('change', function(e) {
                console.log('Fallback provider key changed:', this.value);
                updateModelOptions('id_fallback_provider_key', 'id_fallback_model');
            });
            
            // ページ読み込み時にも更新（既に値が選択されている場合）
            if (newFallbackSelect.value) {
                console.log('Initial fallback provider key value:', newFallbackSelect.value);
                updateModelOptions('id_fallback_provider_key', 'id_fallback_model');
            } else {
                // 値が選択されていない場合、モデルフィールドを非表示にする
                toggleModelFieldVisibility('id_fallback_model', false);
                const fallbackModelSelect = document.getElementById('id_fallback_model');
                if (fallbackModelSelect) {
                    fallbackModelSelect.innerHTML = '<option value="">---------</option>';
                }
            }
        } else {
            console.warn('Fallback provider key select not found');
        }
    }
    
    // 複数の方法で初期化を試みる（Django adminの読み込みタイミングに対応）
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeEventListeners);
    } else {
        // DOMContentLoadedが既に発火している場合
        initializeEventListeners();
    }
    
    // DjangoのjQueryも使用（念のため）
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).ready(function() {
            console.log('Django jQuery ready');
            // 少し遅延させて実行（フォームが完全に読み込まれるのを待つ）
            setTimeout(initializeEventListeners, 100);
        });
    }
    
})(django.jQuery);


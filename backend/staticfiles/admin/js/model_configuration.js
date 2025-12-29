/**
 * 用途別モデル設定画面用JavaScript
 * プロバイダーキーが変更されたときに、対応するモデルの選択肢を動的に更新
 * 
 * 依存: common.js
 */

(function($) {
    'use strict';
    
    /**
     * モデルフィールドの表示/非表示を切り替える
     * @param {string} modelSelectId - モデル選択フィールドのID
     * @param {boolean} show - 表示するかどうか
     */
    function toggleModelFieldVisibility(modelSelectId, show) {
        const modelSelect = document.getElementById(modelSelectId);
        if (!modelSelect) {
            return;
        }
        
        // モデルセレクトボックスの親要素（form-row）を探す
        let fieldContainer = modelSelect.closest('.form-row');
        if (!fieldContainer) {
            fieldContainer = modelSelect.parentElement;
            while (fieldContainer && !fieldContainer.classList.contains('form-row')) {
                fieldContainer = fieldContainer.parentElement;
            }
        }
        
        if (fieldContainer) {
            fieldContainer.style.display = show ? '' : 'none';
            console.log(`${show ? 'Showing' : 'Hiding'} model field: ${modelSelectId}`);
        } else {
            console.warn(`Could not find container for model field: ${modelSelectId}`);
        }
    }
    
    /**
     * モデル選択肢を更新する
     * @param {string} providerKeySelectId - プロバイダーキー選択フィールドのID
     * @param {string} modelSelectId - モデル選択フィールドのID
     */
    async function updateModelOptions(providerKeySelectId, modelSelectId) {
        const providerKeySelect = document.getElementById(providerKeySelectId);
        const modelSelect = document.getElementById(modelSelectId);
        
        if (!providerKeySelect || !modelSelect) {
            console.log(`Fields not found: ${providerKeySelectId} or ${modelSelectId}`);
            return;
        }
        
        const selectedProviderKeyId = providerKeySelect.value;
        
        console.log(`Updating model options for provider key: ${selectedProviderKeyId}`);
        
        if (!selectedProviderKeyId) {
            toggleModelFieldVisibility(modelSelectId, false);
            modelSelect.innerHTML = '<option value="">---------</option>';
            return;
        }
        
        // プロバイダーキーが選択されている場合、モデルフィールドを表示
        toggleModelFieldVisibility(modelSelectId, true);
        
        // ローディング表示
        modelSelect.disabled = true;
        const currentValue = modelSelect.getAttribute('data-current-value') || modelSelect.value;
        modelSelect.innerHTML = '<option value="">読み込み中...</option>';
        
        try {
            const url = '/admin/spin/modelconfiguration/get-models-for-provider/';
            const data = await SalesMindAdmin.postJson(url, {
                provider_key_id: selectedProviderKeyId
            });
            
            modelSelect.disabled = false;
            
            if (data.success && data.models && data.models.length > 0) {
                modelSelect.innerHTML = '<option value="">---------</option>';
                
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
                modelSelect.innerHTML = '<option value="">利用可能なモデルがありません</option>';
                console.warn('No models found for provider key:', selectedProviderKeyId);
            }
        } catch (error) {
            modelSelect.disabled = false;
            modelSelect.innerHTML = '<option value="">エラー: モデルの取得に失敗しました</option>';
            console.error('Error updating model options:', error);
        }
    }
    
    /**
     * イベントリスナーを初期化
     */
    function initializeEventListeners() {
        console.log('Initializing model configuration event listeners');
        
        // Primary provider keyの変更を監視
        setupProviderKeyListener('id_primary_provider_key', 'id_primary_model');
        
        // Fallback provider keyの変更を監視
        setupProviderKeyListener('id_fallback_provider_key', 'id_fallback_model');
    }
    
    /**
     * プロバイダーキーのイベントリスナーを設定
     * @param {string} providerKeySelectId - プロバイダーキー選択フィールドのID
     * @param {string} modelSelectId - モデル選択フィールドのID
     */
    function setupProviderKeyListener(providerKeySelectId, modelSelectId) {
        const providerKeySelect = document.getElementById(providerKeySelectId);
        if (!providerKeySelect) {
            console.warn(`${providerKeySelectId} not found`);
            return;
        }
        
        // 既存のイベントリスナーを削除（重複防止）
        const newSelect = providerKeySelect.cloneNode(true);
        providerKeySelect.parentNode.replaceChild(newSelect, providerKeySelect);
        
        // イベントリスナーを追加
        newSelect.addEventListener('change', function() {
            console.log(`${providerKeySelectId} changed:`, this.value);
            updateModelOptions(providerKeySelectId, modelSelectId);
        });
        
        // ページ読み込み時にも更新
        if (newSelect.value) {
            console.log(`Initial ${providerKeySelectId} value:`, newSelect.value);
            updateModelOptions(providerKeySelectId, modelSelectId);
        } else {
            toggleModelFieldVisibility(modelSelectId, false);
            const modelSelect = document.getElementById(modelSelectId);
            if (modelSelect) {
                modelSelect.innerHTML = '<option value="">---------</option>';
            }
        }
    }
    
    // 複数の方法で初期化を試みる（Django adminの読み込みタイミングに対応）
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeEventListeners);
    } else {
        initializeEventListeners();
    }
    
    // DjangoのjQueryも使用（念のため）
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).ready(function() {
            console.log('Django jQuery ready');
            setTimeout(initializeEventListeners, 100);
        });
    }
    
})(django.jQuery);

/**
 * リアルタイム会話機能
 * OpenAI Realtime APIを使用したリアルタイム音声会話
 */

/**
 * チャットモードを切り替え
 */
function switchChatMode(mode) {
    if (window.logger) {
        window.logger.info('チャットモード切り替え', { mode });
    }
    
    conversationMode = mode;
    
    const textInputArea = document.getElementById('textInputArea');
    const realtimeInputArea = document.getElementById('realtimeInputArea');
    
    if (mode === 'text') {
        // テキストモード
        textInputArea.style.display = 'flex';
        realtimeInputArea.style.display = 'none';
        
        // リアルタイム会話を停止
        if (realtimeClient && isRealtimeTalking) {
            stopRealtimeConversation();
        }
    } else if (mode === 'realtime') {
        // リアルタイムモード
        textInputArea.style.display = 'none';
        realtimeInputArea.style.display = 'flex';
    }
}

/**
 * リアルタイム会話のトグル
 */
async function toggleRealtimeTalk() {
    if (!authToken || !currentSessionId) {
        alert('セッションを開始してください');
        return;
    }
    
    if (isRealtimeTalking) {
        // 会話停止
        stopRealtimeConversation();
    } else {
        // 会話開始
        await startRealtimeConversation();
    }
}

/**
 * リアルタイム会話を開始
 */
async function startRealtimeConversation() {
    try {
        // 認証チェック
        if (!authToken) {
            alert('ログインしてください');
            return;
        }
        
        if (!currentSessionId) {
            alert('セッションを開始してください');
            return;
        }
        
        if (window.logger) {
            window.logger.info('リアルタイム会話を開始', { 
                hasAuthToken: !!authToken, 
                sessionId: currentSessionId 
            });
        }
        
        console.log('Starting realtime conversation with:', { authToken: authToken.substring(0, 10) + '...', currentSessionId });
        
        updateRealtimeStatus('connecting');
        updateRealtimeButton(true, '接続中...');
        
        // RealtimeClientを初期化
        if (!realtimeClient) {
            realtimeClient = new RealtimeClient(authToken, currentSessionId);
            
            // イベントハンドラーを設定
            realtimeClient.onConnected = () => {
                if (window.logger) {
                    window.logger.info('Realtime API接続成功');
                }
                updateRealtimeStatus('connected');
                
                // 音声ストリーミング開始
                realtimeClient.startAudioStream().catch(error => {
                    console.error('音声ストリーミング開始失敗:', error);
                    alert('マイクへのアクセスを許可してください');
                    stopRealtimeConversation();
                });
            };
            
            realtimeClient.onDisconnected = (code, reason) => {
                if (window.logger) {
                    window.logger.info('Realtime API切断', { code, reason });
                }
                updateRealtimeStatus('disconnected');
                isRealtimeTalking = false;
                updateRealtimeButton(false, '会話を開始');
            };
            
            realtimeClient.onTranscript = (text, role) => {
                // 文字起こしをチャットに表示
                if (role === 'user') {
                    addChatMessage('salesperson', text);
                } else if (role === 'assistant') {
                    // AIの応答を追加または更新
                    updateOrAddAIMessage(text);
                }
            };
            
            realtimeClient.onResponse = (response) => {
                if (window.logger) {
                    window.logger.info('AI応答完了', response);
                }
            };
            
            realtimeClient.onError = (error) => {
                console.error('Realtime API エラー:', error);
                if (window.logger) {
                    window.logger.error('Realtime API エラー', { error });
                }
                updateRealtimeStatus('error');
                
                // エラーメッセージを詳細に表示
                let errorMsg = 'エラーが発生しました';
                if (typeof error === 'string') {
                    errorMsg = error;
                } else if (error && error.message) {
                    errorMsg = error.message;
                }
                
                alert(`リアルタイム会話エラー: ${errorMsg}\n\nログを確認してください。`);
                stopRealtimeConversation();
            };
            
            realtimeClient.onStatusChange = (status) => {
                updateRealtimeStatus(status);
            };
        }
        
        // 接続
        await realtimeClient.connect();
        
        isRealtimeTalking = true;
        updateRealtimeButton(true, '会話を停止');
        
    } catch (error) {
        console.error('リアルタイム会話開始エラー:', error);
        if (window.logger) {
            window.logger.error('リアルタイム会話開始エラー', { error: error.message });
        }
        alert(`リアルタイム会話の開始に失敗しました: ${error.message}`);
        updateRealtimeStatus('error');
        updateRealtimeButton(false, '会話を開始');
    }
}

/**
 * リアルタイム会話を停止
 */
function stopRealtimeConversation() {
    if (window.logger) {
        window.logger.info('リアルタイム会話を停止');
    }
    
    if (realtimeClient) {
        realtimeClient.stopAudioStream();
        realtimeClient.disconnect();
        realtimeClient = null;
    }
    
    isRealtimeTalking = false;
    updateRealtimeButton(false, '会話を開始');
    updateRealtimeStatus('disconnected');
}

/**
 * リアルタイムボタンのUI更新
 */
function updateRealtimeButton(active, text) {
    const button = document.getElementById('realtimeTalkButton');
    const textSpan = document.getElementById('realtimeTalkText');
    
    if (button && textSpan) {
        if (active) {
            button.classList.add('active');
            textSpan.textContent = text || '会話を停止';
        } else {
            button.classList.remove('active');
            textSpan.textContent = text || '会話を開始';
        }
    }
}

/**
 * リアルタイムステータスの更新
 */
function updateRealtimeStatus(status) {
    const statusSpan = document.getElementById('realtimeStatus');
    if (!statusSpan) return;
    
    // クラスをリセット
    statusSpan.className = 'realtime-status';
    
    switch (status) {
        case 'connecting':
            statusSpan.textContent = '接続中...';
            break;
        case 'connected':
            statusSpan.textContent = '接続済み';
            statusSpan.classList.add('connected');
            break;
        case 'recording':
            statusSpan.textContent = '会話中';
            statusSpan.classList.add('recording');
            break;
        case 'disconnected':
            statusSpan.textContent = '未接続';
            break;
        case 'error':
            statusSpan.textContent = 'エラー';
            statusSpan.classList.add('error');
            break;
        default:
            statusSpan.textContent = status;
    }
}

/**
 * AIメッセージを更新または追加
 */
let currentAIMessageId = null;

function updateOrAddAIMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    // 既存のAIメッセージを更新
    if (currentAIMessageId) {
        const existingMessage = document.getElementById(currentAIMessageId);
        if (existingMessage) {
            const contentDiv = existingMessage.querySelector('.message-content');
            if (contentDiv) {
                contentDiv.textContent += text;
                chatMessages.scrollTop = chatMessages.scrollHeight;
                return;
            }
        }
    }
    
    // 新しいAIメッセージを作成
    currentAIMessageId = `ai-message-${Date.now()}`;
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message customer';
    messageDiv.id = currentAIMessageId;
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-role">AI顧客</span>
            <span class="message-time">${new Date().toLocaleTimeString('ja-JP')}</span>
        </div>
        <div class="message-content">${text}</div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * セッション終了時のクリーンアップ
 */
function cleanupRealtimeSession() {
    if (realtimeClient) {
        stopRealtimeConversation();
    }
    currentAIMessageId = null;
}

// セッション終了時にクリーンアップ
const originalFinishSession = window.finishSession;
if (originalFinishSession) {
    window.finishSession = function() {
        cleanupRealtimeSession();
        return originalFinishSession.apply(this, arguments);
    };
}


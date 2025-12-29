/**
 * リアルタイム会話機能
 * OpenAI Realtime APIを使用したリアルタイム音声会話
 */

// 音声出力設定
let enableAudioOutput = false;
let audioOutputContext = null;
let audioQueue = [];
let isPlayingAudio = false;

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
    
    // 簡易診断モードではリアルタイム会話を使用できない
    if (typeof currentMode !== 'undefined' && currentMode === 'simple') {
        alert('簡易診断モードではリアルタイム会話は使用できません。\n詳細診断モードをご利用ください。');
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
        
        // 音声出力の確認ダイアログ
        enableAudioOutput = confirm('AI顧客の音声を出力しますか？\n\nはい: 音声出力あり\nいいえ: テキストのみ');
        
        if (enableAudioOutput) {
            console.log('🔊 音声出力: 有効');
            // AudioContextを初期化
            audioOutputContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 24000
            });
        } else {
            console.log('🔇 音声出力: 無効');
        }
        
        if (window.logger) {
            window.logger.info('リアルタイム会話を開始', { 
                hasAuthToken: !!authToken, 
                sessionId: currentSessionId,
                audioOutput: enableAudioOutput
            });
        }
        
        console.log('Starting realtime conversation with:', { authToken: authToken.substring(0, 10) + '...', currentSessionId, audioOutput: enableAudioOutput });
        
        updateRealtimeStatus('connecting');
        updateRealtimeButton(true, '接続中...');
        
        // セッション情報を取得（グローバル変数から）
        let sessionInfo = null;
        
        if (typeof currentSessionInfo !== 'undefined' && currentSessionInfo) {
            // app.js で保存されたセッション情報を使用
            sessionInfo = currentSessionInfo;
            console.log('📋 セッション情報（グローバル変数から取得）:', sessionInfo);
        } else {
            // フォールバック: 企業情報から取得
            sessionInfo = {
                customer_persona: null,
                industry: null,
                company_name: null,
                value_proposition: null
            };
            
            if (typeof currentCompanyInfo !== 'undefined' && currentCompanyInfo) {
                sessionInfo.company_name = currentCompanyInfo.company_name;
                sessionInfo.industry = currentCompanyInfo.industry;
            }
            
            console.log('📋 セッション情報（フォールバック）:', sessionInfo);
        }
        
        // RealtimeClientを初期化
        if (!realtimeClient) {
            realtimeClient = new RealtimeClient(authToken, currentSessionId, sessionInfo);
            
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
                // AI応答が完了したら、次の応答は新しいメッセージとして作成
                currentAIMessageId = null;
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
            
            // 音声再生ハンドラー（音声出力が有効な場合のみ）
            if (enableAudioOutput) {
                realtimeClient.onAudio = (base64Audio) => {
                    playAudioChunk(base64Audio);
                };
            }
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
    
    // 音声出力のクリーンアップ
    stopAudioOutput();
    
    isRealtimeTalking = false;
    updateRealtimeButton(false, '会話を開始');
    updateRealtimeStatus('disconnected');
}

/**
 * Base64エンコードされたPCM16音声データを再生
 */
function playAudioChunk(base64Audio) {
    if (!enableAudioOutput || !audioOutputContext) {
        return;
    }
    
    try {
        // Base64をArrayBufferに変換
        const binaryString = atob(base64Audio);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        
        // PCM16をFloat32に変換
        const pcm16 = new Int16Array(bytes.buffer);
        const float32 = new Float32Array(pcm16.length);
        for (let i = 0; i < pcm16.length; i++) {
            float32[i] = pcm16[i] / 32768.0;
        }
        
        // AudioBufferを作成
        const audioBuffer = audioOutputContext.createBuffer(1, float32.length, 24000);
        audioBuffer.getChannelData(0).set(float32);
        
        // キューに追加
        audioQueue.push(audioBuffer);
        
        // 再生開始
        if (!isPlayingAudio) {
            playNextAudioBuffer();
        }
    } catch (error) {
        console.error('音声再生エラー:', error);
    }
}

/**
 * キュー内の次の音声バッファを再生
 */
function playNextAudioBuffer() {
    if (audioQueue.length === 0) {
        isPlayingAudio = false;
        return;
    }
    
    isPlayingAudio = true;
    
    const buffer = audioQueue.shift();
    const source = audioOutputContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioOutputContext.destination);
    
    source.onended = () => {
        playNextAudioBuffer();
    };
    
    source.start();
}

/**
 * 音声出力を停止してクリーンアップ
 */
function stopAudioOutput() {
    audioQueue = [];
    isPlayingAudio = false;
    
    if (audioOutputContext && audioOutputContext.state !== 'closed') {
        audioOutputContext.close().catch(() => {});
        audioOutputContext = null;
    }
    
    enableAudioOutput = false;
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


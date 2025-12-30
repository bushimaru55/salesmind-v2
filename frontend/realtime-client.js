/**
 * OpenAI Realtime API WebSocketクライアント
 * 
 * リアルタイム音声会話を管理します
 */
class RealtimeClient {
    constructor(authToken, sessionId = null, sessionInfo = null, voice = 'alloy') {
        this.authToken = authToken;
        this.sessionId = sessionId;
        this.sessionInfo = sessionInfo;  // セッション情報（企業情報、ペルソナ等）
        this.voice = voice;  // 音声設定（alloy, echo, fable, onyx, nova, shimmer）
        this.ws = null;
        this.isConnected = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.mediaRecorder = null;
        this.isRecording = false;
        this.sessionConfigured = false;  // セッション設定済みフラグ
        this.sessionReady = false;  // セッション準備完了フラグ
        
        // イベントハンドラー
        this.onConnected = null;
        this.onDisconnected = null;
        this.onTranscript = null;
        this.onResponse = null;
        this.onAudio = null;
        this.onError = null;
        this.onStatusChange = null;
        this.onUserSpeechStopped = null;  // ユーザー発言停止時のコールバック
        
        // メッセージ順序管理
        this.pendingUserItemId = null;  // 文字起こし待ちのユーザーメッセージID
        
        console.log(`🎤 RealtimeClient初期化: voice=${this.voice}`);
    }
    
    /**
     * OpenAI Realtime APIに接続
     */
    async connect() {
        try {
            console.log('='.repeat(80));
            console.log('🚀 Realtime API接続開始');
            
            if (this.isConnected) {
                console.warn('⚠️ 既に接続済み');
                return;
            }
            
            // WebSocket URL
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsHost = window.location.host;
            let wsUrl = `${wsProtocol}//${wsHost}/ws/realtime/?token=${this.authToken}`;
            
            if (this.sessionId) {
                wsUrl += `&session_id=${this.sessionId}`;
            }
            
            console.log('📍 接続情報:');
            console.log('  - Protocol:', wsProtocol);
            console.log('  - Host:', wsHost);
            console.log('  - Token:', this.authToken.substring(0, 10) + '...');
            console.log('  - Session:', this.sessionId);
            console.log('  - URL:', wsUrl.replace(this.authToken, 'TOKEN'));
            
            this._emitStatus('connecting');
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket接続成功');
                console.log('  - readyState:', this.ws.readyState);
                console.log('  - protocol:', this.ws.protocol);
                this.isConnected = true;
                this._emitStatus('connected');
                if (this.onConnected) {
                    this.onConnected();
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('🔌 WebSocket切断');
                console.log('  - Code:', event.code);
                console.log('  - Reason:', event.reason || '(理由なし)');
                console.log('  - Clean:', event.wasClean);
                this.isConnected = false;
                this.sessionConfigured = false;  // フラグリセット
                this.sessionReady = false;  // フラグリセット
                this._emitStatus('disconnected');
                if (this.onDisconnected) {
                    this.onDisconnected(event.code, event.reason);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('❌ WebSocketエラー');
                console.error('  - Error:', error);
                console.error('  - readyState:', this.ws.readyState);
                console.error('  - URL:', wsUrl.replace(this.authToken, 'TOKEN'));
                this._emitError(`WebSocket connection error: ${error.message || 'Unknown error'}`);
            };
            
            this.ws.onmessage = (event) => {
                this._handleMessage(event);
            };
            
        } catch (error) {
            console.error('Failed to connect:', error);
            this._emitError(`Connection failed: ${error.message}`);
            throw error;
        }
    }
    
    /**
     * WebSocket切断
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
        this._stopAudioCapture();
    }
    
    /**
     * 音声ストリーミング開始
     */
    async startAudioStream() {
        try {
            if (!this.isConnected) {
                throw new Error('Not connected to Realtime API');
            }
            
            if (this.isRecording) {
                console.warn('Already recording');
                return;
            }
            
            console.log('Starting audio stream...');
            this._emitStatus('recording');
            
            // マイクアクセス
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 24000
                }
            });
            
            // AudioContextでPCM16に変換
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 24000
            });
            
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            
            // 音声データ送信カウンター（デバッグ用）
            this.audioChunkCount = 0;
            this.lastLogTime = Date.now();
            
            this.processor.onaudioprocess = (e) => {
                if (!this.isRecording || !this.isConnected) return;
                
                // セッション準備完了まで音声送信を待機
                if (!this.sessionReady) {
                    return;
                }
                
                const inputData = e.inputBuffer.getChannelData(0);
                // Float32からPCM16に変換
                const pcm16 = this._float32ToPCM16(inputData);
                
                // WebSocketでバイナリデータとして送信
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(pcm16);
                    this.audioChunkCount++;
                    
                    // 1秒ごとにログ出力
                    const now = Date.now();
                    if (now - this.lastLogTime >= 1000) {
                        console.log(`🎤 音声送信中: ${this.audioChunkCount} chunks/sec (${pcm16.byteLength} bytes/chunk)`);
                        this.audioChunkCount = 0;
                        this.lastLogTime = now;
                    }
                } else {
                    console.warn('⚠️ WebSocket未接続: readyState =', this.ws ? this.ws.readyState : 'null');
                }
            };
            
            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            
            this.isRecording = true;
            
            // セッション設定はsession.created受信後に送信するため、ここでは送信しない
            
            console.log('Audio streaming started with PCM16 format');
            
        } catch (error) {
            console.error('Failed to start audio stream:', error);
            this._emitError(`Failed to start audio: ${error.message}`);
            throw error;
        }
    }
    
    /**
     * 音声ストリーミング停止
     */
    stopAudioStream() {
        this._stopAudioCapture();
        this._emitStatus('connected');
        console.log('Audio streaming stopped');
    }
    
    /**
     * 音声キャプチャの停止
     */
    _stopAudioCapture() {
        this.isRecording = false;
        
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
            this.audioContext = null;
        }
    }
    
    /**
     * Float32からPCM16に変換
     */
    _float32ToPCM16(float32Array) {
        const buffer = new ArrayBuffer(float32Array.length * 2);
        const view = new DataView(buffer);
        
        for (let i = 0; i < float32Array.length; i++) {
            // -1.0 ~ 1.0 の範囲にクリップ
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            // Int16に変換 (-32768 ~ 32767)
            const val = s < 0 ? s * 0x8000 : s * 0x7FFF;
            view.setInt16(i * 2, val, true); // little-endian
        }
        
        return buffer;
    }
    
    /**
     * セッション情報から顧客ペルソナのinstructionsを生成
     */
    _buildCustomerInstructions() {
        let instructions = `【重要：日本語で会話してください】

あなたは日本の企業で働くビジネスパーソンです。
必ず日本語で会話してください。韓国語、英語、その他の言語は使用禁止です。

【あなたは「リアルな顧客」です】

あなたは営業ロールプレイで「顧客」役を演じます。
相手（ユーザー）が「営業担当者」で、あなたに商品を売り込んできます。
あなたは忙しいビジネスパーソンで、貴重な時間を割いて話を聞いています。

=== 会話のルール（重要） ===
- 相手の発言を最後まで聞いてから返答する
- 相手が話している途中で割り込まない
- 相手の発言が完了するまで待つ
- 短い返答でも問題ない（「はい」「なるほど」など）

=== あなたの基本姿勢 ===
- 商品について何も知らない（営業から教えてもらう立場）
- 忙しいので要点を簡潔に説明してほしい
- 本当に役立つなら検討するが、簡単には決めない
- 予算、上司の承認、導入時期など現実的な制約がある

=== リアルな顧客としての反応 ===

【失礼・不真面目な対応を受けた場合】
- 「ちょっと、真面目にやってもらえますか？」
- 「失礼ですね。お時間いただいてるんですが」
- 「ふざけてるんですか？」
- 「これ以上話しても無駄そうですね」と打ち切る
- 冷たい態度で短く返答する

【曖昧・わかりにくい説明を受けた場合】
- 「すみません、よくわかりません」
- 「結局何がメリットなんですか？」
- 「もっと具体的に説明してください」

【興味がない・必要性を感じない場合】
- 「うちには必要ないかな」
- 「今は他に優先すべきことがあるので」
- 「検討しますが、正直あまり興味ないです」

【価格・コストについて】
- 「それ、いくらするんですか？」
- 「高いですね。費用対効果はどうですか？」
- 「予算が限られているので難しいかもしれません」

【導入への懸念】
- 「上に相談しないと決められません」
- 「他社でも似たようなのありますよね？」
- 「導入にどのくらい時間かかりますか？」

=== 絶対にやらないこと ===
- 商品の説明をする（あなたは知らない）
- 「何かご質問は？」など営業的な質問をする
- 「ご説明しましょうか」と提案する
- 過度に親切・協力的になる

=== 応答の基本 ===
- 挨拶 → 短く返す「よろしくお願いします」
- 説明を聞いたら → 「なるほど」「へえ」「それで？」
- 質問されたら → 自社の状況を正直に答える
- わからなければ → 「それはどういうことですか？」
`;
        
        // セッション情報がある場合、詳細なペルソナを追加
        if (this.sessionInfo) {
            if (this.sessionInfo.customer_persona) {
                instructions += `\n=== あなたのペルソナ・役割 ===\n${this.sessionInfo.customer_persona}\n`;
            }
            
            if (this.sessionInfo.industry) {
                instructions += `\n=== あなたの業界 ===\n${this.sessionInfo.industry}\n`;
            }
            
            if (this.sessionInfo.company_name) {
                instructions += `\n=== あなたの会社名 ===\n${this.sessionInfo.company_name}\n`;
            }
            
            if (this.sessionInfo.value_proposition) {
                instructions += `\n=== 営業担当者が提案しようとしている商品・サービス ===\n${this.sessionInfo.value_proposition}\n（注意：これはあなたが売るものではなく、営業担当者があなたに提案してくるものです）\n`;
            }
        }
        
        instructions += `

=== 最終確認 ===
- 必ず日本語で会話する（韓国語・英語は禁止）
- あなたは忙しいビジネスパーソン
- 商品知識はゼロ（営業から聞く立場）
- 失礼な対応には厳しく対応する
- 納得できなければ断る
- 営業的な質問（「何かご質問は？」など）は絶対にしない
- 商品の説明は絶対にしない（あなたは知らない）`;
        
        console.log('📝 生成されたinstructions:', instructions);
        return instructions;
    }
    
    /**
     * セッション設定を送信
     */
    _sendSessionConfig() {
        if (!this.isConnected) {
            console.warn('⚠️ セッション設定送信スキップ: 未接続');
            return;
        }
        
        const instructions = this._buildCustomerInstructions();
        
        const config = {
            type: 'session.update',
            session: {
                model: 'gpt-realtime',
                modalities: ['audio', 'text'],
                instructions: instructions,
                voice: this.voice,
                input_audio_format: 'pcm16',
                input_audio_transcription: {
                    model: 'gpt-4o-mini-transcribe',
                    language: 'ja'
                },
                turn_detection: {
                    type: 'server_vad',
                    // 発言終了の検出感度を調整
                    threshold: 0.6,              // 音声検出の感度（0.0-1.0、高いほど感度低下）
                    prefix_padding_ms: 400,      // 発言開始前のパディング（ミリ秒）
                    silence_duration_ms: 800     // 発言終了と判定する無音時間（ミリ秒、長めに設定）
                },
                output_audio_format: 'pcm16'
            }
        };
        
        console.log('📤 セッション設定送信:');
        console.log(JSON.stringify(config, null, 2));
        
        try {
            this.ws.send(JSON.stringify(config));
            console.log('✅ セッション設定送信完了');
        } catch (error) {
            console.error('❌ セッション設定送信失敗:', error);
        }
    }
    
    /**
     * メッセージ受信処理
     */
    _handleMessage(event) {
        try {
            if (typeof event.data === 'string') {
                const data = JSON.parse(event.data);
                const msgType = data.type;
                
                console.log('📩 メッセージ受信:', msgType);
                
                switch (msgType) {
                    case 'error':
                        console.error('❌ OpenAIエラー:');
                        console.error('  - Type:', data.error.type);
                        console.error('  - Code:', data.error.code);
                        console.error('  - Message:', data.error.message);
                        console.error('  - Full:', JSON.stringify(data.error, null, 2));
                        this._emitError(`OpenAI Error: ${data.error.message || JSON.stringify(data.error)}`);
                        
                        // エラー詳細をログに記録
                        if (window.logger) {
                            window.logger.error('OpenAI Realtime Error', data.error);
                        }
                        break;
                    
                    case 'session.created':
                        console.log('✅ セッション作成:', JSON.stringify(data.session, null, 2));
                        // セッション作成後に設定を送信（1回のみ）
                        if (!this.sessionConfigured) {
                            this.sessionConfigured = true;
                            this._sendSessionConfig();
                        } else {
                            console.warn('⚠️ セッション設定は既に送信済み');
                        }
                        break;
                    
                    case 'session.updated':
                        console.log('✅ セッション更新:', JSON.stringify(data.session, null, 2));
                        // セッション更新完了 - 音声送信可能
                        this.sessionReady = true;
                        console.log('🎤 音声送信準備完了');
                        break;
                    
                    case 'input_audio_buffer.speech_stopped':
                        // ユーザーの発言が停止 - プレースホルダーを作成
                        console.log('🎙️ ユーザー発言停止:', data.item_id);
                        this.pendingUserItemId = data.item_id;
                        if (this.onUserSpeechStopped) {
                            this.onUserSpeechStopped(data.item_id);
                        }
                        break;
                    
                    case 'conversation.item.input_audio_transcription.completed':
                        // ユーザーの発言の文字起こし完了
                        console.log('📝 ユーザー文字起こし完了:', data.item_id);
                        if (this.onTranscript && data.transcript) {
                            this.onTranscript(data.transcript, 'user', data.item_id);
                        }
                        this.pendingUserItemId = null;
                        break;
                    
                    case 'response.audio_transcript.delta':
                        // AIの応答の文字起こし（リアルタイム）
                        if (this.onTranscript && data.delta) {
                            this.onTranscript(data.delta, 'assistant', null);
                        }
                        break;
                    
                    case 'response.audio.delta':
                        // 音声データ（Base64エンコード済みPCM16）
                        if (this.onAudio && data.delta) {
                            this.onAudio(data.delta);
                        }
                        break;
                    
                    case 'response.done':
                        // 応答完了
                        if (this.onResponse) {
                            this.onResponse(data.response);
                        }
                        break;
                    
                    case 'error':
                        console.error('Realtime API error:', data.error);
                        this._emitError(data.error.message || 'Unknown error');
                        break;
                }
            }
        } catch (error) {
            console.error('Failed to handle message:', error);
        }
    }
    
    /**
     * エラーイベントを発火
     */
    _emitError(message) {
        if (this.onError) {
            this.onError(message);
        }
    }
    
    /**
     * ステータスイベントを発火
     */
    _emitStatus(status) {
        if (this.onStatusChange) {
            this.onStatusChange(status);
        }
    }
}

// グローバルスコープに登録
window.RealtimeClient = RealtimeClient;


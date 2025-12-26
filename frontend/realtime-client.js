/**
 * OpenAI Realtime API WebSocketクライアント
 * 
 * リアルタイム音声会話を管理します
 */
class RealtimeClient {
    constructor(authToken, sessionId = null) {
        this.authToken = authToken;
        this.sessionId = sessionId;
        this.ws = null;
        this.isConnected = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.mediaRecorder = null;
        this.isRecording = false;
        
        // イベントハンドラー
        this.onConnected = null;
        this.onDisconnected = null;
        this.onTranscript = null;
        this.onResponse = null;
        this.onAudio = null;
        this.onError = null;
        this.onStatusChange = null;
    }
    
    /**
     * OpenAI Realtime APIに接続
     */
    async connect() {
        try {
            if (this.isConnected) {
                console.warn('Already connected');
                return;
            }
            
            // WebSocket URL
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsHost = window.location.host;
            let wsUrl = `${wsProtocol}//${wsHost}/ws/realtime/?token=${this.authToken}`;
            
            if (this.sessionId) {
                wsUrl += `&session_id=${this.sessionId}`;
            }
            
            console.log('Connecting to Realtime API...');
            this._emitStatus('connecting');
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this._emitStatus('connected');
                if (this.onConnected) {
                    this.onConnected();
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.isConnected = false;
                this._emitStatus('disconnected');
                if (this.onDisconnected) {
                    this.onDisconnected(event.code, event.reason);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this._emitError('WebSocket connection error');
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
            
            // AudioContext初期化
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 24000
            });
            
            // MediaRecorder設定
            const options = {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 16000
            };
            
            this.mediaRecorder = new MediaRecorder(this.mediaStream, options);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && this.isConnected) {
                    // 音声データをOpenAIに送信
                    this.ws.send(event.data);
                }
            };
            
            // 100msごとに音声データを送信
            this.mediaRecorder.start(100);
            this.isRecording = true;
            
            // セッション設定を送信
            this._sendSessionConfig();
            
            console.log('Audio streaming started');
            
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
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaRecorder = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        this.isRecording = false;
    }
    
    /**
     * セッション設定を送信
     */
    _sendSessionConfig() {
        if (!this.isConnected) return;
        
        const config = {
            type: 'session.update',
            session: {
                modalities: ['text', 'audio'],
                instructions: 'あなたはAI営業顧客として、営業担当者と会話します。日本語で応答してください。',
                voice: 'alloy',
                input_audio_format: 'pcm16',
                output_audio_format: 'pcm16',
                input_audio_transcription: {
                    model: 'whisper-1'
                },
                turn_detection: {
                    type: 'server_vad',
                    threshold: 0.5,
                    prefix_padding_ms: 300,
                    silence_duration_ms: 500
                }
            }
        };
        
        this.ws.send(JSON.stringify(config));
    }
    
    /**
     * メッセージ受信処理
     */
    _handleMessage(event) {
        try {
            if (typeof event.data === 'string') {
                const data = JSON.parse(event.data);
                console.log('Received:', data.type);
                
                switch (data.type) {
                    case 'session.created':
                    case 'session.updated':
                        console.log('Session ready:', data);
                        break;
                    
                    case 'conversation.item.input_audio_transcription.completed':
                        // ユーザーの発言の文字起こし
                        if (this.onTranscript && data.transcript) {
                            this.onTranscript(data.transcript, 'user');
                        }
                        break;
                    
                    case 'response.audio_transcript.delta':
                        // AIの応答の文字起こし（リアルタイム）
                        if (this.onTranscript && data.delta) {
                            this.onTranscript(data.delta, 'assistant');
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


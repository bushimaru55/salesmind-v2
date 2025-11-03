// ログ管理クラス
class Logger {
    constructor() {
        this.logs = [];
        this.maxLogs = 1000; // 最大保存件数
        this.loadLogs();
    }

    // ログを読み込む
    loadLogs() {
        try {
            const savedLogs = localStorage.getItem('salesmind_logs');
            if (savedLogs) {
                this.logs = JSON.parse(savedLogs);
            }
        } catch (error) {
            console.error('ログの読み込みに失敗しました:', error);
            this.logs = [];
        }
    }

    // ログを保存する
    saveLogs() {
        try {
            // 最大件数を超える場合は古いログを削除
            if (this.logs.length > this.maxLogs) {
                this.logs = this.logs.slice(-this.maxLogs);
            }
            localStorage.setItem('salesmind_logs', JSON.stringify(this.logs));
        } catch (error) {
            console.error('ログの保存に失敗しました:', error);
            // LocalStorageが満杯の場合、古いログを削除して再試行
            if (error.name === 'QuotaExceededError') {
                this.logs = this.logs.slice(-500);
                try {
                    localStorage.setItem('salesmind_logs', JSON.stringify(this.logs));
                } catch (e) {
                    console.error('ログの保存に再試行しても失敗しました:', e);
                }
            }
        }
    }

    // ログを追加
    log(level, message, data = null) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level: level, // 'info', 'warning', 'error', 'debug'
            message: message,
            data: data,
            userAgent: navigator.userAgent,
            url: window.location.href
        };

        this.logs.push(logEntry);
        this.saveLogs();

        // コンソールにも出力
        const consoleMethod = level === 'error' ? 'error' : level === 'warning' ? 'warn' : 'log';
        console[consoleMethod](`[${level.toUpperCase()}] ${message}`, data || '');

        // ログビューアーが開いていれば更新
        if (window.logViewer) {
            window.logViewer.updateLogs();
        }
    }

    // 情報ログ
    info(message, data = null) {
        this.log('info', message, data);
    }

    // 警告ログ
    warning(message, data = null) {
        this.log('warning', message, data);
    }

    // エラーログ
    error(message, data = null) {
        this.log('error', message, data);
    }

    // デバッグログ
    debug(message, data = null) {
        this.log('debug', message, data);
    }

    // APIリクエストログ
    apiRequest(method, url, requestData = null) {
        this.debug(`API Request: ${method} ${url}`, requestData);
    }

    // APIレスポンスログ
    apiResponse(method, url, status, responseData = null, error = null) {
        if (error || status >= 400) {
            this.error(`API Response: ${method} ${url} - Status: ${status}`, { response: responseData, error: error });
        } else {
            this.info(`API Response: ${method} ${url} - Status: ${status}`, responseData);
        }
    }

    // すべてのログを取得
    getAllLogs() {
        return this.logs;
    }

    // ログをクリア
    clearLogs() {
        this.logs = [];
        this.saveLogs();
        this.info('ログをクリアしました');
    }

    // ログをエクスポート（JSON形式）
    exportLogs() {
        const dataStr = JSON.stringify(this.logs, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `salesmind_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        this.info('ログをエクスポートしました');
    }

    // エラーログのみを取得
    getErrorLogs() {
        return this.logs.filter(log => log.level === 'error');
    }

    // 最近のログを取得
    getRecentLogs(count = 50) {
        return this.logs.slice(-count);
    }
}

// グローバルロガーインスタンス
window.logger = new Logger();


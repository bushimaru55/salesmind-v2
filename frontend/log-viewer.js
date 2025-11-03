// ログビューアークラス
class LogViewer {
    constructor() {
        this.isVisible = false;
        this.filterInfo = true;
        this.filterWarning = true;
        this.filterError = true;
        this.filterDebug = true;
        this.init();
    }

    init() {
        // チェックボックスの状態を復元
        const savedFilters = localStorage.getItem('logViewerFilters');
        if (savedFilters) {
            const filters = JSON.parse(savedFilters);
            this.filterInfo = filters.info !== false;
            this.filterWarning = filters.warning !== false;
            this.filterError = filters.error !== false;
            this.filterDebug = filters.debug !== false;
            
            const infoCheck = document.getElementById('filterInfo');
            const warningCheck = document.getElementById('filterWarning');
            const errorCheck = document.getElementById('filterError');
            const debugCheck = document.getElementById('filterDebug');
            
            if (infoCheck) infoCheck.checked = this.filterInfo;
            if (warningCheck) warningCheck.checked = this.filterWarning;
            if (errorCheck) errorCheck.checked = this.filterError;
            if (debugCheck) debugCheck.checked = this.filterDebug;
        }
    }

    toggle() {
        this.isVisible = !this.isVisible;
        const viewer = document.getElementById('logViewer');
        if (viewer) {
            viewer.style.display = this.isVisible ? 'block' : 'none';
        }
        if (this.isVisible) {
            this.updateLogs();
        }
    }

    close() {
        this.isVisible = false;
        const viewer = document.getElementById('logViewer');
        if (viewer) {
            viewer.style.display = 'none';
        }
    }

    updateLogs() {
        // フィルター状態を更新
        const infoCheck = document.getElementById('filterInfo');
        const warningCheck = document.getElementById('filterWarning');
        const errorCheck = document.getElementById('filterError');
        const debugCheck = document.getElementById('filterDebug');
        
        if (infoCheck) this.filterInfo = infoCheck.checked;
        if (warningCheck) this.filterWarning = warningCheck.checked;
        if (errorCheck) this.filterError = errorCheck.checked;
        if (debugCheck) this.filterDebug = debugCheck.checked;

        // フィルター状態を保存
        localStorage.setItem('logViewerFilters', JSON.stringify({
            info: this.filterInfo,
            warning: this.filterWarning,
            error: this.filterError,
            debug: this.filterDebug
        }));

        const container = document.getElementById('logViewerContent');
        if (!container) return;

        if (!window.logger) {
            container.innerHTML = '<p>ロガーが初期化されていません</p>';
            return;
        }

        const allLogs = window.logger.getAllLogs();
        
        // フィルター適用
        const filteredLogs = allLogs.filter(log => {
            if (log.level === 'info' && !this.filterInfo) return false;
            if (log.level === 'warning' && !this.filterWarning) return false;
            if (log.level === 'error' && !this.filterError) return false;
            if (log.level === 'debug' && !this.filterDebug) return false;
            return true;
        });

        // 最新順に表示
        filteredLogs.reverse();

        if (filteredLogs.length === 0) {
            container.innerHTML = '<p>ログがありません</p>';
            return;
        }

        const logHTML = filteredLogs.map(log => {
            const levelClass = `log-${log.level}`;
            const time = new Date(log.timestamp).toLocaleString('ja-JP');
            let dataHTML = '';
            
            if (log.data) {
                if (typeof log.data === 'object') {
                    dataHTML = `<pre class="log-data">${JSON.stringify(log.data, null, 2)}</pre>`;
                } else {
                    dataHTML = `<pre class="log-data">${log.data}</pre>`;
                }
            }

            return `
                <div class="log-entry ${levelClass}">
                    <div class="log-header">
                        <span class="log-level">[${log.level.toUpperCase()}]</span>
                        <span class="log-time">${time}</span>
                    </div>
                    <div class="log-message">${this.escapeHtml(log.message)}</div>
                    ${dataHTML}
                </div>
            `;
        }).join('');

        container.innerHTML = logHTML;
        
        // 自動スクロール
        container.scrollTop = 0;
    }

    exportLogs() {
        if (window.logger) {
            window.logger.exportLogs();
        }
    }

    clearLogs() {
        if (confirm('すべてのログを削除しますか？')) {
            if (window.logger) {
                window.logger.clearLogs();
                this.updateLogs();
            }
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// グローバルログビューアーインスタンス
window.logViewer = new LogViewer();


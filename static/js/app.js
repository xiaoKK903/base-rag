const App = {
    loading: false,
    loadingCount: 0,

    API_BASE: '/api',

    init() {
        this.setupToastContainer();
        console.log('App initialized');
    },

    setupToastContainer() {
        if (!document.getElementById('toast-container')) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
    },

    async request(url, options = {}) {
        const {
            method = 'GET',
            headers = {},
            body,
            showLoading = true,
            showError = true,
            showSuccess = false
        } = options;

        if (showLoading) {
            this.showLoading();
        }

        try {
            const fetchOptions = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    ...headers
                },
                credentials: 'same-origin'
            };

            if (body && method !== 'GET') {
                fetchOptions.body = JSON.stringify(body);
            }

            const response = await fetch(this.API_BASE + url, fetchOptions);
            const result = await response.json();

            if (showLoading) {
                this.hideLoading();
            }

            if (result.code === 0 || (result.success !== undefined && result.success)) {
                if (showSuccess) {
                    this.toast.success(result.message || '操作成功');
                }
                return result;
            } else {
                if (showError) {
                    this.toast.error(result.message || '操作失败');
                }
                return Promise.reject(result);
            }

        } catch (error) {
            if (showLoading) {
                this.hideLoading();
            }

            if (error.code !== undefined) {
                return Promise.reject(error);
            }

            const errorResult = {
                code: -1,
                message: error.message || '网络请求失败',
                data: null
            };

            if (showError) {
                this.toast.error(errorResult.message);
            }

            return Promise.reject(errorResult);
        }
    },

    get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    },

    post(url, body, options = {}) {
        return this.request(url, { ...options, method: 'POST', body });
    },

    put(url, body, options = {}) {
        return this.request(url, { ...options, method: 'PUT', body });
    },

    delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    },

    showLoading() {
        this.loadingCount++;
        if (this.loadingCount > 0 && !this.loading) {
            this.loading = true;
            this.renderLoadingOverlay();
        }
    },

    hideLoading() {
        this.loadingCount = Math.max(0, this.loadingCount - 1);
        if (this.loadingCount === 0 && this.loading) {
            this.loading = false;
            this.removeLoadingOverlay();
        }
    },

    renderLoadingOverlay() {
        if (document.getElementById('loading-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(overlay);
    },

    removeLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    },

    toast: {
        _toastId: 0,

        _create(toastType, message, duration = 3000) {
            const container = document.getElementById('toast-container') ||
                (() => {
                    const c = document.createElement('div');
                    c.id = 'toast-container';
                    c.className = 'toast-container';
                    document.body.appendChild(c);
                    return c;
                })();

            const toastId = ++this._toastId;
            const toast = document.createElement('div');
            toast.className = `toast ${toastType}`;
            toast.id = `toast-${toastId}`;

            toast.innerHTML = `
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="App.toast._remove(${toastId})">&times;</button>
            `;

            container.appendChild(toast);

            if (duration > 0) {
                setTimeout(() => this._remove(toastId), duration);
            }

            return toastId;
        },

        _remove(toastId) {
            const toast = document.getElementById(`toast-${toastId}`);
            if (toast) {
                toast.style.animation = 'none';
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                toast.style.transition = 'all 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        },

        success(message, duration) {
            return this._create('success', message, duration);
        },

        error(message, duration) {
            return this._create('error', message, duration);
        },

        warning(message, duration) {
            return this._create('warning', message, duration);
        },

        info(message, duration) {
            return this._create('info', message, duration);
        }
    },

    utils: {
        formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
            const d = new Date(date);
            const map = {
                'YYYY': d.getFullYear(),
                'MM': String(d.getMonth() + 1).padStart(2, '0'),
                'DD': String(d.getDate()).padStart(2, '0'),
                'HH': String(d.getHours()).padStart(2, '0'),
                'mm': String(d.getMinutes()).padStart(2, '0'),
                'ss': String(d.getSeconds()).padStart(2, '0')
            };
            return format.replace(/YYYY|MM|DD|HH|mm|ss/g, matched => map[matched]);
        },

        debounce(fn, delay = 300) {
            let timer = null;
            return function (...args) {
                clearTimeout(timer);
                timer = setTimeout(() => fn.apply(this, args), delay);
            };
        },

        throttle(fn, delay = 300) {
            let last = 0;
            return function (...args) {
                const now = Date.now();
                if (now - last > delay) {
                    last = now;
                    fn.apply(this, args);
                }
            };
        },

        deepClone(obj) {
            if (obj === null || typeof obj !== 'object') return obj;
            if (obj instanceof Date) return new Date(obj);
            if (obj instanceof Array) return obj.map(item => this.deepClone(item));
            if (obj instanceof Object) {
                const copy = {};
                Object.keys(obj).forEach(key => {
                    copy[key] = this.deepClone(obj[key]);
                });
                return copy;
            }
            return obj;
        },

        isEmpty(value) {
            if (value === null || value === undefined) return true;
            if (typeof value === 'string' && value.trim() === '') return true;
            if (Array.isArray(value) && value.length === 0) return true;
            if (typeof value === 'object' && Object.keys(value).length === 0) return true;
            return false;
        },

        generateId() {
            return Date.now().toString(36) + Math.random().toString(36).substr(2);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

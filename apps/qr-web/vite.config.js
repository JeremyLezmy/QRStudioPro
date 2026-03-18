var _a, _b;
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
var envBase = (_b = (_a = globalThis.process) === null || _a === void 0 ? void 0 : _a.env) === null || _b === void 0 ? void 0 : _b.VITE_BASE_PATH;
var base = envBase !== null && envBase !== void 0 ? envBase : '/';
export default defineConfig({
    base: base,
    plugins: [react()],
    server: {
        host: true,
        port: 5173,
    },
});

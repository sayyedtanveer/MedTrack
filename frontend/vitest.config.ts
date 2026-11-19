import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  root: path.resolve(__dirname, '..'),
  server: { fs: { allow: [path.resolve(__dirname, '..')] } },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: path.resolve(__dirname, './src/test/setup.ts'),
    include: ['frontend/src/**/*.{test,spec}.?(c|m)[jt]s?(x)', 'tests/unit/frontend/**/*.test.tsx'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      react: path.resolve(__dirname, './node_modules/react'),
      'react-dom': path.resolve(__dirname, './node_modules/react-dom'),
      'react-router-dom': path.resolve(__dirname, './node_modules/react-router-dom'),
      '@tanstack/react-query': path.resolve(__dirname, './node_modules/@tanstack/react-query'),
      '@testing-library/react': path.resolve(__dirname, './node_modules/@testing-library/react'),
      vitest: path.resolve(__dirname, './node_modules/vitest'),
    },
  },
});

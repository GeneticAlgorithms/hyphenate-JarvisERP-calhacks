import { defineConfig } from 'vite'

export default defineConfig({
  base: '/hyphenate-JarvisERP-calhacks/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          gsap: ['gsap']
        }
      }
    }
  }
})

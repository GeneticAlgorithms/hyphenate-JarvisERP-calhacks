import { test, expect } from '@playwright/test'

test.describe('JarvisERP Showcase', () => {
  test('should load homepage without errors', async ({ page }) => {
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    await expect(page).toHaveTitle(/JarvisERP/)
    // Filter out WebGL shader warnings from SwiftShader
    const criticalErrors = errors.filter(e => 
      !e.includes('favicon') && 
      !e.includes('WebGLProgram') && 
      !e.includes('Shader Error')
    )
    expect(criticalErrors).toHaveLength(0)
  })

  test('should render hero section', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.hero-title')).toContainText('JarvisERP')
    await expect(page.locator('.hero-pitch')).toBeVisible()
  })

  test('should render all main sections', async ({ page }) => {
    await page.goto('/')
    
    await expect(page.locator('#the-moment')).toBeVisible()
    await expect(page.locator('#architecture')).toBeVisible()
    await expect(page.locator('#live-engine')).toBeVisible()
    await expect(page.locator('#five-problems')).toBeVisible()
    await expect(page.locator('#glossary')).toBeVisible()
  })

  test('should render particle canvas', async ({ page }) => {
    await page.goto('/')
    const canvas = page.locator('#particle-canvas')
    await expect(canvas).toBeVisible()
  })

  test('should handle the moment interaction', async ({ page }) => {
    await page.goto('/')
    await page.locator('#the-moment').scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)
    
    const bankLine = page.locator('#bank-line')
    await expect(bankLine).toBeVisible()
    
    await bankLine.click()
    await page.waitForTimeout(2000)
    
    const splitCards = page.locator('.split-cards')
    await expect(splitCards).toHaveCSS('opacity', /[0-9.]/)
  })

  test('should test state machine', async ({ page }) => {
    await page.goto('/')
    await page.locator('#live-engine').scrollIntoViewIfNeeded()
    
    const stateDisplay = page.locator('#state-display')
    await expect(stateDisplay).toContainText('new')
    
    await page.click('#btn-propose')
    await page.waitForTimeout(100)
    await expect(stateDisplay).toContainText('proposed')
    
    await page.click('#btn-approve-jarvis')
    await page.waitForTimeout(100)
    const message = page.locator('#state-message')
    await expect(message).toContainText('403')
  })

  test('should verify audit chain', async ({ page }) => {
    await page.goto('/')
    await page.locator('#live-engine').scrollIntoViewIfNeeded()
    
    await page.click('#btn-propose')
    await page.waitForTimeout(200)
    
    await page.click('#btn-tamper')
    await page.waitForTimeout(100)
    
    await page.click('#btn-verify')
    await page.waitForTimeout(100)
    
    const verifyResult = page.locator('#verify-result')
    await expect(verifyResult).toContainText('broken')
  })

  test('should search glossary', async ({ page }) => {
    await page.goto('/')
    await page.locator('#glossary').scrollIntoViewIfNeeded()
    
    const search = page.locator('#glossary-search')
    await search.fill('debit')
    await page.waitForTimeout(100)
    
    const terms = page.locator('.glossary-term')
    const count = await terms.count()
    expect(count).toBeGreaterThan(0)
    expect(count).toBeLessThan(20)
  })
})

test.describe('Screenshots', () => {
  test('hero section desktop', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await expect(page.locator('#hero')).toBeVisible()
    await page.screenshot({ path: 'tests/screenshots/hero-desktop.png', fullPage: false })
  })

  test('the moment desktop', async ({ page }) => {
    await page.goto('/')
    await page.locator('#the-moment').scrollIntoViewIfNeeded()
    await page.waitForTimeout(300)
    await page.screenshot({ path: 'tests/screenshots/moment-desktop.png', fullPage: false })
  })

  test('engine desktop', async ({ page }) => {
    await page.goto('/')
    await page.locator('#live-engine').scrollIntoViewIfNeeded()
    await page.waitForTimeout(300)
    await page.screenshot({ path: 'tests/screenshots/engine-desktop.png', fullPage: false })
  })

  test('hero section mobile', async ({ page, browserName }) => {
    if (browserName !== 'chromium') return
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'tests/screenshots/hero-mobile.png', fullPage: false })
  })
})

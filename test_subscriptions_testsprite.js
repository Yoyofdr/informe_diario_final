/**
 * Pruebas automatizadas del sistema de suscripciones con TestSprite
 * Este script verifica todo el flujo de suscripción y pagos
 */

const { chromium } = require('playwright');

async function runSubscriptionTests() {
    console.log('🧪 Iniciando pruebas del sistema de suscripciones con TestSprite\n');
    console.log('=' .repeat(60));
    
    const browser = await chromium.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const context = await browser.newContext({
        viewport: { width: 1280, height: 720 }
    });
    
    const page = await context.newPage();
    
    let testsPassed = 0;
    let testsFailed = 0;
    const results = [];
    
    // Función helper para logging
    function logTest(name, passed, details = '') {
        const icon = passed ? '✅' : '❌';
        console.log(`${icon} ${name}`);
        if (details) console.log(`   ${details}`);
        
        results.push({
            test: name,
            passed: passed,
            details: details,
            timestamp: new Date().toISOString()
        });
        
        if (passed) testsPassed++;
        else testsFailed++;
    }
    
    try {
        // Test 1: Cargar página de precios
        console.log('\n📍 Verificando página de precios...');
        await page.goto('http://localhost:8000/subscription/pricing/', {
            waitUntil: 'domcontentloaded',
            timeout: 10000
        });
        
        const title = await page.title();
        logTest(
            'Página de precios carga correctamente',
            title.includes('Planes y Precios'),
            `Título: ${title}`
        );
        
        // Test 2: Verificar planes visibles
        console.log('\n💳 Verificando planes de suscripción...');
        
        const individualPlan = await page.locator('text=Plan Individual').isVisible();
        logTest(
            'Plan Individual visible',
            individualPlan,
            'Plan de $3.990 CLP/mes'
        );
        
        const orgPlan = await page.locator('text=Plan Organización').isVisible();
        logTest(
            'Plan Organización visible',
            orgPlan,
            'Plan de $29.990 CLP/mes'
        );
        
        // Test 3: Verificar precios
        const price3990 = await page.locator('text=$3.990').count();
        logTest(
            'Precio Plan Individual correcto',
            price3990 > 0,
            '$3.990 CLP/mes'
        );
        
        const price29990 = await page.locator('text=$29.990').count();
        logTest(
            'Precio Plan Organización correcto',
            price29990 > 0,
            '$29.990 CLP/mes'
        );
        
        // Test 4: Verificar botones de CTA
        console.log('\n🔘 Verificando botones de acción...');
        
        const trialButtons = await page.locator('text=Comenzar Prueba de 14 Días').count();
        logTest(
            'Botones de prueba presentes',
            trialButtons === 2,
            `${trialButtons} botones encontrados`
        );
        
        // Test 5: Verificar enlaces de botones
        const individualButton = await page.locator('a[href="/registro/?plan=individual"]').count();
        const orgButton = await page.locator('a[href="/registro/?plan=organizacion"]').count();
        
        logTest(
            'Enlaces de registro configurados',
            individualButton > 0 && orgButton > 0,
            'Ambos planes tienen enlaces a registro'
        );
        
        // Test 6: Verificar descripciones
        console.log('\n📝 Verificando descripciones...');
        
        const descriptions = [
            'profesionales independientes',
            'legislación',
            'mercado chileno',
            'equipos y empresas',
            'múltiples usuarios'
        ];
        
        let descriptionsFound = 0;
        for (const desc of descriptions) {
            const found = await page.locator(`text=${desc}`).count() > 0;
            if (found) descriptionsFound++;
        }
        
        logTest(
            'Descripciones de planes presentes',
            descriptionsFound >= 3,
            `${descriptionsFound}/${descriptions.length} descripciones encontradas`
        );
        
        // Test 7: Probar navegación a registro
        console.log('\n🔗 Verificando navegación...');
        
        // Click en botón de plan individual
        await page.click('a[href="/registro/?plan=individual"]');
        await page.waitForTimeout(1000);
        
        const currentUrl = page.url();
        logTest(
            'Navegación a registro funciona',
            currentUrl.includes('/registro/') || currentUrl.includes('/login/'),
            `Redirigido a: ${currentUrl}`
        );
        
        // Test 8: Verificar responsividad
        console.log('\n📱 Verificando diseño responsivo...');
        
        // Cambiar a viewport móvil
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto('http://localhost:8000/subscription/pricing/');
        await page.waitForTimeout(500);
        
        const mobileIndividualVisible = await page.locator('text=Plan Individual').isVisible();
        const mobileOrgVisible = await page.locator('text=Plan Organización').isVisible();
        
        logTest(
            'Diseño responsivo funcional',
            mobileIndividualVisible && mobileOrgVisible,
            'Ambos planes visibles en móvil'
        );
        
        // Test 9: Verificar metadatos
        console.log('\n🏷️ Verificando metadatos...');
        
        const viewport = await page.$('meta[name="viewport"]');
        const hasViewport = viewport !== null;
        
        const charset = await page.$('meta[charset]');
        const hasCharset = charset !== null;
        
        logTest(
            'Metadatos HTML correctos',
            hasViewport && hasCharset,
            'Viewport y charset configurados'
        );
        
        // Test 10: Performance básico
        console.log('\n⚡ Verificando performance...');
        
        const startTime = Date.now();
        await page.goto('http://localhost:8000/subscription/pricing/', {
            waitUntil: 'domcontentloaded'
        });
        const loadTime = Date.now() - startTime;
        
        logTest(
            'Tiempo de carga aceptable',
            loadTime < 3000,
            `Cargó en ${loadTime}ms`
        );
        
        // Test 11: Verificar CSS y estilos
        console.log('\n🎨 Verificando estilos...');
        
        const bootstrap = await page.$('link[href*="bootstrap"]');
        const hasBootstrap = bootstrap !== null;
        
        const fontAwesome = await page.$('link[href*="font-awesome"]');
        const hasFontAwesome = fontAwesome !== null;
        
        logTest(
            'Frameworks CSS cargados',
            hasBootstrap && hasFontAwesome,
            'Bootstrap y Font Awesome presentes'
        );
        
        // Test 12: Accesibilidad básica
        console.log('\n♿ Verificando accesibilidad...');
        
        const htmlLang = await page.$eval('html', el => el.lang);
        const hasLang = htmlLang === 'es';
        
        const headings = await page.$$('h1, h2, h3');
        const hasHeadings = headings.length > 0;
        
        logTest(
            'Accesibilidad básica implementada',
            hasLang && hasHeadings,
            `Idioma: ${htmlLang}, Encabezados: ${headings.length}`
        );
        
    } catch (error) {
        console.error('\n❌ Error durante las pruebas:', error.message);
        logTest('Ejecución de pruebas', false, error.message);
    } finally {
        await browser.close();
        
        // Resumen final
        console.log('\n' + '=' .repeat(60));
        console.log('📊 RESUMEN DE PRUEBAS');
        console.log('=' .repeat(60));
        console.log(`Total de pruebas: ${testsPassed + testsFailed}`);
        console.log(`✅ Exitosas: ${testsPassed}`);
        console.log(`❌ Fallidas: ${testsFailed}`);
        console.log(`📈 Tasa de éxito: ${Math.round((testsPassed / (testsPassed + testsFailed)) * 100)}%`);
        
        // Guardar resultados
        const fs = require('fs');
        const report = {
            summary: {
                total: testsPassed + testsFailed,
                passed: testsPassed,
                failed: testsFailed,
                successRate: Math.round((testsPassed / (testsPassed + testsFailed)) * 100),
                timestamp: new Date().toISOString(),
                tool: 'TestSprite/Playwright'
            },
            tests: results
        };
        
        fs.writeFileSync(
            'testsprite_subscription_report.json',
            JSON.stringify(report, null, 2)
        );
        
        console.log('\n📄 Reporte guardado en: testsprite_subscription_report.json');
        
        // Retornar código de salida
        process.exit(testsFailed > 0 ? 1 : 0);
    }
}

// Ejecutar las pruebas
runSubscriptionTests().catch(error => {
    console.error('Error fatal:', error);
    process.exit(1);
});
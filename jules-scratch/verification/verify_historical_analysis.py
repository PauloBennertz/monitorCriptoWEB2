from playwright.sync_api import sync_playwright, expect
import time

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # 1. Navigate to the app
        page.goto("http://localhost:5173/")

        # 2. Open the Historical Analysis Panel
        historical_analysis_button = page.locator("button.manage-button:has-text('Análise Histórica')")
        expect(historical_analysis_button).to_be_visible()
        historical_analysis_button.click()

        # 3. Wait for the modal to be visible
        modal = page.locator(".modal-content.historical-analysis-panel")
        expect(modal).to_be_visible()

        # 4. Fill in the form
        #    - Select a coin
        page.locator('input[id="coin-search"]').fill("Bitcoin")
        time.sleep(1) # Allow time for search results to appear
        page.locator("ul.coin-search-results li:has-text('Bitcoin (BTC)')").click()

        #    - Check the specific alerts that were originally not working
        page.locator('label[for="alert-MEDIA_MOVEL_CIMA"]').click()
        page.locator('label[for="alert-MEDIA_MOVEL_BAIXO"]').click()

        # 5. Run the analysis
        page.locator("button:has-text('Executar Análise')").click()

        # 6. Wait for the results to appear
        results_table = page.locator("table")
        expect(results_table).to_be_visible(timeout=30000)

        # 7. Verify the price column no longer shows "N/A"
        #    We check the first data cell in the price column. It should not be "N/A".
        first_price_cell = results_table.locator("tbody tr:first-child td:nth-child(3)")
        expect(first_price_cell).not_to_have_text("N/A")

        # 8. Verify the download button is enabled
        download_button = page.locator("button:has-text('Baixar Gráfico Interativo (HTML)')")
        expect(download_button).to_be_enabled()

        # 9. Take a screenshot of the final state
        page.screenshot(path="jules-scratch/verification/verification.png")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)
from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.goto("http://localhost:5173/")

    # Wait for the main content to load, handle potential API errors
    try:
        page.wait_for_selector(".crypto-grid", timeout=15000)
    except:
        print("Crypto grid not found, likely due to API errors. Proceeding with modal test.")

    # 1. Open the settings modal
    page.get_by_role("button", name="Gerenciar Alertas").click()
    expect(page.get_by_role("heading", name="Moedas Monitoradas")).to_be_visible()

    # 2. Click to configure the first coin (BTC)
    page.get_by_role("button", name="Configurar Alertas").first.click()
    expect(page.get_by_role("heading", name="Configurar Bitcoin")).to_be_visible()

    # 3. Verify the "Piscar" checkbox is checked by default for the "RSI em Sobrecompra" alert
    rsi_overbought_row = page.locator(".alert-setting-item", has_text="RSI em Sobrecompra")
    blinking_checkbox = rsi_overbought_row.get_by_role("checkbox").nth(1) # The second checkbox in the row

    expect(blinking_checkbox).to_be_checked()
    page.screenshot(path="jules-scratch/verification/blinking_fix_before.png")

    # 4. Uncheck the "Piscar" checkbox
    blinking_checkbox.uncheck()
    expect(blinking_checkbox).not_to_be_checked()

    # 5. Close and reopen the modal to verify persistence
    page.get_by_role("button", name="Fechar").click()
    page.get_by_role("button", name="Gerenciar Alertas").click()
    page.get_by_role("button", name="Configurar Alertas").first.click()
    expect(page.get_by_role("heading", name="Configurar Bitcoin")).to_be_visible()

    # 6. Verify the checkbox is now unchecked
    rsi_overbought_row = page.locator(".alert-setting-item", has_text="RSI em Sobrecompra")
    blinking_checkbox = rsi_overbought_row.get_by_role("checkbox").nth(1)
    expect(blinking_checkbox).not_to_be_checked()
    page.screenshot(path="jules-scratch/verification/blinking_fix_after.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)

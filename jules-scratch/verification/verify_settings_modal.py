from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.goto("http://localhost:5173/")

    # Wait for the header to load
    page.wait_for_selector(".app-header")

    # Click the "Gerenciar Aleras" button
    page.click("button:has-text('Gerenciar Alertas')")

    # Wait for the modal to appear
    page.wait_for_selector(".modal-content")

    # Since there are no monitored coins due to the API error, we can't configure one.
    # We will take a screenshot of the initial state of the modal.
    page.screenshot(path="jules-scratch/verification/settings_modal_empty.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)

from playwright.sync_api import sync_playwright, Page, expect

def run_verification(page: Page):
    """
    This script verifies that the backtester panel opens, a backtest can be run,
    and the resulting chart is displayed.
    """
    # 1. Navigate to the application
    page.goto("http://localhost:5173")

    # 2. Click the "Iniciar Backtester" button
    start_backtester_button = page.get_by_role("button", name="Iniciar Backtester")
    expect(start_backtester_button).to_be_visible()
    start_backtester_button.click()

    # 3. Wait for the panel to appear and verify its title
    backtester_panel_title = page.get_by_role("heading", name="Backtester")
    expect(backtester_panel_title).to_be_visible()

    # 4. Click the "Run Backtest" button
    run_backtest_button = page.get_by_role("button", name="Run Backtest")
    expect(run_backtest_button).to_be_visible()
    run_backtest_button.click()

    # 5. Wait for the chart to be displayed
    # We can wait for the plotly chart container to be visible
    chart_container = page.locator(".js-plotly-plot")
    expect(chart_container).to_be_visible(timeout=60000) # Increase timeout for backtest

    # 6. Take a screenshot
    page.screenshot(path="jules-scratch/verification/backtester_chart.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        run_verification(page)
        browser.close()

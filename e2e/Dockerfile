# Rauchtest-Läufer (#52). Das offizielle Playwright-Image bringt die Browser
# samt Systembibliotheken mit — die Version MUSS zur @playwright/test-Version
# in package.json passen (sonst startet der Browser nicht).
FROM mcr.microsoft.com/playwright:v1.62.1-noble

WORKDIR /e2e

# package-lock.json ist committed (im Node-Container erzeugt) → npm ci = reproduzierbar
COPY package.json package-lock.json ./
# Browser sind im Image, der Post-Install-Download wäre reine Verschwendung.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN npm ci --no-audit --no-fund

COPY playwright.config.ts ./
COPY tests/ ./tests/

CMD ["npx", "playwright", "test"]

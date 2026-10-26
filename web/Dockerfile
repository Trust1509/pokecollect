FROM node:22-alpine AS builder

WORKDIR /app

# package-lock.json ist committed (im Node-Container erzeugt) → npm ci = reproduzierbar
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

ARG NEXT_PUBLIC_API_URL=http://localhost:3010
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY . .
RUN mkdir -p public && npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# #117: npm samt seinem mitgelieferten tar wird zur Laufzeit nicht gebraucht
# (CMD ist node server.js) — Trivy meldete tar 6.2.1 aus genau diesem npm.
# Dasselbe für corepack und yarn (Panel zu #117: blieben im Image, ungenutzt).
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx \
    /usr/local/lib/node_modules/corepack /usr/local/bin/corepack \
    /usr/local/bin/yarn /usr/local/bin/yarnpkg /opt/yarn-*

# #98: Was dieser Container seit sharp NEU verbraucht (Panel-Fund: die
# Dauerlast stand nirgends). sharp/libvips rechnet nativ und mehrfädig —
# Next drosselt in production auf cpus()/2 Threads (image-optimizer.ts).
# Erster Abruf eines Bildes kostet damit CPU (gemessen 0,355 s), jeder
# weitere kommt aus dem Cache (0,004 s). Der Cache selbst liegt zur Laufzeit
# in einem tmpfs mit hartem 256-MB-Deckel (alle drei Compose-Dateien) und
# zählt damit gegen den Arbeitsspeicher, nicht gegen die Platte. Das Image
# wächst durch die Plattform-Binaries deutlich (gemessen 226 → 287 MB,
# +27 %; mit Next 15 und Node 22 355 MB, gemessen 26.10.2026); Abspecken
# ist als eigenes Thema notiert, nicht Teil dieses Slices.

RUN addgroup --system --gid 3010 pokecollect && \
    adduser --system --uid 3010 --ingroup pokecollect pokecollect

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# #98: next/image (sharp) legt seinen Bild-Cache erst beim ersten Abruf an
# (mkdir '/app/.next/cache/images') — das Verzeichnis existiert nach den COPYs
# oben noch nicht und alles darüber gehört root; ohne chown scheitert das
# mkdir mit EACCES, sobald der Prozess als pokecollect (uid 3010) läuft.
# Panel-Nacharbeit: chown NUR auf .next/cache, nicht rekursiv auf .next.
# Beide Stimmen bemängelten den weiten Griff; gegengemessen wurde, dass der
# enge dieselbe Wirkung hat (Cache wird geschrieben, 0 EACCES). Damit bleiben
# Server-Bundles, Manifeste, required-server-files.json und .next/static —
# also ausgeführter Server-Code und an jeden Browser ausgeliefertes
# JavaScript — root-eigen und für uid 3010 nur lesbar.
RUN mkdir -p .next/cache/images && chown -R pokecollect:pokecollect .next/cache

USER pokecollect

EXPOSE 3000

CMD ["node", "server.js"]

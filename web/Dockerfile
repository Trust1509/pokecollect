FROM node:20-alpine AS builder

WORKDIR /app

# package-lock.json ist committed (im Node-Container erzeugt) → npm ci = reproduzierbar
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

ARG NEXT_PUBLIC_API_URL=http://localhost:3010
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY . .
RUN mkdir -p public && npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 3010 pokecollect && \
    adduser --system --uid 3010 --ingroup pokecollect pokecollect

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# #98: next/image (sharp) legt seinen Bild-Cache erst beim ersten Abruf an
# (mkdir '/app/.next/cache/images') — das Verzeichnis existiert nach den COPYs
# oben noch nicht und alles darüber gehört root; ohne chown scheitert das
# mkdir mit EACCES, sobald der Prozess als pokecollect (uid 3010) läuft.
RUN mkdir -p .next/cache/images && chown -R pokecollect:pokecollect .next

USER pokecollect

EXPOSE 3000

CMD ["node", "server.js"]

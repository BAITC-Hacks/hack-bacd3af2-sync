FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Baked into the bundle at build time; the browser calls the API directly.
ARG VITE_API_BASE_URL=http://localhost:8000/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/package.json /app/package-lock.json ./
RUN npm ci
COPY --from=build /app/dist ./dist
COPY --from=build /app/vite.config.ts ./

EXPOSE 5173
CMD ["npm", "run", "preview"]

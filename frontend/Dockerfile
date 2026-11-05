# Etap 1: budowanie aplikacji (TypeScript -> zwykły JavaScript, HTML i CSS)
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Etap 2: serwowanie gotowych plików przez nginx
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
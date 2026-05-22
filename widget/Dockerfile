FROM node:20-alpine AS build

WORKDIR /widget

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /widget/dist/ /usr/share/nginx/html/

EXPOSE 80

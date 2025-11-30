# --- Stage 1: Build the frontend ---
FROM node:18 AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build


# --- Stage 2: Serve with Nginx ---
FROM nginx:stable-alpine

RUN rm -rf /usr/share/nginx/html/*

# Copy build from Vite
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
